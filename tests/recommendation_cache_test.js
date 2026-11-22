const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const Direct=require('../direct_party');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const source=html.slice(html.indexOf('function simParty('),html.indexOf('const simSigB='));
// 추천 시뮬 파티 = 화면 카드 순서·리더 그대로(placementBaseline·placementCompare 스위치는 11/22 삭제 — 배치 비교는 직접 편성 24조건만)
function check(code=source){
 const keys=['a','b','c','d'],stats=Object.fromEntries(keys.map((k,i)=>[k,{stats:{hp:(i+1)*100,def:0,spd:i},power:100,combat:{}}]));
 const c={CFG:{recommendation:{}},DirectParty:Direct,ekey:k=>k,arrangeOf:()=>({order:['c','a','b','d'],lead:'b'}),
  QK:{d:{sv:Object.fromEntries(keys.map(k=>[k,[0,1,1,1,1,1]]))}},Quick:{MUL:1}};
 vm.createContext(c);vm.runInContext(code,c);
 const t={combo:[],ek:keys,b:{finals:stats}},got=JSON.parse(JSON.stringify(c.simParty(t)));
 const so=Direct.toEngine(['c','a','b','d']);
 assert.deepEqual(got.units.map(u=>u.key),so);assert.equal(got.units[got.leader].key,'b');
}
check();const lead='const li=so.indexOf(ar.lead)';assert(source.includes(lead));
assert.throws(()=>check(source.replace(lead,'const li=0')));
console.log('PASS recommendation party: screen order and leader, mutation');
