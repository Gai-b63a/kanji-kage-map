import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from kanji_kage_map.release import build_release, lookup_release
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.inventory import jsonl
from kanji_kage_map.sources import write_json


class PortableReleaseTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / '.cache/tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.temp.name)
        self.snapshot = 'a' * 64
        rows = [dict(entity_id='unicode:U+4E00',snapshot_sha256=self.snapshot,candidates=[dict(name='u4e00',revision=2)],selected_glyph=None),
                dict(entity_id='babelstone:han-pua:1.473:U+E080',snapshot_sha256=self.snapshot,candidates=[],selected_glyph=None)]
        jsonl(self.root / 'inventory.jsonl', [dict(entity_id=r['entity_id']) for r in rows])
        jsonl(self.root / 'mappings.jsonl', rows)
        write_json(self.root / 'mappings.summary.json',dict(snapshot_sha256=self.snapshot,output_sha256=digest_file(self.root / 'mappings.jsonl')))
        for name in ('sources.lock.json','glyphwiki.lock.json'):
            write_json(self.root / name, {})
        glyphs = [dict(reference='u4e00@2',name='u4e00',revision=2,data='99:0:0:0:0:200:200:part'),
                  dict(reference='part@1',name='part',revision=1,data='1:0:0:20:100:180:100')]
        for prefix in ('dependency-audit','pua-research/dependency-audit'):
            folder = self.root / prefix
            folder.mkdir(parents=True)
            jsonl(folder / 'glyphs.jsonl',glyphs)
            jsonl(folder / 'dependencies.jsonl',[dict(parent='u4e00@2',line=1,raw_reference='part',target='part@1')])
            jsonl(folder / 'dependency-issues.jsonl',[])
            write_json(folder / 'checksums.json',{name:digest_file(folder / name) for name in ('glyphs.jsonl','dependencies.jsonl','dependency-issues.jsonl')})
            write_json(folder / 'dependency-summary.json',dict(snapshot_sha256=self.snapshot))

    def tearDown(self):
        self.temp.cleanup()

    def test_portable_lookup_requires_no_upstream_database(self):
        output = self.root / 'release.sqlite3'
        with contextlib.redirect_stdout(io.StringIO()):
            build_release(self.root, output, self.root)
        result = lookup_release(output,'一','u4e00')
        self.assertEqual(result['bundle']['root'],'u4e00@2')
        self.assertEqual(result['bundle']['glyphs']['part']['revision'],1)
        self.assertEqual(result['bundle']['dependency_status'],'complete')
        self.assertIsNone(result['selected_glyph'])
        self.assertEqual(lookup_release(output,'babelstone:han-pua:1.473:U+E080')['candidates'],[])
        with self.assertRaises(ValueError): lookup_release(output,'U+E080')

    def test_repeated_builds_have_identical_database_and_gzip_bytes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            for name in ('a','b'):
                build_release(self.root,self.root / (name+'.sqlite3'),self.root)
        for suffix in ('.sqlite3','.sqlite3.gz'):
            self.assertEqual(digest_file(self.root / ('a'+suffix)),digest_file(self.root / ('b'+suffix)))

    def test_modified_input_rejected_before_database_creation(self):
        with (self.root / 'mappings.jsonl').open('a') as f:f.write('\n')
        with self.assertRaisesRegex(ValueError,'checksum mismatch'):
            build_release(self.root,self.root/'bad.sqlite3',self.root)
        self.assertFalse((self.root/'bad.sqlite3').exists())


if __name__ == '__main__':
    unittest.main()
