"""Verify actual downloaded review-release assets, their ZIP and decompressed DB."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.sources import write_json
from tools.package_reviewed_release import compare


def verify(directory, base):
    directory=Path(directory)
    release=json.loads((directory/'release.json').read_text(encoding='utf-8-sig'))
    if release['tag_name']!='v0.1.0-review.1' or release['draft']:
        raise ValueError('Expected public review supplement')
    expected={name:digest for digest,name in (line.split('  ',1) for line in (directory/'SHA256SUMS').read_text().splitlines())}
    asset_names={a['name'] for a in release['assets']}
    if set(expected)|{'SHA256SUMS'} != asset_names:
        raise ValueError('Checksum list and release assets differ')
    assets=[]
    for asset in release['assets']:
        name=asset['name']
        if Path(name).name!=name or '/' in name or '\\' in name:raise ValueError('Unsafe name')
        path=directory/name;digest=digest_file(path)
        if path.stat().st_size!=asset['size'] or asset.get('digest')!='sha256:'+digest:
            raise ValueError('Public asset metadata mismatch: '+name)
        if name in expected and expected[name]!=digest:raise ValueError('Checksum mismatch: '+name)
        assets.append(dict(name=name,bytes=path.stat().st_size,sha256=digest))
    stem='kanji-kage-map-v0.1.0-review.1'
    manifest=json.loads((directory/(stem+'.manifest.json')).read_text())
    if digest_file(directory/(stem+'.sqlite3.gz'))!=manifest['gzip_sha256']:
        raise ValueError('Manifest gzip hash differs')
    offline=directory/'offline'
    offline.mkdir(exist_ok=False)
    with zipfile.ZipFile(directory/(stem+'-offline.zip')) as z:
        checks={name:digest for digest,name in (line.split('  ',1) for line in z.read('SHA256SUMS').decode().splitlines())}
        if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(checks)|{'SHA256SUMS'}:
            raise ValueError('Unexpected ZIP payload')
        for name,digest in checks.items():
            if not (offline/name).resolve().is_relative_to(offline.resolve()):raise ValueError('Unsafe ZIP path')
            with z.open(name) as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:raise ValueError('ZIP payload hash mismatch')
        z.extractall(offline)
    db=offline/'dataset.sqlite3'
    with gzip.open(offline/(stem+'.sqlite3.gz'),'rb') as src,db.open('xb') as dst:shutil.copyfileobj(src,dst)
    if digest_file(db)!=manifest['build']['dataset_sha256']:
        raise ValueError('Uncompressed database hash mismatch')
    rows=compare(base,db)
    return dict(format='review-release-download-verification-v1',release=release['html_url'],
                tag=release['tag_name'],code_commit=manifest['code_commit'],assets=assets,
                zip_payload_files_verified=len(checks),derived_database_sha256=digest_file(db),
                all_original_table_rows_equal=rows,ledger_sha256=manifest['build']['ledger_sha256'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory');p.add_argument('--base',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();report=verify(args.directory,args.base);write_json(args.output,report)
    print(dict(assets=len(report['assets']),payload_files=report['zip_payload_files_verified'],rows=report['all_original_table_rows_equal']))
