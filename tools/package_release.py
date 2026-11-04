"""Package the portable dataset with offline lookup code and original notices."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def package(project, manifest_path, output):
    project, manifest_path, output = map(Path, (project, manifest_path, output))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    data = manifest_path.with_name(manifest_path.name.replace('.manifest.json', '.sqlite3.gz'))
    if digest(data) != manifest['gzip_sha256'] or data.stat().st_size != manifest['gzip_bytes']:
        raise ValueError('Compressed database does not match the release manifest')
    partial = output.with_suffix(output.suffix + '.part')
    if output.exists() or partial.exists():
        raise ValueError('Output or partial package exists; use another output path')
    files = {
        'NOTICE.md': project / 'NOTICE.md',
        'LICENSE': project / 'LICENSE',
        'tools/verify_release.py': project / 'tools/verify_release.py',
        data.name: data,
        manifest_path.name: manifest_path,
    }
    for directory, pattern in [('kanji_kage_map', '*.py'), ('licenses', '*.txt'),
                               ('schemas', '*.json'), ('docs', '*')]:
        for path in sorted((project / directory).glob(pattern)):
            if path.is_file():
                files[path.relative_to(project).as_posix()] = path
    for name in ('sources.lock.json', 'glyphwiki.lock.json', 'review-sources.lock.json',
                 'review-webfonts.lock.json'):
        files[name] = project / name
    readme = (project / 'docs/DISTRIBUTION.md').read_text(encoding='utf-8').replace('](../', '](').encode('utf-8')
    hashes = {name: digest(path) for name, path in files.items()}
    hashes['README.md'] = hashlib.sha256(readme).hexdigest()
    checksums = ''.join(f'{value}  {name}\n' for name, value in sorted(hashes.items()))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_STORED) as archive:
        for name, path in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            with path.open('rb') as source, archive.open(entry, 'w') as target:
                shutil.copyfileobj(source, target)
        for name, content in [('README.md', readme), ('SHA256SUMS', checksums)]:
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content)
    partial.rename(output)
    result = {'file': output.name, 'bytes': output.stat().st_size,
              'sha256': digest(output), 'payload_files': len(hashes),
              'status': 'local-package-not-published', 'confirmed_matches': 0}
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('.'))
    parser.add_argument('--manifest', type=Path,
                        default=Path('dist/kanji-kage-map-v0.1.manifest.json'))
    parser.add_argument('--output', type=Path,
                        default=Path('dist/kanji-kage-map-v0.1-offline.zip'))
    args = parser.parse_args()
    package(args.project, args.manifest, args.output)
