"""Summarize scoped review history without promoting it to mapping decisions."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.review_decisions import parse_history, attach_history
from kanji_kage_map.sources import write_json
from kanji_kage_map.glyphwiki import digest_file


def summarize(ledger, population):
    current=[r for r in ledger['history'] if r['review_id'] in set(ledger['active_review_ids'])]
    active=[r for r in current if r['decision']!='withdrawn']
    counts=Counter((r['scope']['kind'],r['scope']['criterion'],r['decision']) for r in active)
    groups=defaultdict(list)
    for row in active:
        if row['decision']!='equivalent': continue
        key=json.dumps(dict(entity_id=row['entity_id'],snapshot_sha256=row['snapshot_sha256'],
                            scope=row['scope'],source={k:row['source'][k] for k in ['provider','version','sha256','locator']}),sort_keys=True)
        groups[key].append(row)
    multiple=[]
    for key, rows in sorted(groups.items()):
        if len({r['glyph_reference'] for r in rows})>1:
            multiple.append(dict(context=json.loads(key),glyph_references=sorted({r['glyph_reference'] for r in rows}),
                                 review_ids=sorted(r['review_id'] for r in rows)))
    entities={r['entity_id'] for r in active}
    if len(entities)>population: raise ValueError('Review population exceeds inventory')
    return dict(format='scoped-review-summary-v1',ledger_sha256=ledger['file_sha256'],
                inventory_entities=population,history_records=len(ledger['history']),
                current_records=len(current),withdrawn_current_records=len(current)-len(active),
                active_nonwithdrawn_records=len(active),entities_with_active_scoped_records=len(entities),
                entities_without_active_scoped_records=population-len(entities),
                counts_by_scope=[dict(kind=k,criterion=c,decision=d,records=n) for (k,c,d),n in sorted(counts.items())],
                reviewer_kinds=dict(sorted(Counter(r['reviewer']['kind'] for r in active).items())),
                multiple_equivalent_candidates_same_context=multiple,
                active_contexts=[{k:r[k] for k in ['review_id','entity_id','snapshot_sha256','glyph_reference','scope','source','decision','reviewer']} for r in active],
                policy='Counts describe scoped records only; no global confirmed-entity count or candidate selection is inferred. Different sources, editions and criteria remain separate. Withdrawal excludes a record from active judgments; history remains retained.')


def summarize_dataset(dataset):
    with closing(sqlite3.connect(Path(dataset).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        meta={k:json.loads(v) for k,v in db.execute('SELECT * FROM metadata')}
        if not meta.get('build_complete'): raise ValueError('Incomplete database')
        raw=meta['review_ledger_jsonl'].encode('utf-8')
        if hashlib.sha256(raw).hexdigest()!=meta['review_ledger_sha256']: raise ValueError('Review checksum mismatch')
        ledger=parse_history(raw)
        for entity in {r['entity_id'] for r in ledger['history']}:
            row=db.execute('SELECT json FROM mappings WHERE entity_id=?',(entity,)).fetchone()
            if row is None: raise ValueError('Reviewed identifier absent from mappings')
            attach_history(json.loads(row[0]),ledger)
        report=summarize(ledger,db.execute('SELECT COUNT(*) FROM inventory').fetchone()[0])
        report['dataset_sha256']=digest_file(dataset)
        report['snapshot_sha256']=meta['snapshot_sha256']
        return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset');p.add_argument('--output',required=True)
    args=p.parse_args();write_json(args.output,summarize_dataset(args.dataset))
