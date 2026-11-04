"""Export unchanged bundles for the previously audited dependency findings."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.release import lookup_release
from kanji_kage_map.sources import write_json

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset');p.add_argument('--traces',default='docs/dependency-issue-traces.json');p.add_argument('--output',required=True)
    args=p.parse_args();trace=json.loads(Path(args.traces).read_text(encoding='utf-8'));rows=[]
    for row in trace['affected']:
        result=lookup_release(args.dataset,row['entity_id'],row['candidate'].rsplit('@',1)[0])
        if result['bundle']['root']!=row['candidate'] or result['bundle']['dependency_status']!='issues' or result['snapshot_sha256']!=trace['snapshot_sha256']:
            raise ValueError('Diagnostic bundle differs from fixed audit')
        rows.append(dict(entity_id=row['entity_id'],candidate=row['candidate'],bundle=result['bundle'],findings=row['evidence']))
    write_json(args.output,rows)
