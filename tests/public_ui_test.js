const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function checkNotice(page,file){
 const update=page.match(/<p class="notice update-notice" data-k="update-notice">([\s\S]*?)<\/p>/);
 assert(update,`${file}: distinct update box exists`);
 const text=update[1].replace(/<[^>]*>/g,'').trim();
 assert.match(text,/^📢 11\/15 업데이트 ·/);
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
 assert.match(heading,/<img class="gwen-head" src="assets\/ui_icons\/gwen_header_72.png" width="36" height="36" alt="" aria-hidden="true">/);
 assert(heading.indexOf('gwen-head')<heading.indexOf('파티 편성 네비게이터'),`${file}: face before title`);
 const start=page.indexOf('function miGuide()');
 const guide=vm.runInNewContext(page.slice(start,page.indexOf('function showReco()',start))+';miGuide()');
 assert.match(guide,/<img class="gwen-guide-art" src="assets\/ui_icons\/gwen\/welcome.png"[^>]*alt="" aria-hidden="true">/);
 assert.equal((page.match(/src="assets\/ui_icons\/gwen\/welcome.png"/g)||[]).length,2,`${file}: welcome in first guide and import drawer`);
 assert(page.includes('게임 이미지·만화의 권리는 원 권리자에게 있음.'),`${file}: image and comic attribution`);
}
// Check both the editable template and the generated page served to users.
for(const file of ['party_template.html','index.html']){
 const page=fs.readFileSync(require.resolve('../'+file),'utf8');
 checkNotice(page,file);checkTone(page,file);checkGwen(page,file);
 for(const [from,to,check] of [
  ['gwen_favicon_32.png','old_star.svg',checkGwen],
  ['gwen_favicon_180.png','old_touch.png',checkGwen],
  ['gwen_favicon_512.png','old_icon.png',checkGwen],
  ['class="gwen-head"','class="removed-head"',checkGwen],
  ['class="gwen-guide-art"','class="removed-art"',checkGwen],
  ['게임 이미지·만화의 권리는','게임 이미지의 권리는',checkGwen],
  ['class="notice update-notice"','class="notice"',checkNotice],
  ['코스모 힐데 추가','코스모 힐데 적 정보 추가 및 전투 판정 변경 사항 상세 안내',checkNotice],
  ['background:color-mix','color:color-mix',checkNotice],
  ['border:1px solid var(--acc);border-radius:8px','border:0;border-radius:0',checkNotice],
  ["document.getElementById('update-history').open=true","document.getElementById('update-history').open=false",checkNotice],
  ['모의 전투 결과라 실제 플레이와 다를 수 있음','모의 전투 결과라 실제 플레이와 다를 수 있어요',checkTone],
  ['게임이 켜져 있으면 <b>완전히 껐다</b> 다시 켜야 함','게임이 이미 켜져 있으면 <b>완전히 끄고</b> 다시 켜세요',checkTone],
  ['사이트가 자동으로 열리며 반영됨','사이트가 자동으로 열리며 반영돼요',checkTone]
 ]){assert(page.includes(from));assert.throws(()=>check(page.replace(from,to),file),{code:'ERR_ASSERTION'},`${file}: mutation caught: ${from}`);check(page,file);}
 assert.equal((page.match(/data-k="update-notice"/g)||[]).length,1);
 assert.match(page,/<\/header>\s*<p class="notice update-notice" data-k="update-notice">[^\n]*<\/p>\s*<p class="notice" data-k="notice">모의 전투 결과라 실제 플레이와 다를 수 있음/,`${file}: update directly above the original guidance`);
 assert.match(page,/<summary>업데이트 내역\(11\/15\)<\/summary>11\/15:[^<]+<br>11\/12: 신규 구원자 길레/);
 // Keep the copy action and all four instructions together, in both shipped sources.
 const guide=page.match(/<div class="mi-import-guide">([\s\S]*?)<\/ol>\s*<p class="mut mi-import-fallback">([\s\S]*?)<\/p>\s*<\/div>/);
 assert(guide,`${file}: import guide box and fallback exist`);
 assert.match(guide[1],/^\s*<div class="dtools"><button id="mi-copy" type="button">명령 복사<\/button><\/div>\s*<ol>/,`${file}: existing copy button comes first inside box`);
 assert.equal((page.match(/id="mi-copy"/g)||[]).length,1,`${file}: one copy button`);
 const steps=[...guide[1].matchAll(/<li>([\s\S]*?)<\/li>/g)].map(m=>m[1].trim().replace(/\s+/g,' '));
 assert.deepEqual(steps,[
  '단추를 눌러 복사 → <b>PowerShell</b>에 붙여넣고 <b>Enter</b>',
  '「관리자 확인」 창이 뜨면 <b>[예]</b>',
  '게임에 로그인 → 로비가 보이면 <b>도구 창에서 Enter</b>\n     <span class="mi-import-warning">⚠ 게임이 켜져 있으면 <b>완전히 껐다</b> 다시 켜야 함</span>',
  '사이트가 자동으로 열리며 반영됨'
 ].map(s=>s.replace(/\s+/g,' ')),`${file}: four short steps and separate restart warning`);
 assert.equal(guide[2],'안 될 때·다른 기기에서: 바탕화면 <b>내정보.json</b>을 [파일 선택]으로 올리기');
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
 const Ux=require('../ux_ui'),state={Ux,SIMQ:{busy:1,res:{},scr:{s:{got:2,left:80}},screening:true,loaded:true},
  LASTQ:{1:{rows:[{},{}]}},scrKey:()=> 's',simSig:()=> 'r',growthEnabled:()=>false,SCR_N:8,scrWorkers:()=>2,simEtaText:()=> '남은 시간 계산 중',esc:String};
 const run=vm.createContext(state),start=page.indexOf('function simProgress(st)');
 vm.runInContext(page.slice(start,page.indexOf('function buildCands(',start)),run);
 const paint=()=>vm.runInContext('simProgress({})',run);
 assert.match(paint(),/data-gwen="screen"/);assert.match(paint(),/후보 거르는 중 2\/80/);
 assert.match(paint(),/aria-valuenow="2"/);assert.match(paint(),/data-scrstop="1"/);assert.match(paint(),/data-simcancel="1"/);
 state.SIMQ.screening=false;assert.match(paint(),/data-gwen="long"/);
 state.SIMQ.loaded=false;assert.match(paint(),/data-gwen="inspect"/);
 const bar=page.indexOf('function simBar(');vm.runInContext(page.slice(bar,page.indexOf('function simInvalidate(',bar)),run);
 assert.match(vm.runInContext('simBar(1,[{}],{},false)',run),/data-gwen="inspect"/);
 state.SIMQ.busy=null;state.SIMQ.err='통신 오류';state.SIMQ.errP=1;
 assert.match(vm.runInContext('simBar(1,[{}],{},false)',run),/data-gwen="error"/);
 state.SIMQ.err='';state.SIMQ.res.r={n:100,clear:1};state.goalVal=r=>r.clear;
 assert.match(vm.runInContext('simBar(1,[{}],{},false)',run),/data-gwen="report"/);
 assert.match(vm.runInContext('simBar(1,[{}],{},false)',run),/data-gwen="report"/);
 const css=page.match(/@media\(prefers-reduced-motion:reduce\)\{\.gwen-work[^}]+\}/)?.[0]||'';
 for(const rule of ['.gwen-worker','animation:none','transform:none'])assert(css.includes(rule),rule);
 assert.match(page,/\.gwen-scene\{[^}]*width:140px;height:140px;flex:0 0 140px/);
}
for(const file of ['party_template.html','index.html']){
 const page=fs.readFileSync(require.resolve('../'+file),'utf8');checkLoading(page);
 for(const [from,to] of [
  ['${Ux.gwenWork(sc?"screen":SIMQ.loaded?"long":"inspect")}',''],
  ['${Ux.gwenWork("error")}<span class="bad"','<span class="bad"'],
  ['.gwen-work .gwen-worker{animation:none;transform:none}', '.gwen-work .gwen-worker{animation:gwen-report 1s infinite;transform:none}'],
 ]){assert(page.includes(from));assert.throws(()=>checkLoading(page.replace(from,to)),{code:'ERR_ASSERTION'});}
}
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
console.log('PASS update notice, import label and four-step box (template + index), public headline, mode consistency, boss contents, saved date, skill labels, break description, script syntax');
