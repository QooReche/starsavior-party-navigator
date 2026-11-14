// 「클리어 추천 육성」을 모든 콘텐츠로(11/14): 스테이지형 8개(작전·작전 어려움·일일·장비 탐사·큐브·플래시 포인트·성간 회랑·격전 의뢰)는 같은 탐색을 쓰고,
// 판정은 그 콘텐츠의 목표 지표(3별 목표면 N턴 내 클리어율 t60, 아니면 클리어율)로 한다. 켰는데 조용히 사라지는 경로가 없어야 한다.
//  ① 더 나은가(growthBetter): 목표 지표가 올라야. t60 동률이면 클리어율이 오른 경우만, 진척도·처치 턴만 나아진 것은 아님
//  ② 본선 멈춤(growthStageSearch)·추천 본선 「더 보기」(simBar·goalVal): 목표 지표 50% 경계
//  ③ 고정 육성(플래시 포인트 = Lv200·공명 10 고정): «올릴 항목»에 레벨·공명이 없다
//  ④ 목표 전환(3별 ↔ 클리어만): 문구·탭·예선 캐시 키
//  ⑤ 재점화(작전·작전 어려움)만 재점화 풀을 후보에 더한다
//  ⑥ 조용히 사라지는 경로 0: 8개 콘텐츠 × (대기 사유·탐색 중·오류·더 나음·없음·계산 못 함) 모두 안내가 남는다
//  ⑦ 오토 기준만(수동 모드 제거): 옛 결과에 수동 값(man)이 붙어 있어도 쓰지 않는다
// 끝에서 고친 코드를 일부러 되돌려(결함 주입) 이 시험이 실패하는지 확인한다. 실행: node tests/growth_all_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),S=require('../myinfo_stats'),U=require('../ux_ui');
const growth=require('../data/growth.json'),grades=require('../data/archive_grades.json');
const view={...require('../data/myinfo_view.json'),itemSlots:require('../data/myinfo_slots.json')};
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8'),ui=fs.readFileSync(require.resolve('../growth_ui.js'),'utf8'),ux=fs.readFileSync(require.resolve('../ux_ui.js'),'utf8');
const cut=(s,a,b)=>{const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i,'구간 없음: '+a);return s.slice(i,j)};
const line=(s,start)=>{const m=s.match(new RegExp('^'+start.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'.*$','m'));assert(m,'줄 없음: '+start);return m[0]};
const STAGE=['op','oph','daily','equip','cube','rush','clo','clash'],STAR=['equip','clash'];
const SRC={ui,html,ux};

// growth_ui.js 전체를 가짜 화면에 올린다. o = {kind, goal: 3별 목표 켬, party: 결과 화면이 떠 있는가, req, mi: 내 정보 기준인가, stageName}
function page(src,o={}){
 const out={hidden:false,children:[],append(el){if(!this.children.includes(el))this.children.push(el)}};
 const mk=()=>({dataset:{},innerHTML:'',id:'',className:'',querySelector:()=>null,addEventListener(){},nextElementSibling:null,
  remove(){out.children=out.children.filter(x=>x!==this)}});
 const party={nextElementSibling:null,after(el){this.nextElementSibling=el;out.append(el)}};
 const c={key:o.kind||'op',name:'콘텐츠'},st={tab:'tab',name:o.stageName||'stage',rp:1000};
 const started=[];
 const ctx=vm.createContext({console,Object,Math,JSON,Set,Map,Number,Error,Promise,
  REQ:o.req!==false,MODE:o.mode||'auto',MI:{info:{},growth:{assumed:{version:'v'}},hash:'h'},SIMQ:{busy:null,err:'',n:100,seed:1},
  contents:[c],cur:[st],D:{guild:{steps:[{ex:true,step:10}]},archiveGrades:{}},LASTQ:{},PICK:{},BYKEY:{},R:[],
  $:id=>id==='growth-result'?out.children.find(e=>e.id==='growth-result')||null:id==='out'?out:id==='growth-priority'?null:{value:0,hidden:false},
  document:{createElement:mk,getElementById:id=>id==='assume-growth'?{checked:o.enabled!==false}:null,
   querySelector:s=>s.startsWith('#out > [data-party')&&o.party!==false?party:null,querySelectorAll:()=>[]},
  seasonBlocked:()=>!!o.blocked,miMode:()=>o.mi!==false,simAutoOn:()=>o.auto!==false,starOf:k=>o.goal&&STAR.includes(k)?60:0,
  esc:String,miNum:n=>String(Math.round(n)),simSig:()=>'sig',
  MyInfoReco:{OVERWRITE_VERSION:'o',THRESHOLD_POLICY:{},profile:()=>({results:{},units:{}})},
  Ux:{createResultTabs:()=>({update(){},reset(){}}),resultTabState:x=>x,chip:v=>`<i data-chip="${v}"></i>`,help:()=>'',signed:v=>String(v)},
  setTimeout:fn=>{fn();return 0},clearTimeout(){}});
 vm.runInContext(src.ui,ctx);
 ctx.growthRankPaint=()=>{};ctx.growthSig=()=>'sig';
 const el=()=>out.children.find(e=>e.id==='growth-result')||null;
 return {ctx,c,st,el,out,started,G:vm.runInContext('GROW',ctx),ev:s=>vm.runInContext(s,ctx),
  text:()=>{const e=el();return e?e.innerHTML.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim():''}};
}
const snapshot=fields=>({changes:{a:{changedFields:fields}},errors:[],profile:{results:{}}});

