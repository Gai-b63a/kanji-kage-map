"""Coverage of provisional mappings, with explicit overlapping populations."""
from collections import Counter, defaultdict
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from .glyphwiki import digest_file


def summarize(rows, snapshot):
    groups = defaultdict(Counter)
    versions, seen = set(), set()
    for inventory, mapping in rows:
        entity = inventory['entity_id']
        if entity in seen or mapping['entity_id'] != entity:
            raise ValueError('Duplicate or mismatched entity')
        seen.add(entity)
        if mapping['snapshot_sha256'] != snapshot:
            raise ValueError('Mixed snapshot')
        # This report is deliberately limited to the current unreviewed contract.
        if mapping['review_status'] != 'unreviewed' or mapping['selected_glyph'] is not None:
            raise ValueError('New review contract requires an evidence-aware coverage implementation')
        versions.add((inventory['provider'], inventory['version']))
        candidates = mapping['candidates']
        states = Counter(c['dependency_status'] for c in candidates)
        if set(states) - {'complete', 'issues'}:
            raise ValueError('Unknown dependency state')
        search = mapping['search_status']
        if search not in ('candidates_found', 'requires_source_evidence', 'no_candidate_in_searched_rules'):
            raise ValueError('Unknown search state')
        if bool(candidates) != (search == 'candidates_found'):
            raise ValueError('Candidate count and search state disagree')
        labels = {'all', 'kind:' + inventory['kind']}
        labels.update('membership:' + name for name in inventory['memberships'])
        for label in labels:
            counts = groups[label]
            counts['entities'] += 1
            counts[search] += 1
            counts['candidate_links'] += len(candidates)
            counts['dependency_complete_links'] += states['complete']
            counts['dependency_issue_links'] += states['issues']
            counts['entities_with_any_dependency_complete_candidate'] += bool(states['complete'])
            counts['entities_with_dependency_issue_candidate'] += bool(states['issues'])
            counts['entities_with_multiple_candidates'] += len(candidates) > 1
            counts['glyph_review_unreviewed'] += 1
    if not seen:
        raise ValueError('Empty population')
    result = {}
    for label, counter in sorted(groups.items()):
        counts = {name: counter[name] for name in (
            'entities', 'candidates_found', 'requires_source_evidence', 'no_candidate_in_searched_rules',
            'candidate_links', 'dependency_complete_links', 'dependency_issue_links',
            'entities_with_any_dependency_complete_candidate', 'entities_with_dependency_issue_candidate',
            'entities_with_multiple_candidates', 'glyph_review_unreviewed')}
        counts['confirmed_glyph_matches'] = 0
        def rate(numerator, denominator):
            return dict(numerator=numerator, denominator=denominator,
                        fraction=numerator / denominator if denominator else None)
        result[label] = dict(counts=counts, rates=dict(
            candidate_presence=rate(counts['candidates_found'], counts['entities']),
            confirmed_glyph_match=rate(0, counts['entities']),
            dependency_complete_candidate_links=rate(counts['dependency_complete_links'], counts['candidate_links'])))
    return dict(format='provisional-coverage-v1', snapshot_sha256=snapshot,
                source_versions=[dict(provider=p, version=v) for p, v in sorted(versions)],
                population_rules=dict(all='unique entity IDs', kind='disjoint partition',
                                      membership='overlapping sets; never sum to obtain the total'),
                dependency_scope='recorded reference and command-tag audit; not full syntax, rendering or glyph equivalence',
                groups=result)


def coverage(database):
    path = Path(database).resolve()
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        for left, right in [('inventory', 'mappings'), ('mappings', 'inventory')]:
            if db.execute(f'SELECT entity_id FROM {left} EXCEPT SELECT entity_id FROM {right} LIMIT 1').fetchone():
                raise ValueError('Inventory and mappings do not contain the same IDs')
        snapshot = json.loads(db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0])
        rows = ((json.loads(i), json.loads(m)) for i, m in db.execute(
            'SELECT i.json,m.json FROM inventory i JOIN mappings m USING(entity_id) ORDER BY i.entity_id'))
        report = summarize(rows, snapshot)
    report['database_sha256'] = digest_file(path)
    return report
