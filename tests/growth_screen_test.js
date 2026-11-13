// 「클리어 추천 육성」 탐색의 예선(11/13, 정확도 우선):
//  ① growthStageSearch — 추천 예선과 같은 후보 순서(scrPick, 재점화 풀 포함)로 전 후보 8판 → 상위 20팀 32판 → 본선. 줄이지 않는다
//     2차는 1차 8판을 다시 돌리지 않는다(1차 raw 를 되돌려 보내고 24판만 — 추천 예선과 같음, 합산은 tests/screen_merge_test.py)
//  ② growthEvaluate — 예선은 전체 시간 상한이 없다: 엔진 준비는 내려받기 상한, 준비 뒤엔 팀 결과가 올 때마다 다시 재는 무진행 상한.
//     절전·탭 동결로 타이머가 늦게 돌았거나 탭이 가려져 있으면 끝내지 않는다(누적 결과를 버리지 않게)
//     작업자 풀·대기열은 화면 것 그대로(scrPool·simDispatch): 정상으로 끝나면 작업자를 살려 두고, 끊기면 풀을 끈다
// 화면 예선(simScreen) 쪽은 sim_timeout_test.js 9~14. 끝에서 고친 코드를 일부러 되돌려(결함 주입) 이 시험이 실패하는지 확인한다.
// 실행: node tests/growth_screen_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8'),ui=fs.readFileSync(require.resolve('../growth_ui.js'),'utf8');
const cut=(s,a,b)=>{const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i,'구간 없음: '+a);return s.slice(i,j)};
const SRC={plan:cut(html,'const SCR_ROUNDS=','const scrKey='),cmp:cut(html,'const scrCmp=','// 예선 상태 sc'),pool:cut(html,'// ── 작업자 풀·작업 대기열','// 이 기기의 시뮬 속도'),
 search:cut(ui,'async function growthStageSearch','async function growthStart'),evaluate:cut(ui,'function growthEvaluate','function growthMaybe')};
const key=k=>['a','b','c',k].sort().join(',');

// ① 탐색 흐름. o.stop = {call, done}: call 번째 평가가 done 팀만 끝낸 채 미완료로 돌아옴(무진행 상한·오류)
function searchHarness(src,o){
 const calls=[],teams=Array.from({length:o.teams},(_,i)=>({keys:['a','b','c','t'+i],v:i}));
 const ctx=vm.createContext({console,Object,Math,JSON,Set,Map,Infinity,Error,
  SIMQ:{seed:1,n:100,LOAD_MS:1000},GROW:{id:1},MODE:'auto',
  CFG:{restrict:{},defPenByContent:{},weights:{defenderPenalty:0}},R:['u0','u1','u2','u3'].map(k=>({key:k,el:'x'})),EXCL:new Set(),
  score:()=>[1,{}],rankAll:x=>x,quickIn:()=>({}),quickRank:()=>teams,rkOf:()=>o.rk||0,
  rkQuickTop:(c,st,all,n)=>{calls.push({rkPool:n});return o.rkTop?o.rkTop.map(i=>teams[i]):[]},
  growthJob:(t,k)=>({id:k,t}),simTeamLimit:()=>1000,GrowthGuide:{finalCost:n=>n},Date:{now:()=>1000},
  growthEvaluate:async(jobs,n,seed,c,st,id,deadline,env)=>{calls.push({keys:Array.from(jobs,j=>j.id),jobs:Array.from(jobs),n,final:!!env.final,stall:!!env.screenClock,deadline});
   const nth=calls.filter(x=>x.keys).length,stop=o.stop&&o.stop.call===nth?o.stop:null,done=stop?jobs.slice(0,stop.done):jobs;
   const r=Object.fromEntries(done.map(j=>[j.id,{clear:o.clear?o.clear(j.id,n):0.5,prog:0.5,ttk:20,...(o.noRaw?{}:{raw:'[raw'+n+']'})}]));
   if(stop)Object.defineProperty(r,'incomplete',{value:true});return r}});
 for(const s of [src.plan,src.cmp,src.search])vm.runInContext(s,ctx);
 const profile={results:Object.fromEntries(ctx.R.map(s=>[s.key,{}]))};
 return {ctx,calls,evals:()=>calls.filter(c=>c.keys),run:()=>vm.runInContext('growthStageSearch',ctx)({key:'op',name:'작전'},{tab:'a',name:'b'},profile,1)};
}

