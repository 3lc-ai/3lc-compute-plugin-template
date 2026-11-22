// Copyright 2026 3LC Inc.
// SPDX-License-Identifier: Apache-2.0
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
// The package is the one folder under src/ with a plugin.toml; the page's element ids and route
// start with the manifest's id, so a renamed plugin passes without editing this file.
const src = path.join(__dirname, '..', 'src');
const [pkg] = fs.readdirSync(src).filter(name => fs.existsSync(path.join(src, name, 'plugin.toml')));
const id = fs.readFileSync(path.join(src, pkg, 'plugin.toml'), 'utf8').match(/^id\s*=\s*"([^"]+)"/m)[1];
const html = fs.readFileSync(path.join(src, pkg, 'ui.html'), 'utf8');
const source = html.match(/<script>([\s\S]*?)<\/script>/)[1];
async function test() {
  const button = {}, output = {}, callbacks = []; let respond;
  const API = {protocol: 1, lifecycle:{onDispose: fn => callbacks.push(fn)}, http:{request: path => {
    assert.equal(path, `/api/plugins/${id}/compute?greeting=hi`);
    return new Promise((resolve,reject) => {respond = {resolve,reject};});
  }}};
  const EL = {querySelector: selector => ({[`#${id}-go`]: button, [`#${id}-out`]: output})[selector]};
  const document = {currentScript: {closest: selector => selector === `.${id}-plugin` ? EL : null}};
  vm.runInNewContext(source, {window:{PLUGIN_API:API}, document});
  const success = button.onclick(); assert.equal(button.disabled, true);
  respond.resolve({json: async () => ({message:'hello'})}); await success;
  assert.match(output.textContent, /hello/); assert.equal(button.disabled, false);
  const failure = button.onclick(); respond.reject(new Error('Permission refused')); await failure;
  assert.equal(output.textContent, 'Permission refused'); assert.equal(button.disabled, false);
  const pending = button.onclick(); callbacks.forEach(fn => fn());
  const before = output.textContent;
  respond.resolve({json: async () => ({message:'late'})}); await pending;
  assert.equal(button.onclick, null); assert.equal(output.textContent, before);
  vm.runInNewContext(source, {window:{PLUGIN_API:{}}, document});
  assert.equal(button.disabled, true); assert.match(output.textContent, /needs a newer 3LC Hub/);
  console.log(`${id} success, error, disposal and older-host fallback tests passed`);
}
test().catch(error => {console.error(error); process.exitCode=1;});
