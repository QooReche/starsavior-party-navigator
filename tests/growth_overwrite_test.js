const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),growth=require('../data/growth.json'),raw=require('./fixtures/myinfo_synthetic.json');
const source=fs.readFileSync(require.resolve('../myinfo_reco'),'utf8'),ui=fs.readFileSync(require.resolve('../growth_ui'),'utf8');
const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
function synthetic(){const info=structuredClone(raw);
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  return info;
}
function overwrite(m=M){const info=synthetic(),before=JSON.stringify(info);
  const r=m.overwrite(info,roster,growth,'op',{includeMissing:false});
  assert.equal(r.errors.length,0);assert(Object.keys(r.changes).length>0);
  assert.equal(r.info.units.length,info.units.length);assert.equal(JSON.stringify(info),before);
  for(const [key,a] of Object.entries(r.changes)){
    const old=info.units.find(u=>u.id===a.unit.id);
    assert(a.overwrite);assert.equal(a.source,'owned');assert(a.unit.resonance>=old.resonance);
    for(const [k,v] of Object.entries(old.skills))assert(a.unit.skills[k]>=v);
    for(const [i,v] of old.gauntlet.journey.entries())assert(a.unit.gauntlet.journey[i]>=v);
    assert(a.unit.equip.every(e=>e.enhance>=15));
    assert.deepEqual(a.changedFields,Object.keys(a.changes).filter(f=>JSON.stringify(a.changes[f].before)!==JSON.stringify(a.changes[f].after)));
    assert(r.profile.results[key].power>0);
  }
  const missing=roster.find(s=>!info.units.some(u=>u.id===s.uid));
  const all=m.overwrite(info,roster,growth,'op',{includeMissing:true});
  assert.equal(all.info.units.length,info.units.length);assert(!all.changes[missing.key]);assert(!all.profile.units[missing.key]);
  const excluded=m.overwrite(info,roster,growth,'op',{includeMissing:true,excluded:[missing.key]});
  assert(!excluded.profile.results[missing.key]);
  // An account already above every target stays byte-for-byte intact.
  const key='luna',target=M.assume(key,{...info,units:[]},growth),u=structuredClone(target.unit);
  u.level=300;u.favor=30;u.resonance=Math.max(...Object.keys(growth.units[u.id].resonance).map(Number));u.gauntlet.journey=[1500,1500,1500,1500,1500];
  u.gauntlet.potentials[0][1]=Math.max(...growth.assumed.combat_support.potentials[u.gauntlet.potentials[0][0]].map(Number));
  u.equip.forEach(e=>{e.enhance=16;e.main.value*=2;});
  const high={...info,units:[u],star_link:{level:120,source:[],slots:[]}};
  const h=m.overwrite(high,roster,growth,'op',{includeMissing:false});
  assert.equal(h.errors.length,0);assert.deepEqual(h.info,high);assert.deepEqual(h.changes,{});
  // Mixed fields: preserve the stronger equipment bundle while raising skills.
  const mixed=structuredClone(high);mixed.units[0].skills.basic=1;mixed.units[0].equip.forEach(e=>e.enhance=12);
  const raised=m.overwrite(mixed,roster,growth,'op',{includeMissing:false});
  assert.equal(raised.errors.length,0);assert.deepEqual(raised.changes[key].changedFields,['skills']);
  assert.deepEqual(raised.info.units[0].equip,mixed.units[0].equip);
  const main=growth.assumed.units[key].journey.indexOf(1250);mixed.units[0].gauntlet.journey[main]=499;
  const archive=m.overwrite(mixed,roster,growth,'op');
  assert.deepEqual(archive.info.units[0].gauntlet.journey,mixed.units[0].gauntlet.journey.map((v,i)=>i===main?1250:v));
}
function display(code=ui){const ctx={GrowthGuide:require('../growth_guide'),esc:s=>s,Ux:require('../ux_ui'),MI:{info:synthetic(),growth},contents:[{key:'op'}],$:()=>({value:0}),D:{archiveGrades:require('../data/archive_grades.json'),growthView:{...require('../data/myinfo_view.json'),itemSlots:require('../data/myinfo_slots.json')}}};vm.createContext(ctx);vm.runInContext(code,ctx);
  for(const [kind,field] of [['op','clear'],['clo','clear'],['guild','score'],['cosmo','sum']]){
    assert(ctx.growthBetter(kind,{[field]:.4},{[field]:.8}),kind);
    assert(!ctx.growthBetter(kind,{[field]:.8},{[field]:.8}),kind+' tie');
    assert(!ctx.growthBetter(kind,{[field]:.8},{[field]:.4}),kind+' lower');
  }
  const r=M.overwrite(synthetic(),roster,growth,'op',{includeMissing:false});
  const labels={level:'스타링크',equip:'장비 +15',skills:'스킬',resonance:'공명',journey:'스텔라 아카이브',potentials:'잠재력'};
  for(const a of Object.values(r.changes)){
    const html=ctx.growthTodoRow(a,a.key);assert(ctx.growthBadge(a,true).includes('키워야 함'));
    assert(ctx.growthCardMeta(a).includes('member-power'));
    for(const [f,label] of Object.entries(labels))assert.equal(html.includes('data-growth-field="'+f+'"'),ctx.growthDisplay(a).fields.some(x=>x.field===f&&x.delta!==0));
  }
}
function load(code){const ctx={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,ctx);
  const raw=ctx.module.exports;return {...raw,overwrite:(...args)=>JSON.parse(JSON.stringify(raw.overwrite(...args)))};}
