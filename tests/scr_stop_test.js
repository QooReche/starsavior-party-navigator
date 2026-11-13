// 「클리어 추천 육성」 탐색(growthStageSearch)의 예선(11/13, 정확도 우선): 추천 예선과 같은 후보 순서(scrPick, 재점화 풀 포함)로
// 전 후보 8판 → 상위 20팀 32판을 줄이지 않고 끝까지 돈다. 예선 중 「지금까지 결과로 보기」(GROW.partial)로 멈추면
// 끝난 팀으로 순위를 정해 본선으로 가고 limited 로 알린다. 화면 예선(simScreen) 쪽은 sim_timeout_test.js 9~14.
// 끝에서 고친 코드를 일부러 되돌려(결함 주입) 이 시험이 실패하는지 확인한다.
// 실행: node tests/scr_stop_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8'),ui=fs.readFileSync(require.resolve('../growth_ui.js'),'utf8');
const cut=(s,a,b)=>{const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i,'구간 없음: '+a);return s.slice(i,j)};
const SRC={plan:cut(html,'const SCR_ROUNDS=','const scrKey='),cmp:cut(html,'const scrCmp=','// 예선 상태 sc'),
 search:cut(ui,'async function growthStageSearch','async function growthStart'),limited:cut(ui,'function growthLimitedHtml','function growthNonePaint')};
const key=k=>['a','b','c',k].sort().join(',');

// o.stop = {call, done}: call 번째 평가에서 done 팀만 끝낸 채 사용자가 「지금까지 결과로 보기」를 누른 것처럼(GROW.partial + 미완료 결과)
// o.clear(key, n) = 그 팀의 n판 클리어율
function harness(src,o){
 const calls=[],teams=Array.from({length:o.teams},(_,i)=>({keys:['a','b','c','t'+i],v:i}));
 const ctx=vm.createContext({console,Object,Math,JSON,Set,Map,Infinity,Error,
  SIMQ:{seed:1,n:100,LOAD_MS:1000},GROW:{id:1},MODE:'auto',
  CFG:{restrict:{},defPenByContent:{},weights:{defenderPenalty:0}},R:['u0','u1','u2','u3'].map(k=>({key:k,el:'x'})),EXCL:new Set(),
  score:()=>[1,{}],rankAll:x=>x,quickIn:()=>({}),quickRank:()=>teams,rkOf:()=>o.rk||0,
  rkQuickTop:(c,st,all,n)=>{calls.push({rkPool:n});return o.rkTop?o.rkTop.map(i=>teams[i]):[]},
  growthJob:(t,k)=>({id:k,t}),simTeamLimit:()=>1000,GrowthGuide:{finalCost:n=>n},Date:{now:()=>1000},
  growthEvaluate:async(jobs,n,seed,c,st,id,deadline,env)=>{const call={keys:Array.from(jobs,j=>j.id),n,final:!!env.final,stall:!!env.screenClock,screening:ctx.GROW.screening};calls.push(call);
   const nth=calls.filter(x=>x.keys).length,stop=o.stop&&o.stop.call===nth?o.stop:null,done=stop?jobs.slice(0,stop.done):jobs;
   const r=Object.fromEntries(done.map(j=>[j.id,{clear:o.clear?o.clear(j.id,n):0.5,prog:0.5,ttk:20}]));
   if(stop){if(!stop.hard)ctx.GROW.partial=true;Object.defineProperty(r,'incomplete',{value:true})}
   return r}});
 for(const s of [src.plan,src.cmp,src.search,src.limited])vm.runInContext(s,ctx);
 const profile={results:Object.fromEntries(ctx.R.map(s=>[s.key,{}]))};
 return {ctx,calls,evals:()=>calls.filter(c=>c.keys),html:r=>vm.runInContext('growthLimitedHtml',ctx)(r),
  run:()=>vm.runInContext('growthStageSearch',ctx)({key:'op',name:'작전'},{tab:'a',name:'b'},profile,1)};
}
const plain=x=>JSON.parse(JSON.stringify(x));

