const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),S=require('../myinfo_stats'),G=require('../growth_guide'),L=require('../star_link');
const growth=require('../data/growth.json'),raw=require('./fixtures/myinfo_synthetic.json');
const clone=x=>structuredClone(x),roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
function fixture(){const info=clone(raw);info.star_link_level=240;
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  info.units=roster.slice(0,8).map(s=>({...M.assume(s.key,{...info,units:[]},growth).unit,level:82}));
  info.star_link={level:240,source:info.units.slice(0,4).map(u=>u.id),slots:info.units.slice(4,6).map((u,index)=>({index,id:u.id}))};
  return info;}
function bundle(){const info=fixture(),key=roster[6].key,u=info.units[6];
  u.resonance=0;u.equip=[];u.skills={basic:1,special:1,ultimate:1,passive:1};u.gauntlet.journey=[0,0,0,0,0];u.gauntlet.potentials=[];
  const before=JSON.stringify(info),base=M.profile(info,roster,growth,'op'),all=M.assume(key,info,growth);
  const p=M.assumedProfile(base,all,info,growth,'op');
  assert.equal(S.effective_level(all.unit,all.targetInfo),240);assert.equal(S.effective_level(u,info),82);
  assert(all.changedFields.includes('level'));assert(all.changedFields.includes('equip'));assert(all.changedFields.includes('skills'));
  assert(p.results[key].power>base.results[key].power);
  for(const [component,fields] of Object.entries(G.COMPONENTS)){
    const a=M.assume(key,info,growth,{fields});
    assert(a.changedFields.every(f=>fields.includes(f)),component);
    const r=M.assumedProfile(base,a,info,growth,'op').results[key];assert(r.power>base.results[key].power,component);
    if(component!=='level')assert.equal(S.effective_level(a.unit,a.targetInfo),82);
    if(component!=='equipment')assert.deepEqual(a.unit.equip,u.equip);
    if(component!=='skills')assert.deepEqual(a.unit.skills,u.skills);
    if(component==='level')assert.deepEqual(a.unit,u,'slot registration does not rewrite own level');
  }
  const missing=roster.find(s=>!info.units.some(u=>u.id===s.uid)),a=M.assume(missing.key,info,growth);
  assert.equal(S.effective_level(a.unit,a.targetInfo),240);
  assert.equal(M.assumedProfile(base,a,info,growth,'cosmo').results[a.key].breakdown,undefined);
  assert.deepEqual(M.assumedProfile(base,a,info,growth,'cosmo').results[a.key],S.final_stats(a.unit,info,growth,'fixed200'));
  assert.equal(JSON.stringify(info),before);
  const absent=clone(info);delete absent.units[6].gauntlet;
  const onlyLevel=M.assume(key,absent,growth,{fields:['level']});
  assert.equal(onlyLevel.unit.gauntlet,undefined,'a level comparison must not fabricate journey/potentials');
  assert.throws(()=>M.assumedProfile(base,onlyLevel,absent,growth,'op'),/gauntlet/);
  const complete=M.assume(key,absent,growth);
  assert(M.assumedProfile(base,complete,absent,growth,'op').results[key].power>0);
  assert.deepEqual(G.options({equipment:true}),{growth:false,owned:true});
  assert.deepEqual(G.options({growth:true,equipment:false},{ae:false}),{growth:true,owned:true});
  const template=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
  assert(!template.includes('id="assume-equipment"'));assert(template.includes('id="assume-growth"> 클리어 추천 육성'));
}
async function components(){const t={id:'bundle',key:'u',kind:'growth',source:'owned',candidates:[{id:'bundle'}]};
  const targets=[t,...Object.keys(G.COMPONENTS).map(component=>({...t,id:component,parentId:t.id,component,candidates:[{id:component}]}))];
  const values={base:.7,bundle:.9,level:.8,equipment:.2,skills:.85,potential:.75};
  const r=await G.search({targets,owned:[{id:'base',result:{clear:.7,n:100}}],evaluate:async(jobs,n)=>Object.fromEntries(jobs.map(j=>[j.id,
    {clear:values[j.id],n,prog:.9,progs:Array(n).fill(.9),via:{},ttk:8}]))});
  assert.equal(r.rows.filter(x=>x.component).length,4);
  assert(r.rows.every(x=>x.result&&x.result.prog>0));
  assert(Math.abs(r.rows.find(x=>x.id==='bundle').delta-20)<1e-9);
  assert(Math.abs(r.rows.find(x=>x.id==='equipment').delta+50)<1e-9,'negative must survive');
  assert.equal(G.summary(r,'op/test','s','a','v').rows.length,1);
}
async function slots(){const info=fixture(),before=JSON.stringify(info),incoming=info.units[6].id,outgoing=info.units[4].id;
  assert.equal(L.availability(info),'');assert.equal(L.availability({...info,star_link:null}),'다시 불러오기 필요');
  const ctx=[{id:'op/test'},{id:'clo/test'}],calls=[];
  const evaluate=async({info,context,remaining})=>{const ids=info.star_link.slots.map(s=>s.id);calls.push({ids,context:context.id});
    assert(remaining>=100);const clear=ids.includes(incoming)?(ids.includes(outgoing)?.85:.95):.1;
    return {runs:100,metric:{clear,n:100,prog:.8,progs:Array(100).fill(.8),via:{},ttk:10}};};
  const r=await L.search({info,contexts:ctx,candidates:[incoming,info.star_link.source[0]],evaluate});
  assert.equal(r.slots.length,2);assert.equal(r.swaps.length,1);assert.equal(r.swaps[0].in,incoming);assert.equal(r.swaps[0].out,outgoing);
  assert(r.diagnostics.some(d=>d.kind==='in'));assert(r.diagnostics.some(d=>d.kind==='out'));assert.equal(L.count(r.rows),2);
  assert(r.swaps[0].rows.every(r=>r.confirmed));assert(calls.every(c=>['op/test','clo/test'].includes(c.context)));
  assert.equal(JSON.stringify(info),before);assert(r.runs<=L.LIMITS.maxRuns);
  const uncertain=await L.search({info,contexts:ctx,candidates:[incoming],evaluate:async()=>({runs:100,metric:{clear:.5,n:100}})});
  assert.equal(uncertain.swaps.length,0);assert(uncertain.diagnostics.every(d=>d.rows.every(r=>!r.confirmed)));
  const missing=await L.search({info,contexts:ctx,candidates:[incoming],evaluate:async({context})=>({runs:100,metric:context.id==='op/test'?{clear:.8,n:100}:null})});
  assert.equal(missing.swaps.length,0);assert(missing.limited);
  const capped=await L.search({info,contexts:ctx,candidates:[incoming],evaluate,limits:{maxRuns:200}});
  assert.equal(capped.runs,200);assert(capped.limited);assert.equal(capped.swaps.length,0);
  assert.equal(await L.search({info,contexts:ctx,candidates:[incoming],evaluate,alive:()=>false}),null);
  assert(L.rank([{content:'op/test',delta:1,confirmed:true},{content:'clo/test',delta:2,confirmed:true}],
    [{content:'op/test',delta:100000,confirmed:true},{content:'clo/test',delta:0,confirmed:false}])<0);
  const discovered=await L.search({info,contexts:ctx,candidates:[incoming],evaluate:async()=>({runs:100,paired:true,
    metric:{clear:.99,n:100},controlMetric:{clear:.99,n:100}})});
  assert.equal(discovered.swaps.length,0,'finding a better team is not a slot improvement');
  const budget=await L.search({info,contexts:[{id:'op/a'},{id:'clo/b'},{id:'equip/c'},{id:'cube/d'}],
    candidates:[incoming,...Array.from({length:7},(_,i)=>9001+i)],evaluate:async({info})=>({runs:300,
      metric:{clear:info.star_link.slots.some(s=>s.id===incoming)?.99:.01,n:100}})});
  assert(budget.pairs>0&&budget.swaps.length>0,'diagnostics must not consume the whole exchange budget');
  assert(budget.runs<=12000);
  const two=info.units.slice(6).map(u=>u.id),value=i=>.05+.45*i.star_link.slots.filter(s=>two.includes(s.id)).length;
  const repeated=await L.search({info,contexts:[{id:'op/two'}],candidates:two,evaluate:async({info,referenceInfo})=>({runs:100,paired:true,
    metric:{clear:value(info),n:100},controlMetric:{clear:value(referenceInfo),n:100}})});
  assert.equal(repeated.swaps.length,2);assert.deepEqual(new Set(repeated.slots),new Set(two));
  assert(Math.abs(repeated.rows[0].delta-90)<1e-9,'final comparison must use original slots');
}
function scoring(){const text=fs.readFileSync(require.resolve('../growth_ui.js'),'utf8'),ctx=vm.createContext({GIMACT:['old'],SBACT:[1],DMW:[2]});
  vm.runInContext(text.slice(text.indexOf('function growthScoreEnv'),text.indexOf('function growthTeam')),ctx);
  const env={gim:['a'],season:[3],damage:[4]};
  assert.equal(ctx.growthScoreEnv(env,()=>ctx.GIMACT[0]),'a');assert.equal(ctx.GIMACT[0],'old');
  assert.throws(()=>ctx.growthScoreEnv(env,()=>{throw Error('cancel')}));assert.equal(ctx.DMW[0],2);
}
(async()=>{bundle();scoring();await components();await slots();
  if(process.argv.includes('--mutations')){
    const assume=M.assume;M.assume=(k,i,g,p)=>assume(k,i,g,p||{fields:['skills']});assert.throws(bundle);M.assume=assume;bundle();
    const search=G.search;G.search=async p=>{const r=await search(p);r.rows.forEach(x=>x.delta=Math.max(0,x.delta));return r;};
    await assert.rejects(components);G.search=search;await components();
    const slotSearch=L.search;L.search=async p=>({...await slotSearch(p),swaps:[]});await assert.rejects(slots);L.search=slotSearch;await slots();
    console.log('MUTATIONS caught + restored: bundle, negative contribution, slot exchange');
  }
  console.log('ALL OK bundle + slots');
})().catch(e=>{console.error(e);process.exitCode=1});
