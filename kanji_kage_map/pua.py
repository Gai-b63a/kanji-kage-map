"""Source-ID discovery for PUA; a matching name never confirms equivalence."""
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re

from .glyphwiki import open_index, digest_file
from .sources import write_json


def source_ids(cell):
    # Use only the explicit Source Refs column, not narrative mentions or IDS.
    return sorted(set(re.findall(r'\b[A-Z][A-Z0-9]*[-_][A-Z0-9]+(?:-[A-Z0-9]+)*\b', cell)))


def discover_pua(database, source_rows, inventory, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    evidence = {}
    with Path(source_rows).open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['source_id'] == 'pua-page':
                evidence[row['entity_id']] = row
    counts = Counter()
    with closing(open_index(database)) as db, Path(inventory).open(encoding='utf-8') as stream, \
            (output / 'pua-candidates.jsonl').open('w', encoding='utf-8', newline='\n') as destination:
        snapshot = db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0]
        for line in stream:
            entity = json.loads(line)
            if entity['provider'] != 'BabelStone':
                continue
            row = evidence.get(entity['entity_id'])
            refs = source_ids(row['cells'][5]) if row and len(row['cells']) >= 6 else []
            candidates = []
            for ref in refs:
                glyph = db.execute('SELECT name,revision,related,line FROM latest WHERE name=?', (ref.lower(),)).fetchone()
                if glyph:
                    candidates.append(dict(name=glyph['name'], revision=glyph['revision'], related=glyph['related'],
                        source_line=glyph['line'], rules=['source_id_name'],
                        evidence=dict(source_id='pua-page', line=row['line'], source_ref=ref,
                                      column='Source Refs', links=row['links']),
                        revision_status='resolved' if glyph['revision'] is not None else 'unresolved'))
            status = 'candidates_found' if candidates else 'no_candidate_in_searched_rules' if refs else 'requires_source_evidence'
            counts[status] += 1
            counts['entities'] += 1
            counts['candidate_links'] += len(candidates)
            result = dict(entity_id=entity['entity_id'], snapshot_sha256=snapshot, source_refs=refs,
                          search_status=status, mapping_status='candidate' if candidates else 'unreviewed',
                          review_status='unreviewed', selected_glyph=None, candidates=candidates)
            destination.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + '\n')
    summary = dict(snapshot_sha256=snapshot, source_rows_sha256=digest_file(source_rows),
                   inventory_sha256=digest_file(inventory), counts=dict(counts), confirmed_matches=0,
                   limitation='Exact source-ID/name discovery only; no PUA-codepoint equality or visual identity claim.')
    write_json(output / 'pua-summary.json', summary)
    print(json.dumps(summary, indent=2))
