// Synthetic battle-input duplicate audit; no private account data or engine runs.
'use strict';
const assert=require('node:assert/strict');
const C=require('../cosmo_search'),G=require('../data/cosmo_raid.json');
const roster=Array.from({length:13},(_,i)=>({key:'u'+String(i).padStart(2,'0'),cls:['캐스터','디펜더','서포터'][i%3],el:i%2?'sun':'moon'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:1000-i*13,stats:{hp:100+i*21,def:i*10,spd:i*5},combat:{}}]));
const battleKey=(m,t)=>JSON.stringify([m.base,m.stage,m.seed,m.n_runs,m.options,t.party,t.options]);
async function capture(profile,learned=true,extra={}){
 const S=structuredClone(G.search);
 S.learned={...S.learned,value:learned,S:40,m:1,K:40,M:1,A:8,overlapStarts:2,overlapKeep:2,epochs:3,minCorrelation:-1,missThreshold:1};
 S.screen={runs:2,firstRuns:1,passFrac:.1,passMinMult:1};S.rerank={keep:20,runs:3};S.final.runs=4;S.combine={topTriples:2,show:2};
 const requests=[],started=performance.now();
 const out=await C.search({S,bosses:G.season.bossOrder,results:profile,roster,mode:'top',level:-1,levelMax:2,breaks:[{name:'cube',level:3}],workers:1,stage:'synthetic-cosmo',base:'',sampleSeed:20261119,
 makeWorker:()=>({terminate(){},postMessage(m){for(const t of m.teams)requests.push({key:battleKey(m,t),seed:m.seed,runs:m.n_runs});setImmediate(()=>{
  for(const t of m.teams){const level=t.options.cosmo_raid.level,ks=t.party.units.map(u=>u.key),bi=G.season.bossOrder.indexOf(t.options.cosmo_raid.boss);
   const v=100+ks.reduce((a,k,i)=>a+((Number(k.slice(1))*17+bi*37)%113)*(i+1),0)-Math.abs(level-1)*3+(t.options.break_skill?7:0)+ks.reduce((a,k)=>a+profile[k].stats.hp,0)/100;
   this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{prog:.8,progs:Array(m.n_runs).fill(.8),via:{coop:1},n:m.n_runs,cosmo:{top:v,mean:v-2,clear:.5,frac:.8}}}});
  }this.onmessage({data:{type:'done',id:m.id}});
 });}}),...extra});
 assert(out.rows.length&&out.rows[0].sum>0);
 return {requests,out,ms:performance.now()-started};
}
async function audit(){
 const changed=structuredClone(results);changed.u00.stats.hp+=100;
 const allChanged=structuredClone(results);for(const r of Object.values(allChanged))r.stats.hp+=100;
 const report=[];
 for(const learned of [false,true]){
  const battles=new Map(),before=await capture(results,learned,{battles}),keys=new Set(before.requests.map(r=>r.key));
  const same=await capture(results,learned),after=await capture(changed,learned),all=await capture(allChanged,learned);
  const reused=await capture(changed,learned,{battles}),replay=await capture(results,learned,{battles});
  assert.deepEqual(reused.out,after.out);assert.deepEqual(replay.out,before.out);
  const count=r=>r.requests.filter(j=>keys.has(j.key)).length;
  const row={learned,beforeJobs:before.requests.length,withinSearchDuplicates:before.requests.length-keys.size,
   identicalReplayJobs:count(same),oneUnitChangedJobs:after.requests.length,oneUnitChangedDuplicates:count(after),
   allUnitsChangedDuplicates:count(all),afterReuseJobs:reused.requests.length,replayReuseJobs:replay.requests.length,
   beforeMs:+before.ms.toFixed(1),repeatMs:+same.ms.toFixed(1),replayReuseMs:+replay.ms.toFixed(1),grownMs:+after.ms.toFixed(1),grownReuseMs:+reused.ms.toFixed(1)};
  assert.equal(row.withinSearchDuplicates,0);assert.equal(row.identicalReplayJobs,row.beforeJobs);
  assert(row.oneUnitChangedDuplicates>0);assert.equal(row.allUnitsChangedDuplicates,0);report.push(row);
 }
 return report;
}
if(require.main===module)audit().then(x=>console.log(JSON.stringify(x,null,2))).catch(e=>{console.error(e);process.exitCode=1;});
module.exports={battleKey,capture,audit,results,roster};
