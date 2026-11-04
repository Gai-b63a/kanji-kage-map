"""Recheck inventory issue evidence against pinned sources and UCD operators.

This report closes a source-triage pass, not a glyph-equivalence review.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.inventory import ARITY, PuaTable, ranges, unicode_sets
from kanji_kage_map.sources import verified_sources, write_json


def expression_balance(expression, arities):
    """Track unfilled child slots and complete roots, using UCD-sourced arities."""
    remaining, roots = 0, 0
    for token in re.findall(r'\{[0-9]+\}|.', expression):
        if token.isspace() or token == '〾':
            continue
        if remaining == 0:
            roots += 1
            remaining = 1
        remaining -= 1
        remaining += arities.get(token, 0)
    return dict(complete_or_partial_roots=roots, unfilled_child_slots=remaining,
                one_complete_expression=roots == 1 and remaining == 0)


def review(lock, queue, output):
    sources = verified_sources(lock)
    raw_queue = Path(queue).read_bytes()
    items = json.loads(raw_queue)
    arities = {}
    for prop, arity in [('IDS_Unary_Operator', 1), ('IDS_Binary_Operator', 2), ('IDS_Trinary_Operator', 3)]:
        for lo, hi, _ in ranges(sources['prop-list'][1], prop):
            arities.update((chr(cp), arity) for cp in range(lo, hi + 1))
    if ARITY != arities:
        raise ValueError('Parser operator arities differ from pinned UCD')
    han, components, assigned = unicode_sets(sources['unicode-data'][1], sources['prop-list'][1], sources['blocks'][1])
    blocks = list(ranges(sources['blocks'][1]))
    lines = {key: text.splitlines() for key, (_, text) in sources.items() if isinstance(text, str)}
    table = PuaTable()
    table.feed(sources['pua-page'][1])
    html_rows = {row['line']: row['cells'] for row in table.rows}
    seen, records = set(), []
    for item in items:
        entity = item['entity_id']
        if entity in seen:
            raise ValueError('Duplicate review entity')
        seen.add(entity)
        evidence, leaves, balances = [], {}, {}
        for entry in item['evidence']:
            source_id, start = entry['source_id'], entry['line']
            source, _ = sources[source_id]
            local_id = entity.rsplit(':', 1)[1]
            if source_id == 'pua-page':
                cells = html_rows.get(start, [])
                payload = cells[2] if len(cells) > 2 and cells[0].rstrip('*') == local_id else ''
                location_kind = 'first_html_table_row_ids_cell'
            else:
                fields = lines[source_id][start - 1].split('\t') if 1 <= start <= len(lines[source_id]) else []
                payload = '\t'.join(fields[2:]) if fields and fields[0] == local_id else ''
                location_kind = 'text_line_ids_fields'
            if not entry['raw'] or entry['raw'] not in payload:
                raise ValueError(f'Source evidence not found: {entity}/{source_id}/{start}')
            evidence.append(dict(entry, source_sha256=source['sha256'], source_version=source['version'],
                                 source_url=source['url'], location_kind=location_kind))
            if entry['reason'] == 'unclassified_leaf':
                token = entry['raw']
                if len(token) != 1:
                    raise ValueError('Unexpected leaf token')
                cp = ord(token)
                if cp not in assigned or cp in han | components:
                    raise ValueError('Leaf classification requires new review')
                leaves[f'U+{cp:04X}'] = dict(character=token, assigned=True,
                    block=next(name for lo, hi, name in blocks if lo <= cp <= hi),
                    disposition='retain_as_other_unicode_source_component')
            if entry['reason'] in ('extra_ids_operand', 'ids_arity_mismatch', 'whitespace_in_ids'):
                balances[entry['raw']] = expression_balance(entry['raw'], arities)
        classification = item['classification']
        if classification == 'source_structure_review':
            if not balances or all(b['one_complete_expression'] for b in balances.values()):
                raise ValueError('Expected structural issue was not reproduced')
            decision = 'source_expression_not_one_complete_ids'
            next_action = 'Obtain an explicit source correction or edition-specific glyph evidence; do not infer a corrected expression.'
        elif classification == 'source_whitespace':
            if not balances or not all(b['one_complete_expression'] for b in balances.values()):
                raise ValueError('Whitespace case requires structural review')
            decision = 'source_whitespace_preserved'
            next_action = 'Retain the exact source; ignoring whitespace for inventory enumeration is not a glyph correction.'
        elif classification == 'non_han_component' and leaves:
            decision = 'assigned_unicode_leaves_outside_han_and_radical_sets'
            next_action = 'Retain each source component and its kind; source presence does not establish the PUA glyph identity.'
        else:
            raise ValueError('Unknown review classification')
        records.append(dict(entity_id=entity, source_review_status='source_audit_complete',
                            decision=decision, evidence=evidence, leaves=leaves,
                            expression_balances=balances, next_action=next_action,
                            glyph_review_status='unreviewed', selected_glyph=None))
    report = dict(format='inventory-source-review-v1', reviewer='Codex (automated source audit, policy inspected by agent)',
                  review_date='2026-11-04', queue_sha256=hashlib.sha256(raw_queue).hexdigest(),
                  source_hashes={key: record['sha256'] for key, (record, _) in sources.items()},
                  operator_arity_matches_pinned_ucd=True, entities=len(records),
                  evidence_events=sum(len(r['evidence']) for r in records),
                  decisions=dict(Counter(r['decision'] for r in records)),
                  confirmed_glyph_matches=0, records=records)
    write_json(output, report)
    print(json.dumps({key: value for key, value in report.items() if key not in ('records', 'source_hashes')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', default='sources.lock.json')
    parser.add_argument('--queue', default='docs/inventory-review-queue.json')
    parser.add_argument('--output', default='docs/inventory-source-review.json')
    args = parser.parse_args()
    review(args.lock, args.queue, args.output)
