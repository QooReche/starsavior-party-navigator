// Complete wire requests supplement the phase/result golden, using an immutable harness.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const vm=require('node:vm'),cp=require('node:child_process'),zlib=require('node:zlib');
const {createRequire}=require('node:module'),{oldModules}=require('../tools/measure_role_search');
const {normalize}=require('./search_freeze_test');
const root=path.resolve(__dirname,'..'),ref='6688d7a';
const fixture=path.join(__dirname,'fixtures/search_cosmo_trace_6688d7a.json.gz');
const filename=path.join(__dirname,'search_defaults_test.js');
const original=cp.execFileSync('git',['show',ref+':tests/search_defaults_test.js'],{cwd:root,encoding:'utf8'}).split('(async()=>')[0];
assert.equal(original.split('return {out:plain(out),jobs:').length,2);
assert.equal(original.split('postMessage(m){trace.push').length,2);
const source=original.replace('return {out:plain(out),jobs:','return {trace:plain(trace),out:plain(out),jobs:')
 .replace('postMessage(m){trace.push','postMessage(m){m=alter(m);trace.push');
const harness=vm.runInThisContext('(function(require,alter){'+source+'\nreturn {check};})',{filename});
async function capture(mod,alter=m=>m){const {check}=harness(createRequire(filename),alter);const {trace,out}=await check(mod);return normalize({trace,out});}
(async()=>{
 if(process.argv.includes('--capture')){
  assert.equal(cp.execFileSync('git',['diff',ref,'--','data/cosmo_raid.json','data/guild_defense.json','ui_shared.js','party_placement.js','placement_search.js'],{cwd:root,encoding:'utf8'}),'','shared baseline dependencies changed');
  fs.writeFileSync(fixture,zlib.gzipSync(JSON.stringify(await capture(oldModules(ref).C))));
 }
 const expected=JSON.parse(zlib.gunzipSync(fs.readFileSync(fixture)));
 const actual=await capture(require('../cosmo_search'));
 assert.deepEqual(actual,expected);
 assert(actual.trace.length>1&&actual.trace.every(m=>m.teams.length&&m.n_runs>0));
 // Rerun the actual search with mutations at its worker transport boundary.
 for(const mutate of [
  m=>({...m,stage:'wrong-stage'}),
  m=>({...m,options:{...m.options,unsupported_option:true}}),
  m=>({...m,teams:[...m.teams].reverse()}),
  m=>({...m,seed:m.seed+1})
 ]){const bad=await capture(require('../cosmo_search'),mutate);assert.throws(()=>assert.deepEqual(bad,expected));}
 console.log('PASS full cosmo wire golden: immutable 6688d7a harness, requests/results/order and 4 mutations');
})().catch(e=>{console.error(e);process.exitCode=1;});
