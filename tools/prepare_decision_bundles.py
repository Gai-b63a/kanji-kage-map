"""Reconstruct active review subjects from their exact portable-dataset revisions."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.review_decisions import read_history, attach_decisions
from kanji_kage_map.release import lookup_release
from kanji_kage_map.sources import write_json


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger')
    parser.add_argument('--dataset',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    ledger=read_history(args.ledger)
    records=[]
    seen=set()
    for review in ledger['history']:
        if review['review_id'] not in ledger['active_review_ids'] or review['decision']=='withdrawn':
            continue
        key=(review['entity_id'],review['glyph_reference'])
        if key in seen:
            continue
        result=lookup_release(args.dataset,review['entity_id'],review['glyph_reference'].rsplit('@',1)[0])
        attach_decisions(result,args.ledger)
        if result['bundle']['root'] != review['glyph_reference']:
            raise ValueError('Reviewed revision is not the resolved candidate revision')
        records.append(dict(glyph=review['glyph_reference'],entity_id=review['entity_id'],bundle=result['bundle']))
        seen.add(key)
    write_json(args.output,records)
    print(len(records),'review subjects prepared')
