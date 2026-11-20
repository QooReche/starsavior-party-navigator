const fs=require('node:fs'),vm=require('node:vm');
const assert=require('node:assert/strict'),C=require('../cosmo_search'),G=require('../data/cosmo_raid.json');
const roster=Array.from({length:12},(_,i)=>({key:'u'+String(i).padStart(2,'0'),cls:'캐스터'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:100-i,stats:{hp:100,def:0,spd:1}}]));
async function check(search=C){const S=structuredClone(G.search),seen=[];S.learned.value=false;S.maxPool=0;
 S.screen={runs:2,firstRuns:1,passFrac:.1,passMinMult:1};S.rerank={keep:30,runs:3};S.final.runs=3;S.combine={topTriples:2,show:1};S.retry.maxCandidatesPerBoss=495;
 const out=await search.search({S,bosses:G.season.bossOrder,roster,results,level:6,levelMax:18,mode:'top',breaks:[],workers:2,stage:'x',base:'',
 makeWorker:()=>({terminate(){},postMessage(m){seen.push(m);setImmediate(()=>{for(const t of m.teams){const keys=t.party.units.map(u=>u.key),v=keys.reduce((s,k)=>s+Number(k.slice(1)),100)+(keys[t.party.leader]===keys.slice().sort().at(-1)?1000:0);
 this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{n:m.n_runs,prog:.8,progs:Array(m.n_runs).fill(.8),via:{coop:1},clear:.5,cosmo:{mean:v,top:v,clear:.5,frac:.8}}}});
 }this.onmessage({data:{type:'done',id:m.id}});});}})});
 assert(out.rows.length);assert(out.representative.every(a=>a.sampled>0&&a.misses>0&&a.expanded));
 assert(out.representative.some(a=>a.boundarySampled>0));assert(out.representative.some(a=>a.randomSampled>0));
 const leaders=new Map();for(const m of seen.filter(m=>m.seed===13))for(const t of m.teams){const keys=t.party.units.map(u=>u.key),id=keys.slice().sort().join();if(!leaders.has(id))leaders.set(id,new Set());leaders.get(id).add(keys[t.party.leader]);}
 assert([...leaders.values()].some(s=>s.size===4),'audit miss must expand rerank leaders');
 assert(out.rows[0].teams.every(t=>t.st.frac>0));}
(async()=>{await check();const source=fs.readFileSync(require.resolve('../cosmo_search'),'utf8'),anchor='const leaders=representative.find(a=>a.boss===b)?.expanded;';assert(source.includes(anchor));const c={module:{exports:{}},require:n=>require('../'+n),setTimeout,performance};vm.runInNewContext(source,c);await check(c.module.exports);vm.runInNewContext(source.replace(anchor,'const leaders=false;'),c);await assert.rejects(()=>check(c.module.exports),/expand rerank leaders/);console.log('PASS representative audit: boundary/random, recovery, leader expansion, mutation');})().catch(e=>{console.error(e);process.exitCode=1;});
