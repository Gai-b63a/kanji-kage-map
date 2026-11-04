from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from tools.verify_corrected_release import compare_records, ENTITY, MAPPING_SHA


class CorrectedReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)/'base.sqlite3';self.corrected=Path(self.tmp.name)/'corrected.sqlite3'
        with closing(sqlite3.connect(self.base)) as db:
            db.executescript('CREATE TABLE inventory(entity_id TEXT,json TEXT); CREATE TABLE mappings(entity_id TEXT,json TEXT); CREATE TABLE glyphs(reference TEXT,json TEXT); CREATE TABLE dependencies(parent TEXT,line INTEGER,raw_reference TEXT,target TEXT); CREATE TABLE issues(reference TEXT,json TEXT); CREATE TABLE metadata(key TEXT,value TEXT);')
            row=dict(entity_id=ENTITY,source_refs=[],search_status='requires_source_evidence',candidates=[],selected_glyph=None)
            db.execute('INSERT INTO mappings VALUES (?,?)',(ENTITY,json.dumps(row)))
            db.execute('INSERT INTO glyphs VALUES (?,?)',('test@1','original KAGE'))
            db.execute('INSERT INTO metadata VALUES (?,?)',('inputs',json.dumps({'mappings.jsonl':'old','inventory.jsonl':'unchanged'})))
            db.commit()
        shutil.copyfile(self.base,self.corrected)
        self.change('UPDATE mappings SET json=?',(json.dumps(dict(row,source_refs=['USAT05567'],search_status='no_candidate_in_searched_rules')),))
        self.change('UPDATE metadata SET value=?',(json.dumps({'mappings.jsonl':MAPPING_SHA,'inventory.jsonl':'unchanged'}),))

    def change(self,query,params=()):
        with closing(sqlite3.connect(self.corrected)) as db:
            db.execute(query,params);db.commit()

    def test_exact_correction(self):
        self.assertEqual(compare_records(self.base,self.corrected)['changed_mapping_ids'],[ENTITY])

    def test_unrelated_kage_change_rejected(self):
        self.change("UPDATE glyphs SET json='modified KAGE'")
        with self.assertRaises(ValueError): compare_records(self.base,self.corrected)

    def test_extra_metadata_rejected(self):
        self.change('INSERT INTO metadata VALUES (?,?)',('unverified','true'))
        with self.assertRaises(ValueError): compare_records(self.base,self.corrected)

    def test_missing_mapping_rejected(self):
        self.change('DELETE FROM mappings')
        with self.assertRaises(ValueError): compare_records(self.base,self.corrected)

    def test_unexpected_selection_rejected(self):
        with closing(sqlite3.connect(self.corrected)) as db:
            row=json.loads(db.execute('SELECT json FROM mappings').fetchone()[0])
        row['selected_glyph']='invented'
        self.change('UPDATE mappings SET json=?',(json.dumps(row),))
        with self.assertRaises(ValueError): compare_records(self.base,self.corrected)
