"""Propagate pinned static findings to every candidate through dependency edges."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import gzip
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.sources import write_json
from kanji_kage_map.syntax import inspect_kage
from kanji_kage_map.release import lookup_release


def propagate(db, references):
    db.execute('CREATE TEMP TABLE syntax_seeds(reference TEXT PRIMARY KEY)')
    db.executemany('INSERT INTO syntax_seeds VALUES (?)', [(ref,) for ref in references])
    # UNION removes duplicate (ancestor, origin) pairs and terminates even in cycles.
    sql = '''WITH RECURSIVE impact(reference,origin) AS (
      SELECT reference,reference FROM syntax_seeds
      UNION
      SELECT d.parent,i.origin FROM dependencies d JOIN impact i ON d.target=i.reference
    ) SELECT reference,origin FROM impact ORDER BY reference,origin'''
    result = defaultdict(list)
    for reference, origin in db.execute(sql):
        result[reference].append(origin)
    db.execute('DROP TABLE syntax_seeds')
    return result


def audit(dataset, findings, output):
    dataset, findings, output = Path(dataset), Path(findings), Path(output)
    summary = json.loads(findings.with_name('syntax-summary.json').read_text())
    if digest_file(dataset) != summary['database_sha256'] or digest_file(findings) != summary['issues_sha256']:
        raise ValueError('Static audit input hashes differ')
    if digest_file(Path(__file__).resolve().parents[1] / 'kanji_kage_map/syntax.py') != summary['checker_sha256']:
        raise ValueError('Static checker changed; regenerate its complete audit')
    sources = {}
    for line in findings.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if row['reference'] in sources:
            raise ValueError('Duplicate finding origin')
        sources[row['reference']] = row
    with closing(sqlite3.connect(dataset.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        snapshot = json.loads(db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0])
        if snapshot != summary['snapshot_sha256']:
            raise ValueError('Snapshot mismatch')
        for ref, issue in sources.items():
            row = db.execute('SELECT json FROM glyphs WHERE reference=?',(ref,)).fetchone()
            if row is None or issue['snapshot_sha256'] != snapshot or inspect_kage(json.loads(row[0])['data']) != issue['findings']:
                raise ValueError('Finding origin does not match preserved KAGE')
        affected = propagate(db, sorted(sources))
        output.mkdir(parents=True, exist_ok=True)
        artifact = output / 'syntax-candidate-impact.jsonl.gz'
        counts, reason_links, reason_entities = Counter(), Counter(), Counter()
        roots = set()
        with artifact.open('wb') as file, gzip.GzipFile(filename='',fileobj=file,mode='wb',mtime=0) as compressed:
            for entity, raw in db.execute('SELECT entity_id,json FROM mappings ORDER BY entity_id'):
                mapping = json.loads(raw)
                if mapping['snapshot_sha256'] != snapshot:
                    raise ValueError('Mapping snapshot mismatch')
                counts['entities_scanned'] += 1
                entity_reasons, found = set(), False
                for candidate in mapping['candidates']:
                    counts['candidate_links_scanned'] += 1
                    root = f"{candidate['name']}@{candidate['revision']}"
                    origins = affected.get(root, [])
                    if not origins:
                        continue
                    found = True
                    roots.add(root)
                    counts['affected_candidate_links'] += 1
                    counts['direct_finding_candidate_links' if root in origins else 'dependency_only_candidate_links'] += 1
                    reasons = sorted({f['reason'] for origin in origins for f in sources[origin]['findings']})
                    reason_links.update(reasons)
                    entity_reasons.update(reasons)
                    record = dict(entity_id=entity, candidate=root, origin_references=origins,
                                  reachable_reasons=reasons, has_direct_finding=root in origins,
                                  dependency_status=candidate['dependency_status'],
                                  review_status=mapping['review_status'])
                    compressed.write((json.dumps(record,ensure_ascii=False,sort_keys=True)+'\n').encode('utf-8'))
                if found:
                    counts['affected_entities'] += 1
                    reason_entities.update(entity_reasons)
    verified = 0
    with gzip.open(artifact,'rt',encoding='utf-8') as stream:
        for line in stream:
            impact = json.loads(line)
            result = lookup_release(dataset, impact['entity_id'], impact['candidate'].rsplit('@',1)[0])
            findings_in_bundle = result['static_syntax_audit']['findings']
            if sorted({f['reference'] for f in findings_in_bundle}) != impact['origin_references'] or sorted({f['reason'] for f in findings_in_bundle}) != impact['reachable_reasons']:
                raise ValueError('Propagation differs from direct resolved-bundle inspection')
            verified += 1
    result = dict(format='kage-static-impact-v1', snapshot_sha256=snapshot,
                  dataset_sha256=summary['database_sha256'], direct_findings_sha256=summary['issues_sha256'],
                  checker_sha256=summary['checker_sha256'], direct_finding_origins=len(sources),
                  reachable_nodes_with_findings=len(affected), counts=dict(counts), unique_affected_candidate_roots=len(roots),
                  candidate_links_by_reason=dict(sorted(reason_links.items())), entities_by_reason=dict(sorted(reason_entities.items())),
                  affected_links_verified_by_bundle_inspection=verified,
                  output_sha256=digest_file(artifact), output_bytes=artifact.stat().st_size,
                  limitation='Reachability of static findings, not proof of rendering failure or glyph mismatch. Reasons overlap; raw KAGE and existing mapping states are unchanged.')
    write_json(output / 'syntax-impact-summary.json', result)
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dataset')
    p.add_argument('--findings', default='data/generated/syntax-audit/syntax-issues.jsonl')
    p.add_argument('--output', default='docs')
    args=p.parse_args()
    print(audit(args.dataset,args.findings,args.output)['counts'])
