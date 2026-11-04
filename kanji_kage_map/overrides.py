"""Explicit, scoped candidate choices backed by active whole-glyph reviews."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .review_decisions import require, nonempty, validate


def record_hash(record):
    return hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def read_overrides(path):
    raw=Path(path).read_bytes()
    history=[];ids={};current={}
    fields={'format','override_id','action','review','review_sha256','author','created_at','rationale','supersedes'}
    for line in raw.decode('utf-8').splitlines():
        row=json.loads(line)
        require(set(row)==fields and row['format']=='scoped-mapping-override-v1','Invalid override fields')
        require(nonempty(row['override_id']) and row['override_id'] not in ids,'Invalid or duplicate override ID')
        require(row['action'] in {'select','revoke'},'Invalid override action')
        review=validate(row['review'])
        require(review['decision']=='equivalent' and review['scope']['kind']=='whole_glyph','Selection requires whole-glyph equivalence')
        require(record_hash(review)==row['review_sha256'],'Pinned review content differs')
        require(set(row['author'])=={'name','kind'} and nonempty(row['author']['name']) and row['author']['kind'] in {'human','ai'},'Explicit author required')
        require(nonempty(row['rationale']),'Selection rationale required')
        moment=datetime.fromisoformat(row['created_at'].replace('Z','+00:00'))
        require(moment.tzinfo is not None,'Selection timestamp requires timezone')
        require(moment>=datetime.fromisoformat(review['reviewed_at'].replace('Z','+00:00')),'Selection predates review')
        key=json.dumps({k:review[k] for k in ['entity_id','snapshot_sha256','scope','source']},sort_keys=True)
        previous=row['supersedes']
        if previous is None:
            require(key not in current and row['action']=='select','Existing context requires explicit replacement')
        else:
            require(current.get(key)==previous and previous in ids,'Invalid override predecessor')
            require(moment>=datetime.fromisoformat(ids[previous]['created_at'].replace('Z','+00:00')),'Override predates predecessor')
        ids[row['override_id']]=row;current[key]=row['override_id'];history.append(row)
    return dict(file_sha256=hashlib.sha256(raw).hexdigest(),history=history,
                current_ids=list(current.values()))


def apply_override(result, overrides, override_id):
    """Return a scoped selection; preserve the original mapping and all candidates."""
    require(override_id in overrides['current_ids'],'Override is missing or superseded')
    row=next(r for r in overrides['history'] if r['override_id']==override_id)
    review=row['review']
    require(result['entity_id']==review['entity_id'] and result['snapshot_sha256']==review['snapshot_sha256'],'Override identifier or snapshot differs')
    if row['action']=='revoke':
        return dict(result,scoped_selection=dict(status='revoked',override_id=override_id,selected_glyph=None))
    require('review_decisions' in result,'Dataset must carry the referenced review history')
    ledger=result['review_decisions']
    require(review['review_id'] in ledger['active_review_ids'],'Supporting review is no longer active')
    active=next((r for r in ledger['history'] if r['review_id']==review['review_id']),None)
    require(active==review and record_hash(active)==row['review_sha256'],'Supporting review differs')
    require(review['glyph_reference'] in {f"{c['name']}@{c['revision']}" for c in result['candidates']},'Selected glyph is not a pinned candidate')
    return dict(result,scoped_selection=dict(status='selected',override_id=override_id,
                overrides_sha256=overrides['file_sha256'],selected_glyph=review['glyph_reference'],
                scope=review['scope'],source=review['source'],supporting_review_id=review['review_id'],
                author=row['author'],created_at=row['created_at'],rationale=row['rationale'],
                policy='Applies only to this source, edition and criterion; original mapping is retained.'))
