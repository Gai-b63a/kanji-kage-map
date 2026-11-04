"""Verify downloaded supplement assets and every offline research lookup."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.ids_name_leads import IdsNameLeads
from kanji_kage_map.sources import write_json

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory')
    p.add_argument('--output',required=True)
    a=p.parse_args(); directory=Path(a.directory)
    release=json.loads((directory/'release.json').read_text(encoding='utf-8'))
    if release['tag_name']!='v0.1.0-ids-leads.1' or release['draft']:
        raise ValueError('Expected public supplement release')
    verified=[]
    for asset in release['assets']:
        name=asset['name']
        if Path(name).name!=name:
            raise ValueError('Invalid asset name')
        raw=(directory/name).read_bytes(); digest=hashlib.sha256(raw).hexdigest()
        if len(raw)!=asset['size'] or asset['digest']!='sha256:'+digest:
            raise ValueError('Downloaded asset differs from API hash/size')
        verified.append(dict(name=name,bytes=len(raw),sha256=digest))
    for line in (directory/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1)
        if Path(name).name!=name or hashlib.sha256((directory/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('External file checksum mismatch')
    with zipfile.ZipFile(directory/'pua-ids-name-offline.zip') as z:
        if len(z.namelist())!=len(set(z.namelist())):
            raise ValueError('Duplicate ZIP entry')
        checked=set()
        for line in z.read('SHA256SUMS').decode().splitlines():
            expected,name=line.split('  ',1)
            if hashlib.sha256(z.read(name)).hexdigest()!=expected:
                raise ValueError('ZIP payload checksum mismatch')
            checked.add(name)
        if checked!=set(z.namelist())-{'SHA256SUMS'}:
            raise ValueError('ZIP file set differs')
        for name in ['pua-ids-name-supplement.json.gz','pua-ids-name-supplement.manifest.json','verification.json']:
            if z.read(name)!=(directory/name).read_bytes():
                raise ValueError('ZIP and standalone files differ')
    reader=IdsNameLeads(directory/'pua-ids-name-supplement.json.gz',directory/'pua-ids-name-supplement.manifest.json')
    canonical=hashlib.sha256(gzip.decompress((directory/'pua-ids-name-supplement.json.gz').read_bytes())).hexdigest()
    if canonical!='6e926aaee42e1383074e66efc73cf99f4f42fcb04d6c7e8c8489de25cc1a5e29' or canonical!=reader.manifest['canonical_sha256']:
        raise ValueError('Canonical records differ from local reproduction')
    links=0
    for entity_id in reader.records:
        for ref in reader.lookup(entity_id)['available_references']:
            row=reader.lookup(entity_id,ref)
            if row['bundle']['root']!=ref or row['selected_glyph'] is not None:
                raise ValueError('Lookup failed')
            links+=1
    if len(reader.records)!=6030 or links!=4927 or len(reader.bundles)!=4925:
        raise ValueError('Population differs')
    result=dict(release_url=release['html_url'],assets=verified,zip_payload_files=len(checked),
                entities=6030,candidate_links=links,unique_roots=4925,
                canonical_sha256=canonical,all_lookup_links_verified=True,confirmed_glyph_matches=0)
    write_json(a.output,result); print(json.dumps(result,indent=2))
