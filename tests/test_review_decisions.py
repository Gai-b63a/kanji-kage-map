from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from kanji_kage_map.review_decisions import validate, read_history, attach_decisions


class ReviewDecisionTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.records=[json.loads(l) for l in (root/'docs/sea-review-decisions.jsonl').read_text(encoding='utf-8').splitlines()]
        cache=root/'.cache/tests'; cache.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=cache)
        self.path=Path(self.temp.name)/'reviews.jsonl'

    def tearDown(self):
        self.temp.cleanup()

    def write(self,rows):
        self.path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        return self.path

    def test_scoped_rejection_and_inconclusive_do_not_select_or_rewrite_mapping(self):
        record=self.records[0]
        result=dict(entity_id=record['entity_id'],snapshot_sha256=record['snapshot_sha256'],
                    candidates=[dict(name='u6d77',revision=19)],review_status='unreviewed',selected_glyph=None,bundle=None)
        original=deepcopy(result)
        attached=attach_decisions(result,self.write(self.records))
        self.assertEqual(result,original)
        self.assertEqual(len(attached['review_decisions']['history']),2)
        self.assertIsNone(attached['selected_glyph'])
        for change in [dict(snapshot_sha256='a'*64),dict(candidates=[dict(name='u6d77',revision=20)])]:
            with self.assertRaises(ValueError):
                attach_decisions(dict(result,**change),self.path)

    def test_acceptance_requires_all_aspects_and_verified_edition(self):
        row=deepcopy(self.records[1]);row['decision']='equivalent'
        with self.assertRaises(ValueError): validate(row)
        for observation in row['observations']: observation['result']='agreement'
        validate(row)
        row['source']['edition_alignment']='unverified'
        with self.assertRaises(ValueError): validate(row)
        row=deepcopy(self.records[1]);row['scope']['kind']='feature';row['decision']='equivalent'
        with self.assertRaises(ValueError): validate(row)

    def test_history_withdrawal_and_no_branching(self):
        first=deepcopy(self.records[0]);second=deepcopy(first)
        second.update(review_id='withdrawal',supersedes=first['review_id'],decision='withdrawn')
        ledger=read_history(self.write([first,second]))
        self.assertEqual(ledger['active_review_ids'],['withdrawal'])
        self.assertEqual(len(ledger['history']),2)
        branch=deepcopy(second);branch['review_id']='branch'
        for rows in [[second,first],[first,first],[first,second,branch]]:
            with self.assertRaises(ValueError):read_history(self.write(rows))
        second['scope']['source_id']='unrelated'
        with self.assertRaises(ValueError):read_history(self.write([first,second]))

    def test_requires_provenance_timestamp_rationale_and_difference(self):
        changes=[lambda r:r.update(rationale=''),lambda r:r.update(evidence=[]),
                 lambda r:r.update(reviewed_at='2026-11-04T09:00:00'),
                 lambda r:r['source'].update(sha256='wrong'),
                 lambda r:r['observations'][-1].update(result='agreement')]
        for mutate in changes:
            row=deepcopy(self.records[0]);mutate(row)
            with self.assertRaises(ValueError):validate(row)
