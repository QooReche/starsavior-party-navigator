// node tests/search_executor_batch_test.js
// 공통 실행기 묶음(o.chunk, A-2 — docs/fullscreen_measure_1121.md «묶음 후») 계약:
//  묶음 크기·순서, 팀 key 는 묶음 안 + 처음 것만 받음(남의 key·중복 거부), done 은 전부 받았을 때만, 요청 머리(판 수·옵션)가 다르거나 key 가 겹치면 끊음,
//  무진행 시계는 팀마다 갱신, 취소(drop)는 terminate 하고 이미 받은 팀은 남김, chunk 없으면 지금처럼 팀 하나씩. 일부러 깨뜨린 실행기는 실패해야 함.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../search_executor.js'),'utf8');

function load(src){const c=vm.createContext({setTimeout:()=>0,clearTimeout(){},Date});vm.runInContext(src,c);return c.SearchExecutor;}
// 가짜 작업자: 받은 요청을 쌓아 두고, 시험이 reply 로 답을 고른다
function env(E,cap=1){
 const made=[];let clock=1000;
 const ex=E.shared({capacity:()=>cap,priority:()=>0,loadMs:()=>1000,now:()=>clock,setTimer:()=>0,clearTimer(){},
  makeWorker:()=>{const w={posts:[],postMessage(m){this.posts.push(JSON.parse(JSON.stringify(m)))},terminate(){this.ended=true}};made.push(w);return w}});
 return {ex,made,tick(ms){clock+=ms},send:(w,m)=>{const last=w.posts.at(-1);w.onmessage({data:{id:last.id,requestId:last.id,owner:last.owner,revision:last.revision,job:last.job,jobId:last.jobId,...m}})}};
}
function job(k,n=1,extra={}){return {key:k,n,extra}}
function dispatch(t,jobs,chunk,log){
 const ws=t.ex.reserve(jobs.length);
 return t.ex.dispatch(ws,jobs,{id:7,chunk,live:()=>true,msg:j=>({type:'run',n_runs:j.n,options:j.extra,teams:[{key:j.key,party:{units:[j.key]}}]}),
  team:(j,m)=>log.push(['team',j.key,m.result]),done:()=>log.push(['done']),error:(msg)=>log.push(['error',msg])});
}
const answer=(t,w,keys)=>{for(const [i,k] of keys.entries()){t.send(w,{type:'stage',msg:`시뮬 ${i+1}/${keys.length}팀`});t.send(w,{type:'team',key:k,result:k})}t.send(w,{type:'done'})};

