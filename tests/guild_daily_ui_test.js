const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const UI=require('../guild_daily_ui'),V=require('../guild_view'),U=require('../ui_shared'),Ux=require('../ux_ui');
const G=require('./guild_fixture')(30112),day=Date.parse('2026-11-26T12:00:00+09:00');
const page=fs.readFileSync(require.resolve('../guild_daily_page'),'utf8');
const team={kind:'ex',step:7,level:9,order:['a','b','c','d'],leaderKey:'c',sup:G.search.final.supports.find(s=>s!=='none'),score:20000,mean:18000,clear:.6,brk:'test',brkLv:3,
  evaluation:{partial:true,stageSupportComplete:true,placementComplete:false}};
const base={G,nowMs:day,esc:U.esc,hasInfo:true,sig:'same',plan:null,cards:()=>'<div class="bbar">break</div><div class="rowcards cs-cards">cards</div>',work:()=>'<div data-gwen-slot="guildSearch-board"></div>',report:()=>'<div data-gwen-slot="guildSearch-board"></div>',error:()=>''};
const done={phase:'done',rows:[team],teams:[team],sum:20000,split:{ex:1,normal:0},seals:{used:2,remaining:1},flags:['자리·리더 미평가'],partial:true,plan:{day:V.gameDay(G,day),reductions:[]},sig:'same'};
function contracts(ui,adapter=page){
  const c={GuildDailyUI:ui,CosmoDirectUI:require('../cosmo_direct_ui'),R:team.order.map(key=>({key,name:key,img:key+'.png'}))};
  vm.runInNewContext(adapter,c);
  const cx={...base,summary:st=>c.guildDailySummary(st,'<div data-gwen-slot="guildSearch-result"></div>')};
  const before=JSON.stringify(done);
  assert.deepEqual(Array.from(ui.flags(team)),['자리·리더 미평가']);
  const idle=ui.html({phase:'idle'},cx);assert(!idle.includes('seal-stepper'));assert(!idle.includes('gwen-bubble'));assert(!idle.includes('약 '));
  assert(idle.includes('>오늘 편성 찾기</button>'));assert(idle.includes('data-fold="gs-options"'));assert(idle.includes('EX 열림 · EX 1팀 · 인장 2장'));
  assert(idle.includes('2장(기본 지급) · 3장째는 구매 1회 성광석 30'));
  const closed=ui.html({phase:'idle'},{...cx,nowMs:Date.parse('2026-11-27T04:00:00+09:00')});
  assert(closed.includes('금요일 · EX 닫힘 · 다음 EX는 토요일'));assert(closed.includes('금요일 EX 닫힘 · 일반 1팀 · 인장 1장'));
  assert(ui.html(done,cx).includes('data-gs="follow"'));
  assert(!ui.html({...done,seals:{used:3,remaining:0}},cx).includes('data-gs="follow"'));
  assert(!ui.html({...done,sig:'old'},cx).includes('data-gs="follow"'));
  assert(!ui.html(done,{...cx,nowMs:day+86400000}).includes('data-gs="follow"'));
  const out=ui.html(done,cx);assert(out.includes('data-k="gs-score">20,000'));
  assert(!out.includes('자리·리더 미평가'));assert(!out.includes('부분 결과'));assert(out.includes('중단함 · 여기까지 찾은 결과'));
  assert(out.includes('자료상 미평가: 자리·리더'));assert(out.includes('data-team="0"'));assert(!out.includes('다른 묶음'));
  const head=out.match(/<div class="cs-bh">(.*?)<\/div>/s)[1];
  assert(head.includes('<span class="cs-lv">EX 9</span>'));
  assert(head.includes('알리시아 지원 · '+G.supports.find(s=>String(s.id)===String(team.sup)).name));
  assert(head.includes('평균 점수 18,000 · 클리어율 60%'));assert(!head.includes('상위 점수'));assert(!head.includes('추가 점수'));
  assert(!head.includes('인장'));assert(out.includes('data-fold="gs-basis"><summary>계산 기준 '));
  assert(out.indexOf('cg-top')<out.indexOf('season-actions'));assert(out.indexOf('season-actions')<out.indexOf('data-gs-team'));
  const actions=out.slice(out.indexOf('season-actions'),out.indexOf('data-gs-team'));
  assert(actions.includes('data-gs="follow"'));assert(actions.includes('data-gs="start"'));assert(actions.includes('gs-result-detail'));
  assert.equal((out.match(/class="cg-tab"/g)||[]).length,1);assert(out.includes('aria-label="1팀 합계"'));
  const normal={...team,kind:'normal',step:6};
  assert.deepEqual(Array.from(ui.teamNames([team,normal,normal])),['EX 팀','일반 1팀','일반 2팀']);
  const two=c.guildDailySummary({...done,teams:[team,normal]});assert.equal((two.match(/class="cg-tab"/g)||[]).length,2);
  assert(two.includes('aria-label="2팀 합계"'));assert(!two.includes('attr_undefined'));
  assert.deepEqual(JSON.parse(JSON.stringify(ui.draft(team))),{v:1,slots:team.order.map(key=>({key,grown:false})),leader:'c',brk:{name:'test',level:3}});
  assert.equal(ui.draft({...team,brk:null}).brk,null);assert(ui.draft(team,true).slots.every(s=>s.grown));
  assert(ui.chips(G,normal).includes('<span class="cs-lv">6단계</span>'));
  for(const sup of G.supports){const text=ui.supportLine(G,{...team,sup:sup.id,effectiveSupport:'none'});assert(text.includes(sup.id==='none'?'없음':sup.name));assert(!/한정|파티 전체|해당 직업 없음/.test(text));}
  for(const changed of [true,false])for(const complete of [true,false]){
    const html=ui.result({...done,teams:[{...team,placementChanged:changed,evaluation:{placementComplete:complete}}]},cx);
    assert.equal(html.includes('자리·리더 바꿔 넣음'),changed&&complete);assert(!html.includes('data-recheck'));
  }
  const grown=ui.result(done,cx,true);assert(!grown.includes('cg-top'));assert(!grown.includes('season-actions'));
  const changed=ui.html(done,{...cx,nowMs:day+86400000});assert(changed.includes('날짜 바뀜'));assert(!changed.includes('어제 판'));
  assert(!ui.html({phase:'idle'},{...cx,hasInfo:false}).includes('data-gs="start"'));
  const capped=ui.html({phase:'idle'},{...cx,plan:{withinCap:false,reductions:[],warnings:[]}});assert(capped.includes('data-gs="start" disabled'));assert(capped.includes('상한을 넘음'));
  const run=ui.html({phase:'run'},cx);assert(run.includes('data-gs="partial">중단'));assert(!run.includes('role="progressbar"'));assert(!run.includes('gs-stages'));assert(run.includes('gs-step'));assert(!run.includes('data-gs="cancel"'));
  const els=Object.fromEntries(['[data-gs="partial"]','[data-k="gs-step"]','[data-k="gs-eta"]'].map(k=>[k,{}]));
  ui.progressPaint({querySelector:k=>els[k]},{stopRequested:true,plan:{stages:[{name:'정밀',jobs:1,p:1}]},stageIndex:0,done:1,total:2});
  assert(els['[data-gs="partial"]'].disabled);assert.equal(els['[data-k="gs-step"]'].textContent,'1/1단계 · ');assert.equal(els['[data-k="gs-eta"]'].textContent,'남은 시간 계산 중');
  assert.equal(JSON.stringify(done),before,'rendering preserves every result value');
}
contracts(UI);
const source=fs.readFileSync(require.resolve('../guild_daily_ui'),'utf8');
for(const [from,to] of [["leader:t.leaderKey||t.order[0]","leader:t.order[0]"],["st.partial?Result.warning('중단함 · 여기까지 찾은 결과')","false?Result.warning('중단함 · 여기까지 찾은 결과')"],["st.seals.remaining>0","true"],["&&!stale&&!changed",""],["Result.scoreLine(supportLine(G,t))","''"],["t.evaluation?.placementComplete&&t.placementChanged","false"]]){
  assert(source.includes(from));const context={module:{exports:{}},require:require('node:module').createRequire(require.resolve('../guild_daily_ui'))};vm.runInNewContext(source.replace(from,to),context);assert.throws(()=>contracts(context.module.exports));
}
assert.throws(()=>contracts(UI,page.replace("sumKey:'gs-score'","sumKey:'wrong'")));
for(const k of ['guildPlan','guildFollow','guildClosed','guildDone','guildShort','guildPartial','guildReset'])assert(Ux.GWEN_SAY[k].every(s=>/[가-힣]/.test(s)&&!s.includes('???')));
assert.equal(require('../data/guild_defaults.json').search.preset,'daily');
console.log('PASS daily UI: cosmo summary/actions/teams, seals, support names, stages, source data; 7 mutations');
