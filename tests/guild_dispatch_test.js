'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const GS=require('../guild_search'),Planner=require('../guild_planner'),G=require('../data/guild_defense.json'),V=require('../guild_view');
const roster=Array.from({length:7},(_,i)=>({key:'u'+i,cls:i%2?'캐스터':'서포터'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:1000-i,stats:{hp:1000,atk:100,def:100,spd:100},combat:{}}]));
async function run(planner,chunk,workers=2,cancel=false){
 const S=structuredClone(G.search);S.newSearch=true;S.execution={chunk};S.screen.runs=2;S.screen2={keep:5,runs:3};S.finalists=2;S.final={runs:8,levels:[4,8],supports:['fire','gust']};
 Object.assign(S.learned,{S:12,m:1,K:12,M:1,A:4,epochs:3,minCorrelation:-1,missThreshold:1});
 const trace=[],phases=[],phaseOriginal=GS.runPhase;let active=0,max=0,serial=0,phaseIndex=-1;
 GS.runPhase=o=>{const phase={jobs:o.jobs,runs:o.runs,seed:o.seed,workers:new Set()};phaseIndex=phases.length;phases.push(phase);const h=phaseOriginal(o);return {...h,promise:h.promise.then(r=>{phase.result=r;return r})};};
 try{
  const out=await planner.search({S,G,V,roster,results,tiers:[0,0,0,0],breaks:[{name:'스타피어서',level:1}],workers,stage:'synthetic',base:'',
   onHandle:h=>{if(cancel&&phases.at(-1).seed===6)h.cancel()},
   makeWorker(){const id=serial++;active++;max=Math.max(active,max);let dead=false;return {terminate(){if(!dead){dead=true;active--}},postMessage(m){const phase=phases[phaseIndex];phase.workers.add(id);trace.push(m);
    setTimeout(()=>{if(dead)return;for(const t of m.teams){const mix=t.party.units.reduce((n,u)=>n+Number(u.key.slice(1)),0),v=.55+(mix%5)*.04+t.options.guild.level*.002+(t.options.guild.support==='gust'?.03:0);
     const progs=Array.from({length:m.n_runs},(_,i)=>i%3===0?1:v);
     this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{n:m.n_runs,prog:progs.reduce((a,b)=>a+b,0)/progs.length,progs,clear:progs.filter(p=>p===1).length/progs.length,via:{forced_coop:1}}}});
    }this.onmessage({data:{type:'done',id:m.id}});},id%2?1:3);
   }};}});
  assert.equal(active,0);assert(max<=workers);assert(out.rows.length&&out.rows.every(r=>r.prog>0));assert.equal(out.dropped,0);assert.equal(out.pool,roster.length);
  assert(phases.some(p=>p.seed===6&&p.jobs.length===2),'must exercise two-job precision phase');
  for(const p of phases.filter(p=>p.seed===6))assert.equal(p.workers.size,chunk===1?workers:1,'precision phase must use available workers');
  const normalize=()=>JSON.parse(JSON.stringify({out,phases:phases.map(({workers,...p})=>({...p,result:Object.fromEntries(Object.entries(p.result).sort(([a],[b])=>a.localeCompare(b)))}))}));
  return normalize();
 }finally{GS.runPhase=phaseOriginal;assert.equal(active,0,'workers survive completion/cancellation');}
}
(async()=>{
 assert.equal(G.search.execution.chunk,1);
 const before=await run(Planner,8),after=await run(Planner,1);assert.deepEqual(after,before,'same candidates, seeds, runs, progs/via and complete output');
 assert.deepEqual(await run(Planner,1,1),before);await assert.rejects(()=>run(Planner,1,2,true),/취소/);
 const source=fs.readFileSync(require.resolve('../guild_planner'),'utf8'),anchor='chunk:S.execution?.chunk||8';assert(source.includes(anchor));
 const ctx={module:{exports:{}},require:n=>require('../'+n),setTimeout,performance};vm.runInNewContext(source.replace(anchor,'chunk:8'),ctx);
 await assert.rejects(()=>run(ctx.module.exports,1),/available workers/);
 console.log('PASS guild chunk 1/8 complete phase/result equality, positive progress, both workers, one worker, cancellation, idle regression mutation');
})().catch(e=>{console.error(e);process.exitCode=1;});
