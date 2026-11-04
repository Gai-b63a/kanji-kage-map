"""Build and query a portable, offline dataset without the full upstream index."""
from contextlib import closing
import gzip
import json
from pathlib import Path
import shutil
import sqlite3

from .glyphwiki import digest_file
from .lookup import normalize_identifier
from .sources import write_json
from .syntax import inspect_bundle


def records(path):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            yield json.loads(line)


def build_release(directory, output, project):
    directory, output, project = Path(directory), Path(output), Path(project)
    if output.exists():
        raise ValueError('Release database exists; use a new output path')
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + '.part')
    if partial.exists():
        raise ValueError('Partial build exists; inspect it before rebuilding')
    summary = json.loads((directory / 'mappings.summary.json').read_text(encoding='utf-8'))
    if digest_file(directory / 'mappings.jsonl') != summary['output_sha256']:
        raise ValueError('Mapping checksum mismatch')
    inputs = {'mappings.jsonl': summary['output_sha256'], 'inventory.jsonl':digest_file(directory / 'inventory.jsonl')}
    for prefix in ('dependency-audit', 'pua-research/dependency-audit'):
        audit = directory / prefix
        report = json.loads((audit / 'dependency-summary.json').read_text(encoding='utf-8'))
        if report['snapshot_sha256'] != summary['snapshot_sha256']:
            raise ValueError('Mixed GlyphWiki snapshots')
        hashes = json.loads((audit / 'checksums.json').read_text(encoding='utf-8'))
        for name in ('glyphs.jsonl', 'dependencies.jsonl', 'dependency-issues.jsonl'):
            digest = digest_file(audit / name)
            if digest != hashes[name]:
                raise ValueError(f'Audit artifact changed: {prefix}/{name}')
            inputs[prefix + '/' + name] = digest
    with closing(sqlite3.connect(partial)) as db:
        db.executescript('''
          CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL) WITHOUT ROWID;
          CREATE TABLE inventory(entity_id TEXT PRIMARY KEY,json TEXT NOT NULL) WITHOUT ROWID;
          CREATE TABLE mappings(entity_id TEXT PRIMARY KEY,json TEXT NOT NULL) WITHOUT ROWID;
          CREATE TABLE glyphs(reference TEXT PRIMARY KEY,json TEXT NOT NULL) WITHOUT ROWID;
          CREATE TABLE dependencies(parent TEXT,line INTEGER,raw_reference TEXT,target TEXT,
                                    PRIMARY KEY(parent,line)) WITHOUT ROWID;
          CREATE TABLE issues(reference TEXT,json TEXT NOT NULL);
        ''')
        def put(key, value):
            db.execute('INSERT INTO metadata VALUES (?,?)', (key, json.dumps(value, ensure_ascii=False, sort_keys=True)))
        put('format', 'kanji-kage-map-portable-v0.1')
        put('status', 'provisional-unreviewed')
        put('snapshot_sha256', summary['snapshot_sha256'])
        put('inputs', inputs)
        for file in ('sources.lock.json', 'glyphwiki.lock.json'):
            put(file, json.loads((project / file).read_text(encoding='utf-8')))
        for table, name in [('inventory','inventory.jsonl'), ('mappings','mappings.jsonl')]:
            batch = []
            for row in records(directory / name):
                batch.append((row['entity_id'], json.dumps(row, ensure_ascii=False, sort_keys=True)))
                if len(batch) == 5000:
                    db.executemany(f'INSERT INTO {table} VALUES (?,?)', batch)
                    db.commit()
                    batch.clear()
            db.executemany(f'INSERT INTO {table} VALUES (?,?)', batch)
            db.commit()
            print(table, 'loaded', flush=True)
        for prefix in ('dependency-audit', 'pua-research/dependency-audit'):
            audit = directory / prefix
            for index, row in enumerate(records(audit / 'glyphs.jsonl'), 1):
                encoded = json.dumps(row, ensure_ascii=False, sort_keys=True)
                if prefix.startswith('pua-'):
                    existing = db.execute('SELECT json FROM glyphs WHERE reference=?', (row['reference'],)).fetchone()
                    if existing:
                        if existing[0] != encoded:
                            raise ValueError('Conflicting glyph records')
                        continue
                db.execute('INSERT INTO glyphs VALUES (?,?)', (row['reference'], encoded))
                if index % 10000 == 0:
                    db.commit()
            db.commit()
            for index, row in enumerate(records(audit / 'dependencies.jsonl'), 1):
                values = (row['parent'], row['line'], row['raw_reference'], row['target'])
                if prefix.startswith('pua-'):
                    existing = db.execute('SELECT raw_reference,target FROM dependencies WHERE parent=? AND line=?', values[:2]).fetchone()
                    if existing:
                        if tuple(existing) != values[2:]:
                            raise ValueError('Conflicting dependency records')
                        continue
                db.execute('INSERT INTO dependencies VALUES (?,?,?,?)', values)
                if index % 10000 == 0:
                    db.commit()
            db.commit()
            for row in records(audit / 'dependency-issues.jsonl'):
                db.execute('INSERT INTO issues VALUES (?,?)', (row['reference'], json.dumps(row, sort_keys=True)))
            print(prefix, 'loaded', flush=True)
        if db.execute('SELECT COUNT(*) FROM inventory WHERE entity_id NOT IN (SELECT entity_id FROM mappings)').fetchone()[0] or \
           db.execute('SELECT COUNT(*) FROM mappings WHERE entity_id NOT IN (SELECT entity_id FROM inventory)').fetchone()[0]:
            raise ValueError('Inventory/mapping identifier mismatch')
        counts = {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                  for table in ('inventory','mappings','glyphs','dependencies','issues')}
        counts['missing_dependency_targets'] = db.execute('SELECT COUNT(*) FROM dependencies d LEFT JOIN glyphs g ON d.target=g.reference WHERE g.reference IS NULL').fetchone()[0]
        put('counts', counts)
        put('build_complete', True)
        db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity check failed')
    partial.replace(output)
    compressed = output.with_suffix(output.suffix + '.gz')
    with output.open('rb') as source, compressed.open('wb') as destination:
        with gzip.GzipFile(filename='', fileobj=destination, mode='wb', mtime=0, compresslevel=9) as packed:
            shutil.copyfileobj(source, packed, 1024 * 1024)
    report = dict(format='kanji-kage-map-portable-v0.1', snapshot_sha256=summary['snapshot_sha256'],
                  counts=counts, database_sha256=digest_file(output), gzip_sha256=digest_file(compressed),
                  database_bytes=output.stat().st_size, gzip_bytes=compressed.stat().st_size,
                  status='local-build-only-not-published', confirmed_matches=0)
    write_json(output.with_suffix('.manifest.json'), report)
    print(json.dumps(report, indent=2))


