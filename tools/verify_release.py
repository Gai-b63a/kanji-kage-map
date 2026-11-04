"""Check every portable record and candidate, independently of the builder."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.sources import write_json

parser = argparse.ArgumentParser()
parser.add_argument('database')
parser.add_argument('--output', required=True)
args = parser.parse_args()
path = Path(args.database).resolve()
with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    metadata = {k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')}
    assert metadata['build_complete'] is True
    snapshot = metadata['snapshot_sha256']
    refs = set()
    for ref, encoded in db.execute('SELECT reference,json FROM glyphs'):
        row = json.loads(encoded)
        assert row['reference'] == ref
        assert row['snapshot_sha256'] == snapshot
        assert ref == f"{row['name']}@{row['revision']}"
        refs.add(ref)
    candidate_links = 0
    entities = set()
    for entity, encoded in db.execute('SELECT entity_id,json FROM mappings'):
        row = json.loads(encoded)
        assert row['entity_id'] == entity
        assert row['snapshot_sha256'] == snapshot
        entities.add(entity)
        for candidate in row['candidates']:
            assert f"{candidate['name']}@{candidate['revision']}" in refs
            candidate_links += 1
    inventory_ids = {row[0] for row in db.execute('SELECT entity_id FROM inventory')}
    assert entities == inventory_ids
    missing = []
    for parent, line, raw, target in db.execute('SELECT parent,line,raw_reference,target FROM dependencies'):
        assert parent in refs
        if target not in refs:
            missing.append(dict(parent=parent,line=line,raw_reference=raw,target=target))
    assert len(missing) == metadata['counts']['missing_dependency_targets']
report = dict(database_sha256=digest_file(path), entities=len(entities), glyphs=len(refs),
              candidate_links=candidate_links, missing_targets=missing, integrity_check='ok',
              all_candidate_roots_present=True, inventory_and_mapping_ids_equal=True,
              scope='Complete structural audit; no glyph equivalence assertion')
write_json(args.output, report)
print(json.dumps(report, indent=2))
