// node tests/fullscreen_test.js
// 후보 전체 훑기(CFG.recommendation.fullScreen, 기본 끔 — docs/fullscreen_measure_1121.md)
//  끔: 요청·예선 상태가 지금과 같음(필드도 안 붙음). 켬 + 깰 수 있는 팀 있음(쉬운 스테이지): 끔과 같음.
//  켬 + 전원 «못 깸»: 후보 전체 1판 → 상위 «예선 후보 수» → 예선 8판 → 32판(24판 이어 돌리기). 화면 경로(simScreen)·직접 편성 묶음 경로(recoCalculate) 둘 다.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(ROOT,'party_template.html'),'utf8'),rt=fs.readFileSync(path.join(ROOT,'recommend_runtime.js'),'utf8');
const section=(s,a,b)=>{const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i,'구간 없음: '+a);return s.slice(i,j)};
const CFG0=require('../party_contents.json');
assert.equal(CFG0.recommendation.fullScreen,false,'기본값은 끔');
const plain=x=>JSON.parse(JSON.stringify(x));
const mk=(keys,vd,v)=>({keys,combo:keys.map(key=>({s:{key}})),vd,v,q:{rounds:1,left:0}});
const NAMES=Array.from({length:200},(_,i)=>'t'+String(i).padStart(3,'0'));
const keyOf=k=>['a','b','c',k].sort().join(',');
// 진행도: 빠른 계산 뒤쪽(t150~)이 실제로는 강함 — 훑기가 없으면 예선 후보(80)에 못 듦
const progOf=key=>{const m=key.match(/t(\d{3})/),i=+m[1];return i>=150?0.5+i/1000:0.1+i/10000};
function teamsOf(vds){return NAMES.map((k,i)=>mk(['a','b','c',k],vds(i),200-i))}

// ── 화면 경로(simScreen) ── 가짜 작업자는 요청마다 바로 결과·done 을 돌려줌
function screenRun(full,vds,{stopAfter=null}={}){
 const posts=[],teams=teamsOf(vds),CFG=plain(CFG0);CFG.recommendation.fullScreen=full;
 const c=vm.createContext({CFG,recommendationPolicyTag:()=>[],PLACEMENT_CACHE:{has:()=>true},console,MODE:'auto',MM:'',MI:{pending:null},miMode:()=>false,
  SIMQ:{n:100,seed:1,busy:null,res:{},scr:{},LOAD_MS:180000,RUN_MS:240000},LASTQ:{1:{rows:teams.slice(0,3),all:teams,total:teams.length}},cur:[{tab:'a',name:'b'}],
  contents:[{key:'op'}],$:()=>({value:'0'}),rkOf:()=>0,starOf:()=>0,simParty:t=>({units:t.keys}),teamBreak:()=>null,brkLv:()=>1,
  simMain:r=>r,simCls:()=>'',esc:String,simOpt:()=>({}),document:{querySelector:()=>null,hidden:false},
  navigator:{hardwareConcurrency:3,deviceMemory:8},location:{href:'https://test/index.html'},Date,performance:{now:()=>0},
  setTimeout:()=>0,clearTimeout(){},run(){},
  Worker:class{postMessage(req){posts.push({req,msg:c.SIMQ.msg});const send=m=>this.onmessage({data:{id:req.id,job:req.job,...m}});
   if(stopAfter!=null&&posts.length>stopAfter){this.parked=req;return}
   send({type:'stage',id:undefined,msg:'준비 끝'});const k=req.teams[0].key,n=req.n_runs+(req.teams[0].options.run_offset||0),p=progOf(k);
   send({type:'team',key:k,result:{n,clear:0,prog:p,progs:[p],via:{coop:0},ttk:20,...(req.teams[0].options.raw_runs?{raw:'[raw'+n+']'}:{})}});send({type:'done'})}
   terminate(){this.stopped=true}}});
 vm.runInContext(fs.readFileSync(require.resolve('../search_executor.js'),'utf8'),c);
 for(const [a,b] of [['const simSigB=','// 표시 상태는'],['function simInvalidate()','// 자동 확인'],
  ['function simStart(',"document.querySelectorAll('input[name=\"runs\"]')"],['const SCR_ROUNDS=','function simWaiting(']])vm.runInContext(section(html,a,b),c);
 assert.equal(vm.runInContext('simScreen(1)',c),true);
 return {c,posts,sc:()=>plain(Object.values(c.SIMQ.scr)[0]),ev:s=>vm.runInContext(s,c)};
}
const legs=posts=>{const out=[];for(const p of posts){const n=p.req.n_runs,last=out[out.length-1];if(last&&last.n===n)last.keys.push(p.req.teams[0].key);else out.push({n,keys:[p.req.teams[0].key]})}return out};
const reqs=posts=>plain(posts.map(p=>({n:p.req.n_runs,team:p.req.teams[0]})));
const hard=()=>'hard',easy=i=>i===5?'tight':'hard';

