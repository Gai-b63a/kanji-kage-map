"""Render every statically flagged candidate, keeping all audit states distinct."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.release import lookup_release
from kanji_kage_map.sources import write_json


def audit(dataset, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    source=Path('docs/syntax-candidate-impact.jsonl.gz')
    summary=json.loads(Path('docs/syntax-impact-summary.json').read_text(encoding='utf-8'))
    if digest_file(source)!=summary['output_sha256']:raise ValueError('Impact index changed')
    if json.loads(Path('node_modules/@kurgm/kage-engine/package.json').read_text())['version']!='0.7.0':raise ValueError('Expected pinned engine')
    with gzip.open(source,'rt',encoding='utf-8') as stream: impacts=[json.loads(line) for line in stream]
    records=[];seen=set()
    for row in impacts:
        key=(row['entity_id'],row['candidate'])
        if key in seen:raise ValueError('Duplicate impact record')
        seen.add(key)
        result=lookup_release(dataset,row['entity_id'],row['candidate'].rsplit('@',1)[0])
        if result['snapshot_sha256']!=summary['snapshot_sha256'] or result['bundle']['root']!=row['candidate']:raise ValueError('Snapshot or candidate changed')
        findings=result['static_syntax_audit']['findings']
        if {f['reference'] for f in findings}!=set(row['origin_references']) or {f['reason'] for f in findings}!=set(row['reachable_reasons']):raise ValueError('Static findings changed')
        if result['bundle']['dependency_status']!=row['dependency_status']:raise ValueError('Dependency status changed')
        records.append(dict(**row,bundle=result['bundle'],keep_artifact=False))
    if len(records)!=summary['counts']['affected_candidate_links']:raise ValueError('Impact population changed')
    inputs=output/'bundles.json';rendered=output/'rendered.json'
    write_json(inputs,records)
    subprocess.run(['node','tools/render_bundles.mjs',str(inputs),str(rendered)],check=True,timeout=1800)
    results=json.loads(rendered.read_text(encoding='utf-8'))
    if len(results)!=len(records):raise ValueError('Renderer dropped records')
    categories=Counter();by_reason={};details=[]
    for row,result in zip(records,results):
        if (row['entity_id'],row['candidate'])!=(result['entity_id'],result['candidate']):raise ValueError('Renderer changed identity')
        status='blocked_dependency' if result.get('error')=='Error: Unresolved dependencies' else result['render_status']
        categories[status]+=1
        for reason in row['reachable_reasons']:by_reason.setdefault(reason,Counter())[status]+=1
        details.append({**{k:result[k] for k in ['entity_id','candidate','dependency_status','reachable_reasons']},
                        'outcome':status,**{k:result[k] for k in ['polygon_count','svg_sha256','error'] if k in result}})
    detail_path=output/'results.jsonl.gz'
    with detail_path.open('wb') as destination,gzip.GzipFile(filename='',fileobj=destination,mode='wb',mtime=0) as packed:
        for row in details:packed.write((json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n').encode('utf-8'))
    report=dict(format='syntax-affected-render-audit-v1',dataset_sha256=digest_file(dataset),snapshot_sha256=summary['snapshot_sha256'],
                impact_sha256=digest_file(source),input_sha256=digest_file(inputs),renderer_sha256=digest_file('tools/render_bundles.mjs'),
                package_lock_sha256=digest_file('package-lock.json'),engine='@kurgm/kage-engine@0.7.0',
                candidate_links=len(results),entities=len({r['entity_id'] for r in records}),outcomes=dict(categories),
                outcomes_by_reason={k:dict(v) for k,v in sorted(by_reason.items())},results_sha256=digest_file(detail_path),
                limitation='Only statically flagged candidates. Existing dependency guard retained; finite nonempty output does not certify correctness or equivalence. Raw KAGE and mapping states unchanged.')
    write_json(output/'summary.json',report)
    print(dict(candidate_links=len(results),outcomes=dict(categories)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset');p.add_argument('--output',required=True)
    args=p.parse_args();audit(args.dataset,args.output)
