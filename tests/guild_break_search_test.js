// Production learned guild planner: real result fields, layout/support/break interaction, cancellation.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const GS=require('../guild_search'),Planner=require('../guild_planner'),P=require('../party_placement'),V=require('../guild_view'),G=require('../data/guild_defense.json');
const roster=Array.from({length:8},(_,i)=>({key:'u'+i,cls:i===0?'서포터':'캐스터'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:100-i,stats:{hp:100-i,def:0,spd:10+i}}]));
const skill={name:'큐브 과부하',level:7};
async function run(planner=Planner,{missing=false,cancel=false,experimental=true}={}){
 const S=structuredClone(G.search);S.newSearch=true;S.placement={...S.placement,baseline:experimental,enabled:experimental};Object.assign(S.learned,{S:70,m:1,K:70,M:1,A:10,epochs:3,minCorrelation:-1,missThreshold:1});
 S.screen2={keep:20,runs:3};S.finalists=2;S.final.runs=4;S.final.supports=['none','fire','gust'];
 let created=0,closed=0,stop=false;const sent=[];
 const out=await planner.search({S,G,V,roster,results,tiers:[0,0,0,0],breaks:[skill],workers:1,stage:'guild',base:'',stale:()=>stop,
 onPhase:msg=>{if(cancel&&msg.includes('결합 비교'))stop=true;},
 makeWorker:()=>{created++;return {terminate(){closed++;},postMessage(m){sent.push(m);setImmediate(()=>{
  for(const t of m.teams){if(missing)continue;const k=t.party.units.map(u=>u.key),g=t.options.guild,b=t.options.break_skill;
   const tactical=k.slice(0,2).includes('u0')&&k[t.party.leader]==='u3'&&g.level===5&&g.support==='fire'&&b?.name===skill.name&&b.level===7;
   const prog=tactical?1:k.includes('u0')&&k.includes('u3')?.6:.5,progs=Array(m.n_runs).fill(prog);
   this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{n:m.n_runs,prog,progs,clear:tactical?1:0,via:{forced_coop:2}}}});
  }this.onmessage({data:{type:'done',id:m.id}});
 });}};}}).finally(()=>assert.equal(closed,created,'workers returned on success/error/cancel'));
 assert.equal(created,1,'one worker');return {out,sent};
}
async function check(planner=Planner){const {out,sent}=await run(planner),best=out.rows[0];
 assert.equal(best.brk,skill.name);assert.equal(best.brkLv,7);assert.equal(best.leaderKey,'u3');assert.equal(best.level,5);assert.equal(best.sup,'fire');assert(best.prog>0);assert.equal(out.pool,8);
 assert(sent.some(m=>m.teams.some(t=>t.options.break_skill===null)));assert(sent.some(m=>m.teams.some(t=>t.options.guild.level===0)));
 assert(sent.some(m=>m.seed===9&&m.n_runs===4));return out;
}
(async()=>{
 const defaults=await run(Planner,{experimental:false}),cls0=Object.fromEntries(roster.map(r=>[r.key,r.cls]));
 assert(defaults.out.rows.length&&defaults.out.rows[0].prog>0);
 for(const m of defaults.sent)for(const t of m.teams){const keys=t.party.units.map(u=>u.key);assert.deepEqual(t.party,GS.party(keys,results,cls0).spec);}
 assert(defaults.sent.some(m=>m.teams.some(t=>t.options.guild.support==='fire'&&t.options.break_skill?.name===skill.name)),'off still compares support and break together');
 await check();await assert.rejects(()=>run(Planner,{missing:true}),/누락/);await assert.rejects(()=>run(Planner,{cancel:true}),/취소/);
 const keys=roster.slice(0,4).map(r=>r.key),cls=Object.fromEntries(roster.map(r=>[r.key,r.cls])),layout={order:keys,leaderKey:'u3'};
 const jobs=GS.breakJobs([{keys,...layout,level:0,sup:'fire'}],[skill,{...skill,level:8}],results,cls,[]);
 assert.equal(jobs.length,6);assert.equal(new Set(jobs.map(j=>j.key)).size,6);assert(jobs.every(j=>j.leaderKey==='u3'));
 const src=fs.readFileSync(require.resolve('../guild_planner'),'utf8');assert(src.includes('break_skill:brk'));
 const context={module:{exports:{}},require:n=>require('../'+n.replace('./',''))};
 vm.runInNewContext(src,context);await check(context.module.exports);
 vm.runInNewContext(src.replace('break_skill:brk','break_skill:null'),context);await assert.rejects(()=>check(context.module.exports));
 console.log('PASS guild learned planner, leader/layout/support/break, per-run score, coop retained, workers/cancel/missing, break mutation');
})().catch(e=>{console.error(e);process.exitCode=1;});
