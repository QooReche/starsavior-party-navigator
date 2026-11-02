// 시뮬 시간 상한(진행 기반)·남은 시간 표시 시험. 가짜 시계로 느린 기기·멈춘 작업자·엔진 준비 지연을 흉내 낸다.
// 실행: node tests/sim_timeout_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const section=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
let now=0,timers=[];
const advance=ms=>{const end=now+ms;for(;;){timers.sort((a,b)=>a.at-b.at);const t=timers[0];if(!t||t.at>end)break;timers.shift();now=t.at;t.fn()}now=end};
const workers=[],stops=[];
const mk=keys=>({keys,combo:[]}),st={tab:'1',name:'1-1'};
const ctx=vm.createContext({console,Set,Object,JSON,Math,MODE:'auto',MI:{pending:null},miMode:()=>false,
 Date:{now:()=>now},
 SIMQ:{n:100,seed:1,busy:null,res:{},LOAD_MS:180000,RUN_MS:240000,loaded:false},LASTQ:{},cur:[st],
 contents:[{key:'op'}],$:()=>({value:'0'}),rkOf:()=>0,simParty:t=>({units:t.keys}),teamBreak:()=>null,brkLv:()=>1,
 ckey:t=>t.keys.join(','),simMain:r=>r,simCls:()=>'',esc:String,simOpt:()=>({}),
 document:{querySelector:()=>null,hidden:false},location:{href:'https://test/index.html'},
 setTimeout:(fn,ms)=>{const t={fn,at:now+ms};timers.push(t);return t},clearTimeout:t=>{timers=timers.filter(x=>x!==t)},run(){},
 simStop:msg=>{stops.push(msg);ctx.SIMQ.busy=null;ctx.SIMQ.requestId++},
 Worker:class{constructor(){workers.push(this)}postMessage(req){this.req=req}terminate(){this.stopped=true}}});
vm.runInContext(section('const simSigB=','// 표시 상태는'),ctx);
vm.runInContext(section('function simStart(','document.querySelectorAll(\'input[name="runs"]\')'),ctx);
const ev=s=>vm.runInContext(s,ctx);
const start=teams=>{ctx.LASTQ[1]={rows:teams};ctx.SIMQ.busy=null;stops.length=0;assert.equal(ev('simStart(1)'),true);
 const w=ctx.SIMQ.w,req=w.req;return {w,req,msg:(m)=>w.onmessage({data:Object.assign({id:req.id},m)})}};
const T=[mk(['a','b','c','d']),mk(['a','b','c','e']),mk(['a','b','c','f'])];

// 1) 엔진 준비가 3분 넘게 안 끝나면 「엔진 준비 시간 초과」
let r=start(T);advance(179000);assert.equal(stops.length,0);advance(2000);assert.deepEqual(stops,['엔진 준비 시간 초과']);

// 2) 느린 기기: 팀마다 200초(4분 미만)씩 걸려도 진행이 있으면 끝까지 간다(전체 10분 넘어도 실패 아님)
ctx.SIMQ.w=null;ctx.SIMQ.loaded=false;ctx.SIMQ.rate=undefined;
r=start(T);r.msg({type:'stage',id:undefined,msg:'준비 끝'});
for(let i=0;i<3;i++){r.msg({type:'stage',msg:`시뮬 ${i+1}/3팀 (100판)`});advance(200000);r.msg({type:'team',key:r.req.teams[i].key,result:{n:100,clear:0.5}})}
r.msg({type:'done'});assert.equal(stops.length,0);assert.equal(ev('SIMQ.busy'),null);
assert.equal(Math.round(ev('SIMQ.rate')),2000); // 1판당 2초로 잼

// 3) 잰 속도가 느리면 팀 하나 상한도 늘어난다(3배): 1판 2초 × 100판 × 3 = 600초
assert.equal(ev('simTeamLimit(100)'),600000);
// 남은 시간: 새 요청에서 팀 시작 직후 = 남은 팀 수 × 100판 × 2초
for(const t of T)for(const k of Object.keys(ctx.SIMQ.res))delete ctx.SIMQ.res[k];
r=start(T);r.msg({type:'stage',msg:'시뮬 1/3팀 (100판)'});
assert.equal(ev('SIMQ.eta')-now,600000);assert.match(ev('simEtaText()'),/완료까지 약 10분/);assert.match(ev('simEtaText()'),/오래 걸릴 수 있어요/);
advance(300000);assert.equal(ev('SIMQ.eta')-now,300000);

