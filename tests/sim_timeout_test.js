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
 contents:[{key:'op'}],$:()=>({value:'0'}),rkOf:()=>0,starOf:()=>0,simParty:t=>({units:t.keys}),teamBreak:()=>null,brkLv:()=>1,
 ckey:t=>t.keys.join(','),simMain:r=>r,simCls:()=>'',esc:String,simOpt:()=>({}),
 document:{querySelector:()=>null,hidden:false},location:{href:'https://test/index.html'},
 setTimeout:(fn,ms)=>{const t={fn,at:now+ms};timers.push(t);return t},clearTimeout:t=>{timers=timers.filter(x=>x!==t)},run(){},
 simStop:msg=>{stops.push(msg);ctx.SIMQ.busy=null;ctx.SIMQ.requestId++},
 Worker:class{constructor(){workers.push(this)}postMessage(req){this.req=req}terminate(){this.stopped=true}}});
vm.runInContext(section('const simSigB=','// 표시 상태는'),ctx);
vm.runInContext(section('function simStart(','document.querySelectorAll(\'input[name="runs"]\')'),ctx);
const ev=s=>vm.runInContext(s,ctx);
// 작업자는 팀을 하나씩 받는다(대기열 simDispatch): w.req = 지금 맡은 팀, 그 팀의 done 을 보내야 다음 팀이 온다. 보낼 전체 목록 = SIMQ.lastReq.req.teams
// (이 맥락에는 navigator 가 없어 작업자 1개)
const start=teams=>{ctx.LASTQ[1]={rows:teams};ctx.SIMQ.busy=null;stops.length=0;assert.equal(ev('simStart(1)'),true);
 const w=ctx.SIMQ.w,msg=m=>w.onmessage({data:Object.assign({id:w.req.id,job:w.req.job},m)});
 return {w,req:w.req,all:Array.from(ev('SIMQ.lastReq.req.teams')),msg,team:result=>{msg({type:'team',key:w.req.teams[0].key,result});msg({type:'done'})}}};
const T=[mk(['a','b','c','d']),mk(['a','b','c','e']),mk(['a','b','c','f'])];

// 1) 엔진 준비가 3분 넘게 안 끝나면 「엔진 준비 시간 초과」
let r=start(T);advance(179000);assert.equal(stops.length,0);advance(2000);assert.deepEqual(stops,['엔진 준비 시간 초과']);

// 2) 느린 기기: 팀마다 200초(4분 미만)씩 걸려도 진행이 있으면 끝까지 간다(전체 10분 넘어도 실패 아님)
ctx.SIMQ.w=null;ctx.SIMQ.loaded=false;ctx.SIMQ.rate=undefined;
r=start(T);r.msg({type:'stage',id:undefined,msg:'준비 끝'});
assert.equal(r.all.length,3);assert.equal(r.w.req.teams.length,1);
for(let i=0;i<3;i++){assert.equal(r.w.req.teams[0].key,r.all[i].key);r.msg({type:'stage',msg:'시뮬 1/1팀 (100판)'});advance(200000);r.team({n:100,clear:0.5})}
assert.equal(stops.length,0);assert.equal(ev('SIMQ.busy'),null);
assert.equal(Math.round(ev('SIMQ.rate')),2000); // 1판당 2초로 잼

// 3) 잰 속도가 느리면 팀 하나 상한도 늘어난다(3배): 1판 2초 × 100판 × 3 = 600초
assert.equal(ev('simTeamLimit(100)'),600000);
// 남은 시간: 새 요청에서 팀 시작 직후 = 남은 팀 수 × 100판 × 2초
for(const t of T)for(const k of Object.keys(ctx.SIMQ.res))delete ctx.SIMQ.res[k];
r=start(T);r.msg({type:'stage',msg:'시뮬 1/1팀 (100판)'});
assert.equal(ev('SIMQ.eta')-now,600000);assert.match(ev('simEtaText()'),/완료까지 약 10분/);assert.match(ev('simEtaText()'),/오래 걸릴 수 있어요/);
advance(300000);assert.equal(ev('SIMQ.eta')-now,300000);

// 4) 진행이 멈추면(팀 상한 600초 동안 소식 없음) 「모의 전투 시간 초과」
advance(299000);assert.equal(stops.length,0);advance(2000);assert.deepEqual(stops,['모의 전투 시간 초과']);

