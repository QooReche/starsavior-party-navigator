const assert=require('node:assert/strict');
const E=require('../search_executor'),P=require('../guild_planner'),C=require('../cosmo_search'),R=require('../reco_plan');
const G=require('../data/guild_defense.json'),S=G.search;
const pl=P.plan(S,1000,2);
assert.deepEqual(pl.stages.map(s=>[s.jobs,s.runs]),[[1000,2],[400,10],[12*13*S.final.supports.length,40],[8*3*3,40]]);
assert.equal(pl.total,pl.stages.reduce((n,s)=>n+s.games,0));
assert.equal(P.plan(S,1,0).stages[3].p,0);
assert.equal(P.plan(S,1,0).stages[3].jobs,0);
assert.equal(P.plan(S,1,2).stages[2].jobs,13*S.final.supports.length);
const config=require('../data/cosmo_raid.json').search;
const cosmo=C.plan(config,Array.from({length:12},(_,i)=>({key:'u'+i})),2);
const before=JSON.stringify(cosmo),stages=E.planStages(cosmo.stages);
assert.equal(JSON.stringify(cosmo),before);
assert.deepEqual(stages.map(s=>s.games),cosmo.stages.map(s=>s.games));
assert.deepEqual(stages.map(s=>s.id),cosmo.stages.map(s=>s.id));
for(const list of [pl.stages,stages]){
 assert(list.every(s=>s.name&&s.step&&s.jobs===s.teams&&s.games===s.jobs*s.runs&&s.p>=0&&s.p<=1));
 assert(R.remain(list,{workers:1,rate:{run:1},gap:0,now:0}).remain>0);
}
// Deliberately break an upper bound: the contract check must detect it.
const check=x=>assert(x.stages[3].jobs>=8*3*3);
check(pl);assert.throws(()=>check({...pl,stages:pl.stages.map(s=>s.id===4?{...s,jobs:8*2*3}:s)}));
console.log('PASS 12 stage plan contracts: guild ceilings, conditional break, RecoPlan/cosmo adapter, bound mutation');
