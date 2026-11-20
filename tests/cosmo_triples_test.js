// Synthetic lists only. The frozen implementation fixes scores AND tie order.
const assert = require('node:assert/strict');
const C = require('../cosmo_search.js'), legacy = require('./helpers/cosmo_triples_legacy.js');
const rng = require('../cosmo_learned.js').random(20261120);
const id = t => t.teams.map(e => C.idOf(e.keys)).join('/');
const hit = (a,b) => a.keys.some(k => b.keys.includes(k));
const entry = (key,score) => ({keys:[key],score});
function randomLists(trial) {
  const size = [12,16,32,95][trial%4];
  return [0,1,2].map(() => {
    const out=[], seen=new Set(), count=1+Math.floor(rng()*25);
    for(let i=0;i<count;i++) {
      const keys=new Set(); while(keys.size<4)keys.add('u'+Math.floor(rng()*size));
      const e={keys:[...keys],score:Math.floor(rng()*8)-2}, key=C.idOf(e.keys);
      if(!seen.has(key)){seen.add(key);out.push(e);}
    }
    return out.sort((a,b)=>b.score-a.score);
  });
}
function allTriples(lists) {
  const out=[];
  for(const a of lists[0])for(const b of lists[1])if(!hit(a,b))for(const c of lists[2])if(!hit(a,c)&&!hit(b,c))out.push({sum:a.score+b.score+c.score,teams:[a,b,c]});
  return out.sort((a,b)=>b.sum-a.sum||(id(a)<id(b)?-1:id(a)>id(b)?1:0));
}
async function main() {
  let oldChecks=0,newChecks=0,short=0,limited=0,certified=0;
  for(let trial=0;trial<600;trial++) {
    const lists=randomLists(trial), n=[1,3,10][trial%3], ob={remaining:1e9}, nb={remaining:1e9};
    const expected=legacy(lists,n,ob), actual=C.bestTriples(lists,n,nb);
    assert.deepEqual(actual,expected,'legacy trial '+trial);
    assert(nb.remaining>=ob.remaining,'checks do not increase '+trial);
    oldChecks+=1e9-ob.remaining;newChecks+=1e9-nb.remaining;
    if(actual.length<n)short++;
    if(trial<80) {
      const full=allTriples(lists);
      assert.deepEqual(actual,full.slice(0,n),'exhaustive trial '+trial);
      for(const cap of [0,1,2,5,10,30,80]) {
        const b={remaining:cap}, got=C.bestTriples(lists,n,b);
        if(!b.exhausted){assert.deepEqual(got,expected);continue;}
        limited++;
        const {a:ai,b:bi,c:ci}=b.position, a=lists[0][ai];
        const Ba=lists[1].filter(x=>!hit(a,x)), Ca=lists[2].filter(x=>!hit(a,x));
        const tail=a.score+Ba[bi].score+Ca[ci??0].score;
        const nextB=bi+1<Ba.length?a.score+Ba[bi+1].score+Ca[0].score:-Infinity;
        const nextA=ai+1<lists[0].length?lists[0][ai+1].score+lists[1][0].score+lists[2][0].score:-Infinity;
        assert.equal(b.upperBound,Math.max(tail,nextB,nextA),'remaining bound formula');
        const present=new Set(got.map(id)), missing=full.filter(t=>!present.has(id(t)));
        // Already checked losers can be above the remaining bound; they cannot beat floor.
        const floor=got.length===n?got.at(-1).sum:-Infinity;
        assert(missing.every(t=>t.sum<=Math.max(b.upperBound,floor)),'bound covers unseen winners');
        if(!C.triplesLimited(got,n,b)){certified++;assert.deepEqual(got,expected,'certified exact top');}
      }
    }
  }
  assert(short>100 && limited>100);
  assert(newChecks<oldChecks*.8,`${newChecks} / ${oldChecks}`);
  const single=[[entry('a',3)],[entry('b',2)],[entry('c',1)]];
  const exact={remaining:2};C.bestTriples(single,10,exact);
  assert.equal(exact.remaining,0);assert(!exact.exhausted,'zero remaining is normal completion');
  const ten=Array.from({length:10},()=>({sum:100,teams:[]}));
  assert.equal(C.triplesLimited(ten,10,{exhausted:true,upperBound:99}),false);
  assert.equal(C.triplesLimited(ten,10,{exhausted:true,upperBound:100}),true,'ties still need ID comparison');
  assert.equal(C.triplesLimited(ten,10,{exhausted:true,upperBound:101}),true);
  assert.equal(C.triplesLimited(ten.slice(1),10,{exhausted:true,upperBound:99}),true,'need all ten');
  assert.equal(C.triplesLimited(ten,10,{exhausted:false,remaining:0}),false);
  assert.equal(C.triplesLimited(ten,10,{exhausted:true}),true,'missing bound cannot certify');
  // A late high branch must survive a locally weak earlier A branch.
  const trap=[[entry('a',100),entry('b',99),entry('c',98)],
    [entry('b',100),entry('d',50)],[entry('e',100)]];
  assert.deepEqual(C.bestTriples(trap,2),legacy(trap,2));
  // Stop immediately before a prunable C tail: a genuinely exhausted budget can be certified.
  const tail=[[entry('a',100)],[entry('b',100)],Array.from({length:11},(_,i)=>entry('c'+i,100-i))];
  const tb={remaining:11}, tr=C.bestTriples(tail,10,tb);
  assert(tb.exhausted && tb.upperBound<tr.at(-1).sum);
  assert(!C.triplesLimited(tr,10,tb));assert.deepEqual(tr,legacy(tail,10));
  assert.deepEqual(await C.bestTriplesAsync(tail,10,{remaining:11}),tr);
  // Enough tied candidates to require yielding; the timer must cancel before completion.
  const large=[0,1,2].map(b=>Array.from({length:100},(_,i)=>entry(b+'-'+i,1)));
  let canceled=false;setTimeout(()=>{canceled=true;},0);
  await assert.rejects(C.bestTriplesAsync(large,10,{remaining:2e6},()=>canceled),/취소/);
  assert.deepEqual(C.bestTriples([[],[],[]],10),[]);
  console.log(`PASS 600 legacy/exhaustive trials; checks ${oldChecks} -> ${newChecks}; short ${short}; budgets ${limited}; certificates ${certified}; async cancellation`);
}
main().catch(e=>{console.error(e);process.exitCode=1;});
