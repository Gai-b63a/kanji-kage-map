"""Verify the failed publication's exact existing assets before publishing its draft."""
from contextlib import closing
import gzip
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.verify_review_release_download import verify
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.sources import write_json

REPO='Gai-b63a/kanji-kage-map'
TAG='v0.1.0-preview.2'
COMMIT='1d5f5cff3172eb0d7083155d9c0e8bfcc77084cf'


def main():
    root=Path('recovery-download');root.mkdir()
    raw=subprocess.check_output(['gh','api',f'repos/{REPO}/releases/433768891'])
    release=json.loads(raw)
    if release['tag_name']!=TAG or release['target_commitish']!=COMMIT or not release['prerelease']:
        raise ValueError('Unexpected release identity')
    if len(release['assets'])!=6 or any(a['state']!='uploaded' for a in release['assets']):
        raise ValueError('Incomplete uploaded assets; do not publish')
    (root/'release.json').write_bytes(raw)
    subprocess.run(['gh','release','download',TAG,'--repo',REPO,'--dir',str(root)],check=True)
    subprocess.run(['gh','release','download','v0.1.0-preview.1','--repo',REPO,'--pattern','kanji-kage-map-v0.1.sqlite3.gz','--dir',str(root)],check=True)
    stem='kanji-kage-map-'+TAG
    manifest=json.loads((root/(stem+'.manifest.json')).read_text())
    if manifest['code_commit']!=COMMIT: raise ValueError('Unexpected packaged commit')
    for source,target in [('kanji-kage-map-v0.1.sqlite3.gz','original.sqlite3'),(stem+'.sqlite3.gz','corrected-with-reviews.sqlite3')]:
        with gzip.open(root/source,'rb') as src,(root/target).open('xb') as dst:shutil.copyfileobj(src,dst)
    if digest_file(root/'corrected-with-reviews.sqlite3')!=manifest['build']['dataset_sha256']:
        raise ValueError('Unexpected database hash')
    # Reconstruct only a local comparison base; release assets are never modified.
    shutil.copyfile(root/'corrected-with-reviews.sqlite3',root/'comparison-base.sqlite3')
    keys=['review_ledger_jsonl','review_ledger_sha256','review_parent_dataset_sha256','review_ledger_inputs','review_application']
    with closing(sqlite3.connect(root/'comparison-base.sqlite3')) as db:
        for key in keys:
            if db.execute('DELETE FROM metadata WHERE key=?',(key,)).rowcount!=1:
                raise ValueError('Missing review metadata')
        db.commit()
    report=verify(root,root/'comparison-base.sqlite3',TAG,root/'original.sqlite3',allow_draft=True)
    write_json(root/'verification.json',report)
    if release['draft']:
        subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--draft=false'],check=True)
    current=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/433768891']))
    if current['draft']: raise ValueError('Release is still a draft')
    print(json.dumps(dict(release=current['html_url'],assets=len(current['assets']),verified_payload=report['zip_payload_files_verified'])))


if __name__=='__main__': main()