// 5) 끝난 팀은 다시 시도 때 빼고 돈다 + 취소 뒤 늦게 온 결과는 무시
ctx.SIMQ.w=null;ctx.SIMQ.loaded=true;
r=start(T);r.msg({type:'stage',msg:'시뮬 1/1팀 (100판)'});advance(1000);r.team({n:100,clear:0.9});
const old=r;ctx.SIMQ.requestId++;ctx.SIMQ.busy=null; // 취소(simInvalidate 와 같은 요청 번호 증가)
const before=Object.keys(ctx.SIMQ.res).length;
old.team({n:100,clear:0.1});assert.equal(Object.keys(ctx.SIMQ.res).length,before);
r=start(T);assert.equal(r.all.length,2);

// 6) 백그라운드 탭(가려짐)에서는 상한이 지나도 실패로 끝내지 않는다
ctx.document.hidden=true;advance(3600000);assert.equal(stops.length,0);ctx.document.hidden=false;

// 7) 탭 동결·절전: 타이머가 예정보다 10분 늦게 돌면(그동안 계산도 멈춤) 복귀 직후 실패로 끝내지 않는다
ctx.SIMQ.w=null;ctx.SIMQ.loaded=true;stops.length=0;
r=start(T.slice(2));r.msg({type:'stage',id:undefined,msg:'준비 끝'});r.msg({type:'stage',msg:'시뮬 1/1팀 (100판)'});
const L=ev('simTeamLimit(100)'),freeze=ms=>{now+=ms;const t=timers.sort((a,b)=>a.at-b.at).shift();t.fn()};
freeze(L+600000);assert.equal(stops.length,0);advance(L-1000);assert.equal(stops.length,0);advance(2000);assert.deepEqual(stops,['모의 전투 시간 초과']);

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
// 가짜 작업자: 받은 요청을 posts 에 적기만 한다. 시험이 그 작업자의 «지금 맡은 팀»(w.req) 결과·done 을 손으로 보낸다(대기열은 done 뒤에 다음 팀을 줌)
function screeningHarness(names=['d','e','f','g','h','i'],vOf=i=>10-i,nav={hardwareConcurrency:4,deviceMemory:8}){
 let clock=1000,queue=[];
 const ws=[],posts=[],teams=names.map((k,i)=>({...mk(['a','b','c',k]),v:vOf(i)}));
 const c=vm.createContext({console,MODE:'auto',MM:'',MI:{pending:null},miMode:()=>false,
  SIMQ:{n:100,seed:1,busy:null,res:{},scr:{},LOAD_MS:180000,RUN_MS:240000},LASTQ:{1:{rows:teams.slice(0,3),all:teams,total:teams.length}},cur:[st],
  contents:[{key:'op'}],$:()=>({value:'0'}),rkOf:()=>0,starOf:()=>0,simParty:t=>({units:t.keys}),teamBreak:()=>null,brkLv:()=>1,
  simMain:r=>r,simCls:()=>'',esc:String,simOpt:()=>({}),document:{querySelector:()=>null,hidden:false},
  navigator:nav,location:{href:'https://test/index.html'},
  Date:{now:()=>clock},performance:{now:()=>clock},
  setTimeout:(fn,ms)=>{const t={fn,at:clock+ms};queue.push(t);return t},clearTimeout:t=>{queue=queue.filter(x=>x!==t)},run(){},
  Worker:class{constructor(){ws.push(this)}postMessage(req){this.req=req;posts.push({w:this,req})}terminate(){this.stopped=true}}});
 for(const [a,b] of [['const simSigB=','// 표시 상태는'],['function simInvalidate()','// 자동 확인'],
  ['function simStart(',"document.querySelectorAll('input[name=\"runs\"]')"],['const SCR_ROUNDS=','function simWaiting(']])vm.runInContext(section(a,b),c);
 const evalJS=s=>vm.runInContext(s,c);
 const tick=ms=>{const end=clock+ms;for(;;){queue.sort((a,b)=>a.at-b.at);if(!queue[0]||queue[0].at>end)break;const t=queue.shift();clock=t.at;t.fn()}clock=end};
 const freeze=ms=>{queue.sort((a,b)=>a.at-b.at);assert(queue.length);clock=queue[0].at+ms;queue.shift().fn()};
 const send=(w,m)=>w.onmessage({data:{id:w.req.id,job:w.req.job,...m}});
 const ready=()=>ws.forEach(w=>w.req&&send(w,{type:'stage',id:undefined,msg:'준비 끝'}));
 const result=(w,clear,prog)=>send(w,{type:'team',key:w.req.teams[0].key,result:{n:w.req.n_runs,clear,prog,progs:[prog],via:{coop:0},ttk:20,raw:'[raw'+w.req.n_runs+']'}});
 const fin=w=>send(w,{type:'done'});
 const serve=(w,clear,prog=0.7)=>{result(w,clear,prog);fin(w)};
 return {c,ws,posts,teams,ev:evalJS,tick,freeze,send,ready,result,fin,serve,sc:()=>Object.values(c.SIMQ.scr)[0]};
}
const keyOf=k=>['a','b','c',k].sort().join(','),names=n=>Array.from({length:n},(_,i)=>'t'+i);
const live=h=>h.ws.filter(w=>!w.stopped),busy=h=>live(h).filter(w=>w._job!=null);
// 요청 번호 id(생략 = 지금 요청)로 나간 팀 key 를 보낸 순서대로
const sentOf=(h,id=h.c.SIMQ.requestId)=>h.posts.filter(p=>p.req.id===id),sent=(h,id)=>sentOf(h,id).map(p=>p.req.teams[0].key);
// 지금 단계(같은 요청 번호)의 일을 모두 끝낸다: 일하는 작업자마다 맡은 팀 결과 → done → (다음 팀을 받으면) 반복. clear = 값 또는 key → 값
const finishAll=(h,clear=0.5)=>{const id=h.c.SIMQ.requestId;for(let guard=0;guard<5000;guard++){if(h.c.SIMQ.requestId!==id)return;const w=busy(h)[0];if(!w)return;
 h.serve(w,typeof clear==='function'?clear(w.req.teams[0].key):clear)}assert.fail('finishAll 이 끝나지 않음')};

