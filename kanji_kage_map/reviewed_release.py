"""Create a separate portable DB carrying a validated append-only review ledger."""
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from .glyphwiki import digest_file
from .release import lookup_release
from .review_decisions import parse_history, attach_history


def include_reviews(dataset, ledgers, output):
    dataset, output = Path(dataset).resolve(), Path(output).resolve()
    if output.exists() or output == dataset:
        raise ValueError('Output must be a new file')
    partial = output.with_name(output.name + '.partial')
    if partial.exists():
        raise ValueError('Partial output already exists')
    with closing(sqlite3.connect(dataset.as_uri()+'?mode=ro',uri=True)) as db:
        metadata = {k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')}
    if metadata.get('format') != 'kanji-kage-map-portable-v0.1' or not metadata.get('build_complete'):
        raise ValueError('Expected a completed portable dataset')
    chunks = [metadata.get('review_ledger_jsonl','')]
    inputs = []
    for path in ledgers:
        raw = Path(path).read_bytes()
        chunks.append(raw.decode('utf-8'))
        inputs.append(dict(path=str(path),sha256=digest_file(path)))
    raw = ''.join(chunk.rstrip('\n')+'\n' for chunk in chunks if chunk.strip()).encode('utf-8')
    ledger = parse_history(raw)
    if not ledger['history']:
        raise ValueError('No review decisions supplied')
    for entity in sorted({r['entity_id'] for r in ledger['history']}):
        attach_history(lookup_release(dataset,entity),ledger)
    parent_hash = digest_file(dataset)
    output.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(dataset.as_uri()+'?mode=ro',uri=True)) as source, closing(sqlite3.connect(partial)) as target:
        source.backup(target)
        additions = dict(review_ledger_jsonl=raw.decode('utf-8'),review_ledger_sha256=ledger['file_sha256'],
                         review_parent_dataset_sha256=parent_hash,review_ledger_inputs=inputs,
                         review_application='scoped_evidence_only_no_automatic_selection')
        with target:
            target.executemany('INSERT OR REPLACE INTO metadata VALUES (?,?)',[(k,json.dumps(v,ensure_ascii=False,sort_keys=True)) for k,v in additions.items()])
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Derived database integrity check failed')
    for entity in sorted({r['entity_id'] for r in ledger['history']}):
        result=lookup_release(partial,entity)
        if result['review_decisions']['file_sha256'] != ledger['file_sha256']:
            raise ValueError('Embedded reviews did not round-trip')
    partial.rename(output)
    active=[r for r in ledger['history'] if r['review_id'] in ledger['active_review_ids']]
    return dict(format='reviewed-portable-build-v1',parent_dataset_sha256=parent_hash,
                dataset_sha256=digest_file(output),ledger_sha256=ledger['file_sha256'],
                history_records=len(ledger['history']),active_records=len(active),
                active_decisions=dict(sorted(Counter(r['decision'] for r in active).items())),
                mapping_records_unchanged=True,limitation='Scoped review ledger embedded; global mapping selection and coverage are not rewritten.')
