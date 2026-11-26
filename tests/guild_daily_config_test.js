const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const V=require('../guild_view'),defaults=require('../data/guild_defaults.json'),G=require('./guild_fixture')(30112);
function dates(view=V){
  const cases=[['2026-11-25T01:00:00+09:00','2026-11-24','화',true],
    ['2026-11-25T03:59:59.999+09:00','2026-11-24','화',true],
    ['2026-11-25T04:00:00+09:00','2026-11-25','수',false],
    ['2026-11-26T04:00:00+09:00','2026-11-26','목',true]];
  for(const [time,date,day,open] of cases){const r=view.gameDay(G,Date.parse(time));assert.equal(r.date,date);assert.equal(r.day,day);assert.equal(r.exOpen,open);}
  assert.equal(view.gameDay(G,Date.parse(cases[2][0])).nextEx,'목');
}
dates();
const Daily=require('../guild_daily'),D=defaults.search.daily;
assert.deepEqual(D.seals,{max:3,costNormal:1,costEx:2,dailyGrant:2,grantCap:2,purchaseMax:1,purchaseCost:30});
assert.equal(D.split,undefined);assert.equal(Daily.splits,undefined);
assert.equal(Daily.plan({G,S:G.search,roster:[],results:{},nowMs:Date.parse('2026-11-26T05:00:00+09:00')}).kind,'ex');
assert.equal(Daily.plan({G,S:G.search,roster:[],results:{},nowMs:Date.parse('2026-11-27T04:00:00+09:00')}).kind,'normal');
assert.equal(defaults.search.preset,'daily');
assert.equal(G.search.preset,defaults.search.preset);
assert.equal(require('../data/guild_defense.json').search.preset,defaults.search.preset);
assert.deepEqual(G.search.daily,defaults.search.daily);
assert.deepEqual(require('../data/guild_defense.json').search.daily,defaults.search.daily);
assert.deepEqual(G.search.daily.workers,require('../data/cosmo_raid.json').search.workers);
const src=fs.readFileSync(require.resolve('../guild_view'),'utf8');
const ctx={module:{exports:{}},require:n=>require('../'+n)};
vm.runInNewContext(src.replace('reset.utcOffsetHours-reset.hour','reset.utcOffsetHours'),ctx);
assert.throws(()=>dates(ctx.module.exports),assert.AssertionError);
console.log('PASS daily config: seal costs/cap/single-team defaults, defaults/copies/workers, 4 KST boundary cases, reset mutation');
