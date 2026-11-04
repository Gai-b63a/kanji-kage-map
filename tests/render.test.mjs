import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

test('renderer distinguishes finite output from dependency and empty-output failures', () => {
  const parent = path.resolve('.cache/tests');
  fs.mkdirSync(parent, {recursive:true});
  const dir = fs.mkdtempSync(path.join(parent, 'render-'));
  const input = path.join(dir, 'input.json');
  const output = path.join(dir, 'output.json');
  const bundle = {root:'root@1',dependency_status:'complete',glyphs:{'root@1':{data:'1:0:0:20:100:180:100'}}};
  fs.writeFileSync(input, JSON.stringify([
    {glyph:'valid',bundle,keep_artifact:false},
    {glyph:'unresolved',bundle:{...bundle,dependency_status:'issues'}},
    {glyph:'empty',bundle:{...bundle,glyphs:{'root@1':{data:'0:0:0'}}}}
  ]));
  const run = spawnSync(process.execPath,['tools/render_bundles.mjs',input,output],{encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);
  const rows = JSON.parse(fs.readFileSync(output,'utf8'));
  assert.deepEqual(rows.map(r=>r.render_status),['finite_nonempty','failed','failed']);
  assert.equal(rows[0].review_status,'unreviewed');
  assert.equal(rows[0].contours,undefined);
  assert.equal(rows[0].svg_sha256.length,64);
  // Each test-created file is known and contained in the workspace.
  fs.unlinkSync(input);fs.unlinkSync(output);fs.rmdirSync(dir);
});
