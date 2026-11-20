// This suite isolates candidate selection/retry; layout cross-products are covered by party_placement_test.
const PlacementFixture=require('../party_placement.js');
PlacementFixture.variants=(keys,results)=>[PlacementFixture.baseline(keys,results)];
// 실제 search와 합성 작업자를 통해 상한·확대·결과 재사용·ETA·안내를 검사한다.
const assert=require('node:assert/strict');
const C=require('../cosmo_search.js'), L=require('../cosmo_learned.js'), GS=require('../guild_search.js'), G=require('../data/cosmo_raid.json');
function settings(){const S=structuredClone(G.search);S.placement={auditTeams:0};
  Object.assign(S.learned,{S:80,m:2,K:25,M:1,A:12,overlapStarts:2,overlapKeep:2,minCorrelation:1});
  S.screen={firstRuns:1,runs:2,passFrac:.1,passMinMult:1};S.rerank={keep:15,runs:2};S.final.runs=3;
  S.combine={topTriples:2,show:2};S.minFront=S.minDealer=0;return S;}
function account(n){const roster=Array.from({length:n},(_,i)=>({key:'u'+i,cls:i%2?'캐스터':'서포터'}));
  return {roster,results:Object.fromEntries(roster.map((r,i)=>[r.key,{power:100+i,stats:{atk:100+i}}]))};}
async function run(S,n=16,stopEarly=false){const sent=[],phases=[],progress=[];let stopped=false,created=0,closed=0,eta,idx,time=0;
  try {const out=await C.search({S,...account(n),bosses:G.season.bossOrder,level:6,mode:'top',workers:2,
    onPlan:p=>{eta=C.etaNew({stages:p.stages,prior:[1,1,1,1],warmup:0});},
    onPhase:(msg,total,info)=>{idx=info.stage;eta.begin(idx,info.games,++time);phases.push({msg,total,info,estimate:eta.estimate(time)});},
    onProgress:(d,t)=>{progress.push([idx,d,t]);eta.update(d*(idx===2?2:idx===3?3:1),++time);},stale:()=>stopped,
    makeWorker(){created++;return {terminate(){closed++;},postMessage(m){sent.push(m);setImmediate(()=>{
      for(const t of m.teams){const v=1000+t.party.units.reduce((s,u)=>s+Number(u.key.slice(1))**2,0);
        this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{prog:.8,progs:[.8],via:{},n:m.n_runs,cosmo:{mean:v,top:v,clear:0,frac:.8,n:m.n_runs}}}});}
      if(stopEarly)stopped=true;this.onmessage({data:{type:'done',id:m.id}});
    });}};}});return {out,sent,phases,progress,eta};
  }catch(error){return {error,sent,phases,progress};}finally{assert.equal(created,closed,'모든 워커 반환');}}
