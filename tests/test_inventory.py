import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from kanji_kage_map.inventory import Inventory, PuaTable, unicode_sets, classify_issues, jsonl
from kanji_kage_map.sources import verified_sources, write_json, restore, acquire


def fixture(ids='', pua='', html=''):
    unicode_data = '\n'.join([
        '2E80;CJK RADICAL REPEAT', '4E00;<CJK Ideograph, First>', '4E02;<CJK Ideograph, Last>',
        'F900;CJK COMPATIBILITY IDEOGRAPH-F900', '20000;CJK UNIFIED IDEOGRAPH-20000',
        '2630;TRIGRAM FOR HEAVEN'])
    values = {'ids': ids, 'ids-pua': pua, 'pua-page': html, 'unicode-data': unicode_data,
              'prop-list': '4E00..4E02 ; Unified_Ideograph\n20000 ; Unified_Ideograph',
              'blocks': '2E80..2EFF ; CJK Radicals Supplement\nF900..FAFF ; CJK Compatibility Ideographs'}
    return {key: ({'version': '2025-06-27' if key == 'ids' else '1.473' if key in ('ids-pua', 'pua-page') else '18.0.0'}, value)
            for key, value in values.items()}


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(__file__).resolve().parents[1] / '.cache' / 'tests'
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def test_ucd_ranges_compatibility_and_unassigned_holes(self):
        src = fixture()
        han, components, assigned = unicode_sets(src['unicode-data'][1], src['prop-list'][1], src['blocks'][1])
        self.assertEqual(han, {0x4E00, 0x4E01, 0x4E02, 0xF900, 0x20000})
        self.assertEqual(components, {0x2E80})
        self.assertNotIn(0xF901, assigned)

    def test_multiple_variants_supplementary_unknown_and_regions(self):
        inv = Inventory(fixture('U+4E00\t一\t^⿰𠀀？$(G[B])\t^一$(J)')).build()
        self.assertIn('unicode:U+20000', inv.entities)
        unknown = [o for o in inv.occurrences if o['role'] == 'unknown_component']
        self.assertEqual(len(unknown), 1)
        self.assertIsNone(unknown[0]['entity_id'])
        self.assertEqual(unknown[0]['label'], '(G[B])')
        self.assertNotIn('unicode:U+FF1F', inv.entities)
        self.assertFalse(inv.issues)

    def test_empty_pua_and_html_versioned_identity(self):
        html = '<table><tr><td>U+E080*</td><td>\ue080</td><td></td><td></td><td></td><td></td></tr></table>'
        inv = Inventory(fixture(pua='U+E080\t\ue080', html=html)).build()
        key = 'babelstone:han-pua:1.473:U+E080'
        self.assertEqual(inv.entities[key]['memberships'], {'ids-pua_heading', 'pua-page_heading'})
        self.assertEqual(inv.line_counts['ids-pua']['empty_ids'], 1)
        self.assertNotIn('unicode:U+E080', inv.entities)

    def test_numbered_definition_is_not_assumed_pua_equivalence(self):
        inv = Inventory(fixture('#\t{1}\ttop of 一 (E080 \ue080)\t一\nU+4E00\t一\t^⿰{1}{1}$')).build()
        key = 'babelstone:ids-component:2025-06-27:{1}'
        self.assertIn(key, inv.entities)
        self.assertEqual(len([o for o in inv.occurrences if o['entity_id'] == key]), 3)
        self.assertEqual(inv.definitions[0]['pua_link_status'], 'edition_alignment_unverified')
        self.assertNotIn('babelstone:han-pua:1.473:U+E080', inv.entities)

    def test_symbols_alternatives_and_spaces_preserved(self):
        inv = Inventory(fixture(pua='U+E080\t\ue080\t^⿰一 ☰ or ⿱一一$')).build()
        self.assertIn('unicode:U+2630', inv.entities)
        self.assertFalse(any(i['reason'] == 'ids_arity_mismatch' for i in inv.issues))
        self.assertTrue(any(i['reason'] == 'whitespace_in_ids' for i in inv.issues))

    def test_bad_rows_and_duplicate_headings_not_silent(self):
        inv = Inventory(fixture('bad row\nU+4E00\t丁\t^⿰一$\nU+4E00\t一\tbad')).build()
        reasons = {i['reason'] for i in inv.issues}
        self.assertTrue({'unrecognized_line', 'duplicate_heading', 'codepoint_character_mismatch',
                         'ids_arity_mismatch', 'unparsed_ids_field'} <= reasons)
        self.assertEqual(len(inv.rows), 2)

    def test_html_ignores_history_and_preserves_links(self):
        parser = PuaTable()
        parser.feed('<table><tr><td>U+E080</td><td><a href="source">x&amp;y</a></td></tr></table>'
                    '<table><tr><td>U+E081</td></tr></table>')
        self.assertEqual(len(parser.rows), 1)
        self.assertEqual(parser.rows[0]['cells'][1], 'x&y')
        self.assertEqual(parser.rows[0]['links'], ['source'])

    def test_snapshot_bom_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            root = Path(temp)
            data = b'\xef\xbb\xbfhello\r\n'
            (root / 'raw').write_bytes(data)
            record = dict(id='sample', status='acquired', path='raw', bytes=len(data),
                          sha256=hashlib.sha256(data).hexdigest())
            write_json(root / 'lock.json', {'sources': [record]})
            self.assertEqual(verified_sources(root / 'lock.json')['sample'][1], 'hello\r\n')
            restore(root / 'lock.json')
            (root / 'raw').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash/size mismatch'):
                verified_sources(root / 'lock.json')
            with self.assertRaisesRegex(ValueError, 'hash/size mismatch'):
                restore(root / 'lock.json')

    def test_existing_lock_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            path = Path(temp) / 'lock.json'
            path.write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                acquire(Path(temp) / 'missing.json', path)
            self.assertEqual(path.read_text(), '{}')

    def test_single_glyphwiki_lock_restores_without_rewriting_metadata(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            root = Path(temp)
            data = b'archive bytes'
            (root / 'dump').write_bytes(data)
            lock = root / 'glyphwiki.lock.json'
            write_json(lock, dict(provider='GlyphWiki', path='dump', bytes=len(data),
                                  sha256=hashlib.sha256(data).hexdigest()))
            before = lock.read_bytes()
            restore(lock)
            self.assertEqual(lock.read_bytes(), before)
            (root / 'dump').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash/size mismatch'):
                restore(lock)

    def test_pending_source_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            lock = Path(temp) / 'lock.json'
            write_json(lock, {'sources': [dict(id='missing', status='pending')]})
            with self.assertRaisesRegex(ValueError, 'not acquired'):
                verified_sources(lock)

    def test_binary_source_is_hash_verified_without_text_decoding(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            root = Path(temp)
            data = b'\x00\xff\x80'
            (root / 'font').write_bytes(data)
            write_json(root / 'lock.json', {'sources':[dict(id='font',status='acquired',path='font',
                       bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),encoding='binary')]})
            self.assertEqual(verified_sources(root / 'lock.json')['font'][1],data)

    def test_pua_editions_are_distinct(self):
        inv = Inventory(fixture())
        first = inv.entity('\ue080', 'ids-pua', 'test')
        inv.sources['ids-pua'][0]['version'] = '1.474'
        second = inv.entity('\ue080', 'ids-pua', 'test')
        self.assertNotEqual(first, second)

    def test_latin_component_is_retained_but_flagged(self):
        inv = Inventory(fixture(pua='U+E080\t\ue080\t^⿰一K$')).build()
        self.assertIn('unicode:U+004B', inv.entities)
        self.assertTrue(any(i['reason'] == 'unclassified_leaf' and i['raw'] == 'K' for i in inv.issues))

    def test_review_queue_groups_sources_without_resolving_issues(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            root = Path(temp)
            jsonl(root / 'source-rows.jsonl', [dict(source_id=s, line=1, entity_id='pua:example') for s in ('txt', 'html')])
            jsonl(root / 'parse-issues.jsonl', [dict(source_id=s, line=1, reason='unclassified_leaf', raw='K') for s in ('txt', 'html')])
            rows = classify_issues(root, root / 'review.json')
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(rows[0]['evidence']), 2)
            self.assertEqual(rows[0]['classification'], 'non_han_component')
            self.assertEqual(rows[0]['status'], 'unreviewed')


if __name__ == '__main__':
    unittest.main()