{
 const off=screenRun(false,hard),L=legs(off.posts);
 assert.deepEqual(L.map(x=>[x.n,x.keys.length]),[[8,80],[24,20]],'끔: 지금 예선(8판 80팀 → 24판 20팀)');
 assert(!('full' in off.sc())&&!('res0' in off.sc()),'끔: 예선 상태에 훑기 필드 없음');
 assert(!L[0].keys.includes(keyOf('t199')),'끔: 뒤쪽 강한 팀은 예선 후보 밖(시험 전제)');
 // 켬 + 깰 수 있는 팀 있음 = 끔과 요청·상태 모두 같음
 const offE=screenRun(false,easy),onE=screenRun(true,easy);
 assert.deepEqual(reqs(onE.posts),reqs(offE.posts),'켬 + 쉬운 스테이지: 요청 같음');
 assert.deepEqual(plain(onE.sc()),plain(offE.sc()),'켬 + 쉬운 스테이지: 예선 상태 같음');
 // 켬 + 전원 못 깸 = 훑기 단계 추가
 const on=screenRun(true,hard),M=legs(on.posts),sc=on.sc();
 assert.deepEqual(M.map(x=>[x.n,x.keys.length]),[[1,200],[8,80],[24,20]],'켬: 1판 200팀 → 8판 80팀 → 24판 20팀');
 assert.deepEqual(M[0].keys,teamsOf(hard).map(t=>keyOf(t.keys[3])),'훑기는 빠른 계산 순서 그대로 전부');
 assert(on.posts.filter(p=>p.req.n_runs===1).every(p=>!p.req.teams[0].options.raw_runs&&!p.req.teams[0].options.run_offset),'훑기는 raw 를 안 받음');
 assert(on.posts.filter(p=>p.req.n_runs===24).every(p=>p.req.teams[0].options.run_offset===8&&p.req.teams[0].options.merge_raw),'2차는 1차 8판에 이어 돌림');
 assert.equal(sc.fullDone,true);assert.equal(sc.fullN,80);assert.equal(sc.pool.length,80);assert.equal(sc.total,80);
 const want=NAMES.slice(150).map(keyOf).reverse();
 assert.deepEqual(sc.pool.slice(0,50),want,'예선 후보 = 1판 결과 순(진행도 높은 뒤쪽 팀부터)');
 assert.equal(sc.order[0],keyOf('t199'),'최종 예선 1위 = 진행도 최고');
 assert.equal(sc.done,true);assert.equal(sc.short,false);
 assert(on.posts.slice(1,200).every(p=>/^후보 전체 훑는 중/.test(p.msg)),'훑는 동안 진행 문구');
 assert(on.posts.slice(201,280).every(p=>/^후보 거르는 중/.test(p.msg)),'예선 진행 문구');
}
// 진행 문구: 훑는 동안 «후보 전체 훑는 중»
{
 const on=screenRun(true,hard,{stopAfter:30});
 assert.match(on.c.SIMQ.msg,/^후보 전체 훑는 중 \d+\/200$/);assert.equal(on.sc().round,-1);
 // 「지금까지 결과로 보기」: 1판 결과 순으로 닫고 short, 안내 문구
 on.ev('scrStop()');const sc=on.sc();
 assert.equal(sc.done,true);assert.equal(sc.short,true);assert.equal(sc.fullDone,false);
 assert(sc.order.length>0&&sc.order.length<200);
 const got=Object.keys(sc.res0);assert.deepEqual(sc.order,got.slice().sort((a,b)=>progOf(b)-progOf(a)));
 assert.match(on.ev('scrNote(1,cur[0])'),/후보 전체 200팀 중 \d+팀만 훑었음/);
 // 「끝까지 확인」: 남은 훑기만 이어서
 const before=on.posts.length,seen=new Set(got);
 assert.equal(on.ev('simScreen(1,true)'),true);
 const first=on.posts.slice(before).map(p=>p.req);assert(first.length>0);
 assert(first.every(r=>r.n_runs===1&&!seen.has(r.teams[0].key)),'이미 훑은 팀은 다시 안 돎');
}
// 훑기 중 1판 결과가 하나도 없을 때 「지금까지 결과로 보기」 = 취소
{
 const on=screenRun(true,hard,{stopAfter:0});on.ev('scrStop()');
 assert.equal(Object.keys(on.c.SIMQ.scr).length,0,'결과 없음 → 예선 상태 지움(지금과 같음)');
}
// 순수 함수: 조건
{
 const c=vm.createContext({CFG:plain(CFG0)});vm.runInContext(section(html,'const SCR_ROUNDS=','const scrKey='),c);
 const all=[mk(['a','b','c','d'],'hard',1),mk(['a','b','c','e'],'hard',1),mk(['a','b','c','f'],'hard',1)];
 c.all=all;assert.equal(vm.runInContext('scrFullKeys(all,["x"])',c),null,'끔');
 c.CFG.recommendation.fullScreen=true;assert.deepEqual(plain(vm.runInContext('scrFullKeys(all,["x"])',c)),['a,b,c,d','a,b,c,e','a,b,c,f']);
 assert.equal(vm.runInContext('scrFullKeys(all,["x","y","z"])',c),null,'후보 전체가 예선 후보보다 많지 않으면 훑지 않음');
 all[2].vd='tight';assert.equal(vm.runInContext('scrFullKeys(all,["x"])',c),null,'깰 수 있는 팀 있음');
 assert.equal(vm.runInContext('scrFullKeys([],[])',c),null);
}

