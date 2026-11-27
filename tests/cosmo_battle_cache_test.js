// Exact battle requests may cross the owned/grown pass; candidate IDs may not.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const SS=require('../score_search');
const {capture,results}=require('../tools/bench_cosmo_common');
function keyContract(factory=SS.battleCache){
 const map=new Map(),cx={base:'fixture/',stage:'cosmo',seed:3,runs:4,options:{build:'standard',rules_override:{rule:'old'}}};
 const job={key:'display-id',party:{units:[{key:'u00',stats_override:{atk:100},myinfo_combat:{skill:1}}],leader:0},options:{cosmo_raid:{boss:'a',level:2},run_offset:4,merge_raw:'prior'}};
 const cache=factory(map,cx),result={n:4,cosmo:{top:10},via:{coop:.5}};
 cache.set(job,result);
 assert.deepEqual(JSON.parse(JSON.stringify(cache.get({...job,key:'other-display-id'}))),result);
 assert.notEqual(cache.get(job),result,'consumer must receive a separate result object');
 for(const changed of [{base:'other/'},{stage:'guild'},{seed:4},{runs:5},{options:{build:'standard',rules_override:{rule:'new'}}}])
  assert.equal(factory(map,{...cx,...changed}).get(job),undefined,JSON.stringify(changed));
 for(const edit of [j=>j.party.units[0].stats_override.atk++,j=>j.party.units[0].myinfo_combat.skill++,j=>j.party.leader++,
   j=>j.options.cosmo_raid.level++,j=>j.options.run_offset++,j=>j.options.merge_raw='other']){
  const changed=structuredClone(job);edit(changed);assert.equal(cache.get(changed),undefined);
 }
}
async function parity(){
 const battles=new Map(),changed=structuredClone(results);changed.u00.stats.hp+=100;
 const before=await capture(results,true,{battles});
 assert(battles.size>0&&before.requests.length>0);
 const baseline=await capture(changed,true),shared=await capture(changed,true,{battles});
 assert.deepEqual(shared.out,baseline.out,'complete search result stays bit-identical');
 assert(shared.requests.length>0&&shared.requests.length<baseline.requests.length,'changed teams run; identical teams reuse');
 const firstKeys=new Set(before.requests.map(r=>r.key));
 assert.deepEqual(shared.requests.map(r=>r.key),baseline.requests.filter(r=>!firstKeys.has(r.key)).map(r=>r.key),'missing requests preserve order, seed and interval');
 const replay=await capture(changed,true,{battles});
 assert.equal(replay.requests.length,0);assert.deepEqual(replay.out,baseline.out);
 let handle;
 await assert.rejects(capture(changed,true,{battles,onHandle:h=>{handle=h;},onProgress:()=>handle?.cancel()}),e=>e.gwenCause==='cancel');
 return {before:before.requests.length,uncached:baseline.requests.length,shared:shared.requests.length};
}
async function main(){
 keyContract();const counts=await parity();
 // Deliberately remove reuse; the end-to-end assertion must detect the regression.
 const original=SS.battleCache;
 try{SS.battleCache=(...args)=>({...original(...args),get:()=>undefined});await assert.rejects(parity);}finally{SS.battleCache=original;}
 // Mutate actual key construction, not just an artificial test input.
 const source=fs.readFileSync(require.resolve('../score_search'),'utf8');
 const unchanged={module:{exports:{}}};vm.runInNewContext(source,unchanged);keyContract(unchanged.module.exports.battleCache);
 for(const [from,to] of [['seed,runs,options,j.party,j.options','0,runs,options,j.party,j.options'],
   ['seed,runs,options,j.party,j.options','seed,0,options,j.party,j.options'],
   ['seed,runs,options,j.party,j.options','seed,runs,{},j.party,j.options'],
   ['seed,runs,options,j.party,j.options','seed,runs,options,{},j.options'],
   ['seed,runs,options,j.party,j.options','seed,runs,options,j.party,{}']]){
  assert(source.includes(from));const context={module:{exports:{}}};vm.runInNewContext(source.replace(from,to),context);
  assert.throws(()=>keyContract(context.module.exports.battleCache));
 }
 console.log('PASS cosmo exact-request reuse: '+JSON.stringify(counts)+'; reuse/key mutations killed');
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={keyContract,parity};