function suite(E){
 // 1) 묶음 크기·순서·결과 한 번씩·done 한 번
 {const t=env(E),log=[];dispatch(t,['a','b','c','d','e','f','g'].map(k=>job(k)),3,log);const w=t.made[0];
  for(let i=0;i<3;i++)answer(t,w,w.posts.at(-1).teams.map(x=>x.key));
  assert.deepEqual(w.posts.map(p=>p.teams.map(x=>x.key)),[['a','b','c'],['d','e','f'],['g']],'3팀씩 순서대로');
  assert.deepEqual(log.filter(x=>x[0]==='team').map(x=>x[1]),['a','b','c','d','e','f','g']);assert.deepEqual(log.filter(x=>x[0]!=='team'),[['done']]);}
 // 2) 남의 key·중복은 무시, 3) 다 안 받고 done 이면 오류
 {const t=env(E),log=[];dispatch(t,['a','b','c'].map(k=>job(k)),3,log);const w=t.made[0];
  t.send(w,{type:'team',key:'zz',result:'x'});t.send(w,{type:'team',key:'a',result:1});t.send(w,{type:'team',key:'a',result:2});t.send(w,{type:'team',key:'b',result:3});
  assert.deepEqual(log,[['team','a',1],['team','b',3]],'남의 key·중복 거부');
  t.send(w,{type:'done'});assert.deepEqual(log.at(-1),['error','결과 없이 끝난 작업'],'다 안 받은 done 은 오류');}
 // 4) 요청 머리(판 수·옵션)가 다르거나 key 가 겹치면 묶음을 끊음 — msg 는 작업마다 한 번만 만든다
 {const t=env(E),log=[];let made=0;const ws=t.ex.reserve(9),jobs=[job('a'),job('b'),job('c',2),job('d',2),job('d',2),job('e',2,{x:1})];
  t.ex.dispatch(ws,jobs,{id:7,chunk:10,live:()=>true,msg:j=>{made++;return {type:'run',n_runs:j.n,options:j.extra,teams:[{key:j.key}]}},team:(j,m)=>log.push(m.key),done:()=>log.push('done'),error:m=>log.push(m)});
  const w=t.made[0];for(let i=0;i<4;i++)answer(t,w,w.posts.at(-1).teams.map(x=>x.key));
  assert.deepEqual(w.posts.map(p=>[p.n_runs,p.teams.map(x=>x.key)]),[[1,['a','b']],[2,['c','d']],[2,['d']],[2,['e']]]);
  assert.equal(made,jobs.length,'msg 는 작업마다 한 번');assert.equal(log.at(-1),'done');}
 // 5) 무진행 시계는 팀마다 갱신(w._last), 속도 표본용 w._n 은 판 수
 {const t=env(E),log=[];dispatch(t,['a','b'].map(k=>job(k,8)),2,log);const w=t.made[0];const t0=w._last;
  t.tick(500);t.send(w,{type:'team',key:'a',result:1});assert.equal(w._last,t0+500);t.tick(500);t.send(w,{type:'stage',msg:'시뮬 2/2팀'});assert.equal(w._last,t0+1000);assert.equal(w._n,8);}
 // 6) 취소: terminate, 이미 받은 팀은 남고 done 없음
 {const t=env(E),log=[];dispatch(t,['a','b','c'].map(k=>job(k)),3,log);const w=t.made[0];t.send(w,{type:'team',key:'a',result:1});
  t.ex.drop('reco',7);assert.equal(w.ended,true);t.send(w,{type:'team',key:'b',result:2});assert.deepEqual(log,[['team','a',1]],'취소 뒤 소식 무시, 받은 팀은 남음');}
 // 7) chunk 없음 = 지금처럼 팀 하나씩
 {const t=env(E,2),log=[];dispatch(t,['a','b','c'].map(k=>job(k)),undefined,log);
  assert.deepEqual(t.made.map(w=>w.posts.map(p=>p.teams.length)),[[1],[1]]);}
 // 8) 묶음 크기 식 min(50, ceil(팀/(작업자×40)))
 assert.deepEqual([[10626,8],[120,8],[10626,1],[0,8],[200,2]].map(([a,b])=>E.chunkSize(a,b)),[34,1,50,1,3]);
 // 9) 화면 갱신 간격 제한(throttle, A-1): 첫 호출 바로, 간격 안은 끝에 한 번, trailing:false 면 끝 호출 버림, live 거짓이면 버림, flush·cancel
 {let clock=0,q=[];const env={now:()=>clock,setTimer:(fn,ms)=>{const t={fn,at:clock+ms};q.push(t);return t},clearTimer:t=>{q=q.filter(x=>x!==t)}};
  const tick=ms=>{clock+=ms;for(const t of q.filter(t=>t.at<=clock)){q=q.filter(x=>x!==t);t.fn()}};
  let n=0,alive=true;const f=E.throttle(()=>n++,200,()=>alive,env);
  f();assert.equal(n,1,'첫 호출 바로');f();f();f();assert.equal(n,1);assert.equal(q.length,1,'끝 호출 하나만 예약');tick(199);assert.equal(n,1);tick(1);assert.equal(n,2,'간격 끝에 한 번');
  tick(500);f();assert.equal(n,3,'간격 지나면 바로');f();f.flush();assert.equal(n,4,'flush');f();f.cancel();tick(1000);assert.equal(n,4,'cancel');
  f();assert.equal(n,5);f();alive=false;tick(300);assert.equal(n,5,'live 거짓이면 버림');alive=true;
  let m=0;const g=E.throttle(()=>m++,200,undefined,{...env,trailing:false});tick(1000);g();g();g();assert.equal(m,1);assert.equal(q.length,0,'trailing:false 는 타이머 없음');tick(200);g();assert.equal(m,2);
  // 시계가 뒤로 가도(1시간) 대기는 ms 이하 — 진행 표시가 멈추지 않음
  let b=0;const h=E.throttle(()=>b++,200,undefined,env);h();assert.equal(b,1);clock-=3600000;h();assert.equal(q.length,1);assert.ok(q[0].at-clock<=200,'대기 상한 '+(q[0].at-clock));tick(200);assert.equal(b,2,'시계가 뒤로 가도 간격 끝에 한 번');
  assert.equal(E.PAINT_MS,200);}
 // 10) 작업자 수명(HANDOFF 27②): 취소는 그 묶음을 돌리는 작업자만 끄고, 놀고 있는 작업자는 owner 와 무관하게 살아서 다음 계산이 다시 씀
 const run=(t,owner,id,keys)=>{const log=[];t.ex.dispatch(t.ex.reserve(keys.length),keys.map(k=>job(k)),{owner,id,live:()=>true,
  msg:j=>({type:'run',n_runs:j.n,options:j.extra,teams:[{key:j.key}]}),team:(j,m)=>log.push([j.key,m.result]),done:()=>log.push('done'),error:m=>log.push(m)});return log};
 {const t=env(E,2);const a=run(t,'reco',1,['a']);answer(t,t.made[0],['a']);assert.deepEqual(a,[['a','a'],'done']);
  t.ex.drop('reco');assert.equal(t.made[0].ended,undefined,'입력 변경(전체 취소)에도 놀던 작업자는 살림');
  const b=run(t,'reco',2,['b']);assert.equal(t.made.length,1,'새 계산은 놀던 작업자를 다시 씀(새 부팅 없음)');answer(t,t.made[0],['b']);assert.deepEqual(b,[['b','b'],'done']);}
 {const t=env(E,2);run(t,'reco',1,['a']);answer(t,t.made[0],['a']);           // made[0] = 놀고 있음(마지막 묶음 reco)
  run(t,'reco',2,['b']);assert.equal(t.made[0].posts.length,2,'놀던 작업자가 먼저 받음');
  run(t,'growth',3,['c']);const busy=t.made[0],other=t.made[1];
  t.ex.drop('reco');assert.equal(busy.ended,true,'바쁜 작업자는 끔');assert.equal(other.ended,undefined,'다른 owner 의 바쁜 작업자는 그대로');
  assert.deepEqual([...t.ex.state.workers],[other]);}
 // 11) 늦은 응답: 같은 id·같은 팀 key 로 다른 owner 에 다시 맡긴 뒤 옛 작업의 답(옛 token·owner)은 버림
 {const t=env(E,1);run(t,'reco',5,['a']);const w=t.made[0],old=w.posts.at(-1);answer(t,w,['a']);
  const log=run(t,'direct',5,['a']);assert.equal(t.made.length,1);
  w.onmessage({data:{id:old.id,requestId:old.id,owner:old.owner,revision:old.revision,job:old.job,jobId:old.jobId,type:'team',key:'a',result:'옛것'}});
  assert.deepEqual(log,[],'옛 owner·token 응답 거부');t.send(w,{type:'team',key:'a',result:'새것'});assert.deepEqual(log,[['a','새것']]);}
 {const t=env(E,1);run(t,'reco',5,['a']);const w=t.made[0],old=w.posts.at(-1);answer(t,w,['a']);
  const log=run(t,'reco',5,['a']);    // 같은 owner·id·key·job 번호 — 옛 답과 갈리는 것은 token(jobId)뿐
  w.onmessage({data:{id:old.id,requestId:old.id,owner:old.owner,revision:old.revision,job:old.job,jobId:old.jobId,type:'team',key:'a',result:'옛것'}});
  assert.deepEqual(log,[],'같은 owner 라도 옛 token 응답 거부');}
 // 12) requestId·group 취소 격리: 같은 owner 의 다른 요청은 그대로
 {const t=env(E,2);run(t,'direct',1,['a']);run(t,'direct',2,['b']);t.ex.drop('direct',1);
  assert.equal(t.made[0].ended,true);assert.equal(t.made[1].ended,undefined,'다른 요청은 안 끔');}
 {const t=env(E,2),go=g=>t.ex.dispatch(t.ex.reserve(1),[job(g)],{owner:'cdirect',id:9,group:g,live:()=>true,msg:j=>({type:'run',n_runs:1,teams:[{key:j.key}]}),team(){},done(){},error(){}});
  go('boss1');go('boss2');t.ex.drop('cdirect',9,'boss1');
  assert.equal(t.made[0].ended,true);assert.equal(t.made[1].ended,undefined,'같은 owner·id 의 다른 group 은 안 끔');}
 // 13) trimIdle: 놀고 있는 작업자만 정리(별도 풀 탐색 직전), 바쁜 작업자는 그대로
 {const t=env(E,2);run(t,'reco',1,['a']);answer(t,t.made[0],['a']);run(t,'growth',2,['b']);run(t,'growth',2,['c']);
  const [idle,busy]=[t.made[0],t.made[1]];assert.equal(idle.posts.length,2,'놀던 작업자가 다시 받음');answer(t,idle,['b']);
  t.ex.trimIdle();assert.equal(idle.ended,true,'놀던 작업자 정리');assert.equal(busy.ended,undefined,'바쁜 작업자 유지');assert.deepEqual([...t.ex.state.workers],[busy]);}
}
suite(load(source));
const mutants=[
 ['중복 받음',s=>s.replace('lease.got.has(m.key)','false')],
 ['다 안 받은 done 인정',s=>s.replace("if(lease.got.size<lease.keys.size){o.error('결과 없이 끝난 작업',w,false);return}",'')],
 ['머리 비교 안 함',s=>s.replace('||h!==head','')],
 ['묶음 크기 상한 없음',s=>s.replace('Math.min(50,Math.ceil(','Math.min(1e9,Math.ceil(')],
 ['팀마다 시계 갱신 안 함',s=>s.replace('lease.got.add(m.key);w._last=now();','lease.got.add(m.key);')],
 ['간격 제한 없음',s=>s.replace('if(wait<=0){run();return}','run();return;')],
 ['대기 상한 없음',s=>s.replace('setTimer(run,Math.min(ms,wait))','setTimer(run,wait)')],
 ['끝 호출 버림(항상)',s=>s.replace('if(trailing)timer=setTimer(run,Math.min(ms,wait))','')],
 ['취소 때 놀던 작업자도 끔(옛 동작)',s=>s.replace('if(w._lease&&matches(w._lease.batch))','if(matches(w._lease?.batch||w._lastBatch))')],
 ['취소 때 owner 무관하게 바쁜 작업자 끔',s=>s.replace('if(w._lease&&matches(w._lease.batch))','if(w._lease)')],
 ['trimIdle 이 바쁜 작업자도 끔',s=>s.replace('if(!w._lease)simRelease(w,true)','simRelease(w,true)')],
 ['group 검사 없음',s=>s.replace('&&(group==null||b.o.group===group)','')],
 ['token 검사 없음',s=>s.replace('||m.jobId!=null&&m.jobId!==lease.token','')],
];
// 별도 풀 탐색(길드 legacy·코스모 3보스·길드 daily)은 자기 풀을 띄우기 직전에 공용 풀의 놀던 작업자를 정리해야 함(두 풀 동시 상주 방지)
function trimWiring(page,daily){
 for(const call of ['GuildPlanner.search({S,G,V,','CosmoSearch.search({S,bosses:']){const i=page.indexOf(call);assert.ok(i>0,call);
  assert.match(page.slice(Math.max(0,i-120),i),/simPoolTrimIdle\(\);\s*const out=await $/,call+' 직전에 trimIdle')}
 const i=daily.indexOf('GuildPlanner.search({...cx,session');assert.ok(i>0);assert.match(daily.slice(Math.max(0,i-120),i),/simPoolTrimIdle\(\);\s*const out=await $/,'daily 직전에 trimIdle');
 assert.match(page,/function simPoolTrimIdle\(\)\{return SIM_EXEC\.trimIdle\(\)\}/);}