// 9) 예선은 전체 시간 상한이 없다: 엔진 준비는 내려받기 상한, 준비된 뒤에는 작업자마다 소식(팀 시작·결과)이 오는 한 끝까지.
//    한 작업자라도 소식이 끊기면(무진행 4분 — 다른 작업자가 일하고 있어도) 멈추고 끝난 팀으로 순위
{
 const h=screeningHarness();assert.equal(h.ev('simScreen(1)'),true);assert.equal(h.ws.length,3);
 h.send(h.ws[0],{type:'stage',id:undefined,msg:'준비 끝'});h.tick(61000);assert.equal(h.sc().done,false);
 h.ready();const [a,b,c]=h.ws,ka=a.req.teams[0].key,kb=b.req.teams[0].key;
 for(let i=0;i<3;i++){h.tick(100000);for(const w of h.ws)h.send(w,{type:'stage',msg:'시뮬 1/1팀 (8판)'})}   // 5분 — 팀 시작 소식도 진행
 h.tick(100000);h.result(a,0.5,0.8);h.tick(100000);h.result(b,0.9,0.95);                                  // 8분 20초 — 60초 상한 없음
 assert.equal(h.sc().done,false);assert.equal(h.c.SIMQ.err,'');
 h.tick(39999);assert.equal(h.sc().done,false);h.tick(1);                                          // c 는 마지막 소식 뒤 240초 동안 조용(a·b 는 그 사이 결과를 냄)
 assert.match(h.c.SIMQ.err,/오래 걸려/);assert.equal(h.sc().done,true);assert.equal(h.sc().short,true);
 assert.deepEqual(Array.from(h.sc().order),[kb,ka]);
 assert(h.ws.every(w=>w.stopped));assert.equal(h.c.SIMQ.busy,null);assert.equal(h.c.SIMQ.screening,false);assert.equal(h.c.SIMQ.pool,null);
 const stalled=screeningHarness();stalled.ev('simScreen(1)');stalled.tick(180000);
 assert.match(stalled.c.SIMQ.err,/계산 엔진 준비/);assert.equal(Object.keys(stalled.c.SIMQ.scr).length,0);
 assert(stalled.ws.every(w=>w.stopped));
 // 엔진을 준비 못 한 작업자가 하나라도 있으면(나머지는 준비) 내려받기 상한에서 멈춘다
 const half=screeningHarness();half.ev('simScreen(1)');half.send(half.ws[0],{type:'stage',id:undefined,msg:'준비 끝'});half.send(half.ws[1],{type:'stage',id:undefined,msg:'준비 끝'});
 half.tick(179999);assert.equal(half.c.SIMQ.err,'');half.tick(1);assert.match(half.c.SIMQ.err,/계산 엔진 준비/);
 const hidden=screeningHarness();hidden.ev('simScreen(1)');hidden.ready();hidden.c.document.hidden=true;hidden.tick(3600000);
 assert.equal(hidden.c.SIMQ.err,'');assert.equal(hidden.c.SIMQ.busy,1,'가려진 탭에서는 무진행 상한으로 끝내지 않음');
}

