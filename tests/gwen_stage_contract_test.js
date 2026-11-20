// Every progress-bearing view must feed the common stage, including its fast repaint path.
const assert=require('node:assert/strict'),fs=require('node:fs');
const files=['party_template.html','direct_run.js','direct_ui.js','cosmo_direct_page.js','cosmo_direct_ui.js','cosmo_search.js','guild_search.js'];
const sources=Object.fromEntries(files.map(f=>[f,fs.readFileSync(f,'utf8')]));
const body=(s,name)=>s.slice(s.indexOf('function '+name+'('),s.indexOf('\nfunction ',s.indexOf('function '+name+'(')+1)>>>0);
function check(src){
  for(const [file,s] of Object.entries(src))assert(!/GwenLane\.(registerStage|sync|activate)\(/.test(s),file+' bypasses GwenStage');
  const html=src['party_template.html'];
  const rules=[
    ['reco',html,'simProgress','role="progressbar"',/recoGwenShow\(true/],
    ['direct',src['direct_run.js'],'directResultsPaint',"$('direct-progress').value",/DIRECT_GWEN\.update\(/],
    ['cdirect',src['cosmo_direct_page.js'],'cdPaint','확인 중 ·',/GwenStage\.mount\(host,\{mode:'cdirect'\}\)/],
    ['cosmoSearch',html,'renderCosmoSearch','cs-progress',/searchGwenPaint\(p,'cosmoSearch',CSR\)/],
    ['guildSearch',html,'renderGuildSearch','gd-search-prog',/searchGwenPaint\(p,'guildSearch',GSR\)/]
  ];
  for(const [mode,s,fn,marker,wire] of rules){const part=body(s,fn);assert(part.includes(marker),mode+' lost progress discovery');assert.match(part,wire,mode+' progress has no common stage');}
  assert.match(body(html,'recoGwenShow'),/RECO_GWEN\.progress\(/);
  assert.match(html,/const DIRECT_GWEN=GwenStage\.mount\(document,\{mode:'direct'\}\)/);
  assert.match(html,/const RECO_GWEN=GwenStage\.mount\(document,\{mode:'reco'\}\)/);
  assert.match(body(html,'csTick'),/searchGwenPaint\(\$\('cosmo-search'\),'cosmoSearch',CSR\)/);
  assert.match(body(html,'searchGwenPaint'),/GwenStage\.mount\(host,\{mode\}\)/);
  // Search renderers may accept other consumers, but page adapters must never inject a second actor.
  for(const fn of ['renderCosmoSearch','renderGuildSearch']){
    assert(!/work:Ux\.gwenWork|report:Ux\.gwenReport/.test(body(html,fn)),fn+' duplicates the actor');
  }
  // A new progress element in static screen markup needs an explicit owner contract here.
  const staticHtml=html.slice(0,html.indexOf('<script'));
  for(const match of staticHtml.matchAll(/<progress\b[^>]*id="([^"]+)"/g))assert.equal(match[1],'direct-progress','unowned progress screen: '+match[1]);
}
check(sources);
for(const [file,from] of [
  ['party_template.html',"searchGwenPaint(p,'guildSearch',GSR)"],
  ['party_template.html',"searchGwenPaint(p,'cosmoSearch',CSR)"],
  ['party_template.html','RECO_GWEN.progress(progress||0)'],
  ['direct_run.js','DIRECT_GWEN.update('],
  ['cosmo_direct_page.js',"GwenStage.mount(host,{mode:'cdirect'})"]
]){
  assert(sources[file].includes(from));
  const mutated={...sources,[file]:sources[file].replaceAll(from,'missingStage(')};
  assert.throws(()=>check(mutated),{code:'ERR_ASSERTION'},'omitted '+from);
  check(sources);console.log('MUTATION caught + restored:',from);
}
console.log('PASS 5 progress screens / 5 missing-component mutations');