const keys=(r,seed)=>r.sent.filter(m=>m.seed===seed).flatMap(m=>m.teams.map(t=>t.key));
const checkSuccess=r=>{assert(!r.error,r.error?.stack);assert(r.out.rows[0].sum>0);assert.equal(new Set(r.out.rows[0].teams.flatMap(t=>t.keys)).size,12);};
const render=out=>C.html({...out,phase:'done'},{hasInfo:true,level:6,mode:'top',learned:true,esc:String,label:String,bossName:String,levelMax:18});
async function main(){
  assert.equal(G.search.learned.value,true);assert.equal(G.search.learned.maxScoreCombos,2000000);assert.equal(G.search.maxCombos,363000);
  const S=settings(),a=account(16),count=C.countCombos(S,C.poolAll(S,a.results,a.roster));
  const large=settings();large.learned.S=180; // 59명 모두 표본 최소 포함
  const admitted=await run(large,59,true);
  assert(C.countCombos(large,account(59).roster)>363000);assert(admitted.sent.length>0,'36.3만 초과 학습이 실제 작업까지 진행');
  assert.match(admitted.error?.message||'',/취소/);
  const tooLarge=settings();tooLarge.learned.S=180;
  const over=await run(tooLarge,90,true);assert.match(over.error?.message||'',/안전 상한\(2,000,000개\)/);assert.equal(over.sent.length,0);
  const exact=settings();exact.learned.value=false;
  const combos=GS.combos;let denied;
  try{GS.combos=()=>{throw Error('상한 오류 전에 전수 배열을 만들면 안 됨');};denied=await run(exact,59);}finally{GS.combos=combos;}
  assert.match(denied.error?.message||'',/안전 상한\(363,000개\)/);assert.equal(denied.sent.length,0);
  // 경계는 '초과'만 거부한다. 기본 규모는 위의 실제 큰 풀로 별도 확인.
  const edge=settings();edge.learned.maxScoreCombos=count;const atEdge=await run(edge);checkSuccess(atEdge);
  edge.learned.maxScoreCombos=count-1;const pastEdge=await run(edge);assert.match(pastEdge.error?.message||'',/안전 상한/);assert.equal(pastEdge.sent.length,0);
  const full=settings();full.maxCombos=count;const f=await run(full);checkSuccess(f);
  assert(f.out.audit.every(a=>a.fallback&&!a.expanded));assert.equal(keys(f,1).length,count*3);assert.equal(new Set(keys(f,1)).size,count*3);
  const expanded=settings();expanded.maxCombos=count-1;
  const before=JSON.stringify(expanded),calls=[],select=L.select,auditSample=L.auditSample;
  L.select=async(s,...args)=>{calls.push(['select',s.learned.K,s.learned.M]);return select(s,...args);};
  L.auditSample=async(s,...args)=>{calls.push(['audit',s.learned.A]);return auditSample(s,...args);};
  let e;try{e=await run(expanded);}finally{L.select=select;L.auditSample=auditSample;}
  checkSuccess(e);assert.equal(JSON.stringify(expanded),before,'설정 원본 보존');
  const factor=expanded.learned.fallbackMultiplier;
  assert.equal(calls.filter(c=>c[0]==='select'&&c[1]===expanded.learned.K*factor&&c[2]===expanded.learned.M*factor).length,3,'K·M 확대');
  assert.equal(calls.filter(c=>c[0]==='audit'&&c[1]===expanded.learned.A*factor).length,3,'감사 표본 확대');
  assert(e.out.audit.every(a=>a.fallback&&a.expanded&&a.expandedCore>a.core&&a.expandedAudit.sampled===expanded.learned.A*factor));
  const first=keys(e,1);assert(first.length<count*3,'전수 계산 대신 제한된 후보만 실행');assert.equal(new Set(first).size,first.length,'표본·후보 첫 판 재사용');
  assert.equal(new Set(keys(e,3)).size,keys(e,3).length,'정밀 결과 재사용');
  assert(e.phases.some(p=>p.msg.includes('후보 확대 복귀'))&&!e.phases.some(p=>p.msg.includes('전수 확인')));
  const firstPhases=e.phases.filter(p=>p.info.stage===0),last=firstPhases.at(-1);
  assert.equal(last.total,first.length,'ETA 최종 전체 판 수');
  assert(last.total>firstPhases.find(p=>p.msg.includes('학습 후보·무작위 감사')).total,'확대 ETA 누계 증가');
  assert(e.progress.filter(p=>p[0]!=null).every((p,i,ps)=>p[1]<=p[2]&&(i===0||p[0]!==ps[i-1][0]||p[1]>=ps[i-1][1])),'진행률 완료 수 유지');
  assert(firstPhases.every(p=>p.estimate.ready&&Number.isFinite(p.estimate.remainSec)&&p.estimate.remainSec>=0));
  for(const boss of G.season.bossOrder)assert(render(e.out).includes(boss+': 이 보스는 예측 확인이 부족해 후보를 넓혀 찾았음'));
  assert(!render(e.out).includes('품질 미달 보스는 전수 확인으로 복귀'));
  assert(!render(f.out).includes('data-k="cs-expanded"'));
  // 상한을 넘겨도 품질이 충분하면 확대하지 않는다.
  const good=settings();good.maxCombos=count-1;good.learned.minCorrelation=-1;good.learned.missThreshold=1;
  const g=await run(good);checkSuccess(g);assert(g.out.audit.every(a=>!a.fallback&&!a.expanded));
  assert(keys(g,1).length<first.length,'확대 경로가 실제로 더 많은 후보를 계산');
  console.log('PASS learned limits: 36.3만/200만/경계, 전수·확대 분기, K/M/감사, 재사용, ETA, 안내, 정상 품질');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
