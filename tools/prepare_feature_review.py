"""Prepare exact candidate bundles for reproducing a scoped visual review."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.release import lookup_release
from kanji_kage_map.feature_reviews import attach_feature_reviews
from kanji_kage_map.sources import write_json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review')
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    review = json.loads(Path(args.review).read_text(encoding='utf-8'))
    seen, records = set(), []
    for item in review['observations']:
        key = item['entity_id'], item['glyph_reference']
        if key in seen:
            continue
        seen.add(key)
        result = lookup_release(args.dataset, key[0], key[1].rsplit('@', 1)[0])
        attach_feature_reviews(result, args.review)
        if result['bundle']['root'] != key[1]:
            raise ValueError('Candidate revision changed')
        records.append(dict(entity_id=key[0], glyph=key[1], bundle=result['bundle']))
    write_json(args.output, records)
