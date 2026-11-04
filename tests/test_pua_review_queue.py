from copy import deepcopy
import unittest

from tools.build_pua_review_queue import classify, TASKS


class PuaReviewQueueTests(unittest.TestCase):
    def mapping(self, refs=None, candidates=None):
        refs, candidates = refs or [], candidates or []
        return dict(entity_id='babelstone:han-pua:1.473:U+E080', source_refs=refs,
                    candidates=candidates, search_status='candidates_found' if candidates else
                    'no_candidate_in_searched_rules' if refs else 'requires_source_evidence')

    def test_candidates_remain_unreviewed_and_missing_specimen_is_independent(self):
        m = self.mapping(['UK-1'], [dict(name='uk-1', revision=1), dict(name='uk-2', revision=2)])
        original = deepcopy(m)
        r = classify(m, dict(cells=['', '', '', '', '', 'UK-1']), missing=True)
        self.assertEqual(m, original)
        self.assertEqual(r['review_status'], 'unreviewed')
        self.assertIsNone(r['selected_glyph'])
        self.assertIn('locate_missing_specimen', r['next_actions'])
        self.assertIn('disambiguate_candidates', r['next_actions'])
        self.assertTrue(set(r['next_actions']) <= set(TASKS))

    def test_no_candidate_routes_depend_on_available_evidence(self):
        cases = [(['USAT05567'], '', 'source_id_without_exact_name_candidate'),
                 ([], 'book', 'bibliographic_source_requires_investigation'),
                 ([], '', 'primary_source_requires_investigation')]
        for refs, bibliography, category in cases:
            r = classify(self.mapping(refs), dict(cells=['', '', '', '', bibliography, ' '.join(refs)]))
            self.assertEqual(r['category'], category)

    def test_numbered_text_difference_does_not_transfer_pua_candidates(self):
        r = classify(self.mapping(), numbered=dict(text_comparison='ids_text_differs'))
        self.assertEqual(r['candidate_references'], [])
        self.assertIn('resolve_ids_text_difference', r['next_actions'])
        self.assertIn('establish_numbered_target_edition', r['next_actions'])

    def test_rejects_contradictory_inputs(self):
        row = dict(cells=['', '', '', '', '', 'USAT05567'])
        with self.assertRaises(ValueError):
            classify(self.mapping(), row)
        mapping = self.mapping(['USAT05567'])
        mapping['search_status'] = 'candidates_found'
        with self.assertRaises(ValueError):
            classify(mapping, row)
