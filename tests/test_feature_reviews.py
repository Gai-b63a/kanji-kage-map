from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from kanji_kage_map.feature_reviews import attach_feature_reviews

ROOT = Path(__file__).resolve().parents[1]


class FeatureReviewTests(unittest.TestCase):
    def setUp(self):
        self.review = json.loads((ROOT / 'docs/unicode-sea-review.json').read_text(encoding='utf-8'))
        refs = sorted({row['glyph_reference'] for row in self.review['observations']})
        self.result = dict(entity_id='unicode:U+6D77', snapshot_sha256=self.review['snapshot_sha256'],
                           candidates=[dict(name=r.rsplit('@', 1)[0], revision=int(r.rsplit('@', 1)[1])) for r in refs],
                           bundle={'root': 'u6d77@19'}, selected_glyph=None, review_status='unreviewed')
        (ROOT / '.cache/tests').mkdir(parents=True, exist_ok=True)

    def test_agreement_and_conflict_remain_scoped_without_changing_mapping(self):
        before = deepcopy(self.result)
        result = attach_feature_reviews(self.result, ROOT / 'docs/unicode-sea-review.json')
        self.assertEqual(self.result, before)
        self.assertEqual(result['review_status'], 'unreviewed')
        self.assertIsNone(result['selected_glyph'])
        rows = result['feature_reviews']['observations']
        self.assertEqual({r['result'] for r in rows}, {'feature_agreement', 'feature_conflict'})
        self.assertEqual(len(rows), 2)

    def test_wrong_snapshot_revision_and_unjustified_full_match_are_rejected(self):
        variants = []
        changed = deepcopy(self.review); changed['snapshot_sha256'] = 'other'; variants.append(changed)
        changed = deepcopy(self.review); changed['observations'][0]['glyph_reference'] = 'u6d77@20'; variants.append(changed)
        changed = deepcopy(self.review); changed['full_glyph_match_status'] = 'matched'; variants.append(changed)
        changed = deepcopy(self.review); changed['observations'][0]['result'] = 'feature_conflict'; variants.append(changed)
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache/tests') as temp:
            path = Path(temp) / 'review.json'
            for review in variants:
                path.write_text(json.dumps(review), encoding='utf-8')
                with self.assertRaises(ValueError):
                    attach_feature_reviews(self.result, path)
