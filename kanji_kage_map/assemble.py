"""Join evidence and dependency results into a complete provisional mapping."""
from collections import Counter
import json
from pathlib import Path

from .glyphwiki import digest_file
from .sources import write_json


def assemble(directory, output):
    directory, output = Path(directory), Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    base = directory / 'candidates.jsonl'
    pua_file = directory / 'pua-research/pua-candidates.jsonl'
    statuses = {}
    snapshot = None
    for candidates, audit in [(base, directory / 'dependency-audit'),
                              (pua_file, directory / 'pua-research/dependency-audit')]:
        summary = json.loads((audit / 'dependency-summary.json').read_text(encoding='utf-8'))
        if digest_file(candidates) != summary['candidates_sha256']:
            raise ValueError('Candidates changed since dependency audit')
        if snapshot is not None and snapshot != summary['snapshot_sha256']:
            raise ValueError('Audit snapshot mismatch')
        snapshot = summary['snapshot_sha256']
        checksums = json.loads((audit / 'checksums.json').read_text(encoding='utf-8'))
        status_file = audit / 'candidate-dependencies.jsonl'
        if digest_file(status_file) != checksums[status_file.name]:
            raise ValueError('Dependency status checksum mismatch')
        with status_file.open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                state = tuple(row['reachable_issues'])
                if row['reference'] in statuses and statuses[row['reference']] != state:
                    raise ValueError('Conflicting dependency audits')
                statuses[row['reference']] = state
    overrides = {}
    with pua_file.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['entity_id'] in overrides:
                raise ValueError('Duplicate PUA identifier')
            overrides[row['entity_id']] = row
    counts = Counter()
    seen = set()
    partial = output.with_suffix(output.suffix + '.part')
    with base.open(encoding='utf-8') as stream, partial.open('w', encoding='utf-8', newline='\n') as destination:
        for line in stream:
            row = json.loads(line)
            key = row['entity_id']
            if key in seen:
                raise ValueError('Duplicate inventory identifier')
            seen.add(key)
            row = overrides.pop(key, row)
            if row['snapshot_sha256'] != snapshot:
                raise ValueError('Mapping snapshot mismatch')
            row['glyph_difference_status'] = 'unreviewed'
            for candidate in row['candidates']:
                ref = candidate['name'] + (f"@{candidate['revision']}" if candidate['revision'] is not None else '')
                if ref not in statuses:
                    raise ValueError(f'Candidate has not been audited: {ref}')
                reasons = statuses[ref]
                candidate['dependency_status'] = 'issues' if reasons else 'complete'
                candidate['dependency_issues'] = list(reasons)
                candidate['render_status'] = 'not_run'
            counts[row['search_status']] += 1
            counts['entities'] += 1
            counts['candidate_links'] += len(row['candidates'])
            counts['candidate_links_with_dependency_issues'] += sum(c['dependency_status'] == 'issues' for c in row['candidates'])
            destination.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    if overrides:
        raise ValueError('PUA identifiers absent from base inventory')
    partial.replace(output)
    write_json(output.with_suffix('.summary.json'), dict(schema_version=1, snapshot_sha256=snapshot,
               inputs={'unicode_candidates': digest_file(base), 'pua_candidates': digest_file(pua_file)},
               output_sha256=digest_file(output), counts=dict(counts), confirmed_matches=0,
               release_status='provisional-unreviewed'))
