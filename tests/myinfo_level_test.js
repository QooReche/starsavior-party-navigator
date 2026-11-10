const assert=require('node:assert/strict');
const M=require('../myinfo_import.js'),S=require('../myinfo_stats.js'),V=require('../myinfo_view.js');
const info={format:M.FORMAT,star_link_level:201,star_link:{level:201,source:[900002],slots:[{index:0,id:900001},{index:99,id:0}]},
  units:[{id:900001,level:23},{id:900002,level:200},{id:900003,level:17}]};
assert.equal(M.validate(info),'');
assert.deepEqual(M.warnings(info),[]);
assert.deepEqual(info.units.map(u=>S.effective_level(u,info)),[201,201,17]);
assert.match(V.levelBadge(info.units[0],info),/Lv201.*스타링크 · 슬롯/);
assert.match(V.levelBadge(info.units[1],info),/Lv201.*스타링크 · 소스/);
assert.doesNotMatch(V.levelBadge(info.units[2],info),/스타링크/);
assert.match(V.levelBadge(info.units[2],info),/Lv17/);
assert.match(V.levelBadge(info.units[0],info,'fixed200'),/Lv200/);
assert.doesNotMatch(V.levelBadge(info.units[0],info,'fixed200'),/스타링크/);
const clone=()=>structuredClone(info);
for(const value of [0,-1,1.5,'23',null,true,2147483648]){
  let x=clone();x.units[0].level=value;assert.notEqual(M.validate(x),'');
  x=clone();x.star_link.level=value;assert.notEqual(M.validate(x),'');
}
for(const change of [
  x=>x.star_link=null,x=>x.star_link=[],x=>x.star_link.level=200,
  x=>x.star_link.source=[1,2,3,4,5],x=>x.star_link.source=[1,1],
  x=>x.star_link.source=[0],x=>x.star_link.source=['1'],x=>x.star_link.source={},
  x=>x.star_link.slots={},x=>x.star_link.slots=[null],
  x=>x.star_link.slots=[{index:0,id:-1}],x=>x.star_link.slots=[{index:100,id:1}],
  x=>x.star_link.slots=[{index:-1,id:1}],x=>x.star_link.slots=[{index:0.5,id:1}],
  x=>x.star_link.slots=[{index:0,id:1.5}],x=>x.star_link.slots=[{index:0,id:1},{index:0,id:2}],
]){const x=clone();change(x);assert.notEqual(M.validate(x),'');}
const missing=clone();missing.star_link.slots.push({index:4,id:900099});
assert.equal(M.validate(missing),'');assert.deepEqual(M.warnings(missing),['스타링크 슬롯 구원자 정보 없음']);
const empty=clone();empty.star_link.source=[];empty.star_link.slots=[];assert.equal(M.validate(empty),'');
const old=require('./fixtures/myinfo_legacy.json');assert.equal(M.validate(old),'');
assert.equal(S.level_info(old.units[0],old).source,'legacy');
assert.deepEqual(S.level_info(old.units[0],old).missing,['star_link.level','star_link.slots','star_link.source','unit.level']);
console.log('PASS effective levels, badges, validation, missing-slot warning, legacy');
