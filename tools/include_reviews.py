"""Build a new portable database containing review history."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.reviewed_release import include_reviews
from kanji_kage_map.sources import write_json

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dataset')
    p.add_argument('ledgers',nargs='+')
    p.add_argument('--output',required=True)
    p.add_argument('--report',required=True)
    args=p.parse_args()
    report=include_reviews(args.dataset,args.ledgers,args.output)
    write_json(args.report,report)
    print(report)