// ① 더 나은가
function better(src){
 const h=page(src),B=(k,b,r)=>h.ctx.growthBetter(k,b,r);
 for(const k of STAGE){
  assert(B(k,{clear:.4},{clear:.8}),k+' 클리어율 오름');assert(!B(k,{clear:.8},{clear:.8}),k+' 동률');assert(!B(k,{clear:.8},{clear:.4}),k+' 내림');
  assert(!B(k,{clear:.5,prog:.6,ttk:30},{clear:.5,prog:.9,ttk:10}),k+' 진척도·처치 턴만 나아진 것은 «더 잘 깸»이 아님');
  assert(!B(k,{clear:0,prog:.2},{clear:0,prog:.9}),k+' 0% 끼리 진척도만');
  assert(B(k,null,{clear:.1}),k+' 지금 결과가 없으면 0 으로 봄');assert(!B(k,{clear:.3},null),k+' 결과 없음');
 }
 for(const k of STAR){
  assert(B(k,{t60:.2,clear:.9},{t60:.5,clear:.9}),'N턴 내 확률 오름');
  assert(B(k,{t60:.2,clear:.9},{t60:.5,clear:.8}),'목표(N턴 내)가 오르면 클리어율이 조금 내려도 더 나음');
  assert(!B(k,{t60:.4,clear:.9},{t60:.4,clear:.9}),'t60 동률');
  assert(!B(k,{t60:.4,clear:.9},{t60:.4,clear:.7}),'t60 동률·클리어율 하락');
  assert(B(k,{t60:0,clear:.03},{t60:0,clear:.6}),'t60 동률이면 클리어율이 오른 경우만 인정');
  assert(!B(k,{t60:.4,clear:.9,prog:.9,ttk:40},{t60:.4,clear:.9,prog:1,ttk:20}),'t60·클리어율 동률, 처치 턴만');
  assert(!B(k,{t60:.6,clear:.6},{t60:.5,clear:1}),'t60 하락은 클리어율이 올라도 아님');
 }
 for(const [k,f] of [['guild','score'],['cosmo','sum']]){assert(B(k,{[f]:1},{[f]:2}));assert(!B(k,{[f]:2},{[f]:2}));assert(!B(k,{clear:0},{clear:1}),'시즌 콘텐츠는 점수로만');}
 // ⑦ 오토 기준만: 수동 값으로 바꾸는 함수가 없다
 assert.equal(typeof h.ctx.growthMetric,'undefined');assert(!/\bMODE\b|\.man\b/.test(src.ui),'growth_ui.js 에 수동 모드 흔적');
 assert.equal(h.ctx.growthGoal({clear:.9,t60:.2}),.2);assert.equal(h.ctx.growthGoal({clear:.9,t60:null}),.9);assert.equal(h.ctx.growthGoal(null),null);
}

