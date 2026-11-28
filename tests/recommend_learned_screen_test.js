// Real screen/bundle adapters and SIM_EXEC, with synthetic worker battle results.
'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm');
const {readSrc,cut,loadModule}=require('./helpers/page'),{fixture,expected}=require('./recommend_learned_test');
const U=require('../ui_shared'),A=require('../recommend_learned'),id=U.teamKey,plain=x=>JSON.parse(JSON.stringify(x));
const html=readSrc('party_template.html'),runtime=readSrc('recommend_runtime.js');
const timer=(fn,ms)=>{const t=setTimeout(fn,ms);if(ms>100)t.unref();return t;};
const tick=()=>new Promise(setImmediate);
async function until(test){for(let i=0;i<2000;i++){if(test())return;await new Promise(r=>setTimeout(r,1));}assert.fail('synthetic screen did not settle');}
function create({enabled=true,easy=false,pausePhase=null,pauseAfter=3,pauseCompute=null,missing=false,page=html,rt=runtime,learned=readSrc('cosmo_learned.js')}={}){
 const f=fixture(pauseCompute?20:13),trace=[],progress=[],paints=[],workers=[],late=[],settings={...plain(require('../party_contents.json').recommendation.learnedUnion),value:enabled,S:40,m:1,epochs:3};
 // Hold a real learner yield: train pauses after a fitted fold; scan after 4096 scored combinations.
 let computing='',releaseCompute=null;const compute={visits:0,finished:0,settled:false,error:null};
 const L=loadModule(learned,{setTimeout(fn,ms){if(computing===pauseCompute&&!releaseCompute){releaseCompute=fn;return 0;}return timer(fn,ms);}});
 for(const name of ['train','scan']){const original=L[name];L[name]=async(...args)=>{
  computing=name;if(name==='scan'){const visit=args[2];args[2]=keys=>{compute.visits++;visit(keys);};}
  try{const result=await original(...args);if(name===pauseCompute)compute.finished++;return result;}finally{computing='';}
 };}
 const helper=loadModule(readSrc('recommend_learned.js'),{require:name=>name==='./cosmo_learned.js'?L:U});
 const prepare=helper.prepare;helper.prepare=(...args)=>prepare(...args).then(x=>{compute.settled=true;return x;},e=>{compute.settled=true;compute.error=e;throw e;});
 if(easy)f.all[0].vd='tight';
 const box={all:f.all,cands:f.rows.map(s=>({s,score:0})),rows:f.all.slice(0,3),total:f.all.length};let received=0,paused=false;
 const ctx=vm.createContext({UiShared:U,...(!missing?{RecommendLearned:helper}:{}),GwenLane:require('../gwen_lane'),console,URL,Date,setTimeout:timer,clearTimeout,
  CFG:{recommendation:{learnedUnion:settings}},QK:{d:{sv:{}}},D:{pen:{}},Quick:{evaluate:()=>({rounds:1,left:0})},
  partyPool:cands=>cands.filter(x=>f.pool.includes(x.s.key)),
  SIMQ:{LOAD_MS:180000,RUN_MS:240000,n:100,seed:1,rateS:10,busy:null,res:{},scr:{},meta:{}},RECO:{},LASTQ:{1:box},cur:[{tab:'a',name:'b'}],contents:[{key:'op',parties:1}],
  document:{hidden:false,querySelector:()=>null},navigator:{hardwareConcurrency:3,deviceMemory:8},location:{href:'https://synthetic.test/index.html'},
  $:()=>({value:0}),rkOf:()=>0,starOf:()=>0,miMode:()=>false,MM:'',MI:{},recommendationPolicyTag:()=>[],
  simOpt:()=>({}),simParty:f.ctx.party,teamBreak:f.ctx.breakFor,brkLv:()=>5,breakOwned:()=>f.ctx.breaks,ekey:f.ctx.engineKey,
  quickIn:()=>({growth:1,power:null,qs:{bp:100},prm:{}}),qBase:()=>({growth:1,power:null}),simRateAdd(){},simTeamLimit:()=>240000,run(){},
  recoIdentity:()=> 'fixed',recoProgressPaint(task){if(task.sc?.union&&task.sc.round<0&&Number.isFinite(task.progress))paints.push({phase:task.sc.round,progress:task.progress,remaining:task.remaining,got:task.sc.got,all:task.sc.left});},directResultsPaint(){},goalVal:r=>r?.clear,esc:String,
  Worker:class{
   constructor(){workers.push(this);}
   postMessage(m){const sc=Object.values(ctx.SIMQ.scr)[0],phase=sc?.round;trace.push({phase,req:plain(m)});
    setImmediate(()=>{if(this.dead)return;const send=x=>this.onmessage({data:{...m,...x}});send({type:'stage',msg:'준비 끝'});
     for(const t of m.teams){if(this.dead)return;
      if(phase===pausePhase&&received++>=pauseAfter){paused=true;
       // Deliver queued replies even after terminate(), through the actual SIM_EXEC receiver.
       const pending=m.teams.slice(m.teams.indexOf(t));late.push(()=>{for(const t of pending)send({type:'team',key:t.key,result:f.result(t.key,m.n_runs+(t.options?.run_offset||0))});send({type:'done'});});return;}
      send({type:'team',key:t.key,result:f.result(t.key,m.n_runs+(t.options?.run_offset||0))});
      if(sc)progress.push({phase,got:sc.got,all:sc.left,helper:A.progress(sc),alert:ctx.scrAlertOf(sc,sc.alertAt+1)});
     }send({type:'done'});
    });
   }
   terminate(){this.dead=true;}
  }
 });
 vm.runInContext(readSrc('search_executor.js'),ctx);
 vm.runInContext(cut(page,'const SCR_WMAX=','// 이 기기의 시뮬 속도'),ctx);
 vm.runInContext(cut(page,'function simInvalidate()','// 자동 확인'),ctx);
 vm.runInContext(cut(page,'const SCR_ROUNDS=','function simWaiting('),ctx);
 vm.runInContext(cut(page,'function recoPlanStages(st)','// 자동 추천만:'),ctx);
 vm.runInContext(cut(rt,'function recoTaskCancel(','// ── 현장 재조사'),ctx);
 ctx.ckey=combo=>id(combo.map(x=>x.s.key));ctx.scrWorkers=()=>2;ctx.recheckIdent=()=> 'fixed';ctx.simSig=(_,t)=>id(t.keys);
 ctx.simStop=(msg)=>{ctx.simInvalidate();ctx.SIMQ.err=msg;};
 const snapshot={key:'fixed',c:ctx.contents[0],st:ctx.cur[0],seed:1,n:100,options:{},qi:ctx.quickIn(),profile:null,engineKey:f.ctx.engineKey,
  breaks:f.ctx.breaks,screenKey:()=> 'scr',party:f.ctx.party,breakFor:f.ctx.breakFor};
 const task={owner:'reco-bundle',request:0,engine:'synthetic'};ctx.RECO.task=task;
 return {ctx,f,box,settings,trace,progress,paints,workers,snapshot,task,compute,sc:()=>Object.values(ctx.SIMQ.scr)[0],paused:()=>paused,
  computePaused:()=>!!releaseCompute,releaseCompute(){releaseCompute();},
  late(){assert(late.length>0,'a real queued reply must be delivered');for(const send of late.splice(0))send();},
  async screen(){assert.equal(ctx.simScreen(1),true);await until(()=>paused||this.sc()?.done||ctx.SIMQ.err);assert(!ctx.SIMQ.err,ctx.SIMQ.err);},
  async bundle(){await ctx.recoScreenCalculate(snapshot,task,1,box);},
  resume(){pausePhase=null;received=0;paused=false;},close(){ctx.simPoolDrop(task.owner);ctx.simPoolDrop();}};
}
const jobs=(h,phase)=>h.trace.filter(x=>x.phase===phase).flatMap(x=>x.req.teams.map(t=>({key:t.key,party:t.party,seed:x.req.seed,runs:x.req.n_runs,options:{...x.req.options,...t.options}})));
function remainingWork(h){
 for(let i=0;i<h.paints.length;i++){const p=h.paints[i];
  assert.equal(p.remaining,(p.all-p.got)*10/2,'bundle ETA includes every remaining sample/outside/F battle');
  if(i)assert(p.remaining<=h.paints[i-1].remaining,'remaining work never increases at a union phase transition');
 }
 assert.equal(h.paints.at(-1).remaining,0);
}
async function screenAndBundle(sources={}){
 const h=create(sources);await h.screen();const e=await expected(h.f,h.settings,1,80),sc=h.sc();
 assert.deepEqual(jobs(h,-2).map(j=>j.key),e.sample);assert.deepEqual(jobs(h,-3).map(j=>j.key),e.outside);
 assert.equal(jobs(h,-1).length,210);assert.equal(sc.pool.length,80);assert(sc.pool.some(k=>k.includes('u12')));
 assert.equal(h.progress.filter(x=>x.phase<0).at(-1).got,610);
 assert(h.progress.filter(x=>x.phase<0).every(x=>x.all===610&&x.got===x.helper.got&&x.alert==='scan'),'combined forced progress includes all phases');
 assert(h.workers.length<=2,'all phases reuse the common worker pool');
 const bundle=create(sources);await bundle.bundle();assert.deepEqual(plain(bundle.sc().pool),plain(sc.pool),'bundle and screen select the same promotion');
 for(let i=0;i<bundle.paints.length;i++){const p=bundle.paints[i];assert.equal(p.progress,p.got/p.all,'bundle paints cumulative progress including each phase entry');if(i)assert(p.progress>=bundle.paints[i-1].progress,'bundle progress never resets between union phases');}
 remainingWork(bundle);
 assert(bundle.paints.some(p=>p.phase===-3&&p.got===40));assert(bundle.paints.some(p=>p.phase===-1&&p.got===400));
 for(const phase of [-2,-3,-1,0,1])assert.deepEqual(jobs(bundle,phase),jobs(h,phase),'bundle/screen worker request parity phase '+phase);
 const off=create({enabled:false});await off.screen();assert(!off.sc().union);
 assert.deepEqual(jobs(off,-1),jobs(h,-1),'U360 preserves every F worker request');
 const absent=create({enabled:false,missing:true});await absent.screen();
 for(const phase of [-1,0,1])assert.deepEqual(jobs(off,phase),jobs(absent,phase),'disabled path identical to absent helper');
 const easy=create({easy:true});await easy.screen();assert(!easy.sc().union&&!easy.sc().full);assert(!easy.trace.some(x=>x.phase<0));
 for(const x of [h,bundle,off,absent,easy])x.close();
}
async function partial(sources={}){
 for(const phase of [-2,-3])for(const action of ['scrStop','simInvalidate']){
  const h=create({...sources,pausePhase:phase});await h.screen();const sc=h.sc(),done=new Set(Object.keys(phase===-2?sc.union.observed:sc.res0));
  assert(done.size>=3);const plan=h.ctx.recoPlanStages(h.ctx.cur[0]),scan=plan.find(x=>x.id==='1:scan');
  assert.equal(scan.jobs,610);assert.equal(scan.done,A.progress(sc).got,'ETA counts training and outside completed battles');
  h.ctx[action]();await tick();assert(sc.done&&sc.short&&!sc.fullDone);assert(sc.order.length>=done.size);
  const stopped=A.progress(sc);assert.match(h.ctx.scrNote(1,h.ctx.cur[0]),new RegExp(`${stopped.all}판 중 ${stopped.got}판만 확인했음`),'partial note counts sample and outside battles');
  assert.equal(h.ctx.scrAlertOf(sc),'','stopping clears forced exploration');
  A.restore(sc,h.box.all);assert(sc.order.every(k=>h.box.all.some(t=>id(t.keys)===k)),'partial results remain displayable');
  const before=h.trace.length;h.resume();assert.equal(h.ctx.simScreen(1,true),true);await until(()=>sc.done||h.ctx.SIMQ.err);
  assert(!h.ctx.SIMQ.err,h.ctx.SIMQ.err);assert(sc.fullDone);assert.equal(sc.pool.length,80);
  assert(h.trace.slice(before).filter(x=>x.phase===phase).flatMap(x=>x.req.teams).every(t=>!done.has(t.key)),'resume skips completed phase teams');
  h.close();
 }
}
// Attach a rejection handler immediately, so cancellation cannot escape as an unhandled rejection.
function start(h,mode){
 const state={settled:false,error:null};
 if(mode==='screen')assert.equal(h.ctx.simScreen(1),true);
 else h.bundle().then(()=>{state.settled=true;},e=>{state.settled=true;state.error=e;});
 return state;
}
async function bundleRemainingResume(sources={}){
 const h=create({...sources,pausePhase:-3,pauseAfter:359}),state=start(h,'bundle');
 try{
  await until(h.paused);await tick();assert.equal(Object.keys(h.sc().res0).length,359);
  h.ctx.recoTaskCancel();await tick();assert(state.settled&&state.error);
  const task={owner:'reco-bundle',request:h.task.request,engine:'synthetic'};
  h.ctx.RECO.task=task;h.resume();const before=h.trace.length;
  await h.ctx.recoScreenCalculate(h.snapshot,task,1,h.box);
  assert.equal(h.trace.slice(before).filter(x=>x.phase===-3).flatMap(x=>x.req.teams).length,1,'resume evaluates only the last outside team');
  remainingWork(h);
 }finally{h.close();}
}
async function bundleCancel(sources={},phase=-2){
 const h=create({...sources,pausePhase:phase}),state=start(h,'bundle');
 try{
  await until(h.paused);await tick();const sc=h.sc(),before=plain(A.partial(sc)),count=h.trace.length;
  assert(Object.keys(before).length>=3,'cancel only after real team results');
  assert(h.workers.some(w=>!w.dead&&w._lease),'bundle owns active worker leases');
  h.ctx.recoTaskCancel();await tick();
  assert(state.settled&&state.error,'bundle cancellation rejects its pending calculation');
  assert.match(state.error.message,/중단|취소/);assert(h.task.cancelled);
  assert(h.workers.every(w=>!w._lease),'bundle cancellation releases its owner leases');
  h.late();await tick();assert.deepEqual(plain(A.partial(sc)),before,'cancelled bundle keeps only completed results');
  assert.equal(h.trace.length,count,'cancelled bundle cannot dispatch another phase');assert(!sc.fullDone);
 }finally{h.close();}
}
async function computeCancel(sources={},mode='screen',phase='train'){
 const h=create({...sources,pauseCompute:phase}),state=start(h,mode);
 try{
  await until(h.computePaused);const sc=h.sc(),before=plain(A.partial(sc)),count=h.trace.length;
  assert.equal(Object.keys(sc.union.observed).length,40,'all sample battles precede CPU cancellation');
  assert.equal(sc.union.outside,null);assert.equal(h.compute.visits,phase==='scan'?4096:0,'cancel inside actual fit/scoring work');
  h.ctx[mode==='screen'?'scrStop':'recoTaskCancel']();h.releaseCompute();
  await until(()=>h.compute.settled||h.compute.finished);await tick();
  assert.equal(h.compute.finished,0,mode+' '+phase+' must stop at the held learner yield');
  assert(h.compute.settled&&h.compute.error,'learning promise rejects cancellation');
  assert.match(h.compute.error.message,/중단|취소/);
  if(mode==='bundle')assert(state.settled&&state.error,'bundle propagates CPU cancellation');
  else assert(sc.done&&sc.short,'screen retains partial sample results');
  assert.deepEqual(plain(A.partial(sc)),before);assert.equal(sc.union.outside,null,'cancelled predictions are not published');
  assert.equal(h.trace.length,count,'no outside or F battle after CPU cancellation');assert(!sc.fullDone);
 }finally{h.close();}
}
async function lateInvalidation(sources={},mode='screen',phase=-2){
 const h=create({...sources,pausePhase:phase}),state=start(h,mode);
 try{
  await until(h.paused);await tick();const sc=h.sc();assert(Object.keys(A.partial(sc)).length>=3);
  h.ctx.simInvalidate();
  const before=plain(sc),count=h.trace.length,paints=h.paints.length;
  h.late();await tick();
  assert.deepEqual(plain(sc),before,mode+' ignores queued team/done responses after input invalidation');
  assert.equal(h.trace.length,count,'late done cannot dispatch new work');assert.equal(h.paints.length,paints,'late reply cannot repaint');
  assert(sc.done&&sc.short&&!sc.fullDone);assert.equal(h.ctx.SIMQ.busy,null);assert.equal(h.ctx.SIMQ.screening,false);
  if(mode==='bundle')assert(state.settled&&state.error,'invalidated bundle rejects');
 }finally{h.close();}
}
(async()=>{
 await screenAndBundle();await partial();await bundleRemainingResume();
 for(const phase of [-2,-3,-1])await bundleCancel({},phase);
 for(const mode of ['screen','bundle']){
  for(const phase of ['train','scan'])await computeCancel({},mode,phase);
  for(const phase of [-2,-3,-1])await lateInvalidation({},mode,phase);
 }
 for(const [name,before,after,check] of [
  ['forced progress','sc.got++;if(w._t)','sc.got=1;if(w._t)',screenAndBundle],
  ['ETA total','const n=sc.union?.total||sc.full.length','const n=sc.full.length',partial],
 ]){
  assert(html.includes(before),'mutation anchor: '+name);let caught=false;
  try{await check({page:html.replace(before,after)});}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'mutation survived: '+name);
 }
 const start='task.sc?.union&&task.sc.round<0?task.sc.got/task.sc.left:0';assert(runtime.includes(start));let caught=false;
 try{await screenAndBundle({rt:runtime.replace(start,'0')});}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
 assert(caught,'bundle phase progress reset mutation survived');
 let mutations=3;
 async function rejectMutation(name,check){let caught=false;try{await check();}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'mutation survived: '+name);mutations++;console.log('REJECTED '+name);}
 const remaining='task.sc?.union&&task.sc.round<0?unionRemaining():rate?';assert(runtime.includes(remaining));
 await rejectMutation('phase-only bundle remaining',()=>screenAndBundle({rt:runtime.replace(remaining,'rate?')}));
 const capacity='Math.max(1,scrWorkers())';assert(runtime.includes(capacity));
 await rejectMutation('shrinking worker count in union ETA',()=>screenAndBundle({rt:runtime.replace(capacity,'Math.max(1,ws.length)')}));
 await rejectMutation('phase-limited capacity on resume',()=>bundleRemainingResume({rt:runtime.replace(capacity,'Math.max(1,ws.capacity)')}));
 const stop='task.stop?.();simPoolDrop(task.owner);';assert(runtime.includes(stop));
 for(const phase of [-2,-3,-1])await rejectMutation('bundle stop '+phase,()=>bundleCancel({rt:runtime.replace(stop,'simPoolDrop(task.owner);')},phase));
 const learner=readSrc('cosmo_learned.js');
 for(const mode of ['screen','bundle'])for(const phase of ['train','scan']){
  const before=phase==='train'?"await pause();if(stale())throw Error('취소');":'await pause();check();';assert(learner.includes(before));
  // Skip that CPU loop's cancellation checks: downstream guards must not mask continued fitting/scoring.
  const broken=phase==='train'?learner.replace(before,'await pause();'):learner.replace('if(stale())throw Object.assign','if(false)throw Object.assign');
  await rejectMutation(mode+' cancel during '+phase,()=>computeCancel({learned:broken},mode,phase));
 }
 const invalidate=cut(html,'function simInvalidate()','// 자동 확인');
 for(const mode of ['screen','bundle'])for(const phase of [-2,-3,-1])await rejectMutation(mode+' late response '+phase,
  ()=>lateInvalidation({page:html.replace(invalidate,'function simInvalidate(){}\n')},mode,phase));
 console.log(`PASS U360 screen/bundle parity, cumulative remaining work, battle/fit/scoring cancellation, invalidated late replies, resume, easy/off paths; ${mutations} mutations rejected`);
})().catch(e=>{console.error(e);process.exitCode=1;});