// 4) 진행이 멈추면(팀 상한 600초 동안 소식 없음) 「시뮬 시간 초과」
advance(299000);assert.equal(stops.length,0);advance(2000);assert.deepEqual(stops,['시뮬 시간 초과']);

// 5) 끝난 팀은 다시 시도 때 빼고 돈다 + 취소 뒤 늦게 온 결과는 무시
ctx.SIMQ.w=null;ctx.SIMQ.loaded=true;
r=start(T);r.msg({type:'stage',msg:'시뮬 1/3팀 (100판)'});advance(1000);r.msg({type:'team',key:r.req.teams[0].key,result:{n:100,clear:0.9}});
const old=r;ctx.SIMQ.requestId++;ctx.SIMQ.busy=null; // 취소(simInvalidate 와 같은 요청 번호 증가)
const before=Object.keys(ctx.SIMQ.res).length;
old.msg({type:'team',key:old.req.teams[1].key,result:{n:100,clear:0.1}});assert.equal(Object.keys(ctx.SIMQ.res).length,before);
r=start(T);assert.equal(r.req.teams.length,2);

// 6) 백그라운드 탭(가려짐)에서는 상한이 지나도 실패로 끝내지 않는다
ctx.document.hidden=true;advance(3600000);assert.equal(stops.length,0);ctx.document.hidden=false;

// 7) 탭 동결·절전: 타이머가 예정보다 10분 늦게 돌면(그동안 계산도 멈춤) 복귀 직후 실패로 끝내지 않는다
ctx.SIMQ.w=null;ctx.SIMQ.loaded=true;stops.length=0;
r=start(T.slice(2));r.msg({type:'stage',id:undefined,msg:'준비 끝'});r.msg({type:'stage',msg:'시뮬 1/1팀 (100판)'});
const L=ev('simTeamLimit(100)'),freeze=ms=>{now+=ms;const t=timers.sort((a,b)=>a.at-b.at).shift();t.fn()};
freeze(L+600000);assert.equal(stops.length,0);advance(L-1000);assert.equal(stops.length,0);advance(2000);assert.deepEqual(stops,['시뮬 시간 초과']);

// 7-1) 멈춘 동안의 팀 시간은 속도 표본에 넣지 않는다
ctx.SIMQ.w=null;stops.length=0;for(const k of Object.keys(ctx.SIMQ.res))delete ctx.SIMQ.res[k];
r=start(T.slice(0,1));r.msg({type:'stage',id:undefined,msg:'준비 끝'});r.msg({type:'stage',msg:'시뮬 1/1팀 (100판)'});
const rate0=ev('SIMQ.rate');freeze(ev('simTeamLimit(100)')+600000);r.msg({type:'team',key:r.req.teams[0].key,result:{n:100,clear:0.5}});r.msg({type:'done'});
assert.equal(ev('SIMQ.rate'),rate0);assert.equal(stops.length,0);

// 8) 수동 모드: 「수동 서순」 진행 메시지도 진행으로 인정(자동 반 + 수동 반이 각각 상한 안이면 끝까지)
const rateAuto=ev('SIMQ.rate');ctx.MODE='manual';ctx.SIMQ.w=null;stops.length=0;ctx.SIMQ.rateM=undefined;
for(const k of Object.keys(ctx.SIMQ.res))delete ctx.SIMQ.res[k];
r=start(T.slice(0,1));r.msg({type:'stage',id:undefined,msg:'준비 끝'});r.msg({type:'stage',msg:'시뮬 1/1팀 (100판)'});advance(500000);
r.msg({type:'stage',msg:'수동 서순 1/1팀 (정책 4종 시험)'});advance(500000);assert.equal(stops.length,0);
r.msg({type:'team',key:r.req.teams[0].key,result:{n:100,clear:0.5}});r.msg({type:'done'});
assert.equal(Math.round(ev('SIMQ.rateM')),10000);assert.equal(ev('SIMQ.rate'),rateAuto); // 자동 속도는 그대로
ctx.MODE='auto';

