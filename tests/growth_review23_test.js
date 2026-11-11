// Review regressions exercise production UI signatures, persistence and scheduling.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const G=require('../growth_guide'),GS=require('../guild_search'),V=require('../guild_view'),D=require('../data/guild_defense.json');
const ui=fs.readFileSync(require.resolve('../growth_ui'),'utf8'),source=fs.readFileSync(require.resolve('../growth_guide'),'utf8');
function context(code=ui,storage={}){
  const ctx={GrowthGuide:G,GuildView:V,MI:{hash:'synthetic',info:{},growth:{assumed:{version:'test'}}},
    CFG:{restrict:{}},R:[],EXCL:new Set(),MODE:'auto',MM:'myinfo',SCROWN:0,BRSEL:{},SESSION_BR:{},
    SIMOPT:{build:'standard'},GS:{sel:{level:0,tiers:[0,0,0,0]}},GSR:{rows:[],banCoop:true},
    CSR:{rows:[],optLevel:0,optMode:'top',optFast:false},D:{guild:D,cosmoRaid:{season:'test',bosses:['a','b','c'].map(key=>({key})),search:{}}},
    document:{getElementById:id=>id==='assume-growth'?{checked:true}:{value:'all'}},
    LS:{get:k=>storage[k],set:(k,v)=>(storage[k]=JSON.parse(JSON.stringify(v)),true)},
    miProfile:()=>({units:{}}),MyInfoReco:{profile:()=>({units:{}})},breakOwned:()=>[],csProfile:()=>({})};
  ctx.simOpt=key=>({...ctx.SIMOPT,...(key==='op'?{rekindle:1}:{})});
  vm.createContext(ctx);vm.runInContext(code,ctx);
  vm.runInContext("GROW.versions={engine:'engine',data:'data'}",ctx);
  return ctx;
}
const stage={tab:'tab',name:'stage'},content=key=>({key,name:key});
function save(ctx,key,name=stage.name){const sig=ctx.growthSig(content(key),{...stage,name});
  G.save(ctx.LS,false,{signature:sig,content:key+'/'+name,account:ctx.MI.hash,version:'engine|data',at:Date.now(),
    rows:[{key:'x',kind:'growth',delta:1,confirmed:true}]});return sig;}