// ②-a 육성 본선 멈춤: 3팀씩, 최선의 목표 지표가 50% 이상이면 멈춤. ⑤ 재점화 풀
async function stop(src){
 const P={plan:cut(src.html,'const SCR_ROUNDS=','const scrKey='),cmp:cut(src.html,'const scrCmp=','// 예선 상태 sc'),
  goal:cut(src.ui,'function growthStageKind(','function growthJob'),search:cut(src.ui,'async function growthStageSearch','async function growthStart')};
 const run=async(o)=>{const calls=[],teams=Array.from({length:o.teams||12},(_,i)=>({keys:['a','b','c','t'+i],v:i}));
  const ctx=vm.createContext({console,Object,Math,JSON,Set,Map,Infinity,Error,SIMQ:{seed:1,n:100,LOAD_MS:1000},GROW:{id:1},MODE:'auto',
   CFG:{restrict:{},defPenByContent:{},weights:{defenderPenalty:0}},R:(o.roster||['u0','u1','u2','u3']).map(k=>({key:k,el:'x'})),EXCL:new Set(),
   score:()=>[1,{}],rankAll:x=>x,quickIn:()=>o.noQuick?null:{},quickRank:()=>teams,rkOf:k=>['op','oph'].includes(k)?o.rk||0:0,starOf:()=>0,
   rkQuickTop:(c,st,all,n)=>{calls.push({rkPool:n,kind:c.key});return []},growthJob:(t,k)=>({id:k,t}),simTeamLimit:()=>1000,GrowthGuide:{finalCost:n=>n},Date:{now:()=>1000},
   growthEvaluate:async(jobs,n,seed,c,st,id,deadline,env)=>{calls.push({keys:Array.from(jobs,j=>j.id),final:!!env.final});
    return Object.fromEntries(jobs.map(j=>[j.id,env.final?o.final(j.id):{clear:.5,prog:.5,ttk:20,raw:'[]'}]))}});
  for(const s of [P.plan,P.cmp,P.goal,P.search])vm.runInContext(s,ctx);
  const profile={results:Object.fromEntries(ctx.R.map(s=>[s.key,{}]))};
  const r=await vm.runInContext('growthStageSearch',ctx)({key:o.kind||'equip',name:'x'},{tab:'a',name:'b'},profile,1);
  return {r,finals:calls.filter(c=>c.final).length,calls};};
 // 클리어율은 90% 여도 60턴 내 확률이 50% 미만이면 다음 3팀을 더 본다(3별 목표)
 assert.equal((await run({final:()=>({clear:.9,t60:.4999,prog:1})})).finals,3,'t60 49.99% — 9팀까지');
 assert.equal((await run({final:()=>({clear:.9,t60:.5,prog:1})})).finals,1,'t60 50% — 멈춤');
 assert.equal((await run({final:()=>({clear:.2,t60:.5,prog:1})})).finals,1);
 // 클리어만(t60 없음)이면 클리어율 50% 경계
 assert.equal((await run({kind:'daily',final:()=>({clear:.4999,t60:null,prog:1})})).finals,3);
 assert.equal((await run({kind:'daily',final:()=>({clear:.5,t60:null,prog:1})})).finals,1);
 // 최선은 예선 순위 규칙(목표 지표 먼저)으로 고른다
 const pick=await run({final:k=>k.endsWith('t0')?{clear:1,t60:.1,prog:1}:{clear:.6,t60:.3,prog:1}});
 assert.equal(pick.r.best.t60,.3,'클리어율이 높아도 t60 이 낮으면 최선이 아님');
 // 계산하지 못하는 경우는 이유를 남긴다(던지거나 조용히 끝내지 않음)
 assert.equal((await run({roster:['u0','u1','u2'],final:()=>({clear:1})})).r.reason,'few');
 assert.equal((await run({noQuick:true,final:()=>({clear:1})}).catch(e=>({r:{reason:'던짐: '+e.message}}))).r.reason,'quick');
 // ⑤ 재점화 풀은 작전·작전 어려움에서 재점화를 켰을 때만
 for(const kind of STAGE){const x=await run({kind,rk:3,final:()=>({clear:1,prog:1})}),pool=x.calls.filter(c=>c.rkPool);
  assert.equal(pool.length,['op','oph'].includes(kind)?1:0,kind+' 재점화 풀');if(pool.length)assert.equal(pool[0].kind,kind);}
 assert.equal((await run({kind:'oph',rk:0,final:()=>({clear:1})})).calls.filter(c=>c.rkPool).length,0);
}

