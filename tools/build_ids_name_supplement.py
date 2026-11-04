"""Package checked research rows and unchanged KAGE closures for offline lookup."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import resolve_bundle
from kanji_kage_map.ids_name_leads import IdsNameLeads
from kanji_kage_map.sources import write_json

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', default='data/generated/pua-ids-name-research')
    p.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    directory, output = Path(a.directory), Path(a.output)
    summary = json.loads((directory/'pua-ids-name-leads-summary.json').read_text(encoding='utf-8'))
    raw = (directory/'pua-ids-name-leads.jsonl.gz').read_bytes()
    if hashlib.sha256(raw).hexdigest() != summary['output_sha256']:
        raise ValueError('Lead checksum differs')
    rows = [json.loads(line) for line in gzip.decompress(raw).decode().splitlines()]
    references = sorted({f"{c['name']}@{c['revision']}" for r in rows for c in r['candidates']})
    bundles = [resolve_bundle(a.database, ref) for ref in references]
    if len(rows) != 6030 or len({r['entity_id'] for r in rows}) != 6030:
        raise ValueError('Adopted PUA population differs')
    data = dict(snapshot_sha256=summary['snapshot_sha256'], records=rows, bundles=bundles,
                provenance=dict(ids_pua_sha256=summary['source_sha256'], inventory_sha256=summary['inventory_sha256'],
                                lead_rows_canonical_sha256=hashlib.sha256(gzip.decompress(raw)).hexdigest()))
    canonical = json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    payload = gzip.compress(canonical,mtime=0)
    output.mkdir(parents=True,exist_ok=True)
    archive = output/'pua-ids-name-supplement.json.gz'
    manifest = output/'pua-ids-name-supplement.manifest.json'
    archive.write_bytes(payload)
    write_json(manifest,dict(format='pua-ids-name-supplement-v1', filename=archive.name,
                            sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload),
                            canonical_sha256=hashlib.sha256(canonical).hexdigest(),
                            snapshot_sha256=summary['snapshot_sha256'], entities=len(rows), unique_roots=len(bundles)))
    reader = IdsNameLeads(archive, manifest)
    links = 0
    for row in rows:
        result = reader.lookup(row['entity_id'])
        for reference in result['available_references']:
            found = reader.lookup(row['entity_id'],reference)
            if found['bundle']['root'] != reference or found['selected_glyph'] is not None:
                raise ValueError('Offline lookup differs')
            links += 1
    write_json(output/'verification.json',dict(entities=len(rows), candidate_links=links,
               unique_roots=len(bundles), all_lookups_verified=True, archive_sha256=reader.manifest['sha256']))
    print(json.dumps(reader.manifest,indent=2))
