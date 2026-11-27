'use strict';
const KNOWN_DEFECT=false;
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const Daily=require('../guild_daily'),{scenario}=require('./guild_daily_test');
async function check(daily=Daily){
  const s=await scenario({daily,count:24,secondsPerGame:.05,day:'2026-11-27T12:00:00+09:00',
    settings:S=>{S.daily.probe.teams=12;S.daily.rerank.keep=600;}});
  const p=s.plans[0],t=s.out.teams[0],jobs=s.trace.filter(m=>m.phase===7).reduce((n,m)=>n+m.teams.length,0);
  assert.equal(p.day.exOpen,false);assert(p.withinCap);assert(p.poolLimit<24);
  assert.equal(p.placeScope,KNOWN_DEFECT?'ex':'all');
  assert(t.prog>0);assert.equal(s.out.partial,false);
  assert.equal(t.evaluation.placementComplete,!KNOWN_DEFECT);
  assert(KNOWN_DEFECT?jobs===0:jobs>0,`placement jobs: ${jobs}`);
}
(async()=>{
  await check();
  const src=fs.readFileSync(require.resolve('../guild_daily'),'utf8');
  const from='if(over()&&maxTeams>1)';
  assert(src.includes(from));
  const ctx={module:{exports:{}},require:n=>require('../'+n),setTimeout,clearTimeout};
  vm.runInNewContext(src.replace(from,'if(over())'),ctx);
  await assert.rejects(()=>check(ctx.module.exports),undefined,'one-team reduction must stay disabled');
  // Exercise the reduced-scope branch even though today's one-team plan needs no scope reduction.
  const reduced=src.replace("placeScope='all';const reductions", "placeScope='ex';const reductions");
  async function forced(code){
    const c={module:{exports:{}},require:n=>require('../'+n),setTimeout,clearTimeout};vm.runInNewContext(code,c);
    const s=await scenario({daily:c.module.exports,day:'2026-11-27T12:00:00+09:00'});
    assert(s.out.teams[0].prog>0);assert.equal(s.out.teams[0].evaluation.placementComplete,true);
    assert(s.trace.some(m=>m.phase===7));
  }
  await forced(reduced);
  await assert.rejects(()=>forced(reduced.replace("&&i>0)continue;",')continue;')));
  await assert.rejects(()=>forced(reduced.replace("!t||i===0||t.kind==='ex'","!t||t.kind==='ex'")));
  console.log('PASS closed-day first-team placement; positive progress; 3 mutations killed');
})().catch(e=>{console.error(e);process.exitCode=1;});
