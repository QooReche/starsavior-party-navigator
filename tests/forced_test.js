// node tests/forced_test.js
// 강제 탐색(후보 전체 훑기) 연출 — 그웬 길(gwen_lane.js FORCED·forcedSync). 진행 칸·판정은 tests/fullscreen_test.js.
//  훑기 진입: body.is-forced + 폐허 장면 + assets/forced/ 그림을 그때 처음 받음 + 걷기 꺼짐
//  끝(found → ''): 클래스·장면이 걷히고 다시 걸음.  멈춤: 바로 원래대로.  쉬운 스테이지: 아무것도 안 바뀜(그림도 안 받음).
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const harness=require('./helpers/gwen_dom');
const ROOT=path.join(__dirname,'..'),read=p=>fs.readFileSync(path.join(ROOT,p),'utf8').replace(/\r\n/g,'\n');
const lane=read('gwen_lane.js'),policy=read('gwen_policy.js'),ux=read('ux_ui.js'),html=read('party_template.html'),css=read('forced.css');
const section=(s,a,b)=>s.slice(s.indexOf(a),s.indexOf(b,s.indexOf(a)));
function setup(code,{missing=false}={}){
  const h=harness();h.load(policy);h.load(ux);
  // 그림 요청 기록(+ 폴더가 없을 때 = decode 실패)
  h.loads=[];const Base=h.c.Image;
  h.c.Image=class extends Base{set src(v){this._src=v;h.loads.push(v);}get src(){return this._src;}decode(){return missing&&/assets\/forced\//.test(this._src)?Promise.reject(Error('404')):super.decode();}};
  h.load(code);
  const {c}=h;h.host=h.add('reco-gwen-stage');h.add('mi-panel').hidden=true;
  for(const mode of ['direct','reco'])for(const part of ['board','result']){const e=h.add(mode+'-'+part+'-slot',mode==='reco'?h.host:h.doc.body);e.dataset.gwenSlot=mode+'-'+part;}
  c.$=id=>h.doc.getElementById(id);c.DIRECT={mode:'reco'};
  h.load(html.match(/const DIRECT_GWEN=GwenStage.mount.*\n/)[0]+html.match(/const RECO_GWEN=GwenStage.mount.*\n/)[0]);
  c.contents=[{key:'op'}];h.add('content').value=0;
  h.load(section(html,'function guildGwenMode()','function simProgress('));
  c.GwenStage.activate('reco');
  h.state=()=>c.GwenLane.mount().state;h.board=()=>c.$('reco-board-lane');h.forced=()=>h.doc.body.classList.contains('is-forced');
  h.forcedLoads=()=>h.loads.filter(u=>u.includes('assets/forced/'));
  // 진행률을 올리며 ms 동안 흘려보냄 → 그동안 한 번이라도 걸었는가
  h.walk=async(alert,step,from,ms=4000)=>{let moved=false;const x0=h.state().x;
    for(let t=0;t<ms;t+=200){c.recoGwenShow(true,Math.min(1,from+t/ms*.5),null,step,alert);await h.tick(200);moved=moved||h.state().moving||Math.abs(h.state().x-x0)>.5;}return moved;};
  return h;
}
async function scenario(code=lane){
  // 쉬운 스테이지(경보 값 없음): 평소처럼 걷고, 클래스·장면·그림 요청이 없음
  let h=setup(code);
  assert.equal(await h.walk('','s1',.1),true,'평소: 진행률을 따라 걸음');
  assert.equal(h.forced(),false);assert(!h.board().dataset.alert);assert.equal(h.board().querySelector('.fx-scene'),null);
  assert.deepEqual(h.forcedLoads(),[],'쉬운 스테이지: 연출 그림을 받지 않음');
  // 훑기 진입
  const before=h.loads.length;
  h.c.recoGwenShow(true,.2,null,'s2','scan');
  assert.equal(h.forced(),true,'훑기 진입: body.is-forced');assert.equal(h.board().dataset.alert,'scan');
  assert.equal(h.state().moving,false,'훑기 진입 순간 걷기 멈춤');
  const scene=h.board().querySelector('.fx-scene');assert(scene,'폐허 장면이 깔림');
  assert.deepEqual(scene.children.map(e=>e.className),['fx-bg','fx-glow','fx-gwen','fx-fog','fx-fog','fx-ash','fx-ember','fx-noise']);
  const want=['scene.webp','gwen_back.webp','gwen_idcard.webp'].map(f=>'http://test/assets/forced/'+f);
  assert.deepEqual(h.forcedLoads(),want,'훑기 진입 때 장면 그림(넓은 배경·뒷모습·신분증 사진)만 받음');assert(h.loads.length>before);
  await h.flush();assert.equal(h.doc.body.dataset.forcedArt,'ready','다 받으면 그림으로 바꿈');
  assert.equal(await h.walk('scan','s2',.2,12000),false,'훑는 동안은 걷지 않음(진행률이 올라도)');
  assert.equal(h.board().querySelectorAll('.fx-scene').length,1,'장면은 한 번만 깖');
  assert(!/^\[/.test(h.doc.querySelector('.gwen-lane-speech').textContent),'시스템 메시지는 길의 말풍선이 아니라 진행 칸 기록 줄에만');
  // 훑기 끝 → found: 클래스는 바로 빠지고 장면은 걷히는 중, 다시 걸음
  h.c.recoGwenShow(true,0,null,'s3','found');
  assert.equal(h.forced(),false,'훑기가 끝나면 is-forced 제거');assert.equal(h.board().dataset.alert,'found');assert(h.board().querySelector('.fx-scene'));
  assert.equal(await h.walk('found','s3',0),true,'끝나면 다시 걸음');
  h.c.recoGwenShow(true,.6,null,'s3','');
  assert(!h.board().dataset.alert);assert.equal(h.board().querySelector('.fx-scene'),null,'원래 길로 돌아옴');
  // 다시 들어와도 그림을 또 받지 않음 · 중간에 멈추면(결과·대기) 바로 원래대로
  const n=h.forcedLoads().length;h.c.recoGwenShow(true,.1,null,'s4','scan');assert.equal(h.forced(),true);assert.equal(h.forcedLoads().length,n);
  h.c.recoGwenShow(false);
  assert.equal(h.forced(),false,'멈추면 is-forced 제거');assert(!h.board().dataset.alert);assert.equal(h.doc.querySelector('.fx-scene'),null);
  // 직접 편성 길도 같은 함수: 두 길 중 하나라도 훑는 중이면 켜짐, 무대를 없애면 꺼짐
  h.load("DIRECT_GWEN.update({mode:'direct',phase:'work',bundleRunning:true,alert:'scan',progress:.1,count:4})");
  assert.equal(h.forced(),true);assert(h.c.$('direct-board-lane').querySelector('.fx-scene'));
  h.c.GwenStage.destroy('direct');assert.equal(h.forced(),false,'무대를 없애면 꺼짐');
  // 그림 폴더가 없을 때: 상태·장면은 그대로 켜지고 그림 표시(data-forced-art)만 안 붙음 → CSS 바탕·색조로 보임
  h=setup(code,{missing:true});h.c.recoGwenShow(true,.2,null,'s','scan');await h.flush();
  assert.equal(h.forced(),true);assert(h.board().querySelector('.fx-scene'));assert.equal(h.doc.body.dataset.forcedArt,undefined);
}
(async()=>{
  await scenario();
  // 그림·스타일이 서로 맞는가
  const G=require('../gwen_lane');
  // 오염 SD 그웬은 없앴음(그웬은 화면에 한 곳): 그림·경로·스타일이 남지 않고, 폴더의 파일 = 화면이 쓰는 목록 = 생성 도구가 만드는 목록
  assert(!fs.existsSync(path.join(ROOT,'assets/forced/gwen'))&&!('arts' in G.FORCED)&&!/fx-avatar|fx-eye|forced\/gwen\//.test(css+html+lane),'오염 그웬 흔적 없음');
  assert.deepEqual(fs.readdirSync(path.join(ROOT,'assets/forced')).sort(),G.FORCED.scene.slice().sort(),'폴더에 안 쓰는 그림 없음');
  const tool=read('tools/build_forced_art.py');for(const f of G.FORCED.scene)assert(tool.includes("'"+f+"'"),f+': 생성 도구가 만듦');
  assert.deepEqual(Object.keys(G.forcedLine(1,2)).sort(),['i','text'],'기록 줄은 글만');
  let total=0;for(const f of G.FORCED.scene){const size=fs.statSync(path.join(ROOT,'assets/forced',f)).size;total+=size;assert(css.includes('assets/forced/'+f),f+': forced.css 가 씀');}
  assert(total<260000,'장면 그림 합계 용량');
  for(const cls of G.FORCED.layers.match(/fx-[a-z]+/g))assert(css.includes('.fx-scene .'+cls),cls);
  assert(!/backdrop-filter|blur\(/.test(css),'무거운 필터 없음');assert(!/prefers-reduced-motion/.test(css));
  // 스위치·설정 없이 상태 하나로만
  assert(!/CFG|localStorage|location\.search/.test(section(lane,'// --- 강제 탐색','// --- 무대 등록')));
  // 일부러 깨뜨려 보기: 고친 줄을 되돌리면 위 시나리오가 실패해야 함
  for(const [name,from,to] of [
    ['훑는 중에도 걸음',"current.phase!=='work'||current.alert==='scan'||!visible()","current.phase!=='work'||!visible()"],
    ['is-forced 안 붙음',"doc.body.classList.toggle('is-forced',forcedOn.size>0);",''],
    ['끝나도 is-forced 가 남음',"if(alert==='scan')forcedOn.add(mode);else forcedOn.delete(mode);","if(alert)forcedOn.add(mode);"],
    ['장면을 안 치움',"if(!alert){scene?.remove();return;}","if(!alert)return;"],
    ['평소에도 그림을 받음',"    forcedLoad(doc);\n  }","  }\n  if(root.document)forcedLoad(root.document);"],
    ['그림 표시가 안 붙음',"doc.body.dataset.forcedArt='ready';",''],
    ['말풍선이 그대로 나옴',"e.speech&&e.kind!=='rift'&&","e.speech&&"],
  ]){assert(lane.includes(from),name);await assert.rejects(scenario(lane.replace(from,to)),{code:'ERR_ASSERTION'},'깨뜨려도 통과함: '+name);}
  console.log('PASS forced: 훑기 진입(is-forced·폐허 장면·장면 그림·걷기 꺼짐), 끝·멈춤 시 원래대로, 쉬운 스테이지 변화 없음, 폴더 없음 폴백, 그림·스타일 대응; 깨뜨리기 7건');
})().catch(e=>{console.error(e);process.exitCode=1;});