// ② 실제 growthEvaluate 를 가짜 시계·가짜 작업자로 돌린다
function evalHarness(src,n=8){
 let clock=1000,queue=[];const ws=[];
 const ctx=vm.createContext({console,Object,Math,Promise,Infinity,MODE:'auto',Date:{now:()=>clock},document:{hidden:false},
  setTimeout:(fn,ms)=>{const t={fn,at:clock+ms};queue.push(t);return t},clearTimeout:t=>{queue=queue.filter(x=>x!==t)},
  SIMQ:{LOAD_MS:180000,seed:1},GROW:{id:1,errors:[],versions:{engine:'v'}},simTeamLimit:()=>240000,
  location:{href:'https://test/index.html'},simOpt:()=>({}),growthPaint(){},growthMetric:r=>r,
  navigator:{hardwareConcurrency:4,deviceMemory:8},
  Worker:class{constructor(){ws.push(this)}postMessage(req){this.req=req;(this.log||(this.log=[])).push(req)}terminate(){this.stopped=true}}});
 vm.runInContext(src.pool,ctx);vm.runInContext(src.evaluate,ctx);
 const jobs=['j0','j1','j2','j3','j4','j5'].map(id=>({id,party:{}}));let out=null;
 vm.runInContext('growthEvaluate',ctx)(jobs,n,1,{key:'op'},{tab:'a',name:'b'},1,Infinity,{screenClock:{}}).then(r=>{out=r});
 // 작업자는 팀을 하나씩 받는다(대기열): team = 지금 맡은 팀의 결과, done 을 보내야 다음 팀이 온다
 const send=(w,m)=>w.onmessage({data:{id:w.req.id,job:w.req.job,...m}});
 const team=w=>send(w,{type:'team',key:w.req.teams[0].key,result:{ver:'v',clear:0.5,prog:0.7}}),done=w=>send(w,{type:'done'});
 return {ctx,ws,out:async()=>{await new Promise(setImmediate);return out},
  ready:()=>ws.forEach(w=>send(w,{type:'stage',id:undefined,msg:'준비 끝'})),
  team,done,serve:w=>{team(w);done(w)},busy:()=>ws.filter(w=>!w.stopped&&w._job!=null),
  finish:()=>{for(let g=0;g<100;g++){const w=ws.find(w=>!w.stopped&&w._job!=null);if(!w)return;team(w);done(w)}},
  // 시간이 흐르며 타이머가 제때 돈다
  tick:ms=>{const end=clock+ms;for(;;){queue.sort((a,b)=>a.at-b.at);if(!queue[0]||queue[0].at>end)break;const t=queue.shift();clock=t.at;t.fn()}clock=end},
  // 절전·탭 동결: 다음 타이머가 예정보다 ms 늦게 돈다
  freeze:ms=>{queue.sort((a,b)=>a.at-b.at);assert(queue.length);clock=queue[0].at+ms;queue.shift().fn()}};
}

