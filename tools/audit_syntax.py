"""Audit every stored glyph in a portable database without modifying raw data."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.syntax import inspect_kage
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.sources import write_json


def audit(database, output):
    database, output = Path(database), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    issues = output / 'syntax-issues.jsonl'
    counts, glyph_count, affected, lines = Counter(), 0, 0, 0
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db, \
            issues.open('w', encoding='utf-8', newline='\n') as stream:
        snapshot = json.loads(db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0])
        for reference, encoded in db.execute('SELECT reference,json FROM glyphs ORDER BY reference'):
            record = json.loads(encoded)
            if record['snapshot_sha256'] != snapshot:
                raise ValueError('Glyph snapshot mismatch')
            glyph_count += 1
            lines += len(record['data'].split('$')) if record['data'] else 0
            findings = inspect_kage(record['data'])
            if findings:
                affected += 1
                counts.update(finding['reason'] for finding in findings)
                stream.write(json.dumps(dict(reference=reference, snapshot_sha256=snapshot,
                                             findings=findings), ensure_ascii=False, sort_keys=True) + '\n')
            if glyph_count % 200000 == 0:
                print(f'{glyph_count} glyphs checked', flush=True)
    report = dict(format='kage-static-audit-v1', engine='@kurgm/kage-engine@0.7.0',
                  database_sha256=digest_file(database), snapshot_sha256=snapshot,
                  glyphs_checked=glyph_count, lines_checked=lines,
                  glyphs_with_findings=affected, finding_counts=dict(sorted(counts.items())),
                  issues_sha256=digest_file(issues),
                  checker_sha256=digest_file(Path(__file__).resolve().parents[1] / 'kanji_kage_map/syntax.py'),
                  scope='direct stored lines; required numeric inputs and engine dispatch only',
                  exclusions=['dependency propagation', 'head/tail combination semantics',
                              'geometry after component transforms', 'glyph equivalence',
                              'unused trailing fields and comment payloads'])
    write_json(output / 'syntax-summary.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('--output', type=Path, default=Path('data/generated/syntax-audit'))
    args = parser.parse_args()
    audit(args.database, args.output)
