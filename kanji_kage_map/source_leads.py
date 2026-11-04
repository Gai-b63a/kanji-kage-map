"""Read source-ID leads without turning them into PUA glyph decisions."""
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

from .lookup import normalize_identifier
from .release import lookup_release


class SourceLeads:
    def __init__(self, dataset, matches, summary):
        self.dataset = Path(dataset)
        summary_bytes = Path(summary).read_bytes()
        self.summary = json.loads(summary_bytes)
        raw = Path(matches).read_bytes()
        if self.summary['format'] != 'pua-unihan-source-matches-v1':
            raise ValueError('Unsupported source relation format')
        if hashlib.sha256(raw).hexdigest() != self.summary['output_sha256']:
            raise ValueError('Source relation checksum mismatch')
        self.summary_sha256 = hashlib.sha256(summary_bytes).hexdigest()
        records = [json.loads(line) for line in gzip.decompress(raw).decode('utf-8').splitlines()]
        self.records = {r['entity_id']: r for r in records}
        if len(records) != len(self.records) or len(records) != self.summary['entities']:
            raise ValueError('Duplicate or incomplete source relation records')
        with closing(sqlite3.connect(self.dataset.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            metadata = {k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')}
            if metadata.get('format') != 'kanji-kage-map-portable-v0.1' or not metadata.get('build_complete'):
                raise ValueError('Not a completed portable dataset')
            if metadata['inputs']['inventory.jsonl'] != self.summary['inventory_sha256']:
                raise ValueError('Relation and dataset inventories differ')
            sources = {s['id']:s for s in metadata['sources.lock.json']['sources']}
            if sources['pua-page']['sha256'] != self.summary['pua_source']['sha256']:
                raise ValueError('Relation and dataset PUA sources differ')
            self.snapshot = metadata['snapshot_sha256']
            inventory = {k:json.loads(v) for k,v in db.execute('SELECT entity_id,json FROM inventory')}
        expected = {k for k in inventory if k.startswith('babelstone:han-pua:')}
        if set(self.records) != expected:
            raise ValueError('Relation PUA population differs from dataset')
        for record in records:
            if record['relation_scope'] != 'literal_source_id_match_only' or record['glyph_review_status'] != 'unreviewed' or record['selected_glyph'] is not None:
                raise ValueError('Source relations cannot certify glyph matches')
            targets = sorted({e['unicode_entity_id'] for e in record['evidence']})
            if targets != record['unicode_targets']:
                raise ValueError('Targets lack source-ID evidence')
            for evidence in record['evidence']:
                if evidence['property'] not in {f'kIRG_{r}Source' for r in ['G','H','J','KP','K','M','S','T','UK','U','V']}:
                    raise ValueError('Evidence is not an IRG source property')
                if evidence['source_ref'] not in record['source_refs'] or evidence['source_ref'] not in evidence['raw_value'].split():
                    raise ValueError('Source IDs are inconsistent with evidence')
            for target in targets:
                if target not in inventory or inventory[target]['version'] != self.summary['source']['version']:
                    raise ValueError('Unicode target or edition differs from dataset')

    def lookup(self, identifier, unicode_target=None, glyph=None):
        identifier = normalize_identifier(identifier)
        if identifier not in self.records:
            raise ValueError('Use an adopted, edition-qualified BabelStone PUA identifier')
        relation = self.records[identifier]
        requested = normalize_identifier(unicode_target) if unicode_target else None
        if requested is not None and requested not in relation['unicode_targets']:
            raise ValueError('Requested Unicode target is not supported by this source relation')
        if glyph is not None and requested is None:
            raise ValueError('Specify --unicode-target when requesting a glyph bundle')
        pua = lookup_release(self.dataset, identifier)
        leads = [lookup_release(self.dataset, target, glyph if target == requested else None)
                 for target in relation['unicode_targets']]
        if any(m['snapshot_sha256'] != self.snapshot for m in [pua] + leads):
            raise ValueError('Mapping and dataset snapshots differ')
        return dict(entity_id=identifier, snapshot_sha256=self.snapshot,
                    pua_mapping=pua, source_relation=relation, unicode_leads=leads,
                    provenance=dict(summary_sha256=self.summary_sha256,
                                    relations_sha256=self.summary['output_sha256'],
                                    pua_source=self.summary['pua_source'], unihan_source=self.summary['source'],
                                    unihan_member=self.summary['member'], unihan_member_sha256=self.summary['member_sha256']),
                    selected_glyph=None, glyph_review_status='unreviewed',
                    limitation='Unicode candidate bundles are research leads, not confirmed PUA glyph mappings. The original PUA mapping is unchanged; relation discovery may include documented corrections absent from that dataset.')
