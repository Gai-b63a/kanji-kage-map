"""Offline access to existing-name research leads, never confirmed mappings."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

from .lookup import normalize_identifier


class IdsNameLeads:
    def __init__(self, supplement, manifest):
        raw = Path(supplement).read_bytes()
        self.manifest = json.loads(Path(manifest).read_text(encoding='utf-8'))
        if self.manifest['format'] != 'pua-ids-name-supplement-v1':
            raise ValueError('Unsupported supplement format')
        if hashlib.sha256(raw).hexdigest() != self.manifest['sha256']:
            raise ValueError('Supplement checksum mismatch')
        data = json.loads(gzip.decompress(raw))
        if data['snapshot_sha256'] != self.manifest['snapshot_sha256']:
            raise ValueError('Snapshot mismatch')
        self.snapshot = data['snapshot_sha256']
        self.provenance = data['provenance']
        self.records = {r['entity_id']: r for r in data['records']}
        self.bundles = {b['root']: b for b in data['bundles']}
        if len(self.records) != len(data['records']) or len(self.records) != self.manifest['entities']:
            raise ValueError('Duplicate or incomplete entity population')
        if len(self.bundles) != len(data['bundles']) or len(self.bundles) != self.manifest['unique_roots']:
            raise ValueError('Duplicate or incomplete bundle population')
        needed = set()
        for r in self.records.values():
            if not r['entity_id'].startswith('babelstone:han-pua:1.473:U+'):
                raise ValueError('Unqualified or wrong-edition entity')
            if r['review_status'] != 'unreviewed' or r['selected_glyph'] is not None or r['evidence_kind'] != 'existing_ids_name_lead_only':
                raise ValueError('Research leads cannot certify glyph identity')
            supported = {a['name'] for a in r['attempts'] if a['status'] == 'existing_name_found'}
            names = [c['name'] for c in r['candidates']]
            if set(names) != supported or len(names) != len(set(names)):
                raise ValueError('Candidates lack matching discovery evidence')
            for c in r['candidates']:
                reference = f"{c['name']}@{c['revision']}"
                needed.add(reference)
                if reference not in self.bundles:
                    raise ValueError('Candidate bundle missing')
        if needed != set(self.bundles):
            raise ValueError('Unreferenced bundles in supplement')
        for reference, b in self.bundles.items():
            if b['snapshot_sha256'] != self.snapshot or b['review_status'] != 'unreviewed':
                raise ValueError('Bundle snapshot or review state differs')
            root = b['glyphs'].get(reference)
            if root is None or reference != f"{root['name']}@{root['revision']}":
                raise ValueError('Wrong root revision')
            expected_edges = []
            for parent, glyph in b['glyphs'].items():
                for line, stroke in enumerate(glyph['data'].split('$'), 1):
                    fields = stroke.split(':')
                    if fields[0] == '99':
                        if len(fields) < 8:
                            raise ValueError('Malformed dependency')
                        child = fields[7]
                        target = b['glyphs'].get(child)
                        if target is None:
                            raise ValueError('Missing dependency')
                        if '@' in child and child != f"{target['name']}@{target['revision']}":
                            raise ValueError('Pinned dependency revision differs')
                        if child.split('@')[0] != target['name']:
                            raise ValueError('Dependency name differs')
                        expected_edges.append((parent, line, child, target['name'], target['revision']))
            actual_edges = [(e['parent'], e['line'], e['raw_reference'], e['resolved_name'], e['resolved_revision']) for e in b['dependencies']]
            if sorted(actual_edges) != sorted(expected_edges) or b['issues'] or b['dependency_status'] != 'complete':
                raise ValueError('Dependency audit differs')

    def lookup(self, identifier, glyph=None):
        identifier = normalize_identifier(identifier)
        if identifier not in self.records:
            raise ValueError('Use an adopted edition-qualified PUA identifier')
        record = self.records[identifier]
        references = [f"{c['name']}@{c['revision']}" for c in record['candidates']]
        if glyph is not None and glyph not in references:
            raise ValueError('Request an exact candidate name@revision from this entity')
        return dict(entity_id=identifier, snapshot_sha256=self.snapshot,
                    research_record=deepcopy(record), available_references=references,
                    bundle=deepcopy(self.bundles[glyph]) if glyph else None,
                    provenance=deepcopy(self.provenance), supplement_sha256=self.manifest['sha256'],
                    selected_glyph=None, review_status='unreviewed',
                    limitation='Existing-name research leads only; requested bundle is not a selected or confirmed mapping.')
