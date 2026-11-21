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
  assert.equal(E.PAINT_MS,200);}
}
suite(load(source));
const mutants=[
 ['중복 받음',s=>s.replace('lease.got.has(m.key)','false')],
 ['다 안 받은 done 인정',s=>s.replace("if(lease.got.size<lease.keys.size){o.error('결과 없이 끝난 작업',w,false);return}",'')],
 ['머리 비교 안 함',s=>s.replace('||h!==head','')],
 ['묶음 크기 상한 없음',s=>s.replace('Math.min(50,Math.ceil(','Math.min(1e9,Math.ceil(')],
 ['팀마다 시계 갱신 안 함',s=>s.replace('lease.got.add(m.key);w._last=now();','lease.got.add(m.key);')],
 ['간격 제한 없음',s=>s.replace('if(wait<=0){run();return}','run();return;')],
 ['끝 호출 버림(항상)',s=>s.replace('if(trailing)timer=setTimer(run,wait)','')],
];
for(const [name,f] of mutants){const src=f(source);assert.notEqual(src,source,name+': 바꿀 곳 없음');assert.throws(()=>suite(load(src)),assert.AssertionError,name);}
console.log('PASS executor batch: 크기·순서, key 거부·중복, done 조건, 머리 분리, 팀 단위 시계, 취소 보존, chunk 없음=지금, 크기 식, 갱신 간격 제한; mutations '+mutants.length+' rejected');
