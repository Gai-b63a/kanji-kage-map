"""Validate a review ledger and its subject bindings against a portable dataset."""
import argparse
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.release import lookup_release
from kanji_kage_map.review_decisions import read_history, attach_decisions
from kanji_kage_map.sources import write_json


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger')
    p.add_argument('--dataset',required=True)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    ledger=read_history(args.ledger)
    entities={r['entity_id'] for r in ledger['history']}
    for entity in sorted(entities):
        attach_decisions(lookup_release(args.dataset,entity),args.ledger)
    active=[r for r in ledger['history'] if r['review_id'] in ledger['active_review_ids']]
    report=dict(format='review-ledger-validation-v1',ledger_sha256=ledger['file_sha256'],
                dataset_sha256=digest_file(args.dataset),history_records=len(ledger['history']),
                active_records=len(active),entities=len(entities),
                active_decisions=dict(sorted(Counter(r['decision'] for r in active).items())),
                scope='Record contract, history, candidate membership, and snapshot only; not evidence authenticity or re-performance of visual judgments.')
    write_json(args.output,report)
    print(report)