async function suite(src){
 // 번갈아 순서: 빠른 계산 순(t0,t1…) 1 · 근사 점수 순(t29,t28…) 1
 const want=[];for(let i=0;i<15;i++)want.push(key('t'+i),key('t'+(29-i)));

 // A) 전 후보 8판 → 상위 20팀 32판 → 본선. 예선만 무진행 상한(screenClock)·기한 없음
 {const h=searchHarness(src,{teams:30,clear:(k,n)=>k===key('t7')?(n===8?0.6:0.9):k===key('t3')&&n===32?0.95:0.5}),r=await h.run(),e=h.evals();
  assert.deepEqual(e[0].keys,want);assert.equal(e[0].n,8);assert.equal(e[0].stall,true);assert.equal(e[0].deadline,Infinity);
  assert.equal(e[1].n,32);assert.equal(e[1].keys.length,20);assert.equal(e[1].keys[0],key('t7'),'8판 결과 순으로 2차에 올림');assert.equal(e[1].stall,true);
  assert(e[0].jobs.every(j=>j.options.raw_runs===true&&j.runs===undefined),'1차는 raw 를 달라고 함');
  assert(e[1].jobs.every(j=>j.runs===24&&j.options.run_offset===8&&j.options.merge_raw==='[raw8]'&&!('raw_runs' in j.options)),'2차 = 1차 8판 + 24판');
  assert(e[2].jobs.every(j=>j.runs===undefined&&!j.options),'본선은 그대로 100판');assert.equal(r.runs,30*8+20*24+3*100);
  // 1차 결과에 raw 가 없으면(옛 엔진 묶음) 2차는 32판을 다 돈다
  const old=searchHarness(src,{teams:30,noRaw:true}),ro=await old.run();
  assert(old.evals()[1].jobs.every(j=>j.runs===undefined&&j.options.raw_runs===true&&j.options.run_offset===undefined));assert.equal(ro.runs,30*8+20*32+3*100);
  assert.equal(e[2].final,true);assert.equal(e[2].n,100);assert.equal(e[2].stall,false);assert.equal(e[2].keys[0],key('t3'),'본선은 32판 결과 순');
  assert.equal(e[2].keys.length,3);assert(!('limited' in r));}

 // B) 재점화 풀: 재점화>0 일 때만 SCR_RK 팀을 후보에 번갈아 넣는다
 {const off=searchHarness(src,{teams:200});await off.run();
  assert(!off.calls.some(c=>c.rkPool),'재점화 0 이면 재점화 풀을 만들지 않음');assert.equal(off.evals()[0].keys.length,120);
  const on=searchHarness(src,{teams:200,rk:3,rkTop:[100,101,102]});await on.run();
  assert.deepEqual(on.calls[0],{rkPool:40});const first=on.evals()[0].keys;
  assert.equal(first.length,123);assert.deepEqual(first.slice(0,6),[key('t0'),key('t199'),key('t100'),key('t1'),key('t198'),key('t101')]);}

 // C) 예선이든 본선이든 다 못 끝내면 «미완료»(부분 결과로 넘어가지 않는다 — 멈추는 것은 「중단」뿐)
 for(const call of [1,2,3])await assert.rejects(searchHarness(src,{teams:30,stop:{call,done:5}}).run(),/미완료/);

 // D) 예선에 전체 시간 상한이 없다: 팀 결과가 200초마다 와도(총 20분) 끝까지 간다
 {const h=evalHarness(src);assert.equal(h.ws.length,3);h.ready();
  for(let i=0;i<6;i++){h.tick(200000);assert.equal(await h.out(),null);h.serve(h.ws[i%3])}
  const r=await h.out();assert(r&&!r.incomplete);assert.equal(Object.keys(r).length,6);assert(h.ws.every(w=>!w.stopped),'정상으로 끝나면 작업자를 끄지 않음');
  assert.deepEqual(h.ws.flatMap(w=>w.log).map(q=>q.teams[0].key).sort(),['j0','j1','j2','j3','j4','j5'],'팀마다 한 번씩');assert(h.ws.every(w=>w.log.every(q=>q.teams.length===1)));
  h.tick(10000000);assert(h.ws.every(w=>!w.stopped));
  // 대기열: 빨리 끝내는 작업자가 더 가져간다
  const q=evalHarness(src);q.ready();for(let i=0;i<4;i++)q.serve(q.ws[0]);assert.equal(q.ws[0].log.length,4);assert.equal(q.ws[1].log.length,1);
  q.finish();const rq=await q.out();assert(rq&&!rq.incomplete);assert.equal(Object.keys(rq).length,6);}

 // E) 엔진 준비는 내려받기 상한(3분), 준비 뒤 무진행(4분)이면 미완료로 끝낸다
 {const h=evalHarness(src);h.tick(179999);assert.equal(await h.out(),null);h.tick(1);const r=await h.out();assert(r&&r.incomplete);assert(h.ws.every(w=>w.stopped));
  const g=evalHarness(src);g.ready();g.team(g.ws[0]);g.tick(239999);assert.equal(await g.out(),null);g.tick(1);const q=await g.out();
  assert(q&&q.incomplete);assert.equal(Object.keys(q).length,1);assert(g.ws.every(w=>w.stopped),'끊기면 풀을 끈다');assert.equal(g.ctx.SIMQ.pool,null);}

 // F) 절전·탭 동결 복귀: 타이머가 10분 늦게 돌아도 끝내지 않고 누적 결과를 지킨다. 그 뒤 진짜 무진행이면 끝낸다
 {const h=evalHarness(src);h.ready();h.team(h.ws[0]);h.team(h.ws[1]);
  h.freeze(600000);assert.equal(await h.out(),null,'동결 복귀 직후 끝내면 안 됨');assert(h.ws.every(w=>!w.stopped));
  h.tick(200000);assert.equal(await h.out(),null);
  h.finish();
  const r=await h.out();assert(r&&!r.incomplete);assert.equal(Object.keys(r).length,6);
  const g=evalHarness(src);g.ready();g.team(g.ws[0]);g.freeze(600000);assert.equal(await g.out(),null);g.tick(240000);const q=await g.out();assert(q&&q.incomplete);}

 // G) 가려진 탭에서는 무진행 상한으로 끝내지 않는다
 {const h=evalHarness(src);h.ready();h.ctx.document.hidden=true;h.tick(3600000);assert.equal(await h.out(),null);
  h.ctx.document.hidden=false;h.tick(240000);const r=await h.out();assert(r&&r.incomplete);}
}

