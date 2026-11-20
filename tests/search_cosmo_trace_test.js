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
const source=original.replace('return {out:plain(out),jobs:','return {trace:plain(trace),out:plain(out),jobs:');
const {check}=vm.runInThisContext('(function(require){'+source+'\nreturn {check};})',{filename})(createRequire(filename));
async function capture(mod){const {trace,out}=await check(mod);return normalize({trace,out});}
(async()=>{
 if(process.argv.includes('--capture'))fs.writeFileSync(fixture,zlib.gzipSync(JSON.stringify(await capture(oldModules(ref).C))));
 const expected=JSON.parse(zlib.gunzipSync(fs.readFileSync(fixture)));
 const actual=await capture(require('../cosmo_search'));
 assert.deepEqual(actual,expected);
 assert(actual.trace.length>1&&actual.trace.every(m=>m.teams.length&&m.n_runs>0));
 // Real transport mutations: stage/global options, batch boundaries, dispatch order.
 for(const mutate of [
  x=>{x.trace[0].stage='wrong-stage';},
  x=>{x.trace[0].options={...x.trace[0].options,unsupported_option:true};},
  x=>{const m=x.trace.find(m=>m.teams.length>1);assert(m);x.trace.push({...m,teams:m.teams.splice(1)});},
  x=>{[x.trace[0],x.trace[1]]=[x.trace[1],x.trace[0]];}
 ]){const bad=structuredClone(actual);mutate(bad);assert.throws(()=>assert.deepEqual(bad,expected));}
 console.log('PASS full cosmo wire golden: immutable 6688d7a harness, requests/results/order and 4 mutations');
})().catch(e=>{console.error(e);process.exitCode=1;});
