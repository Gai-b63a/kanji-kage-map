"""Acquire original bytes and verify them before offline use."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def acquire(manifest, lock):
    manifest, lock = Path(manifest).resolve(), Path(lock).resolve()
    if lock.exists():
        raise ValueError('Lock already exists; use restore or choose a new --lock path')
    records = []
    for spec in json.loads(manifest.read_text(encoding='utf-8'))['sources']:
        record = dict(spec)
        try:
            with urlopen(Request(spec['url'], headers={'User-Agent': 'kanji-kage-map/0.1'}), timeout=60) as response:
                data = response.read()
                record['final_url'] = response.url
                record['http_last_modified'] = response.headers.get('Last-Modified')
            # Content-addressed storage never overwrites a previous snapshot.
            digest = hashlib.sha256(data).hexdigest()
            path = lock.parent / 'data' / 'raw' / digest / spec['filename']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            record.update(status='acquired', path=path.relative_to(lock.parent).as_posix(),
                          sha256=digest, bytes=len(data), retrieved_at=datetime.now(timezone.utc).isoformat())
        except (OSError, ValueError) as error:
            record.update(status='pending', error=str(error))
        records.append(record)
        print(spec['id'], record['status'], flush=True)
    write_json(lock, {'schema_version': 1, 'sources': records})
    return all(r['status'] == 'acquired' for r in records)


def restore(lock):
    """Fetch missing pinned inputs, refusing changed upstream bytes."""
    lock = Path(lock).resolve()
    for record in json.loads(lock.read_text(encoding='utf-8'))['sources']:
        if record['status'] != 'acquired':
            raise ValueError(f"Cannot restore pending source: {record['id']}")
        path = (lock.parent / record['path']).resolve()
        if not path.is_relative_to(lock.parent):
            raise ValueError('Source path escapes project')
        if path.exists():
            data = path.read_bytes()
        else:
            with urlopen(Request(record['url'], headers={'User-Agent': 'kanji-kage-map/0.1'}), timeout=60) as response:
                data = response.read()
        if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError(f"Source hash/size mismatch: {record['id']}; original snapshot required")
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        print(record['id'], 'verified', flush=True)


def verified_sources(lock):
    lock = Path(lock).resolve()
    result = {}
    for record in json.loads(lock.read_text(encoding='utf-8'))['sources']:
        if record['status'] != 'acquired':
            raise ValueError(f"Source not acquired: {record['id']}")
        path = (lock.parent / record['path']).resolve()
        if not path.is_relative_to(lock.parent):
            raise ValueError('Source path escapes project')
        data = path.read_bytes()
        if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError(f"Source hash/size mismatch: {record['id']}")
        result[record['id']] = (record, data if record.get('encoding') == 'binary' else data.decode(record.get('encoding', 'utf-8-sig')))
    return result
