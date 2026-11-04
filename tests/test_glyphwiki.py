import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tarfile
import tempfile
import unittest

from kanji_kage_map.glyphwiki import parse_row, index_dump, digest_file, resolve_bundle, collect_candidates
from kanji_kage_map.sources import write_json
from kanji_kage_map.audit import audit_dependencies
from kanji_kage_map.lookup import lookup


class GlyphWikiTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.cache' / 'tests'
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.root = Path(self.temp.name)
        self.db = self.root / 'glyphs.sqlite3'

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        newest = 'name | related | data\n---+---+---\n' + '\n'.join([
            'u4e00 | u4e00 | 99:0:0:0:0:200:200:part@1',
            'part | u4e00 | 1:0:0:0:0:200:200',
            'u4e00-j | u4e00 | 99:0:0:0:0:200:200:part',
            'uf900 | u4e00 | 99:0:0:0:0:200:200:part@99',
            'loop | u3013 | 99:0:0:0:0:200:200:loop',
            'mismatch | u3013 | 1:0:0:1:1:2:2',
            'deleted | u3013 | -'])
        history = '\n'.join([
            'u4e00\\@1 | u4e00 | 99:0:0:0:0:200:200:part@1',
            'u4e00\\@2 | u4e00 | 99:0:0:0:0:200:200:part@1',
            'part\\@1 | u4e00 | 1:0:0:0:0:100:100',
            'part\\@2 | u4e00 | 1:0:0:0:0:200:200',
            'u4e00-j\\@1 | u4e00 | 99:0:0:0:0:200:200:part',
            'uf900\\@1 | u4e00 | 99:0:0:0:0:200:200:part@99',
            'loop\\@1 | u3013 | 99:0:0:0:0:200:200:loop',
            'mismatch\\@1 | u3013 | 1:0:0:1:1:2:2',
            'mismatch\\@2 | u3013 | 1:0:0:2:2:3:3',
            'deleted\\@1 | u3013 | -'])
        archive = self.root / 'dump.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            for name, text in [('dump_newest_only.txt', newest), ('dump_all_versions.txt', history),
                               ('LICENSE.txt', 'fixture license'), ('README_en.txt', 'fixture'), ('README_ja.txt', 'fixture')]:
                data = text.encode()
                member = tarfile.TarInfo(name)
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
        lock = self.root / 'lock.json'
        write_json(lock, dict(path='dump.tar.gz', bytes=archive.stat().st_size, sha256=digest_file(archive)))
        with contextlib.redirect_stdout(io.StringIO()):
            index_dump(lock, self.db, self.root / 'reports')

    def test_preserve_related_and_non_numeric_data(self):
        self.assertEqual(parse_row(b'abc\\@17 | u4e00 | -\n', True), ('abc', 17, 'u4e00', '-'))
        with self.assertRaises(ValueError):
            parse_row(b'abc | u4e00 | 1:0:0', True)

    def test_max_revision_content_check_and_strict_dependencies(self):
        self.build()
        result = resolve_bundle(self.db, 'u4e00')
        self.assertEqual(result['glyphs']['u4e00']['revision'], 2)
        self.assertEqual(result['glyphs']['part@1']['data'], '1:0:0:0:0:100:100')
        self.assertEqual(result['dependency_status'], 'complete')
        result = resolve_bundle(self.db, 'uf900')
        self.assertEqual(result['issues'][0]['reason'], 'missing_reference')
        self.assertNotIn('part@99', result['glyphs'])
        result = resolve_bundle(self.db, 'u4e00-j')
        self.assertEqual(result['dependencies'][0]['resolved_revision'], 2)
        self.assertIn('revision_unresolved', {x['reason'] for x in resolve_bundle(self.db, 'mismatch')['issues']})

    def test_cycles_and_invalid_data_reported(self):
        self.build()
        self.assertIn('cycle', {x['reason'] for x in resolve_bundle(self.db, 'loop')['issues']})
        self.assertIn('invalid_kage_command', {x['reason'] for x in resolve_bundle(self.db, 'deleted')['issues']})

    def test_candidate_rules_do_not_map_pua_or_claim_matches(self):
        self.build()
        inventory = self.root / 'inventory.jsonl'
        entries = [dict(entity_id='unicode:U+4E00', provider='Unicode', local_id='U+4E00'),
                   dict(entity_id='babelstone:han-pua:1.473:U+E080', provider='BabelStone', local_id='U+E080')]
        inventory.write_text('\n'.join(json.dumps(e) for e in entries), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            collect_candidates(self.db, inventory, self.root / 'candidates')
        rows = [json.loads(x) for x in (self.root / 'candidates/candidates.jsonl').read_text().splitlines()]
        self.assertEqual({c['name'] for c in rows[0]['candidates']}, {'u4e00', 'u4e00-j', 'part', 'uf900'})
        self.assertIsNone(rows[0]['selected_glyph'])
        self.assertEqual(rows[1]['search_status'], 'requires_source_evidence')
        self.assertEqual(rows[1]['candidates'], [])
        result = lookup('一', self.root / 'candidates/candidates.jsonl', self.db, 'u4e00')
        self.assertEqual(result['bundle']['root'], 'u4e00@2')
        self.assertEqual(result['review_status'], 'unreviewed')
        self.assertIsNone(result['selected_glyph'])
        with self.assertRaisesRegex(ValueError, 'not among'):
            lookup('一', self.root / 'candidates/candidates.jsonl', self.db, 'loop')

    def test_full_dependency_audit_tracks_pinned_missing_and_cycle(self):
        self.build()
        with sqlite3.connect(self.db) as db:
            snapshot = db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0]
        db.close()
        candidates = self.root / 'candidates.jsonl'
        candidates.write_text(json.dumps(dict(snapshot_sha256=snapshot, candidates=[
            dict(name='u4e00', revision=2), dict(name='uf900', revision=1), dict(name='loop', revision=1)])) + '\n')
        with contextlib.redirect_stdout(io.StringIO()):
            summary = audit_dependencies(self.db, candidates, self.root / 'audit')
        self.assertEqual(summary['candidate_root_status']['complete'], 1)
        self.assertEqual(summary['candidate_root_status']['missing_reference'], 1)
        self.assertEqual(summary['candidate_root_status']['cycle_reachable'], 1)
        glyphs = [json.loads(x) for x in (self.root / 'audit/glyphs.jsonl').read_text().splitlines()]
        self.assertEqual(next(r for r in glyphs if r['reference']=='part@1')['data'], '1:0:0:0:0:100:100')


if __name__ == '__main__':
    unittest.main()
