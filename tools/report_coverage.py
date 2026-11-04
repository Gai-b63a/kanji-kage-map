"""Report population-specific coverage from a portable database."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.coverage import coverage
from kanji_kage_map.sources import write_json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database')
    parser.add_argument('--output', default='docs/coverage.json')
    args = parser.parse_args()
    report = coverage(args.database)
    write_json(args.output, report)
    for label, group in report['groups'].items():
        c = group['counts']
        print(label, c['entities'], 'entities;', c['candidates_found'], 'with candidates;',
              c['confirmed_glyph_matches'], 'confirmed')