(async()=>{
 await suite(SRC);console.log('PASS 육성 예선: 번갈아 순서·끝까지·재점화 풀·미완료·상한 없음·준비/무진행 상한·동결 복귀·가려진 탭');
 // 결함 주입: 고친 코드를 되돌리면 실패해야 한다
 const rep=(s,a,b)=>{assert(s.includes(a),'주입 대상 없음: '+a);return s.replace(a,b)};
 const mutants={
  '번갈아 대신 이어 붙이기':{...SRC,plan:rep(SRC.plan,'for(let i=0;i<m;i++)for(const l of lists){const k=l[i];','for(const l of lists)for(let i=0;i<m;i++){const k=l[i];')},
  '재점화 풀 끔':{...SRC,plan:rep(SRC.plan,'SCR_RK=40','SCR_RK=0')},
  '2차 판 수 줄임':{...SRC,plan:rep(SRC.plan,'{n:32,top:20}','{n:16,top:10}')},
  '부분 결과로 넘어감':{...SRC,search:rep(SRC.search,"if(GROW.id!==id||r.incomplete||Object.keys(r).length!==jobs.length)throw Error('미완료');",'')},
  '예선에 무진행 상한 안 씀':{...SRC,search:rep(SRC.search,'...(!final?{screenClock:{}}:{})','')},
  '예선 60초 상한 되살림':{...SRC,evaluate:rep(SRC.evaluate,"stall.ready?simTeamLimit(n,'auto'):SIMQ.LOAD_MS","stall.ready?60000:SIMQ.LOAD_MS")},
  '팀 결과가 와도 다시 안 잼':{...SRC,evaluate:rep(SRC.evaluate,"team(j,m){if(stall)arm();",'team(j,m){')},
  '2차가 1차 판을 다시 돎':{...SRC,search:rep(SRC.search,"const raw=prev&&prev.n<n?prev.r[k]?.raw:null;",'const raw=null;')},
  '2차에 판 번호를 안 밂':{...SRC,search:rep(SRC.search,"run_offset:prev.n,",'')},
  '정상 종료에도 작업자를 끔':{...SRC,evaluate:rep(SRC.evaluate,"if(cut)simPoolDrop();",'simPoolDrop();')},
  '끊겨도 작업자를 안 끔':{...SRC,evaluate:rep(SRC.evaluate,"if(cut)simPoolDrop();",'')},
  '고정 분배(done 없이 다음 팀)':{...SRC,pool:rep(SRC.pool,"w._job=null;if(--left===0){o.done();return}feed(w);arm()}","w._job=null;if(--left===0){o.done();return}arm()}")},
  '준비 전에도 무진행 상한':{...SRC,evaluate:rep(SRC.evaluate,"stall.ready?simTeamLimit(n,'auto'):SIMQ.LOAD_MS","true?simTeamLimit(n,'auto')+1:SIMQ.LOAD_MS")},
  '동결 복귀에 끝냄':{...SRC,evaluate:rep(SRC.evaluate,'Date.now()-due>5000||','false||')},
  '가려진 탭에서도 끝냄':{...SRC,evaluate:rep(SRC.evaluate,"||(typeof document!=='undefined'&&document.hidden)",'')},
  '무진행이어도 안 끝냄':{...SRC,evaluate:rep(SRC.evaluate,'{arm();return;}finish(true);}','{arm();return;}arm();}')}};
 for(const [name,src] of Object.entries(mutants)){let caught=false;try{await suite(src)}catch(e){caught=true}
  assert(caught,'결함 주입이 통과해 버림: '+name);console.log('MUTATION caught:',name)}
 console.log('ALL OK growth screen');
})().catch(e=>{console.error(e);process.exit(1)});
