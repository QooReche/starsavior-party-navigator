const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function checkNotice(page,file){
 const update=page.match(/<p class="notice update-notice" data-k="update-notice">([\s\S]*?)<\/p>/);
 assert(update,`${file}: distinct update box exists`);
 const text=update[1].replace(/<[^>]*>/g,'').trim();
 assert.match(text,/^📢 11\/19 업데이트 ·/);
 assert([...text].length<=60,`${file}: notice including details stays within 60 characters`);
 assert.match(update[1],/<a href="#update-history"[^>]*>자세히<\/a>/);
 assert.match(page,/<details class="note" id="update-history"><summary>업데이트 내역/);
 const css=page.match(/\.notice\.update-notice\{([^}]+)\}/)?.[1]||'';
 for(const rule of ['background:color-mix','border:1px solid var(--acc)','border-radius:8px'])assert(css.includes(rule),`${file}: ${rule}`);
 assert.match(page,/@media\(min-width:1000px\)\{\.update-notice\{white-space:nowrap\}\}/);
 // Exercise the link's real handler: following an anchor must reveal the folded history.
 const history={open:false},handler=update[1].match(/onclick="([^"]+)"/);
 assert(handler,`${file}: details link opens history`);
 vm.runInNewContext(handler[1],{document:{getElementById:id=>{assert.equal(id,'update-history');return history;}}});
 assert.equal(history.open,true);
}
function checkTone(page,file){
 for(const phrase of ['모의 전투 결과라 실제 플레이와 다를 수 있음','게임이 켜져 있으면 <b>완전히 껐다</b> 다시 켜야 함','사이트가 자동으로 열리며 반영됨'])assert(page.includes(phrase),`${file}: ${phrase}`);
}
function checkGwen(page,file){
 for(const [rel,size] of [['icon',32],['icon',512],['apple-touch-icon',180]]){
  const link=[...page.matchAll(/<link\b[^>]*>/g)].map(m=>m[0]).find(s=>s.includes(`rel="${rel}"`)&&s.includes(`sizes="${size}x${size}"`));
  assert(link?.includes(`href="assets/ui_icons/gwen_favicon_${size}.png"`),`${file}: Gwen ${rel} ${size}`);
 }
 const heading=page.match(/<header class="site-head"><h1>([\s\S]*?)<\/h1>/)?.[1]||'';
 assert.match(heading,/<img class="gwen-head" src="assets\/ui_icons\/gwen_header_72.png" width="36" height="36" alt="" aria-hidden="true"(?: loading="lazy")?>/);
 assert(heading.indexOf('gwen-head')<heading.indexOf('파티 편성 네비게이터'),`${file}: face before title`);
 const start=page.indexOf('function miGuide()');
 const guide=vm.runInNewContext(page.slice(start,page.indexOf('function showReco()',start))+';miGuide()', {Ux:require('../ux_ui')});
 assert.match(guide,/<img class="gwen-guide-art" data-gwen-expression="welcome" data-gwen-art="welcome" data-gwen-static="assets\/ui_icons\/gwen\/welcome.png"[^>]*alt="" aria-hidden="true"(?: loading="lazy")?>/);
 assert.equal((page.match(/data-gwen-static="assets\/ui_icons\/gwen\/welcome.png"/g)||[]).length,1,`${file}: welcome in first guide and import drawer`);
 assert(page.includes('게임 이미지·만화의 권리는 원 권리자에게 있음.'),`${file}: image and comic attribution`);
 // 탐정 사무소 꾸밈: 장식은 alt=""·aria-hidden, 보안 안내 문구는 뜻·위치 그대로.
 assert.match(guide,/^<div class="party guide case-request" data-k="miguide" data-state="needs-info"><img class="case-clip" src="assets\/ui_icons\/office_clip\.svg" width="18" height="30" alt="" aria-hidden="true"><p class="case-tag">사건 의뢰서 · 접수 대기<\/p><h3>내 구원자로 깰 파티 찾기<\/h3>/);
 assert.match(guide,/<p class="account-safe">캡처 파일은 계정 정보가 들어 있으므로 다른 사람에게 공유 금지<\/p>/);
 assert.match(guide,/<p class="mut">내 정보는 이 브라우저에만 저장됨<\/p>/);
 assert.equal((guide.match(/data-gwen-art=/g)||[]).length,1,`${file}: 첫 안내에 그웬은 한 번`);
 const drawer=page.slice(page.indexOf('<aside id="drawer"'),page.indexOf('</aside>'));
 assert.match(drawer,/<div class="mut" style="margin-bottom:10px">내 구원자 정보는 서버 전송 없이 이 브라우저에 저장함\.<\/div>/);
 // 불러오기 창: 그웬 말은 말풍선(장식, 대사는 ux_ui.js 가 채움), 순서 안내는 말풍선 밖에 사이트 문구로 그대로.
 assert.match(drawer,/<div class="gwen-greet"><img class="gwen-welcome" [^>]*alt="" aria-hidden="true" loading="lazy"><div class="gwen-greet-text"><span class="gwen-bubble" data-gwen-say="import" data-tail="left" aria-hidden="true"><\/span><p class="gwen-greet-note mut">아래 5단계를 순서대로 하면 됨<\/p><\/div><\/div>/);
 assert.equal((drawer.match(/class="gwen-bubble"/g)||[]).length,1,`${file}: 불러오기 창 말풍선 한 개`);
 // 말풍선: 그웬 그림마다 한 개, 꼬리는 그림 쪽. 대사는 화면 파일에 직접 쓰지 않고 대사 표에서만 가져옴.
 const Ux=require('../ux_ui'),bubble=Ux.gwenSay('welcome','right');
 assert.match(bubble,/^<span class="gwen-bubble" data-gwen-say="welcome" data-tail="right" aria-hidden="true">[^<]+<\/span>$/);
 assert(guide.includes(bubble+'<img class="gwen-guide-art"'),`${file}: 첫 안내 말풍선은 그림 바로 앞`);
 assert.equal((guide.match(/class="gwen-bubble"/g)||[]).length,1,`${file}: 첫 안내 말풍선 한 개`);
 assert.match(guide,/<p class="account-safe">[^<]+<\/p><div class="gwen-guide-footer"><div><p class="mut">내 정보는 이 브라우저에만 저장됨<\/p>/,`${file}: 보안 안내는 말풍선 밖 기존 자리`);
 for(const lines of Object.values(Ux.GWEN_SAY))for(const line of lines)assert(!page.includes(line),`${file}: 대사는 ux_ui.js 한곳에만: ${line}`);
 assert.equal((drawer.match(/<li>/g)||[]).length,5,`${file}: 불러오기 5단계 유지`);
 const emptyAt=page.indexOf('function miEmpty()'),empty=vm.runInNewContext(page.slice(emptyAt,page.indexOf('function miGuide()',emptyAt))+';miEmpty()', {Ux:require('../ux_ui')});
 assert.match(empty,/data-gwen-art="files"/);
 assert(empty.includes(`<span class="gwen-say-lane">${Ux.gwenSay('empty')}</span>`),`${file}: 빈 명단 말풍선`);assert.equal((empty.match(/class="gwen-bubble"/g)||[]).length,1);
 assert.match(empty,/<button type="button" data-mi-empty-open>계정 정보 불러오기<\/button>/);assert.equal((empty.match(/data-gwen-art=/g)||[]).length,1);
 assert(page.includes('if(e.target.closest("button[data-mi-empty-open]")){$("mi-open-import").click();return}'),`${file}: 빈 상태 단추 연결`);
 for(const f of ['office_clip','office_magnifier','office_file','office_board']){const svg=fs.readFileSync(require.resolve('../assets/ui_icons/'+f+'.svg'),'utf8');
  assert(svg.length<=10000,f);assert.doesNotMatch(svg,/<script|<image|href=/,f);}
}
// Check both the editable template and the generated page served to users.
for(const file of ['party_template.html','index.html']){
 const page=fs.readFileSync(require.resolve('../'+file),'utf8');
 checkNotice(page,file);checkTone(page,file);checkGwen(page,file);checkIdle(page,file);
 const uxCss=fs.readFileSync(require.resolve('../ux.css'),'utf8').replace(/\r\n/g,'\n'),checkHelp=(p,f)=>checkHelpOnce(p,uxCss,f);checkHelp(page,file);
 for(const [from,to,check] of [
  ['gwen_favicon_32.png','old_star.svg',checkGwen],
  ['gwen_favicon_180.png','old_touch.png',checkGwen],
  ['gwen_favicon_512.png','old_icon.png',checkGwen],
  ['class="gwen-head"','class="removed-head"',checkGwen],
  ['"welcome","gwen-guide-art"','"welcome","removed-art"',checkGwen],
  ['${Ux.gwenSay("welcome","right")}','',checkGwen],
  ['Ux.gwenSay("welcome","right")','Ux.gwenSay("welcome","left")',checkGwen],
  ['${Ux.gwenWork("screen","empty")}','${Ux.gwenWork("screen")}',checkGwen],
  ['<span class="gwen-bubble" data-gwen-say="import" data-tail="left" aria-hidden="true"></span>','<span class="gwen-bubble" data-gwen-say="import" data-tail="left"></span>',checkGwen],
  ['<span class="gwen-bubble" data-gwen-say="import" data-tail="left" aria-hidden="true"></span>','<span class="gwen-bubble" data-tail="left" aria-hidden="true">단장님의 정보! 내가 받아 갈게</span>',checkGwen],
  ['<p class="gwen-greet-note mut">아래 5단계를 순서대로 하면 됨</p>','',checkGwen],
  ['${waiting?Ux.gwenWork("inspect"):Ux.gwenIdle()}<div id="reco-actions">','${waiting?Ux.gwenWork("inspect"):""}<div id="reco-actions">',checkIdle],
  ['${waiting?Ux.gwenWork("inspect"):Ux.gwenIdle()}<div id="reco-actions">','${Ux.gwenIdle()}${waiting?Ux.gwenWork("inspect"):""}<div id="reco-actions">',checkIdle],
  ['<div class="acts"><button type="button" data-miopen="1">계정 정보 불러오기</button></div><p class="account-safe">','<div class="acts">${Ux.gwenIdle()}<button type="button" data-miopen="1">계정 정보 불러오기</button></div><p class="account-safe">',checkIdle],
  ['.idle button:not(.ux-help){margin-top:8px;font-size:15px;padding:8px 20px}','.idle .x .y button{margin-top:8px;font-size:15px;padding:8px 20px}',checkHelp],
  ['.cands button{padding:2px 10px;font-size:12px}','#out button{padding:2px 10px;font-size:12px}',checkHelp],
  ['<button id="growth-hint" type="button" class="ux-help"','<button type="button" class="ux-help" data-help="중복">ⓘ</button><button id="growth-hint" type="button" class="ux-help"',checkHelp],
  ['게임 이미지·만화의 권리는','게임 이미지의 권리는',checkGwen],
  ['class="notice update-notice"','class="notice"',checkNotice],
  ['자동 대상 클라 기준 교정','자동 대상 클라 기준 교정 및 구원자 열세 명 상세 안내',checkNotice],
  ['background:color-mix','color:color-mix',checkNotice],
  ['border:1px solid var(--acc);border-radius:8px','border:0;border-radius:0',checkNotice],
  ["document.getElementById('update-history').open=true","document.getElementById('update-history').open=false",checkNotice],
  ['모의 전투 결과라 실제 플레이와 다를 수 있음','모의 전투 결과라 실제 플레이와 다를 수 있어요',checkTone],
  ['게임이 켜져 있으면 <b>완전히 껐다</b> 다시 켜야 함','게임이 이미 켜져 있으면 <b>완전히 끄고</b> 다시 켜세요',checkTone],
  ['사이트가 자동으로 열리며 반영됨','사이트가 자동으로 열리며 반영돼요',checkTone]
 ]){assert(page.includes(from));assert.throws(()=>check(page.replace(from,to),file),{code:'ERR_ASSERTION'},`${file}: mutation caught: ${from}`);check(page,file);}
 assert.equal((page.match(/data-k="update-notice"/g)||[]).length,1);
 assert.match(page,/<\/header>\s*<p class="notice update-notice" data-k="update-notice">[^\n]*<\/p>\s*<p class="notice" data-k="notice">모의 전투 결과라 실제 플레이와 다를 수 있음/,`${file}: update directly above the original guidance`);
 assert.match(page,/<summary>업데이트 내역\(11\/21\)<\/summary>11\/21:[^<]+<br>11\/19:[^<]+<br>11\/15:[^<]+<br>11\/12: 신규 구원자 길레/);
 // Keep the copy action and all four instructions together, in both shipped sources.
 const guide=page.match(/<div class="mi-import-guide">([\s\S]*?)<\/ol>\s*<p class="mut mi-import-fallback">([\s\S]*?)<\/p>\s*<\/div>/);
 assert(guide,`${file}: import guide box and fallback exist`);
 assert.match(guide[1],/^\s*<div class="dtools"><button id="mi-copy" type="button">명령 복사<\/button><\/div>\s*<ol>/,`${file}: existing copy button comes first inside box`);
 assert.equal((page.match(/id="mi-copy"/g)||[]).length,1,`${file}: one copy button`);
 const steps=[...guide[1].matchAll(/<li>([\s\S]*?)<\/li>/g)].map(m=>m[1].trim().replace(/\s+/g,' '));
 // Each step: bold one-line title, then detail line(s); the restart warning is its own line in step 4.
 const T=t=>`<b class="mi-step-title">${t}</b>`,D=d=>` <span class="mi-step-do">${d}</span>`;
 assert.deepEqual(steps,[
  T('PowerShell 열기')+D('<span class="mi-keys"><kbd>Windows</kbd>+<kbd>R</kbd></span> → <b>powershell</b> 입력 → <kbd>Enter</kbd>'),
  T('명령 붙여넣기')+D('위쪽 <b>[명령 복사]</b> 단추 클릭')+D('→ PowerShell 창에 붙여넣기')+D('<span class="mi-keys"><kbd>Ctrl</kbd>+<kbd>V</kbd></span> 또는 마우스 오른쪽 클릭 → <kbd>Enter</kbd>'),
  T('관리자 확인')+D('「관리자 확인」 창이 뜨면 <b>[예]</b>'),
  T('게임 로그인')+D('게임에 로그인해 로비 화면까지 들어가기')+D('→ 명령을 붙여넣었던 <b>PowerShell 창</b>으로 돌아와 <kbd>Enter</kbd>')+' <span class="mi-step-do mut">(게임 화면이 아니라 PowerShell 창에서 누름 · 반응 없으면 몇 번 더 눌러도 됨)</span>'+' <span class="mi-import-warning">⚠ 기존에 이미 게임이 켜져 있으면 <b>완전히 껐다</b> 다시 켜야 함</span>',
  T('자동 반영')+D('사이트가 자동으로 열리며 반영됨')
 ],`${file}: five titled steps and separate restart warning`);
 assert.equal(guide[2],'<b class="mi-fallback-title">안 될 때·다른 기기에서</b><span class="mi-step-do">바탕화면 <b>내정보.json</b>을 [파일 선택]으로 올리기</span>');
 // Summary card mirrors the five step titles in the same order.
 const summary=page.match(/<ol class="guide-steps">([\s\S]*?)<\/ol>/);
 assert(summary,`${file}: summary steps exist`);
 assert.deepEqual([...summary[1].matchAll(/<li><b>([^<]+)<\/b>/g)].map(m=>m[1]),['PowerShell 열기','명령 붙여넣기','관리자 확인','게임 로그인','자동 반영'],`${file}: summary matches five steps`);
 // Execute the real renderer through empty -> loaded -> cleared states.
 const nodes=Object.fromEntries(['mi-chip','mi-panel','option-chips','content','rk','mi-open-import','share-mi','share-link','mi-view','mi-clear','mi-panel-clear'].map(id=>[id,{dataset:{},classList:{toggle(){}},closest(){return this;}}]));
 nodes.content.value='op';nodes['mi-panel'].hidden=true;
 const state={MI:{info:null},EXCL:new Set(),$:id=>nodes[id],document:{querySelector:()=>({})},contents:{op:{key:'op'}},rkOf:()=>false,MM:'',simAutoOn:()=>true,esc:String};
 const chip=vm.createContext(state),start=page.indexOf('function renderChip()');
 assert(start>=0,`${file}: renderChip exists`);
 vm.runInContext(page.slice(start,page.indexOf('function saveSel()',start)),chip);
 vm.runInContext('renderChip()',chip);
 assert.equal(nodes['mi-open-import'].textContent,'내 정보 불러오기',`${file}: empty import label`);
 state.MI.info={units:[]};
 vm.runInContext('renderChip()',chip);
 assert.equal(nodes['mi-chip'].dataset.state,'loaded');
 assert.equal(nodes['mi-open-import'].textContent,'새로 불러오기(내 정보)',`${file}: loaded import label`);
 state.MI.info=null;
 vm.runInContext('renderChip()',chip);
 assert.equal(nodes['mi-open-import'].textContent,'내 정보 불러오기',`${file}: cleared import label`);
}

