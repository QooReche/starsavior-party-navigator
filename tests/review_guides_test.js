// Review regressions use invented accounts; mutations run in memory only.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {createRequire}=require('node:module'),S=require('../myinfo_stats'),G=require('../growth_guide'),L=require('../star_link'),I=require('../myinfo_import');
const growth=require('../data/growth.json'),raw=require('./fixtures/myinfo_synthetic.json');
const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
const source=fs.readFileSync(require.resolve('../myinfo_reco'),'utf8');
function adapter(code=source){const file=require.resolve('../myinfo_reco'),ctx={module:{exports:{}},require:createRequire(file)};
  vm.runInNewContext(code,ctx);return ctx.module.exports;}
const M=adapter();
function fixture(){const info=structuredClone(raw);info.star_link_level=120;
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  info.units=roster.slice(0,8).map(s=>({...structuredClone(M.assume(s.key,{...info,star_link:null,units:[]},growth).unit),level:82}));
  info.star_link={level:120,source:info.units.slice(0,4).map(u=>u.id),slots:info.units.slice(4,6).map((u,index)=>({index,id:u.id}))};
  return info;
}
function sourceLevels(m=M){const info=fixture();
  for(const [i,level] of [[0,121],[1,100],[6,140]]){info.units[i].level=level;const key=roster[i].key;
    for(const fields of [['level'],undefined]){const a=m.assume(key,info,growth,{fields});
      assert.equal(S.effective_level(a.unit,a.targetInfo),level,'source/high own level must be retained');
      assert(!a.targetInfo.star_link.slots.some(s=>s.id===a.unit.id),'must not add virtual source or downgrade slot');
      assert(!a.changedFields.includes('level'));
      assert.equal(a.changes.level.after,level);
    }
  }
  const snapshot=JSON.stringify(info);m.assume(roster[0].key,info,growth);assert.equal(JSON.stringify(info),snapshot);
}
function legacy(m=M){const info=fixture();delete info.star_link;info.units.forEach(u=>delete u.level);
  const key=roster[6].key,u=info.units[6];u.equip=[];u.skills={basic:1,special:1,ultimate:1,passive:1};u.resonance=0;
  u.gauntlet.journey=[0,0,0,0,0];u.gauntlet.potentials=[];
  const before=JSON.stringify(info),base=m.profile(info,roster,growth,'op');
  assert.throws(()=>m.assume(key,info,growth,{fields:['level']}),e=>e.code==='level-data');
  for(const fields of [undefined,G.COMPONENTS.equipment,G.COMPONENTS.skills,G.COMPONENTS.potential]){
    const a=m.assume(key,info,growth,{fields}),r=m.assumedProfile(base,a,info,growth,'op').results[key];
    assert.equal(S.effective_level(a.unit,a.targetInfo),120);
    assert(r.power>base.results[key].power,'non-level changes must actually affect stats');
    assert(!a.changedFields.includes('level'));
  }
  assert.equal(JSON.stringify(info),before);
  delete info.units[6].gauntlet;
  assert.throws(()=>m.assumedProfile(base,m.assume(key,info,growth,{fields:['equip']}),info,growth,'op'),/gauntlet/);
}
const ui=fs.readFileSync(require.resolve('../star_link_ui'),'utf8');
async function isolation(code=ui){const info=fixture();delete info.units[7].gauntlet;let searched=false,candidates=[];
  assert.equal(I.validate(info),'');assert.equal(L.availability(info),'');
  const ctx={MI:{info,growth},R:roster,EXCL:new Set(),D:{},QK:{d:{}},GROW:{id:0},GrowthGuide:G,MyInfoReco:M,
    SIMQ:{busy:null},SLOT:{contexts:new Map([['op/a',{version:'test'}]]),excluded:[]},slotSync(){},slotPaint(){},
    fetch:async()=>({ok:true,json:async()=>({ver:'test'})}),slotEvaluateState(){},
    StarLink:{...L,search:async p=>{searched=true;candidates=p.candidates;return {swaps:[]};}}};
  vm.runInNewContext(code.slice(code.indexOf('async function slotStart'),code.indexOf('function slotPaint')),ctx);
  await ctx.slotStart();assert.equal(ctx.SLOT.phase,'done',ctx.SLOT.msg);assert(searched,'healthy candidates must reach search');
  assert(candidates.includes(info.units[6].id));assert(!candidates.includes(info.units[7].id));
  assert(candidates.every(id=>!info.star_link.source.includes(id)&&!info.star_link.slots.some(s=>s.id===id)));
  assert.equal(ctx.SLOT.excluded.length,1);assert.match(ctx.SLOT.excluded[0].reason,/gauntlet/);
}
function signatures(g=G){const s={account:'a',options:{growth:true},targets:['u'],preset:'p',content:['op','a'],excluded:[],breaks:[],mode:'auto',rules:{},engine:'e',data:'d',modifiers:['x',0]};
  const sig=g.signature(s),other=g.signature({...s,content:['clo','b'],targets:['v']});assert(g.compatible(sig,other));
  const row={key:'u',kind:'growth',confirmed:true,delta:50};const history={a:{signature:sig,rows:[row],content:'op/a',account:'a',version:'v'}};
  assert.equal(g.priority(history,other)[0].count,1);
  let same=history;g.save({get:()=>same,set:(_,v)=>same=v},false,{account:'a',version:'v',content:'clo/b',signature:other,rows:[]});
  assert.equal(Object.keys(same).length,2,'compatible content history must survive');
  assert(g.compatible(sig,g.signature({...s,mode:'manual'})),'legacy mode belongs to content, not common context');
  for(const change of [{excluded:['u']},{breaks:['x']},{rules:{x:1}},{modifiers:['y',1]}]){
    const changed=g.signature({...s,...change});assert.equal(g.priority(history,changed).length,0);
    let value=history;g.save({get:()=>value,set:(_,v)=>value=v},false,{account:'a',version:'v',content:'clo/b',signature:changed,rows:[]});
    assert.equal(Object.keys(value).length,1);
  }
}
async function diagnostics(l=L){for(const empty of [false,true]){const info=fixture();if(empty)info.star_link.slots[0].id=0;
  const calls=[],r=await l.search({info,contexts:[{id:'op/a'}],candidates:[info.units[6].id],evaluate:async p=>{
    calls.push(p);assert.equal(p.info.star_link.slots.length,2);assert.equal(new Set(p.info.star_link.slots.map(s=>s.index)).size,2);
    return {runs:100,metric:{clear:.5,n:100,prog:.8,progs:Array(100).fill(.8),via:{}}};}});
  assert(!r.diagnostics.some(d=>d.kind==='out'&&!d.id));
  assert.equal(calls.filter(c=>!c.focus.length).length,1,'only baseline has empty focus');
  if(!empty)assert(r.diagnostics.some(d=>d.kind==='in'&&d.note==='교환 필요'));
}}
function zero(i=I){const info=fixture();info.star_link_level=info.star_link.level=0;info.units[0].level=0;
  assert.equal(i.validate(info),'');assert.equal(S.effective_level(info.units[0],info),1);assert(L.availability(info));
  info.units[0].level=-1;assert(i.validate(info));
}
(async()=>{sourceLevels();legacy();await isolation();signatures();await diagnostics();zero();
  if(process.argv.includes('--mutations')){
    const revert=source.replace("!info.star_link?.source?.includes(unit.id)","true").replace('(!owned || linkLevel>currentLevel.level)','true');
    assert.notEqual(revert,source);assert.throws(()=>sourceLevels(adapter(revert)),/source\/high own level/);
    const blockLegacy=source.replace('assumed.levelUnknown &&','false &&');assert.notEqual(blockLegacy,source);
    assert.throws(()=>legacy(adapter(blockLegacy)),/가정 자료 미지원/);
    const abort=ui.replace('SLOT.excluded.push({id:s.uid,reason:String(e.message)});','throw e;');assert.notEqual(abort,ui);
    await assert.rejects(()=>isolation(abort),/gauntlet/);
    const guide=fs.readFileSync(require.resolve('../growth_guide'),'utf8');
    assert.throws(()=>signatures(adapter(guide.replace('function compatible(a,b){','function compatible(a,b){return true;'))),assert.AssertionError);
    const slots=fs.readFileSync(require.resolve('../star_link'),'utf8');
    const oversized=slots.replace("if(!id || (kind==='in'&&!slots.includes(0)))continue;",'')
      .replace("const ids=slots.slice();ids[slots.indexOf(kind==='in'?0:id)]=kind==='in'?id:0;","const ids=kind==='in'?[...slots,id]:slots.filter(v=>v!==id);");
    assert.notEqual(oversized,slots);await assert.rejects(()=>diagnostics(adapter(oversized)),assert.AssertionError);
    const importer=fs.readFileSync(require.resolve('../myinfo_import'),'utf8');
    assert.throws(()=>zero(adapter(importer.replace('!int32(s.level,0)','!int32(s.level)'))),assert.AssertionError);
    sourceLevels();legacy();await isolation();console.log('MUTATIONS caught + restored: source slot, legacy component gate, per-savior isolation');
    signatures();await diagnostics();zero();console.log('MUTATIONS caught + restored: incompatible history, slot capacity, zero import');
  }
  console.log('ALL OK review regressions');
})().catch(e=>{console.error(e);process.exitCode=1});
