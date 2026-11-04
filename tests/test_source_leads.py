from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from kanji_kage_map.source_leads import SourceLeads


class SourceLeadTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / '.cache/tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.temp.name)
        self.db = self.root / 'data.sqlite3'
        self.matches = self.root / 'matches.gz'
        self.summary_path = self.root / 'summary.json'
        self.pua = 'babelstone:han-pua:1.473:U+E080'
        self.target = 'unicode:U+4E00'
        self.summary = dict(format='pua-unihan-source-matches-v1', entities=1,
                            inventory_sha256='inventory', pua_source=dict(sha256='pua'),
                            source=dict(version='18.0.0'), member='Unihan_IRGSources.txt', member_sha256='member')
        self.record = dict(entity_id=self.pua, source_refs=['UK-00001'],
                           unicode_targets=[self.target], glyph_review_status='unreviewed', selected_glyph=None,
                           relation_scope='literal_source_id_match_only',
                           evidence=[dict(unicode_entity_id=self.target, property='kIRG_UKSource',
                                          source_ref='UK-00001', raw_value='UK-00001', line=1)])
        metadata = dict(format='kanji-kage-map-portable-v0.1', build_complete=True,
                        inputs={'inventory.jsonl':'inventory'}, snapshot_sha256='snapshot')
        metadata['sources.lock.json'] = dict(sources=[dict(id='pua-page', sha256='pua')])
        with sqlite3.connect(self.db) as db:
            db.executescript('CREATE TABLE metadata(key,value); CREATE TABLE inventory(entity_id,json);'
                             'CREATE TABLE mappings(entity_id,json); CREATE TABLE glyphs(reference,json);'
                             'CREATE TABLE dependencies(parent,line,raw_reference,target); CREATE TABLE issues(reference,json);')
            db.executemany('INSERT INTO metadata VALUES (?,?)', [(k,json.dumps(v)) for k,v in metadata.items()])
            for key, version in [(self.pua,'1.473'),(self.target,'18.0.0')]:
                db.execute('INSERT INTO inventory VALUES (?,?)',(key,json.dumps(dict(version=version))))
                mapping = dict(entity_id=key, snapshot_sha256='snapshot', selected_glyph=None, review_status='unreviewed',
                               candidates=[] if key == self.pua else [dict(name='u4e00',revision=2)])
                db.execute('INSERT INTO mappings VALUES (?,?)',(key,json.dumps(mapping)))
            db.execute('INSERT INTO glyphs VALUES (?,?)',('u4e00@2',json.dumps(dict(reference='u4e00@2',name='u4e00',revision=2,data='1:0:0:20:100:180:100'))))
        db.close()

    def tearDown(self):
        self.temp.cleanup()

    def reader(self, record=None, summary=None):
        raw = gzip.compress((json.dumps(record or self.record)+'\n').encode())
        self.matches.write_bytes(raw)
        s = deepcopy(summary or self.summary)
        s['output_sha256'] = hashlib.sha256(raw).hexdigest()
        self.summary_path.write_text(json.dumps(s))
        return SourceLeads(self.db, self.matches, self.summary_path)

    def test_bundle_is_attached_to_unicode_lead_without_pua_promotion(self):
        result = self.reader().lookup(self.pua, 'U+4E00', 'u4e00')
        self.assertEqual(result['unicode_leads'][0]['bundle']['root'], 'u4e00@2')
        self.assertEqual(result['pua_mapping']['candidates'], [])
        self.assertIsNone(result['pua_mapping']['bundle'])
        self.assertIsNone(result['selected_glyph'])
        self.assertEqual(result['glyph_review_status'], 'unreviewed')
        self.assertIsNone(self.reader().lookup(self.pua)['unicode_leads'][0]['bundle'])

    def test_rejects_unsupported_selection_and_unqualified_pua(self):
        reader = self.reader()
        for args in [('U+E080',), (self.pua,'U+4E01'), (self.pua,None,'u4e00'), (self.pua,'U+4E00','other')]:
            with self.assertRaises(ValueError):
                reader.lookup(*args)

    def test_rejects_hash_edition_population_and_unjustified_claims(self):
        self.reader()
        self.matches.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            SourceLeads(self.db, self.matches, self.summary_path)
        for mutate in [lambda s:s.update(inventory_sha256='wrong'),
                       lambda s:s['source'].update(version='17.0.0'), lambda s:s.update(entities=2)]:
            summary = deepcopy(self.summary); mutate(summary)
            with self.assertRaises(ValueError):
                self.reader(summary=summary)
        for mutate in [lambda r:r.update(glyph_review_status='matched'),
                       lambda r:r.update(unicode_targets=[]),
                       lambda r:r['evidence'][0].update(property='kDefinition'),
                       lambda r:r['evidence'][0].update(source_ref='UK-00002')]:
            record = deepcopy(self.record); mutate(record)
            with self.assertRaises(ValueError):
                self.reader(record=record)
