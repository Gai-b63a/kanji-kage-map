"""Audit the complete dependency closure of every discovered candidate."""
from collections import Counter, deque
from contextlib import closing
import json
from pathlib import Path
import re

from .glyphwiki import open_index, digest_file
from .sources import write_json

REASONS = {1: 'missing_reference', 2: 'invalid_reference', 4: 'revision_unresolved',
           8: 'invalid_kage_command', 16: 'malformed_dependency', 32: 'empty_kage',
           64: 'cycle_reachable'}


def propagate(children, own):
    """Compute reachable faults and cycle reachability without recursive DFS."""
    parents = [[] for _ in children]
    degree = []
    for parent, targets in enumerate(children):
        degree.append(len(targets))
        for child in targets:
            parents[child].append(parent)
    sinks = deque(i for i, value in enumerate(degree) if value == 0)
    while sinks:
        node = sinks.popleft()
        for parent in parents[node]:
            degree[parent] -= 1
            if degree[parent] == 0:
                sinks.append(parent)
    masks = [mask | (64 if degree[i] else 0) for i, mask in enumerate(own)]
    queue = deque(i for i, mask in enumerate(masks) if mask)
    pending = set(queue)
    while queue:
        node = queue.popleft()
        pending.remove(node)
        for parent in parents[node]:
            combined = masks[parent] | masks[node]
            if combined != masks[parent]:
                masks[parent] = combined
                if parent not in pending:
                    pending.add(parent)
                    queue.append(parent)
    return masks


def audit_dependencies(database, candidates, output):
    candidates, output = Path(candidates), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    keys, ids, children, own = [], {}, [], []
    roots = set()
    candidate_links = 0

    def intern(key):
        if key not in ids:
            ids[key] = len(keys)
            keys.append(key)
            children.append([])
            own.append(0)
        return ids[key]

    with closing(open_index(database)) as db:
        snapshot = db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0]
        with candidates.open(encoding='utf-8') as stream:
            for line in stream:
                record = json.loads(line)
                if record['snapshot_sha256'] != snapshot:
                    raise ValueError('Candidate/index snapshot mismatch')
                for candidate in record['candidates']:
                    key = candidate['name'] + (f"@{candidate['revision']}" if candidate['revision'] is not None else '')
                    roots.add(intern(key))
                    candidate_links += 1
        raw_refs = {}
        issue_counts = Counter()
        edge_count = 0
        with (output / 'glyphs.jsonl').open('w', encoding='utf-8', newline='\n') as glyphs, \
                (output / 'dependencies.jsonl').open('w', encoding='utf-8', newline='\n') as edges, \
                (output / 'dependency-issues.jsonl').open('w', encoding='utf-8', newline='\n') as problems:
            def problem(node, mask, **context):
                own[node] |= mask
                issue_counts[REASONS[mask]] += 1
                problems.write(json.dumps(dict(reference=keys[node], reason=REASONS[mask], **context),
                                          ensure_ascii=False, sort_keys=True) + '\n')

            node = 0
            while node < len(keys):
                key = keys[node]
                match = re.fullmatch(r'([a-z0-9_.-]+)(?:@(\d+))?', key)
                if not match:
                    problem(node, 2)
                    node += 1
                    continue
                name, revision = match.groups()
                row = db.execute('SELECT * FROM history WHERE name=? AND revision=?', (name, int(revision))).fetchone() if revision else \
                    db.execute('SELECT * FROM latest WHERE name=?', (name,)).fetchone()
                if row is None:
                    problem(node, 1)
                    node += 1
                    continue
                if row['revision'] is None:
                    problem(node, 4)
                glyphs.write(json.dumps(dict(reference=key, snapshot_sha256=snapshot, **dict(row)),
                                       ensure_ascii=False, sort_keys=True) + '\n')
                if not row['data']:
                    problem(node, 32)
                else:
                    for number, stroke in enumerate(row['data'].split('$'), 1):
                        fields = stroke.split(':')
                        if not fields[0].isdigit():
                            problem(node, 8, line=number, raw=stroke)
                            continue
                        if fields[0] != '99':
                            continue
                        if len(fields) < 8:
                            problem(node, 16, line=number, raw=stroke)
                            continue
                        raw = fields[7]
                        if raw not in raw_refs:
                            target = raw
                            if re.fullmatch(r'[a-z0-9_.-]+', raw):
                                current = db.execute('SELECT revision FROM latest WHERE name=?', (raw,)).fetchone()
                                if current and current[0] is not None:
                                    target = f'{raw}@{current[0]}'
                            raw_refs[raw] = intern(target)
                        child = raw_refs[raw]
                        children[node].append(child)
                        edges.write(json.dumps(dict(parent=key, line=number, raw_reference=raw,
                                                     target=keys[child]), ensure_ascii=False, sort_keys=True) + '\n')
                        edge_count += 1
                node += 1
                if node % 100000 == 0:
                    print(f'{node} dependency nodes processed; {len(keys)} discovered', flush=True)
    masks = propagate(children, own)
    counts = Counter()
    with (output / 'candidate-dependencies.jsonl').open('w', encoding='utf-8', newline='\n') as stream:
        for node in sorted(roots, key=lambda i: keys[i]):
            reasons = [reason for bit, reason in REASONS.items() if masks[node] & bit]
            counts['issues' if reasons else 'complete'] += 1
            for reason in reasons:
                counts[reason] += 1
            stream.write(json.dumps(dict(reference=keys[node], dependency_status='issues' if reasons else 'complete',
                                         reachable_issues=reasons, review_status='unreviewed', render_status='not_run'),
                                    sort_keys=True) + '\n')
    summary = dict(schema_version=1, snapshot_sha256=snapshot, candidates_sha256=digest_file(candidates),
                   candidate_links=candidate_links, unique_candidate_roots=len(roots),
                   dependency_nodes=len(keys), dependency_edges=edge_count,
                   local_issue_events=dict(issue_counts), candidate_root_status=dict(counts),
                   cycle_reachable_nodes=sum(bool(mask & 64) for mask in masks),
                   limitation='Reference and command-tag audit only; no coordinate, rendering, or glyph-identity certification.')
    write_json(output / 'dependency-summary.json', summary)
    write_json(output / 'checksums.json', {name: digest_file(output / name) for name in
               ('glyphs.jsonl', 'dependencies.jsonl', 'dependency-issues.jsonl', 'candidate-dependencies.jsonl', 'dependency-summary.json')})
    print(json.dumps(summary, indent=2))
    return summary
