const assert=require('node:assert/strict');
const Daily=require('../guild_daily');
function check(daily=Daily){
  let created=0,closed=0;
  const s=daily.createSession(()=>({id:++created,terminate(){closed++;}}));
  s.resume('data1');const first=s.pool.get(0);
  s.caches.set(0,new Map([['old',{}]]));s.signature='old';
  s.reset();assert.equal(s.caches.size,0);assert.equal(s.signature,null);
  s.resume('data1');assert.equal(s.pool.get(0),first);assert.equal(closed,0);
  s.caches.set(0,new Map());s.resume('data2');
  assert.equal(s.caches.size,0);assert.notEqual(s.pool.get(0),first);assert.equal(closed,1);
  s.pool.close();s.resume('data2');s.pool.get(0);assert.equal(created,3);
  s.close();assert(s.closed);assert.equal(closed,3);
}
if(require.main===module){check();console.log('PASS: session reset/reuse/data change/cancel/close');}
module.exports={check};
