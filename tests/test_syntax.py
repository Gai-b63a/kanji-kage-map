import unittest
from kanji_kage_map.syntax import inspect_kage, inspect_line, inspect_bundle


class SyntaxTests(unittest.TestCase):
    def test_bundle_checks_dependency_without_double_counting_aliases(self):
        glyph = dict(name='bad', revision=1, data='1:0:0:0:0:bad:1')
        bundle = dict(glyphs={'bad': glyph, 'bad@1': glyph}, review_status='unreviewed')
        result = inspect_bundle(bundle)
        self.assertEqual(result['glyphs_checked'], 1)
        self.assertEqual(result['findings'][0]['reference'], 'bad@1')
        self.assertEqual(result['status'], 'findings')
        self.assertEqual(bundle['review_status'], 'unreviewed')

    def reasons(self, raw):
        return {item['reason'] for item in inspect_line(raw)}

    def test_required_coordinates_and_finite_values(self):
        self.assertEqual(inspect_line('1:0:2:32:31:176:31'), [])
        self.assertIn('missing_numeric_field', self.reasons('6:0:0:1:2:3:4:5:6'))
        self.assertIn('nonfinite_field', self.reasons('1:0:2:0:0:Infinity:1'))
        self.assertIn('nonnumeric_field', self.reasons('1:0:2:0:0:oops:1'))
        self.assertEqual(inspect_line('1:0:2:-3.5:0:203:1'), [])

    def test_noops_are_distinct_from_bad_tags_and_comments(self):
        self.assertEqual(inspect_line('0:0:comment text'), [])
        self.assertIn('engine_noop_command', self.reasons('9:0:0'))
        self.assertIn('engine_unsupported_command', self.reasons('8:0:0'))
        self.assertIn('invalid_command_tag', self.reasons(':0:0'))
        self.assertEqual(inspect_line('101:0:2:1:2:3:4'), [])
        self.assertIn('missing_numeric_field', self.reasons('12:0:0:1:2:3:4:5:6'))

    def test_reference_optional_stretch_and_transform(self):
        self.assertEqual(inspect_line('99:0:0:0:0:200:200:u4e00@1'), [])
        self.assertEqual(inspect_line('99:200:0:0:0:200:200:u4e00@1'), [])
        self.assertIn('blank_numeric_zero_coercion', self.reasons('99::0:0:0:200:200:u4e00'))
        self.assertIn('missing_numeric_field', self.reasons('99:150:0:0:0:200:200:u4e00'))
        self.assertEqual(inspect_line('99:150:0:0:0:200:200:u4e00:0:0:0'), [])
        self.assertEqual(inspect_line('0:99:1:0:0:200:200'), [])
        self.assertIn('unsupported_rotation_mode', self.reasons('0:99:5:0:0:200:200'))
        self.assertEqual(inspect_kage('')[0]['reason'], 'empty_kage')
        self.assertEqual(inspect_kage('0:0:comment$s')[0]['line'], 2)
