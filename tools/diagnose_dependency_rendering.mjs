// Diagnostic only: deliberately observe engine behavior on known invalid inputs.
// This does not bypass the production renderer's dependency checks.
import fs from 'node:fs';
import crypto from 'node:crypto';
import { Kage, Polygons } from '@kurgm/kage-engine';

const [input, output] = process.argv.slice(2);
if (!input || !output) throw new Error('Usage: input.json output.json');
const version = JSON.parse(fs.readFileSync('node_modules/@kurgm/kage-engine/package.json','utf8')).version;
if (version !== '0.7.0') throw new Error('Expected pinned engine 0.7.0');
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const raw = fs.readFileSync(input);
const rows = JSON.parse(raw);
const results = rows.map(row => {
  const kage = new Kage();
  kage.kUseCurve = false;
  const missing = [];
  kage.kBuhin.onMissing = name => { missing.push(name); };
  for (const [name, glyph] of Object.entries(row.bundle.glyphs)) kage.kBuhin.push(name, glyph.data);
  const result = {entity_id: row.entity_id, candidate: row.candidate,
    dependency_status: row.bundle.dependency_status,
    raw_glyph_hashes: Object.fromEntries(Object.entries(row.bundle.glyphs).map(([name,g]) => [name,sha(g.data)]))};
  try {
    const strokes = kage.getEachStrokes(row.bundle.glyphs[row.bundle.root].data);
    result.expanded_strokes = strokes.length;
    result.strokes_with_nonfinite_fields = strokes.filter(s => Object.values(s).some(v => typeof v === 'number' && !Number.isFinite(v))).length;
    const polygons = new Polygons();
    kage.makeGlyph(polygons, row.bundle.root);
    const points = polygons.array.flatMap(p => p.array);
    result.polygon_count = polygons.array.length;
    result.nonfinite_output_points = points.filter(p => !Number.isFinite(p.x) || !Number.isFinite(p.y)).length;
    result.svg_sha256 = sha(polygons.generateSVG());
    result.engine_result = polygons.array.length ? 'nonempty_output' : 'empty_output';
  } catch (error) {
    result.engine_result = 'exception'; result.error = String(error);
  }
  result.missing_lookups = [...new Set(missing)].sort();
  const invalid = row.findings.map(f => f.issue).filter(i => i.reason === 'invalid_kage_command');
  if (invalid.length) {
    // Counterfactual in memory only. Never export this as replacement KAGE.
    const alternative = new Kage(); alternative.kUseCurve = false;
    for (const [name,glyph] of Object.entries(row.bundle.glyphs)) {
      const lines = glyph.data.split('$');
      const omitted = invalid.filter(i => i.reference === glyph.reference);
      for (const issue of omitted) {
        if (lines[issue.line-1] !== issue.raw) throw new Error('Finding does not match pinned raw data');
      }
      alternative.kBuhin.push(name,lines.filter((_,i)=>!omitted.some(f=>f.line===i+1)).join('$'));
    }
    try {
      const polygons = new Polygons(); alternative.makeGlyph(polygons,row.bundle.root);
      result.counterfactual_omission = {policy:'Diagnostic omission only, not an approved repair',
        svg_sha256:sha(polygons.generateSVG()),polygon_count:polygons.array.length,
        same_svg_as_original:sha(polygons.generateSVG())===result.svg_sha256};
    } catch(error) { result.counterfactual_omission = {error:String(error)}; }
  }
  return result;
});
const sources = ['kage.js','buhin.js','stroke.js','font/mincho/index.js'];
const report = {format:'dependency-engine-diagnostic-v1',engine:'@kurgm/kage-engine@0.7.0',
  input_sha256:sha(raw),engine_source_sha256:Object.fromEntries(sources.map(name => [name,sha(fs.readFileSync('node_modules/@kurgm/kage-engine/lib/esm/'+name))])),
  policy:'Known invalid inputs observed without repair; no dependency, mapping or equivalence status changes. Nonfinite stroke fields include unused coordinates and are not independently a validity judgment.',results};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(results.map(({candidate,engine_result,polygon_count,strokes_with_nonfinite_fields,missing_lookups})=>({candidate,engine_result,polygon_count,strokes_with_nonfinite_fields,missing_lookups})),null,2));
