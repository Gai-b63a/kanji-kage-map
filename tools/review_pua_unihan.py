"""Join literal PUA source IDs to pinned Unihan IRG values, without glyph claims."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.pua import source_ids
from kanji_kage_map.sources import verified_sources, write_json

PROPERTIES = {f'kIRG_{region}Source' for region in ['G', 'H', 'J', 'KP', 'K', 'M', 'S', 'T', 'UK', 'U', 'V']}


def index_sources(text):
    index = defaultdict(list)
    for number, line in enumerate(text.splitlines(), 1):
        if not line or line.startswith('#'):
            continue
        cp, prop, value = line.split('\t')
        if prop not in PROPERTIES:
            continue
        if not re.fullmatch(r'U\+[0-9A-F]{4,6}', cp):
            raise ValueError('Invalid Unihan codepoint')
        for token in value.split():
            index[token].append(dict(unicode_entity_id='unicode:' + cp, property=prop,
                                     source_ref=token, line=number, raw_value=value))
    return index


def match_record(mapping, index):
    hits = [hit for ref in mapping['source_refs'] for hit in index.get(ref, [])]
    targets = sorted({hit['unicode_entity_id'] for hit in hits})
    status = ('multiple_unicode_targets' if len(targets) > 1 else 'one_unicode_target' if targets else
              'no_exact_irg_source_match' if mapping['source_refs'] else 'no_source_id_to_compare')
    return dict(entity_id=mapping['entity_id'], source_refs=mapping['source_refs'],
                source_id_match_status=status, unicode_targets=targets, evidence=hits,
                unmatched_source_refs=[r for r in mapping['source_refs'] if r not in index],
                glyph_review_status='unreviewed', selected_glyph=None,
                relation_scope='literal_source_id_match_only')


def review(lock, candidates, output):
    source, archive = verified_sources(lock)['unihan']
    member = 'Unihan_IRGSources.txt'
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        raw = z.read(member)
    text = raw.decode('utf-8')
    if f'# Unicode Version {source["version"]}' not in text.splitlines()[:12]:
        raise ValueError('Unihan header version mismatch')
    index = index_sources(text)
    inventory = {r['entity_id']: r for r in map(json.loads, Path('data/generated/inventory.jsonl').read_text(encoding='utf-8').splitlines())}
    mappings = [json.loads(line) for line in Path(candidates).read_text(encoding='utf-8').splitlines()]
    mappings = [m for m in mappings if ':han-pua:' in m['entity_id']]
    if len({m['entity_id'] for m in mappings}) != len(mappings) or {m['entity_id'] for m in mappings} != {k for k in inventory if ':han-pua:' in k}:
        raise ValueError('PUA population differs')
    discovery = json.loads(Path(candidates).with_name('pua-summary.json').read_text())
    if discovery['inventory_sha256'] != digest_file('data/generated/inventory.jsonl'):
        raise ValueError('Discovery inventory hash mismatch')
    source_rows_path = Path('data/generated/source-rows.jsonl')
    if discovery['source_rows_sha256'] != digest_file(source_rows_path):
        raise ValueError('Discovery source rows hash mismatch')
    pua_source = next(s for s in json.loads(Path('sources.lock.json').read_text())['sources'] if s['id'] == 'pua-page')
    if digest_file(pua_source['path']) != pua_source['sha256']:
        raise ValueError('PUA source hash mismatch')
    rows = [json.loads(line) for line in source_rows_path.read_text(encoding='utf-8').splitlines()]
    rows = [r for r in rows if r['source_id'] == 'pua-page']
    row_index = {r['entity_id']:r for r in rows}
    if len(row_index) != len(rows) or set(row_index) != {m['entity_id'] for m in mappings}:
        raise ValueError('PUA table population differs')
    records = [match_record(m, index) for m in sorted(mappings, key=lambda m: m['entity_id'])]
    for record in records:
        row = row_index[record['entity_id']]
        if source_ids(row['cells'][5]) != record['source_refs']:
            raise ValueError('PUA source IDs differ')
        record['pua_evidence'] = dict(line=row['line'], column='Source Refs')
        for target in record['unicode_targets']:
            if target not in inventory or inventory[target]['version'] != source['version']:
                raise ValueError('Unicode target missing or edition mismatch')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in records).encode('utf-8')
    queue = output / 'pua-unihan-source-matches.jsonl.gz'
    with queue.open('wb') as stream, gzip.GzipFile(filename='', fileobj=stream, mode='wb', mtime=0) as zipped:
        zipped.write(payload)
    group = {r['entity_id']: r for r in records}
    newly_addressable = [m['entity_id'] for m in mappings if not m['candidates'] and group[m['entity_id']]['unicode_targets']]
    summary = dict(format='pua-unihan-source-matches-v1', source=source,
                   pua_source=pua_source, source_rows_sha256=discovery['source_rows_sha256'],
                   member=member, member_sha256=hashlib.sha256(raw).hexdigest(),
                   candidates_sha256=digest_file(candidates), inventory_sha256=discovery['inventory_sha256'],
                   entities=len(records), statuses=dict(sorted(Counter(r['source_id_match_status'] for r in records).items())),
                   match_events=sum(len(r['evidence']) for r in records),
                   target_unicode_entities=len({t for r in records for t in r['unicode_targets']}),
                   previously_without_glyphwiki_candidate_with_unicode_target=len(newly_addressable),
                   examples_without_previous_candidate=newly_addressable[:10],
                   output_sha256=digest_file(queue), output_bytes=queue.stat().st_size,
                   confirmed_glyph_matches=0,
                   limitation='Exact literal matching in eleven IRG properties only. A Unicode source relationship is not confirmation of the PUA glyph, a specific regional GlyphWiki glyph, or unchanged source edition. Existing mappings are not modified.')
    write_json(output / 'pua-unihan-summary.json', summary)
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lock', default='review-unihan.lock.json')
    p.add_argument('--candidates', default='data/generated/pua-source-id-fix/pua-candidates.jsonl')
    p.add_argument('--output', default='docs')
    args = p.parse_args()
    result = review(args.lock, args.candidates, args.output)
    print(json.dumps({k:result[k] for k in ['entities','statuses','match_events','target_unicode_entities','previously_without_glyphwiki_candidate_with_unicode_target']}))
