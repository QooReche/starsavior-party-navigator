// Every progress-bearing view must feed the common stage, including its fast repaint path.
const assert=require('node:assert/strict'),fs=require('node:fs');
const files=fs.readdirSync('.').filter(f=>f.endsWith('.js')||f==='party_template.html');
const sources=Object.fromEntries(files.map(f=>[f,fs.readFileSync(f,'utf8')]));
// Exact occurrences, rather than file/function allowlists: adding even one more indicator fails.
// The five owners are checked below. Shared producers feed these owners; growth's independent
// result tab is outside this five-screen change. Counts without running work are not progress.
const inventory={
  'cosmo_direct_page.js':[['${active.bosses.reduce((n,b)=>n+(CDIRECT.rows[b]?.progress||0),0)}/${active.bosses.length*SIMQ.n}','cdirect']],
  'cosmo_direct_ui.js':[['${n}/4','excluded: party size'],['${n}/4','excluded: party size'],['${all?num(m.total):`미완료 · ${m.doneCount}/${m.bosses.length}','excluded: ready result count']],
  'cosmo_search.js':[['${attempt}/${retry.limits.length - 1}','cosmoSearch'],['${st.total ? ` · ${num(st.done)}/${num(st.total)}','cosmoSearch']],
  'direct_bundle.js':[['role="progressbar"','reco'],['${own.progress||0}/${own.snapshot.runs}','direct'],['${Math.max(1,b.steps.findIndex(s=>s.kind===b.current)+1)}/${b.steps.length}','direct']],
  'direct_party.js':[['${members.length}/4','excluded: party size']],
  'direct_run.js':[['${running.progress||0}/${running.snapshot.runs}','direct'],['${row.progress||0}/${row.snapshot.runs}','direct']],
  'growth_ui.js':[['${d}/24','producer: env.paint; default growth tab outside five owners'],['${Object.keys(results).length}/${jobs.length}','producer: env.paint; default growth tab outside five owners']],
  'guild_search.js':[['${st.total ? ` · ${st.done}/${st.total}','guildSearch']],
  'myinfo_view.js':[["${n}/${e?.parts||'?'}",'excluded: equipment set parts']],
  'party_template.html':[['<progress','direct'],['${rows.filter(j=>SIMQ.res[j.sig]).length}/${rows.length}','reco'],['${seen}/${sc.total}','excluded: stopped sample count'],['${sc.got||0}/${sc.left}','reco'],['${sc.got}/${sc.left}','reco'],['role="progressbar"','reco'],['${done}/${all}','reco'],['${dmgScore(party.map(x=>x.s.key),DMW[0]).toFixed(1)}/10','excluded: power score'],['${eq}/6','excluded: equipment slots']],
  'placement_page.js':[['${DIRECT.placement.done||0}/24','direct'],['${CDIRECT.placement.done||0}/24','cdirect'],['${d}/24','reco']],
  'recommend_runtime.js':[['${got}/${jobs.length}','producer: recoProgressPaint / directResultsPaint']],
  'sim_worker.js':[['${i+1}/${m.teams.length}','producer: worker result consumers']]
};
const progressPattern=/<progress\b|role=["']progressbar["']|\$\{[^}\r\n]+\}\/\$\{[^}\r\n]+\}|\$\{[^}\r\n]+\}\/\d+/g;
const body=(s,name)=>s.slice(s.indexOf('function '+name+'('),s.indexOf('\nfunction ',s.indexOf('function '+name+'(')+1)>>>0);
function check(src){
  for(const [file,s] of Object.entries(src)){
    const found=[...s.matchAll(progressPattern)].map(m=>m[0]);
    assert.deepEqual(found,(inventory[file]||[]).map(x=>x[0]),file+' has unowned/new progress indicators');
  }
  for(const [file,s] of Object.entries(src))if(file!=='gwen_lane.js')assert(!/GwenLane\.(registerStage|sync|activate)\(/.test(s),file+' bypasses GwenStage');
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
  assert(body(html,'searchGwenPaint').includes("step:state.id+':'+state.msg"),'search phase token missing');
  assert.match(body(src['direct_bundle.js'],'recoProgressPaint'),/recoGwenShow\(true,task\.progress/);
  assert(!/Ux\.gwenWork/.test(body(src['direct_bundle.js'],'recoProgressPaint')),'bundle progress duplicates the actor');
  assert.match(src['recommend_runtime.js'],/recoProgressPaint\(task\)/);
  assert.match(src['growth_ui.js'],/paint=env\.paint\|\|growthPaint/);
  // Search renderers may accept other consumers, but page adapters must never inject a second actor.
  for(const fn of ['renderCosmoSearch','renderGuildSearch']){
    assert(!/work:Ux\.gwenWork|report:Ux\.gwenReport/.test(body(html,fn)),fn+' duplicates the actor');
  }
}
check(sources);
for(const [file,from] of [
  ['party_template.html',"searchGwenPaint(p,'guildSearch',GSR)"],
  ['party_template.html',"searchGwenPaint(p,'cosmoSearch',CSR)"],
  ['party_template.html','RECO_GWEN.progress(progress||0)'],
  ['direct_run.js','DIRECT_GWEN.update('],
  ['cosmo_direct_page.js',"GwenStage.mount(host,{mode:'cdirect'})"],
  ['direct_bundle.js','recoGwenShow(true,task.progress||0)'],
  ['party_template.html',"step:state.id+':'+state.msg"]
]){
  assert(sources[file].includes(from));
  const replacement=from.endsWith('(')?'Boolean(':from.startsWith('step:')?'step:null':'void 0';
  const mutated={...sources,[file]:sources[file].replaceAll(from,replacement)};
  assert.throws(()=>check(mutated),{code:'ERR_ASSERTION'},'omitted '+from);
  check(sources);console.log('MUTATION caught + restored:',from);
}
for(const indicator of ['<progress id="new-screen">','<div role="progressbar">','${done}/${total}']){
  const mutated={...sources,'new_screen.js':'function paint(){return `'+indicator+'`;}'};
  assert.throws(()=>check(mutated),{code:'ERR_ASSERTION'},'new progress indicator escaped discovery');
  check(sources);console.log('MUTATION caught + restored: new indicator',indicator);
}
console.log('PASS 5 progress screens / 10 contract mutations');
