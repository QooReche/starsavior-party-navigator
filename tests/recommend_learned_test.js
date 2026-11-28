// U360 제품 경로: 실제 학습기·공용 작업자 + 측정 드라이버의 독립 인코더/선택 대조.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {readSrc,cut,loadModule}=require('./helpers/page');
const L=require('../cosmo_learned'),M=require('../tools/learned_reco_measure'),GS=require('../guild_search'),U=require('../ui_shared');
const plain=x=>JSON.parse(JSON.stringify(x)),id=U.teamKey;
const html=readSrc('party_template.html'),runtime=readSrc('recommend_runtime.js');
const defaults=()=>({...plain(require('../data/cosmo_raid.json').search.learned),value:true,outside:360,S:40,m:1,epochs:3});
function fixture(size=13){
 const rows=Array.from({length:size},(_,i)=>({key:'u'+String(i).padStart(2,'0'),cls:['서포터','디펜더','캐스터'][i%3],el:['sun','moon','star'][i%3]}));
 const pool=rows.slice(0,10).map(r=>r.key),by=new Map(rows.map(r=>[r.key,r]));
 const make=keys=>({keys,combo:keys.map(k=>({s:by.get(k)})),vd:'hard',v:0});
 const all=GS.combos({newSearch:true},rows.slice(0,10)).map(make);
 // Engine order differs deliberately from candidate order; leader and break vary too.
 const party=t=>({units:t.keys.slice().reverse().map(k=>({key:k==='u12'?k+'@bloom':k})),leader:t.keys.includes('u11')?2:0});
 const breakFor=t=>t.keys.includes('u10')?{name:'synthetic-break',level:5}:null;
 const ctx={team:make,party,engineKey:k=>k==='u12'?k+'@bloom':k,breakFor,breaks:['synthetic-break']};
 const result=(key,n=1,ties=false)=>{const keys=key.split(','),p=ties?.5:keys.reduce((s,k)=>s+Number(k.slice(1)),0)/100;
  return {ver:'synthetic',n,clear:0,prog:p,ttk:20,progs:Array(n).fill(p),via:{coop:0},raw:JSON.stringify(Array.from({length:n},()=>['wipe',20,20,p]))};};
 return {rows,pool,all,make,ctx,result};
}
async function expected(f,settings,seed,K){
 const S={learned:{...settings,K}},sample=await L.sample(S,f.rows,seed);
 const enc=M.encoder(f.rows,{team:f.ctx.team,simParty:f.ctx.party,ekey:f.ctx.engineKey,teamBreak:f.ctx.breakFor,breaks:f.ctx.breaks});
 const model=await L.train(enc,sample,sample.map(k=>f.result(id(k)).prog),L.config(S,f.rows.length));
 const heap=new L.Heap(settings.outside),pool=new Set(f.pool);
 await L.scan(S,f.rows,keys=>{if(keys.some(k=>!pool.has(k)))heap.put({keys,id:L.id(keys),score:model.predict(keys)});},()=>false);
 return {sample:sample.map(id),outside:heap.sorted().map(x=>id(x.keys)),enc};
}
function harness(A,{enabled=true,easy=false,ties=false,halt=null}={}){
 const f=fixture(),settings={...defaults(),value:enabled},by=new Map(f.all.map(t=>[id(t.keys),t])),trace=[];
 const c=vm.createContext({UiShared:U,RecommendLearned:A,Date,setTimeout:()=>0,clearTimeout(){}});
 for(const [a,b] of [['const SCR_ROUNDS=','const scrKey='],['const scrCmp=','function scrNote('],['function recoScreenSequence(','function simWaiting(']])vm.runInContext(cut(html,a,b),c);
 for(const name of ['scrRoundN','scrPrior','scrLegOpt'])c[name]=vm.runInContext(name,c);
 if(easy)f.all[0].vd='tight';
 const pool=c.scrPick(f.all),sc=c.scrFullInit({done:false,order:[],n:pool.length,total:pool.length,pool,res:{},res2:{},up:null,round:0},f.all);
 A.init(sc,settings,f.rows,new Set(f.pool));
 let stopped=false,seen=0;
 const ctx={...f.ctx,seed:1,add(keys){const key=id(keys);if(!by.has(key))by.set(key,f.make(keys));return by.get(key);}};
 const leg=async(i,keys)=>{
  c.scrLegEnter(sc,i,keys.length);const dest=A.destination(sc,i),n=c.scrRoundN(i);
  trace.push({i,keys:[...keys],before:plain(A.progress(sc)),alert:c.scrAlertOf(sc,Infinity)});
  for(const key of keys){
   if(halt?.phase===i&&seen++===halt.after){stopped=true;throw Error('synthetic cancel');}
   const pr=c.scrPrior(sc,i,key),runs=pr?n-pr.off:n;
   trace.at(-1).requests??=[];trace.at(-1).requests.push({key,party:ctx.party(by.get(key)),runs,seed:ctx.seed,options:{rng_streams:true,break_skill:ctx.breakFor(by.get(key)),...c.scrLegOpt(pr)}});
   dest[key]=f.result(key,n,ties);sc.got++;
   const progress=A.progress(sc);assert(progress.got<=progress.all,'completed work exceeds progress budget');
  }
 };
 const run=async()=>{await A.prepare(sc,ctx,leg,()=>stopped);await new Promise((resolve,reject)=>c.recoScreenSequence(sc,20,by,(i,keys,next)=>leg(i,keys).then(next,reject),()=>{c.scrClose(sc);resolve();}));};
 return {A,c,f,sc,ctx,settings,trace,by,run,resume(){stopped=false;halt=null;sc.done=false;return run();}};
}
async function check(A){
 const h=harness(A),{f,sc}=h,e=await expected(f,h.settings,1,sc.fullN);
 const enc=A.encoder(f.rows,f.ctx);assert.equal(enc.size,e.enc.size);
 for(const keys of GS.combos({newSearch:true},f.rows))assert.deepEqual(plain(enc.encode(keys)),plain(e.enc.encode(keys)),'actual simParty order/leader/break feature parity');
 await h.run();
 assert.deepEqual(plain(sc.union.sample.map(id)),e.sample,'measurement sample seed/order');
 assert.deepEqual(plain(sc.union.outside),e.outside,'measurement U360 prediction order');
 assert.equal(sc.union.settings.learned.K,80,'promotion budget overrides learned K');
 assert.deepEqual(h.trace.map(x=>[x.i,x.keys.length]),[[-2,40],[-3,360],[-1,210],[0,80],[1,20]]);
 assert(sc.union.outside.every(k=>k.split(',').some(x=>!f.pool.includes(x))),'only outside-pool teams get extra battles');
 assert.equal(sc.fullN,80);assert.equal(sc.pool.length,80);assert.equal(sc.total,80);
 assert(sc.pool.some(k=>k.split(',').some(x=>!f.pool.includes(x))),'real outside results must affect promotion');
 assert(sc.pool.every(k=>sc.full.includes(k)),'training-only teams never enter completed promotion');
 assert.equal(sc.union.total,610);assert.deepEqual(plain(A.progress(sc)),{got:610,all:610});
 assert.equal(h.trace[1].before.got,40);assert.equal(h.trace[2].before.got,400);
 assert(h.trace.slice(0,3).every(x=>x.alert==='scan'),'forced scan stays active throughout sample/outside/F');
 assert(h.trace.slice(0,3).flatMap(x=>x.requests).every(j=>j.runs===1&&j.seed===1&&j.options.raw_runs&&!j.options.run_offset&&!j.options.merge_raw),'all one-run phases preserve seed/run offset');
 assert(h.trace[3].requests.every(j=>j.runs===7&&j.options.run_offset===1&&j.options.merge_raw),'promotion reuses actual one-run raw');
 assert(h.trace[4].requests.every(j=>j.runs===24&&j.options.run_offset===8&&j.options.merge_raw),'second screen reuses first-screen raw');
 for(const t of f.all)assert.deepEqual(plain(sc.res0[id(t.keys)]),f.result(id(t.keys)),'F results preserved exactly');
 const off=harness(A,{enabled:false});await off.run();
 assert(!off.sc.union);assert.deepEqual(off.trace.map(x=>[x.i,x.keys.length]),[[-1,210],[0,80],[1,20]]);
 assert.deepEqual(h.trace.find(x=>x.i===-1).requests,off.trace.find(x=>x.i===-1).requests,'F request stream remains unchanged');
 const easy=harness(A,{easy:true});await easy.run();assert(!easy.sc.full&&!easy.sc.union,'easy stage bypasses full scan and learning');
 assert.deepEqual(easy.trace.map(x=>x.i),[0,1]);
 const tie=harness(A,{ties:true});await tie.run();
 assert.deepEqual(plain(tie.sc.pool),tie.f.all.slice(0,80).map(t=>id(t.keys)),'F tie positions win before outside teams');
 // A disabled helper must be an exact no-op, not merely produce the same final order.
 const pristine=harness(A,{enabled:false}),before=plain(pristine.sc);A.init(pristine.sc,{value:false},[],new Set());
 assert.deepEqual(plain(pristine.sc),before);await A.prepare(pristine.sc,{},()=>assert.fail('disabled helper dispatched work'));
 return h;
}
async function cancellation(A){
 for(const phase of [-2,-3]){
  const h=harness(A,{halt:{phase,after:3}});await assert.rejects(h.run(),/synthetic cancel/);
  const partial=A.partial(h.sc),completed=new Set(Object.keys(phase===-2?h.sc.union.observed:h.sc.res0));assert(Object.keys(partial).length>=3,'cancellation keeps completed teams');
  h.c.scrClose(h.sc);assert(h.sc.done&&h.sc.short&&!h.sc.fullDone);
  assert.deepEqual(new Set(h.sc.order),new Set(Object.keys(partial)),'partial result order covers every completed sample/outside team');
  const restored=A.restore(h.sc,h.f.all.slice());assert(Object.keys(partial).every(k=>restored.some(t=>id(t.keys)===k)),'partial teams restored to display');
  const n=h.trace.length;await h.resume();
  const resumed=h.trace.slice(n).filter(x=>x.i===phase).flatMap(x=>x.requests||[]);
  assert(resumed.every(j=>!completed.has(j.key)),'resume never repeats completed phase work');
  assert.equal(h.sc.fullDone,true);assert.equal(h.sc.pool.length,80);assert.equal(A.progress(h.sc).got,A.progress(h.sc).all);
 }
 const h=harness(A);await assert.rejects(A.prepare(h.sc,h.ctx,()=>assert.fail('stale phase dispatched'),()=>true),/취소/);
 assert.equal(Object.keys(h.sc.union.observed).length,0,'cancel before sampling does no work');
}
function partialTieOrder(page,A){
 const c=vm.createContext({UiShared:U,RecommendLearned:A});vm.runInContext(cut(page,'const scrCmp=','function scrNote('),c);
 const full=['a,b,c,d','a,b,c,e'],sample=[['a','b','c','z'],['a','b','c','d'],['a','b','c','y']],result={clear:0,prog:.5,ttk:20};
 const observed=['a,b,c,d','a,b,c,y','a,b,c,z'];
 const run=keys=>plain(c.scrOrder({full,fullDone:false,res0:{'a,b,c,e':result},union:{sample,observed:Object.fromEntries(keys.map(k=>[k,result]))}}));
 const wanted=[...full,'a,b,c,z','a,b,c,y'];
 assert.deepEqual(run(observed),wanted,'partial ties preserve F first and original sample order');
 assert.deepEqual(run(observed.slice().reverse()),wanted,'worker completion order cannot change partial ties');
}
async function main(){
 const configured=require('../party_contents.json').recommendation.learnedUnion,measured=require('../data/cosmo_raid.json').search.learned;
 assert.equal(configured.value,true);assert.equal(configured.outside,360);
 for(const [k,v] of Object.entries(measured))if(!['K','value','note','outside'].includes(k))assert.deepEqual(configured[k],v,'measurement parameter '+k);
 const source=readSrc('recommend_learned.js'),load=s=>loadModule(s,{setTimeout,clearTimeout});
 await check(load(source));await cancellation(load(source));partialTieOrder(html,load(source));
 const mutations=[
  ['outside filter','if(keys.some(k=>!pool.has(k)))top.put','if(true)top.put'],
  ['promotion K','K:sc.fullN','K:sc.fullN+1'],
  ['F tie ordering','sc.full=u.base.concat(u.outside)','sc.full=u.outside.concat(u.base)'],
  ['progress sample charge','u.base.length+u.sample.length+u.outside.length','u.base.length+u.outside.length'],
  ['actual leader','if(i===p.leader)','if(i===0)'],
 ];
 for(const [name,before,after] of mutations){assert(source.includes(before),'mutation anchor: '+name);let caught=false;
  try{await check(load(source.replace(before,after)));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'mutation survived: '+name);
 }
 const stable='keys=[...new Set([...sc.full,...(sc.union.sample||[]).map(k=>UiShared.teamKey(k))])],pos=new Map(keys.map((k,i)=>[k,i]))';
 assert(html.includes(stable));assert.throws(()=>partialTieOrder(html.replace(stable,'pos=new Map([...sc.full,...Object.keys(sc.union.observed)].map((k,i)=>[k,i]))'),load(source)),assert.AssertionError,'unstable partial tie mutation');
 console.log('PASS U360 production selection/encoder parity, F preservation, outside budget, promotion, disabled/easy paths, partial/resume/progress/ties; 6 mutations rejected');
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={fixture,expected,harness,check,cancellation};
