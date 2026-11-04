import unittest

from tools.review_pua_unihan import index_sources, match_record


class PuaUnihanTests(unittest.TestCase):
    def test_literal_namespace_and_property_scope(self):
        index = index_sources('# comment\nU+4E00\tkIRG_UKSource\tUK-00001\n'
                              'U+4E01\tkIRG_SSource\tSAT-00001\n'
                              'U+4E02\tkDefinition\tUSAT00001\n')
        result = match_record(dict(entity_id='pua', source_refs=['USAT00001', 'UK-00001']), index)
        self.assertEqual(result['unicode_targets'], ['unicode:U+4E00'])
        self.assertEqual(result['unmatched_source_refs'], ['USAT00001'])
        self.assertEqual(result['evidence'][0]['line'], 2)
        self.assertEqual(result['glyph_review_status'], 'unreviewed')
        self.assertIsNone(result['selected_glyph'])

    def test_ambiguity_is_retained_and_distinct_from_no_evidence(self):
        index = index_sources('U+4E00\tkIRG_GSource\tG-1 G-2\nU+4E01\tkIRG_GSource\tG-1\n')
        result = match_record(dict(entity_id='pua', source_refs=['G-1']), index)
        self.assertEqual(result['source_id_match_status'], 'multiple_unicode_targets')
        self.assertEqual(len(result['unicode_targets']), 2)
        self.assertEqual(match_record(dict(entity_id='pua', source_refs=[]), index)['source_id_match_status'], 'no_source_id_to_compare')
        self.assertEqual(match_record(dict(entity_id='pua', source_refs=['G-3']), index)['source_id_match_status'], 'no_exact_irg_source_match')