def lookup_release(dataset, value, glyph=None):
    from .review_decisions import attach_embedded
    identifier = normalize_identifier(value)
    with closing(sqlite3.connect(Path(dataset).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        metadata = {k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')}
        if metadata.get('format') != 'kanji-kage-map-portable-v0.1' or not metadata.get('build_complete'):
            raise ValueError('Not a completed portable dataset')
        found = db.execute('SELECT json FROM mappings WHERE entity_id=?', (identifier,)).fetchone()
        if not found:
            raise ValueError('Identifier is not in the adopted inventory')
        result = json.loads(found[0])
        result['bundle'] = None
        result['bundle_status'] = 'choose_candidate' if result['candidates'] else 'no_evidence_backed_candidate'
        if glyph is None:
            return attach_embedded(result, metadata)
        candidate = next((c for c in result['candidates'] if c['name'] == glyph), None)
        if not candidate or candidate['revision'] is None:
            raise ValueError('Requested glyph is not a pinned candidate')
        root = f"{glyph}@{candidate['revision']}"
        glyphs, edges, problems = {}, [], []
        active, visited = set(), set()
        stack = [(root, root, False)]
        while stack:
            ref, alias, leaving = stack.pop()
            if leaving:
                active.remove(ref)
                visited.add(ref)
                continue
            row = db.execute('SELECT json FROM glyphs WHERE reference=?', (ref,)).fetchone()
            if row is None:
                problems.append(dict(reference=alias, reason='missing_reference'))
                continue
            data = json.loads(row[0])
            glyphs[alias] = data
            if ref in active:
                problems.append(dict(reference=alias, reason='cycle'))
                continue
            if ref in visited:
                continue
            active.add(ref)
            stack.append((ref, alias, True))
            problems.extend(json.loads(row[0]) for row in db.execute('SELECT json FROM issues WHERE reference=?',(ref,)))
            for line, raw, target in db.execute('SELECT line,raw_reference,target FROM dependencies WHERE parent=? ORDER BY line',(ref,)):
                edges.append(dict(parent=ref,line=line,raw_reference=raw,target=target))
                stack.append((target,raw,False))
        result['bundle_status'] = 'requested_candidate'
        result['bundle'] = dict(root=root, snapshot_sha256=metadata['snapshot_sha256'], glyphs=glyphs,
                               dependencies=edges, issues=problems, dependency_status='issues' if problems else 'complete',
                               review_status='unreviewed', render_status='not_run')
        result['static_syntax_audit'] = inspect_bundle(result['bundle'])
        return attach_embedded(result, metadata)
