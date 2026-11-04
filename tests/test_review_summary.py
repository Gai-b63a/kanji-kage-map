from copy import deepcopy
import json
from pathlib import Path
import unittest

from kanji_kage_map.review_decisions import parse_history
from tools.summarize_reviews import summarize


class ReviewSummaryTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.one=json.loads((root/'docs/one-review-decision.jsonl').read_text(encoding='utf-8'))
        self.sea=[json.loads(line) for line in (root/'docs/sea-review-decisions.jsonl').read_text(encoding='utf-8').splitlines()]

    def report(self,rows):
        return summarize(parse_history((''.join(json.dumps(r)+'\n' for r in rows)).encode()),109556)

    def test_contexts_and_entities_are_not_record_counts(self):
        report=self.report([self.one]+self.sea)
        self.assertEqual(report['active_nonwithdrawn_records'],3)
        self.assertEqual(report['entities_with_active_scoped_records'],2)
        self.assertEqual(report['entities_without_active_scoped_records'],109554)
        self.assertEqual(len(report['active_contexts']),3)

    def test_withdrawal_removes_current_judgment_not_history(self):
        withdrawal=deepcopy(self.one)
        withdrawal.update(review_id='withdraw-one',supersedes=self.one['review_id'],decision='withdrawn')
        report=self.report([self.one,withdrawal])
        self.assertEqual(report['history_records'],2)
        self.assertEqual(report['withdrawn_current_records'],1)
        self.assertEqual(report['active_nonwithdrawn_records'],0)

    def test_multiple_equivalent_candidates_are_flagged_without_selection(self):
        other=deepcopy(self.one);other.update(review_id='another-glyph',glyph_reference='u4e00-j@30')
        report=self.report([self.one,other])
        self.assertEqual(len(report['multiple_equivalent_candidates_same_context']),1)
        other['scope']['source_id']='different-source'
        self.assertEqual(self.report([self.one,other])['multiple_equivalent_candidates_same_context'],[])
