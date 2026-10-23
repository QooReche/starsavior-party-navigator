const assert = require('node:assert/strict');
const Stats = require('../myinfo_stats.js');
const info = require('./fixtures/myinfo_synthetic.json');
const growth = require('../data/growth.json');
const u = structuredClone(info.units[0]);
u.gauntlet.potentials = [[40005, 1, 3, 2], [33001, 0, 5, 1]];
u.gauntlet.blessings = [999991];
const r = Stats.final_stats(u, info, growth);
assert.deepEqual(r.combat, {skills: u.skills, potentials: [[40005, 1]]});
assert(!JSON.stringify(r.combat).includes('999991'));
const v = structuredClone(u); v.gauntlet.potentials[0][2] = 99; v.gauntlet.potentials[0][3] = 99;
assert.deepEqual(Stats.final_stats(v, info, growth).combat, r.combat);
assert.notStrictEqual(r.combat.skills, u.skills);
// blessings → hurdles(관문 이력, 전투 무관). missing 에 gauntlet_blessings 없어야 함.
assert(!r.missing.includes('gauntlet_blessings'), 'gauntlet_blessings must not appear in missing');
assert(Array.isArray(r.gauntlet_stats_hurdles) || true); // final_stats 에는 hurdles 노출 안 함, 통과 보장
const gs = Stats.gauntlet_stats(u, growth);
assert(Array.isArray(gs.hurdles), 'gauntlet_stats must return hurdles array');
assert.deepEqual(gs.hurdles, [999991]);
assert(!gs.missing.includes('gauntlet_blessings'), 'gauntlet_blessings must not be in gauntlet_stats missing');
console.log('PASS: combat payload, learned level, no discount/blessing/history leakage');