// 10) 예선 동결 복귀: 타이머가 크게 늦게 돌면 끝내지 않고 다시 잰다. 멈춘 시간은 속도에서 제외. 늦게 온 결과는 무시
{
 const h=screeningHarness();h.ev('simScreen(1)');h.ready();h.tick(10000);
 const [a,b,c]=h.ws,ka=a.req.teams[0].key,kb=b.req.teams[0].key;h.send(a,{type:'stage',msg:'시뮬 1/1팀 (8판)'});
 h.tick(800);h.result(a,0.5,0.8);const rate=h.c.SIMQ.rateS;assert.equal(rate,100);
 h.send(b,{type:'stage',msg:'시뮬 1/1팀 (8판)'});h.freeze(600000);
 assert.equal(h.sc().done,false);assert.equal(h.c.SIMQ.err,'');h.result(b,0.9,0.95);assert.equal(h.c.SIMQ.rateS,rate);
 h.tick(239999);assert.equal(h.sc().done,false);h.tick(1);
 assert.equal(h.sc().done,true);assert.deepEqual(Array.from(h.sc().order),[kb,ka]);
 const saved=JSON.stringify(h.sc());h.result(c,1,1);h.fin(a);
 assert.equal(JSON.stringify(h.sc()),saved,'멈춘 뒤 늦은 예선 결과는 무시');
 h.ev('simInvalidate()');assert.equal(JSON.stringify(h.sc()),saved,'부분 예선 순위는 재시도에 보존');
}

// 11) 2차 도중 「지금까지 결과로 보기」: 먼저 끝난 팀만 32판 결과로 위에 올리지 않는다(8판 순위 그대로). 32판 결과는 남겨 「끝까지 확인」 때 다시 안 돈다
//     2차는 1차 8판을 다시 돌리지 않는다: 1차 결과의 raw 를 그대로 되돌려 보내고 뒤쪽 24판(run_offset 8)만 — 결과의 판 수는 32
{
 const h=screeningHarness();h.ev('simScreen(1)');h.ready();
 assert(sentOf(h).every(p=>p.req.n_runs===8&&p.req.teams[0].options.raw_runs===true&&p.req.teams[0].options.run_offset===undefined));
 const best8=h.ws[1].req.teams[0].key;finishAll(h,k=>k===best8?0.9:0.5);
 assert.equal(h.sc().round,1);
 assert(sentOf(h).length===3&&sentOf(h).every(p=>p.req.n_runs===24&&p.req.teams[0].options.run_offset===8&&p.req.teams[0].options.merge_raw==='[raw8]'&&!('raw_runs' in p.req.teams[0].options)),'2차 = 1차 raw + 24판');
 const w0=busy(h).find(w=>w.req.teams[0].key!==best8),early=w0.req.teams[0].key;
 h.serve(w0,0.6,0.8);                                                                              // 2차에서 한 팀만 끝남(8판 1등이 아닌 팀)
 h.ev('scrStop()');const sc=h.sc();
 assert.equal(sc.done,true);assert.equal(sc.short,true);assert.equal(sc.order.length,6);
 assert.equal(sc.order[0],best8,'8판 결과 순 — 2차를 먼저 끝낸 팀이 위로 올라오지 않음');
 assert.equal(Object.keys(sc.res).length,6);assert(Object.values(sc.res).every(r=>r.n===8));assert.deepEqual(Object.keys(sc.res2),[early]);
 assert.equal(sc.res2[early].n,32,'합친 판 수');
 assert.match(h.ev('scrNote(1,cur[0])'),/중간에 멈춰서 상위 팀을 짧게만 확인했어요/);assert.equal(h.c.SIMQ.err,'');
 assert.equal(h.ev('simScreen(1,true)'),true);h.ready();const id=h.c.SIMQ.requestId;
 finishAll(h,0.55);
 assert.equal(sent(h,id).length,5);assert(!sent(h,id).includes(early),'이미 32판을 돈 팀은 다시 안 돎');assert(sentOf(h,id).every(p=>p.req.n_runs===24));
 assert.equal(h.sc().done,true);assert.equal(h.sc().short,false);assert.equal(h.sc().order[0],early,'2차를 다 마치면 32판 결과 순');
 assert.equal(h.ev('scrNote(1,cur[0])'),'');
 // 1차 결과에 raw 가 없으면(옛 엔진 묶음과 섞임) 2차는 32판을 처음부터 돈다
 const o=screeningHarness();o.ev('simScreen(1)');o.ready();
 const id1=o.c.SIMQ.requestId;while(o.c.SIMQ.requestId===id1){const w=busy(o)[0];o.send(w,{type:'team',key:w.req.teams[0].key,result:{n:8,clear:0.5,prog:0.7,ttk:20}});o.fin(w)}
 assert(sentOf(o).every(p=>p.req.n_runs===32&&p.req.teams[0].options.raw_runs===true&&p.req.teams[0].options.run_offset===undefined));
}

