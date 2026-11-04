"""Fetch or verify the exact site handoff assets without rebuilding the dataset."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',default='docs/deploy-data-manifest.json')
    p.add_argument('--verify-local',action='store_true')
    p.add_argument('--output',default='.cache/deploy-data')
    p.add_argument('--only',nargs='+',help='Asset IDs or license paths; omitted means all')
    a=p.parse_args()
    m=json.loads(Path(a.manifest).read_text(encoding='utf-8'))
    if m['format']!='site-deploy-data-handoff-v1':
        raise ValueError('Unsupported manifest')
    items=m['assets']+m['license_files']
    available={i.get('id',i.get('path')) for i in items}
    if a.only and not set(a.only)<=available:
        raise ValueError('Unknown requested asset')
    for item in items:
        if a.only and item.get('id',item.get('path')) not in a.only:
            continue
        if a.verify_local:
            file=Path(item['local_path'])
            expected=item.get('local_sha256',item['sha256'])
        else:
            relative=Path(item.get('filename',item.get('path')))
            output=Path(a.output).resolve();file=(output/relative).resolve()
            if not file.is_relative_to(output):
                raise ValueError('Destination outside output directory')
            expected=item['sha256']
            if not file.exists():
                file.parent.mkdir(parents=True,exist_ok=True)
                temporary=file.with_name(file.name+'.download')
                with urlopen(Request(item['url'],headers={'User-Agent':'kanji-kage-map-deploy/1'}),timeout=90) as src,temporary.open('wb') as dst:
                    shutil.copyfileobj(src,dst)
                with temporary.open('rb') as stream:
                    if hashlib.file_digest(stream,'sha256').hexdigest()!=expected:
                        raise ValueError(f'Download hash mismatch: {relative}; destination not replaced')
                temporary.replace(file)
        with file.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=expected:
                raise ValueError(f'Hash mismatch: {file}')
        if 'bytes' in item and file.stat().st_size!=item['bytes']:
            raise ValueError(f'Size mismatch: {file}')
        print('verified',item.get('id',item.get('path')))
