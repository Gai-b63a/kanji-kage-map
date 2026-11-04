// Observe pinned engine adjustment stages without changing production inputs.
import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {Kage,Polygons} from '@kurgm/kage-engine';
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const [input,output]=process.argv.slice(2);
if(!input||!output)throw new Error('Usage: bundles.json report.json');
assert.equal(JSON.parse(fs.readFileSync('node_modules/@kurgm/kage-engine/package.json')).version,'0.7.0');
const stages=['adjustHane','adjustMage','adjustTate','adjustKakato','adjustUroko','adjustUroko2','adjustKirikuchi'];
function inspect(data,glyphs={}){
  const kage=new Kage();kage.kUseCurve=false;
  for(const [name,g] of Object.entries(glyphs))kage.kBuhin.push(name,g.data);
  const captured={};
  for(const stage of stages){
    const original=kage.kFont[stage].bind(kage.kFont);
    kage.kFont[stage]=rows=>{
      const result=original(rows);
      captured[stage]=rows.map(({stroke,...adjustments})=>adjustments);
      // Copy values now: later stages mutate the same adjustment objects.
      captured[stage]=structuredClone(captured[stage]);
      return result;
    };
  }
  const strokes=kage.getEachStrokes(data);
  const polygons=new Polygons();kage.makeGlyph2(polygons,data);
  const last=strokes.at(-1);
  return {captured,strokes:strokes.length,polygon_count:polygons.array.length,svg_sha256:hash(polygons.generateSVG()),
    last_command_is_nan:Number.isNaN(last.a1_100),last_control_segments:last.getControlSegments().map(s=>s.map(v=>Number.isNaN(v)?'NaN':v)),
    last_crosses_distant_segment:last.isCross(1000,1000,1100,1000)};
}
function compare(original,omitted){
  assert.equal(original.strokes,omitted.strokes+1);
  const differences=[];
  for(const stage of stages){
    for(let i=0;i<omitted.strokes;i++){
      const a=original.captured[stage][i],b=omitted.captured[stage][i];
      for(const key of Object.keys(a))if(!Object.is(a[key],b[key]))differences.push({stage,expanded_stroke_index:i,field:key,with_invalid:a[key],without_invalid:b[key]});
    }
  }
  return {original,omitted,differences,same_svg:original.svg_sha256===omitted.svg_sha256};
}
const bytes=fs.readFileSync(input);const row=JSON.parse(bytes).find(r=>r.candidate==='hkcs_m28eb6@1');
assert.ok(row);
const data=row.bundle.glyphs[row.bundle.root].data;assert.ok(data.endsWith('$s'));
const actual=compare(inspect(data,row.bundle.glyphs),inspect(data.slice(0,-2),row.bundle.glyphs));
const minimal=compare(inspect('1:0:0:20:100:180:100$s'),inspect('1:0:0:20:100:180:100'));
assert.equal(actual.same_svg,false);assert.equal(minimal.same_svg,false);
assert.equal(minimal.original.last_command_is_nan,true);
assert.equal(minimal.original.last_crosses_distant_segment,true);
const sources=['kage.js','stroke.js','2d.js','font/mincho/index.js'];
for(const comparison of [actual,minimal]){
  delete comparison.original.captured;
  delete comparison.omitted.captured;
}
fs.writeFileSync(output,JSON.stringify({format:'invalid-command-adjustment-trace-v1',engine:'@kurgm/kage-engine@0.7.0',
  input_sha256:hash(bytes),sources:Object.fromEntries(sources.map(p=>[p,hash(fs.readFileSync('node_modules/@kurgm/kage-engine/lib/esm/'+p))])),
  candidate:row.candidate,actual,minimal,policy:'Diagnostic counterfactual only. No KAGE repair or glyph-equivalence determination.'},null,2)+'\n');
console.log(JSON.stringify({actual_differences:actual.differences,minimal_differences:minimal.differences},null,2));
