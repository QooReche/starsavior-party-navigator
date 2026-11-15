const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
// Check both the editable template and the generated page served to users.
for(const file of ['party_template.html','index.html']){
 const page=fs.readFileSync(require.resolve('../'+file),'utf8');
 const update=page.match(/<p class="notice" data-k="update-notice">([^<]*)<\/p>/);
 assert(update,`${file}: top update notice exists`);
 assert.match(update[1],/^📢 11\/15 업데이트 ·/,`${file}: update date`);
 assert.equal((page.match(/data-k="update-notice"/g)||[]).length,1);
 assert.match(page,/<\/header>\s*<p class="notice" data-k="update-notice">[^<]*<\/p>\s*<p class="notice" data-k="notice">모의 전투 결과라 실제 플레이와 다를 수 있어요/,`${file}: update directly above the original guidance`);
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
  '게임에 로그인 → 로비가 보이면 <b>도구 창에서 Enter</b>\n     <span class="mi-import-warning">⚠ 게임이 이미 켜져 있으면 <b>완전히 끄고</b> 다시 켜세요</span>',
  '사이트가 자동으로 열리며 반영돼요'
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
 assert.match(card,/data-k="luck-note"/,'mi-verdict 카드 안');assert.match(visible(result),/클리어 확률이 매우 낮아요\(약 0\.5%\)/);
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
assert.deepEqual(cfg.breakSkills['행성 정화'].bonusRoles,[]);
assert.equal(cfg.breakSkills['행성 정화'].text,'광역 피해(공격력 100%), 강인도 피해 +1, 스킬 후 노바 +1');
// Parse all template scripts as JavaScript; data replacement is an identifier in the template.
for(const [,code] of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))new vm.Script(code);
console.log('PASS update notice, import label and four-step box (template + index), public headline, mode consistency, boss contents, saved date, skill labels, break description, script syntax');
