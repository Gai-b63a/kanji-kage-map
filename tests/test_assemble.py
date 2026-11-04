import json
from pathlib import Path
import tempfile
import unittest

from kanji_kage_map.assemble import assemble
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.inventory import jsonl
from kanji_kage_map.sources import write_json


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / '.cache/tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.temp.name)
        (self.root / 'pua-research').mkdir()
        self.snapshot = 'a' * 64
        empty = dict(entity_id='babelstone:han-pua:1.473:U+E080', snapshot_sha256=self.snapshot,
                     candidates=[], search_status='requires_source_evidence', review_status='unreviewed',
                     mapping_status='unreviewed', selected_glyph=None)
        jsonl(self.root / 'candidates.jsonl', [empty])
        pua = dict(empty, candidates=[dict(name='uk-1', revision=2)], search_status='candidates_found', mapping_status='candidate')
        jsonl(self.root / 'pua-research/pua-candidates.jsonl', [pua])
        for source, audit, rows in [('candidates.jsonl', 'dependency-audit', []),
                                   ('pua-research/pua-candidates.jsonl', 'pua-research/dependency-audit',
                                    [dict(reference='uk-1@2', reachable_issues=[])])]:
            directory = self.root / audit
            directory.mkdir()
            jsonl(directory / 'candidate-dependencies.jsonl', rows)
            write_json(directory / 'checksums.json', {'candidate-dependencies.jsonl':digest_file(directory / 'candidate-dependencies.jsonl')})
            write_json(directory / 'dependency-summary.json', dict(snapshot_sha256=self.snapshot,
                       candidates_sha256=digest_file(self.root / source)))

    def tearDown(self):
        self.temp.cleanup()

    def test_source_candidate_replaces_only_matching_inventory_id(self):
        output = self.root / 'mappings.jsonl'
        assemble(self.root, output)
        row = json.loads(output.read_text())
        self.assertEqual(row['candidates'][0]['dependency_status'], 'complete')
        self.assertIsNone(row['selected_glyph'])
        self.assertEqual(row['glyph_difference_status'], 'unreviewed')

    def test_modified_audit_status_is_rejected(self):
        (self.root / 'pua-research/dependency-audit/candidate-dependencies.jsonl').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            assemble(self.root, self.root / 'mappings.jsonl')

    def test_changed_candidates_are_not_treated_as_audited(self):
        with (self.root / 'candidates.jsonl').open('a') as stream:
            stream.write('\n')
        with self.assertRaisesRegex(ValueError, 'changed since'):
            assemble(self.root, self.root / 'mappings.jsonl')


if __name__ == '__main__':
    unittest.main()
