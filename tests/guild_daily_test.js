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
async function scenario({daily=Daily,count=8,follows=0,stopRound=0,weak=false,move=false,settings,setup,stop,stopWhen,staleAt,timeOutStage,clock,scoreFn,viaFn,growth=false,day='2026-11-26T05:00:00+09:00'}={}){
  scenarioCount++;
  const f=fixture(count);settings?.(f.S);setup?.(f);const trace=[],phases=[],plans=[],life={active:0,max:0,created:0};
  let round=0,phase=0,label='',partial=false,invalid=false,handle,fakeNow=0;
  const cx={...f,nowMs:Date.parse(day),tiers:[],breaks:[{name:'synthetic',level:1}],workers:1,secondsPerGame:.0001,stage:'guild/test/7단계',base:'',clock,
    growthResults:growth?structuredClone(f.results):undefined,stale:()=>invalid,...(timeOutStage?{clock:()=>fakeNow}:{}),
    onPlan:p=>plans.push(p),onPhase:(name,total,meta)=>{phase=meta.policyStage;label=name;phases.push({label,total,...meta});
      assert(meta.stage<plans.at(-1).stages.length);assert.equal(plans.at(-1).stages[meta.stage].games,meta.games);},
    partialRequested:()=>partial,onHandle:h=>{handle=h;},onProgress:(d,total,eta)=>{
      assert(eta.ready&&Number.isFinite(eta.remainSec));
      if(timeOutStage===phase)fakeNow=5400001;
      if(round===stopRound&&(stop===phase||staleAt===phase||stopWhen?.({phase,label,trace,phases}))&&d===1){partial=staleAt!==phase;invalid=staleAt===phase;handle.cancel();}},
    makeWorker(){life.created++;life.active++;life.max=Math.max(life.max,life.active);let dead=false;
      return {terminate(){if(!dead){dead=true;life.active--;}},postMessage(m){trace.push({...plain(m),phase,label});setImmediate(()=>{
        if(dead)return;const send=x=>this.onmessage({data:{...x,id:m.id}});send({type:'stage',msg:'준비 끝'});
        for(const t of m.teams){if(dead)return;
          const prior=t.options.merge_raw?JSON.parse(t.options.merge_raw):[],off=t.options.run_offset||0;
          assert.equal(prior.length,off);const raw=prior.concat(Array.from({length:m.n_runs},(_,i)=>['wipe',10,20,.6,(scoreFn||((t)=>score(t,{weak,move})))(t,i+off)]));
          send({type:'team',key:t.key,result:{n:raw.length,prog:.6,progs:raw.map(x=>x[3]),clear:0,via:viaFn?viaFn(t,off,{phase,label,runs:m.n_runs}):{trigger:1},guild:{base_scores:raw.map(x=>x[4])},raw:JSON.stringify(raw)}});
        }if(!dead)send({type:'done'});
      });}};
    }};
  let out;const rounds=[],session=daily.createSession(cx.makeWorker);cx.session=session;
  try{for(round=0;round<=follows;round++){
    partial=false;
    const start=trace.length,phaseStart=phases.length;
    out=await daily.search({...cx,previous:out});
    rounds.push({out,trace:trace.slice(start),jobs:trace.slice(start).reduce((n,m)=>n+m.teams.length,0)});
    assert(phases.slice(phaseStart).every((p,i)=>p.stage===i),'stage indices stay ordered');
  }}finally{session.close();assert.equal(life.active,0);}
  assert.equal(life.max,1);assert.equal(life.created,stop&&follows>stopRound?2:1,'same pool; canceled worker is replaced on retry');
  if(!growth&&!(stop&&follows>stopRound)){const ranges=new Map();for(const m of trace){assert.equal(m.seed,f.S.daily.seed);for(const t of m.teams){
    const end=ranges.get(t.key)||0;assert.equal(t.options.run_offset||0,end,'no duplicate seed/game, including no-break and ineffective support');ranges.set(t.key,end+m.n_runs);
  }}}
  return {out,trace,phases,plans,cx,rounds,life};
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
  const p=daily.plan({...f,nowMs:Date.parse('2026-11-26T05:00:00+09:00'),secondsPerGame:.01,breaks:[]});
  assert.equal(p.placeScope,'ex');assert(p.withinCap);assert(p.estimatedSec<5400);assert.deepEqual(plain(p.reductions.slice(0,3)),['자리·리더 대상: EX 팀만','조건 비교: 상위 8팀','정밀: 상위 200팀']);
  assert(p.poolLimit<40);assert.equal(p.D.screen.runs,2);
  const combinations=p.poolLimit*(p.poolLimit-1)*(p.poolLimit-2)*(p.poolLimit-3)/24;
  assert.equal(p.stages[2].games,combinations*18,'estimate includes all boundary ties');
  const growth=daily.plan({...f,nowMs:Date.parse('2026-11-26T05:00:00+09:00'),secondsPerGame:.01,growthResults:f.results});
  assert(growth.estimatedSec<5400);assert(growth.poolLimit<=p.poolLimit);assert.equal(growth.passes,2);
}
async function checks(daily=Daily){
  const strong=await scenario({daily});valid(strong.out,1);assert.equal(strong.out.split.ex,1);
  assert(!strong.trace.some(m=>m.teams.some(t=>t.options.guild.step!==7)));
  const weak=await scenario({daily,weak:true});valid(weak.out,1);assert.equal(weak.out.split.ex,1);
  assert(!weak.trace.some(m=>m.teams.some(t=>t.options.guild.step!==7)),'weak EX still stays EX');
  const normalBest=await scenario({daily,day:'2026-11-27T04:00:00+09:00',scoreFn:t=>t.options.guild.step===5?2000:1000});
  valid(normalBest.out,1);assert.equal(normalBest.out.teams[0].step,5,'choose score, not highest stage number');
  assert(strong.trace.some(m=>m.n_runs===18&&m.teams.some(t=>t.options.run_offset===2)));
  const chain=await scenario({daily,count:12,follows:1});valid(chain.out,2);
  assert.deepEqual(plain(chain.out.split),{ex:1,normal:1});assert.equal(chain.out.seals.used,3);
  assert.deepEqual(chain.out.teams[0],chain.rounds[0].out.teams[0],'first team unchanged');
  const used=new Set(chain.out.teams[0].keys),sup=chain.out.teams[0].sup;
  assert(chain.rounds[1].trace.every(m=>m.teams.every(t=>t.options.guild.step!==7&&t.party.units.every(u=>!used.has(u.key))&&t.options.guild.support!==sup)));
  assert(chain.out.teams[1].sup!=='none');assert.equal(chain.out.teams[1].effectiveSupport,'none','mismatched support is still assigned');
  assert.notEqual(chain.out.teams[0].signature,chain.out.teams[1].signature);
  await assert.rejects(()=>scenario({daily,count:12,follows:2}),/인장 3장/);
  const closed=await scenario({daily,count:12,follows:2,day:'2026-11-27T04:00:00+09:00'});valid(closed.out,3);
  assert.equal(closed.out.seals.used,3);assert.equal(closed.out.seals.remaining,0);
  assert(closed.trace.every(m=>m.teams.every(t=>t.options.guild.step!==7)));
  assert.deepEqual(closed.out.teams.slice(0,2),closed.rounds[1].out.teams);
  assert.equal(closed.rounds[1].trace.filter(m=>m.phase===2).length,0,'normal sweep cache reused');
  assert.equal(closed.rounds[2].trace.filter(m=>m.phase===2).length,0,'third sweep also reused');
  await assert.rejects(()=>scenario({daily,count:16,follows:3,day:'2026-11-27T04:00:00+09:00'}),/인장 3장/);
  const grown=await scenario({daily,count:8,follows:1,growth:true});valid(grown.out,2);valid(grown.out.growth,2);
  for(const stage of [2,4,6,7]){
    const stopped=await scenario({daily,stop:stage});assert(stopped.out.partial);
    if(stage===2)assert.equal(stopped.out.teams.length,0);
    if(stage===4)assert(stopped.out.flags.includes('스테이지·지원 미평가'));
    if(stage===7){valid(stopped.out,1);assert(!stopped.out.teams[0].evaluation.placementComplete);}
  }
  const stopped=await scenario({daily,count:12,follows:1,stop:2,stopRound:1});valid(stopped.out,1);
  assert(stopped.out.partial);assert(!stopped.out.teams[0].evaluation.partial,'partial follow does not mark earlier team partial');
  assert.equal(stopped.out.seals.used,2);
  const resumed=await scenario({daily,count:12,follows:2,stop:2,stopRound:1});valid(resumed.out,2);
  assert(resumed.rounds[1].out.partial);assert(!resumed.out.partial,'empty stopped attempt does not taint completed retry');
  assert(resumed.out.teams.every(t=>!t.evaluation.partial));
  const moved=await scenario({daily,move:true});assert(moved.out.teams.some(t=>t.placementChanged));
  return {chain,closed};
}
async function regression(daily=Daily){
  const capped=await scenario({daily,timeOutStage:6});assert(capped.out.partial&&capped.out.timeCapped);
  await assert.rejects(()=>scenario({daily,staleAt:6}),/취소/);
  const coop=await scenario({daily,settings:S=>{S.banCoop=true;},viaFn:t=>({coop:t.party.units.some(u=>u.key==='u00')?.1:0})});
  valid(coop.out,1);assert(!coop.out.teams[0].keys.includes('u00'));
  const clear=await scenario({daily,scoreFn:t=>{const keys=t.party.units.map(u=>u.key);return score(t)+(keys.join()===keys.slice().sort().join()&&t.party.leader===0?1000:0);}});
  assert(!clear.trace.some(m=>m.phase===7&&m.teams.some(t=>t.options.run_offset===100)));
  const growthPartial=await scenario({daily,growth:true,stopWhen:({phase,phases})=>phase===6&&phases.filter(p=>p.policyStage===2).length===2});
  assert(growthPartial.out.partial&&growthPartial.out.growth.partial);
  const scoreFn=t=>{const keys=t.party.units.map(u=>u.key).sort(),moved=t.party.units[t.party.leader].key===keys.at(-1),g=t.options.guild;
    return score(t,{move:true})+(moved&&g.level===2?500:0)+(moved&&g.support==='s4'?100:0);};
  const after=await scenario({daily,settings:S=>{S.supportRole={};},scoreFn});valid(after.out,1);
  assert(after.phases.some(p=>p.label==='바뀐 자리의 스테이지·지원 재확인'));
  assert(after.phases.some(p=>p.label==='바뀐 조건 40판 확인'));
  assert(after.phases.some(p=>p.label==='바뀐 조건 브레이크 재비교'));
  const {cx,out}=await scenario({daily});delete cx.session;
  await assert.rejects(()=>daily.search({...cx,previous:out,nowMs:cx.nowMs+86400000}),/조건이 바뀌/);
  await assert.rejects(()=>daily.search({...cx,previous:out,results:{...cx.results,u00:{...cx.results.u00,power:1234}}}),/조건이 바뀌/);
}
async function main(){
  packing();margins();caps();const measured=await checks();await regression();const scenarios=scenarioCount;
  const old=Daily.search;let dispatched=false;Daily.search=async()=>{dispatched=true;return {};};
  try{await Planner.search({...fixture(),S:{...defaults,preset:'daily'}});assert(dispatched);}finally{Daily.search=old;}
  const src=fs.readFileSync(require.resolve('../guild_daily'),'utf8');
  const mutations=[
    ['Math.abs(value(incumbent))*margin','0',margins],
    ["placeScope='ex';reductions.push","placeScope='all';reductions.push",caps],
    ['cx.roster.filter(r=>!units.has(r.key))','cx.roster',checks],
    ['cx.S.final.supports.filter(s=>!supports.has(s))','cx.S.final.supports',checks],
    ['>D.seals.max','>99',checks],
    ['cache=shared.caches.get(pass)||new Map()','cache=new Map()',checks],
    ['session.resume();','',checks],
    ['partial:partial||teams.some(t=>t.evaluation?.partial)','partial:partial||!!previous?.partial',checks],
    ["effectiveSupport=GS.finalSupports(S,keys,cls).includes(sup)?sup:'none'","effectiveSupport=sup",checks],
    ['if(pick.key===original.key)','if(true)',checks],
    ['combos*sweeps*(D.rerank.runs-D.screen.runs)','keep*sweeps*(D.rerank.runs-D.screen.runs)',caps],
    ['cx.previous.inputSignature!==inputSig','false',regression],
    ['if(pick===inc&&challenger&&choosePlacement(challenger,inc,D.place.margin)===challenger)','if(pick===inc)',regression]
  ];
  for(const [from,to,check] of mutations){assert(src.includes(from),from);const ctx={module:{exports:{}},require:n=>require('../'+n),setTimeout,clearTimeout};
    vm.runInNewContext(src.replace(from,to),ctx);await assert.rejects(async()=>check(ctx.module.exports),undefined,'mutation must fail: '+from);
  }
  console.log('Fresh jobs by click (synthetic): EX→normal '+measured.chain.rounds.map(r=>r.jobs)+'; closed normal×3 '+measured.closed.rounds.map(r=>r.jobs));
  console.log(`PASS daily: ${scenarios} fake-worker scenarios; ${mutations.length} killed mutations`);
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={fixture,scenario,checks,packing,margins,caps};
