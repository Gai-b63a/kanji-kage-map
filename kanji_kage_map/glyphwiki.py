"""Official dump acquisition and loss-aware indexing."""
import hashlib
import json
import re
import sqlite3
import tarfile
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from .sources import write_json


def fetch_dump(lock_path):
    lock = Path(lock_path).resolve()
    if lock.exists():
        raise ValueError('Dump lock exists; choose a new lock for a new snapshot')
    raw = lock.parent / 'data' / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    partial = raw / 'glyphwiki.download.part'
    digest = hashlib.sha256()
    size = 0
    url = 'https://glyphwiki.org/dump.tar.gz'
    with urlopen(Request(url, headers={'User-Agent': 'kanji-kage-map/0.1'}), timeout=60) as response:
        metadata = dict(url=url, final_url=response.url,
                        http_last_modified=response.headers.get('Last-Modified'),
                        etag=response.headers.get('ETag'))
        with partial.open('xb') as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
                size += len(chunk)
    target = raw / digest.hexdigest() / 'dump.tar.gz'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError('Snapshot already exists; preserve partial and inspect existing snapshot')
    partial.rename(target)
    metadata.update(schema_version=1, provider='GlyphWiki', sha256=digest.hexdigest(), bytes=size,
                    path=target.relative_to(lock.parent).as_posix(),
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    license_status='pending-extraction-from-archive')
    write_json(lock, metadata)
    print(json.dumps(metadata, indent=2))


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_row(raw, history):
    """Keep KAGE and related values; remove only aligned table padding."""
    text = raw.decode('utf-8').rstrip('\r\n')
    fields = text.split('|', 2)
    if len(fields) != 3:
        return None
    name, related, data = (f.strip() for f in fields)
    if name == 'name':
        return None
    name = name.replace('\\@', '@').replace('\\\\', '\\')
    if history:
        match = re.fullmatch(r'(.+)@(\d+)', name)
        if not match:
            raise ValueError('History row has no revision')
        name, revision = match[1], int(match[2])
    else:
        revision = None
    if not re.fullmatch(r'[a-z0-9_.-]+', name):
        raise ValueError('Unexpected glyph name')
    return name, revision, related, data


def index_dump(lock_path, database, report_dir):
    lock_path = Path(lock_path).resolve()
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    archive = (lock_path.parent / lock['path']).resolve()
    if not archive.is_relative_to(lock_path.parent):
        raise ValueError('Archive escapes project')
    if archive.stat().st_size != lock['bytes'] or digest_file(archive) != lock['sha256']:
        raise ValueError('Archive checksum mismatch')
    database, report_dir = Path(database), Path(report_dir)
    if database.exists():
        raise ValueError('Index already exists; choose a new output')
    database.parent.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    with closing(sqlite3.connect(database)) as db, tarfile.open(archive) as tar, (report_dir / 'import-issues.jsonl').open('w', encoding='utf-8', newline='\n') as issues:
        db.executescript('''
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE history (name TEXT, revision INTEGER, related TEXT, data TEXT, line INTEGER,
                                  PRIMARY KEY(name, revision)) WITHOUT ROWID;
            CREATE TABLE latest (name TEXT PRIMARY KEY, revision INTEGER, related TEXT, data TEXT, line INTEGER) WITHOUT ROWID;
        ''')
        db.execute('INSERT INTO metadata VALUES (?, ?)', ('snapshot_sha256', lock['sha256']))
        db.execute('INSERT INTO metadata VALUES (?, ?)', ('build_status', 'building'))
        db.commit()
        for member in ('dump_newest_only.txt', 'dump_all_versions.txt'):
            history = member == 'dump_all_versions.txt'
            table = 'history' if history else 'latest'
            count = Counter()
            batch = []
            for line, raw in enumerate(tar.extractfile(member), 1):
                count['total_lines'] += 1
                try:
                    parsed = parse_row(raw, history)
                except (UnicodeError, ValueError) as error:
                    count['issues'] += 1
                    issues.write(json.dumps(dict(member=member, line=line, reason=str(error),
                                                 raw=raw.decode('utf-8', errors='replace')), ensure_ascii=False) + '\n')
                    continue
                if parsed is None:
                    # Retain every non-data line for audit; do not silently discard.
                    count['non_data'] += 1
                    issues.write(json.dumps(dict(member=member, line=line, reason='non_data_line',
                                                 raw=raw.decode('utf-8')), ensure_ascii=False) + '\n')
                    continue
                batch.append((*parsed, line))
                count['rows'] += 1
                if len(batch) >= 10000:
                    db.executemany(f'INSERT INTO {table} VALUES (?,?,?,?,?)', batch)
                    db.commit()
                    batch.clear()
            db.executemany(f'INSERT INTO {table} VALUES (?,?,?,?,?)', batch)
            db.commit()
            counts[member] = dict(count)
            print(member, dict(count), flush=True)
        # Only the maximum revision can establish the snapshot's current revision.
        db.execute('''UPDATE latest SET revision = (
            SELECT h.revision FROM history h WHERE h.name=latest.name
            AND h.revision=(SELECT MAX(revision) FROM history WHERE name=latest.name)
            AND h.data=latest.data AND h.related=latest.related)''')
        unresolved = db.execute('SELECT COUNT(*) FROM latest WHERE revision IS NULL').fetchone()[0]
        empty = db.execute("SELECT COUNT(*) FROM latest WHERE data='' ").fetchone()[0]
        db.execute('CREATE INDEX latest_related ON latest(related)')
        for member in ('LICENSE.txt', 'README_en.txt', 'README_ja.txt'):
            (report_dir / member).write_bytes(tar.extractfile(member).read())
        status = 'complete' if not any(c.get('issues', 0) for c in counts.values()) else 'needs_review'
        db.execute('UPDATE metadata SET value=? WHERE key=?', (status, 'build_status'))
        db.commit()
    report = dict(schema_version=1, snapshot_sha256=lock['sha256'], counts=counts,
                  unresolved_latest_revisions=unresolved, empty_latest_data=empty, build_status=status,
                  license_sha256=digest_file(report_dir / 'LICENSE.txt'))
    write_json(report_dir / 'index-summary.json', report)
    print(json.dumps(report, indent=2))


