"""Compare explicit numbered-component PUA claims without asserting edition identity."""
import argparse
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.inventory import Inventory, PuaTable
from kanji_kage_map.sources import verified_sources, write_json


def review(lock, output):
    sources = verified_sources(lock)
    inventory = Inventory(sources).build()
    table = PuaTable()
    table.feed(sources['pua-page'][1])
    rows = {}
    for row in table.rows:
        if row['cells'] and row['cells'][0].startswith('U+'):
            local_id = row['cells'][0].rstrip('*')
            if local_id in rows:
                raise ValueError('Duplicate PUA row')
            rows[local_id] = row
    ids_source, ids_text = sources['ids']
    ids_lines = ids_text.splitlines()
    pua_source, _ = sources['pua-page']
    counts, records = Counter(), []
    for definition in inventory.definitions:
        claim = definition['pua_codepoint_claim']
        row = rows.get(claim)
        raw_line = ids_lines[definition['line'] - 1]
        if claim is None or claim[2:] not in raw_line:
            raise ValueError('Definition lacks an explicit source PUA claim')
        original = definition['replacement']
        target = row['cells'][2] if row is not None and len(row['cells']) > 2 else None
        if row is None:
            comparison = 'claimed_codepoint_absent_from_adopted_pua_table'
        elif target == original:
            comparison = 'ids_text_identical'
        elif original == '？' and target == '':
            comparison = 'unknown_placeholder_versus_blank'
        else:
            comparison = 'ids_text_differs'
        counts[comparison] += 1
        records.append(dict(
            entity_id=definition['entity_id'],
            source_claim=dict(pua_codepoint=claim, source_version=ids_source['version'],
                              source_sha256=ids_source['sha256'], source_url=ids_source['url'],
                              line=definition['line'], target_pua_edition_specified=False),
            comparison_target=dict(entity_id=f"babelstone:han-pua:{pua_source['version']}:{claim}",
                                   source_version=pua_source['version'], source_sha256=pua_source['sha256'],
                                   source_url=pua_source['url'], line=row['line'] if row else None),
            numbered_ids=original, pua_ids=target, text_comparison=comparison,
            relation_status='explicit_codepoint_claim_target_edition_unverified',
            glyph_review_status='unreviewed', selected_glyph=None,
            next_action='Establish PUA edition continuity and compare the isolated component glyph; text equality alone is insufficient.'))
    report = dict(format='numbered-component-source-review-v1', records=records,
                  entities=len(records), comparison_counts=dict(sorted(counts.items())),
                  confirmed_glyph_matches=0,
                  scope='source-declared PUA codepoints and text comparison only; no KAGE candidate propagation')
    write_json(output, report)
    print(dict(entities=len(records), comparison_counts=report['comparison_counts']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', default='sources.lock.json')
    parser.add_argument('--output', default='docs/numbered-component-source-review.json')
    args = parser.parse_args()
    review(args.lock, args.output)
