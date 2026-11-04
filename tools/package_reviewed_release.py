"""Package an immutable base dataset plus validated review history and lookup code."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.release import lookup_release
from kanji_kage_map.reviewed_release import include_reviews
from kanji_kage_map.sources import write_json

BASE_SHA = '99d876fce6118a3b80924fd05b3b9c8580ac0496a5db403daba0ac6ff64b3ab6'


def compare(base, derived):
    counts={}
    with closing(sqlite3.connect(Path(base).resolve().as_uri()+'?mode=ro',uri=True)) as a, closing(sqlite3.connect(Path(derived).resolve().as_uri()+'?mode=ro',uri=True)) as b:
        for table,order in [('inventory','entity_id'),('mappings','entity_id'),('glyphs','reference'),('dependencies','parent,line'),('issues','reference,json')]:
            left=a.execute(f'SELECT * FROM {table} ORDER BY {order}')
            right=b.execute(f'SELECT * FROM {table} ORDER BY {order}')
            count=0
            while True:
                x,y=left.fetchmany(10000),right.fetchmany(10000)
                if x != y: raise ValueError(f'Original records changed: {table}')
                if not x: break
                count+=len(x)
            counts[table]=count
        original=dict(a.execute('SELECT * FROM metadata'));updated=dict(b.execute('SELECT * FROM metadata'))
        if any(updated.get(k)!=v for k,v in original.items()): raise ValueError('Original metadata changed')
    return counts


def package(base, output):
    base,output=Path(base),Path(output)
    if digest_file(base)!=BASE_SHA: raise ValueError('Expected exact published preview.1 database')
    output.mkdir(parents=True,exist_ok=True)
    if list(output.iterdir()): raise ValueError('Output directory must be empty')
    stem='kanji-kage-map-v0.1.0-review.1'
    db=output/(stem+'.sqlite3')
    build=include_reviews(base,['docs/sea-review-decisions.jsonl','docs/one-review-decision.jsonl'],db)
    rows=compare(base,db)
    examples={}
    for entity,glyph,name in [('U+4E00','u4e00','one'),('U+6D77','u6d77','sea')]:
        result=lookup_release(db,entity,glyph)
        if result['selected_glyph'] is not None: raise ValueError('Review import selected a glyph')
        examples[name]=result
    if [r['decision'] for r in examples['one']['review_decisions']['history']] != ['equivalent']:
        raise ValueError('Missing structural equivalence review')
    if {r['decision'] for r in examples['sea']['review_decisions']['history']} != {'different','inconclusive'}:
        raise ValueError('Missing scoped sea reviews')
    compressed=output/(stem+'.sqlite3.gz')
    with db.open('rb') as src,compressed.open('xb') as dst,gzip.GzipFile(filename='',fileobj=dst,mode='wb',mtime=0) as z:
        shutil.copyfileobj(src,z)
    manifest=dict(format='review-supplement-release-v1',release='v0.1.0-review.1',
                  base_release='v0.1.0-preview.1',build=build,original_rows_verified=rows,
                  gzip_sha256=digest_file(compressed),gzip_bytes=compressed.stat().st_size,
                  code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                  mapping_selection_policy='unchanged; reviews scoped by source and criterion',
                  known_correction='U+EADD source-ID correction is documented in the included audit; original mapping rows retain preview.1 values.')
    manifest_path=output/(stem+'.manifest.json');write_json(manifest_path,manifest)
    for name,example in examples.items():write_json(output/(name+'-reviewed.json'),example)
    tracked=subprocess.check_output(['git','ls-files','-z']).decode('utf-8').split('\0')
    names=[n for n in tracked if n and (n in {'LICENSE','NOTICE.md','sources.json','sources.lock.json','glyphwiki.lock.json','package.json','package-lock.json'} or
           (n.startswith('kanji_kage_map/') and n.endswith('.py')) or n.startswith('licenses/') or
           n.startswith('schemas/') or n.startswith('tools/') or (n.startswith('requirements') and n.endswith('.txt')) or
           (n.startswith('docs/') and not n.startswith('docs/website/')) or n.startswith('review-'))]
    files={n:Path(n) for n in names}
    files.update({p.name:p for p in [compressed,manifest_path,output/'one-reviewed.json',output/'sea-reviewed.json']})
    readme=Path('docs/REVIEW-DISTRIBUTION.md').read_bytes()
    hashes={n:digest_file(p) for n,p in files.items()};hashes['README.md']=hashlib.sha256(readme).hexdigest()
    checks=''.join(f'{h}  {n}\n' for n,h in sorted(hashes.items())).encode()
    archive=output/(stem+'-offline.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED) as z:
        for name,path in sorted(files.items()):
            entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));entry.create_system=3;entry.external_attr=0o100644<<16
            with path.open('rb') as src,z.open(entry,'w') as dst:shutil.copyfileobj(src,dst)
        for name,data in [('README.md',readme),('SHA256SUMS',checks)]:
            entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));entry.create_system=3;entry.external_attr=0o100644<<16;z.writestr(entry,data)
    with zipfile.ZipFile(archive) as z:
        for name,expected in hashes.items():
            with z.open(name) as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=expected:raise ValueError('Packaged hash mismatch: '+name)
    assets=[compressed,manifest_path,archive,output/'one-reviewed.json',output/'sea-reviewed.json']
    (output/'SHA256SUMS').write_text(''.join(f'{digest_file(p)}  {p.name}\n' for p in assets),encoding='utf-8',newline='\n')
    print(json.dumps(dict(assets=len(assets)+1,package_files=len(hashes),original_rows_verified=rows)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('base');p.add_argument('--output',required=True)
    args=p.parse_args();package(args.base,args.output)
