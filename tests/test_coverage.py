from copy import deepcopy
import unittest

from kanji_kage_map.coverage import summarize


class CoverageTests(unittest.TestCase):
    def rows(self):
        inventory = dict(entity_id='one', kind='han', provider='Unicode', version='18.0.0',
                         memberships=['unicode_han', 'ids_heading', 'ids_heading'])
        mapping = dict(entity_id='one', snapshot_sha256='s', review_status='unreviewed',
                       selected_glyph=None, search_status='candidates_found',
                       candidates=[dict(dependency_status='complete'), dict(dependency_status='issues')])
        other = dict(entity_id='two', kind='pua', provider='BabelStone', version='1.473', memberships=['pua-page_heading'])
        unresolved = dict(mapping, entity_id='two', search_status='requires_source_evidence', candidates=[])
        return [(inventory, mapping), (other, unresolved)]

    def test_overlapping_sets_do_not_inflate_total_and_no_candidates_is_not_success(self):
        groups = summarize(self.rows(), 's')['groups']
        self.assertEqual(groups['all']['counts']['entities'], 2)
        self.assertEqual(groups['membership:ids_heading']['counts']['entities'], 1)
        self.assertEqual(groups['all']['rates']['candidate_presence']['fraction'], .5)
        self.assertEqual(groups['all']['rates']['confirmed_glyph_match']['fraction'], 0)
        self.assertEqual(groups['all']['rates']['dependency_complete_candidate_links']['fraction'], .5)
        self.assertIsNone(groups['kind:pua']['rates']['dependency_complete_candidate_links']['fraction'])
        self.assertEqual(groups['all']['counts']['entities_with_dependency_issue_candidate'], 1)

    def test_refuses_inconsistent_or_new_contract_data(self):
        for key, value in [('review_status', 'matched'), ('selected_glyph', 'one@1'),
                           ('snapshot_sha256', 'other'), ('search_status', 'requires_source_evidence')]:
            rows = deepcopy(self.rows())
            rows[0][1][key] = value
            with self.assertRaises(ValueError):
                summarize(rows, 's')
        with self.assertRaises(ValueError):
            summarize(self.rows() * 2, 's')
        with self.assertRaises(ValueError):
            summarize([], 's')
