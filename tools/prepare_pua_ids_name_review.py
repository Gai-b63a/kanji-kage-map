"""Resolve research leads and compare against a pinned published mapping snapshot."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import resolve_bundle
from kanji_kage_map.sources import write_json


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--leads', required=True)
    p.add_argument('--summary', required=True)
    p.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    p.add_argument('--published', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    compressed = Path(a.leads).read_bytes()
    summary = json.loads(Path(a.summary).read_text(encoding='utf-8'))
    if hashlib.sha256(compressed).hexdigest() != summary['output_sha256']:
        raise ValueError('Lead file hash differs')
    rows = [json.loads(line) for line in gzip.decompress(compressed).decode().splitlines()]
    if len(rows) != 6030 or len({r['entity_id'] for r in rows}) != 6030:
        raise ValueError('PUA population differs')
    with Path(a.published).open('rb') as stream:
        published_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    if published_sha != '4cb1ba08625e6a6771589304cfe214573c18165f32b59c68cdbc3054847cd0aa':
        raise ValueError('Published preview.2 database hash differs')
    counts = Counter()
    bundles = []
    references = {}
    with sqlite3.connect(Path(a.published).resolve().as_uri()+'?mode=ro', uri=True) as db:
        for row in rows:
            found = db.execute('SELECT json FROM mappings WHERE entity_id=?', (row['entity_id'],)).fetchone()
            if found is None:
                raise ValueError('Missing published entity')
            original = json.loads(found[0])
            if original['snapshot_sha256'] != summary['snapshot_sha256']:
                raise ValueError('Published snapshot differs')
            old = {(c['name'], c['revision']) for c in original['candidates']}
            if row['candidates'] and not old:
                counts['previously_candidate_free_entities_with_leads'] += 1
            for c in row['candidates']:
                reference = f"{c['name']}@{c['revision']}"
                counts['links_already_in_published' if (c['name'], c['revision']) in old else 'new_research_links'] += 1
                references.setdefault(reference, []).append(row['entity_id'])
    for reference, entity_ids in sorted(references.items()):
        bundle = resolve_bundle(a.database, reference)
        if bundle['snapshot_sha256'] != summary['snapshot_sha256']:
            raise ValueError('Bundle snapshot differs')
        counts['unique_roots'] += 1
        counts['dependency_' + bundle['dependency_status']] += 1
        bundles.append(dict(candidate=reference, entity_ids=entity_ids, bundle=bundle, keep_artifact=False))
    output = Path(a.output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output/'bundles.json', bundles)
    write_json(output/'comparison.json', dict(snapshot_sha256=summary['snapshot_sha256'],
               leads_sha256=summary['output_sha256'], counts=dict(counts),
               published_dataset_path=a.published,
               published_dataset_sha256=published_sha,
               limitation='New research links are not equivalent glyphs; mappings are unchanged.'))
    print(json.dumps(dict(counts), indent=2))
