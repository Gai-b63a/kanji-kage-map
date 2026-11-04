from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from kanji_kage_map.ids_name_leads import IdsNameLeads


class IdsNameLeadTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1]/'.cache/tests'
        parent.mkdir(parents=True,exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.temp.name)
        self.entity = 'babelstone:han-pua:1.473:U+E87D'
        self.reference = 'u2ff0-u98e0-u76e7@2'
        name = self.reference.split('@')[0]
        self.data = dict(snapshot_sha256='snapshot',provenance={},records=[dict(
            entity_id=self.entity,review_status='unreviewed',selected_glyph=None,
            evidence_kind='existing_ids_name_lead_only',
            attempts=[dict(name=name,status='existing_name_found')],
            candidates=[dict(name=name,revision=2)])],bundles=[dict(
            root=self.reference,snapshot_sha256='snapshot',review_status='unreviewed',
            glyphs={self.reference:dict(name=name,revision=2,data='99:0:0:0:0:200:200:part@1'),
                    'part@1':dict(name='part',revision=1,data='1:0:0:0:0:200:200')},
            dependencies=[dict(parent=self.reference,line=1,raw_reference='part@1',resolved_name='part',resolved_revision=1)],
            issues=[],dependency_status='complete')])

    def tearDown(self):
        self.temp.cleanup()

    def reader(self, data=None):
        raw = gzip.compress(json.dumps(data or self.data).encode(),mtime=0)
        archive = self.root/'supplement.gz'
        manifest = self.root/'manifest.json'
        archive.write_bytes(raw)
        manifest.write_text(json.dumps(dict(format='pua-ids-name-supplement-v1',
            sha256=hashlib.sha256(raw).hexdigest(),snapshot_sha256='snapshot',entities=1,unique_roots=1)))
        return IdsNameLeads(archive,manifest)

    def test_explicit_bundle_without_selection_or_alias_mutation(self):
        reader = self.reader()
        self.assertIsNone(reader.lookup(self.entity)['bundle'])
        r = reader.lookup(self.entity,self.reference)
        self.assertEqual(r['bundle']['root'],self.reference)
        self.assertIsNone(r['selected_glyph'])
        r['bundle']['glyphs'].clear()
        self.assertEqual(len(reader.lookup(self.entity,self.reference)['bundle']['glyphs']),2)

    def test_wrong_entity_revision_and_unqualified_pua_rejected(self):
        reader = self.reader()
        for identifier, glyph in [('U+E87D',None),(self.entity,self.reference.replace('@2','@1')),
                                  (self.entity,self.reference.split('@')[0])]:
            with self.assertRaises(ValueError):
                reader.lookup(identifier,glyph)

    def test_corrupt_file_and_broken_dependency_rejected(self):
        self.reader()
        (self.root/'supplement.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'checksum'):
            IdsNameLeads(self.root/'supplement.gz',self.root/'manifest.json')
        for mutate in [lambda d:d['bundles'][0]['glyphs'].pop('part@1'),
                       lambda d:d['bundles'][0]['glyphs']['part@1'].update(revision=2),
                       lambda d:d['records'][0].update(selected_glyph=self.reference),
                       lambda d:d['records'][0].update(attempts=[]),
                       lambda d:d['bundles'][0].update(dependencies=[])]:
            data = deepcopy(self.data)
            mutate(data)
            with self.assertRaises(ValueError):
                self.reader(data)
