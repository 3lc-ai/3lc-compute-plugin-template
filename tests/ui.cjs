// Copyright 2026 3LC Inc.
// SPDX-License-Identifier: Apache-2.0
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(new URL('../src/tlc_plugin_template/ui.html', 'file://' + __filename.replace(/\\/g, '/')), 'utf8');
const source = html.match(/<script>([\s\S]*?)<\/script>/)[1];
async function test() {
  const button = {}, output = {}, callbacks = []; let respond;
  const API = {lifecycle:{onDispose: fn => callbacks.push(fn)}, compute:{request: path => {
    assert.equal(path, '/api/plugins/template/compute?greeting=hi');
    return new Promise((resolve,reject) => {respond = {resolve,reject};});
  }}};
  const EL = {querySelector: selector => selector === '#template-go' ? button : output};
  vm.runInNewContext(source, {window:{PLUGIN_API:API}, document:{currentScript:{closest: () => EL}}});
  const success = button.onclick(); assert.equal(button.disabled, true);
  respond.resolve({json: async () => ({message:'hello'})}); await success;
  assert.match(output.textContent, /hello/); assert.equal(button.disabled, false);
  const failure = button.onclick(); respond.reject(new Error('Permission refused')); await failure;
  assert.equal(output.textContent, 'Permission refused'); assert.equal(button.disabled, false);
  const pending = button.onclick(); callbacks.forEach(fn => fn());
  const before = output.textContent;
  respond.resolve({json: async () => ({message:'late'})}); await pending;
  assert.equal(button.onclick, null); assert.equal(output.textContent, before);
  vm.runInNewContext(source, {window:{PLUGIN_API:{}}, document:{currentScript:{closest: () => EL}}});
  assert.equal(button.disabled, true); assert.match(output.textContent, /Update your Compute/);
  console.log('template success, error, disposal and older-host fallback tests passed');
}
test().catch(error => {console.error(error); process.exitCode=1;});
