import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tools.audit_mapping_regeneration import audit


class MappingRegenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / 'base.sqlite3'
        self.mappings = Path(self.tmp.name) / 'mappings.jsonl'
        self.row = dict(entity_id='unicode:4E00', snapshot_sha256='snapshot',
                        search_status='candidates', candidates=[dict(evidence=['original'])])
        with closing(sqlite3.connect(self.database)) as db:
            db.executescript('CREATE TABLE metadata(key TEXT,value TEXT); CREATE TABLE mappings(entity_id TEXT PRIMARY KEY,json TEXT);')
            db.execute('INSERT INTO metadata VALUES (?,?)', ('snapshot_sha256', json.dumps('snapshot')))
            db.execute('INSERT INTO mappings VALUES (?,?)', (self.row['entity_id'], json.dumps(self.row)))
            db.commit()

    def write(self, rows):
        self.mappings.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')

    def test_nested_evidence_change_and_added_null_are_not_hidden(self):
        revised = dict(self.row, candidates=[dict(evidence=['changed'])], extra=None)
        self.write([revised])
        result = audit(self.database, self.mappings)
        self.assertEqual(result['entities_compared'], 1)
        fields = result['changes'][0]['fields']
        self.assertEqual([f['field'] for f in fields], ['candidates', 'extra'])
        self.assertFalse(fields[1]['before_present'])
        self.assertTrue(fields[1]['after_present'])

    def test_population_and_snapshot_fail_closed(self):
        for rows in ([], [self.row, self.row], [dict(self.row, entity_id='unexpected')],
                     [dict(self.row, snapshot_sha256='other')]):
            with self.subTest(rows=rows):
                self.write(rows)
                with self.assertRaises(ValueError):
                    audit(self.database, self.mappings)

    def test_identical_mapping(self):
        self.write([self.row])
        result = audit(self.database, self.mappings)
        self.assertEqual(result['unchanged_entities'], 1)
        self.assertEqual(result['changes'], [])
