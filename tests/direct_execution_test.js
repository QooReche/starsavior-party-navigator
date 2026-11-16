// Real scheduler with controlled workers/clock. No engine results are asserted from mocks.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const source=html.slice(html.indexOf('const SCR_WMAX='),html.indexOf('// 이 기기의 시뮬 속도'));
function harness(src=source,cores=3){let time=0,timers=[];const workers=[],events=[];
 const c=vm.createContext({console,Date:{now:()=>time},SIMQ:{LOAD_MS:180000},navigator:{hardwareConcurrency:cores,deviceMemory:8},document:{hidden:false},
  setTimeout:(fn,ms)=>{const t={fn,due:time+ms};timers.push(t);return t},clearTimeout:t=>timers=timers.filter(x=>x!==t),
  Worker:class{constructor(){workers.push(this)}postMessage(m){this.req=m;events.push([m.owner,m.teams[0].key])}terminate(){this.dead=true}}});
 vm.runInContext(src,c);let id=0;
 const start=(owner,keys,opts={})=>{const request=++id,rows={},errors=[],ws=c.scrPool(keys.length),job={request,rows,errors,ws,done:0};
  const arm=c.simWatch(ws,()=>240000,()=>!job.cancelled,()=>{errors.push('timeout');c.simPoolDrop(owner,request)});
  c.simDispatch(ws,keys,{owner,id:request,revision:3,live:()=>!job.cancelled,arm,
   msg:key=>({type:'run',n_runs:100,teams:[{key}]}),stage(){},team(key,m){rows[key]=m.result},done(){job.done++},error(msg){errors.push(msg);c.simPoolDrop(owner,request)},...opts});return job;};
 const send=(w,m)=>w.onmessage({data:{id:w.req.id,requestId:w.req.requestId,job:w.req.job,jobId:w.req.jobId,owner:w.req.owner,revision:w.req.revision,...m}});
 const finish=w=>{send(w,{type:'team',key:w.req.teams[0].key,result:{clear:.6,n:100,progs:[.6],via:{}}});send(w,{type:'done'})};
 const tick=ms=>{const end=time+ms;for(let guard=0;guard<1000;guard++){timers.sort((a,b)=>a.due-b.due);if(!timers.length||timers[0].due>end)break;const t=timers.shift();time=t.due;t.fn()}time=end};
 return {c,workers,events,start,send,finish,tick};
}
function isolation(src=source){const h=harness(src),a=h.start('reco',['r1','r2','r3']),d=h.start('direct',['d1']);
 assert.equal(h.workers.length,2);assert.equal(d.ws.length,0,'direct must wait for an active team');
 const w=h.workers[0],old={...w.req},handler=w.onmessage;h.finish(w);
 assert.equal(w.req.owner,'direct','direct gets the first released worker');assert.equal(w.onmessage,handler,'handler installed once');
 h.c.simPoolDrop('reco');assert(!w.dead,'recommendation cancellation killed a direct lease');
 w.onmessage({data:{type:'team',...old,key:'d1',result:{clear:1}}});assert.equal(Object.keys(d.rows).length,0,'late response accepted');
 h.send(w,{type:'team',requestId:999,key:'d1',result:{clear:1}});assert.equal(Object.keys(d.rows).length,0,'wrong request accepted');
 h.send(w,{type:'team',key:'d1',result:{clear:.6}});h.send(w,{type:'team',key:'d1',result:{clear:1}});assert.equal(d.rows.d1.clear,.6,'duplicate replaced result');
 h.send(w,{type:'done'});h.send(w,{type:'done'});assert.equal(d.done,1);assert(!a.done);
 const x=h.start('direct',['x']),y=h.start('direct',['y']);h.c.simPoolDrop('direct',x.request);assert(!y.ws[0].dead,'individual cancel killed sibling');h.finish(y.ws[0]);assert.equal(y.done,1);
 const dead=h.workers.find(w=>w.dead),before=JSON.stringify(d.rows);dead.onmessage({data:{...dead.req,type:'team',key:'d1',result:{clear:0}}});assert.equal(JSON.stringify(d.rows),before);
}
isolation();
{
 const h=harness(source,2),r=h.start('reco',['a','b']),d=h.start('direct',['x']);h.send(r.ws[0],{type:'stage',msg:'준비 끝'});
 // Queue wait exceeds preparation timeout while the other team still progresses.
 h.tick(170000);h.send(r.ws[0],{type:'stage',msg:'계산 중'});h.tick(170000);assert.equal(d.errors.length,0);h.finish(r.ws[0]);
 assert.equal(d.ws.length,1);h.send(d.ws[0],{type:'stage',msg:'준비 끝'});h.c.document.hidden=true;h.tick(1000000);assert.equal(d.errors.length,0);h.c.document.hidden=false;h.finish(d.ws[0]);assert.equal(d.done,1);
 assert.equal(h.workers.length,1,'global cap');h.c.simPoolDrop('reco');
}
for(const [cores,memGB,mobile,want] of [[16,8,false,8],[16,1,false,1],[16,2,false,2],[16,8,true,2],[1,8,false,1]])assert.equal(harness().c.scrWorkerCount({cores,memGB,mobile}),want);
const mutate=(name,a,b)=>{assert(source.includes(a));assert.throws(()=>isolation(source.replace(a,b)),assert.AssertionError,name);console.log('MUTATION caught + restored:',name)};
mutate('global pool termination',"b.owner===owner&&(requestId==null",'true&&(requestId==null');
mutate('requestId validation removed','if(!boot&&(m.id!==o.id||(m.requestId!=null&&m.requestId!==o.id)))return;','');
console.log('PASS ownership, priority, cap, queue time, hidden tab, individual/bundle cancellation, late/duplicate/request validation');
const direct=fs.readFileSync(require.resolve('../direct_run.js'),'utf8');
const collect=direct.slice(direct.indexOf('function directCollectRecommendation()'),direct.indexOf('function directDifference('));
function firstRecommendation(src){const first={key:'first',q:{power:1}},selected={key:'selected',q:{power:2}},a={clear:.8,n:100},b={clear:.2,n:100};
 const c=vm.createContext({DIRECT:{draft:{}},SIMQ:{busy:null,n:100,seed:1,res:{first:a,selected:b},meta:{first:{runs:100,seed:1,condition:'same'}}},contents:[{}],cur:[{}],$:()=>({value:0}),LASTQ:{1:{rows:[first,selected]}},simSig:(s,t)=>t.key,growthBaseline:()=>b});
 vm.runInContext(src,c);c.directCollectRecommendation();assert.equal(c.DIRECT.compare.result,a,'comparison used selected alternative instead of rows[0]');}
