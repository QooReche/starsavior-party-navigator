'use strict';
const assert=require('node:assert/strict'),{stats,wilson,comparison}=require('../tools/evaluate_guild_time');
const a={scores:[10,20,30,40,50,60,70,80,90,100],clears:[0,0,0,0,0,0,0,0,1,1]};a.summary=stats(a.scores,a.clears);
assert.deepEqual(a.summary,{top:95,mean:55,clear:.2,n:10});
const same=comparison(a,a,100);assert.deepEqual(same.ci95,{topRatio:[1,1],meanRatio:[1,1],clearDifference:[0,0]});
const b={scores:a.scores.map(x=>x*.5),clears:a.clears.map(()=>0)};b.summary=stats(b.scores,b.clears);
assert.deepEqual(comparison(a,b,100).ci95.topRatio,[.5,.5]);assert.equal(comparison(a,b,100).point.clearDifference,-.2);
assert(wilson(0,1000)[1]<.004);assert(wilson(1,1000)[0]>.996);
assert.throws(()=>comparison(a,{...b,scores:[1]}),/length/);
// The tail mean must be recomputed per draw, not treated as a mean of all games.
assert.notEqual(a.summary.top,a.summary.mean);
console.log('PASS guild holdout score/tail/Wilson/paired interval and degradation detection');
