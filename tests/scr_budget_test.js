// 예선 시간 예산(11/13) — 「클리어 추천 육성」 탐색(growthStageSearch)이 추천 예선과 같은 규칙(scrPick·ScrPlan)으로
// 후보를 번갈아 세우고, 잰 속도로 돌 수 있는 만큼만 돌며, 줄였으면 limited 로 알리는지 본다. 화면 예선(simScreen) 쪽은 sim_timeout_test.js 13~15.
// 끝에서 고친 코드를 일부러 되돌려(결함 주입) 이 시험이 실패하는지 확인한다.
// 실행: node tests/scr_budget_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8'),ui=fs.readFileSync(require.resolve('../growth_ui.js'),'utf8');
const cut=(s,a,b)=>{const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i,'구간 없음: '+a);return s.slice(i,j)};
const SRC={plan:cut(html,'const SCR_ROUNDS=','const scrKey='),cmp:cut(html,'const scrCmp=','// 줄여서 본'),
 search:cut(ui,'async function growthStageSearch','async function growthStart'),limited:cut(ui,'function growthLimitedHtml','function growthNonePaint')};
const key=k=>['a','b','c',k].sort().join(',');

function harness(src,o){
 let clock=1000;const calls=[],teams=Array.from({length:o.teams},(_,i)=>({keys:['a','b','c','t'+i],v:i}));
 const ctx=vm.createContext({console,Object,Math,JSON,Set,Map,Infinity,Error,
  SIMQ:{seed:1,n:100,LOAD_MS:1000,rateS:o.rate||0,rateSt:o.rateSt},GROW:{id:1},MODE:'auto',
  CFG:{restrict:{},defPenByContent:{},weights:{defenderPenalty:0}},R:['u0','u1','u2','u3'].map(k=>({key:k,el:'x'})),EXCL:new Set(),
  score:()=>[1,{}],rankAll:x=>x,quickIn:()=>({}),quickRank:()=>teams,rkOf:()=>o.rk||0,
  rkQuickTop:(c,st,all,n)=>{calls.push({rkPool:n});return o.rkTop?o.rkTop.map(i=>teams[i]):[]},
  scrWorkers:()=>3,growthJob:(t,k)=>({id:k,t}),simTeamLimit:()=>1000,GrowthGuide:{finalCost:n=>n},Date:{now:()=>clock},
  growthEvaluate:async(jobs,n,seed,c,st,id,deadline,env)=>{calls.push({keys:Array.from(jobs,j=>j.id),n,final:!!env.final});
   if(env.screenClock&&!env.screenClock.deadline)env.screenClock.deadline=clock+60000;
   clock+=o.cost?o.cost(jobs.length,n,calls.length):0;if(o.rateAfter&&!env.final)ctx.SIMQ.rateS=o.rateAfter;
   const r=Object.fromEntries(jobs.map(j=>[j.id,{clear:0.5,prog:0.5,ttk:20}]));
   if(o.incomplete)Object.defineProperty(r,'incomplete',{value:true});return r}});
 for(const s of [src.plan,src.cmp,src.search,src.limited])vm.runInContext(s,ctx);
 const profile={results:Object.fromEntries(ctx.R.map(s=>[s.key,{}]))};
 return {ctx,calls,run:()=>vm.runInContext('growthStageSearch',ctx)({key:'op',name:'작전'},{tab:'a',name:'b'},profile,1)};
}

