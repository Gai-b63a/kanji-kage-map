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
from tools.verify_corrected_release import verify as verify_correction
from kanji_kage_map.review_decisions import parse_history
from kanji_kage_map.release import lookup_release
from contextlib import closing
import sqlite3


def verify(directory, base, tag='v0.1.0-review.1', original=None, allow_draft=False):
    directory=Path(directory)
    if tag not in {'v0.1.0-review.1','v0.1.0-preview.2'}:
        raise ValueError('Unsupported release tag')
    if tag=='v0.1.0-preview.2':
        if original is None: raise ValueError('Corrected verification requires the original public baseline')
        verify_correction(original,base)
    release=json.loads((directory/'release.json').read_text(encoding='utf-8-sig'))
    if release['tag_name']!=tag or (release['draft'] and not allow_draft):
        raise ValueError('Expected public release')
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
    stem='kanji-kage-map-'+tag
    manifest=json.loads((directory/(stem+'.manifest.json')).read_text())
    if manifest['release']!=tag: raise ValueError('Manifest release differs')
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
    for name in (stem+'.sqlite3.gz',stem+'.manifest.json','one-reviewed.json','sea-reviewed.json'):
        if digest_file(offline/name)!=digest_file(directory/name):
            raise ValueError('ZIP and standalone asset differ: '+name)
    db=offline/'dataset.sqlite3'
    with gzip.open(offline/(stem+'.sqlite3.gz'),'rb') as src,db.open('xb') as dst:shutil.copyfileobj(src,dst)
    if digest_file(db)!=manifest['build']['dataset_sha256']:
        raise ValueError('Uncompressed database hash mismatch')
    rows=compare(base,db)
    with closing(sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)) as connection:
        metadata={k:json.loads(v) for k,v in connection.execute('SELECT * FROM metadata')}
    ledger=parse_history(metadata['review_ledger_jsonl'].encode('utf-8'))
    if ledger['file_sha256']!=manifest['build']['ledger_sha256'] or ledger['file_sha256']!=metadata['review_ledger_sha256']:
        raise ValueError('Embedded review hash differs')
    for entity in {r['entity_id'] for r in ledger['history']}:
        lookup_release(db,entity)
    return dict(format='review-release-download-verification-v1',release=release['html_url'],
                tag=release['tag_name'],draft=release['draft'],code_commit=manifest['code_commit'],assets=assets,
                zip_payload_files_verified=len(checks),derived_database_sha256=digest_file(db),
                all_original_table_rows_equal=rows,ledger_sha256=manifest['build']['ledger_sha256'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory');p.add_argument('--base',required=True);p.add_argument('--output',required=True)
    p.add_argument('--tag',default='v0.1.0-review.1',choices=['v0.1.0-review.1','v0.1.0-preview.2'])
    p.add_argument('--original',help='Exact public preview.1 DB, required for corrected release verification')
    args=p.parse_args();report=verify(args.directory,args.base,args.tag,args.original);write_json(args.output,report)
    print(dict(assets=len(report['assets']),payload_files=report['zip_payload_files_verified'],rows=report['all_original_table_rows_equal']))