const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const section=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
const ctx=vm.createContext({Ux:require('../ux_ui'),miNum:require('../ux_ui').num,growthEnabled:()=>false,miMode:()=>true,MODE:'auto',SIMQ:{res:{}},simSig:()=> 'selected',esc:s=>String(s).replaceAll('<','&lt;'),
 QK:{d:{st:{}}},GuildSearch:require('../guild_search.js'),Number,Math,Date});
vm.runInContext(section('function simTitle(', 'function simBar('),ctx);
vm.runInContext(section('function miVerdict(', 'function miTab('),ctx);
vm.runInContext(section('const BIGBOSS=', '// 「추천 편성 보기」'),ctx);
vm.runInContext(section('function savedTime(', 'function renderMi('),ctx);
const ev=s=>vm.runInContext(s,ctx),visible=s=>s.replace(/<[^>]*>/g,'');
assert.match(visible(ev('miVerdict({}, {})')),/계산 전/);
ctx.SIMQ.res.selected={clear:.96,n:100,ci:[.91,.99],ttk:22,ta:35,first:'에밀리#1001',first_p:.41};
const headline=ev('miVerdict({}, {})');
assert.match(headline,/data-state="done"/);assert.match(headline,/data-verdict="safe"/);assert.match(visible(headline),/클리어96%/);assert.match(visible(headline),/약 35턴/);assert.match(headline,/에밀리 위험 41%/);
assert.match(headline,/data-help="100판 · 95% 구간/);
assert.match(headline,/내 구원자 기준/);ctx.miMode=()=>false;assert.match(ev('miVerdict({}, {})'),/표준 육성 기준/);ctx.miMode=()=>true;
assert.doesNotMatch(visible(headline),/ttk|95%|#1001|근사|TURN/);
// 오토 기준만(11/14 수동 모드 제거): 옛 결과에 수동 값(man)이 붙어 있거나 MODE 가 남아 있어도 오토 값만 보인다
ctx.MODE='manual';ctx.SIMQ.res.selected.man={c:.4,n:100,ci:[.3,.5],t:14,unsupported:[{unit:'합성 구원자',raw:'수동 잠재력'}]};
assert.match(ev('miVerdict({}, {})'),/data-verdict="safe"/);assert.match(visible(ev('miVerdict({}, {})')),/클리어96%/);assert.match(visible(ev('miVerdict({}, {})')),/약 35턴/);
assert.match(visible(ev('miVerdict({}, {})')),/오토 전투/);assert.doesNotMatch(visible(ev('miVerdict({}, {})')),/수동/);
ctx.SIMQ.res.selected.unsupported=[{unit:'합성 구원자',raw:'자동 잠재력'}];
{const result=ev('miVerdict({}, {})');
 assert.match(visible(result),/지원하지 않음 · 합성 구원자 · 자동 잠재력/);assert.doesNotMatch(visible(result),/수동 잠재력/);
 assert.doesNotMatch(result,/<details/);
}
delete ctx.MODE;
// 운에 크게 좌우되는 결과 안내: 96% 결과엔 없고, 성간 회랑 485 같은 0.5%(구간 0.2~1.2%) 결과엔 결과 카드 안에 뜬다
assert.doesNotMatch(ev('miVerdict({}, {})'),/data-k="luck-note"/);
ctx.SIMQ.res.selected={clear:.005,n:2000,ci:[.002,.012],ta:80};
{const result=ev('miVerdict({}, {})'),card=result.slice(0,result.lastIndexOf('</div>'));
 assert.match(card,/data-k="luck-note"/,'mi-verdict 카드 안');assert.match(visible(result),/클리어 확률 매우 낮음\(약 0\.5%\)/);
 assert.match(visible(result),/30번 도전해도 한 번이라도 깰 확률은 약 14%/);assert.match(result,/data-verdict="risk"/);}
ctx.SIMQ.res.selected={clear:.6,n:100,ci:[.5,.69],ta:40};assert.doesNotMatch(ev('miVerdict({}, {})'),/luck-note/);
delete ctx.SIMQ.res.selected;assert.doesNotMatch(ev('miVerdict({}, {})'),/luck-note/);

for(const key of ['op','oph','equip','clo','rush','cosmo']){
 ctx.QK.d.st[key]={'area|boss':{bp:100,w:[[[150,0,0,0,0,true]]]}};
 ctx.content={key};assert.equal(ev('bigBoss(content,{tab:"area",name:"boss"})'),1.5);
}
ctx.QK.d.st.op['area|mob']={bp:100,w:[[[200,0,0,0,0,false]]]};
assert.equal(ev('bigBoss({key:"op"},{tab:"area",name:"mob"})'),0);
assert.match(ev('bigBossNote(1.5)'),/data-k="bigboss"/);assert.match(ev('bigBossNote(1.5)'),/data-help=/);
assert.equal(ev('savedTime("2026-10-23T08:47:00")'),'10-23 08:47');
assert.equal(ev('savedTime("bad")'),'');
const skills=require('../skill_view.js');
const card=skills.render([{sl:'기본기',n:'시험',tg:'-',ty:'SOME_RAW_KEY',d1:'[효과]',dx:'[효과]',mx:1,gl:[['효과','RAW_KEY','설명']]}]);
assert.doesNotMatch(card,/SOME_RAW_KEY|RAW_KEY|- ·/);
assert.match(card,/min-height:40px/);
const cfg=require('../party_contents.json');
function checkLoading(page){
 const Ux=require('../ux_ui'),gwenCalls=[];
 const state={Ux,SIMQ:{busy:1,res:{},scr:{s:{got:2,left:80}},screening:true,loaded:true},
  LASTQ:{1:{rows:[{},{}]}},scrKey:()=> 's',simSig:()=> 'r',growthEnabled:()=>false,SCR_N:8,scrWorkers:()=>2,simEtaText:()=> '남은 시간 계산 중',esc:String,
  DIRECT:{mode:'reco'},GwenLane:{sync:o=>gwenCalls.push(o)},recoGwenShow:(show,p)=>gwenCalls.push({show,progress:p}),$:()=>null};
 const run=vm.createContext(state),start=page.indexOf('function simProgress(st)');
 vm.runInContext(page.slice(start,page.indexOf('function buildCands(',start)),run);
 const paint=()=>{gwenCalls.length=0;return vm.runInContext('simProgress({})',run);};
 // 그웬 걷기 연출은 reco-gwen-stage(#out 밖 고정)가 맡아 simProgress HTML 에 없음.
 const html=paint();assert.match(html,/후보 거르는 중 2\/80/);
 assert.match(html,/aria-valuenow="2"/);assert.match(html,/data-scrstop="1"/);assert.match(html,/data-simcancel="1"/);
 assert(gwenCalls.some(c=>c.show===true),'recoGwenShow(true) called during progress');
 state.SIMQ.screening=false;paint();state.SIMQ.loaded=false;paint();
 const bar=page.indexOf('function simBar(');vm.runInContext(page.slice(bar,page.indexOf('function simInvalidate(',bar)),run);
 assert.match(vm.runInContext('simBar(1,[{}],{},false)',run),/data-gwen="inspect"/);
 state.SIMQ.busy=null;state.SIMQ.err='통신 오류';state.SIMQ.errP=1;
 assert.match(vm.runInContext('simBar(1,[{}],{},false)',run),/data-gwen="error"/);
 state.SIMQ.err='';state.SIMQ.res.r={n:100,clear:1};state.goalVal=r=>r.clear;
 const completed=vm.runInContext('simBar(1,[{}],{},false)',run);
 assert.match(completed,/data-state="done"/);
 assert.doesNotMatch(completed,/data-gwen="report"/,'result illustration belongs to the shared lane');
 assert.match(page,/GwenStage\.slot\('reco','result'\)/);
 const h=require('./helpers/gwen_dom')();
 for(const file of ['gwen_policy.js','ux_ui.js','gwen_lane.js'])h.load(fs.readFileSync(require.resolve('../'+file),'utf8'));
 for(const part of ['board','result'])h.add('test-reco-'+part).dataset.gwenSlot='reco-'+part;
 const result=h.c.GwenStage.mount(h.doc,{mode:'reco'}).elements.result;
 assert(result.classList.contains('gwen-summary-result'),'result summary layout class missing');
 assert(result.classList.contains('gwen-reaction'),'result portrait class missing');
 const css=page.match(/@media\(prefers-reduced-motion:reduce\)\{\.gwen-work[^}]+\}/)?.[0]||'';
 for(const rule of ['.gwen-worker','animation:none','transform:none'])assert(css.includes(rule),rule);
 assert.match(page,/\.gwen-scene\{[^}]*width:140px;height:140px;flex:0 0 140px/);
}
for(const file of ['party_template.html','index.html']){
 const page=fs.readFileSync(require.resolve('../'+file),'utf8');checkLoading(page);
 // simProgress 의 gwenWork 는 reco-gwen-stage(#out 밖 고정 무대)로 대체함.
 // 남은 변이: gwenError 와 CSS reduced-motion
 for(const [from,to] of [
  ['${Ux.gwenError(SIMQ.cancelled?"cancel":"calculation")}<span class="bad"','<span class="bad"'],
  ['.gwen-work .gwen-worker{animation:none;transform:none}', '.gwen-work .gwen-worker{animation:gwen-report 1s infinite;transform:none}'],
 ]){assert(page.includes(from));assert.throws(()=>checkLoading(page.replace(from,to)),{code:'ERR_ASSERTION'});}
 // reco-gwen-stage 가 HTML 에 존재하는지 확인
 assert(page.includes('id="reco-gwen-stage"'),`${file}: reco stage host must exist`);
 assert(page.includes('data-gwen-slot="reco-board"'),`${file}: reco board slot must exist`);
}
// 대기 칸(결과 전): 「추천 편성 보기」 단추 옆에 그웬 한 번(계산 준비 중에는 기존 수사 그림만), 단추·체크박스는 그대로.
function checkIdle(page,file){
 const Ux=require('../ux_ui');
 const view=page.match(/function idleView\(\)\{[\s\S]*?growthControlPlace\(\)\}/)?.[0]||'';
 assert(view.includes('${waiting?Ux.gwenWork("inspect"):Ux.gwenIdle()}<div id="reco-actions">'),`${file}: 대기 칸 그웬은 단추 묶음 앞, 준비 중에는 수사 그림만`);
 assert.equal((page.match(/Ux\.gwenIdle\(\)/g)||[]).length,1,`${file}: 대기 그웬은 대기 칸에만 한 번(첫 안내 등 다른 화면에는 두지 않음)`);
 assert(view.includes('<button type="button" data-go="1" title="현재 조건과 내 정보로 추천함">추천 편성 보기</button>'),`${file}: 단추 그대로`);
 const idle=Ux.gwenIdle();
 assert.equal(idle,`<span class="idle-gwen" data-gwen-idle>${Ux.gwenSay('idle','left')}<button type="button" class="gwen-poke" aria-label="그웬 부르기">${Ux.gwenImage('ready','idle-gwen-art',112)}</button><span class="gwen-announcement" role="status" aria-live="polite" aria-atomic="true"></span></span>`);
 assert.doesNotMatch(idle,/<a |data-gwen=|\ssrc=/,'장식만: 조작부·진행 표식·즉시 로딩 없음');
 // 첫 안내와 대기 칸은 같은 #out 을 통째로 바꾸므로 동시에 보이지 않음.
 assert.match(page,/if\(!MI\.info&&!REQ\)\{renderMi\(\);\$\("out"\)\.innerHTML=miGuide\(\);return\}/,`${file}: 첫 안내는 #out 교체`);
 assert.match(view,/out\.innerHTML=`<div class="party idle"/,`${file}: 대기 칸도 #out 교체`);
}
// ⓘ 도움말은 자리마다 하나: 글리프는 숨기고 CSS 로 그린 i 만 보임. 「칸 안의 단추」 규칙이 숨김을 덮어쓰면 ⓘ 가 두 개로 보임.
function checkHelpOnce(page,css,file){
 const control=page.match(/<span id="growth-control">[\s\S]*?<\/span><\/span>/)?.[0]||'';
 assert.equal((control.match(/class="ux-help"/g)||[]).length,1,`${file}: 육성 체크박스 줄 ⓘ 한 개`);
 assert.equal((page.match(/id="growth-hint"/g)||[]).length,1,`${file}: growth-hint 한 개`);
 assert.doesNotMatch(page,/ⓘ<\/button>\s*(?:<button[^>]*class="ux-help"|\$\{(?:Ux\.help|q)\()/,`${file}: ⓘ 단추가 연달아 붙지 않음`);
 const guard='\nbutton.ux-help.ux-help,.season-reference .ux-help{font-size:0;line-height:0;padding:0;margin:0;';
 assert(css.includes(guard),'ⓘ 글리프 숨김 규칙');assert(css.includes(".ux-help::before{content:'i';"),'그려 넣은 i');
 // 숨김 규칙(클래스 2 + 요소 1)을 이길 수 있는 「… button」 글자 크기·안쪽 여백 규칙이 없어야 함.
 const style=page.match(/<style>([\s\S]*?)<\/style>/)[1];
 for(const [name,text,limit] of [[file,style,Infinity],['ux.css',css,css.indexOf(guard)]]){
  for(const m of text.matchAll(/([^{}]+)\{([^{}]*)\}/g)){
   if(!/(?:^|;)\s*(?:font|font-size|padding)\s*:/.test(m[2]))continue;
   for(const sel of m[1].split(',').map(s=>s.trim())){
    if(!/(?:^|[\s>+~])button(?:\[[^\]]*\])*$/.test(sel))continue;
    const ids=(sel.match(/#[\w-]+/g)||[]).length,cls=(sel.match(/\.[\w-]+|\[[^\]]*\]|:(?!not|is|where|has)[\w-]+/g)||[]).length;
    assert(!ids&&(cls<2||cls===2&&m.index<limit),`${name}: ⓘ 숨김을 덮어쓰는 규칙 ${sel}{${m[2]}}`);
   }
  }
 }
}
function checkIdleCss(css){
 for(const part of [
  '.idle:has(>.idle-gwen){display:grid;grid-template-columns:auto auto;justify-content:center;align-items:center;gap:6px 20px}',
  '.idle-gwen{display:contents;pointer-events:none}',
  '.gwen-poke{grid-column:1;grid-row:1/3;width:112px;height:112px;pointer-events:auto}',
  '.idle-gwen>.gwen-bubble{grid-column:2;grid-row:1;justify-self:start;align-self:end;max-width:280px}',
  '.idle:has(>.idle-gwen)>#reco-actions{grid-column:2;grid-row:2;align-self:start;margin-top:0;min-width:0}',
  'body:has(#drawer.open) .idle-gwen>*{visibility:hidden}',
  '@media(max-width:600px){\n .idle:has(>.idle-gwen){grid-template-columns:64px minmax(0,1fr);gap:8px 10px}\n .gwen-poke{grid-row:1;width:64px;height:64px}\n .idle-gwen>.gwen-bubble{align-self:center;max-width:100%}\n .idle:has(>.idle-gwen)>#reco-actions{grid-column:1/-1}\n}',
 ])assert(css.includes(part),part);
 // 동작 줄이기: 말풍선 등장 연출 없음(그림은 mountGwen 이 정지 PNG 로 둠).
 assert.match(css,/@media\(prefers-reduced-motion:reduce\)\{\s*\.gwen-bubble,/);
 assert.doesNotMatch(css,/\.idle-gwen[^{}]*\{[^}]*animation/,'대기 그웬에 별도 반복 연출 없음');
}
// 말풍선 모양·연출(ux.css): 테마 색, 그림 쪽 꼬리 4방향, 1회 등장, 동작 줄이기에서는 즉시 표시, 좁은 화면 배치.
function checkBubbleCss(css){
 const rule=sel=>{const at=css.indexOf('\n'+sel+'{');assert(at>=0,sel);return css.slice(at+sel.length+2,css.indexOf('}',at));};
 const base=rule('.gwen-bubble');
 for(const part of ['position:relative','max-width:min(100%,280px)','border:1px solid rgba(217,185,121,.62)','border-radius:14px','background:#1e2a45','word-break:keep-all','overflow-wrap:anywhere','pointer-events:none','animation:gwen-bubble-pop .38s cubic-bezier(.3,1.45,.5,1) 1 both'])assert(base.includes(part),part);
 const tail=rule('.gwen-bubble::after');
 for(const part of ["content:''",'position:absolute','left:var(--tx)','top:var(--ty)','rotate:var(--tr)','background:#1e2a45'])assert(tail.includes(part),part);
 for(const [dir,turn] of [['up','225deg'],['left','135deg'],['right','-45deg']])assert(rule(`.gwen-bubble[data-tail=${dir}]`).includes('--tr:'+turn),dir);
 assert(base.includes('--tr:45deg'),'기본 꼬리는 아래(그림이 말풍선 아래)');
 assert.equal(rule('.gwen-bubble:empty'),'display:none');
 assert.match(css,/@keyframes gwen-bubble-pop\{0%\{opacity:0;scale:\.72\}60%\{opacity:1\}100%\{opacity:1;scale:1\}\}/);
 assert.match(css,/@media\(prefers-reduced-motion:reduce\)\{\s*\.gwen-bubble,\.gwen-roam \.gwen-bubble,\.gwen-roam \.gwen-bubble::after\{animation:none\}\s*\.gwen-roam \.gwen-say-lane\{align-items:center\}\s*\}/);
 // 걷는 그림: 말풍선과 꼬리가 그림과 같은 박자(12초, 같은 구간)로 움직임.
 const beat=name=>css.match(new RegExp('@keyframes '+name+'\{(0%,12%)\{[^}]*\}(40%,60%)\{[^}]*\}(88%,100%)\{'))?.slice(1).join(' ');
 for(const name of ['gwen-roam','gwen-say-roam','gwen-tail-roam'])assert.equal(beat(name),'0%,12% 40%,60% 88%,100%',name);
 assert(rule('.gwen-roam .gwen-bubble').includes('gwen-say-roam 12s linear infinite'));
 assert(rule('.gwen-roam .gwen-bubble::after').includes('gwen-tail-roam 12s linear infinite'));
 assert.match(rule('.gwen-say-lane'),/width:min\(100%,560px\);min-height:40px/);
 assert.match(rule('.gwen-bubble-space'),/width:100%;min-height:64px/);
 assert.match(css,/@media\(max-width:1199px\)\{[^\n]*\.gwen-reaction \.gwen-bubble\{--tx:calc\(100% \+ \.5px\);--ty:50%;--tr:-45deg/,'좁은 결과 화면: 그림 왼쪽 말풍선, 꼬리 오른쪽');
 assert.match(css,/@media\(max-width:600px\)\{\.gwen-guide-footer>\.gwen-bubble\{--tail:50%;grid-column:1;grid-row:auto;justify-self:center\}/,'휴대폰 첫 안내: 그림 위 가운데');
 assert(css.includes('.result-summary:has(.gwen-reaction) [data-gwen="report"] .gwen-say-lane{display:none}'),'작은 보고 그림은 말풍선 생략');
 assert.doesNotMatch(css,/\.gwen-say[{:]/,'옛 말풍선 규칙 제거');
}
{const css=fs.readFileSync(require.resolve('../ux.css'),'utf8').replace(/\r\n/g,'\n'),page=fs.readFileSync(require.resolve('../party_template.html'),'utf8');checkIdleCss(css);
 for(const [from,to] of [
  ['.idle-gwen{display:contents;pointer-events:none}','.idle-gwen{display:contents}'],
  ['body:has(#drawer.open) .idle-gwen>*{visibility:hidden}',''],
  ['.gwen-poke{grid-row:1;width:64px;height:64px}','.gwen-poke{grid-row:1;width:112px;height:112px}'],
  ['.idle:has(>.idle-gwen)>#reco-actions{grid-column:2;grid-row:2;','.idle:has(>.idle-gwen)>#reco-actions{grid-column:1;grid-row:1;'],
 ]){assert(css.includes(from),from);assert.throws(()=>checkIdleCss(css.replace(from,to)),{code:'ERR_ASSERTION'},'mutation survived: '+from);}
 for(const [from,to] of [
  ['\nbutton.ux-help.ux-help,.season-reference .ux-help{font-size:0;','\n.ux-help,.season-reference .ux-help{font-size:0;'],
  ['\nbutton.ux-help.ux-help,.season-reference .ux-help{font-size:0;line-height:0;padding:0;margin:0;','\nbutton.ux-help.ux-help,.season-reference .ux-help{font-size:12px;line-height:0;padding:0;margin:0;'],
  ['.bbody button{font-size:13px;white-space:nowrap}','.x .y .z button{font-size:13px;white-space:nowrap}'],
 ]){assert(css.includes(from),from);assert.throws(()=>checkHelpOnce(page,css.replace(from,to),'party_template.html'),{code:'ERR_ASSERTION'},'mutation survived: '+from);}}
{const css=fs.readFileSync(require.resolve('../ux.css'),'utf8').replace(/\r\n/g,'\n');checkBubbleCss(css);
 for(const [from,to] of [
  [' .gwen-bubble,.gwen-roam .gwen-bubble,.gwen-roam .gwen-bubble::after{animation:none}',' .gwen-bubble{animation:none}'],
  ['animation:gwen-bubble-pop .38s cubic-bezier(.3,1.45,.5,1) 1 both}\n.gwen-bubble:empty','animation:gwen-bubble-pop .38s cubic-bezier(.3,1.45,.5,1) infinite both}\n.gwen-bubble:empty'],
  ['.gwen-bubble:empty{display:none}','.gwen-bubble:empty{display:block}'],
  ['.gwen-bubble[data-tail=left]{--tx:-.5px;--ty:50%;--tr:135deg','.gwen-bubble[data-tail=left]{--tx:-.5px;--ty:50%;--tr:45deg'],
  ['@keyframes gwen-tail-roam{0%,12%','@keyframes gwen-tail-roam{0%,20%'],
  ['max-width:min(100%,280px)','max-width:none'],
  ['border:1px solid rgba(217,185,121,.62);border-radius:14px','border:0;border-radius:0'],
  ['.result-summary:has(.gwen-reaction) [data-gwen="report"] .gwen-say-lane{display:none}',''],
 ]){assert(css.includes(from),from);assert.throws(()=>checkBubbleCss(css.replace(from,to)),{code:'ERR_ASSERTION'},'mutation survived: '+from);}}
for(const f of ['investigate.webp','files.webp'])assert(fs.statSync(require.resolve('../assets/ui_icons/gwen/'+f)).size<=80000);
for(const module of ['guild_search','cosmo_search']){
 const search=require('../'+module),cx={hasInfo:true,work:require('../ux_ui').gwenWork,workMode:'screen',esc:String,label:String,level:0,mode:'top',levelMax:1};
 assert.match(search.html({phase:'run',msg:'후보 확인 중',done:2,total:80},cx),/data-gwen="screen"/);
 assert.match(search.html({phase:'err',msg:'통신 오류'},cx),/data-gwen="error"/);
 assert.match(search.html({phase:'done',rows:[]},cx),/data-gwen="error"/);
 assert.doesNotMatch(search.html({phase:'idle'},cx),/data-gwen=/);
}
assert.deepEqual(cfg.breakSkills['행성 정화'].bonusRoles,[]);
assert.equal(cfg.breakSkills['행성 정화'].text,'광역 피해(공격력 100%), 강인도 피해 +1, 스킬 후 노바 +1');
// Parse all template scripts as JavaScript; data replacement is an identifier in the template.
for(const [,code] of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))new vm.Script(code);
console.log('PASS idle-panel Gwen (once, beside the button, hidden under the import drawer), one help icon per spot, Gwen speech bubbles (guide, import drawer, empty roster, stylesheet), update notice, import label and five-step box (template + index), public headline, mode consistency, boss contents, saved date, skill labels, break description, script syntax');
