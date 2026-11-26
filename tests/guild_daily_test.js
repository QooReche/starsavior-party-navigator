const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const Daily=require('../guild_daily'),Planner=require('../guild_planner'),V=require('../guild_view'),C=require('../score_combinations');
const defaults=require('../data/guild_defaults.json').search;
const plain=x=>JSON.parse(JSON.stringify(x));
let scenarioCount=0;
function fixture(count=8){
  const S=structuredClone(defaults);Object.assign(S,{preset:'daily',poolSize:count,minPowerRatio:0,minRole:{},minFront:0,minDealer:0,banCoop:false});
  S.final.supports=['none','s0','s1','s2','s3','s4'];S.supportRole={s1:'디펜더',s2:'레인저',s3:'서포터',s4:'어쌔신'};
  Object.assign(S.daily.rerank,{keep:20});Object.assign(S.daily.probe,{teams:6,levels:[0,1,2],steps:[6,5]});
  const G={season:{id:30112,boss:{engine:'client'}},dataVersion:'synthetic',search:S,defaultStep:7,
    steps:Array.from({length:7},(_,i)=>({step:i+1,ex:i===6,base:100,bossKill:900,kill:0,eliteKill:0,waves:[[{boss:true}]]})),
    rules:{entryDaysEx:['화','목','토']},challenge:{levels:Array.from({length:12},(_,i)=>({level:i+1,score:0}))},sets:{items:[]},stepsMeta:{minions:0}};
  const roster=Array.from({length:count},(_,i)=>({key:'u'+String(i).padStart(2,'0'),cls:'캐스터'}));
  const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:1000-i,stats:{hp:1000,atk:100,def:100,spd:100},combat:{}}]));
  return {S,G,roster,results};
}
const teamNumber=t=>Math.floor(Number(t.party.units[0].key.slice(1))/4);
function score(t,{weak=false,move=false}={}){
  const g=t.options.guild,keys=t.party.units.map(u=>Number(u.key.slice(1))),block=keys.every(k=>Math.floor(k/4)===Math.floor(keys[0]/4));
  const leader=t.party.units[t.party.leader].key;
  return (g.step===7?(weak?400:5000):900)+(block?100:0)+(g.support==='s0'?30:0)+
    (t.options.break_skill?15:0)+(move&&leader===t.party.units.map(u=>u.key).sort().at(-1)?300:0)+(g.level===1?10:0);
}
async function scenario({daily=Daily,count=8,seals=3,weak=false,move=false,settings,stop,stopWhen,staleAt,timeOutStage,clock,scoreFn,viaFn,split,growth=false,day='2026-11-26T05:00:00+09:00'}={}){
  scenarioCount++;
  const f=fixture(count);settings?.(f.S);const trace=[],phases=[],plans=[],life={active:0,max:0,created:0};
  let phase=0,label='',partial=false,invalid=false,handle,fakeNow=0;
  const cx={...f,seals,split,nowMs:Date.parse(day),tiers:[],breaks:[{name:'synthetic',level:1}],workers:1,secondsPerGame:.0001,stage:'guild/test/7단계',base:'',clock,
    growthResults:growth?structuredClone(f.results):undefined,stale:()=>invalid,...(timeOutStage?{clock:()=>fakeNow}:{}),
    onPlan:p=>plans.push(p),onPhase:(name,total,meta)=>{phase=meta.policyStage;label=name;phases.push({label,total,...meta});
      assert(meta.stage<plans.at(-1).stages.length);assert.equal(plans.at(-1).stages[meta.stage].games,meta.games);},
    partialRequested:()=>partial,onHandle:h=>{handle=h;},onProgress:(d,total,eta)=>{
      assert(eta.ready&&Number.isFinite(eta.remainSec));
      if(timeOutStage===phase)fakeNow=5400001;
      if((stop===phase||staleAt===phase||stopWhen?.({phase,label,trace,phases}))&&d===1){partial=staleAt!==phase;invalid=staleAt===phase;handle.cancel();}},
    makeWorker(){life.created++;life.active++;life.max=Math.max(life.max,life.active);let dead=false;
      return {terminate(){if(!dead){dead=true;life.active--;}},postMessage(m){trace.push({...plain(m),phase,label});setImmediate(()=>{
        if(dead)return;const send=x=>this.onmessage({data:{...x,id:m.id}});send({type:'stage',msg:'준비 끝'});
        for(const t of m.teams){if(dead)return;
          const prior=t.options.merge_raw?JSON.parse(t.options.merge_raw):[],off=t.options.run_offset||0;
          assert.equal(prior.length,off);const raw=prior.concat(Array.from({length:m.n_runs},(_,i)=>['wipe',10,20,.6,(scoreFn||((t)=>score(t,{weak,move})))(t,i+off)]));
          send({type:'team',key:t.key,result:{n:raw.length,prog:.6,progs:raw.map(x=>x[3]),clear:0,via:viaFn?viaFn(t,off):{trigger:1},guild:{base_scores:raw.map(x=>x[4])},raw:JSON.stringify(raw)}});
        }if(!dead)send({type:'done'});
      });}};
    }};
  let out;try{out=await daily.search(cx);}finally{assert.equal(life.active,0);}
  assert.equal(life.max,1);assert.equal(life.created,1,'one worker pool for the search, including growth');
  assert(phases.every((p,i)=>p.stage===i),'P1 stage indices never move backward on conditional sweeps/retries/growth');
  if(!growth){const ranges=new Map();for(const m of trace){assert.equal(m.seed,f.S.daily.seed);for(const t of m.teams){
    const end=ranges.get(t.key)||0;assert.equal(t.options.run_offset||0,end,'no duplicate seed/game, including no-break and ineffective support');ranges.set(t.key,end+m.n_runs);
  }}}
  return {out,trace,phases,plans,cx};
}
function valid(out,n){
  assert.equal(out.teams.length,n);assert(out.sum>0);assert.equal(out.sum,out.teams.reduce((s,t)=>s+t.score,0));
  assert.equal(new Set(out.teams.flatMap(t=>t.keys)).size,n*4);
  assert.equal(new Set(out.teams.map(t=>t.sup)).size,n);assert(out.teams.every(t=>t.sup!=='none'));
}
function packing(combinations=C){
  const make=(id,keys,sup,score,mean=score)=>({id,keys,sup,score,mean});
  const a=make('a',['a'],'s0',10,10),b=make('b',['b'],'s0',20),c=make('c',['b'],'s1',5),d=make('d',['a'],'s1',9);
  const opts={id:t=>t.id,resources:t=>({units:t.keys,support:[t.sup]}),secondary:t=>t.mean,setId:ts=>ts.map(t=>t.id).sort().join('/')};
  const best=combinations.bestSets([[a,d],[b,c]],1,null,opts)[0];assert.equal(best.sum,29);assert.deepEqual(plain(best.teams.map(t=>t.id)),['d','b']);
  const tie=combinations.bestSets([[make('a',['a'],'s0',10,1),make('z',['z'],'s0',10,9)]],1,null,opts);assert.equal(tie[0].teams[0].id,'z');
  const xs=[a,{...b,sup:'s1'}];assert.equal(combinations.bestSets([xs,xs],10,null,opts).length,1,'symmetric slots do not consume finalist places');
}
function margins(daily=Daily){
  const a={score:1000,mean:800},small={score:1009,mean:900},edge={score:1010,mean:900},large={score:1011,mean:800};
  assert.equal(daily.choosePlacement(a,small,.01),a);assert.equal(daily.choosePlacement(a,edge,.01),a);assert.equal(daily.choosePlacement(a,large,.01),large);
  assert.equal(daily.choosePlacement(a,{score:1000,mean:807},.01),a);
}
function caps(daily=Daily){
  const f=fixture(40);f.S.daily=structuredClone(defaults.daily);
  const p=daily.plan({...f,seals:4,nowMs:Date.parse('2026-11-26T05:00:00+09:00'),secondsPerGame:.05,breaks:[]});
  assert.equal(p.placeScope,'ex');assert(p.withinCap);assert(p.estimatedSec<5400);assert.deepEqual(plain(p.reductions.slice(0,3)),['자리·리더 대상: EX 팀만','조건 비교: 상위 8팀','정밀: 상위 200팀']);
  assert(p.poolLimit<40);assert.equal(p.D.screen.runs,2);
  const combinations=p.poolLimit*(p.poolLimit-1)*(p.poolLimit-2)*(p.poolLimit-3)/24;
  assert.equal(p.stages[2].games,combinations*2*18,'estimate includes all boundary ties');
  const growth=daily.plan({...f,seals:4,nowMs:Date.parse('2026-11-26T05:00:00+09:00'),secondsPerGame:.05,growthResults:f.results});
  assert(growth.estimatedSec<5400);assert(growth.poolLimit<=p.poolLimit);assert.equal(growth.passes,2);
}
async function checks(daily=Daily){
  const strong=await scenario({daily,seals:2});valid(strong.out,1);assert.equal(strong.out.split.ex,1);assert(!strong.trace.some(m=>m.teams.some(t=>t.options.guild.step!==7)),'strong EX skips normal sweep');
  assert(strong.trace.some(m=>m.n_runs===18&&m.teams.some(t=>t.options.run_offset===2)));
  assert(strong.trace.some(m=>m.n_runs===30&&m.teams.some(t=>t.options.run_offset===10)));
  const multi=await scenario({daily});valid(multi.out,2);assert(multi.out.teams.some(t=>t.sup!=='s0'&&t.effectiveSupport==='none'),'mismatched support is assigned');
  assert(!multi.out.partial);assert(multi.out.evaluation.placementComplete);
  const weak=await scenario({daily,seals:2,weak:true});valid(weak.out,2);assert.equal(weak.out.split.normal,2);assert(weak.out.reason.includes('EX 팀 점수가 낮아 일반 2팀'));
  const ex2=await scenario({daily,seals:4});valid(ex2.out,2);assert.equal(ex2.out.split.ex,2);
  const few=await scenario({daily,seals:4,day:'2026-11-25T05:00:00+09:00'});valid(few.out,2);assert.equal(few.out.seals.remaining,2);assert(few.out.warnings.some(s=>s.includes('4팀 중 2팀')));
  const retry=await scenario({daily,seals:4,settings:S=>{S.daily.probe.teams=1;}});valid(retry.out,2);assert(retry.phases.filter(p=>p.policyStage===4).length>1,'candidate expansion executes');
  const shortage=await scenario({daily,seals:4,settings:S=>{S.daily.probe.teams=1;},scoreFn:t=>t.party.units.some(u=>u.key==='u00')?5000:1});
  valid(shortage.out,1);assert.equal(shortage.out.seals.remaining,2);
  const moved=await scenario({daily,move:true});valid(moved.out,2);assert(moved.out.teams.some(t=>t.placementChanged));
  const firstPlace=moved.phases.find(p=>p.policyStage===7),firstPlan=moved.plans.find(p=>p.stages[firstPlace.stage]?.policyStage===7);
  assert(firstPlan.stages.slice(firstPlace.stage+1).some(s=>s.games>0),'placement screen is not the last work in the ETA');
  assert.equal(moved.plans.at(-1).eta.estimate(Date.now()/1000).remainSec,0);
  const rechecks=moved.phases.filter(p=>p.label==='바뀐 자리의 스테이지·지원 재확인');assert.equal(rechecks.length,moved.out.teams.filter(t=>t.placementChanged).length);
  // Recheck jobs are stage 7 only; every support excludes all other final teams.
  const finalSupports=new Set(moved.out.teams.map(t=>t.sup));
  for(const t of moved.out.teams)assert(t.evaluation.placementComplete);
  assert(finalSupports.size===2);
  for(const stage of [2,4,6,7]){const stopped=await scenario({daily,stop:stage});assert(stopped.out.partial);assert(stopped.out.flags.includes('자리·리더 미평가'));
    if(stage===2)assert.equal(stopped.out.teams.length,0);if(stage===4)assert(stopped.out.flags.includes('스테이지·지원 미평가'));if(stage===7){valid(stopped.out,2);assert.equal(stopped.out.coverage.selectedStage,6);}
  }
  const fixed=await scenario({daily,seals:2,split:{ex:0,normal:2}});valid(fixed.out,2);assert(!fixed.trace.some(m=>m.teams.some(t=>t.options.guild.step===7)));
  const growth=await scenario({daily,seals:2,growth:true});valid(growth.out,1);valid(growth.out.growth,1);
  return {strong,multi,moved};
}
async function regression(daily=Daily){
  const partial=await scenario({daily,seals:2,weak:true,stopWhen:({phase,trace})=>phase===6&&trace.at(-1).teams[0].options.guild.step!==7});
  valid(partial.out,1);assert.equal(partial.out.split.ex,1);assert.equal(partial.out.teams[0].n,40);assert.equal(partial.out.coverage.selectedStage,6);
  assert(partial.out.evaluation.breakComplete&&partial.out.evaluation.stageSupportComplete);
  const capped=await scenario({daily,seals:2,timeOutStage:6});assert(capped.out.partial&&capped.out.timeCapped);
  const clearIncumbent=await scenario({daily,seals:2,scoreFn:t=>{
    const keys=t.party.units.map(u=>u.key);return score(t)+(keys.join()===keys.slice().sort().join()&&t.party.leader===0?1000:0);
  }});
  assert(!clearIncumbent.trace.some(m=>m.phase===7&&m.teams.some(t=>t.options.run_offset===100)),'clear incumbent win stops at 100 games');
  assert.equal(clearIncumbent.trace.filter(m=>m.phase===7&&m.n_runs===80).reduce((s,m)=>s+m.teams.length,0),3,'three challengers plus incumbent');
  const growthPartial=await scenario({daily,seals:2,growth:true,stopWhen:({phase,phases})=>phase===6&&phases.filter(p=>p.policyStage===2).length===2});
  assert(growthPartial.out.partial&&growthPartial.out.growth.partial);assert(growthPartial.out.flags.includes('육성 포함 미평가'));
  await assert.rejects(()=>scenario({daily,staleAt:6}),/취소/);
  const coop=await scenario({daily,seals:2,settings:S=>{S.banCoop=true;},viaFn:t=>({coop:t.party.units.some(u=>u.key==='u00')?.1:0})});
  valid(coop.out,1);assert(!coop.out.teams.some(t=>t.keys.includes('u00')));
  const CS=require('../cosmo_search'),oldPass=CS.pickPass,oldSteps=C.steps,seen=[];
  CS.pickPass=(jobs,res,...rest)=>{seen.push(plain(res));return oldPass(jobs,res,...rest);};
  C.steps=(lists,...rest)=>{assert(lists.flat().every(t=>t.n===10),'all packing candidates use exactly 10 games, even after another final');return oldSteps(lists,...rest);};
  try{
    await scenario({daily,seals:4,settings:S=>{S.daily.probe.teams=1;},scoreFn:(t,i)=>score(t)+(i<2?5000:0)});
    assert(seen.length>1);for(const [key,r] of Object.entries(seen[1]))assert.deepEqual(r,seen[0][key],'retry screening always uses first 2 games');
    await scenario({daily,seals:2,weak:true});
  }finally{CS.pickPass=oldPass;C.steps=oldSteps;}
  const scoreFn=t=>{
    const keys=t.party.units.map(u=>u.key).sort(),moved=t.party.units[t.party.leader].key===keys.at(-1),g=t.options.guild;
    return score(t,{move:true})+(moved&&((g.step===7&&g.level===2)||(g.step===5))?500:0)+(moved&&g.support==='s4'?100:0);
  };
  const before=await scenario({daily,settings:S=>{S.supportRole={};S.daily.place.margin=100;},scoreFn});
  assert(!before.phases.some(p=>p.label.includes('재확인')),'unchanged placements do not recheck conditions');
  const after=await scenario({daily,settings:S=>{S.supportRole={};},scoreFn});valid(after.out,2);
  const assigned=new Map(before.out.teams.map(t=>[t.keys.slice().sort().join(),t.sup]));
  const visited=new Set();
  for(const m of after.trace.filter(m=>m.label==='바뀐 자리의 스테이지·지원 재확인')){
    const id=m.teams[0].party.units.map(u=>u.key).sort().join();
    if(!visited.has(id)&&visited.size){for(const prev of visited)assigned.set(prev,after.out.teams.find(t=>t.keys.slice().sort().join()===prev).sup);}
    visited.add(id);const forbidden=[...assigned].filter(([k])=>k!==id).map(([,sup])=>sup);
    assert(m.teams.every(t=>!forbidden.includes(t.options.guild.support)),'recheck excludes other teams supports');
  }
  assert.equal(visited.size,2);assert(after.phases.some(p=>p.label==='바뀐 조건 40판 확인'));assert(after.phases.some(p=>p.label==='바뀐 조건 브레이크 재비교'));
  assert.equal(after.phases.filter(p=>p.label==='자리·리더 비교'&&p.runs===20).length,2,'one placement search per team, no loop back');
}
async function main(){
  packing();margins();caps();await checks();await regression();const scenarios=scenarioCount;
  const old=Daily.search;let dispatched=false;Daily.search=async()=>{dispatched=true;return {};};
  try{await Planner.search({...fixture(),S:{...defaults,preset:'daily'}});assert(dispatched);}finally{Daily.search=old;}
  const src=fs.readFileSync(require.resolve('../guild_daily'),'utf8');
  for(const [from,to,check] of [
    ['Math.abs(value(incumbent))*margin','0',margins],
    ["placeScope='ex';reductions.push","placeScope='all';reductions.push",caps],
    ["effectiveSupport=GS.finalSupports(S,keys,cls).includes(sup)?sup:'none'","effectiveSupport=sup",async d=>{const r=await scenario({daily:d});assert(r.out.teams.some(t=>t.sup!=='s0'&&t.effectiveSupport==='none'));}],
    ["support:[t.sup]","support:[]",async d=>valid((await scenario({daily:d})).out,2)],
    ['t.score<normalMaximum(G)*D.seals.costEx/D.seals.costNormal*D.split.weakExRatio','false',async d=>assert.equal((await scenario({daily:d,seals:2,weak:true})).out.split.normal,2)],
    ['if(pick.key===original.key)','if(true)',async d=>assert((await scenario({daily:d,move:true})).out.teams.some(t=>t.placementChanged))],
    ['combos*sweeps*(D.rerank.runs-D.screen.runs)','keep*sweeps*(D.rerank.runs-D.screen.runs)',caps],
    ['const full=cache.get(j.key);','const full=cache.get(j.key); n=full.n;',regression],
    ['if(checkpointStage<6){checkpoint=bundles[0];checkpointStage=5;}','checkpoint=bundles[0];checkpointStage=5;',regression],
    ['supports.filter(s=>!taken.has(s))','supports',regression],
    ['if(s.id<stage&&','if(s.id<=stage&&',checks],
    ['if(pick===inc&&challenger&&choosePlacement(challenger,inc,D.place.margin)===challenger)','if(pick===inc)',regression]
  ]){
    assert(src.includes(from),from);const ctx={module:{exports:{}},require:n=>require('../'+n),setTimeout,clearTimeout};vm.runInNewContext(src.replace(from,to),ctx);
    await assert.rejects(async()=>check(ctx.module.exports),undefined,'mutation must fail: '+from);
  }
  const combinationSource=fs.readFileSync(require.resolve('../score_combinations'),'utf8');
  for(const [from,to] of [['a.secondary-b.secondary','0'],['if(setId&&top.some(x=>x.key===key))return;','if(false)return;']]){
    const ctx={module:{exports:{}}};assert(combinationSource.includes(from));vm.runInNewContext(combinationSource.replace(from,to),ctx);assert.throws(()=>packing(ctx.module.exports));
  }
  console.log(`PASS daily: ${scenarios} fake-worker scenarios; packing/support/EX/shortage/retry/placement/partial/growth/ETA/deadline, precision and checkpoint regressions, 14 killed mutations`);
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={fixture,scenario,checks,packing,margins,caps};
