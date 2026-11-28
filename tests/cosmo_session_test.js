// Real page adapters and search policies, with deterministic synthetic workers.
// No engine download, account data, DOM renderer, or frozen expectation changes.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {createRequire}=require('node:module'),{performance}=require('node:perf_hooks');
const {harness}=require('./guild_daily_page_test'),{fixture}=require('./guild_daily_test');
const read=f=>fs.readFileSync(require.resolve('../'+f),'utf8'),plain=x=>JSON.parse(JSON.stringify(x));
const template=read('party_template.html'),executor=read('search_executor.js'),cosmo=read('cosmo_search.js'),dailyPage=read('guild_daily_page.js');
const daily=read('guild_daily.js');
function setup({templateSource=template,executorSource=executor,cosmoSource=cosmo,pageSource=dailyPage,dailySource=daily}={}){
  const {c,elements}=harness(pageSource),f=fixture(12),events={},fetches=[];
  const life={created:0,active:0,max:0,requests:0},trace=[];
  c.engine='engine-a';c.D.guild=f.G;c.R=f.roster;c.MI.profiles.op={results:f.results};c.MI.profiles.cosmo={results:f.results};
  c.SIMQ.LOAD_MS=60000;
  const S=structuredClone(require('../data/cosmo_raid.json').search);
  Object.assign(S,{learned:{value:false},workers:{min:1,max:1},screen:{runs:2,firstRuns:1,passFrac:.1,passMinMult:1},
    rerank:{keep:20,runs:3},combine:{topTriples:2,show:2},final:{...S.final,runs:4},placement:{enabled:false,baseline:false}});
  c.D.cosmoRaid={search:S,season:{id:1023},dataVersion:'synthetic',levelMax:2,
    bosses:['a','b','c'].map(key=>({key,name:key,sim:true}))};
  Object.assign(c.CSR,{id:0,optLevel:1,optMode:'mean',optLearned:false});
  Object.assign(c,{performance,setTimeout,clearTimeout,scrWorkers:()=>1,simTeamLimit:()=>60000,
    searchPlacementTag:()=>[],growthOwnedContext:()=>({}),growthPaint(){},searchGwenPaint(){}});
  c.document.querySelector=()=>null;
  elements['cosmo-search']={addEventListener:(name,fn)=>{events[name]=fn;}};
  c.fetch=async(url,options)=>{fetches.push({url,options});return {ok:true,json:async()=>({ver:c.engine})};};
  c.Worker=class{
    constructor(){life.created++;life.active++;life.max=Math.max(life.max,life.active);}
    terminate(){if(!this.dead){this.dead=true;life.active--;}}
    postMessage(m){life.requests++;trace.push(plain(m));setImmediate(()=>{
      if(this.dead)return;
      const send=data=>this.onmessage({data:{...m,...data}});
      if(c.failWorker){this.onerror({message:'synthetic worker error'});return;}
      send({type:'stage',msg:'준비 끝'});
      for(const t of m.teams){
        if(this.dead)return;
        const prior=JSON.parse(t.options?.merge_raw||'[]'),raw=prior.concat(Array.from({length:m.n_runs},()=>['wipe',10,20,.6,900]));
        const raid=t.options?.cosmo_raid;
        const boss=raid?['a','b','c'].indexOf(raid.boss):0;
        const score=100+t.party?.units.reduce((n,u)=>n+(Math.floor(Number(u.key.slice(1))/4)===boss?100:0),0)||100;
        send({type:'team',key:t.key,result:{n:raw.length,prog:.6,progs:raw.map(r=>r[3]),clear:0,via:{trigger:1},
          guild:{base_scores:raw.map(r=>r[4])},raw:JSON.stringify(raw),cosmo:{mean:score,top:score+2,clear:0,frac:.6,n:m.n_runs}}});
        c.afterTeam?.();
      }
      if(!this.dead)send({type:'done'});
    });}
  };
  vm.runInContext(executorSource,c);
  function module(file,source=read(file)){
    const mod={exports:{}},requireFile=createRequire(require.resolve('../'+file));
    const requireLocal=name=>name==='./search_executor.js'?c.SearchExecutor:name==='./cosmo_search.js'?c.CosmoSearch:
      name==='./guild_daily.js'?c.GuildDaily:requireFile(name);
    vm.runInContext('(function(require,module){'+source+'\n})',c,{filename:file})(requireLocal,mod);
    return mod.exports;
  }
  c.CosmoSearch=module('cosmo_search.js',cosmoSource);c.GuildDaily=module('guild_daily.js',dailySource);c.GuildPlanner=module('guild_planner.js');
  c.GuildView=require('../guild_view');
  const options=c.guildDailyOptions;
  c.guildDailyOptions=()=>({...options(),nowMs:Date.parse('2026-11-26T05:00:00+09:00'),workers:1});
  const start=templateSource.indexOf('const CSR='),end=templateSource.indexOf('$("content").innerHTML=',start);
  assert(start>=0&&end>start);
  const section=templateSource.slice(start,end).replace(/^const CSR=[^\n]+\n/,'');
  vm.runInContext(section,c);
  c.renderCosmoSearch=()=>{};c.csTick=()=>{};c.ownedSimBreaks=()=>[];
  const poolStart=templateSource.indexOf('const SIM_EXEC=SearchExecutor.shared('),poolEnd=templateSource.indexOf('const SIMPOOL=',poolStart);
  assert(poolStart>=0&&poolEnd>poolStart);
  vm.runInContext(templateSource.slice(poolStart,poolEnd)+'this.shared=SIM_EXEC;this.simPoolTrimIdle=()=>SIM_EXEC.trimIdle();',c);
  return {c,life,trace,fetches,events,close(){c.csSessionRelease?.();c.guildDailyRelease();c.shared.drop();c.shared.trimIdle();}};
}
async function search(c){
  await c.cosmoSearchStart();assert.equal(c.CSR.phase,'done',c.CSR.msg);
  assert(c.CSR.rows.length&&c.CSR.rows[0].sum>0,'search evaluates nonempty positive results');
  assert(c.CSR.rows[0].teams.every(t=>t.st.frac>0),'synthetic battle progresses');
  return plain(c.CSR.rows);
}
async function guild(c){await c.guildDailyStart();assert.equal(c.GSR.phase,'done',c.GSR.msg);assert(c.GSR.sum>0);}
function recommend(c){return new Promise((resolve,reject)=>c.shared.dispatch(c.shared.reserve(1),[{}],{
  id:1,live:()=>true,msg:()=>({type:'run',n_runs:1,teams:[{key:'reco',options:{}}]}),
  team:(job,m)=>assert(m.result.progs[0]>0),done:resolve,error:reject}));}