// ②-b 추천 본선: 보여 준 팀이 모두 목표 지표 50% 미만이면 「더 보기」(다음 3팀). ④ 예선 캐시 키
function mainStop(src){
 const mk=(mode,res)=>{const ctx=vm.createContext({MODE:mode,SIMQ:{res,n:100,busy:null,err:''},simSig:(st,t)=>t.k,esc:String,simEtaText:()=>''});
  for(const s of [line(src.html,'const goalVal='),cut(src.html,'function simBar(','function simInvalidate(')])vm.runInContext(s,ctx);return ctx};
 const rows=[{k:'a'},{k:'b'},{k:'c'}],more=(mode,r)=>/data-more/.test(mk(mode,{a:r,b:r,c:r}).simBar(1,rows,{},true));
 assert(more('auto',{clear:.9,t60:.4,n:100}),'클리어율 90% 여도 60턴 내 40% 면 더 본다');
 assert(!more('auto',{clear:.9,t60:.5,n:100}));assert(!more('auto',{clear:.5,t60:null,n:100}));assert(more('auto',{clear:.4999,t60:null,n:100}));
 assert(!more('manual',{clear:.9,t60:.9,n:100,man:{c:.1,t60:.1}}),'옛 수동 값(man)·MODE 는 보지 않음');
 const sg=vm.runInContext('goalVal',mk('auto',{}));assert.equal(sg({clear:.9,t60:.4}),.4);assert.equal(sg({clear:.9}),.9);assert.equal(sg(undefined),null);
 // ④ 목표를 바꾸면 예선 캐시를 다시 쓴다
 const key=goal=>{const ctx=vm.createContext({JSON,contents:[{key:'equip'}],$:()=>({value:0}),rkOf:()=>0,miMode:()=>false,MI:{},SCROWN:'',MM:'',starOf:()=>goal});
  vm.runInContext(line(src.html,'const scrKey='),ctx);return vm.runInContext('scrKey({tab:"t",name:"n"},1)',ctx)};
 assert.notEqual(key(60),key(0),'3별 목표와 클리어만의 예선 결과를 섞지 않음');assert.equal(key(60),key(60));
}

// ③ 고정 육성: 플래시 포인트(Lv200·공명 10 고정)는 레벨·공명을 올릴 항목에 넣지 않는다. 스테이지형 8개 모두 능력치 규칙이 있다
function fixed(){
 for(const k of STAGE)assert(S.rule_for_content(k),k+' 능력치 규칙 없음 — 육성 계정을 만들 수 없음');
 assert.equal(S.rule_for_content('rush'),'fixed200');for(const k of STAGE.filter(k=>k!=='rush'))assert.equal(S.rule_for_content(k),'normal');
 const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
 const info=structuredClone(require('./fixtures/myinfo_synthetic.json'));
 for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
 info.star_link={level:240,source:[],slots:[]};info.star_link_level=240;
 for(const x of info.units){x.level=80;x.resonance=0;x.equip=[];x.skills={basic:1,special:1,ultimate:1,passive:1};x.gauntlet.journey=[0,0,0,0,0];x.gauntlet.potentials=[];}
 const rush=M.overwrite(info,roster,growth,'rush',{includeMissing:false}),equip=M.overwrite(info,roster,growth,'equip',{includeMissing:false});
 assert.equal(rush.errors.length,0);assert.equal(equip.errors.length,0);assert(Object.keys(rush.changes).length>0);
 for(const a of Object.values(rush.changes)){assert(!a.changedFields.includes('level')&&!a.changedFields.includes('resonance'),'고정 콘텐츠에 레벨·공명');
  assert(a.changedFields.includes('equip')&&a.changedFields.includes('skills'));
  const d=U.member(a,info,growth,'rush',grades,view);assert(d.fields.every(f=>!['level','resonance'].includes(f.field)));assert(d.after>d.before,'올릴 항목이 전투력을 올림');}
 for(const a of Object.values(equip.changes))assert(a.changedFields.includes('level')&&a.changedFields.includes('resonance'),'일반 콘텐츠는 레벨·공명도 올림');
 for(const [key,r] of Object.entries(rush.profile.results))if(rush.changes[key])assert(r.power>M.profile(info,roster,growth,'rush').results[key].power);
}

