const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const section=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
const ctx=vm.createContext({MODE:'auto',SIMQ:{res:{}},simSig:()=> 'selected',esc:s=>String(s).replaceAll('<','&lt;'),
 QK:{d:{st:{}}},Number,Math,Date});
vm.runInContext(section('function simTitle(', 'function simBar('),ctx);
vm.runInContext(section('function miVerdict(', 'function miTab('),ctx);
vm.runInContext(section('const BIGBOSS=', '// 「추천 편성 보기」'),ctx);
vm.runInContext(section('function savedTime(', 'function renderMi('),ctx);
const ev=s=>vm.runInContext(s,ctx),visible=s=>s.replace(/<[^>]*>/g,'');
assert.match(visible(ev('miVerdict({}, {})')),/시뮬 전/);
ctx.SIMQ.res.selected={clear:.96,n:100,ci:[.91,.99],ttk:22,ta:35,first:'에밀리#1001',first_p:.41};
const headline=ev('miVerdict({}, {})');
assert.equal(visible(headline),'깰 수 있음 · 클리어 96% · 약 35턴 · 에밀리 위험 41%');
assert.match(headline,/title="100판 · 95% 구간/);
assert.doesNotMatch(visible(headline),/ttk|95%|#1001|근사|TURN/);
ctx.MODE='manual';ctx.SIMQ.res.selected.man={c:.4,n:100,ci:[.3,.5],t:14};
assert.equal(visible(ev('miVerdict({}, {})')),'어려움 · 클리어 40% · 약 14턴');
for(const key of ['op','oph','equip','clo','rush','cosmo']){
 ctx.QK.d.st[key]={'area|boss':{bp:100,w:[[[150,0,0,0,0,true]]]}};
 ctx.content={key};assert.equal(ev('bigBoss(content,{tab:"area",name:"boss"})'),1.5);
}
ctx.QK.d.st.op['area|mob']={bp:100,w:[[[200,0,0,0,0,false]]]};
assert.equal(ev('bigBoss({key:"op"},{tab:"area",name:"mob"})'),0);
assert.equal(visible(ev('bigBossNote(1.5)')),'⚠ 큰 보스전 — 시뮬이 실제와 다를 수 있음');
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
console.log('PASS public headline, mode consistency, boss contents, saved date, skill labels, break description, script syntax');
