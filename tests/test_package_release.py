import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('package_release', Path(__file__).resolve().parents[1] / 'tools/package_release.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PackageTest(unittest.TestCase):
    def test_deterministic_self_contained_allowlist_and_tamper_rejection(self):
        parent = Path(__file__).resolve().parents[1] / '.cache/tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temporary:
            root = Path(temporary)
            for name in ('docs/DISTRIBUTION.md', 'NOTICE.md', 'LICENSE', 'tools/verify_release.py',
                         'kanji_kage_map/__main__.py', 'licenses/GLYPHWIKI.txt',
                         'sources.lock.json', 'glyphwiki.lock.json', 'review-sources.lock.json',
                         'review-webfonts.lock.json', '.env', 'data/raw/private.txt'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('[notice](../NOTICE.md)', encoding='utf-8')
            data = root / 'sample.sqlite3.gz'
            data.write_bytes(gzip.compress(b'fixture database', mtime=0))
            manifest = root / 'sample.manifest.json'
            manifest.write_text(json.dumps({'gzip_sha256': module.digest(data), 'gzip_bytes': data.stat().st_size}))
            first, second = root / 'first.zip', root / 'second.zip'
            module.package(root, manifest, first)
            module.package(root, manifest, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertNotIn('.env', archive.namelist())
                self.assertNotIn('data/raw/private.txt', archive.namelist())
                self.assertEqual(archive.read('README.md'), b'[notice](NOTICE.md)')
                for line in archive.read('SHA256SUMS').decode().splitlines():
                    expected, name = line.split('  ', 1)
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)
            with self.assertRaisesRegex(ValueError, 'exists'):
                module.package(root, manifest, first)
            data.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'does not match'):
                module.package(root, manifest, root / 'bad.zip')
            self.assertFalse((root / 'bad.zip').exists())
