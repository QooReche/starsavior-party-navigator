const assert=require('node:assert/strict'),fs=require('node:fs');
const harness=require('./helpers/gwen_dom');
const read=p=>fs.readFileSync(require.resolve('../'+p),'utf8').replace(/\r\n/g,'\n');
const source=read('direct_ui.js'),template=read('party_template.html');
function check(code=source){
  const h=harness(),{c}=h;
  for(const id of ['content','mi-panel','start-screen','direct-panel','cosmo-direct-panel','out','growth-control-home','growth-control','direct-picker-dialog'])h.add(id);
  c.$=id=>h.doc.getElementById(id);c.$('content').value=0;c.$('mi-panel').hidden=true;
  const strip=h.add('mode-strip');strip.innerHTML=template.match(/<nav id="mode-strip"[^>]*>([\s\S]*?)<\/nav>/)[1];
  Object.assign(c,{contents:[{key:'cosmo'},{key:'op'},{key:'cube'},{key:'guild'}],MI:{info:null},
    Ux:require('../ux_ui'),RECO:{},recoGwenVisibility(){},growthControlPlace(){},cdRefresh(){c.cosmoRefresh++},cosmoRefresh:0,
    GwenStage:{activate:m=>c.activeStage=m,mount(){}},
    history:{state:{},replaceState(){c.navigations++},pushState(){c.navigations++}},
    location:{href:'http://test/?c=cosmo&pm=direct'},navigations:0});
  h.load(code);
  h.load("DIRECT.draft={v:1,slots:[null,null,null,null]};DIRECT.mode='direct';DIRECT.slots={};directSync=()=>{};directResultsPaint=()=>{};directPaintInput=()=>'';directPaint=()=>{painted++};");
  c.painted=0;c.directRefresh();
  assert.equal(c.$('cosmo-direct-panel').hidden,false);assert.equal(c.$('direct-panel').hidden,true);assert.equal(c.activeStage,'cdirect');
  assert.equal(c.painted,0);assert(c.cosmoRefresh>0);
  for(const host of [strip,c.$('start-screen')])assert(!host.querySelector('[data-pn-mode="direct"]').disabled);
  c.directNavigate('direct');assert.equal(c.navigations,1,'cosmo entry allowed');
  for(const index of [1,2,3,0,1]){
    c.$('content').value=index;c.directRefresh();
    assert.equal(c.$('cosmo-direct-panel').hidden,index!==0);assert.equal(c.$('direct-panel').hidden,index===0);
  }
  assert(c.painted>0);assert(!template.includes('direct-construction'));
  c.$('content').value=0;c.directNavigate('reco');assert.equal(c.$('cosmo-direct-panel').hidden,true);
}
check();
const mutations=[
  ["info||DIRECT.mode!=='direct'||!cosmo","true"],
  ["info||DIRECT.mode!=='direct'||cosmo","info||DIRECT.mode!=='direct'"],
  ["?'cdirect':stageMode","?null:stageMode"],
  ['directVisibility();cdRefresh();','directVisibility();'],
  ["  const before=source?.closest", "  if(mode==='direct'&&contents[$('content').value]?.key==='cosmo')return;\n  const before=source?.closest"]
];
for(const [before,after] of mutations){assert(source.includes(before),before);assert.throws(()=>check(source.replace(before,after)),{code:'ERR_ASSERTION'},before);}
const U=require('../ux_ui');
assert.equal(U.GWEN_SCENES.construction.file,'construction');assert.equal(U.GWEN_SCENES.construction.fallback,'board');
assert.equal(U.GWEN_SCENES.construction.blink,undefined);
assert.match(U.gwenImage('construction'),/data-gwen-art="construction"/);
async function fallback(code=read('ux_ui.js')){
  const h=harness();h.load(read('gwen_policy.js'));h.load(code);
  const Base=h.c.Image;h.c.Image=class extends Base{decode(){return this.src?.includes('construction')?Promise.reject(Error('missing approved art')):super.decode();}};
  h.add('notice').innerHTML=h.c.Ux.gwenImage('construction');h.c.Ux.mount();await h.flush();
  const img=h.doc.getElementById('notice').querySelector('img');
  assert.equal(img.dataset.gwenArt,'board','missing artwork must fall back');
  assert.equal(img.dataset.gwenStatic,'assets/ui_icons/gwen/board.png');
  assert.equal(img.getAttribute('aria-hidden'),'true');
}
(async()=>{
  await fallback();
  const ux=read('ux_ui.js'),guard='if(fallback&&fallback!==s.expression)';assert(ux.includes(guard));
  await assert.rejects(()=>fallback(ux.replace(guard,'if(false)')),{code:'ERR_ASSERTION'});
  await fallback();
  console.log(`PASS cosmo direct entry, isolated panels, transitions, navigation, reusable construction art fallback; ${mutations.length+1} mutations caught`);
})().catch(e=>{console.error(e);process.exitCode=1;});