// 12) 실제 본선 시간 초과: 완료 결과 유지 → 미완료 팀만 재시도, 이전 작업자의 늦은 메시지는 무시. 본선도 팀마다 작업자에 나눈다
{
 const h=screeningHarness();h.ev('simStart(1)');assert.equal(h.ws.length,3);
 assert.deepEqual(sent(h),Array.from(h.ev('SIMQ.lastReq.req.teams')).map(t=>t.key));assert(sentOf(h).every(p=>p.req.n_runs===100&&p.req.teams.length===1));
 const olds=h.ws.map(w=>({on:w.onmessage,req:w.req})),first=h.ws[0].req.teams[0].key;
 h.ready();h.serve(h.ws[0],0.9,0.95);h.tick(239999);assert.equal(h.c.SIMQ.err,'');h.tick(1);
 assert.match(h.c.SIMQ.err,/끝난 팀은 이어서/);assert.equal(h.c.SIMQ.busy,null);assert(h.ws.every(w=>w.stopped));
 assert.equal(Object.keys(h.c.SIMQ.res).length,1);
 h.ev('simStart(1)');assert.equal(live(h).length,2,'남은 팀 수만큼만 작업자');assert.equal(sent(h).length,2);
 assert(!sent(h).includes(first));
 const o=olds[1];o.on({data:{id:o.req.id,job:o.req.job,type:'team',key:o.req.teams[0].key,result:{clear:1,prog:1}}});
 o.on({data:{id:o.req.id,job:o.req.job,type:'done'}});assert.equal(Object.keys(h.c.SIMQ.res).length,1);assert.equal(h.c.SIMQ.busy,1);
 h.ready();finishAll(h,0.8);
 assert.equal(Object.keys(h.c.SIMQ.res).length,3);assert.equal(h.c.SIMQ.busy,null);h.tick(1000000);assert.equal(h.c.SIMQ.err,'');
 assert(live(h).length===2,'정상으로 끝나면 작업자를 끄지 않음');
}
console.log('PASS 예선 상한 없음·준비 지연/실패·작업자별 무진행 상한·가려진 탭·동결·2차 도중 멈춤·1차 판 재사용·본선 부분 결과 재시도');

