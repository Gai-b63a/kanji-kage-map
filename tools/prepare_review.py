"""Deterministic diagnostic sample; no implicit confirmation of font editions."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kanji_kage_map.glyphwiki import resolve_bundle
from kanji_kage_map.sources import write_json

rows = []
with (ROOT / 'data/generated/pua-research/pua-candidates.jsonl').open(encoding='utf-8') as stream:
    for line in stream:
        row = json.loads(line)
        if row['candidates']:
            rows.append(row)
sample = [rows[i * (len(rows) - 1) // 11] for i in range(12)]
records = []
for row in sample:
    candidate = row['candidates'][0]
    ref = f"{candidate['name']}@{candidate['revision']}"
    records.append(dict(entity_id=row['entity_id'], glyph=ref, evidence=candidate['evidence'],
                        diagnostic_only=True, font_version='1.472', inventory_version='1.473',
                        bundle=resolve_bundle(ROOT / 'data/generated/glyphwiki.sqlite3', ref)))
write_json(ROOT / 'data/generated/review/bundles.json', records)
