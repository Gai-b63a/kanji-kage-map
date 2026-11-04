"""Compare regenerated BabelStone discovery to an immutable portable baseline."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.pua import source_ids
from kanji_kage_map.sources import write_json


def audit(database, candidates, source_rows):
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        snapshot = json.loads(db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0])
        baseline = {key: json.loads(raw) for key, raw in db.execute(
            "SELECT entity_id,json FROM mappings WHERE entity_id LIKE 'babelstone:%'")}
    revised = {}
    for line in Path(candidates).read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if row['entity_id'] in revised or row['snapshot_sha256'] != snapshot:
            raise ValueError('Duplicate ID or snapshot mismatch')
        revised[row['entity_id']] = row
    if set(baseline) != set(revised):
        raise ValueError('Identifier population changed')
    def project(row):
        return dict(source_refs=row['source_refs'], search_status=row['search_status'],
                    mapping_status=row['mapping_status'], review_status=row['review_status'],
                    selected_glyph=row['selected_glyph'],
                    candidate_references=sorted(f"{c['name']}@{c['revision']}" for c in row['candidates']))
    changes = [dict(entity_id=key, before=project(baseline[key]), after=project(revised[key]))
               for key in sorted(baseline) if project(baseline[key]) != project(revised[key])]
    rows = [json.loads(line) for line in Path(source_rows).read_text(encoding='utf-8').splitlines()]
    rows = [r for r in rows if r['source_id'] == 'pua-page']
    unparsed = [dict(entity_id=r['entity_id'], line=r['line'], raw_source_refs=r['cells'][5])
                for r in rows if r['cells'][5].strip() and not source_ids(r['cells'][5])]
    for change in changes:
        source = next((r for r in rows if r['entity_id'] == change['entity_id']), None)
        if source:
            change['source'] = dict(source_id=source['source_id'], line=source['line'],
                                    raw_source_refs=source['cells'][5])
    return dict(format='pua-discovery-change-audit-v1', snapshot_sha256=snapshot,
                inputs={str(p): digest_file(p) for p in [database, candidates, source_rows]},
                entities_compared=len(baseline), pua_source_rows=len(rows),
                nonempty_source_cells=sum(bool(r['cells'][5].strip()) for r in rows),
                nonempty_source_cells_without_recognized_id=unparsed,
                baseline_search_counts=dict(sorted(Counter(r['search_status'] for r in baseline.values()).items())),
                revised_search_counts=dict(sorted(Counter(r['search_status'] for r in revised.values()).items())),
                changes=changes,
                limitation='Projection compares discovery IDs and states, not all candidate evidence fields or glyph equivalence; one recognized ID does not prove a cell was completely parsed.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('database')
    p.add_argument('candidates')
    p.add_argument('source_rows')
    p.add_argument('--output', default='docs/pua-discovery-change.json')
    args = p.parse_args()
    result = audit(args.database, args.candidates, args.source_rows)
    write_json(args.output, result)
    print(len(result['changes']), 'changed identifiers')