async function suite(src){
 // 번갈아 순서: 빠른 계산 순(t0,t1…) 1 · 근사 점수 순(t29,t28…) 1
 const want=[];for(let i=0;i<15;i++)want.push(key('t'+i),key('t'+(29-i)));

 // A) 속도를 모름: 앞 6팀으로 재고(1판 0.5초, 24초 씀) → 남은 1차 예산 12초 = 9팀 → 2차는 10팀 16판 → limited 15/30
 {const h=harness(src,{teams:30,rateAfter:500,cost:(m,n,i)=>i===1?24000:i===2?6000:0}),r=await h.run();
  const scr=h.calls.filter(c=>c.keys&&!c.final);
  assert.deepEqual(scr[0],{keys:want.slice(0,6),n:8,final:false},'속도 재기: 번갈아 순서의 앞 6팀');
  assert.deepEqual(scr[1],{keys:want.slice(6,15),n:8,final:false},'남은 예산만큼만');
  assert.equal(scr.length,3);assert.equal(scr[2].n,16,'2차 판 수 = 남은 시간 맞춤(하한 16)');assert.equal(scr[2].keys.length,10);
  assert(scr[2].keys.every(k=>want.slice(0,15).includes(k)));
  assert.deepEqual(JSON.parse(JSON.stringify(r.limited)),{seen:15,total:30});
  assert(h.calls.some(c=>c.final&&c.n===100),'본선은 그대로');
  assert.match(vm.runInContext('growthLimitedHtml',h.ctx)(r),/시간이 부족해 후보 15\/30팀만 확인했어요/);}

 // B) 이 스테이지에서 잰 빠른 속도: 재지 않고 전부 8판 → 상위 20팀 32판, 안내 없음
 {const h=harness(src,{teams:30,rate:50,rateSt:'op|a|b'}),r=await h.run(),scr=h.calls.filter(c=>c.keys&&!c.final);
  assert.equal(scr.length,2);assert.deepEqual(scr[0].keys,want);assert.equal(scr[1].n,32);assert.equal(scr[1].keys.length,20);
  assert.equal(r.limited,null);assert.equal(vm.runInContext('growthLimitedHtml',h.ctx)(r),'');}

 // C) 다른 스테이지에서 잰 속도는 버리고 다시 잰다. 느리면 2차 생략 → 「짧게만」
 {const h=harness(src,{teams:8,rate:50,rateSt:'op|x|y',rateAfter:3000,cost:()=>0}),r=await h.run(),scr=h.calls.filter(c=>c.keys&&!c.final);
  assert.equal(scr[0].keys.length,6,'다른 스테이지 속도면 앞 6팀으로 다시 잼');assert.equal(scr[1].keys.length,2,'최소 팀 수(12)까지는 돎');
  assert.equal(scr.length,2,'2차 생략');assert.deepEqual(JSON.parse(JSON.stringify(r.limited)),{seen:8,total:8});
  assert.match(vm.runInContext('growthLimitedHtml',h.ctx)(r),/후보를 짧게만 확인했어요/);}

 // D) 재점화 풀: 재점화>0 일 때만 SCR_RK 팀을 후보에 번갈아 넣는다
 {const off=harness(src,{teams:200,rate:1,rateSt:'op|a|b'});await off.run();
  assert(!off.calls.some(c=>c.rkPool),'재점화 0 이면 재점화 풀을 만들지 않음');assert.equal(off.calls.find(c=>c.keys).keys.length,120);
  const on=harness(src,{teams:200,rate:1,rateSt:'op|a|b',rk:3,rkTop:[100,101,102]});await on.run();
  assert.deepEqual(on.calls[0],{rkPool:40});const first=on.calls.find(c=>c.keys).keys;
  assert.equal(first.length,123);assert.deepEqual(first.slice(0,6),[key('t0'),key('t199'),key('t100'),key('t1'),key('t198'),key('t101')]);}

 // E) 안전망: 그래도 상한에 걸리면 종전대로 미완료
 {const h=harness(src,{teams:30,rate:50,rateSt:'op|a|b',incomplete:true});await assert.rejects(h.run(),/미완료/);}
}

(async()=>{
 await suite(SRC);console.log('PASS 육성 탐색 예산: 번갈아 순서·속도 재기·1차 축소·2차 판 수/생략·limited 안내·재점화 풀·미완료 안전망');
 // 결함 주입: 고친 코드를 되돌리면 실패해야 한다
 const rep=(s,a,b)=>{assert(s.includes(a),'주입 대상 없음: '+a);return s.replace(a,b)};
 const mutants={
  '1차 축소 끔':{...SRC,plan:rep(SRC.plan,'if(!(rate>0))return total;\n  return','return total;\n  return')},
  '번갈아 대신 이어 붙이기':{...SRC,plan:rep(SRC.plan,'for(let i=0;i<m;i++)for(const l of lists){const k=l[i];','for(const l of lists)for(let i=0;i<m;i++){const k=l[i];')},
  '2차 하한 없음':{...SRC,plan:rep(SRC.plan,'SCR_N2MIN=16','SCR_N2MIN=1')},
  '재점화 풀 끔':{...SRC,plan:rep(SRC.plan,'SCR_RK=40','SCR_RK=0')},
  '스테이지별 속도 구분 없음':{...SRC,plan:rep(SRC.plan,'if(SIMQ.rateSt!==k){','if(false){')},
  'limited 안 남김':{...SRC,search:rep(SRC.search,'if(keys.length<total)limited={seen:keys.length,total};','')},
  '속도 재기 없음':{...SRC,search:rep(SRC.search,'!(SIMQ.rateS>0)&&total>probe?','false?')}};
 for(const [name,src] of Object.entries(mutants)){let caught=false;try{await suite(src)}catch(e){caught=true}
  assert(caught,'결함 주입이 통과해 버림: '+name);console.log('MUTATION caught:',name)}
 console.log('ALL OK scr budget');
})().catch(e=>{console.error(e);process.exit(1)});
