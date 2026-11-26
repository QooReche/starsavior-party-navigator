const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const UI=require('../guild_daily_ui'),V=require('../guild_view'),U=require('../ui_shared'),Ux=require('../ux_ui');
const G=require('./guild_fixture')(30112),day=Date.parse('2026-11-26T12:00:00+09:00');
const team={kind:'ex',step:7,level:9,order:['a','b','c','d'],leaderKey:'c',sup:G.search.final.supports.find(s=>s!=='none'),score:20000,mean:18000,clear:.6,brk:'test',brkLv:3,
  evaluation:{partial:true,stageSupportComplete:true,placementComplete:false}};
const cx={G,nowMs:day,esc:U.esc,hasInfo:true,sig:'same',plan:null,cards:()=>'<div class="rowcards gs-compact">cards</div>',breakBar:()=>'<div class="bbar">break</div>',label:k=>k,say:Ux.gwenSay,work:()=>'<div data-gwen-slot="guildSearch-board"></div>',report:()=>'<div data-gwen-slot="guildSearch-result"></div>',error:()=>''};
const done={phase:'done',rows:[team],teams:[team],sum:20000,split:{ex:1,normal:0},seals:{used:2,remaining:1},flags:['자리·리더 미평가'],partial:true,plan:{day:V.gameDay(G,day),reductions:[]},sig:'same'};
function contracts(ui){
  assert.deepEqual(Array.from(ui.flags(team)),['자리·리더 미평가']);
  const idle=ui.html({phase:'idle'},cx);assert(!idle.includes('seal-stepper'));assert(!idle.includes('자동(추천)'));
  assert(idle.includes('오늘 편성 찾기 (1팀)'));assert(idle.includes('오늘 EX 한 팀부터 찾아볼게'));
  assert(idle.includes('2장(기본 지급) · 3장째는 구매 1회 성광석 30'));
  const closed=ui.html({phase:'idle'},{...cx,nowMs:Date.parse('2026-11-27T04:00:00+09:00')});
  assert(closed.includes('금요일 · EX 닫힘 · 다음 EX는 토요일'));assert(closed.includes('오늘 편성 찾기 (1팀)'));
  assert(ui.html(done,cx).includes('data-gs="follow"'));
  assert(!ui.html({...done,seals:{used:3,remaining:0}},cx).includes('data-gs="follow"'));
  assert(!ui.html({...done,sig:'old'},cx).includes('data-gs="follow"'));
  assert(!ui.html(done,{...cx,nowMs:day+86400000}).includes('data-gs="follow"'));
  assert.equal(ui.sayKey({following:true},null,{exOpen:true}),'guildFollow');
  const out=ui.html(done,cx);assert(out.includes('data-k="gs-score">20,000'));assert(out.includes('자리·리더 미평가'));assert(out.includes('부분 결과'));assert(out.includes('★ 별의 도전 9 · 추가 점수 +'));assert(!out.includes('9단계'));assert(out.includes('data-team="0"'));assert(!out.includes('다른 묶음'));
  assert.deepEqual(JSON.parse(JSON.stringify(ui.draft(team))),{v:1,slots:team.order.map(key=>({key,grown:false})),leader:'c',brk:{name:'test',level:3}});
  assert.equal(ui.draft({...team,brk:null}).brk,null);assert(ui.draft(team,true).slots.every(s=>s.grown));
  const normal=ui.chips(G,{kind:'normal',step:6,level:0});assert(normal.includes('스테이지 6단계'));assert(normal.includes('★ 별의 도전 없음'));
  const changed=ui.html(done,{...cx,nowMs:day+86400000});assert(changed.includes('날짜 바뀜'));assert(!changed.includes('어제 판'));
  assert(!ui.html({phase:'idle'},{...cx,hasInfo:false}).includes('data-gs="start"'));
  const run=ui.html({phase:'run'},cx);assert(run.includes('data-gs="partial">중단'));assert(run.includes('role="progressbar"'));assert(!run.includes('data-gs="cancel"'));
}
contracts(UI);
const source=fs.readFileSync(require.resolve('../guild_daily_ui'),'utf8');
for(const [from,to] of [["leader:t.leaderKey||t.order[0]","leader:t.order[0]"],["...(e&&!e.placementComplete?['자리·리더 미평가']:[])","...[]"],["${U.num(st.sum)}","0"],["st.seals.remaining>0","true"],["&&!stale&&!changed",""]]){
  assert(source.includes(from));const context={module:{exports:{}},require:require('node:module').createRequire(require.resolve('../guild_daily_ui'))};vm.runInNewContext(source.replace(from,to),context);assert.throws(()=>contracts(context.module.exports));
}
for(const k of ['guildPlan','guildFollow','guildClosed','guildDone','guildShort','guildPartial','guildReset'])assert(Ux.GWEN_SAY[k].every(s=>/[가-힣]/.test(s)&&!s.includes('???')));
assert.equal(require('../data/guild_defaults.json').search.preset,'legacy');
console.log('PASS daily UI: 16 presentation/import/follow contracts, 5 mutations, 7 Gwen keys, legacy default');