function mutate(name,code,from,to,test){assert(code.includes(from));let caught=false;
  try{test(code.replace(from,to));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'mutation survived: '+name);console.log('MUTATION caught + restored:',name);
}
overwrite();overwrite(load(source));display();
mutate('original account mutation',source,'const target=clone(info),','const target=info,',s=>overwrite(load(s)));
mutate('missing selection',source,'||!out.units[s.key]','',s=>overwrite(load(s)));
mutate('higher journey preserved',source,'Math.max(v,old.gauntlet?.journey?.[i]||0)','v',s=>overwrite(load(s)));
mutate('higher equipment preserved',source,'if(!(presetPower>originalPower))','if(false)',s=>overwrite(load(s)));
mutate('strict improvement only',ui,'metric(result)>(metric(baseline)??0)','metric(result)>=(metric(baseline)??0)',display);
// Per-field presentation mutation coverage is in ux_ui_test.js.
console.log('ALL OK whole-account overwrite');
async function timeout(code=ui){let active=0;
  const ctx={setTimeout,clearTimeout,SIMQ:{LOAD_MS:5},simTeamLimit:()=>5,
    Worker:class {constructor(){active++;}postMessage(){}terminate(){if(!this.dead){this.dead=true;active--;}}}};
  vm.createContext(ctx);vm.runInContext(code,ctx);
  const handle=require('../guild_search').runPhase({makeWorker:()=>ctx.growthWorker(),workers:2,jobs:[{key:'a',party:{}},{key:'b',party:{}}],runs:4,
    stage:'guild/test/EX',base:'http://example.test/'});
  try{const reason=await Promise.race([handle.promise.then(()=>'completed',e=>e.message),new Promise(ok=>setTimeout(()=>ok('hung'),40))]);
    assert(reason.includes('시간 초과'));assert.equal(active,0);
  }finally{handle.cancel();}
}
async function warmup(code=ui){const ctx={setTimeout,clearTimeout,Date,MODE:'auto',simTeamLimit:()=>5,SIMQ:{LOAD_MS:100},
  GROW:{id:1,errors:[],versions:{engine:'test'}},location:{href:'http://example.test/'},simOpt:()=>({}),growthPaint(){},
  Worker:class {postMessage(req){setTimeout(()=>{if(this.dead)return;
    this.onmessage({data:{id:req.id,type:'stage',msg:'준비 끝'}});
    this.onmessage({data:{id:req.id,type:'team',key:'team',result:{ver:'test',prog:.8,n:req.n_runs,progs:Array(req.n_runs).fill(.8),via:{}}}});
    this.onmessage({data:{id:req.id,type:'done'}});},25);}terminate(){this.dead=true;}}};
  vm.createContext(ctx);   // 작업자 풀·대기열은 화면 것 그대로(navigator 없음 = 작업자 1개)
  const page=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
  vm.runInContext(page.slice(page.indexOf('// ── 작업자 풀·작업 대기열'),page.indexOf('// 이 기기의 시뮬 속도')),ctx);
  vm.runInContext(code.slice(code.indexOf('function growthEvaluate'),code.indexOf('function growthMaybe')),ctx);
  const r=await ctx.growthEvaluate([{id:'team',party:{}}],8,1,{key:'op'},{tab:'a',name:'b'},1,Infinity,{screenClock:{deadline:null}});
  assert(!r.incomplete&&r.team?.prog>0,'engine preparation must use the load limit, not the short no-progress limit');ctx.SIMQ.w?.terminate();
}
(async()=>{await warmup();await timeout();let caught=false;
  try{await timeout(ui.replace("timer=setTimeout(()=>wrapper.onerror?.({message:'시간 초과'})","timer=setTimeout(()=>{}"));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'timeout mutation survived');console.log('MUTATION caught + restored: seasonal worker timeout');
  caught=false;
  try{await warmup(ui.replace("stall.ready?simTeamLimit(n,'auto'):SIMQ.LOAD_MS","true?simTeamLimit(n,'auto'):SIMQ.LOAD_MS"));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'warmup mutation survived');console.log('MUTATION caught + restored: screening warmup budget');
})().catch(e=>{console.error(e);process.exitCode=1;});
