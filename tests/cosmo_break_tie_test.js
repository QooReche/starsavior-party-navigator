// 최종 브레이크 순위 → 자동 카드 머리 → 직접 편성 가져오기까지 같은 결과로 검사함.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const C=require('../cosmo_search'),D=require('../cosmo_direct');
const bosses=['a','b','c'],brks=[null,{name:'스킬 A',level:3},{name:'스킬 B',level:5}];
const teams=bosses.map((boss,i)=>({keys:[0,1,2,3].map(k=>'u'+(i*4+k)),order:[0,1,2,3].map(k=>'u'+(i*4+k))}));
const triples=[{teams}],season={bosses:bosses.map(key=>({key})),levelMax:18};
const summary=(top,mean,clear=.4)=>({top,mean,clear,frac:.8,n:40});
function rank(stats,mode='top',options={}){
  const variants=options.brks||brks,res={};
  teams.forEach((t,i)=>variants.forEach((b,j)=>{if(stats[j])res[C.jobKey(bosses[i],t.keys,6,b)]={cosmo:stats[j],via:{},progs:[.8]};}));
  return C.finalRankBrk(triples,bosses,()=>6,variants,res,mode,1)[0];
}
const source=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const bar=source.slice(source.indexOf('function seasonBreakBar('),source.indexOf('function ownedSimBreaks('));
const ctx={GuildSearch:require('../guild_search'),esc:String,CFG:{breakSkills:{}},D:{bicons:{}},BG:{}};
vm.createContext(ctx);vm.runInContext(bar,ctx);
function checkPick(row,name){assert(row.sum>0);assert(row.teams.every(t=>t.brk===name&&!t.brkTie));}
let count=0;
function test(name,f){f();count++;console.log('PASS '+name);}
test('상위 동점이면 평균 점수',()=>{
  const r=rank([summary(100,60),summary(100,80),summary(100,70,1)]);checkPick(r,'스킬 A');
  assert.equal(r.sum,300);assert.equal(r.sum2,240);
});
test('평균 동점이면 상위 점수',()=>checkPick(rank([summary(100,60),summary(120,60),summary(130,50,1)],'mean'),'스킬 A'));
test('두 점수 동점이면 클리어율',()=>checkPick(rank([summary(90,60,1),summary(100,80,.4),summary(100,80,.8)]),'스킬 B'));
test('기준 점수 우선 및 일반 가져오기',()=>{
  const r=rank([summary(100,90,1),summary(110,80,.2),summary(105,100,1)]);checkPick(r,'스킬 A');
  assert.equal(r.teams[0].brkLv,3);
  assert.deepEqual(D.fromSearch(r,season).teams.a.draft.brk,{name:'스킬 A',level:3});
  assert(ctx.seasonBreakBar(r.teams[0]).includes('스킬 A'));
});
test('미장착이 더 좋으면 기존 선택 유지',()=>checkPick(rank([summary(120,90),summary(110,80),summary(100,90)]),null));
test('완전 동점은 표·자동 카드 문구 및 직접 편성 null',()=>{
  const r=rank([summary(100,80),summary(100,80),summary(100,80)]);
  assert(r.teams.every(t=>t.brkTie===true&&t.brk===null));
  const message='브레이크 스킬: 점수 차이 없음(아무거나 장착 가능)';
  assert(C.table(r,'top',{esc:String,bossName:String,label:String}).includes(message));
  const html=C.table(r,'top',{esc:String,bossName:String,label:String,team:t=>ctx.seasonBreakBar(t)});
  assert.equal(html.split(message).length-1,3);assert(!html.includes('장착 안 함'));
  assert(ctx.seasonBreakBar(r.teams[0],true).includes(message));
  assert(Object.values(D.fromSearch(r,season).teams).every(t=>t.draft.brk===null));
});
test('점수 완전 동점은 클리어율이 달라도 안내·가져오기 null',()=>{
  const r=rank([summary(100,80,.2),summary(100,80,.8),summary(100,80,.4)]);
  assert(r.teams.every(t=>t.brkTie===true&&t.brk==='스킬 A'&&t.st.clear===.8));
  assert(Object.values(D.fromSearch(r,season).teams).every(t=>t.draft.brk===null));
});
test('일부 후보만 동점이면 전체 동점 아님',()=>checkPick(rank([summary(100,80),summary(100,80),summary(90,80)]),null));
test('미장착 결과 누락이면 동점 선언 안 함',()=>checkPick(rank([null,summary(100,80),summary(100,80)]),'스킬 A'));
test('미장착을 비교하지 않았으면 동점 선언 안 함',()=>checkPick(rank([summary(100,80),summary(100,80)],'top',{brks:brks.slice(1)}),'스킬 A'));
test('비교 스킬이 없으면 기존 미장착 표시',()=>{
  const r=rank([summary(100,80)],'top',{brks:[null]});checkPick(r,null);
  assert(ctx.seasonBreakBar(r.teams[0]).includes('브레이크 스킬 장착 안 함'));
});
console.log(`브레이크 동점 단위 통과 ${count} / 실패 0`);