// ── 예선은 끝까지(11/13, 정확도 우선): 줄이지 않고 다 돈다. 멈추는 것은 사용자뿐 → 알리고 「끝까지 확인」 ──
// 13) 후보 순서는 풀별 번갈아. 느린 기기여도 전 후보 8판 → 상위 20팀(1차 8판 + 24판)을 끝까지 돌고, 다 돌면 안내가 없다. 끝난 뒤 작업자는 본선이 다시 쓴다
{
 const h=screeningHarness(names(30),i=>i);                    // 근사 점수 순 = 빠른 계산 순의 반대
 h.c.SIMQ.rateS=5000;                                         // 1판 5초 — 예전 같으면 60초 상한에 걸릴 속도
 assert.equal(h.ev('simScreen(1)'),true);
 const pool=Array.from(h.sc().pool),want=[];for(let i=0;i<15;i++)want.push(keyOf('t'+i),keyOf('t'+(29-i)));
 assert.deepEqual(pool,want,'빠른 계산 1 · 근사 점수 1 번갈아');
 const id1=h.c.SIMQ.requestId;
 assert.deepEqual(sent(h),pool.slice(0,3),'처음에는 작업자 수만큼, 후보 순서대로');
 h.ready();
 for(let i=0;i<9;i++){h.tick(200000);assert.equal(h.sc().done,false);for(const w of busy(h))h.serve(w,0.4,0.6)}   // 30분 — 상한 없음
 finishAll(h,0.5);
 assert.deepEqual(sent(h,id1),pool,'전 후보를 후보 순서대로 하나씩(줄이지 않음, 중복 없음)');assert(sentOf(h,id1).every(p=>p.req.n_runs===8));
 assert.equal(h.sc().round,1);const id2=h.c.SIMQ.requestId;finishAll(h,0.6);
 assert.equal(sent(h,id2).length,20);assert.equal(new Set(sent(h,id2)).size,20);assert(sentOf(h,id2).every(p=>p.req.n_runs===24),'2차는 상위 20팀: 1차 8판에 24판을 더해 32판');
 const sc=h.sc();
 assert.equal(sc.done,true);assert.equal(sc.short,false);assert.equal(Object.keys(sc.res).length,30);assert.equal(Object.keys(sc.res2).length,20);
 assert(Object.values(sc.res2).every(r=>r.n===32));
 assert.equal(sc.order.length,30);assert(Array.from(sc.order).slice(0,20).every(k=>sc.res2[k]));
 assert.equal(h.ev('scrNote(1,cur[0])'),'');assert.equal(h.ev('simScreen(1,true)'),false,'다 봤으면 「끝까지 확인」 없음');
 assert(h.ws.length===3&&h.ws.every(w=>!w.stopped),'끝까지 돌면 작업자를 끄지 않는다');
 assert.equal(h.c.SIMQ.busy,null);h.tick(10000000);assert.equal(h.c.SIMQ.err,'','끝난 뒤 무진행 감시가 남아 있지 않음');
 // 본선: 살아 있는 작업자 셋에 팀을 하나씩 — 새로 띄우지 않는다
 assert.equal(h.ev('simStart(1)'),true);assert.equal(h.ws.length,3);
 assert.equal(sent(h).length,3);assert.equal(new Set(sentOf(h).map(p=>p.w)).size,3);assert(sentOf(h).every(p=>p.req.n_runs===100));
 // 남은 시간: 팀 3 × 100판 × 1판 2초 ÷ 작업자 3
 h.c.SIMQ.rate=2000;for(const w of h.ws)h.send(w,{type:'stage',msg:'시뮬 1/1팀 (100판)'});
 assert.equal(h.c.SIMQ.eta-h.c.Date.now(),200000);
 finishAll(h,0.9);assert.equal(h.c.SIMQ.busy,null);assert.equal(Object.keys(h.c.SIMQ.res).length,3);assert(h.ws.every(w=>!w.stopped));
 // 무효화(조건 변경·취소)에서는 모두 끈다
 h.ev('simInvalidate()');assert(h.ws.every(w=>w.stopped));assert.equal(h.c.SIMQ.pool,null);assert.equal(h.c.SIMQ.w,null);
}

// 14) 1차 도중 「지금까지 결과로 보기」: 끝난 팀으로 순위 → 안내 + 「끝까지 확인」(안 돈 팀만 8판 → 상위 20팀 32판). 끝난 팀이 없으면 그냥 취소
{
 const h=screeningHarness(names(30),i=>i);h.ev('simScreen(1)');h.ready();const pool=Array.from(h.sc().pool);
 let best;for(let i=0;i<7;i++){const w=busy(h)[i%3];if(i===4)best=w.req.teams[0].key;h.serve(w,i===4?0.9:0.3,0.6)}
 h.ev('scrStop()');const sc=h.sc();
 assert.equal(sc.done,true);assert.equal(sc.short,true);assert.equal(sc.order.length,7);assert.equal(sc.order[0],best);
 assert.equal(h.c.SIMQ.err,'','멈춤은 오류가 아님(본선으로 이어 감)');assert.equal(h.c.SIMQ.busy,null);assert(h.ws.every(w=>w.stopped));
 const note=h.ev('scrNote(1,cur[0])');assert.match(note,/중간에 멈춰서 후보 7\/30팀만 확인했어요/);assert.match(note,/data-scrmore="1"[^>]*>끝까지 확인/);
 h.c.SIMQ.busy=1;assert.doesNotMatch(h.ev('scrNote(1,cur[0])'),/data-scrmore/,'계산 중엔 단추 없음');h.c.SIMQ.busy=null;
 const todo=pool.filter(k=>!sc.res[k]);
 assert.equal(h.ev('simScreen(1,true)'),true);h.ready();const id=h.c.SIMQ.requestId;
 finishAll(h,0.4);
 assert.deepEqual(sent(h,id),todo,'안 돈 23팀만 이어서(후보 순서대로)');assert.equal(todo.length,23);assert(sentOf(h,id).every(p=>p.req.n_runs===8));
 assert.equal(h.sc().round,1);const id2=h.c.SIMQ.requestId;finishAll(h,0.7);
 assert.equal(sent(h,id2).length,20);assert(sentOf(h,id2).every(p=>p.req.n_runs===24));assert(sent(h,id2).includes(best));
 assert.equal(h.sc().done,true);assert.equal(h.sc().short,false);assert.equal(h.ev('scrNote(1,cur[0])'),'');
 // 끝난 팀이 하나도 없으면 순위를 낼 수 없다 → 취소(다시 자동으로 돌지 않게 「중단함」)
 const none=screeningHarness(names(30));none.ev('simScreen(1)');none.ready();none.ev('scrStop()');
 assert.equal(Object.keys(none.c.SIMQ.scr).length,0);assert.equal(none.c.SIMQ.err,'중단함');assert(none.ws.every(w=>w.stopped));
}
console.log('PASS 예선 끝까지: 번갈아 순서·줄이지 않음·상한 없음·작업자 재사용·본선 나눔·1차 도중 멈춤 안내·끝까지 확인·빈 멈춤');

