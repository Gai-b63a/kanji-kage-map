import unittest
from kanji_kage_map.lookup import normalize_identifier
from kanji_kage_map.pua import source_ids


class LookupTests(unittest.TestCase):
    def test_unicode_forms(self):
        for value in ('海', 'U+6d77', 'unicode:U+6D77'):
            self.assertEqual(normalize_identifier(value), 'unicode:U+6D77')
        self.assertEqual(normalize_identifier('𠀀'), 'unicode:U+20000')

    def test_pua_requires_version(self):
        for value in ('\ue080', 'U+E080', 'unicode:U+E080', 'U+F0000', 'babelstone:U+E080',
                      'babelstone:han-pua:1.473:U+4E00', 'babelstone:han-pua:1.473:U+FFFFFF'):
            with self.assertRaises(ValueError):
                normalize_identifier(value)
        key = 'babelstone:han-pua:1.473:U+E080'
        self.assertEqual(normalize_identifier(key), key)

    def test_invalid_unicode(self):
        for value in ('U+110000', 'U+D800', '海龍'):
            with self.assertRaises(ValueError):
                normalize_identifier(value)

    def test_source_ids_preserve_distinct_namespaces(self):
        self.assertEqual(source_ids('UK-20863\nTC-3E52\nUK-20863'), ['TC-3E52', 'UK-20863'])
        self.assertEqual(source_ids('G_CY0651'), ['G_CY0651'])
        self.assertEqual(source_ids('USAT05567 USAT-05567 USAT05567'), ['USAT-05567', 'USAT05567'])
        self.assertEqual(source_ids('XUSAT05567 USAT055678 unrelated12345'), [])


if __name__ == '__main__':
    unittest.main()
