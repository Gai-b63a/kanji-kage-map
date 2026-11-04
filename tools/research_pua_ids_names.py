"""Look up existing IDS-shaped names; never synthesize KAGE or assert identity."""
import argparse
from collections import Counter
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import open_index
from kanji_kage_map.inventory import ARITY, is_pua
from kanji_kage_map.sources import write_json


def name_for(expression, allowed_leaves):
    if not expression or expression[0] not in ARITY:
        return None, 'not_composite'
    pending = 1
    for token in expression:
        if pending == 0:
            return None, 'extra_operand'
        pending -= 1
        if token in ARITY:
            pending += ARITY[token]
        elif is_pua(ord(token)):
            return None, 'edition_scoped_pua_leaf'
        elif token not in allowed_leaves:
            return None, 'unsupported_leaf_or_notation'
    if pending:
        return None, 'incomplete_expression'
    return '-'.join(f'u{ord(token):04x}' for token in expression), None


def run(database, inventory, source, output):
    inventory_bytes = Path(inventory).read_bytes()
    entities = [json.loads(line) for line in inventory_bytes.decode('utf-8').splitlines()]
    pua = {r['entity_id']: r for r in entities if r['kind'] == 'pua'}
    allowed = {r['character'] for r in entities if r['provider'] == 'Unicode' and r['unicode_assigned']}
    raw = Path(source).read_bytes()
    expected = '9b083f81125cdfa8384a8b8df4ff2a706c018fc6c91185792060d3e873a9df72'
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('IDS_PUA source differs from adopted version')
    source_rows = {}
    for line, text in enumerate(raw.decode('utf-8-sig').splitlines(), 1):
        if not text or text.startswith('#'):
            continue
        fields = text.split('\t')
        entity_id = 'babelstone:han-pua:1.473:' + fields[0]
        if entity_id not in pua or entity_id in source_rows:
            raise ValueError('Unexpected or duplicate PUA heading')
        source_rows[entity_id] = (line, fields[2:])
    rows = []
    counts = Counter()
    with closing(open_index(database)) as db:
        snapshot = db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0]
        if snapshot != 'fd3aebc0a3d3d6bdb7c6498e9f2a65f3abe316c23e59ed4a1dd73abd30fa2b72':
            raise ValueError('GlyphWiki snapshot differs')
        for entity_id in sorted(pua):
            line, fields = source_rows.get(entity_id, (None, []))
            attempts, candidates = [], {}
            for field in fields:
                match = re.fullmatch(r'\^(.*?)\$(?:\([^)]*\))?', field)
                if not match:
                    attempts.append(dict(raw=field, status='unsupported_field_notation'))
                    continue
                for expression in match[1].split(' or '):
                    name, reason = name_for(expression, allowed)
                    attempt = dict(expression=expression, name=name)
                    if reason:
                        attempt['status'] = reason
                    else:
                        glyph = db.execute('SELECT name,revision,related,line FROM latest WHERE name=?', (name,)).fetchone()
                        attempt['status'] = 'existing_name_found' if glyph else 'name_not_found'
                        if glyph:
                            candidates[name] = dict(glyph)
                    attempts.append(attempt)
            status = 'leads_found' if candidates else 'searched_no_name_found' if any(a.get('name') for a in attempts) else 'not_searchable_by_this_rule'
            counts[status] += 1
            counts['entities'] += 1
            counts['candidate_links'] += len(candidates)
            rows.append(dict(entity_id=entity_id, source_line=line, attempts=attempts,
                             candidates=list(candidates.values()), status=status,
                             evidence_kind='existing_ids_name_lead_only', review_status='unreviewed', selected_glyph=None))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in rows).encode()
    compressed = gzip.compress(payload, mtime=0)
    (output/'pua-ids-name-leads.jsonl.gz').write_bytes(compressed)
    summary = dict(format='pua-existing-ids-name-leads-v1', snapshot_sha256=snapshot,
                   source_sha256=expected, inventory_sha256=hashlib.sha256(inventory_bytes).hexdigest(),
                   counts=dict(counts), source_heading_count=len(source_rows),
                   output_sha256=hashlib.sha256(compressed).hexdigest(),
                   attempt_status_counts=dict(Counter(a['status'] for r in rows for a in r['attempts'])),
                   limitations=['Exact existing name lookup only; no suffix or indirect-reference search.',
                                'PUA leaves and unsupported notation are explicitly excluded.',
                                'No generated KAGE, identity judgment, or published mapping change.'])
    write_json(output/'pua-ids-name-leads-summary.json', summary)
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    p.add_argument('--inventory', default='data/generated/inventory.jsonl')
    p.add_argument('--source', default='data/raw/9b083f81125cdfa8384a8b8df4ff2a706c018fc6c91185792060d3e873a9df72/IDS_PUA.TXT')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    print(json.dumps(run(a.database, a.inventory, a.source, a.output), indent=2))
