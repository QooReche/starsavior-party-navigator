const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const P=require('../party_placement'),GS=require('../guild_search'),C=require('../cosmo_search'),J=require('../placement_search');
const Direct=require('../direct_party'),CD=require('../cosmo_direct');
const keys=['a','b','c','d'],results={a:{power:99,stats:{hp:100,def:0,spd:1}},b:{power:1,stats:{hp:90,def:3000,spd:2}},c:{power:5,stats:{hp:80,def:0,spd:200}},d:{power:1,stats:{hp:70,def:9000,spd:3}}};
function candidates(p=P){assert.deepEqual(JSON.parse(JSON.stringify(p.baseline(keys,results))),{order:['d','b','a','c'],leaderKey:'c'});
  const all=p.all(keys),full=p.all(keys,true);assert.equal(all.length,24);assert.equal(full.length,96);
  assert.equal(new Set(all.map(x=>p.executionKey(keys,x))).size,24);
  assert.equal(new Set(full.map(x=>p.executionKey(keys,x))).size,96);
  for(const layout of full){const party=p.party(keys,results,layout);assert.equal(party.spec.units[party.spec.leader].key,layout.leaderKey);assert.deepEqual(party.order,layout.order);}
  const variants=p.variants(keys,results,{c:['stealth'],a:['taunt']});assert(variants.some(x=>x.order[0]==='c'));assert(variants.some(x=>x.order[0]==='a'));
  assert.deepEqual(JSON.parse(JSON.stringify(p.levels([{level:6,score:8},{level:6,score:7},{level:4,score:6}],8,[3]))),[2,3,4,6]);
}
candidates();
const control={module:{exports:{}}};vm.runInNewContext(fs.readFileSync(require.resolve('../party_placement'),'utf8'),control);candidates(control.module.exports);
const roster=keys.map((key,i)=>({key,cls:i%2?'캐스터':'디펜더'}));
assert.equal(GS.pool({newSearch:true,poolSize:1,minPowerRatio:1,minRole:{},excluded:keys,banCoop:true},results,roster).length,4);
assert.equal(GS.combos({newSearch:true,minFront:4,minDealer:4},roster).length,1);
assert(!GS.coopHit({newSearch:true,banCoop:true},{via:{coop:5,forced_coop:8}}));
const p=P.baseline(keys,results),job=C.bossJobs({topQ:.2},'x',3,[keys],results,{},null,p)[0];
assert.notEqual(job.key,C.bossJobs({topQ:.2},'x',3,[keys],results,{},null,{...p,leaderKey:'b'})[0].key);
assert.notEqual(C.jobKey('x',keys,3,{name:'cube',level:1},p),C.jobKey('x',keys,3,{name:'cube',level:2},p));
const triples=[{teams:[{keys,...p},{keys,...p},{keys,...p}]}],bosses=['x','y','z'];
const jobs=C.finalJobs({topQ:.2},triples,bosses,3,results,{}),res=Object.fromEntries(jobs.map(j=>[j.key,{cosmo:{mean:10,top:20,clear:1,frac:1}}]));
assert.equal(C.finalRank(triples,bosses,3,res,'top',1)[0].sum,60);
assert(C.finalRankBrk(triples,bosses,()=>3,[null],res,'top',1)[0].teams.every(t=>t.leaderKey==='c'));
// Search -> direct -> storage/share retains a rear-row leader and engine slots.
const season={id:1,levelMax:18,bosses:bosses.map(key=>({key}))};
let state=CD.fromSearch({teams:bosses.map((boss,i)=>({boss,keys:keys.map(k=>k+i),order:p.order.map(k=>k+i),leaderKey:'c'+i,level:3}))},season);
state=CD.restore(JSON.parse(JSON.stringify(CD.storage(state))),season);
assert.equal(state.teams.x.draft.leader,'c0');assert.deepEqual(state.teams.x.draft.slots.map(s=>s.key),p.order.map(k=>k+'0'));
let draft={v:1,slots:keys.map(key=>({key,grown:key==='a'})),leader:'a',brk:null};
draft=Direct.edit(draft,{type:'arrange',order:p.order,leaderKey:p.leaderKey});assert.equal(draft.leader,'c');assert(draft.slots.find(s=>s.key==='a').grown);
async function joint(){const team={boss:'x',keys,...p},seen=[];
 const makeJob=(t,l,b,layout)=>C.bossJobs({topQ:.2},t.boss,l,[keys],results,{},b,layout)[0];
 const out=await J.cosmo({teams:[team],makeJob,level:6,maxLevel:8,auto:true,mode:'top',breaks:[{name:'cube',level:2}],runs:4,probeRuns:2,boundaries:{x:[3]},settings:{screenRuns:2},run:async(jobs,n,seed)=>{
   seen.push(...jobs);return Object.fromEntries(jobs.map(j=>{const tactical=j.order[0]==='a'&&j.leaderKey==='d',v=tactical&&j.level===2?100:10-j.level;return [j.key,{prog:.8,progs:Array(n).fill(.8),via:{forced_coop:2},cosmo:{top:v,mean:v,clear:.8,frac:.8,n}}];}));
 }});
 assert.equal(out.teams[0].level,2);assert.equal(out.teams[0].leaderKey,'d');assert.equal(out.teams[0].order[0],'a');assert(out.teams[0].brkTie);assert.equal(out.teams[0].brk,null);
 assert(seen.some(j=>j.level===3)&&seen.some(j=>j.level===2));assert(out.teams[0].st.frac>0);
 await assert.rejects(()=>J.cosmo({teams:[team],makeJob,level:3,auto:false,mode:'top',breaks:[],runs:2,probeRuns:1,run:async()=>({})}),/누락/);
}
joint().then(()=>{
 for(const [from,to] of [["k.map(leaderKey=>","k.slice(0,1).map(leaderKey=>"],["(s.def||0)/3000","0"]]){
  const src=fs.readFileSync(require.resolve('../party_placement'),'utf8');assert(src.includes(from));const ctx={module:{exports:{}}};vm.runInNewContext(src.replace(from,to),ctx);
  assert.throws(()=>candidates(ctx.module.exports));
 }
 console.log('PASS placement candidates, cache identity, final API, direct roundtrip, joint boundaries/break tie, missing results, 2 mutations');
}).catch(e=>{console.error(e);process.exitCode=1;});