// ④ 문구·탭: 3별 목표면 «N턴 안에» 기준, 클리어만이면 클리어율 기준
function words(src){
 const grown=snapshot(['skills']),flat=snapshot([]);
 const star=page(src,{kind:'equip',goal:true}).ctx,plain=page(src,{kind:'equip',goal:false}).ctx;
 assert.equal(star.growthGoalTurns('equip'),60);assert.equal(star.growthGoalTurns('clash'),60);assert.equal(star.growthGoalTurns('op'),0);assert.equal(plain.growthGoalTurns('equip'),0);
 assert.equal(star.growthNoneText('equip',{snapshot:grown,baseline:{t60:0,clear:.03},best:{t60:0,clear:.03}}),'추천 기준까지 키워도 60턴 안에 깨는 편성은 찾지 못했어요 (지금 60턴 내 0% · 클리어 3%)');
 assert.equal(star.growthNoneText('equip',{snapshot:grown,baseline:{t60:.4,clear:.9},best:{t60:.4,clear:.9}}),'추천 기준까지 키워도 지금(60턴 내 40%)보다 60턴 안에 잘 깨는 편성은 찾지 못했어요');
 assert.equal(star.growthNoneText('equip',{snapshot:grown,baseline:{t60:1,clear:1},best:{t60:1,clear:1}}),'추가 육성 없이도 60턴 내 클리어율 100%예요');
 assert.equal(star.growthNoneText('equip',{snapshot:grown,baseline:{t60:.2,clear:1},best:{t60:.2,clear:1}}),'추천 기준까지 키워도 지금(60턴 내 20%)보다 60턴 안에 잘 깨는 편성은 찾지 못했어요','클리어율 100% 여도 3별 목표를 못 채웠으면 «100%예요»라 하지 않음');
 assert.match(star.growthNoneHint('equip',{snapshot:grown,baseline:{t60:0,clear:.5},best:{t60:0,clear:.5}}).flat().join('|'),/클리어는 되지만 60턴 안에.*클리어만/);
 assert.match(star.growthNoneHint('equip',{snapshot:grown,baseline:{t60:0,clear:0},best:{t60:0,clear:0}}).flat().join('|'),/아직 어려운 스테이지/);
 assert.equal(star.growthNoneHint('equip',{snapshot:grown,baseline:{t60:1,clear:1},best:{t60:1,clear:1}}).length,0);
 // 클리어만: 종전 문구 그대로
 assert.equal(plain.growthNoneText('equip',{snapshot:grown,baseline:{clear:0,t60:null},best:{clear:0,t60:null}}),'추천 기준까지 키워도 이 스테이지는 모의 전투에서 깨지 못했어요 (지금 0%)');
 assert.equal(plain.growthNoneText('equip',{snapshot:grown,baseline:{clear:.4,t60:null},best:{clear:.4,t60:null}}),'추천 기준까지 키워도 지금(40%)보다 잘 깨는 편성은 찾지 못했어요');
 assert.equal(plain.growthNoneText('daily',{snapshot:flat,baseline:{clear:.4}}),'이미 추천 기준까지 다 키워서 더 올릴 항목이 없어요');
 for(const k of STAGE)assert.equal(plain.growthNoneText(k,{snapshot:grown,baseline:{clear:1}}),'추가 육성 없이도 모의 전투 클리어율 100%예요',k);
 // 계산하지 못한 이유
 assert.match(plain.growthNoneText('cube',{reason:'few',best:null}),/4명 미만이라 계산하지 못했어요/);assert.match(plain.growthNoneText('cube',{reason:'quick',best:null}),/자료가 없어서 계산하지 못했어요/);
 assert.equal(plain.growthNoneHint('cube',{reason:'few',best:null}).length,0);
 // 탭
 const X=vm.runInNewContext(src.ux+';module.exports',{module:{exports:{}},require:p=>require('../'+p)});
 const base={enabled:true,phase:'done',better:true};
 const t=X.resultTabState({...base,kind:'equip',goalTurns:60,baseline:{t60:.1,clear:.9},best:{t60:.7,clear:.95}});
 assert.equal(t.now,'60턴 내 10%');assert.equal(t.growth,'맞추면 70% ↑');assert(t.recommend,'클리어율 90% 여도 목표(60턴 내)가 50% 미만이면 추천 표시');
 assert(!X.resultTabState({...base,kind:'equip',goalTurns:60,baseline:{t60:.5,clear:.9},best:{t60:.7,clear:.9}}).recommend);
 const p=X.resultTabState({...base,kind:'equip',goalTurns:0,baseline:{t60:null,clear:.3},best:{t60:null,clear:.6}});
 assert.equal(p.now,'클리어 30%');assert.equal(p.growth,'맞추면 60% ↑');assert(p.recommend);
 for(const k of STAGE)assert.equal(X.resultTabState({...base,kind:k,baseline:{clear:.4},best:{clear:.8}}).now,'클리어 40%',k+' 는 확률로 보임');
 for(const k of ['guild','cosmo'])assert.equal(X.resultTabState({...base,kind:k,baseline:{score:100,sum:100},best:{score:200,sum:200}}).now,'점수 100점');
}

