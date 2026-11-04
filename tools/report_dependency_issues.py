"""Trace every issue-bearing candidate to raw evidence in a portable dataset."""
import argparse
from collections import deque
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.release import lookup_release
from kanji_kage_map.sources import write_json


def shortest_path(root, target, edges):
    children = {}
    for edge in edges:
        children.setdefault(edge['parent'], []).append(edge)
    queue = deque([(root, [])])
    seen = {root}
    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        for edge in sorted(children.get(node, []), key=lambda e: (e['line'], e['target'])):
            if edge['target'] not in seen:
                seen.add(edge['target'])
                queue.append((edge['target'], path + [edge]))
    raise ValueError(f'Issue is not reachable from {root}: {target}')


def report(database):
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        meta = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
        if meta.get('format') != 'kanji-kage-map-portable-v0.1' or not meta.get('build_complete'):
            raise ValueError('Expected a completed portable dataset')
        issues = [json.loads(j) for (j,) in db.execute('SELECT json FROM issues ORDER BY reference,json')]
        affected = []
        entities = links = 0
        for entity, raw in db.execute('SELECT entity_id,json FROM mappings ORDER BY entity_id'):
            mapping = json.loads(raw)
            entities += 1
            if mapping['snapshot_sha256'] != meta['snapshot_sha256']:
                raise ValueError('Snapshot mismatch')
            for candidate in mapping['candidates']:
                links += 1
                if candidate['dependency_status'] != 'issues':
                    continue
                bundle = lookup_release(database, entity, candidate['name'])['bundle']
                evidence = []
                reachable_reasons = set()
                nodes = {bundle['root']} | {e['target'] for e in bundle['dependencies']}
                for issue in issues:
                    ref = issue['reference']
                    if ref not in nodes:
                        continue
                    path = shortest_path(bundle['root'], ref, bundle['dependencies'])
                    row = db.execute('SELECT json FROM glyphs WHERE reference=?', (ref,)).fetchone()
                    glyph = json.loads(row[0]) if row else None
                    if issue['reason'] == 'missing_reference' and glyph is not None:
                        raise ValueError('Recorded missing glyph exists')
                    if 'line' in issue:
                        if glyph is None or glyph['data'].split('$')[issue['line'] - 1] != issue['raw']:
                            raise ValueError('Issue raw line does not match the preserved glyph')
                    reachable_reasons.add(issue['reason'])
                    evidence.append(dict(issue=issue, shortest_dependency_path=path, glyph=glyph))
                if reachable_reasons != set(candidate['dependency_issues']):
                    raise ValueError('Recorded candidate reasons differ from traceable local issues')
                affected.append(dict(entity_id=entity, candidate=bundle['root'], evidence=evidence,
                                     dependency_status='issues', review_status=mapping['review_status']))
        covered = {json.dumps(e['issue'], sort_keys=True) for a in affected for e in a['evidence']}
        if covered != {json.dumps(i, sort_keys=True) for i in issues}:
            raise ValueError('Some local issues have no affected candidate trace')
        return dict(format='dependency-issue-traces-v1', snapshot_sha256=meta['snapshot_sha256'],
                    scope=dict(entities_scanned=entities, candidate_links_scanned=links,
                               local_issue_events=len(issues), affected_candidate_links=len(affected),
                               affected_entities=len({a['entity_id'] for a in affected})),
                    limitation='Traces the recorded dependency audit findings; not a full syntax or glyph-equivalence review.',
                    affected=affected)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database')
    parser.add_argument('--output', default='docs/dependency-issue-traces.json')
    args = parser.parse_args()
    result = report(args.database)
    write_json(args.output, result)
    print(json.dumps(result['scope']))
