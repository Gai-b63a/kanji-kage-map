"""Exercise every PUA source-lead lookup and every newly reachable candidate bundle."""
import argparse
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.source_leads import SourceLeads
from kanji_kage_map.sources import write_json


def audit(dataset, matches, summary):
    reader = SourceLeads(dataset, matches, summary)
    counts, statuses = Counter(), Counter()
    roots = set()
    issues = []
    for key in sorted(reader.records):
        result = reader.lookup(key)
        counts['pua_lookups'] += 1
        assert result['selected_glyph'] is None and result['glyph_review_status'] == 'unreviewed'
        for lead in result['unicode_leads']:
            counts['unicode_lead_links'] += 1
            counts['unicode_candidate_links'] += len(lead['candidates'])
        if result['pua_mapping']['candidates'] or not result['unicode_leads']:
            continue
        counts['previously_without_candidate_with_leads'] += 1
        for lead in result['unicode_leads']:
            for candidate in lead['candidates']:
                resolved = reader.lookup(key, lead['entity_id'], candidate['name'])
                chosen = next(m for m in resolved['unicode_leads'] if m['entity_id'] == lead['entity_id'])
                bundle = chosen['bundle']
                assert resolved['pua_mapping']['candidates'] == [] and resolved['pua_mapping']['bundle'] is None
                assert bundle['root'] == f"{candidate['name']}@{candidate['revision']}"
                counts['new_lead_bundles_checked'] += 1
                roots.add(bundle['root'])
                statuses[bundle['dependency_status']] += 1
                if bundle['issues']:
                    issues.append(dict(entity_id=key, target=lead['entity_id'], root=bundle['root'], issues=bundle['issues']))
    return dict(format='source-lead-lookup-audit-v1', dataset_sha256=digest_file(dataset),
                relations_sha256=digest_file(matches), summary_sha256=digest_file(summary),
                snapshot_sha256=reader.snapshot, counts=dict(counts), unique_new_lead_bundle_roots=len(roots),
                new_lead_dependency_status=dict(statuses), dependency_issues=issues,
                limitation='All PUA lookup routes exercised; bundles checked for previously candidate-free PUA only. No rendering or glyph-equivalence confirmation.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dataset')
    p.add_argument('--matches', default='docs/pua-unihan-source-matches.jsonl.gz')
    p.add_argument('--summary', default='docs/pua-unihan-summary.json')
    p.add_argument('--output', default='docs/source-lead-lookup-audit.json')
    args = p.parse_args()
    result = audit(args.dataset, args.matches, args.summary)
    write_json(args.output, result)
    print(result['counts'])
