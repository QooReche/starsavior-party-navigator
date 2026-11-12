const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const gate=require('../season_gate.js'),stats=require('../myinfo_stats.js');
const frag=require('../data/foe_clash.json');
const html=fs.readFileSync('index.html','utf8');
assert(require('../sim/manifest.json').files.includes('data/foe_clash.json'));
// Generated payload: build_party_html's content and period wiring.
const match=html.match(/const D=(\{[^\n]+\});/);
assert(match,'generated D payload');
const D=JSON.parse(match[1]),clash=D.contents.find(c=>c.key==='clash');
assert(clash);assert.equal(clash.name,'격전 의뢰');assert.equal(clash.boss,true);
assert.equal(clash.stages.length,18);assert.equal(new Set(clash.stages.map(s=>s.tab)).size,3);
const quick=require('../data/quick.json');
for(const s of clash.stages)assert(quick.st.clash[s.tab+'|'+s.name], 'quick/sim entry for '+s.name);
assert.deepEqual(clash.seasonPeriod,frag.period);
assert.equal(stats.rule_for_content('clash'),'normal');
const source=fs.readFileSync('season_gate_ui.js','utf8');
function audit(code){
  let now=Date.parse(frag.period.start)-1;
  const nodes={'content':{value:0,options:[{}]},'season-chip':{},'season-note':{}};
  const ctx={D,contents:[clash],SeasonGate:gate,Date:{now:()=>now},location:{search:''},$:id=>nodes[id]};
  vm.createContext(ctx);vm.runInContext(code,ctx);
  for(const [time,phase,blocked,label] of [
    [Date.parse(frag.period.start)-1,'upcoming',true,'미오픈'],
    [Date.parse(frag.period.start),'active',false,''],
    [Date.parse(frag.period.end)-1,'active',false,''],
    [Date.parse(frag.period.end),'ended',true,'미오픈']]){
    now=time;assert.equal(ctx.seasonStatus('clash').phase,phase);
    assert.equal(ctx.seasonBlocked('clash'),blocked);
    ctx.seasonPaint();assert.equal(nodes['season-chip'].textContent,label);
    assert(nodes.content.options[0].textContent.includes('격전 의뢰'));
    if(blocked)assert(nodes.content.options[0].textContent.includes('[미오픈]'));
  }
}
audit(source);
const mutant=source.replace("['guild','cosmo','clash']","['guild','cosmo']");
assert.notEqual(mutant,source);assert.throws(()=>audit(mutant));
console.log('PASS clash list, 3x6 stages, normal level, start/end gate; MUTATION caught: clash gate removed');
