"""Bundle offline reader, research data and their separate license notices."""
import argparse
import hashlib
from pathlib import Path
import zipfile

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',required=True)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    directory = Path(a.directory)
    files = {f.name:f.read_bytes() for f in directory.iterdir() if f.suffix in {'.gz','.json'}}
    for relative in ['LICENSE','NOTICE.md','docs/IDS-NAME-SUPPLEMENT.md','docs/PUA-IDS-NAME-LEADS.md',
                     'sources.lock.json','glyphwiki.lock.json','docs/pua-ids-name-leads-summary.json']:
        files[relative] = (root/relative).read_bytes()
    for folder, pattern in [('kanji_kage_map','*.py'),('licenses','*')]:
        for f in (root/folder).glob(pattern):
            if f.is_file():
                files[f.relative_to(root).as_posix()] = f.read_bytes()
    files['SHA256SUMS'] = ''.join(f'{hashlib.sha256(b).hexdigest()}  {n}\n' for n,b in sorted(files.items())).encode()
    with zipfile.ZipFile(directory/'pua-ids-name-offline.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,raw in sorted(files.items()):
            info = zipfile.ZipInfo(name,date_time=(2026,11,4,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info,raw)
    (directory/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n'
        for f in sorted(directory.iterdir()) if f.is_file() and f.name != 'SHA256SUMS'),encoding='utf-8')
