import unittest
from tools.research_pua_ids_names import name_for


class ExistingIdsNameTests(unittest.TestCase):
    def test_nested_and_supplementary(self):
        self.assertEqual(name_for('⿰飠⿱𠂉盧', set('飠𠂉盧')),
                         ('u2ff0-u98e0-u2ff1-u20089-u76e7', None))

    def test_pua_must_not_be_cross_provider_identity(self):
        self.assertEqual(name_for('⿰飠\ue87d', set('飠\ue87d'))[1], 'edition_scoped_pua_leaf')

    def test_incomplete_extra_and_unknown_are_not_search_names(self):
        for expression, reason in [('⿰飠', 'incomplete_expression'),
                                   ('⿰飠盧盧', 'extra_operand'),
                                   ('⿰飠？', 'unsupported_leaf_or_notation'),
                                   ('⿰飠{1}', 'unsupported_leaf_or_notation'),
                                   ('盧', 'not_composite')]:
            with self.subTest(expression=expression):
                self.assertEqual(name_for(expression, set('飠盧'))[1], reason)