firstRecommendation(collect);
assert.throws(()=>firstRecommendation(collect.replace('result=SIMQ.res[sig]','result=growthBaseline(c,st)')),assert.AssertionError);
console.log('MUTATION caught + restored: growthBaseline instead of completed rows[0]');
async function manifestTimeout(){
 const src=direct.slice(direct.indexOf('async function directManifest('),direct.indexOf('async function directRunRows('));
 let now=0,queue=[],signal;
 const ctx=vm.createContext({AbortController,Error,Date:{now:()=>now},SIMQ:{LOAD_MS:180000},document:{hidden:false},
  setTimeout:(fn,ms)=>{const t={fn,at:now+ms};queue.push(t);return t},clearTimeout:t=>queue=queue.filter(x=>x!==t),
  fetch:(u,o)=>{signal=o.signal;return new Promise((yes,no)=>signal.addEventListener('abort',()=>no(Error('aborted'))));}});
 vm.runInContext(src,ctx);const active={},result=ctx.directManifest(active).catch(e=>e.message);
 ctx.document.hidden=true;now=180000;queue.shift().fn();assert(!signal.aborted,'hidden preparation expired');
 ctx.document.hidden=false;now=960000;queue.shift().fn();assert(!signal.aborted,'sleep resume expired');
 now+=180000;queue.shift().fn();assert.match(await result,/시간 초과/);assert(!active.abort);assert.equal(queue.length,0);
 const cancelled={},p=ctx.directManifest(cancelled).catch(e=>e.message);cancelled.abort();await p;assert.equal(queue.length,0);
 console.log('PASS manifest preparation timeout, hidden/sleep correction and explicit cancellation');
}
manifestTimeout().catch(e=>{console.error(e);process.exitCode=1});