// ── 속도 개선(11/13): 결과는 그대로, 빨리 ──
// 15) 순위는 작업자 수·끝난 순서와 무관: 동률은 후보 순서로 가른다. 작업자 1개(후보 순서대로 끝남)와 작업자 3개(뒤 작업자가 먼저 끝남)의 순위·2차에 올린 팀이 같다
{
 const clearOf=k=>k===keyOf('t7')?0.75:k===keyOf('t22')?0.75:0.5;          // 대부분 동률, 둘만 위
 const runAll=(nav,pickW)=>{const h=screeningHarness(names(30),i=>i,nav);h.ev('simScreen(1)');h.ready();
  for(let g=0;g<5000&&!h.sc().done;g++){const w=pickW(busy(h));h.serve(w,clearOf(w.req.teams[0].key))}return h};
 const one=runAll({hardwareConcurrency:2,deviceMemory:8},b=>b[0]),many=runAll({hardwareConcurrency:4,deviceMemory:8},b=>b[b.length-1]);
 const shuffled=runAll({hardwareConcurrency:16,deviceMemory:8},b=>b[(b.length*7+3)%b.length]);
 assert.equal(one.ws.length,1);assert.equal(many.ws.length,3);assert.equal(shuffled.ws.length,8);
 const pool=Array.from(one.sc().pool),top=[keyOf('t7'),keyOf('t22')].sort((a,b)=>pool.indexOf(a)-pool.indexOf(b));
 const want=top.concat(pool.filter(k=>!top.includes(k)));
 assert.deepEqual(Array.from(one.sc().order),want,'동률은 후보 순서');
 assert.notDeepEqual(Object.keys(many.sc().res),Object.keys(one.sc().res),'시험 전제: 끝난 순서는 서로 다름');
 for(const h of [many,shuffled]){assert.deepEqual(Array.from(h.sc().order),want,'작업자 수·끝난 순서가 달라도 같은 순위');
  assert.deepEqual(Array.from(h.sc().up),Array.from(one.sc().up),'2차에 올린 팀도 같음')}
}

// 16) 대기열: 빨리 끝내는 작업자가 더 가져간다(고정 분배 아님). 다음 팀은 그 작업의 done 뒤에만. 같은 결과 두 번·다른 작업 번호·다른 팀 key·결과 없는 done 은 받지 않는다
{
 const h=screeningHarness(names(12),i=>i);h.ev('simScreen(1)');h.ready();const pool=Array.from(h.sc().pool),id=h.c.SIMQ.requestId;
 const [a,b,c]=h.ws;
 for(let i=0;i<5;i++){h.send(a,{type:'stage',msg:'시뮬 1/1팀 (8판)'});h.serve(a,0.5)}             // a 혼자 5팀, b·c 는 첫 팀을 아직 못 끝냄
 assert.deepEqual(sentOf(h).filter(p=>p.w===a).map(p=>p.req.teams[0].key),[pool[0],pool[3],pool[4],pool[5],pool[6],pool[7]]);
 assert.equal(sentOf(h).filter(p=>p.w===b).length,1);assert.equal(h.sc().got,5);
 const breq=b.req;h.result(b,0.6);assert.equal(b.req,breq,'결과만으로는 다음 팀을 안 줌(done 확인 뒤)');
 h.result(b,0.1);assert.equal(h.sc().res[breq.teams[0].key].clear,0.6,'같은 작업의 두 번째 결과는 버림');assert.equal(h.sc().got,6);
 h.fin(b);assert.notEqual(b.req,breq);
 const creq=c.req;h.send(c,{type:'team',job:creq.job+50,key:creq.teams[0].key,result:{n:8,clear:1}});assert.equal(h.sc().res[creq.teams[0].key],undefined,'맡긴 작업 번호가 아니면 무시');
 h.send(c,{type:'team',key:'x,y,z,w',result:{n:8,clear:1}});assert.equal(h.sc().got,6,'맡긴 팀이 아니면 무시');
 h.send(c,{type:'done',job:creq.job+50});assert.equal(c.req,creq);
 finishAll(h,0.5);assert.equal(sent(h,id).length,12);assert.equal(new Set(sent(h,id)).size,12,'중복 배정 없음');
 assert.equal(new Set(sentOf(h,id).map(p=>p.req.job)).size,12);
 // 옛 sim_worker.js(캐시) = job 을 되돌려 주지 않음 → 지금 맡은 작업의 답으로 받는다
 const old=screeningHarness();old.ev('simScreen(1)');old.ready();
 for(let g=0;g<100&&!old.sc().done;g++){const w=busy(old)[0],r=w.req;w.onmessage({data:{id:r.id,type:'team',key:r.teams[0].key,result:{n:r.n_runs,clear:0.5,prog:0.5,ttk:9}}});w.onmessage({data:{id:r.id,type:'done'}})}
 assert.equal(old.sc().done,true);assert.equal(old.sc().short,false);
 // 결과 없이 done → 오류로 멈춘다(조용히 건너뛰지 않음)
 const bad=screeningHarness();bad.ev('simScreen(1)');bad.ready();bad.fin(bad.ws[0]);
 assert.notEqual(bad.c.SIMQ.err,'');assert.equal(bad.c.SIMQ.busy,null);assert(bad.ws.every(w=>w.stopped));
}