// ⑥ 조용히 사라지는 경로 0
function silent(src){
 // 탐색 시작: 스테이지형 8개 모두(내 정보 기준·결과 화면·자동 모의 전투일 때)
 for(const kind of STAGE){const h=page(src,{kind});h.ctx.growthPaint=()=>{};h.ctx.growthStart=c=>h.started.push(c.key);
  h.ctx.growthMaybe(h.c,h.st);assert.deepEqual(h.started,[kind],kind+' 탐색을 시작하지 않음');}
 {const h=page(src,{kind:'equip',req:false});h.ctx.growthStart=c=>h.started.push(c.key);h.ctx.growthMaybe(h.c,h.st);assert.equal(h.started.length,0,'「추천 편성 보기」 전에는 시작 안 함');}
 {const h=page(src,{kind:'equip',enabled:false});h.ctx.growthStart=c=>h.started.push(c.key);h.ctx.growthMaybe(h.c,h.st);h.ctx.growthPaint();assert.equal(h.started.length,0);assert.equal(h.el(),null,'껐으면 아무것도 안 보임');}
 for(const kind of STAGE){
  // 시작하지 못한 사유마다 안내
  for(const [o,want,set] of [[{mi:false},/내 정보 기준으로 추천할 때만/],[{},/모의 전투가 끝나지 않아/,h=>{h.ctx.SIMQ.err='중단함'}],[{auto:false},/모의 전투를 실행하면 이어서/],
   [{},/다른 계산이 끝나면/,h=>{h.ctx.SIMQ.busy=1}],[{},/계산 준비 중/]]){
   const h=page(src,{kind,...o});h.ctx.growthStart=()=>{};if(set)set(h);h.ctx.growthMaybe(h.c,h.st);
   assert.equal(h.el()?.dataset.state,'idle',kind+' 대기 안내 없음');assert.match(h.text(),want,kind);assert.match(h.text(),/클리어 추천 육성/);}
  // 탐색 중·오류(중단 포함)
  {const h=page(src,{kind});h.ev("GROW.phase='running';GROW.msg='후보 확인 1/9';growthPaint()");assert.match(h.text(),/탐색 중.*후보 확인 1\/9/,kind);
   h.ev("GROW.phase='error';GROW.msg='미완료';GROW.errors=['미완료'];growthPaint()");assert.match(h.text(),/계산을 끝내지 못했어요 · 다시 실행해 주세요/,kind);assert.equal(h.el().dataset.state,'error');}
  // 끝남: 더 나음 → 요약, 아님 → 한 줄 안내, 계산 못 함 → 이유
  {const h=page(src,{kind});h.ctx.SIMQ.res={sig:{clear:.2,t60:null}};h.ctx.LASTQ[1]={rows:[{keys:['a','b','c','d']}]};h.G.phase='done';
   h.G.result={best:{clear:.7,t60:null,ttk:20},team:null,snapshot:snapshot(['skills']),kind,runs:1};h.ctx.growthPaint();
   assert.equal(h.el()?.dataset.state,'done',kind);assert.match(h.text(),/지금 ?20% → 맞추면 ?70%/,kind);assert.match(h.text(),/이것만 맞추면 깰 수 있어요/);
   h.G.result.best={clear:.2,t60:null,prog:1,ttk:1};h.ctx.growthPaint();
   assert.equal(h.el()?.dataset.state,'none',kind);assert.match(h.text(),/지금\(20%\)보다 잘 깨는 편성은 찾지 못했어요/,kind+' 진척도·턴만 나아진 결과를 «더 나음»으로 보이면 안 됨');
   Object.assign(h.G.result,{best:null,reason:'few'});h.ctx.growthPaint();assert.match(h.text(),/4명 미만이라 계산하지 못했어요/,kind);
   Object.assign(h.G.result,{best:null,reason:'quick'});h.ctx.growthPaint();assert.match(h.text(),/자료가 없어서 계산하지 못했어요/,kind);}
 }
 // 3별 목표: 큰 숫자는 60턴 내 확률, 클리어율은 아래 줄
 for(const kind of STAR){const h=page(src,{kind,goal:true});h.ctx.SIMQ.res={sig:{clear:.03,t60:0}};h.ctx.LASTQ[1]={rows:[{keys:['a','b','c','d']}]};h.G.phase='done';
  h.G.result={best:{clear:.9,t60:.6,ttk:20},team:null,snapshot:snapshot(['skills']),kind,runs:1};h.ctx.growthPaint();
  assert.match(h.el().innerHTML,/data-goal="60"/);assert.match(h.text(),/60턴 내 · 지금 ?0% → 맞추면 ?60%/);assert.match(h.text(),/클리어 3% → 90%/);assert.match(h.text(),/60턴 안에 깰 확률이 올라가요/);
  assert.match(h.el().innerHTML,/data-chip="0.6"/,'판정 칩도 목표 지표로');
  h.G.result.best={clear:.9,t60:0,ttk:20};h.ctx.growthPaint();assert.equal(h.el().dataset.state,'done','60턴 내 확률은 그대로여도 클리어율이 올랐으면 보임(숫자는 그대로 0% → 0%)');
  assert.match(h.text(),/지금 ?0% → 맞추면 ?0%/);assert.match(h.text(),/클리어 3% → 90%/);
  h.G.result.best={clear:.03,t60:0,ttk:5,prog:1};h.ctx.growthPaint();assert.equal(h.el().dataset.state,'none');assert.match(h.text(),/60턴 안에 깨는 편성은 찾지 못했어요/);}
 // 공략 DB 에 아직 없는 구원자(직업 기본 우선순위로 판단)는 결과 칸에 그 사실을 적는다 — 더 나음·없음 둘 다
 {const h=page(src,{kind:'op'});h.ctx.D.journeyPriority={fallback:{a:'레인저'}};h.ctx.BYKEY.a={name:'새구원자'};
  assert.match(h.ctx.growthArchiveNote(['a','b','a']),/스텔라 아카이브 우선순위: 새구원자 — 공략 DB 미반영 · 직업 기본값/);assert.equal(h.ctx.growthArchiveNote(['b']),'');
  h.ctx.SIMQ.res={sig:{clear:.2,t60:null}};h.ctx.LASTQ[1]={rows:[{keys:['a','b','c','d']}]};h.G.phase='done';
  const snap={...snapshot(['skills']),profile:{results:{},units:{a:{},b:{}}}};
  h.G.result={best:{clear:.2,t60:null},team:null,snapshot:snap,kind:'op',runs:1};h.ctx.growthPaint();
  assert.equal(h.el().dataset.state,'none');assert.match(h.text(),/새구원자 — 공략 DB 미반영 · 직업 기본값/);
  h.ctx.D.journeyPriority={fallback:{}};h.ctx.growthPaint();assert.doesNotMatch(h.text(),/공략 DB 미반영/);}
 // 길방: EX 밖 단계는 이유를 적는다. 기간이 끝난 시즌 콘텐츠·결과 화면이 없을 때는 표시 자체가 없다(«켜짐» 표시도 없는 화면)
 {const h=page(src,{kind:'guild',stageName:'3'});h.ctx.growthStart=()=>{throw Error('시작하면 안 됨')};h.ctx.growthMaybe(h.c,h.st);assert.match(h.text(),/EX 단계에서만 계산해요/);}
 {const h=page(src,{kind:'clash',blocked:true});h.ctx.growthPaint();assert.equal(h.el(),null);}
 {const h=page(src,{kind:'equip',party:false});h.ctx.growthPaint();assert.equal(h.el(),null,'진행 화면·안내 화면에는 육성 칸이 없음(«켜짐» 표시가 진행 화면에 있음)');}
}

