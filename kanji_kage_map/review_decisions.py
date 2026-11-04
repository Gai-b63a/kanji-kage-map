"""Validate append-only, scoped review decisions independently of candidate mappings."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from .lookup import normalize_identifier

ASPECTS = {'components', 'layout', 'stroke_topology', 'regional_form'}
DECISIONS = {'equivalent', 'different', 'feature_agreement', 'feature_difference', 'inconclusive', 'withdrawn'}
FIELDS = {'format','review_id','entity_id','snapshot_sha256','glyph_reference','scope','decision',
          'reviewer','reviewed_at','source','evidence','observations','limitations','rationale','supersedes'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value,str) and bool(value.strip())


def validate(record):
    require(set(record) == FIELDS, 'Unexpected or missing review fields')
    require(record['format'] == 'glyph-review-decision-v1', 'Unsupported review format')
    require(bool(re.fullmatch(r'[a-z0-9][a-z0-9._-]*',record['review_id'])), 'Invalid review ID')
    require(normalize_identifier(record['entity_id']) == record['entity_id'], 'Canonical entity ID required')
    require(bool(re.fullmatch(r'[0-9a-f]{64}',record['snapshot_sha256'])), 'Snapshot hash required')
    require(bool(re.fullmatch(r'[a-z0-9_.-]+@[1-9][0-9]*',record['glyph_reference'])), 'Pinned glyph reference required')
    scope = record['scope']
    require(set(scope) == {'kind','criterion','source_id'}, 'Explicit criterion and source context required')
    require(scope['kind'] in {'whole_glyph','feature'} and all(nonempty(scope[k]) for k in ['criterion','source_id']), 'Invalid scope')
    if scope['kind'] == 'whole_glyph':
        require(scope['criterion'] == 'structural_glyph_v1', 'Unsupported whole-glyph criterion')
    decision = record['decision']
    require(decision in DECISIONS, 'Invalid decision')
    allowed = {'equivalent','different','inconclusive','withdrawn'} if scope['kind'] == 'whole_glyph' else {'feature_agreement','feature_difference','inconclusive','withdrawn'}
    require(decision in allowed, 'Feature evidence cannot certify whole-glyph equivalence')
    require(set(record['reviewer']) == {'name','kind'} and nonempty(record['reviewer']['name']) and record['reviewer']['kind'] in {'human','ai'}, 'Reviewer attribution required')
    moment = datetime.fromisoformat(record['reviewed_at'].replace('Z','+00:00'))
    require(moment.tzinfo is not None, 'Review timestamp must have timezone')
    source = record['source']
    require(set(source) == {'provider','version','url','sha256','locator','edition_alignment'}, 'Source provenance fields required')
    require(all(nonempty(source[k]) for k in ['provider','version','url','locator']), 'Source location and edition required')
    require(bool(re.fullmatch('[0-9a-f]{64}',source['sha256'])), 'Source hash required')
    require(source['edition_alignment'] in {'verified','unverified'}, 'Edition alignment required')
    require(isinstance(record['evidence'],list) and bool(record['evidence']), 'Evidence required')
    for item in record['evidence']:
        require(set(item) == {'kind','sha256','locator'}, 'Evidence fields required')
        require(nonempty(item['kind']) and nonempty(item['locator']) and bool(re.fullmatch('[0-9a-f]{64}',item['sha256'])), 'Pinned evidence required')
    require(isinstance(record['observations'],list), 'Observations must be a list')
    aspects = {}
    for item in record['observations']:
        require(set(item) == {'aspect','result','detail'} and nonempty(item['aspect']) and nonempty(item['detail']), 'Observation fields required')
        require(item['result'] in {'agreement','difference','not_checked'}, 'Invalid observation result')
        require(item['aspect'] not in aspects, 'Duplicate observation aspect')
        aspects[item['aspect']] = item['result']
    require(isinstance(record['limitations'],list) and all(nonempty(x) for x in record['limitations']), 'Limitations must be text entries')
    require(nonempty(record['rationale']), 'Decision rationale required')
    require(record['supersedes'] is None or nonempty(record['supersedes']), 'Invalid supersedes ID')
    if decision == 'equivalent':
        require(scope['criterion'] == 'structural_glyph_v1', 'Unsupported whole-glyph equivalence criterion')
        require(source['edition_alignment'] == 'verified', 'Cannot accept an unverified source edition')
        require(ASPECTS <= set(aspects) and set(aspects.values()) == {'agreement'}, 'Whole-glyph acceptance requires every structural aspect checked and agreed')
    if decision == 'different':
        require(source['edition_alignment'] == 'verified', 'Whole-glyph rejection requires verified source edition')
    if decision in {'different','feature_difference'}:
        require('difference' in aspects.values(), 'Difference decision lacks a difference observation')
    if decision == 'feature_agreement':
        require(bool(aspects) and set(aspects.values()) == {'agreement'}, 'Feature agreement contradicts observations')
    if decision == 'withdrawn':
        require(record['supersedes'] is not None, 'Withdrawal requires a prior decision')
    return record


def subject(record):
    return (record['entity_id'],record['snapshot_sha256'],record['glyph_reference'],
            json.dumps(record['scope'],sort_keys=True),record['source']['provider'],record['source']['version'],
            record['source']['sha256'],record['source']['locator'])


def read_history(path):
    raw = Path(path).read_bytes()
    history, current, ids = [], {}, {}
    for line in raw.decode('utf-8').splitlines():
        record = validate(json.loads(line))
        require(record['review_id'] not in ids, 'Duplicate review ID')
        key, previous = subject(record), record['supersedes']
        if previous is not None:
            require(previous in ids and subject(ids[previous]) == key, 'Superseded decision must precede this record with the same subject')
            require(current.get(key) == previous, 'Cannot branch from an obsolete decision')
            before = datetime.fromisoformat(ids[previous]['reviewed_at'].replace('Z','+00:00'))
            after = datetime.fromisoformat(record['reviewed_at'].replace('Z','+00:00'))
            require(after >= before, 'Revision predates its predecessor')
        else:
            require(key not in current, 'Existing subject requires an explicit supersedes link')
        current[key] = record['review_id']
        ids[record['review_id']] = record
        history.append(record)
    return dict(file_sha256=hashlib.sha256(raw).hexdigest(), history=history,
                active_review_ids=[r['review_id'] for r in history if current[subject(r)] == r['review_id']])


def attach_decisions(result, path):
    ledger = read_history(path)
    candidates = {f"{c['name']}@{c['revision']}" for c in result['candidates']}
    relevant = [r for r in ledger['history'] if r['entity_id'] == result['entity_id']]
    for record in relevant:
        require(record['snapshot_sha256'] == result['snapshot_sha256'], 'Review snapshot differs from mapping')
        require(record['glyph_reference'] in candidates, 'Reviewed glyph is not a pinned mapping candidate')
    requested = result['bundle']['root'] if result.get('bundle') else None
    history = [r for r in relevant if requested is None or r['glyph_reference'] == requested]
    ids = {r['review_id'] for r in history}
    return dict(result, review_decisions=dict(file_sha256=ledger['file_sha256'],history=history,
                active_review_ids=[i for i in ledger['active_review_ids'] if i in ids],
                application='scoped_evidence_only_no_automatic_selection'))
