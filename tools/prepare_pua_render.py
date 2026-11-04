"""Prepare every unique PUA discovery candidate for the pinned render engine."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kanji_kage_map.glyphwiki import resolve_bundle, digest_file
from kanji_kage_map.sources import write_json

source = ROOT / 'data/generated/pua-research/pua-candidates.jsonl'
refs = set()
with source.open(encoding='utf-8') as stream:
    for line in stream:
        for candidate in json.loads(line)['candidates']:
            if candidate['revision'] is None:
                raise ValueError('Cannot render an unpinned candidate')
            refs.add(f"{candidate['name']}@{candidate['revision']}")
records = []
for ref in sorted(refs):
    records.append(dict(glyph=ref, keep_artifact=False,
                        bundle=resolve_bundle(ROOT / 'data/generated/glyphwiki.sqlite3', ref)))
write_json(ROOT / 'data/generated/review/pua-all-bundles.json', records)
write_json(ROOT / 'docs/pua-render-input.json', dict(candidates_sha256=digest_file(source),
           bundle_sha256=digest_file(ROOT / 'data/generated/review/pua-all-bundles.json'), unique_candidates=len(refs)))
