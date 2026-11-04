from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from kanji_kage_map.overrides import record_hash, read_overrides, apply_override


class OverrideTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.review=json.loads((root/'docs/one-review-decision.jsonl').read_text(encoding='utf-8'))
        self.row=dict(format='scoped-mapping-override-v1',override_id='one-j',action='select',review=self.review,
                      review_sha256=record_hash(self.review),author=dict(name='Test',kind='ai'),created_at='2026-11-04T11:00:00Z',rationale='Explicit fixture selection',supersedes=None)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'overrides.jsonl'
        self.result=dict(entity_id=self.review['entity_id'],snapshot_sha256=self.review['snapshot_sha256'],candidates=[dict(name='u4e00',revision=46)],selected_glyph=None,
                         review_decisions=dict(history=[self.review],active_review_ids=[self.review['review_id']]))

    def load(self,rows):
        self.path.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
        return read_overrides(self.path)

    def test_scoped_application_preserves_original(self):
        before=deepcopy(self.result)
        result=apply_override(self.result,self.load([self.row]),'one-j')
        self.assertEqual(self.result,before)
        self.assertIsNone(result['selected_glyph'])
        self.assertEqual(result['scoped_selection']['selected_glyph'],'u4e00@46')

    def test_revocation_and_obsolete_selection(self):
        revoke=dict(self.row,override_id='revoke',action='revoke',supersedes='one-j')
        history=self.load([self.row,revoke])
        with self.assertRaises(ValueError):apply_override(self.result,history,'one-j')
        self.assertEqual(apply_override(self.result,history,'revoke')['scoped_selection']['status'],'revoked')
        with self.assertRaises(ValueError):self.load([self.row,revoke,dict(revoke,override_id='branch')])

    def test_changed_or_withdrawn_review_and_wrong_candidate_rejected(self):
        history=self.load([self.row])
        for mutate in [lambda r:r['review_decisions'].update(active_review_ids=[]),lambda r:r.update(candidates=[]),lambda r:r.update(snapshot_sha256='x'),lambda r:r['review_decisions']['history'][0].update(rationale='changed')]:
            result=deepcopy(self.result);mutate(result)
            with self.assertRaises(ValueError):apply_override(result,history,'one-j')
        changed=deepcopy(self.row);changed['review']['scope']['source_id']='other'
        with self.assertRaises(ValueError):self.load([changed])
