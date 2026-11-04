// SPDX-License-Identifier: GPL-3.0-only
// Optional review renderer; KAGE data retains its separate data license.
import fs from 'node:fs';
import crypto from 'node:crypto';
import { Kage, Polygons } from '@kurgm/kage-engine';

const [input, output] = process.argv.slice(2);
if (!input || !output) throw new Error('Usage: node tools/render_bundles.mjs input.json output.json');
const records = JSON.parse(fs.readFileSync(input, 'utf8'));
if (!Array.isArray(records) || !records.length) throw new Error('Non-empty bundle list required');
const rendered = records.map(record => {
  const bundle = record.bundle;
  try {
    if (bundle.dependency_status !== 'complete') throw new Error('Unresolved dependencies');
    const kage = new Kage();
    kage.kUseCurve = false;
    for (const [name, glyph] of Object.entries(bundle.glyphs)) kage.kBuhin.push(name, glyph.data);
    const polygons = new Polygons();
    kage.makeGlyph(polygons, bundle.root);
    const contours = polygons.array.map(p => p.array.map(({x,y}) => [x,y]));
    if (!contours.length || contours.some(p => p.some(v => v.some(n => !Number.isFinite(n))))) {
      throw new Error('Empty or non-finite polygon output');
    }
    const svg = polygons.generateSVG();
    return {...record, bundle: undefined, engine: '@kurgm/kage-engine@0.7.0',
      render_status: 'finite_nonempty', polygon_count: contours.length,
      svg_sha256: crypto.createHash('sha256').update(svg).digest('hex'),
      contours: record.keep_artifact === false ? undefined : contours,
      svg: record.keep_artifact === false ? undefined : svg,
      review_status: 'unreviewed'};
  } catch (error) {
    return {...record, bundle: undefined, render_status: 'failed', error: String(error), review_status: 'unreviewed'};
  }
});
fs.writeFileSync(output, JSON.stringify(rendered, null, 2) + '\n');
console.log(JSON.stringify({total:rendered.length, passed:rendered.filter(r=>r.render_status==='finite_nonempty').length}));
