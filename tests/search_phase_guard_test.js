const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const E=require('../search_executor'),GS=require('../guild_search');
function harness(executor=E,{chunk=0,pool:reuse=false,keys=['a','b']}={}){
 let time=0,hidden=false,serial=0;const timers=new Map(),sent=[],ws=[],progress=[];
 const makeWorker=()=>{const w={postMessage:m=>sent.push(m),terminate(){this.dead=true}};ws.push(w);return w};
 const watch={now:()=>time,setTimer:(fn,ms)=>{timers.set(++serial,{fn,due:time+ms});return serial},clearTimer:id=>timers.delete(id),hidden:()=>hidden,loadMs:()=>100,limit:()=>200};
 const pool=reuse?executor.workerPool(makeWorker):undefined;
 const h=executor.runPhase({makeWorker,pool,jobs:keys.map(key=>({key,party:{}})),workers:1,runs:2,seed:1,stage:'test',base:'',chunk,watch,onProgress:d=>progress.push(d)});
 // Attach rejection handler before manually advancing the clock.
 const outcome=h.promise.then(value=>({value}),error=>({error}));
 const send=(type,extra={})=>ws[0].onmessage({data:{type,id:sent.at(-1).id,...extra}});
 const team=(key='a')=>send('team',{key,result:{prog:.8,progs:[.6,1],via:{coop:.1}}});
 function tick(at){time=at;for(const [id,t] of [...timers])if(t.due<=time){timers.delete(id);t.fn();}}
 return {h,outcome,send,team,tick,timers,sent,ws,progress,pool,hide:v=>hidden=v};
}
async function checks(E){
 let x=harness(E);x.tick(100);assert.match((await x.outcome).error?.message||'',/준비 시간/);assert.equal(x.timers.size,0);assert(x.ws[0].dead);
 x=harness(E);x.send('stage',{msg:'준비 끝'});x.tick(199);assert(!x.ws[0].dead);x.tick(200);assert.match((await x.outcome).error?.message||'',/무진행/);
 x=harness(E);x.hide(true);x.tick(100);assert(!x.ws[0].dead);x.hide(false);x.tick(200);assert((await x.outcome).error);
 x=harness(E);x.tick(6000);assert(!x.ws[0].dead);x.tick(6100);assert((await x.outcome).error);
 x=harness(E);x.team();x.tick(199);assert(!x.ws[0].dead);x.team('b');x.send('done');assert.equal(Object.keys((await x.outcome).value).length,2);assert.equal(x.timers.size,0);
 x=harness(E);x.team();x.send('done');assert.match((await x.outcome).error?.message||'',/누락/);
 x=harness(E);x.send('team',{id:undefined,key:'a',result:{}});x.team('b');x.send('done');assert.match((await x.outcome).error?.message||'',/id/);
 x=harness(E);x.team('alien');assert.match((await x.outcome).error?.message||'',/요청 밖/);
 x=harness(E);x.team();x.team();assert.match((await x.outcome).error?.message||'',/중복/);
 x=harness(E);x.send('team',{key:'a',result:null});assert((await x.outcome).error);
 x=harness(E);x.send('done',{id:99});assert(!x.ws[0].dead);x.tick(100);assert((await x.outcome).error);
 x=harness(E);x.send('done',{requestId:99});assert(!x.ws[0].dead);x.h.cancel();assert.equal((await x.outcome).error.gwenCause,'cancel');
 x=harness(E);x.team();const late=x.ws[0].onmessage;x.h.cancel();late({data:{type:'team',id:1,key:'b',result:{}}});assert.equal((await x.outcome).error.gwenCause,'cancel');assert.deepEqual(Object.keys(x.h.snapshot()),['a']);assert.equal(x.timers.size,0);
 x=harness(E,{keys:['a','a']});x.team();x.team();x.send('done');assert((await x.outcome).value);assert.deepEqual(x.progress,[1,2]);
 x=harness(E,{chunk:1,pool:true});x.team();x.send('done');const first=x.sent[0].id;assert.notEqual(first,x.sent[1].id);
 x.send('team',{id:first,key:'b',result:{}});assert.deepEqual(x.progress,[1]);x.team('b');x.send('done');assert((await x.outcome).value);assert.equal(x.timers.size,0);assert(!x.ws[0].dead);x.pool.close();
 x=harness(E,{keys:[]});assert.deepEqual(JSON.parse(JSON.stringify((await x.outcome).value)),{});assert.equal(x.ws.length,0);assert.equal(x.timers.size,0);
 assert.throws(()=>GS.pickTop({}, {}, [{key:'missing'}],{},[],5,{}),/누락/);
}
(async()=>{
 await checks(E);
 // Mutations must produce an assertion, without waiting for a wall-clock timeout.
 const src=fs.readFileSync(require.resolve('../search_executor'),'utf8');
 for(const [from,to] of [['late||env.hidden?.()','false'],["if(left)throw new Error('계산 결과가 누락된 채 작업이 끝남');",''],["&&m.id!==requestId)throw",'&&false)throw']]){
  assert(src.includes(from));const ctx={module:{exports:{}},setTimeout,clearTimeout};vm.runInNewContext(src.replace(from,to),ctx);
  await assert.rejects(()=>checks(ctx.module.exports),assert.AssertionError);
 }
 console.log('PASS 17 phase guard scenarios + 3 mutations: boot/run stalls, hidden/late timer, ids, missing/duplicate replies, repeated jobs, reuse/cancel');
})().catch(e=>{console.error(e);process.exitCode=1});
