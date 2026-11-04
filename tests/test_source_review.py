import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('source_review', Path(__file__).resolve().parents[1] / 'tools/review_inventory_sources.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class SourceReviewTests(unittest.TestCase):
    def test_distinguishes_extra_roots_from_unfilled_children(self):
        arities = {'⿰': 2, '⿱': 2, '⿾': 1}
        extra = review.expression_balance('⿰氵丰月', arities)
        missing = review.expression_balance('⿰氵', arities)
        self.assertEqual(extra['complete_or_partial_roots'], 2)
        self.assertEqual(extra['unfilled_child_slots'], 0)
        self.assertFalse(extra['one_complete_expression'])
        self.assertEqual(missing['complete_or_partial_roots'], 1)
        self.assertEqual(missing['unfilled_child_slots'], 1)
        self.assertFalse(missing['one_complete_expression'])
        self.assertTrue(review.expression_balance('⿱口⿰⿰丶丶 口', arities)['one_complete_expression'])
        self.assertTrue(review.expression_balance('⿰{121}⿾一', arities)['one_complete_expression'])
        self.assertFalse(review.expression_balance('', arities)['one_complete_expression'])
