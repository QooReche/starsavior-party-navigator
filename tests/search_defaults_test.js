// Differential contract check against the same revision used for the private free-policy benchmark.
const assert=require('node:assert/strict');
const {oldModules}=require('../tools/measure_role_search');
const C=require('../cosmo_search'),GS=require('../guild_search'),L=require('../cosmo_learned');
const old=oldModules('5139b2e'),G=require('../data/cosmo_raid.json');
const plain=x=>JSON.parse(JSON.stringify(x));
const roster=Array.from({length:13},(_,i)=>({key:'u'+String(i).padStart(2,'0'),cls:['캐스터','디펜더','서포터'][i%3],el:i%2?'sun':'moon'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:1000-i*13,stats:{hp:100+i*21,def:i*10,spd:i*5},combat:{}}]));
const cls=Object.fromEntries(roster.map(r=>[r.key,r.cls])),keys=roster.slice(0,4).map(r=>r.key);
assert.deepEqual(G.search.placement.baseline,false);assert.deepEqual(G.search.placement.enabled,false);
for(const s of [G.search,require('../data/guild_defense.json').search])assert.equal(s.minFront+s.minDealer,0);
assert.deepEqual(plain(GS.party(keys,results,cls)),plain(old.GS.party(keys,results,cls)));
assert.deepEqual(plain(L.encoder(roster,results,roster).encode(keys)),plain(old.L.encoder(roster,results,roster).encode(keys)));
assert.notDeepEqual(plain(L.encoder(roster,results,roster,{baseline:true}).encode(keys)),plain(old.L.encoder(roster,results,roster).encode(keys)));
assert.equal(GS.jobKey(keys,4,'none',[]),old.GS.jobKey(keys,4,'none',[]));
assert.equal(C.jobKey('a',keys,6,{name:'cube',level:3}),old.C.jobKey('a',keys,6,{name:'cube',level:3}));
async function check(mod){
 const S=structuredClone(G.search);S.learned={...S.learned,S:40,m:1,K:40,M:1,A:8,overlapStarts:2,overlapKeep:2,epochs:3,minCorrelation:-1,missThreshold:1};
 S.screen={runs:2,firstRuns:1,passFrac:.1,passMinMult:1};S.rerank={keep:20,runs:3};S.final.runs=4;S.combine={topTriples:2,show:2};
 const trace=[];
 const out=await mod.search({S,bosses:G.season.bossOrder,results,roster,mode:'top',level:-1,levelMax:2,breaks:[{name:'cube',level:3}],workers:2,stage:'x',base:'',sampleSeed:20261119,
 makeWorker:()=>({terminate(){},postMessage(m){trace.push(plain(m));setImmediate(()=>{
  for(const t of m.teams){const level=t.options.cosmo_raid.level,ks=t.party.units.map(u=>u.key),bi=G.season.bossOrder.indexOf(t.options.cosmo_raid.boss);
   const v=100+ks.reduce((a,k,i)=>a+((Number(k.slice(1))*17+bi*37)%113)*(i+1),0)-Math.abs(level-1)*3+(t.options.break_skill?7:0);
   this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{prog:.8,progs:Array(m.n_runs).fill(.8),via:{coop:1},n:m.n_runs,cosmo:{top:v,mean:v-2,clear:.5,frac:.8}}}});
  }this.onmessage({data:{type:'done',id:m.id}});
 });}})});
 assert(out.rows.length&&out.rows[0].sum>0);assert(trace.every(m=>![11,12,13,77123].includes(m.seed)));
 return {out:plain(out),jobs:trace.flatMap(m=>m.teams.map(t=>plain({t,runs:m.n_runs,seed:m.seed}))).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)))};
}
(async()=>{const expected=await check(old.C),actual=await check(C);assert.deepEqual(actual,expected);
 // Mutation: switching the default layout must invalidate the differential contract.
 const party=GS.party;try{GS.party=(k,r)=>require('../party_placement').party(k,r);assert.notDeepEqual(plain(GS.party(keys,results,cls)),plain(old.GS.party(keys,results,cls)));}finally{GS.party=party;}
 console.log('PASS default search: legacy party/features/keys, learned auto-level/break jobs and complete results, layout mutation');
})().catch(e=>{console.error(e);process.exitCode=1;});