const PAGE=fs.readFileSync(require.resolve('../party_template.html'),'utf8'),DAILY=fs.readFileSync(require.resolve('../guild_daily_page.js'),'utf8');
trimWiring(PAGE,DAILY);
for(const [name,f,g] of [['daily trim 없음',x=>x,x=>x.replace(/if\(typeof simPoolTrimIdle==='function'\)simPoolTrimIdle\(\);\n(\s*const out=await GuildPlanner.search)/,'$1')],
 ['코스모 trim 없음',x=>x.replace(/if\(typeof simPoolTrimIdle==='function'\)simPoolTrimIdle\(\);\n(  const out=await CosmoSearch)/,'$1'),x=>x]]){
 const p2=f(PAGE),d2=g(DAILY);assert.ok(p2!==PAGE||d2!==DAILY,name+': 바꿀 곳 없음');assert.throws(()=>trimWiring(p2,d2),assert.AssertionError,name)}
for(const [name,f] of mutants){const src=f(source);assert.notEqual(src,source,name+': 바꿀 곳 없음');assert.throws(()=>suite(load(src)),assert.AssertionError,name);}
console.log('PASS executor batch: 크기·순서, key 거부·중복, done 조건, 머리 분리, 팀 단위 시계, 취소 보존, chunk 없음=지금, 크기 식, 갱신 간격 제한(시계 역행 상한), 작업자 수명(놀던 작업자 유지·trimIdle·늦은 응답·취소 격리); mutations '+mutants.length+' rejected');
