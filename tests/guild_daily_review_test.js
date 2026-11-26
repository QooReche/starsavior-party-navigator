// P3 review regressions: synthetic workers only, no battle engine or account data.
const assert=require('node:assert/strict');
const Daily=require('../guild_daily'),GS=require('../guild_search');
const {fixture,scenario}=require('./guild_daily_test');
const defaults=require('../data/guild_defaults.json').search;
const nowMs=Date.parse('2026-11-26T05:00:00+09:00');
const cases=[];const test=(name,fn)=>cases.push([name,fn]);
const banned=S=>{S.banCoop=true;};
const ordered=t=>t.party.leader===0&&t.party.units.map(u=>u.key).join()===t.party.units.map(u=>u.key).sort().join();
test('EX 31,500 + normal 3,000 loses to three normal 15,000 teams',async()=>{
  const {out,trace}=await scenario({count:12,seals:3,setup:({G,S})=>{
    G.steps.forEach(s=>{s.base=0;s.bossKill=15000;});S.daily.probe.teams=12;
  },scoreFn:t=>{
    const keys=t.party.units.map(u=>Number(u.key.slice(1))),g=t.options.guild;
    if(g.step===7)return keys.every(k=>k<4)?31500:100;
    const id=keys.sort((a,b)=>a-b).join();
    return ['0,4,5,6','1,7,8,9','2,3,10,11'].includes(id)?15000:id==='4,5,6,7'?3000:100;
  }});
  assert.equal(out.sum,45000);assert.equal(out.split.normal,3);
  assert(trace.some(m=>m.phase===6&&m.teams.some(t=>t.options.guild.step!==7)));
  assert(out.reason.includes('합산'));
});
test('pool floor preserves maximum split plus spare units, including unknown speed',()=>{
  const f=fixture(40);f.S.daily=structuredClone(defaults.daily);
  for(const secondsPerGame of [undefined,.05]){
    const p=Daily.plan({...f,seals:3,nowMs,secondsPerGame});
    assert(p.poolLimit>=20);assert.equal(p.availableTeams>=3,true);
  }
});
test('pool reduction preserves role supplements and front/dealer requirements',async()=>{
  const f=fixture(40);f.roster[39].cls='디펜더';f.roster[38].cls='서포터';
  Object.assign(f.S,{minFront:1,minDealer:1,minRole:{디펜더:1,서포터:1}});
  const old=GS.combos;let seen=false;
  GS.combos=(S,rows)=>{
    seen=true;assert(rows.some(r=>r.key==='u39'));assert(rows.some(r=>r.key==='u38'));
    assert(old(S,rows).length>0);throw Error('pool checked');
  };
  try{await assert.rejects(()=>Daily.search({...f,seals:3,nowMs,secondsPerGame:.05}),/pool checked/);assert(seen);}
  finally{GS.combos=old;}
});
test('unknown speed uses measured browser order of magnitude',()=>{
  const p=Daily.plan({...fixture(40),seals:3,nowMs,workers:1});
  assert(p.secondsPerGame>0&&p.secondsPerGame<.1);assert(p.estimateFallback);
});
test('saved cosmo speed is worker-adjusted and explicit measurement takes precedence',()=>{
  const cx={...fixture(40),nowMs,seals:3,workers:2,cosmoSpeed:{sec:[.01,.02,.03,.04],workers:1}};
  const p=Daily.plan(cx);assert.equal(p.secondsPerGame,.02);assert.equal(p.estimateFallback,false);
  assert.equal(Daily.plan({...cx,secondsPerGame:.003}).secondsPerGame,.003);
});
test('slow device refuses over-cap plan without cutting below floor',()=>{
  const f=fixture(40);f.S.daily=structuredClone(defaults.daily);
  const p=Daily.plan({...f,nowMs,seals:3,secondsPerGame:1});
  assert.equal(p.poolLimit,20);assert.equal(p.withinCap,false);
  assert.deepEqual(p.reductions.slice(0,3),['자리·리더 대상: EX 팀만','조건 비교: 상위 8팀','정밀: 상위 200팀']);
  assert.equal(Daily.plan({...fixture(12),nowMs,seals:3,secondsPerGame:1}).poolLimit,12);
});
test('three seals compare every split when initial EX total is below normal ceiling',async()=>{
  const C=require('../score_combinations'),old=C.steps,seen=new Set();
  C.steps=function(lists,...rest){seen.add(lists.length);return old(lists,...rest);};
  try{
    const {out}=await scenario({count:12,seals:3,scoreFn:t=>{
      const keys=t.party.units.map(u=>Number(u.key.slice(1)));
      return keys.every(k=>Math.floor(k/4)===Math.floor(keys[0]/4))?(t.options.guild.step===7?1999:1000):1;
    }});
    assert.equal(out.sum,3000);assert.equal(out.split.normal,3);
    for(const n of [2,3])assert(seen.has(n));
  }finally{C.steps=old;}
});
test('EX total equal to normal ceiling skips normal sweep',async()=>{
  const {out,trace}=await scenario({seals:2,scoreFn:t=>t.options.guild.step===7?2000:1000});
  assert.equal(out.sum,2000);assert.equal(out.split.ex,1);
  assert(!trace.some(m=>m.teams.some(t=>t.options.guild.step!==7)));assert(out.reason.includes('생략'));
});
test('final coop exclusion replaces invalid finalists',async()=>{
  const {out}=await scenario({seals:2,settings:banned,viaFn:(t,off,{phase})=>({coop:phase===6&&t.party.units.some(u=>u.key==='u00')?1:0})});
  assert.equal(out.teams.length,1);assert(!out.teams[0].keys.includes('u00'));assert(out.sum>0);
});
test('finals refill excluded slots even when another finalist survives',async()=>{
  const {out}=await scenario({count:12,seals:2,split:{ex:1,normal:0},settings:S=>{
    banned(S);S.final.supports=['s0'];S.daily.probe.levels=[0];S.daily.combine.top=2;
  },scoreFn:(t,i)=>{
    const keys=t.party.units.map(u=>Number(u.key.slice(1))),block=Math.floor(keys[0]/4);
    if(!keys.every(k=>Math.floor(k/4)===block))return 1;
    return block===0?10000:block===1?9000:i<10?8500:9500;
  },viaFn:(t,off,{phase})=>({coop:phase===6&&t.party.units.every(u=>Number(u.key.slice(1))<4)?1:0})});
  assert.equal(out.sum,9500);assert.deepEqual(out.teams[0].keys.slice().sort(),['u08','u09','u10','u11']);
});
test('final coop exhaustion returns shortage instead of exception',async()=>{
  const {out}=await scenario({seals:2,settings:banned,viaFn:(t,off,{phase})=>({coop:phase===6?1:0})});
  assert.equal(out.teams.length,0);assert.equal(out.seals.remaining,2);assert(out.warnings.some(s=>s.includes('팀만')));
});
test('excluded incumbent uses next valid placement',async()=>{
  const {out}=await scenario({seals:2,settings:banned,viaFn:(t,off,{phase})=>({coop:phase===7&&ordered(t)?1:0})});
  assert.equal(out.teams.length,1);assert(out.teams[0].placementChanged);assert(out.sum>0);
});
test('placement finalists refill from remaining layouts',async()=>{
  const {out}=await scenario({seals:2,settings:banned,viaFn:(t,off,{phase})=>({coop:phase===7&&off>0&&t.party.units[t.party.leader].key!=='u03'?1:0})});
  assert.equal(out.teams.length,1);assert.equal(out.teams[0].leaderKey,'u03');
});
test('placement coop exhaustion returns shortage',async()=>{
  const {out}=await scenario({seals:2,settings:banned,viaFn:(t,off,{phase})=>({coop:phase===7?1:0})});
  assert.equal(out.teams.length,0);assert.equal(out.seals.remaining,2);assert(out.warnings.some(s=>s.includes('팀만')));
});
test('signature separates effective pool, policy, and combination limit',()=>{
  const cx={...fixture(40),seals:3,nowMs,secondsPerGame:.0001},day=Daily.plan(cx).day;
  const base=Daily.signature(cx,day);
  assert.notEqual(base,Daily.signature({...cx,secondsPerGame:.05},day));
  assert.notEqual(base,Daily.signature({...cx,maxCombineChecks:17},day));
  const p=Daily.plan(cx);
  assert.notEqual(Daily.signature(cx,day,p),Daily.signature(cx,day,{...p,placeScope:'ex'}));
  assert.notEqual(Daily.signature(cx,day,p),Daily.signature(cx,day,{...p,D:{...p.D,probe:{...p.D.probe,teams:1}}}));
});
async function main(){let failed=0;for(const [name,fn] of cases){try{await fn();console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+'\n'+e.message);}}console.log(`${cases.length-failed}/${cases.length} P3 review regressions passed`);if(failed)process.exitCode=1;}
if(require.main===module)main();