function historyOp(code=ui){const ctx=context(code),old=save(ctx,'op','first');
  ctx.GSR.rows=[{keys:['a','b','c','d'],sup:'gust',level:0}];ctx.GS.sel.level=3;ctx.GSR.banCoop=false;
  save(ctx,'op','second');assert(ctx.LS.get('growth.history')['op/first'],'guild memory must not purge earlier op');
  assert.equal(ctx.growthSig(content('op'),{...stage,name:'first'}),old,'op exact signature ignores guild state');
}
function historySeason(code=ui){const ctx=context(code);save(ctx,'guild');
  ctx.CSR.rows=[{teams:[{boss:'a',keys:['e','f','g','h'],level:2}]}];ctx.CSR.optLevel=2;ctx.CSR.optMode='mean';ctx.CSR.optFast=true;
  save(ctx,'cosmo');assert(ctx.LS.get('growth.history')['guild/stage'],'cosmo search must not purge guild');
  const p=G.priority(ctx.LS.get('growth.history'),ctx.growthSig(content('cosmo'),stage));assert.equal(p[0].count,2);
}
function historyReload(code=ui){const storage={},ctx=context(code,storage);
  ctx.GSR.rows=[{keys:['a','b','c','d'],sup:'gust',level:0}];
  ctx.CSR.rows=[{teams:[{boss:'a',keys:['e','f','g','h'],level:0}]}];save(ctx,'guild');save(ctx,'cosmo');
  // Restore independent snapshots so the reload assertion also covers the old purge bug.
  const guild=ctx.LS.get('growth.history')['guild/stage'];assert(guild);
  const refreshed=context(code,storage);save(refreshed,'op');
  assert(refreshed.LS.get('growth.history')['guild/stage'],'reload/op must retain guild');
  assert(refreshed.LS.get('growth.history')['cosmo/stage'],'reload/op must retain cosmo');
}
function signatureScope(code=ui){const ctx=context(code),sig=key=>ctx.growthSig(content(key),stage);
  const op=sig('op'),guild=sig('guild'),cosmo=sig('cosmo');
  assert(G.compatible(op,guild)&&G.compatible(guild,cosmo),'content options are not common rules');
  ctx.GSR.rows.push({keys:['a','b','c','d']});assert.notEqual(sig('guild'),guild);assert.equal(sig('op'),op);assert.equal(sig('cosmo'),cosmo);
  const changed=sig('guild');ctx.CSR.optLevel++;assert.equal(sig('guild'),changed);assert.notEqual(sig('cosmo'),cosmo);
  const before=sig('cosmo');assert.equal(ctx.growthSig(content('cosmo'),{tab:'another boss',name:'another stage'}),before,'view-only boss tab');
  for(const field of ['season','difficulty','banCoop','ranking','teams']){
    const parsed=JSON.parse(changed),next=structuredClone(parsed);next[4].at(-1)[field]='changed';
    assert.notEqual(JSON.stringify(next),changed);assert(G.compatible(changed,JSON.stringify(next)),field);
  }
  for(const mutate of [()=>ctx.MI.hash='other',()=>ctx.EXCL.add('excluded'),()=>ctx.SIMOPT.build='other',
    ()=>ctx.document.getElementById=()=>({checked:false,value:'missing'}),()=>vm.runInContext("GROW.versions.engine='other'",ctx),
    ()=>vm.runInContext("GROW.versions.data='other'",ctx)]){const before=sig('op');mutate();assert(!G.compatible(before,sig('op')));}
}
async function missingBoss(code=ui){const ctx=context(code);
  for(const teams of [undefined,[],[{boss:'a',keys:['a','b','c','d'],level:0}],
    ['a','a','c'].map(boss=>({boss,keys:['a','b','c','d'],level:0}))]){
    ctx.CSR.rows=[{teams}];await assert.rejects(ctx.growthCosmo(content('cosmo'),stage,0,Date.now()+1000),/보유 탐색 먼저/);
  }
}
async function exactControls(code=ui){const ctx=context(code),keys=['x','a','b','c','d'];
  ctx.R=keys.map(key=>({key,cls:'test'}));ctx.BYKEY=Object.fromEntries(ctx.R.map(s=>[s.key,s]));
  ctx.CFG.weights={defenderPenalty:0};ctx.CFG.defPenByContent={};ctx.partyPool=rows=>rows;ctx.partySyn=()=>[];
  ctx.score=()=>[0,[]];ctx.setTimeout=setTimeout;
  ctx.growthTeam=combo=>({combo,keys:combo.map(x=>x.s.key),v:combo.some(x=>x.s.key==='x')?0:10});
  ctx.growthQuickCmp=(a,b)=>b.v-a.v;
  const original={results:Object.fromEntries(keys.map(k=>[k,{}]))};
  const targets=await ctx.growthCandidates(content('guild'),stage,()=>true,Date.now()+1000,
    {original,profile:original,qi:null,exactControls:true,targets:[{id:'x',key:'x'}],makeJob:(t,id)=>({id,t,keys:t.keys})});
  assert(targets[0].candidates.length>0);assert(targets[0].controlsComplete);
  for(const c of targets[0].candidates)assert(targets[0].controls.some(j=>j.keys.slice().sort().join()===c.keys.slice().sort().join()),
    'owned target must retain its own same-companion control even when approximations prefer another owner');
}
async function workerProgs(code=fs.readFileSync(require.resolve('../sim_worker'),'utf8')){
  const messages=[],ctx={URL,self:{location:{href:'https://example.test/sim_worker.js'}},postMessage:m=>messages.push(m)};
  vm.createContext(ctx);vm.runInContext(code,ctx);
  const p={globals:{get:name=>name==='run_auto'?(_stage,_party,n)=>JSON.stringify({n,prog:.8,progs:Array(n).fill(.8),via:{trigger:1}}):()=>{}},toPy:x=>x};
  ctx.testEngine={p,ver:'test'};vm.runInContext('ready=Promise.resolve(testEngine)',ctx);
  for(const n of [4,100]){messages.length=0;await ctx.onmessage({data:{type:'run',id:n,stage:'guild/test/EX',n_runs:n,seed:1,
    teams:[{key:'guild',party:{units:[]},options:{guild:{level:0}}}]}});
    assert(!messages.some(m=>m.type==='error'));const result=messages.find(m=>m.type==='team')?.result;
    assert(result?.prog>0);assert.equal(result.progs?.length,n);assert.equal(result.via.trigger,1);
    const metric=G.guildMetric(GS,V,D,0,[]).prepare(result);assert(metric?.top>0);assert.equal(metric.scores.length,n);
  }
}
async function controls(g=G){const metric=g.guildMetric(GS,V,D,0,[]),calls=[],targets=[{id:'x',key:'x',kind:'growth',
  candidates:[{id:'assumed'}],controls:Array.from({length:4},(_,i)=>({id:'control'+i}))}],
  owned=[{id:'old',result:metric.prepare({n:100,clear:0,prog:.6,progs:Array(100).fill(.6)})}];
  const evaluate=async(jobs,n,seed)=>{calls.push({jobs,n,seed});return Object.fromEntries(jobs.map(j=>{
    const p=j.id==='assumed'||(j.id==='control3'&&n===100)?.9:j.id==='control3'?.1:.6;
    return [j.id,metric.prepare({n,prog:p,clear:0,progs:Array(n).fill(p),via:{}})];}));};
  const result=await g.search({targets,owned,metric,evaluate});
  assert(result.rows[0].result?.prog>0);assert.equal(result.rows[0].delta,0,'same companions/control discovery cannot masquerade as growth');
  for(const j of targets[0].controls)assert(calls[1].jobs.some(x=>x.id===j.id),'all controls need 100 runs');
  assert.equal(calls[1].n,100);assert.equal(new Set(calls[1].jobs.map(j=>j.id)).size,calls[1].jobs.length);assert(result.runs<=7200);
  const partial=await g.search({targets,owned,metric,evaluate:async(jobs,n,seed)=>{
    const out=await evaluate(jobs,n,seed);if(n===100)delete out.control3;return out;}});
  assert.equal(partial.rows[0].delta,null);assert.equal(partial.rows[0].result,null);assert.notEqual(partial.rows[0].status,'evaluated');
  const limited=await g.search({targets,owned,metric,evaluate,limits:{maxRuns:350}});
  assert(limited.runs<=350);assert.equal(limited.rows[0].delta,null);
  const unfinished=await g.search({targets:[{...targets[0],controlsComplete:false}],owned,metric,evaluate});
  assert.equal(unfinished.rows[0].result,null,'deadline during control generation');
}
function load(code){const ctx={module:{exports:{}}};vm.runInNewContext(code,ctx);return ctx.module.exports;}
async function mutation(name,code,from,to,test){assert(code.includes(from),name);let caught=false;
  try{await test(code.replace(from,to));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'mutation survived: '+name);console.log('MUTATION caught + restored:',name);
}
(async()=>{
  historyOp();historySeason();historyReload();signatureScope();await missingBoss();await exactControls();await workerProgs();await controls();
  for(const [name,test] of [['op history',historyOp],['season history',historySeason],['reload history',historyReload]])
    await mutation(name,ui,'policy:[GrowthGuide.VERSION','policy:[JSON.stringify([GS.sel,GSR,CSR]),GrowthGuide.VERSION',test);
  await mutation('boss tab',ui,"(c.key==='cosmo'?[]:[st.tab,st.name])",'[st.tab,st.name]',signatureScope);
  await mutation('boss guard',ui,"throw Error('보유 탐색 먼저 · 보스 3개 기준 편성 필요')","throw Error('missing baseline')",missingBoss);
  await mutation('exact owned control',ui,'config.exactControls&&original.results[target.key]','false',exactControls);
  await mutation('worker progs',fs.readFileSync(require.resolve('../sim_worker'),'utf8'),
    'key:t.key,result:res','key:t.key,result:{...res,progs:null}',workerProgs);
  await mutation('guild controls reservation',source,'[t.best,mean,cap,...(t.controls||[])]','[t.best,mean,cap]',s=>controls(load(s)));
  await mutation('guild controls completion',source,'selected.has(t.id)&&(t.controls||[]).every(j=>fr[j.id])','selected.has(t.id)',s=>controls(load(s)));
  await mutation('guild final baseline',source,'const finalOwned=metric?[...owned,...targets.flatMap(t=>t.controls||[])]:bestOwned','const finalOwned=bestOwned',s=>controls(load(s)));
  historyOp();historySeason();historyReload();signatureScope();await missingBoss();await exactControls();await workerProgs();await controls();
  console.log('ALL OK growth review23');
})().catch(e=>{console.error(e);process.exitCode=1;});
