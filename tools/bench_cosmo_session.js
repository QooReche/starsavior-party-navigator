// Page-level synthetic S2 benchmark. Workers perform real harness work without
// artificial boot delays; this measures JS orchestration, not browser/Pyodide boot.
'use strict';
const assert=require('node:assert/strict'),cp=require('node:child_process'),path=require('node:path'),os=require('node:os');
const {performance}=require('node:perf_hooks');
const {setup,search}=require('../tests/cosmo_session_test');
const root=path.resolve(__dirname,'..'),baseline='80e449a';
const beforeSources=Object.fromEntries([['templateSource','party_template.html'],['cosmoSource','cosmo_search.js']]
  .map(([key,file])=>[key,cp.execFileSync('git',['-c','safe.directory='+root,'show',baseline+':'+file],{cwd:root,encoding:'utf8'})]));
const median=values=>[...values].sort((a,b)=>a-b)[Math.floor(values.length/2)];
const rounded=n=>+n.toFixed(3);
async function trial(before){
  const h=setup(before?beforeSources:{}),out={};
  try{
    for(const name of ['first','repeat','changed']){
      if(name==='changed')h.c.CSR.optMode='top';
      const created=h.life.created,requests=h.life.requests,start=performance.now();
      const rows=await search(h.c),ms=performance.now()-start;
      out[name]={ms,created:h.life.created-created,requests:h.life.requests-requests,rows};
      assert.equal(out[name].created,before||name==='first'?1:0,name+' worker creation delta');
      assert(out[name].requests>0,'S2 benchmark must still dispatch real battle jobs');
    }
    assert.deepEqual(out.repeat.rows,out.first.rows,'same-input restart preserves exact results');
    assert.equal(h.life.max,1,'only one worker pool resides at any point');
    assert.equal(h.life.active,before?0:1,'only session implementation retains completed worker');
    return out;
  }finally{h.close();assert.equal(h.life.active,0,'benchmark releases all workers');}
}
function compare(before,after){
  for(const name of ['first','repeat','changed']){
    assert.deepEqual(after[name].rows,before[name].rows,name+' exact baseline result');
    assert.equal(after[name].requests,before[name].requests,name+' battle dispatch count unchanged');
  }
}
async function main(){
  const freeGB=os.freemem()/1024**3;
  assert(freeGB>=6,'benchmark requires at least 6 GiB available memory');
  compare(await trial(true),await trial(false)); // One discarded warmup per version.
  const samples={before:[],after:[]};
  for(let i=0;i<5;i++){
    let before,after;
    if(i%2===0){before=await trial(true);after=await trial(false);}
    else{after=await trial(false);before=await trial(true);}
    compare(before,after);samples.before.push(before);samples.after.push(after);
  }
  const summarize=version=>Object.fromEntries(['first','repeat','changed'].map(name=>[name,{
    medianMs:rounded(median(samples[version].map(s=>s[name].ms))),
    samplesMs:samples[version].map(s=>rounded(s[name].ms)),
    created:samples[version].map(s=>s[name].created),requests:samples[version][0][name].requests
  }]));
  console.log(JSON.stringify({baseline,fixture:{units:12,bosses:3,workers:1,learned:false},
    warmupsPerVersion:1,measuredPairs:5,freeGiB:rounded(freeGB),
    before:summarize('before'),after:summarize('after'),
    exactResults:true,identicalBattleDispatchCounts:true,
    scope:'Synthetic page/search orchestration; no artificial worker delay or real engine boot.'},null,2));
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={trial,compare};
