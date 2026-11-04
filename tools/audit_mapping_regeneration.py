"""Compare every regenerated mapping field against a portable baseline."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.sources import write_json


def audit(database, mappings):
    seen, changes = set(), []
    before_counts, after_counts = Counter(), Counter()
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        snapshot = json.loads(db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0])
        baseline_ids = {r[0] for r in db.execute('SELECT entity_id FROM mappings')}
        with Path(mappings).open(encoding='utf-8') as stream:
            for line in stream:
                after = json.loads(line)
                key = after['entity_id']
                if key in seen or key not in baseline_ids:
                    raise ValueError('Duplicate or unexpected identifier: ' + key)
                seen.add(key)
                before = json.loads(db.execute('SELECT json FROM mappings WHERE entity_id=?', (key,)).fetchone()[0])
                if before['snapshot_sha256'] != snapshot or after['snapshot_sha256'] != snapshot:
                    raise ValueError('Snapshot mismatch: ' + key)
                before_counts[before['search_status']] += 1
                after_counts[after['search_status']] += 1
                fields = []
                for field in sorted(set(before) | set(after)):
                    if (field in before) != (field in after) or before.get(field) != after.get(field):
                        fields.append(dict(field=field, before_present=field in before,
                                           after_present=field in after,
                                           before=before.get(field), after=after.get(field)))
                if fields:
                    changes.append(dict(entity_id=key, fields=fields))
        if seen != baseline_ids:
            raise ValueError('Missing baseline identifiers')
    return dict(format='mapping-regeneration-audit-v1', snapshot_sha256=snapshot,
                baseline_sha256=digest_file(database), mappings_sha256=digest_file(mappings),
                entities_compared=len(seen), unchanged_entities=len(seen)-len(changes),
                baseline_search_counts=dict(sorted(before_counts.items())),
                revised_search_counts=dict(sorted(after_counts.items())),
                changes=sorted(changes, key=lambda r: r['entity_id']),
                comparison='All parsed JSON fields, including nested candidate evidence; array order is significant.',
                limitation='Mapping comparison does not itself compare portable glyph tables or certify glyph equivalence.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database')
    parser.add_argument('mappings')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit(args.database, args.mappings)
    write_json(args.output, result)
    print(result['entities_compared'], 'compared;', len(result['changes']), 'changed')
