// Cross-pass result oracle with unequal stats/combat, seed intervals and via rates.
const assert=require('node:assert/strict');
const Daily=require('../guild_daily');
const {scenario}=require('./guild_daily_test');
const {baseline,teamResults}=require('../tools/bench_safe_daily');
async function check(daily=Daily){
  for(const field of ['same','stats','combat']){
    const run=async impl=>scenario({daily:{...impl,search(cx){
      if(field!=='same'){
        cx={...cx,growthResults:structuredClone(cx.growthResults)};
        if(field==='stats')cx.growthResults.u00.stats.atk+=71;
        else cx.growthResults.u00.combat.extra=71;
      }
      return impl.search(cx);
    }},growth:true,scoreFn:(t,i)=>1000+i%7+t.party.units.reduce((s,u)=>s+u.stats_override.atk+(u.myinfo_combat.extra||0),0),
      viaFn:(t,off)=>({trigger:(off+1)/7,coop:t.party.units[0].stats_override.atk/700})});
    const before=await run(baseline()),after=await run(daily);
    assert.deepEqual(teamResults(after.out),teamResults(before.out),field+' complete results');
    const games=r=>r.trace.reduce((s,m)=>s+m.teams.length*m.n_runs,0);
    assert(games(after)<games(before),field+' must actually reuse identical work');
  }
}
if(require.main===module)check().then(()=>console.log('PASS: daily exact-request reuse, stats/combat and via')).catch(e=>{console.error(e);process.exitCode=1;});
module.exports={check};