async function suite(src){
 // 번갈아 순서: 빠른 계산 순(t0,t1…) 1 · 근사 점수 순(t29,t28…) 1
 const want=[];for(let i=0;i<15;i++)want.push(key('t'+i),key('t'+(29-i)));

 // A) 기본: 전 후보 8판 → 상위 20팀 32판 → 본선. 줄이지 않고, 안내도 없다. 예선만 무진행 상한(screenClock)을 쓴다
 {const h=harness(src,{teams:30,clear:(k,n)=>k===key('t7')?(n===8?0.6:0.9):0.5}),r=await h.run(),e=h.evals();
  assert.deepEqual(e[0].keys,want);assert.equal(e[0].n,8);assert.equal(e[0].stall,true);assert.equal(e[0].screening,true);
  assert.equal(e[1].n,32);assert.equal(e[1].keys.length,20);assert.equal(e[1].keys[0],key('t7'),'8판 결과 순으로 2차에 올림');
  assert.equal(e[2].final,true);assert.equal(e[2].n,100);assert.equal(e[2].stall,false);assert.equal(e[2].screening,false);assert.equal(e[2].keys[0],key('t7'));
  assert.equal(r.limited,null);assert.equal(h.html(r),'');assert.equal(h.ctx.GROW.screening,false);}

 // B) 1차 도중 멈춤(7팀 끝남): 2차 없이 끝난 팀으로 본선, limited 7/30
 {const h=harness(src,{teams:30,stop:{call:1,done:7},clear:k=>k===want[4]?0.9:0.3}),r=await h.run(),e=h.evals();
  assert.equal(e.length,2,'2차는 돌지 않음');assert.equal(e[1].final,true);assert.equal(e[1].keys.length,3);assert.equal(e[1].keys[0],want[4]);
  assert(e[1].keys.every(k=>want.slice(0,7).includes(k)));
  assert.deepEqual(plain(r.limited),{seen:7,total:30});assert.match(h.html(r),/중간에 멈춰서 후보 7\/30팀만 확인했어요/);
  assert.equal(h.ctx.GROW.partial,false,'멈춤 표시는 한 번 쓰고 지움');}

 // C) 2차 도중 멈춤(3팀 끝남): 32판 결과는 버리고 8판 순위 그대로 본선, limited = 「상위 팀을 짧게만」
 {const h=harness(src,{teams:30,stop:{call:2,done:3},clear:(k,n)=>n===32?0.99:k===key('t9')?0.8:0.5}),r=await h.run(),e=h.evals();
  assert.equal(e[1].n,32);assert.equal(e[2].final,true);assert.equal(e[2].keys[0],key('t9'),'8판 1등이 그대로 본선 첫 팀');
  assert.equal(e[1].keys[0],key('t9'));
  assert.deepEqual(e[2].keys,e[1].keys.slice(0,3),'먼저 끝난 팀만 32판 결과로 위에 올리지 않음(8판 순)');
  assert.deepEqual(plain(r.limited),{seen:30,total:30});assert.match(h.html(r),/중간에 멈춰서 상위 팀을 짧게만 확인했어요/);}

 // D) 재점화 풀: 재점화>0 일 때만 SCR_RK 팀을 후보에 번갈아 넣는다
 {const off=harness(src,{teams:200});await off.run();
  assert(!off.calls.some(c=>c.rkPool),'재점화 0 이면 재점화 풀을 만들지 않음');assert.equal(off.evals()[0].keys.length,120);
  const on=harness(src,{teams:200,rk:3,rkTop:[100,101,102]});await on.run();
  assert.deepEqual(on.calls[0],{rkPool:40});const first=on.evals()[0].keys;
  assert.equal(first.length,123);assert.deepEqual(first.slice(0,6),[key('t0'),key('t199'),key('t100'),key('t1'),key('t198'),key('t101')]);}

 // E) 멈춤이 아닌 미완료(무진행 상한·오류)·끝난 팀 없는 멈춤·본선 중 멈춤 표시는 종전대로 «미완료»
 await assert.rejects(harness(src,{teams:30,stop:{call:1,done:7,hard:true}}).run(),/미완료/);
 await assert.rejects(harness(src,{teams:30,stop:{call:1,done:0}}).run(),/미완료/);
 await assert.rejects(harness(src,{teams:30,stop:{call:3,done:1}}).run(),/미완료/);
}

(async()=>{
 await suite(SRC);console.log('PASS 육성 탐색 예선: 번갈아 순서·끝까지·1차/2차 도중 멈춤·limited 안내·재점화 풀·미완료');
 // 결함 주입: 고친 코드를 되돌리면 실패해야 한다
 const rep=(s,a,b)=>{assert(s.includes(a),'주입 대상 없음: '+a);return s.replace(a,b)};
 const mutants={
  '번갈아 대신 이어 붙이기':{...SRC,plan:rep(SRC.plan,'for(let i=0;i<m;i++)for(const l of lists){const k=l[i];','for(const l of lists)for(let i=0;i<m;i++){const k=l[i];')},
  '재점화 풀 끔':{...SRC,plan:rep(SRC.plan,'SCR_RK=40','SCR_RK=0')},
  '멈춤을 미완료로':{...SRC,search:rep(SRC.search,'if(soft&&Object.keys(r).length){stopped=true;return r;}','')},
  '1차에서 멈춰도 2차 진행':{...SRC,search:rep(SRC.search,'if(stopped)limited={seen:keys.length,total};\n    else if(keys.length>3){','if(keys.length>3){')},
  '2차 도중 멈춘 32판 결과로 순위':{...SRC,search:rep(SRC.search,'if(stopped)limited={seen:total,total};else keys=top.sort(','keys=top.filter(k=>r2[k]).sort(')},
  '2차 멈춤 안 알림':{...SRC,search:rep(SRC.search,'if(stopped)limited={seen:total,total};else keys','if(!stopped)keys')},
  '본선에서도 멈춤 허용':{...SRC,search:rep(SRC.search,'const soft=!final&&GROW.partial','const soft=GROW.partial')},
  '예선에 무진행 상한 안 씀':{...SRC,search:rep(SRC.search,'...(!final?{screenClock:{}}:{})','')},
  '2차 판 수 줄임':{...SRC,plan:rep(SRC.plan,'{n:32,top:20}','{n:16,top:10}')}};
 for(const [name,src] of Object.entries(mutants)){let caught=false;try{await suite(src)}catch(e){caught=true}
  assert(caught,'결함 주입이 통과해 버림: '+name);console.log('MUTATION caught:',name)}
 console.log('ALL OK scr stop');
})().catch(e=>{console.error(e);process.exit(1)});