def open_index(database):
    db = sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    status = db.execute("SELECT value FROM metadata WHERE key='build_status'").fetchone()
    if not status or status[0] != 'complete':
        db.close()
        raise ValueError('Index is not complete; inspect import report')
    return db


def collect_candidates(database, inventory_path, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    totals = Counter()
    with closing(open_index(database)) as db, Path(inventory_path).open(encoding='utf-8') as inventory, \
            (output / 'candidates.jsonl').open('w', encoding='utf-8', newline='\n') as destination:
        snapshot = db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0]
        for line in inventory:
            entity = json.loads(line)
            candidates = {}
            if entity['provider'] == 'Unicode':
                base = 'u' + format(int(entity['local_id'][2:], 16), '04x')
                searches = [('unicode_name', 'name=?', (base,)),
                            ('name_suffix', 'name>=? AND name<?', (base + '-', base + '.')),
                            ('related_field', 'related=?', (base,))]
                for rule, where, params in searches:
                    for row in db.execute('SELECT name,revision,related,line FROM latest WHERE ' + where, params):
                        item = candidates.setdefault(row['name'], dict(name=row['name'], revision=row['revision'],
                            related=row['related'], source_line=row['line'], rules=[],
                            revision_status='resolved' if row['revision'] is not None else 'unresolved'))
                        item['rules'].append(rule)
                search_status = 'candidates_found' if candidates else 'no_candidate_in_searched_rules'
            else:
                search_status = 'requires_source_evidence'
            record = dict(entity_id=entity['entity_id'], snapshot_sha256=snapshot,
                          search_status=search_status, mapping_status='candidate' if candidates else 'unreviewed',
                          review_status='unreviewed', selected_glyph=None,
                          candidates=[candidates[k] for k in sorted(candidates)])
            destination.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
            totals[search_status] += 1
            totals['entities'] += 1
            totals['candidate_links'] += len(candidates)
        summary = dict(snapshot_sha256=snapshot, inventory_sha256=digest_file(inventory_path),
                       counts=dict(totals), confirmed_matches=0,
                       rules=['unicode_name', 'name_suffix', 'related_field'],
                       limitation='Name and related-field hits are discovery evidence, not glyph equivalence.')
        write_json(output / 'candidate-summary.json', summary)
        print(json.dumps(summary, indent=2))


def resolve_bundle(database, reference):
    """Preserve pinned revisions and every dependency edge; never fall back."""
    with closing(open_index(database)) as db:
        snapshot = db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0]
        glyphs, edges, issues = {}, [], []
        visiting, done = set(), set()
        stack = [(reference, False)]
        while stack:
            key, leaving = stack.pop()
            if leaving:
                visiting.remove(key)
                done.add(key)
                continue
            if key in visiting:
                issues.append(dict(reference=key, reason='cycle'))
                continue
            if key in done:
                continue
            match = re.fullmatch(r'([a-z0-9_.-]+)(?:@(\d+))?', key)
            if not match:
                issues.append(dict(reference=key, reason='invalid_reference'))
                done.add(key)
                continue
            name, rev = match.groups()
            row = db.execute('SELECT * FROM history WHERE name=? AND revision=?', (name, int(rev))).fetchone() if rev else \
                db.execute('SELECT * FROM latest WHERE name=?', (name,)).fetchone()
            if row is None:
                issues.append(dict(reference=key, reason='missing_reference'))
                done.add(key)
                continue
            glyphs[key] = dict(row)
            if row['revision'] is None:
                issues.append(dict(reference=key, reason='revision_unresolved'))
            if not row['data']:
                issues.append(dict(reference=key, reason='empty_kage'))
            visiting.add(key)
            stack.append((key, True))
            for line, stroke in enumerate(row['data'].split('$'), 1):
                fields = stroke.split(':')
                if not fields[0].isdigit():
                    issues.append(dict(reference=key, line=line, reason='invalid_kage_command', raw=stroke))
                    continue
                if fields[0] != '99':
                    continue
                if len(fields) < 8:
                    issues.append(dict(reference=key, line=line, reason='malformed_dependency', raw=stroke))
                    continue
                child = fields[7]
                edges.append(dict(parent=key, line=line, raw_reference=child))
                stack.append((child, False))
        for edge in edges:
            target = glyphs.get(edge['raw_reference'])
            edge['resolved_name'] = target['name'] if target else None
            edge['resolved_revision'] = target['revision'] if target else None
        return dict(snapshot_sha256=snapshot, root=reference, glyphs=glyphs, dependencies=edges, issues=issues,
                    dependency_status='complete' if not issues else 'issues',
                    review_status='unreviewed', render_status='not_run')