async function reuse(sources){
  const h=setup(sources),{c,life,fetches}=h;
  try{
    const rows=await search(c);
    assert.equal(life.active,1,'finished cosmo retains its worker');assert.equal(life.created,1);
    const session=c.CSR.session,first=session.pool.get(0);
    assert.deepEqual(await search(c),rows);assert.equal(c.CSR.session,session);
    assert.equal(life.created,1,'identical restart creates zero workers');assert.equal(session.pool.get(0),first);
    c.CSR.optMode='top';await search(c);assert.equal(life.created,1,'condition-only restart creates zero workers');
    c.CSR.optMode='mean';c.engine='engine-b';assert.deepEqual(await search(c),rows);
    assert(first.dead,'engine-only deployment terminates old cosmo worker');assert.equal(life.created,2);
    assert.equal(life.active,1);assert.equal(life.max,1);
    assert.equal(fetches.length,4);assert(fetches.every(f=>f.url==='sim/manifest.json'&&f.options.cache==='no-cache'));
    c.fetch=async()=>({ok:false});await c.cosmoSearchStart();assert.equal(c.CSR.phase,'err');
    assert.equal(life.active,0,'manifest failure closes retained cosmo worker');
  }finally{h.close();}
}
async function growthVersion(kind,version,sources){
  const h=setup(sources),{c,life,trace}=h;
  const state=kind==='cosmo'?c.CSR:c.GSR,profile=c.MI.profiles[kind==='cosmo'?'cosmo':'op'];
  const data=kind==='cosmo'?c.D.cosmoRaid:c.D.guild;
  const label=kind+' growth '+version;
  let guildInput;
  const planner=c.GuildPlanner.search;
  c.GuildPlanner.search=cx=>{guildInput=cx;return planner(cx);};
  // Guild's page resets even with profileOverride. Re-enter its real planner
  // with the captured page input to exercise the retained session without reset.
  const run=async()=>{
    let out;
    if(kind==='cosmo')out=await c.cosmoSearchStart(state,profile);
    else if(!guildInput)out=await c.guildDailyStart(state,profile);
    else out=await planner({...guildInput,engineVersion:c.engine});
    assert.equal(state.phase,'done',state.msg);
    assert(out?.rows.length>0,label+' evaluates results');
    if(kind==='cosmo')assert(out.rows[0].teams.every(t=>t.st.frac>0),label+' battle progresses');
    const sum=kind==='cosmo'?out.rows[0].sum:out.sum;
    assert(sum>0,label+' positive score');
    return plain({rows:out.rows,sum});
  };
  const games=()=>trace.reduce((n,m)=>n+m.n_runs*m.teams.length,0);
  try{
    const initial=await run(),session=state.session,first=session.pool.get(0),initialGames=games();
    assert(initialGames>0,label+' initially dispatches battles');
    assert([...session.caches.values()].some(cache=>cache.size>0),label+' populates cache');
    const requests=life.requests;
    assert.deepEqual(await run(),initial,label+' unchanged results');
    assert.equal(state.session,session,label+' retains session');
    assert.equal(life.requests,requests,label+' unchanged version reuses all battles');
    if(version==='engine')c.engine='engine-b';else data.dataVersion='synthetic-b';
    const changed=await run();
    assert.equal(games()-initialGames,initialGames,label+' version change recomputes every battle');
    assert.equal(changed.sum,initial.sum,label+' deterministic score unchanged');
    assert(first.dead,label+' version change retires loaded worker');
    const refreshed=life.requests;
    assert.deepEqual(await run(),changed,label+' refreshed results');
    assert.equal(life.requests,refreshed,label+' refreshed cache is reusable');
  }finally{h.close();}
}
async function handoff(sources){
  const h=setup(sources),{c,life}=h;
  try{
    const rows=await search(c),first=c.CSR.session;await guild(c);
    assert(first.closed,'guild creation closes idle cosmo session');assert.equal(life.active,1);assert.equal(life.max,1);
    const gs=c.GSR.session;assert.deepEqual(await search(c),rows);
    assert(gs.closed,'cosmo creation closes idle guild session');assert.equal(life.active,1);assert.equal(life.max,1);
    const cs=c.CSR.session;await recommend(c);assert(cs.closed,'shared creation closes idle cosmo session');
    assert.equal(life.active,1);assert.equal(life.max,1);
    assert.deepEqual(await search(c),rows);assert.equal(c.shared.state.workers.length,0);assert.equal(life.max,1);
    await guild(c);const gs2=c.GSR.session;await recommend(c);
    assert(gs2.closed,'shared creation closes idle guild session');assert.equal(life.active,1);assert.equal(life.max,1);
    // A page run awaiting profile loading already owns its retained pool.
    await search(c);const running=c.CSR.session;let release;
    c.miGrowth=()=>new Promise(resolve=>{release=resolve;});
    const pending=c.cosmoSearchStart();assert.equal(c.CSR.phase,'run');
    await recommend(c);const survived=c.CSR.session===running&&!running.closed;
    release({});await pending;assert(survived,'shared creation keeps running cosmo session');
    assert.equal(c.CSR.phase,'done',c.CSR.msg);
    const grown={...c.CSR,phase:'idle'},retained=c.CSR.session;
    const growthPending=c.cosmoSearchStart(grown,c.MI.profiles.cosmo);
    assert.equal(c.CSR.phase,'done');assert.equal(grown.phase,'run');
    await recommend(c);const growthSurvived=c.CSR.session===retained&&!retained.closed;
    let growthFailure;release({});await growthPending.catch(e=>{growthFailure=e;});
    assert(growthSurvived,'shared creation keeps active growth target session despite completed global phase');
    if(growthFailure)throw growthFailure;
    assert.equal(grown.phase,'done',grown.msg);
  }finally{h.close();}
}
async function detachedPool(sources={}){
  const h=setup(sources),templateSource=sources.templateSource||template;
  const c={SearchExecutor:h.c.SearchExecutor,scrWorkers:()=>1,SIMQ:{LOAD_MS:60000},document:{hidden:false}};
  vm.createContext(c);
  const start=templateSource.indexOf('const SIM_EXEC=SearchExecutor.shared('),end=templateSource.indexOf('const SIMPOOL=',start);
  vm.runInContext(templateSource.slice(start,end)+'this.shared=SIM_EXEC;',c);
  try{await recommend(c);assert.equal(h.life.active,1,'pool fragment works without GSR or CSR globals');}
  finally{c.shared.drop();c.shared.trimIdle();h.close();}
}
async function creationRace(sources){
  const h=setup(sources),{c,life}=h,run=c.CosmoSearch.search;
  try{
    let injected;
    c.CosmoSearch.search=cx=>run({...cx,onPlan:plan=>{
      cx.onPlan?.(plan);
      // Another owner becomes idle after the page's initial trim, before dispatch.
      injected=c.GuildDaily.createSession(()=>c.SearchExecutor.createWorker());
      c.GSR.session=injected;c.GSR.phase='done';injected.pool.get(0);
    }});
    await search(c);assert(injected.closed,'session creation hook reclaims newly idle guild worker');
    assert.equal(life.max,1,'creation-time cleanup prevents transient double pool');
  }finally{h.close();}
}
async function cleanup(sources){
  const h=setup(sources),{c,life,events}=h;
  try{
    await search(c);c.failWorker=true;await c.cosmoSearchStart();
    assert.equal(c.CSR.phase,'err');assert.equal(life.active,0,'worker error closes cosmo session');
    c.failWorker=false;await search(c);
    let stopped=false;c.afterTeam=()=>{if(stopped)return;stopped=true;events.click({target:{closest:()=>({dataset:{cs:'cancel'}})}});};
    await c.cosmoSearchStart();assert(stopped);assert.equal(c.CSR.phase,'idle');
    assert.equal(life.active,0,'cancel closes cosmo session');c.afterTeam=null;
    await search(c);let release;const growth=c.miGrowth;
    c.miGrowth=()=>new Promise(resolve=>{release=resolve;});const canceled=c.cosmoSearchStart();
    events.click({target:{closest:()=>({dataset:{cs:'cancel'}})}});
    const idleCanceled=life.active===0;release({});await canceled;
    assert(idleCanceled,'cancel before dispatch immediately closes retained worker');c.miGrowth=growth;
    await search(c);const old=c.CSR.session;
    c.miGrowth=()=>new Promise(resolve=>{release=resolve;});const pending=c.cosmoSearchStart();
    c.CSR.id++;const newer=c.SearchExecutor.createSession(()=>c.SearchExecutor.createWorker());c.CSR.session=newer;
    release({});await pending;assert(old.closed,'stale completion closes old session');
    assert(!newer.closed&&c.CSR.session===newer,'stale completion preserves newer session');assert.equal(life.active,0);
  }finally{h.close();}
}
async function main(){
  await reuse();await handoff();await cleanup();await detachedPool();await creationRace();
  for(const kind of ['cosmo','guild'])for(const version of ['engine','data'])await growthVersion(kind,version);
  const mutate=(source,from,to)=>{assert(source.includes(from),'mutation anchor exists: '+from);return source.replace(from,to);};
  const cosmoGuard="if(typeof CSR!=='undefined'&&CSR.phase!=='run'&&!CSR.session?.active&&typeof csSessionRelease==='function')csSessionRelease();";
  const sharedHook=template.slice(template.indexOf(' beforeCreateWorker:()=>{'),template.indexOf('\n',template.indexOf(' beforeCreateWorker:()=>{')));
  const mutations=[
    [reuse,{cosmoSource:mutate(cosmo,'if (!cx.session||!completed) session.close();','session.close();')},/finished cosmo retains/],
    [reuse,{templateSource:mutate(template,'engineVersion:manifest.ver,','')},/engine-only deployment/],
    [reuse,{executorSource:mutate(executor,'this.version!==undefined&&this.version!==version','false')},/engine-only deployment/],
    [handoff,{templateSource:mutate(template,sharedHook,sharedHook.replace(cosmoGuard,''))},/shared creation closes idle cosmo/],
    [handoff,{templateSource:mutate(template,sharedHook,sharedHook.replace("CSR.phase!=='run'&&",'').replace('!CSR.session?.active&&',''))},/shared creation keeps running cosmo/],
    [handoff,{templateSource:mutate(template,sharedHook,sharedHook.replace('!CSR.session?.active&&',''))},/active growth target session/],
    [creationRace,{executorSource:mutate(executor,'beforeCreateWorker?.();return makeWorker();','return makeWorker();')},/creation hook reclaims/],
    [detachedPool,{templateSource:mutate(template,sharedHook,sharedHook.replace("typeof CSR!=='undefined'&&",''))},/CSR is not defined/],
    [cleanup,{templateSource:mutate(template,'}csSessionRelease();CSR.phase="idle";','}CSR.phase="idle";')},/cancel before dispatch/],
    [cleanup,{templateSource:mutate(template,'if(stale()){session.close();if(CSR.session===session)CSR.session=null;}','if(stale()){csSessionRelease(CSR);}')},/stale completion closes old session/]
  ];
  for(const [check,sources,error] of mutations)await assert.rejects(()=>check(sources),error);
  // Remove every data-version guard: session identity, input signature (including
  // the planner's copy in S), and per-job cache key. Any remaining guard masks reuse.
  let guildNoData=daily;
  for(const [from,to] of [
    ['cx.G.dataVersion,cx.engineVersion','cx.engineVersion'],
    ["'guild-follow-v1',cx.G.season.id,cx.G.dataVersion,day.date,cx.S,",
      "'guild-follow-v1',cx.G.season.id,day.date,{...cx.S,dataVersion:undefined},"],
    ['GS.jobKey(keys,level,effectiveSupport,sets,brk,party,G)',
      'GS.jobKey(keys,level,effectiveSupport,sets,brk,party,{...G,dataVersion:undefined})']
  ])guildNoData=mutate(guildNoData,from,to);
  const versionMutations=[
    ['cosmo','engine',{cosmoSource:mutate(cosmo,'cx.dataVersion,cx.engineVersion','cx.dataVersion')}],
    ['cosmo','data',{cosmoSource:mutate(cosmo,'cx.base,cx.dataVersion,cx.engineVersion','cx.base,cx.engineVersion')}],
    ['guild','engine',{dailySource:mutate(daily,'cx.G.dataVersion,cx.engineVersion','cx.G.dataVersion')}],
    ['guild','data',{dailySource:guildNoData}]
  ];
  for(const [kind,version,sources] of versionMutations)
    await assert.rejects(()=>growthVersion(kind,version,sources),new RegExp(kind+' growth '+version+' version change recomputes every battle'));
  console.log('PASS cosmo S2 page: same/changed-input reuse, engine-only refresh, guild/cosmo/shared handoff, creation race, active/growth guards, cancel/error/stale cleanup, detached globals; growth cache engine/data isolation in cosmo/guild; '+(mutations.length+versionMutations.length)+' killed mutations');
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={setup,search,reuse,handoff,cleanup,detachedPool,creationRace};