// 7) 시간 표기
assert.equal(ev('fmtDur(42000)'),'42초');assert.equal(ev('fmtDur(150000)'),'2분 30초');assert.equal(ev('fmtDur(599000)'),'10분');
assert.match((ctx.SIMQ.busy=1,ctx.SIMQ.loaded=true,ctx.SIMQ.eta=now-60000,ev('simEtaText()')),/예상보다 오래/);ctx.SIMQ.busy=null;
console.log('PASS 엔진 준비 초과·느린 기기 완료·속도 비례 상한·남은 시간·무진행 초과·완료 팀 재사용·늦은 메시지 무시·가려진 탭·동결 복귀·수동 모드·예상 초과');

// 별도 상태로 실제 simStop/simInvalidate와 예선 콜백까지 실행한다(중단을 가짜 함수로 대체하지 않음).
function screeningHarness(){
 let clock=1000,queue=[];
 const ws=[],teams=['d','e','f','g','h','i'].map((k,i)=>({...mk(['a','b','c',k]),v:10-i}));
 const c=vm.createContext({console,MODE:'auto',MM:'',MI:{pending:null},miMode:()=>false,
  SIMQ:{n:100,seed:1,busy:null,res:{},scr:{},LOAD_MS:180000,RUN_MS:240000},LASTQ:{1:{rows:teams.slice(0,3),all:teams,total:6}},cur:[st],
  contents:[{key:'op'}],$:()=>({value:'0'}),rkOf:()=>0,simParty:t=>({units:t.keys}),teamBreak:()=>null,brkLv:()=>1,
  simMain:r=>r,simCls:()=>'',esc:String,simOpt:()=>({}),document:{querySelector:()=>null,hidden:false},
  navigator:{hardwareConcurrency:4,deviceMemory:8},location:{href:'https://test/index.html'},
  Date:{now:()=>clock},performance:{now:()=>clock},
  setTimeout:(fn,ms)=>{const t={fn,at:clock+ms};queue.push(t);return t},clearTimeout:t=>{queue=queue.filter(x=>x!==t)},run(){},
  Worker:class{constructor(){ws.push(this)}postMessage(req){this.req=req}terminate(){this.stopped=true}}});
 for(const [a,b] of [['const simSigB=','// 표시 상태는'],['function simInvalidate()','// 자동 확인'],
  ['function simStart(',"document.querySelectorAll('input[name=\"runs\"]')"],['const SCR_ROUNDS=','function simWaiting(']])vm.runInContext(section(a,b),c);
 const evalJS=s=>vm.runInContext(s,c);
 const tick=ms=>{const end=clock+ms;for(;;){queue.sort((a,b)=>a.at-b.at);if(!queue[0]||queue[0].at>end)break;const t=queue.shift();clock=t.at;t.fn()}clock=end};
 const freeze=ms=>{queue.sort((a,b)=>a.at-b.at);assert(queue.length);clock=queue[0].at+ms;queue.shift().fn()};
 const send=(w,m)=>w.onmessage({data:{id:w.req.id,...m}});
 const ready=()=>ws.forEach(w=>send(w,{type:'stage',id:undefined,msg:'준비 끝'}));
 const result=(w,i,clear,prog)=>send(w,{type:'team',key:w.req.teams[i].key,result:{n:w.req.n_runs,clear,prog,progs:[prog],via:{coop:0},ttk:20}});
 return {c,ws,teams,ev:evalJS,tick,freeze,send,ready,result,sc:()=>Object.values(c.SIMQ.scr)[0]};
}

// 9) 가장 늦은 작업자 준비 뒤부터 예선 60초를 잰다. 준비 실패는 실제 중단/풀 정리로 끝난다.
{
 const h=screeningHarness();assert.equal(h.ev('simScreen(1)'),true);assert.equal(h.ws.length,3);
 h.send(h.ws[0],{type:'stage',msg:'준비 끝'});h.tick(61000);assert.equal(h.sc().done,false);
 h.ready();h.tick(59000);assert.equal(h.sc().done,false);h.tick(1000);
 assert.equal(h.sc().done,true);assert.equal(h.sc().cut,true);assert.equal(h.sc().order.length,0);
 assert(h.ws.every(w=>w.stopped));assert.equal(h.c.SIMQ.busy,null);
 const stalled=screeningHarness();stalled.ev('simScreen(1)');stalled.tick(180000);
 assert.match(stalled.c.SIMQ.err,/계산 엔진 준비/);assert.equal(Object.keys(stalled.c.SIMQ.scr).length,0);
 assert(stalled.ws.every(w=>w.stopped));
}

