const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),S=require('../myinfo_stats'),G=require('../growth_guide'),Share=require('../share_state');
const growth=require('../data/growth.json'),raw=require('./fixtures/myinfo_synthetic.json'),clone=x=>JSON.parse(JSON.stringify(x));
const info=clone(raw);
// Explicit synthetic zero tactics, rather than silently accepting missing imported fields.
for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
function generation(){const before=JSON.stringify(info),base=M.profile(info,roster,growth,'op');
  for(const s of roster){const a=M.assume(s.key,info,growth),p=M.assumedProfile(base,a,info,growth,'op'),f=p.results[s.key];
    assert.equal(f.missing.length,0);assert(f.power>0);assert.notEqual(p,base);
    assert.equal(a.unit.id,s.uid);assert.deepEqual(a.unit.skills,growth.assumed.units[s.key].skills);
    const unlocked=Math.max(...Object.entries(growth.units[s.uid].resonance_unlock).filter(([,lv])=>lv<=S.effective_level(a.unit,a.targetInfo)).map(([n])=>+n));
    assert.equal(a.unit.resonance,Math.max(base.units[s.key]?.resonance||0,unlocked));
    if(!base.units[s.key]){assert.equal(a.source,'assumed');assert.equal(a.unit.sigil,0);assert.equal(a.unit.favor,0);
      assert.equal(a.unit.equip.length,6);assert.equal(M.team([s.key],p,k=>k).assumed,1);}
    const fixed=M.assumedProfile(base,a,info,growth,'cosmo').results[s.key];
    assert.deepEqual(fixed,S.final_stats(a.unit,{...info,star_link_level:400},growth,'fixed200'));
    assert.notEqual(fixed.power,f.power);
  }
  assert.equal(JSON.stringify(info),before);
  const key=roster.find(s=>s.uid===info.units[0].id).key,a=M.assume(key,info,growth,{kind:'equipment'});
  const expected=clone(info.units[0]);expected.equip=clone(growth.assumed.units[key].equip);
  assert.deepEqual(a.unit,expected);assert.deepEqual(a.changedFields,['equip']);
  const bad=clone(growth);delete bad.assumed.combat_support.potentials[a.unit.gauntlet.potentials[0]?.[0]];
  const missing=M.assume('luna',raw,growth);assert.throws(()=>M.assumedProfile(base,missing,raw,growth,'op'),/tactics/);
  const unsupported=clone(M.assume('luna',info,growth));unsupported.unit.gauntlet.potentials=[[999999,1,0,0]];
  assert.throws(()=>M.assumedProfile(base,unsupported,info,growth,'op'),/potential/);
  unsupported.unit.gauntlet.potentials=[];unsupported.unit.skills.basic=999;
  assert.throws(()=>M.assumedProfile(base,unsupported,info,growth,'op'),/combat.skill/);
}
function signatures(){const b={account:'a',options:{growth:true},targets:['u'],preset:'p',content:['op','1','3'],excluded:['x'],breaks:['fire'],mode:'auto',rules:{},engine:'e',data:'d'};
  for(const key of Object.keys(b))assert.notEqual(G.signature(b),G.signature({...b,[key]:key==='excluded'?['y']:key==='options'?{}:'changed'}),key);
  const q=Share.stringify({ag:true,ae:true,ao:false,units:info.units,assumed:M.assume('luna',info,growth)});
  assert(!q.includes('units')&&!q.includes('item')&&!q.includes('assumed'));
  assert.deepEqual(Share.parse('?'+q,[],[]),{ag:true,ao:false});
  assert(!q.includes('ae='));assert.deepEqual(Share.parse('?ae=1',[],[]),{});
}
function quickOrdering(){const text=fs.readFileSync(require.resolve('../growth_ui.js'),'utf8'),start=text.indexOf('function growthQuickCmp'),end=text.indexOf('async function growthCandidates',start);
  const ctx=vm.createContext({QO:{hard:0,tight:1,safe:2}});vm.runInContext(text.slice(start,end),ctx);
  const early={vd:'hard',q:{rounds:1,left:0},v:10},late={vd:'hard',q:{rounds:20,left:0},v:10};
  assert(ctx.growthQuickCmp(late,early)<0,'hard candidates must prefer surviving longer');
  assert(ctx.growthQuickCmp({...late,vd:'safe',q:{rounds:3,left:.8}},{...early,vd:'safe',q:{rounds:1,left:.2}})<0);
  let tabsReset=0,removed=0;
  const cancel=vm.createContext({document:{getElementById(id){assert.equal(id,'growth-result');return {remove(){removed++;}};}},growthTabs:{reset(){tabsReset++;}},GROW:{id:3,stop:()=>{},result:{},errors:[]},SIMQ:{busy:'growth'}});
  vm.runInContext(text.slice(text.indexOf('function growthCancel'),text.indexOf('function growthInit')),cancel);
  cancel.growthCancel();assert.equal(cancel.SIMQ.busy,null);assert.equal(cancel.GROW.result,null);assert.equal(cancel.GROW.id,4);assert.equal(tabsReset,1);assert.equal(removed,1);
}
async function scheduling(){const targets=Array.from({length:4},(_,i)=>({id:'t'+i,key:'u'+i,kind:'growth',source:'assumed',
  candidates:[0,1].map(j=>({id:`t${i}c${j}`})),controls:[{id:'owned'+i}]})),calls=[];
  const evaluate=async(jobs,n,seed)=>{calls.push({jobs,n,seed});return Object.fromEntries(jobs.map(j=>[j.id,{n,clear:j.id==='owned2'?0.8:j.id==='old'?0.1:0.4,prog:0.8,ttk:12,progs:Array(n).fill(.8),via:{}}]));};
  const result=await G.search({targets,owned:[{id:'old',result:{n:100,clear:.1}}],evaluate});
  assert.equal(calls.length,2);assert.notEqual(calls[0].seed,calls[1].seed);
  assert(calls[1].jobs.some(j=>j.id==='owned2'),'new owned baseline retained');
  assert.equal(result.baseline.clear,.8);assert(result.rows.every(r=>r.delta<0&&r.result.n===result.baseline.n&&r.screened===2));
  // A noisy four-run re-search must never evict or overwrite the established winner.
  const adversarial=clone(targets);adversarial[0].controls.push({id:'old'});
  const noisy=async(jobs,n,seed)=>{if(seed===900001)assert(jobs.some(j=>j.id==='old'),'established winner evicted');
    return Object.fromEntries(jobs.map(j=>[j.id,{n,clear:j.id==='old'?(n===4?0:.9):.8,prog:1,ttk:10}]));};
  const kept=await G.search({targets:adversarial,owned:[{id:'old',result:{n:100,clear:.9}}],evaluate:noisy});
  assert.equal(kept.baseline.clear,.9);
  const partial=await G.search({targets:adversarial,owned:[{id:'old',result:{n:100,clear:.9}}],evaluate:async(jobs,n,seed)=>{
    const r=await noisy(jobs,n,seed);if(seed===900001)delete r.old;return r;}});
  assert(partial.baselinePending);assert.equal(partial.baseline,null);assert(partial.rows.every(r=>r.delta===null&&!r.confirmed));
  assert(result.runs<=G.LIMITS.maxRuns);assert.equal(calls[0].jobs[0].id,'t0c0');assert.equal(calls[0].jobs[4].id,'t0c1');
  const manual=await G.search({targets,owned:[],evaluate,mode:'manual',limits:{maxRuns:1100}});
  assert(manual.runs<=1100);assert.equal(G.finalCost(100,'manual'),333);
  const cap=await G.search({targets,owned:[],evaluate,limits:{finalists:1}});
  assert.equal(cap.rows.filter(r=>r.status==='evaluated').length,1);assert(cap.rows.some(r=>r.status==='screened'&&r.delta===null));
  const none=await G.search({targets,owned:[],evaluate:async()=>({})});assert(none.rows.every(r=>r.status==='unevaluated'&&r.delta===null));
  assert.equal(await G.search({targets,owned:[],evaluate,alive:()=>false}),null);
  let db={},writes=0;const storage={get:k=>db[k],set:(k,v)=>{writes++;db[k]=v;return true;}};
  const entry=G.summary(result,'op/1/3','sig','a','v');
  assert.equal(G.save(storage,true,entry),false);assert.equal(writes,0);
  G.save(storage,false,entry);G.save(storage,false,entry);assert.equal(Object.keys(db['growth.history']).length,1);
  assert(!JSON.stringify(db).includes('progs'));assert(!JSON.stringify(db).includes('equip'));
  G.save(storage,false,{...entry,account:'other',content:'clo/1/2'});assert.equal(Object.keys(db['growth.history']).length,1);
  assert(G.compare({clear:0,n:100},{clear:1,n:100}).delta<0);
  assert(G.compare({clear:1,n:100},{clear:0,n:100}).confirmed);
}
(async()=>{generation();signatures();quickOrdering();await scheduling();
  if(process.argv.includes('--mutations')){const original=M.assume;M.assume=(key,i,g,p)=>({...original(key,i,g,p),unit:i.units[0]});
    assert.throws(generation);M.assume=original;generation();
    const sig=G.signature;G.signature=()=>'';assert.throws(signatures);G.signature=sig;signatures();
    const save=G.save;G.save=(s,shared,e)=>save(s,false,e);await assert.rejects(scheduling);G.save=save;await scheduling();
    console.log('MUTATIONS caught + restored: generation, signature, shared storage');}
  console.log('ALL OK assumed guide');})().catch(e=>{console.error(e);process.exitCode=1;});
