"""Build an exhaustive research queue; never promote discovery to glyph identity."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.pua import source_ids
from kanji_kage_map.sources import write_json

TASKS = {
    'establish_font_edition': 'Obtain a specimen of the adopted PUA edition, or document glyph continuity from edition-specific evidence.',
    'locate_missing_specimen': 'Locate the adopted-edition specimen missing from the inspected font; do not substitute a fallback glyph.',
    'compare_source_and_candidates': 'Compare the source specimen and every pinned candidate; record structural and regional differences.',
    'disambiguate_candidates': 'Keep all candidates until source evidence supports a selection or an explicit ambiguity decision.',
    'investigate_source_identifier': 'Investigate source-ID spelling and primary-source crosswalks; absence under exact-name search is not global absence.',
    'inspect_cited_source': 'Inspect the bibliography or linked source in the pinned table row and establish a citable glyph identity.',
    'locate_primary_source': 'Locate a primary specimen or definition for this edition-specific PUA identifier.',
    'establish_numbered_target_edition': 'Establish the PUA edition intended by the numbered definition before transferring any correspondence.',
    'compare_isolated_component': 'Compare the isolated component against its intended source; do not equate it with a transformed component in a full glyph.',
    'resolve_ids_text_difference': 'Investigate the two source IDS descriptions; text differences do not by themselves establish glyph differences.',
}


def classify(mapping, source_row=None, numbered=None, missing=False):
    tasks, blockers = [], []
    expected = ('candidates_found' if mapping['candidates'] else
                'no_candidate_in_searched_rules' if mapping['source_refs'] else 'requires_source_evidence')
    if mapping['search_status'] != expected or any(c['revision'] is None for c in mapping['candidates']):
        raise ValueError('Inconsistent discovery state or unpinned candidate')
    refs = sorted(f"{c['name']}@{c['revision']}" for c in mapping['candidates'])
    if numbered is not None:
        category = 'numbered_target_edition_unverified'
        blockers.append('numbered_target_edition_unspecified')
        tasks.extend(['establish_numbered_target_edition', 'compare_isolated_component'])
        if numbered['text_comparison'] == 'ids_text_differs':
            tasks.append('resolve_ids_text_difference')
    else:
        if source_row is None:
            raise ValueError('PUA entity lacks its adopted table row')
        if source_ids(source_row['cells'][5]) != mapping['source_refs']:
            raise ValueError('Source IDs differ from the pinned table row')
        blockers.append('adopted_table_and_inspected_font_editions_differ')
        tasks.append('establish_font_edition')
        if missing:
            blockers.append('specimen_absent_from_inspected_font')
            tasks.append('locate_missing_specimen')
        if refs:
            category = 'candidate_visual_review_required'
            tasks.append('compare_source_and_candidates')
            if len(refs) > 1:
                tasks.append('disambiguate_candidates')
        elif mapping['source_refs']:
            category = 'source_id_without_exact_name_candidate'
            tasks.append('investigate_source_identifier')
        elif source_row['cells'][4].strip():
            category = 'bibliographic_source_requires_investigation'
            tasks.append('inspect_cited_source')
        else:
            category = 'primary_source_requires_investigation'
            tasks.append('locate_primary_source')
    return dict(entity_id=mapping['entity_id'], search_status=mapping['search_status'],
                review_status='unreviewed', selected_glyph=None, category=category,
                candidate_references=refs, source_refs=mapping['source_refs'],
                blockers=blockers, next_actions=tasks)


def build(candidates, output):
    paths = dict(candidates=Path(candidates), inventory=Path('data/generated/inventory.jsonl'),
                 source_rows=Path('data/generated/source-rows.jsonl'), sources_lock=Path('sources.lock.json'),
                 numbered=Path('docs/numbered-component-source-review.json'),
                 font_metadata=Path('docs/pua-font-metadata.json'),
                 font_missing=Path('docs/pua-font-missing.json'), font_lock=Path('review-sources.lock.json'))
    def read(name):
        return json.loads(paths[name].read_text(encoding='utf-8'))
    def lines(name):
        return [json.loads(s) for s in paths[name].read_text(encoding='utf-8').splitlines()]
    def unique(rows):
        result = {r['entity_id']: r for r in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate identifier')
        return result
    inventory = unique([r for r in lines('inventory') if r['provider'] == 'BabelStone'])
    mappings = unique(lines('candidates'))
    numbered = unique(read('numbered')['records'])
    rows = unique([r for r in lines('source_rows') if r['source_id'] == 'pua-page'])
    missing = set(unique(read('font_missing')))
    if set(inventory) != set(mappings) or set(rows) & set(numbered) or set(rows) | set(numbered) != set(inventory):
        raise ValueError('Research inputs do not cover the same population')
    if not missing <= set(rows):
        raise ValueError('Missing-font report contains unknown identifiers')
    snapshots = {r['snapshot_sha256'] for r in mappings.values()}
    if len(snapshots) != 1:
        raise ValueError('Mixed snapshots')
    discovery = json.loads(paths['candidates'].with_name('pua-summary.json').read_text())
    for name in ['inventory', 'source_rows']:
        if digest_file(paths[name]) != discovery[name + '_sha256']:
            raise ValueError('Discovery inputs have changed')
    sources = {s['id']: s for s in read('sources_lock')['sources']}
    for name in ['ids', 'pua-page']:
        if digest_file(sources[name]['path']) != sources[name]['sha256']:
            raise ValueError('Primary source hash mismatch')
    font = read('font_lock')['sources'][0]
    meta = read('font_metadata')
    if meta['source_sha256'] != font['sha256'] or digest_file(font['path']) != font['sha256']:
        raise ValueError('Font evidence hash mismatch')
    if font['observed_font_version'] == sources['pua-page']['version'] or meta['version_matches']:
        raise ValueError('Edition mismatch policy must be re-evaluated for the new font')
    records = []
    for key in sorted(mappings):
        mapping = mappings[key]
        if mapping['review_status'] != 'unreviewed' or mapping['selected_glyph'] is not None:
            raise ValueError('Queue policy must be revised for reviewed mappings')
        if key in rows:
            row = rows[key]
            record = classify(mapping, source_row=row, missing=key in missing)
            record['evidence'] = dict(source_id='pua-page', version=inventory[key]['version'],
                                      sha256=sources['pua-page']['sha256'], line=row['line'],
                                      url=sources['pua-page']['url'])
        else:
            claim = numbered[key]
            if claim['source_claim']['source_sha256'] != sources['ids']['sha256']:
                raise ValueError('Numbered source mismatch')
            record = classify(mapping, numbered=claim)
            record['evidence'] = claim['source_claim']
            record['edition_unverified_comparison_target'] = claim['comparison_target']['entity_id']
        records.append(record)
    payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in records).encode('utf-8')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    queue = output / 'pua-review-queue.jsonl.gz'
    with queue.open('wb') as stream, gzip.GzipFile(filename='', fileobj=stream, mode='wb', mtime=0) as compressed:
        compressed.write(payload)
    summary = dict(format='pua-research-queue-v1', snapshot_sha256=next(iter(snapshots)),
                   inputs={k: dict(path=str(p), sha256=digest_file(p)) for k, p in paths.items()},
                   entities=len(records), categories=dict(sorted(Counter(r['category'] for r in records).items())),
                   blocker_counts=dict(sorted(Counter(b for r in records for b in r['blockers']).items())),
                   next_action_counts=dict(sorted(Counter(t for r in records for t in r['next_actions']).items())),
                   task_definitions=TASKS, queue_sha256=digest_file(queue), queue_bytes=queue.stat().st_size,
                   confirmed_glyph_matches=0,
                   limitation='Research triage, not completed visual review or identity confirmation. Includes the U+EADD source-ID correction; the preview.1 database is unchanged.')
    write_json(output / 'pua-review-queue-summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', default='data/generated/pua-source-id-fix/pua-candidates.jsonl')
    parser.add_argument('--output', default='docs')
    args = parser.parse_args()
    result = build(args.candidates, args.output)
    print(json.dumps(dict(entities=result['entities'], categories=result['categories'], bytes=result['queue_bytes'])))
