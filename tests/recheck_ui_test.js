// node tests/recheck_ui_test.js — 현장 재조사 화면 조각(recheck_ui.js): 진행도·기록 줄·조사·자리 변화·칸 문구(진행 중/바뀜/그대로/되돌림/중단/오류).
// 화면 흐름 전체(진입·단계·끝·그웬 한 곳·길 접힘)는 tests/e2e/test_recheck.py, 그웬 한 곳 규칙은 tests/gwen_one_test.js.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const SRC=fs.readFileSync(path.join(__dirname,'..','recheck_ui.js'),'utf8');
const J=x=>JSON.parse(JSON.stringify(x));   // vm 안에서 만든 값은 원형이 달라 deepEqual 전에 옮김
const load=(src=SRC)=>{const m={exports:{}};vm.runInNewContext(src,{module:m,globalThis:{}});return m.exports;};
function check(U){
  const W=(stage,got,all)=>({state:'work',stage,got,all,teams:2});
  // 진행도: 단계 순서대로 늘고(훑기 0~50%, 1단계 ~80%, 2단계 ~95%, 판정 95%), 끝나면 1
  const seq=[W('enter',0,0),W('screen',0,48),W('screen',24,48),W('screen',48,48),W('check100',4,8),W('check100',8,8),W('final200',3,3),W('fix',0,0)].map(U.progress);
  for(let i=1;i<seq.length;i++)assert(seq[i]>=seq[i-1],'진행도가 줄어듦 '+i+': '+seq);
  assert.equal(seq[0],0);assert(seq.at(-1)<1&&seq.at(-1)>=.9);assert.equal(U.progress({state:'done'}),1);assert.equal(U.progress({state:''}),0);
  // 훑기 «N/24»: 팀 수와 무관하게 24가지 기준
  assert.equal(U.screened(W('screen',24,48)),12);assert.equal(U.screened(W('check100',1,8)),24);
  // 기록 줄은 단계가 바뀔 때와 훑기 절반에서만 바뀜
  const keys=[W('screen',1,48),W('screen',23,48),W('screen',24,48),W('screen',47,48)].map(U.logKey);
  assert.deepEqual(J(keys),['screen','screen','half','half']);assert.equal(U.logKey(W('final200',1,3)),'final200');
  // 조사
  assert.equal(U.josa('힐데','을/를'),'를');assert.equal(U.josa('세레스','을/를'),'를');assert.equal(U.josa('카르멘','을/를'),'을');
  assert.equal(U.josa('전열','로'),'로');assert.equal(U.josa('카르멘','로'),'으로');assert.equal(U.josa('벨','로'),'로');
  // 자리 변화(화면 자리 순서 [후열, 전열, 전열, 후열]): 역할이 바뀐 구원자와 새 리더만
  const rule={order:['h','c','b','s'],lead:'c'},now={order:['c','h','s','b'],lead:'h'};
  assert.deepEqual(J(U.moves(rule,now)),{c:{from:'front',to:'back',lead:false},h:{from:'back',to:'front',lead:true},s:{from:'back',to:'front',lead:false},b:{from:'front',to:'back',lead:false}});
  assert.deepEqual(J(U.moves(rule,{order:['s','b','c','h'],lead:'c'})),{},'전열끼리·후열끼리 바꾼 것은 변화 아님');
  const names={h:'힐데',c:'카르멘',b:'벨',s:'세레스'};
  assert.equal(U.story(rule,now,k=>names[k]),'힐데·세레스를 전열로, 리더를 힐데로 바꿈');
  assert.equal(U.story(rule,{...rule,lead:'b'},k=>names[k]),'리더를 벨로 바꿈');
  // 칸: 진행 중(제목·단계 3칸·막대·기록 줄·확정 단추) → 끝(같은 칸 자리의 기록 줄)
  const work=U.strip(W('screen',24,48));
  for(const t of ['현장 재조사 — 자리·리더 맞추는 중','① 24가지 훑기 <em>12/24</em>','② 유력 3개 정밀 대조','③ 확정','scaleX(0.250)','data-recheck-stop','role="progressbar"'])assert(work.includes(t),'진행 중 칸: '+t);
  assert(!U.strip(W('screen',1,48),{bundle:true}).includes('data-recheck-stop'),'묶음 길은 확정 단추 없음(건너뛰기)');
  const done={state:'done',outcome:'changed',teams:2,deep:true};
  const ch=U.strip(done,{rows:[{label:'1안',from:{clear:.62},to:{clear:.86}},{label:'2안',from:{clear:.84},to:{clear:.9}}],story:'힐데·세레스를 전열로 바꿈'});
  for(const t of ['진형 재정렬','1안 클리어 <em>62% → 86%</em> · 2안 클리어 <em>84% → 90%</em>','유력 3개 200판 확인. 힐데·세레스를 전열로 바꿈','이전 자리로 보기','data-end="changed"'])assert(ch.includes(t),'바뀜: '+t);
  assert(U.strip({...done,deep:false},{}).includes('100판 확인'));
  const same=U.strip({state:'done',outcome:'same',teams:2},{});assert(same.includes('현 진형 유지')&&same.includes('가장 좋음')&&same.includes('2팀 × 24가지'));
  const rev=U.strip({state:'done',outcome:'same',teams:1},{reverted:true});assert(rev.includes('되돌림')&&!rev.includes('가장 좋음'),'되돌림은 «가장 좋음»이라 쓰지 않음');
  for(const [state,text] of [['cancel','재조사 중단 — 규칙 자리 유지'],['error','재조사를 끝내지 못함 — 규칙 자리 유지']]){const h=U.strip({state},{});assert(h.includes(text)&&!h.includes('가장 좋음'),state);}
  // 요약 이전→지금 줄: 얼굴 8개, 리더 표시, 옮긴 얼굴 표시, 수치
  const sw=U.swap(rule,now,k=>k+'.webp',{from:{clear:.62},to:{clear:.86}});
  assert.equal(sw.match(/class="rc-f"/g).length,8);assert.equal(sw.match(/data-lead/g).length,2);assert.equal(sw.match(/data-moved/g).length,4);assert(sw.includes('<s>62%</s> → 86%'));
}
check(load());
// 그림·스타일: assets/recon 은 빌더가 만들고 recheck.css 가 모두 씀, 배경 두 장 150KB 안, 움직임은 transform·opacity 연속(steps·흐림 없음)
{const G=require('../gwen_lane.js'),css=fs.readFileSync(path.join(__dirname,'..','recheck.css'),'utf8'),tool=fs.readFileSync(path.join(__dirname,'..','tools','build_recon_art.py'),'utf8');
 let office=0;for(const f of G.RECHECK_ART.scene){const size=fs.statSync(path.join(__dirname,'..','assets','recon',f)).size;if(f.startsWith('office'))office+=size;
  assert(css.includes('assets/recon/'+f),f+': recheck.css 가 씀');assert(tool.includes(f.replace(/^gwen_(\w+)\.webp$/,"gwen_{pose}.webp"))||tool.includes("'"+f+"'"),f+': 빌더가 만듦');}
 assert(office<=150000,'배경 두 장 합계 '+office);
 assert(!/steps\(|backdrop-filter|blur\(|prefers-reduced-motion/.test(css),'steps·흐림·움직임 줄이기 분기 없음');
 for(const [,name,body] of css.matchAll(/@keyframes ([\w-]+)\{(.*)\}\s*$/gm))for(const [,prop] of body.matchAll(/([a-z-]+):/g))
  assert(['transform','opacity','scale','translate'].includes(prop),name+': '+prop+' 는 합성 속성이 아님');
 for(const cls of G.RECHECK_ART.layers.match(/rc-[a-z]+/g))assert(css.includes('.'+cls),cls+': 스타일 없음');}
// 일부러 깨뜨려 보기
for(const [name,from,to] of [
  ['단계 가중치 뒤바뀜','check100:.5+.3*f,final200:.8+.15*f','check100:.8+.15*f,final200:.5+.3*f'],
  ['기록 줄이 매번 바뀜',"r.stage==='screen'&&r.all&&r.got*2>=r.all?'half'","r.stage==='screen'&&r.all&&r.got%2?'half'"],
  ['받침 무시',"return jong?pair[0]:pair[2];","return pair[2];"],
  ['같은 역할 이동도 변화로 셈','if(from!==to||lead)','if(now.order[i]!==rule.order[i]||lead)'],
  ['되돌림도 «가장 좋음»',"d.reverted?'지금 자리·리더 그대로':","false?'':"],
]){assert(SRC.includes(from),name);assert.throws(()=>check(load(SRC.replace(from,to))),{code:'ERR_ASSERTION'},'깨뜨려도 통과함: '+name);console.log('MUTATION caught:',name);}
console.log('PASS recheck_ui: 진행도·기록 줄·조사·자리 변화·칸 문구(진행/바뀜/그대로/되돌림/중단/오류)·이전→지금 줄; 깨뜨리기 5건');