// ── 직접 편성 묶음 경로(recoCalculate → recoScreenCalculate → recoEvaluate, 실제 공통 실행기) ──
async function bundleRun(full,vds){
 const trace=[],CFG=plain(CFG0);CFG.recommendation.fullScreen=full;
 const ctx=vm.createContext({console,URL,Date,setTimeout,clearTimeout,CFG,navigator:{hardwareConcurrency:3},document:{hidden:false},location:{href:'https://synthetic.test/index.html'},
  SIMQ:{LOAD_MS:180000,res:{},scr:{},meta:{}},RECO:{},LASTQ:{},recoIdentity:()=> 'fixed',recoProgressPaint(){},directResultsPaint(){},simTeamLimit:()=>240000,simRateAdd(){},goalVal:r=>r?.clear,
  RecommendPipeline:require('../recommend_pipeline'),SCR_RK:0,rkQuickTop:()=>[],messages:[],
  Worker:class{postMessage(m){trace.push(plain(m));setImmediate(()=>{if(this.dead)return;const send=x=>this.onmessage({data:{...m,...x}});
   send({type:'stage',msg:'준비 끝'});const t=m.teams[0],n=m.n_runs+(t.options?.run_offset||0),p=progOf(t.key)||0.5;
   send({type:'team',key:t.key,result:{ver:'synthetic',n,clear:0,prog:p,progs:[p],...(t.options?.raw_runs?{raw:'[raw]'}:{})}});send({type:'done'});});}terminate(){this.dead=true;}}});
 vm.runInContext(fs.readFileSync(path.join(ROOT,'search_executor.js'),'utf8'),ctx);
 vm.runInContext(section(html,'const SCR_WMAX=','// 이 기기의 시뮬 속도'),ctx);
 for(const [a,b] of [['const SCR_ROUNDS=','const scrKey='],['const scrCmp=','function scrNote('],['function recoScreenSequence(','function simWaiting(']])vm.runInContext(section(html,a,b),ctx);
 vm.runInContext(section(rt,'function recoEvaluate(','async function recoEnsure('),ctx);
 ctx.ckey=combo=>combo.map(x=>x.s.key).sort().join(',');
 let rowsN=3;const all=teamsOf(vds),task={owner:'reco',request:0,engine:'synthetic'};
 const origEval=ctx.recoEvaluate;ctx.recoEvaluate=(s,t,jobs,n,o)=>{ctx.messages.push(o.label||(o.screen?'예선':'본선'));return origEval(s,t,jobs,n,o)};
 const snap={key:'fixed',c:{key:'op',parties:1},st:{tab:'a',name:'b'},seed:1,n:4,options:{},screenKey:()=> 'scr',
  plan:()=>({all,rows:all.slice(0,rowsN),total:all.length}),sig:t=>ckeyOf(t),party:t=>({units:t.keys}),breakFor:()=>null,result:t=>ctx.SIMQ.res[ckeyOf(t)],
  more(p,n){rowsN=n},meta:{parts:Array.from({length:8},()=>({}))},first:()=>null};
 const ckeyOf=t=>t.keys.slice().sort().join(',');
 ctx.RECO.task=task;await ctx.recoCalculate(snap,task);ctx.simPoolDrop('reco');
 return {trace,sc:plain(ctx.SIMQ.scr.scr),messages:ctx.messages};
}
(async()=>{
 const off=await bundleRun(false,hard),on=await bundleRun(true,hard),offE=await bundleRun(false,easy),onE=await bundleRun(true,easy);
 const strip=t=>t.map(m=>({n:m.n_runs,team:m.teams[0]}));
 assert.deepEqual(legs(off.trace.map(req=>({req}))).map(x=>[x.n,x.keys.length]),[[8,80],[24,20],[4,9]],'묶음 끔: 예선 → 본선(목표 미달이라 9팀)');
 assert.deepEqual(legs(on.trace.map(req=>({req}))).map(x=>[x.n,x.keys.length]),[[1,200],[8,80],[24,20],[4,9]],'묶음 켬: 훑기 추가');
 assert.deepEqual(strip(onE.trace),strip(offE.trace),'묶음 켬 + 쉬운 스테이지: 요청 같음');
 assert.deepEqual(onE.sc,offE.sc,'묶음 켬 + 쉬운 스테이지: 예선 상태 같음');
 assert(!('full' in off.sc));assert.equal(on.sc.order[0],keyOf('t199'));
 assert.deepEqual(on.messages.slice(0,3),['후보 전체 훑는 중','예선','예선'],'진행 문구');
 assert.deepEqual(off.messages.slice(0,2),['예선','예선']);
 console.log('PASS fullScreen: 끔=지금 그대로(필드 없음), 켬+쉬움=끔과 같음, 켬+전원 못 깸=1판 전체→8→32(화면·묶음), 멈춤·이어 하기, 조건');
})().catch(e=>{console.error(e);process.exitCode=1;});
