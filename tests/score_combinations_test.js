const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const C=require('../score_combinations'),S=require('../score_search');
const plain=x=>JSON.parse(JSON.stringify(x)),id=e=>e.id;
const resources=e=>({units:e.keys,support:e.support?[e.support]:[],equipment:e.equipment||[]});
function exhaustive(lists,n){const out=[];
  function walk(i,teams,used,sum){
    if(i===lists.length){out.push({sum,teams});return;}
    for(const e of lists[i]){const tokens=Object.entries(resources(e)).flatMap(([kind,xs])=>xs.map(x=>JSON.stringify([kind,x])));if(tokens.some(t=>used.has(t)))continue;
      walk(i+1,[...teams,e],new Set([...used,...tokens]),sum+e.score);}
  }
  walk(0,[],new Set(),0);
  return out.sort((a,b)=>b.sum-a.sum||(a.teams.map(id).join('/')<b.teams.map(id).join('/')?-1:a.teams.map(id).join('/')>b.teams.map(id).join('/')?1:0)).slice(0,n);
}
function check(c=C){
  for(let count=1;count<=4;count++)for(let seed=1;seed<=40;seed++){
    const rng=S.random(seed),lists=Array.from({length:count},(_,i)=>Array.from({length:5},(_,j)=>{
      const key='u'+Math.floor(rng()*9),sup='s'+Math.floor(rng()*5);
      return {id:i+'-'+j,keys:[key],support:sup,equipment:['eq'+Math.floor(rng()*7)],score:Math.floor(rng()*5)};
    }).sort((a,b)=>b.score-a.score));
    assert.deepEqual(plain(c.bestSets(lists,4,null,{id,resources})),exhaustive(lists,4),count+' teams, seed '+seed);
  }
  const tie=[[{id:'z',keys:['a'],score:1},{id:'a',keys:['b'],score:1}],[{id:'x',keys:['c'],score:1}]];
  assert.equal(c.bestSets(tie,1,null,{id})[0].teams[0].id,'a');
  const lists=Array.from({length:4},(_,i)=>Array.from({length:40},(_,j)=>({id:i+'-'+j,keys:['u'+j],support:'u'+i,score:40-j}))); // more than 30 resource bits
  const best=c.bestSets(lists,1,null,{id,resources});assert.equal(best[0].sum,154);
  const budget={remaining:2};c.bestSets(lists,1,budget,{id,resources});assert(budget.exhausted);assert(budget.upperBound>=best[0].sum);assert(budget.position);
  const conflict=[[{id:'a',keys:['a'],support:'same',score:2}],[{id:'b',keys:['b'],support:'same',score:2}]];
  assert.deepEqual(plain(c.bestSets(conflict,1,null,{id,resources})),[]);
  assert.deepEqual(plain(c.bestSets([[]],1)),[]);assert.deepEqual(plain(c.bestSets([],1)),[]);
}
check();
const source=fs.readFileSync(require.resolve('../score_combinations'),'utf8');
for(const [from,to] of [['if (x[w] & y[w])','if (false)'],['Object.entries(resources(e))',"Object.entries({units:e.keys})"],['<floor())break','<=floor())break'],['if(L.length!==3)','if(false)']]){
  assert(source.includes(from));const ctx={module:{exports:{}}};vm.runInNewContext(source.replace(from,to),ctx);assert.throws(()=>check(ctx.module.exports));
}
console.log('PASS N-team combinations: 160 exhaustive resource/tie cases, wide masks, budget, 4 mutations');
