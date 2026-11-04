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
from tools.verify_corrected_release import verify as verify_correction

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


def package(base, output, corrected=False, baseline=None):
    base,output=Path(base),Path(output)
    if corrected:
        if baseline is None: raise ValueError('Corrected packaging requires the immutable public baseline')
        correction=verify_correction(baseline,base)
        with closing(sqlite3.connect(base.resolve().as_uri()+'?mode=ro',uri=True)) as connection:
            inputs=json.loads(connection.execute("SELECT value FROM metadata WHERE key='inputs'").fetchone()[0])
        if inputs['mappings.jsonl']!='ecf47b9cb361af7fb447f08000d34e811391fc6a869f7c9872463597e6daf6e1':
            raise ValueError('Expected audited corrected mappings')
        eadd=lookup_release(base,'babelstone:han-pua:1.473:U+EADD')
        if eadd['source_refs']!=['USAT05567'] or eadd['search_status']!='no_candidate_in_searched_rules':
            raise ValueError('Missing source-ID correction')
    elif digest_file(base)!=BASE_SHA:
        raise ValueError('Expected exact published preview.1 database')
    output.mkdir(parents=True,exist_ok=True)
    if list(output.iterdir()): raise ValueError('Output directory must be empty')
    release='v0.1.0-preview.2' if corrected else 'v0.1.0-review.1'
    stem='kanji-kage-map-'+release
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
    manifest=dict(format='review-supplement-release-v1',release=release,
                  base_release=None if corrected else 'v0.1.0-preview.1',build=build,original_rows_verified=rows,
                  gzip_sha256=digest_file(compressed),gzip_bytes=compressed.stat().st_size,
                  code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                  mapping_selection_policy='unchanged; reviews scoped by source and criterion',
                  known_correction=('U+EADD source-ID correction applied; all other mapping fields match preview.1.' if corrected else
                      'U+EADD source-ID correction is documented in the included audit; original mapping rows retain preview.1 values.'))
    manifest_path=output/(stem+'.manifest.json');write_json(manifest_path,manifest)
    if corrected:
        manifest['correction_verification']=correction
        write_json(manifest_path,manifest)
    for name,example in examples.items():write_json(output/(name+'-reviewed.json'),example)
    tracked=subprocess.check_output(['git','ls-files','-z']).decode('utf-8').split('\0')
    names=[n for n in tracked if n and (n in {'LICENSE','NOTICE.md','sources.json','sources.lock.json','glyphwiki.lock.json','package.json','package-lock.json'} or
           (n.startswith('kanji_kage_map/') and n.endswith('.py')) or n.startswith('licenses/') or
           n.startswith('schemas/') or n.startswith('tools/') or (n.startswith('requirements') and n.endswith('.txt')) or
           (n.startswith('docs/') and not n.startswith('docs/website/')) or n.startswith('review-'))]
    files={n:Path(n) for n in names}
    files.update({p.name:p for p in [compressed,manifest_path,output/'one-reviewed.json',output/'sea-reviewed.json']})
    readme=Path('docs/CORRECTED-DISTRIBUTION.md' if corrected else 'docs/REVIEW-DISTRIBUTION.md').read_bytes()
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
    p.add_argument('--corrected',action='store_true',help='Package the fully regenerated preview.2 candidate data')
    p.add_argument('--baseline',help='Exact public preview.1 database for all-record correction verification')
    args=p.parse_args();package(args.base,args.output,args.corrected,args.baseline)
