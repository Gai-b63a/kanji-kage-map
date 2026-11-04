"""Apply an explicitly requested scoped override to an offline lookup."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.overrides import read_overrides, apply_override
from kanji_kage_map.release import lookup_release
from kanji_kage_map.sources import write_json

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dataset');p.add_argument('overrides');p.add_argument('override_id');p.add_argument('--output',required=True)
    args=p.parse_args();history=read_overrides(args.overrides)
    row=next((r for r in history['history'] if r['override_id']==args.override_id),None)
    if row is None: raise ValueError('Unknown override ID')
    result=lookup_release(args.dataset,row['review']['entity_id'])
    selected=apply_override(result,history,args.override_id)
    if row['action']=='select':
        selected=apply_override(lookup_release(args.dataset,row['review']['entity_id'],row['review']['glyph_reference'].rsplit('@',1)[0]),history,args.override_id)
    write_json(args.output,selected)