async function suite(src=SRC){better(src);await stop(src);mainStop(src);fixed();words(src);silent(src)}
(async()=>{
 await suite();console.log('PASS 육성 전 콘텐츠: 목표 지표 판정·50% 경계·고정 육성·목표 전환·재점화 풀·조용히 사라지는 경로 0·오토 기준만');
 const rep=(s,a,b)=>{assert(s.includes(a),'주입 대상 없음: '+a);return s.replace(a,b)};
 const m=(file,a,b)=>({...SRC,[file]:rep(SRC[file],a,b)});
 const mutants={
  '작전·성간 회랑만 탐색(옛 차단)':m('ui',"if(!miMode()||!growthStageKind(c.key)){growthPaint();return;}","if(!miMode()||!['op','clo'].includes(c.key))return;"),
  '작전·성간 회랑 밖은 칸을 지움(옛 차단)':m('ui',"if(seasonBlocked(c.key)){growthTabs?.reset();el?.remove();return;}","if(seasonBlocked(c.key)||!['op','clo','guild','cosmo'].includes(c.key)){growthTabs?.reset();el?.remove();return;}"),
  '공략 DB 미반영 표시를 안 함':m('ui',"growthArchiveNote(Object.keys(r?.snapshot?.profile?.units||{}))+","''+"),
  '대기 사유를 안 보임':m('ui',"if(!why){el?.remove();return;}","if(true){el?.remove();return;}"),
  '스테이지형 = 작전·성간 회랑':m('ui',"function growthStageKind(kind){return !['guild','cosmo'].includes(kind);}","function growthStageKind(kind){return ['op','clo'].includes(kind);}"),
  '판정을 클리어율로만':m('ui',"function growthGoal(r){return r?(r.t60??r.clear):null;}","function growthGoal(r){return r?r.clear:null;}"),
  '진척도만 나아져도 더 나음':m('ui',"return Number.isFinite(a)&&(a>b||(a===b&&result.t60!=null&&result.clear>(baseline?.clear??0)));}","return Number.isFinite(a)&&(a>b||(a===b&&(result.prog??0)>(baseline?.prog??0)));}"),
  't60 동률이면 클리어율이 내려도 더 나음':m('ui',"result.clear>(baseline?.clear??0)","result.clear>=0"),
  '본선 멈춤을 클리어율로':m('ui',"if(growthGoal(best)>=.5)break;","if(best?.clear>=.5)break;"),
  '본선 멈춤 경계 초과':m('ui',"if(growthGoal(best)>=.5)break;","if(growthGoal(best)>.5)break;"),
  '후보 부족을 이유 없이 끝냄':m('ui',"return {best:null,runs:0,reason:'few'};","return {best:null,runs:0};"),
  '자료 없음을 오류로 던짐':m('ui',"if(!qi)return {best:null,runs:0,reason:'quick'};","if(!qi)throw Error('빠른 계산 자료 없음');"),
  '3별 문구를 클리어율 기준으로':m('ui',"star=prob&&turns>0&&(b?.t60!=null||r?.best?.t60!=null);\n  if(r?.reason==='few')","star=false;\n  if(r?.reason==='few')"),
  '요약 숫자를 클리어율로':m('ui',"→ <small>맞추면</small>${pct(growthGoal(r.best))}</b>","→ <small>맞추면</small>${pct(r.best.clear)}</b>"),
  '추천 본선 멈춤을 클리어율로':m('html',"const goalVal=r=>r?(r.t60??r.clear):null;","const goalVal=r=>r?r.clear:null;"),
  '예선 캐시 키에 목표 없음':m('html',"rkOf(contents[$(\"content\").value].key),starOf(contents[$(\"content\").value].key),","rkOf(contents[$(\"content\").value].key),"),
  '탭을 클리어율로':m('ux',"const goal=r=>goalTurns&&r?.t60!=null?r.t60:r?.clear;","const goal=r=>r?.clear;"),
  '탭: 스테이지형 = 작전·성간 회랑':m('ux',"const probability=kind!=='guild'&&kind!=='cosmo'","const probability=kind==='op'||kind==='clo'")};
 for(const [name,src] of Object.entries(mutants)){let caught=false;try{await suite(src)}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e}
  assert(caught,'결함 주입이 통과해 버림: '+name);console.log('MUTATION caught:',name)}
 console.log('ALL OK growth all contents; '+Object.keys(mutants).length+' mutations');
})().catch(e=>{console.error(e);process.exit(1)});