// 17) 작업자 수 = min(코어 − 1, 8, 메모리 예산). 모바일 2개까지, 저메모리 1~2개, 모르면 보수적으로
{
 const h=screeningHarness(),n=(cores,memGB,mobile)=>h.ev(`scrWorkerCount(${JSON.stringify({cores,memGB,mobile})})`);
 assert.equal(n(16,8),8);assert.equal(n(32,8),8);assert.equal(n(8,8),7);assert.equal(n(4,8),3);assert.equal(n(2,8),1);assert.equal(n(1,8),1);
 assert.equal(n(16,4),6);assert.equal(n(16,2),2);assert.equal(n(16,1),1);assert.equal(n(16,0.5),1);assert.equal(n(4,2),2);
 assert.equal(n(16,8,true),2);assert.equal(n(2,8,true),1);
 assert.equal(n(undefined,undefined),1);assert.equal(n(16,undefined),6);assert.equal(n(undefined,8),1);
 assert.equal(h.ev('scrWorkers()'),3);
 // 작업 수보다 많이 띄우지 않는다
 const few=screeningHarness(['d','e','f','g'],i=>10-i,{hardwareConcurrency:16,deviceMemory:8});few.ev('simScreen(1)');assert.equal(few.ws.length,4);
}
console.log('PASS 속도 개선: 순위는 작업자 수와 무관·대기열(중복 없음·done 뒤 배정)·작업자 수');

// 18) 실제 sim_worker.js: 작업 번호(job)를 진행·결과·done·오류에 그대로 되돌려 주고, 요청마다 만든 파이썬 객체(toPy)는 오류가 나도 해제하며, 함수 핸들은 한 번만 얻는다
(async()=>{
 const out=[];let made=0,freed=0,gets=0;
 const wk=vm.createContext({URL,self:{location:{href:'https://example.test/sim_worker.js'}},postMessage:m=>out.push(m)});
 vm.runInContext(fs.readFileSync(require.resolve('../sim_worker.js'),'utf8'),wk);
 wk.fake={toPy:()=>{made++;return {destroy(){freed++}}},globals:{get:()=>{gets++;return (stage,party,n,seed,extra)=>{if(JSON.parse(extra).boom)throw Error('boom');return JSON.stringify({n})}}}};
 vm.runInContext('ready=Promise.resolve({p:fake,ver:"t"})',wk);
 for(const job of [0,1,2])await wk.onmessage({data:{type:'run',id:7,job,stage:'op/a/b',n_runs:8,seed:1,mode:job===1?'manual':'auto',teams:[{key:'k'+job,party:{},options:job===2?{boom:1}:{}}]}});
 assert(out.length>0&&out.every(m=>m.id===7&&[0,1,2].includes(m.job)));
 for(const job of [0,1])assert.deepEqual(out.filter(m=>m.job===job).map(m=>m.type),job?['stage','stage','team','done']:['stage','team','done']);
 assert.deepEqual(out.filter(m=>m.job===2).map(m=>m.type),['stage','error']);
 assert.equal(made,3);assert.equal(freed,3,'toPy 객체 해제(오류가 나도)');assert.equal(gets,2,'run_auto·run_manual 핸들은 한 번만');
 console.log('PASS 작업자: 작업 번호 되돌림·파이썬 객체 해제·핸들 재사용');
})().catch(e=>{console.error(e);process.exit(1)});
