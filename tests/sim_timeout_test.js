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
