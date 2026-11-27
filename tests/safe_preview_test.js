const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {fixture,scenario}=require('./guild_daily_test');
const Daily=require('../guild_daily'),V=require('../guild_view'),E=require('../search_executor');
const {teamResults}=require('../tools/bench_safe_daily');
const source=fs.readFileSync(require.resolve('../guild_daily_page'),'utf8');
function harness(src=source){
  const f=fixture(40);let calls=0;
  const c={D:{guild:f.G},R:f.roster,EXCL:new Set(),GSR:{banCoop:false},
    MI:{info:{},hash:'synthetic',growth:{},profiles:{op:{results:f.results}}},GuildView:V,
    day:Date.parse('2026-11-26T05:00:00+09:00'),grown:false,
    guildIdentity:()=>[f.G.season.id,f.G.dataVersion],gsTiers:()=>[],ownedSimBreaks:()=>[],
    growthOptions:()=>({growth:c.grown}),growthEnabled:()=>c.grown,
    GuildDaily:{plan(cx){calls++;return Daily.plan(cx);}}};
  c.Date=class extends Date{static now(){return c.day;}};
  c.GuildView={...V,gameDay:(g,now=c.day)=>V.gameDay(g,now)};
  vm.createContext(c);vm.runInContext(src,c);
  return {c,calls:()=>calls};
}
function checkPreview(src=source){
  const {c,calls}=harness(src),first=c.guildDailyPreview();
  for(let i=0;i<50;i++)assert.equal(c.guildDailyPreview(),first);
  assert.equal(calls(),1);
  for(const change of [()=>c.grown=true,()=>c.MI.profiles.op.results.u00.stats.atk++,
    ()=>c.EXCL.add('u01'),()=>c.GSR.banCoop=true,()=>c.D.guild.dataVersion='next',
    ()=>c.D.guild.search.daily.probe.teams++,()=>c.day+=86400000]){
    const before=calls();change();c.guildDailyPreview();assert.equal(calls(),before+1,'changed input rebuilds preview');
    c.guildDailyPreview();assert.equal(calls(),before+1);
  }
}
async function checkEta(daily=Daily){
  const original=E.etaNew;let estimates=0,progress=0;
  E.etaNew=(...args)=>{const e=original(...args),estimate=e.estimate;e.estimate=(...xs)=>{estimates++;return estimate(...xs);};return e;};
  try{
    const before=await scenario();assert(estimates>0);estimates=0;
    const after=await scenario({daily:{...daily,search:cx=>daily.search({...cx,progressEta:false,onProgress(){progress++;}})}});
    assert(progress>0);assert.equal(estimates,0,'unused callback ETA must not be evaluated');
    assert.deepEqual(teamResults(after.out),teamResults(before.out));
  }finally{E.etaNew=original;}
}
if(require.main===module){checkPreview();checkEta().then(()=>console.log('PASS: preview signatures and optional ETA')).catch(e=>{console.error(e);process.exitCode=1;});}
module.exports={harness,checkPreview,checkEta};
