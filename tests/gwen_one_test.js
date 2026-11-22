// node tests/gwen_one_test.js
// 규칙(docs/gwen_stage.md «부품 계약»): 그웬은 화면에 한 곳에만 나온다.
//  세는 그림 = SD 배우·반신·등신대(모두 같은 배우 노드 [data-gwen=lane]) + 강제 탐색의 뒷모습(.fx-gwen) + «관리 실패» 신분증 사진.
//  여섯 무대(reco·direct·cdirect·cosmoSearch·guildSearch·home)의 대기→진행→결과, 강제 탐색 중·끝(found)·결과(루트 확보/관리 실패)에서 1개 이하.
//  보이고 안 보이고는 실제 DOM 상태 + forced.css 의 숨김 규칙으로 정함 — 규칙 줄을 지우면(일부러 깨뜨리기) 둘이 되어 실패해야 함.
//  세지 않는 것: «그웬의 메모» 이름표의 16px 얼굴 아이콘(글 머리표), 무대 밖 안내 그림(첫 안내·불러오기 서랍 — tests/public_ui_test.js 가 «한 번만»을 따로 봄).
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const harness=require('./helpers/gwen_dom');
const ROOT=path.join(__dirname,'..'),read=p=>fs.readFileSync(path.join(ROOT,p),'utf8').replace(/\r\n/g,'\n');
const lane=read('gwen_lane.js'),policy=read('gwen_policy.js'),ux=read('ux_ui.js'),CSS=read('forced.css');
const MODES=['reco','direct','cdirect','cosmoSearch','guildSearch','home'];
// forced.css 의 숨김 규칙(이 줄들이 «한 곳»을 지킴)
const RULES={
  actor:'.gwen-lane[data-alert=scan] :is(.gwen-lane-actor,.gwen-stage-banner){clip-path:inset(50%)}',
  found:'.gwen-lane[data-alert=found] .fx-gwen{display:none}',
  bust:'[data-forced-art] .result-summary:has(.scr-verdict[data-verdict=fail]) [data-gwen-slot=reco-result]{display:none}',
  back:'[data-forced-art] .fx-scene .fx-gwen{',
  idcard:'[data-forced-art] .result-summary:has([data-gwen-slot=reco-result]) .scr-verdict[data-verdict=fail] span::after{content:"";',
};
function figures(h,css){
  const has=k=>css.includes(RULES[k]),art=!!h.doc.body.dataset.forcedArt,out=[];
  const failBox=e=>{const box=e.closest('.result-summary');return !!box&&box.querySelectorAll('.scr-verdict').some(v=>v.dataset.verdict==='fail')&&!!box.querySelector('[data-gwen-slot=reco-result]');};
  for(const a of h.doc.querySelectorAll('[data-gwen=lane]')){
    if(!a.isConnected||a.closest('[hidden]'))continue;
    if(has('actor')&&a.closest('.gwen-lane')?.dataset.alert==='scan')continue;
    if(has('bust')&&art&&failBox(a))continue;
    out.push('배우');}
  for(const g of h.doc.querySelectorAll('.fx-gwen')){const al=g.closest('.gwen-lane')?.dataset.alert;
    if(art&&has('back')&&(al==='scan'||al==='found'&&!has('found')))out.push('뒷모습');}
  for(const v of h.doc.querySelectorAll('.scr-verdict'))if(v.dataset.verdict==='fail'&&art&&has('idcard')&&failBox(v))out.push('신분증 사진');
  return out;
}
async function scenario(css=CSS,code=lane){
  const h=harness();h.load(policy);h.load(ux);h.load(code);
  const {c}=h,G=c.GwenStage,one=where=>{const f=figures(h,css);assert(f.length<=1,where+': 그웬이 '+f.length+'곳('+f.join('·')+')');return f;};
  h.add('mi-panel').hidden=true;
  // 결과 요약(추천): 판정 줄과 결과 자리가 한 상자 안(party_template.html 의 .result-summary)
  const summary=h.add('summary');summary.className='result-summary';
  const stage={};
  for(const mode of MODES){for(const part of ['board','result']){const e=h.add(mode+'-'+part+'-slot',mode==='reco'&&part==='result'?summary:h.doc.body);e.dataset.gwenSlot=mode+'-'+part;}
    stage[mode]=G.mount(h.doc,{mode});}
  one('처음');
  // 여섯 무대: 대기 → 진행 → 결과. 무대를 바꿔도 배우는 한 명
  for(const mode of MODES){G.activate(mode);stage[mode].reset();await h.flush();one(mode+' 대기');
    stage[mode].progress(.3,'',{step:mode+'1'});await h.tick(400);assert.deepEqual(one(mode+' 진행'),['배우']);
    stage[mode].done({clear:.8});await h.flush();one(mode+' 결과');
    assert(h.doc.querySelectorAll('[data-gwen=lane]').length<=1,mode+': 배우 노드는 하나');}
  // 강제 탐색(추천·직접 편성 길): 훑는 중 = 뒷모습 한 명(SD 배우 숨김), 끝(found) = 뒷모습이 빠지고 SD 배우, 그 뒤 = SD 배우
  for(const mode of ['reco','direct']){G.activate(mode);const run=(alert,step)=>stage[mode].progress(.2,'',{step,alert});
    run('scan',mode+'s');await h.flush();assert.equal(h.doc.body.dataset.forcedArt,'ready');assert.deepEqual(one(mode+' 훑는 중'),['뒷모습']);
    await h.tick(3000);assert.deepEqual(one(mode+' 훑는 중(시간 지남)'),['뒷모습']);
    run('found',mode+'f');await h.flush();assert.deepEqual(one(mode+' 훑기 끝(정화 중)'),['배우']);
    run('',mode+'f');await h.flush();assert.deepEqual(one(mode+' 예선'),['배우']);
    stage[mode].done({clear:.3});await h.flush();one(mode+' 결과');}
  // 결과의 판정 줄: 루트 확보 = 결과 자리 그웬 그대로, 관리 실패 = 신분증 사진이 그 한 명(결과 자리 그웬 숨김)
  G.activate('reco');stage.reco.done({clear:.3});await h.flush();
  const verdict=h.add('verdict',summary);verdict.className='scr-verdict';
  verdict.dataset.verdict='ok';assert.deepEqual(one('루트 확보'),['배우']);
  verdict.dataset.verdict='fail';assert.deepEqual(one('관리 실패'),['신분증 사진']);
  // 그림 폴더가 없으면(data-forced-art 없음) 사진이 없고 결과 자리 그웬이 그대로
  delete h.doc.body.dataset.forcedArt;assert.deepEqual(one('관리 실패(그림 없음)'),['배우']);
}
(async()=>{
  await scenario();
  for(const [k,rule] of Object.entries(RULES))assert.equal(CSS.split(rule).length,2,'forced.css 규칙 한 번: '+k);
  // 일부러 깨뜨려 보기: 숨김 규칙을 지우면 그웬이 두 곳이 되어 실패해야 함
  for(const k of ['actor','found','bust'])await assert.rejects(scenario(CSS.replace(RULES[k],'')),/그웬이 2곳/,'깨뜨려도 통과함: '+k);
  console.log('PASS 그웬은 한 곳: 여섯 무대 대기·진행·결과, 강제 탐색 중·끝·예선, 판정(루트 확보·관리 실패·그림 없음); 깨뜨리기 3건');
})().catch(e=>{console.error(e);process.exitCode=1;});