// 10) 예선 동결 복귀: 남은 계산 시간 보존, 멈춘 시간은 속도에서 제외, 완료 팀만 순위에 남김.
{
 const h=screeningHarness();h.ev('simScreen(1)');h.ready();h.tick(10000);
 const [a,b,c]=h.ws;h.send(a,{type:'stage',msg:'시뮬 1/2팀 (8판)'});
 h.tick(800);h.result(a,0,0.5,0.8);const rate=h.c.SIMQ.rateS;assert(rate>0);
 h.send(b,{type:'stage',msg:'시뮬 1/2팀 (8판)'});h.freeze(600000);
 assert.equal(h.sc().done,false);h.result(b,0,0.9,0.95);assert.equal(h.c.SIMQ.rateS,rate);
 h.tick(999);assert.equal(h.sc().done,false);h.tick(1);
 assert.equal(h.sc().cut,true);assert.deepEqual(Array.from(h.sc().order),[b.req.teams[0].key,a.req.teams[0].key]);
 assert(h.ws.every(w=>w.stopped));assert.equal(h.c.SIMQ.screening,false);
 const saved=JSON.stringify(h.sc());h.result(c,0,1,1);h.send(a,{type:'done'});
 assert.equal(JSON.stringify(h.sc()),saved,'시간 초과 뒤 늦은 예선 결과는 무시');
 h.ev('simInvalidate()');assert.equal(JSON.stringify(h.sc()),saved,'완료된 부분 예선 순위는 재시도에 보존');
}

// 11) 2차 예선 도중 시간 초과: 승격한 팀의 이전 결과와 완료된 32판 결과를 함께 보존.
{
 const h=screeningHarness();h.ev('simScreen(1)');h.ready();
 h.ws.slice().forEach(w=>{w.req.teams.forEach((_,i)=>h.result(w,i,0.5,0.7));h.send(w,{type:'done'})});
 assert.equal(h.sc().round,1);assert(h.ws.every(w=>w.req.n_runs===32));
 h.result(h.ws[0],0,0.6,0.8);const winner=h.ws[0].req.teams[0].key;h.tick(60000);
 assert.equal(h.sc().cut,true);assert.equal(h.sc().order.length,6);assert.equal(h.sc().order[0],winner);
 assert.equal(h.sc().res[winner].n,32);assert.equal(Object.values(h.sc().res).filter(r=>r.n===8).length,5);
}

// 12) 실제 본선 시간 초과: 완료 결과 유지 → 미완료 팀만 재시도, 이전 작업자의 늦은 메시지는 무시.
{
 const h=screeningHarness();h.ev('simStart(1)');const w=h.ws[0],oldSend=w.onmessage,req=w.req;
 h.send(w,{type:'stage',msg:'준비 끝'});h.result(w,0,0.9,0.95);h.tick(240000);
 assert.match(h.c.SIMQ.err,/끝난 팀은 이어서/);assert.equal(h.c.SIMQ.busy,null);assert(w.stopped);
 assert.equal(Object.keys(h.c.SIMQ.res).length,1);
 h.ev('simStart(1)');assert.equal(h.ws[1].req.teams.length,2);
 assert(!h.ws[1].req.teams.some(t=>t.key===req.teams[0].key));
 oldSend({data:{id:req.id,type:'team',key:req.teams[1].key,result:{clear:1,prog:1}}});
 oldSend({data:{id:req.id,type:'done'}});assert.equal(Object.keys(h.c.SIMQ.res).length,1);assert.equal(h.c.SIMQ.busy,1);
 h.ws[1].req.teams.forEach((_,i)=>h.result(h.ws[1],i,0.8,0.9));h.send(h.ws[1],{type:'done'});
 assert.equal(Object.keys(h.c.SIMQ.res).length,3);assert.equal(h.c.SIMQ.busy,null);h.tick(1000000);assert.equal(h.c.SIMQ.err,'');
}
console.log('PASS 실제 예선 준비 지연/실패·동결·부분 순위·2차 예선 시간 초과·본선 부분 결과 재시도');
