const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const P=require('../party_placement'),Direct=require('../direct_party');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const source=html.slice(html.indexOf('function simParty('),html.indexOf('const simSigB='));
function check(code=source){
 const keys=['a','b','c','d'],stats=Object.fromEntries(keys.map((k,i)=>[k,{stats:{hp:(i+1)*100,def:0,spd:i},power:100,combat:{}}]));
 const winner={order:['c','b','d','a'],leaderKey:'d'},cache=new Map([['same',winner]]);
 const c={CFG:{recommendation:{placementBaseline:true,placementCompare:false}},PartyPlacement:P,DirectParty:Direct,
  PLACEMENT_CACHE:cache,rememberPlacement(t,key,p){t.combo.placement=p;},recommendationPlacementKey:()=> 'same',
  ekey:k=>k,arrangeOf:()=>({order:['c','a','b','d'],lead:'b'}),QK:{d:{sv:Object.fromEntries(keys.map(k=>[k,[0,1,1,1,1,1]]))}},Quick:{MUL:1}};
 vm.createContext(c);vm.runInContext(code,c);
 const t={combo:[],ek:keys,b:{finals:stats}},get=()=>JSON.parse(JSON.stringify(c.simParty(t)));
 const baseline=P.baseline(keys,stats);assert.deepEqual(get().units.map(u=>u.key),baseline.order);assert.equal(get().leader,baseline.order.indexOf(baseline.leaderKey));
 c.CFG.recommendation.placementCompare=true;assert.deepEqual(get().units.map(u=>u.key),winner.order);assert.equal(get().leader,0+winner.order.indexOf(winner.leaderKey));
 c.CFG.recommendation.placementCompare=false;assert.deepEqual(get().units.map(u=>u.key),baseline.order,'turning compare off ignores a previous winner');
 c.CFG.recommendation.placementBaseline=false;assert.deepEqual(get().units.map(u=>u.key),keys);assert.equal(get().leader,1);
}
check();const gate='CFG.recommendation?.placementCompare?PLACEMENT_CACHE.get(key):null';assert(source.includes(gate));
assert.throws(()=>check(source.replace(gate,'PLACEMENT_CACHE.get(key)')));
console.log('PASS recommendation cache: A/B off, B only, A on/off transition, mutation');
