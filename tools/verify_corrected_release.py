"""Verify the exact allowed correction against the immutable public preview."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.sources import write_json

BASE_SHA = '99d876fce6118a3b80924fd05b3b9c8580ac0496a5db403daba0ac6ff64b3ab6'
MAPPING_SHA = 'ecf47b9cb361af7fb447f08000d34e811391fc6a869f7c9872463597e6daf6e1'
ENTITY = 'babelstone:han-pua:1.473:U+EADD'


def compare_records(before, after):
    """Check all rows; caller separately verifies the immutable baseline hash."""
    counts, changed = {}, []
    with closing(sqlite3.connect(Path(before).resolve().as_uri()+'?mode=ro',uri=True)) as a, closing(sqlite3.connect(Path(after).resolve().as_uri()+'?mode=ro',uri=True)) as b:
        for table, order in [('inventory','entity_id'),('mappings','entity_id'),('glyphs','reference'),('dependencies','parent,line'),('issues','reference,json')]:
            x=a.execute(f'SELECT * FROM {table} ORDER BY {order}')
            y=b.execute(f'SELECT * FROM {table} ORDER BY {order}')
            count=0
            while True:
                left,right=x.fetchmany(10000),y.fetchmany(10000)
                if len(left)!=len(right): raise ValueError('Population changed: '+table)
                if not left: break
                for old,new in zip(left,right):
                    if old==new: continue
                    if table!='mappings' or old[0]!=ENTITY or new[0]!=ENTITY:
                        raise ValueError('Unexpected record change: '+table)
                    original,revised=json.loads(old[1]),json.loads(new[1])
                    if original.get('source_refs')!=[] or original.get('search_status')!='requires_source_evidence':
                        raise ValueError('Unexpected original EADD record')
                    expected=dict(original,source_refs=['USAT05567'],search_status='no_candidate_in_searched_rules')
                    if revised!=expected: raise ValueError('Unexpected EADD fields')
                    changed.append(ENTITY)
                count+=len(left)
            counts[table]=count
        if changed!=[ENTITY]: raise ValueError('Expected exactly one corrected mapping')
        am={k:json.loads(v) for k,v in a.execute('SELECT * FROM metadata')}
        bm={k:json.loads(v) for k,v in b.execute('SELECT * FROM metadata')}
        expected=dict(am,inputs=dict(am['inputs'],**{'mappings.jsonl':MAPPING_SHA}))
        if bm!=expected: raise ValueError('Unexpected metadata change')
    return dict(rows_compared=counts,changed_mapping_ids=changed,
                changed_mapping_fields=['search_status','source_refs'],
                changed_metadata=['inputs.mappings.jsonl'],all_other_records_identical=True)


def verify(before, after):
    if digest_file(before)!=BASE_SHA: raise ValueError('Expected exact public preview.1 baseline')
    return dict(format='corrected-portable-verification-v1',baseline_sha256=BASE_SHA,
                revised_sha256=digest_file(after),**compare_records(before,after))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline');p.add_argument('corrected');p.add_argument('--output',required=True)
    args=p.parse_args();write_json(args.output,verify(args.baseline,args.corrected))
