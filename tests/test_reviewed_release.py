import json
from pathlib import Path
import sqlite3
import unittest

from tests import test_source_leads as fixtures
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.release import lookup_release
from kanji_kage_map.reviewed_release import include_reviews


class ReviewedReleaseTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.SourceLeadTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root,self.db=self.fixture.root,self.fixture.db
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE metadata SET value=? WHERE key='snapshot_sha256'",(json.dumps('a'*64),))
            for key,raw in db.execute('SELECT entity_id,json FROM mappings').fetchall():
                row=json.loads(raw);row['snapshot_sha256']='a'*64
                db.execute('UPDATE mappings SET json=? WHERE entity_id=?',(json.dumps(row),key))
        db.close()
        self.row=json.loads((Path(__file__).resolve().parents[1]/'docs/one-review-decision.jsonl').read_text())
        self.row.update(snapshot_sha256='a'*64,glyph_reference='u4e00@2')

    def ledger(self,row,name='ledger'):
        path=self.root/(name+'.jsonl');path.write_text(json.dumps(row)+'\n');return path

    def test_embedding_round_trip_parent_unchanged_and_append_withdrawal(self):
        before=digest_file(self.db)
        output=self.root/'reviewed.sqlite3'
        report=include_reviews(self.db,[self.ledger(self.row)],output)
        self.assertEqual(digest_file(self.db),before)
        self.assertEqual(report['active_decisions'],{'equivalent':1})
        for glyph in [None,'u4e00']:
            result=lookup_release(output,'U+4E00',glyph)
            self.assertEqual(result['review_decisions']['history'][0]['decision'],'equivalent')
            self.assertIsNone(result['selected_glyph'])
        self.row.update(review_id='withdrawal',supersedes=self.row['review_id'],decision='withdrawn')
        newer=self.root/'withdrawn.sqlite3'
        report=include_reviews(output,[self.ledger(self.row,'withdrawal')],newer)
        self.assertEqual(report['history_records'],2)
        self.assertEqual(report['active_decisions'],{'withdrawn':1})
        self.assertEqual(lookup_release(newer,'U+4E00')['review_decisions']['active_review_ids'],['withdrawal'])

    def test_rejects_overwrite_and_wrong_binding_before_creating_output(self):
        with self.assertRaises(ValueError):include_reviews(self.db,[self.ledger(self.row)],self.db)
        self.row['glyph_reference']='u4e00@99'
        output=self.root/'bad.sqlite3'
        with self.assertRaises(ValueError):include_reviews(self.db,[self.ledger(self.row)],output)
        self.assertFalse(output.exists())
        self.assertFalse(output.with_name(output.name+'.partial').exists())
