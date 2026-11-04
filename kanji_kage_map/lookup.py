"""User-facing lookup that keeps discovery separate from confirmation."""
import json
from pathlib import Path
import re

from .glyphwiki import resolve_bundle
from .inventory import is_pua
from .syntax import inspect_bundle


def normalize_identifier(value):
    if value.startswith('babelstone:'):
        if not re.fullmatch(r'babelstone:(han-pua:[^:]+:U\+[0-9A-F]{4,6}|ids-component:[^:]+:\{\d+\})', value):
            raise ValueError('BabelStone identifiers require namespace, version, and local ID')
        if ':han-pua:' in value and not is_pua(int(value.rsplit('U+', 1)[1], 16)):
            raise ValueError('BabelStone Han PUA local ID must be a private-use scalar')
        return value
    if len(value) == 1:
        cp = ord(value)
    else:
        match = re.fullmatch(r'(?:unicode:)?U\+([0-9a-fA-F]{4,6})', value)
        if not match:
            raise ValueError('Use one Unicode character, U+hex, or a versioned BabelStone identifier')
        cp = int(match[1], 16)
    if cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF:
        raise ValueError('Not a Unicode scalar value')
    if is_pua(cp):
        raise ValueError('PUA requires provider and version: babelstone:han-pua:1.473:U+E080')
    return f'unicode:U+{cp:04X}'


def lookup(value, candidates, database, glyph=None):
    identifier = normalize_identifier(value)
    record = None
    with Path(candidates).open(encoding='utf-8') as stream:
        for line in stream:
            item = json.loads(line)
            if item['entity_id'] == identifier:
                record = item
                break
    if record is None:
        raise ValueError('Identifier is not in the adopted inventory')
    result = dict(record)
    result['bundle'] = None
    result['bundle_status'] = 'choose_candidate' if record['candidates'] else 'no_evidence_backed_candidate'
    if glyph is not None:
        candidate = next((c for c in record['candidates'] if c['name'] == glyph), None)
        if candidate is None:
            raise ValueError('Requested glyph is not among the recorded candidates')
        if candidate['revision'] is None:
            raise ValueError('Candidate revision is unresolved')
        bundle = resolve_bundle(database, f"{glyph}@{candidate['revision']}")
        if bundle['snapshot_sha256'] != record['snapshot_sha256']:
            raise ValueError('Candidate/index snapshot mismatch')
        result['bundle'] = bundle
        result['static_syntax_audit'] = inspect_bundle(bundle)
        result['bundle_status'] = 'requested_candidate'
        # User selection is not a review decision or a claim of equivalence.
        result['selected_glyph'] = None
    return result
