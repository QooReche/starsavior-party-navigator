'use strict';
const assert=require('node:assert/strict'),{stats,wilson,comparison}=require('../tools/evaluate_guild_time');
const a={scores:[10,20,30,40,50,60,70,80,90,100],clears:[0,0,0,0,0,0,0,0,1,1]};a.summary=stats(a.scores,a.clears);
assert.deepEqual(a.summary,{top:95,mean:55,clear:.2,n:10});
const same=comparison(a,a,100);assert.deepEqual(same.ci95,{topRatio:[1,1],meanRatio:[1,1],clearDifference:[0,0]});
const b={scores:a.scores.map(x=>x*.5),clears:a.clears.map(()=>0)};b.summary=stats(b.scores,b.clears);
assert.deepEqual(comparison(a,b,100).ci95.topRatio,[.5,.5]);assert.equal(comparison(a,b,100).point.clearDifference,-.2);
assert(wilson(0,1000)[1]<.004);assert(wilson(1,1000)[0]>.996);
assert.throws(()=>comparison(a,{...b,scores:[1]}),/length/);
// The tail mean must be recomputed per draw, not treated as a mean of all games.
assert.notEqual(a.summary.top,a.summary.mean);
const mutant=eval('('+stats.toString().replace('Math.ceil(n*.2-1e-9)','n')+')');
assert.throws(()=>assert.deepEqual(mutant(a.scores,a.clears),a.summary),assert.AssertionError);
(async()=>{
 const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),GS=require('../guild_search'),{instrument}=require('../tools/measure_guild_time');
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'guild-measure-')),original=GS.runPhase;
 let sent=0;
 GS.runPhase=o=>{const result={};for(const j of o.jobs){sent++;result[j.key]={prog:1,clear:1,n:o.runs,progs:Array(o.runs).fill(1),via:{coop:1},cosmo:null};o.onResult?.(j.key,result[j.key]);}return {promise:Promise.resolve(result),cancel(){}};};
 const opts={jobs:[{key:'synthetic',party:{units:[]},options:{}}],runs:2,seed:1,stage:'synthetic'};
 try{
  let t=instrument(dir,{synthetic:1});await GS.runPhase(opts).promise;assert(!t.summary().resumed);t.close();
  fs.appendFileSync(path.join(dir,'events.jsonl'),'{"torn":');
  t=instrument(dir,{synthetic:1});const resumed=await GS.runPhase(opts).promise;assert(t.summary().resumed);assert.equal(sent,1);assert.equal(resumed.synthetic.prog,1);assert.equal(resumed.synthetic.via.coop,1);assert.deepEqual(resumed.synthetic.progs,[1,1]);t.close();
  assert.throws(()=>instrument(dir,{synthetic:2}),/mismatch/);
  t=instrument(dir,{synthetic:1});await GS.runPhase({...opts,seed:2}).promise;assert.equal(sent,2,'different seed must not reuse a result');t.close();
 }finally{GS.runPhase=original;fs.rmSync(dir,{recursive:true,force:true});}
 console.log('PASS guild holdout score/tail/Wilson/paired interval, tail mutation, journal recovery/pins/seed isolation');
})().catch(e=>{console.error(e);process.exitCode=1;});
