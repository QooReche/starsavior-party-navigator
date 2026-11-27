// Real page -> planner -> daily session and shared executor, with synthetic workers.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {harness}=require('./guild_daily_page_test'),{fixture}=require('./guild_daily_test');
const Daily=require('../guild_daily'),Planner=require('../guild_planner'),View=require('../guild_view');
const read=f=>fs.readFileSync(require.resolve('../'+f),'utf8');
const page=read('guild_daily_page.js'),executor=read('search_executor.js'),template=read('party_template.html');
const plain=x=>JSON.parse(JSON.stringify(x));
function setup({pageSource=page,executorSource=executor,templateSource=template}={}){
  const {c}=harness(pageSource),f=fixture(8),life={created:0,active:0,max:0,requests:0},fetches=[];
  c.engine='engine-a';c.D.guild=f.G;c.R=f.roster;c.MI.profiles.op.results=f.results;
  c.GuildDaily=Daily;c.GuildPlanner=Planner;c.GuildView=View;
  c.setTimeout=setTimeout;c.clearTimeout=clearTimeout;c.scrWorkers=()=>1;c.simTeamLimit=()=>60000;
  c.fetch=async(url,options)=>{fetches.push({url,options});return {ok:true,json:async()=>({ver:c.engine})};};
  c.Worker=class {
    constructor(){life.created++;life.active++;life.max=Math.max(life.max,life.active);}
    terminate(){if(!this.dead){this.dead=true;life.active--;}}
    postMessage(m){life.requests++;setImmediate(()=>{
      if(this.dead)return;
      const send=data=>this.onmessage({data:{...m,...data}});
      send({type:'stage',msg:'준비 끝'});
      for(const t of m.teams){
        if(this.dead)return;
        const prior=JSON.parse(t.options?.merge_raw||'[]');
        const raw=prior.concat(Array.from({length:m.n_runs},()=>['wipe',10,20,.6,900]));
        send({type:'team',key:t.key,result:{n:raw.length,prog:.6,progs:raw.map(r=>r[3]),clear:0,
          via:{trigger:1},guild:{base_scores:raw.map(r=>r[4])},raw:JSON.stringify(raw)}});
      }
      if(!this.dead)send({type:'done'});
    });}
  };
  vm.runInContext(executorSource,c);
  const options=c.guildDailyOptions;
  c.guildDailyOptions=()=>({...options(),nowMs:Date.parse('2026-11-26T05:00:00+09:00'),workers:1});
  const start=templateSource.indexOf('const SIM_EXEC=SearchExecutor.shared(');
  const end=templateSource.indexOf('const SIMPOOL=',start);
  assert(start>=0&&end>start);
  vm.runInContext(templateSource.slice(start,end)+'this.shared=SIM_EXEC;this.simPoolTrimIdle=()=>SIM_EXEC.trimIdle();',c);
  return {c,life,fetches,close(){c.guildDailyRelease();c.shared.drop();c.shared.trimIdle();}};
}
async function search(c){
  await c.guildDailyStart();assert.equal(c.GSR.phase,'done',c.GSR.msg);
  assert(c.GSR.sum>0&&c.GSR.rows.length>0,'actual evaluated results');
  return plain({teams:c.GSR.teams,rows:c.GSR.rows,sum:c.GSR.sum});
}
function recommend(c){
  return new Promise((resolve,reject)=>c.shared.dispatch(c.shared.reserve(1),[{}],{
    id:1,live:()=>true,msg:()=>({type:'run',n_runs:1,teams:[{key:'reco',options:{}}]}),
    team:(job,m)=>assert(m.result.progs[0]>0),done:resolve,error:reject}));
}
async function engineChange(sources){
  const h=setup(sources),{c,life,fetches}=h;
  try{
    const result=await search(c),session=c.GSR.session,first=session.pool.get(0);
    assert.equal(life.created,1);assert(life.requests>0);
    assert.deepEqual(await search(c),result);assert.equal(session.pool.get(0),first);
    const identity=plain([c.D.guild.season.id,c.D.guild.dataVersion]);
    c.engine='engine-b';assert.deepEqual(await search(c),result);
    assert.deepEqual(plain([c.D.guild.season.id,c.D.guild.dataVersion]),identity);
    assert(first.dead,'engine-only deployment must terminate old worker');
    assert.notEqual(session.pool.get(0),first);assert.equal(life.created,2);
    assert.equal(life.active,1);assert.equal(life.max,1);
    assert.equal(fetches.length,3);assert(fetches.every(f=>f.url==='sim/manifest.json'&&f.options.cache==='no-cache'));
    c.fetch=async()=>({ok:false});await c.guildDailyStart();
    assert.equal(c.GSR.phase,'err');assert.equal(life.active,0,'failed manifest must not run stale engine');
  }finally{h.close();}
}
async function poolHandoff(sources){
  const h=setup(sources),{c,life}=h;
  try{
    const result=await search(c),session=c.GSR.session;
    assert.equal(life.active,1);await recommend(c);
    assert.equal(life.active,1,'guild completion -> recommendation retains only one pool');
    assert.equal(life.max,1,'idle guild worker must close before shared worker creation');
    assert(session.closed);assert.equal(c.GSR.session,null);
    assert.deepEqual(await search(c),result,'recreating the guild session preserves results');
    assert.equal(c.shared.state.workers.length,0,'guild start still trims shared idle workers');
    assert.equal(life.active,1);assert.equal(life.max,1);
    // Hold an actual page start before planner dispatch, while its retained pool is in use.
    const running=c.GSR.session;let release;
    c.miGrowth=()=>new Promise(resolve=>{release=resolve;});
    const pending=c.guildDailyStart();assert.equal(c.GSR.phase,'run');
    await recommend(c);const survived=!running.closed&&c.GSR.session===running;
    release({});await pending;
    assert(survived,'shared pool creation must not close a running guild search');
    assert.equal(c.GSR.phase,'done',c.GSR.msg);
  }finally{h.close();}
}
async function main(){
  await engineChange();await poolHandoff();
  const mutations=[
    [engineChange,{pageSource:page.replace('engineVersion:manifest.ver,','')},/engine-only deployment/],
    [poolHandoff,{executorSource:executor.replace('env.beforeCreateWorker?.();','')},/retains only one pool/],
    [poolHandoff,{templateSource:template.replace(/^ beforeCreateWorker:.*$/m,'')},/retains only one pool/],
    [poolHandoff,{templateSource:template.replaceAll("if(typeof GSR!=='undefined'&&GSR.phase!=='run'&&typeof guildDailyRelease==='function')guildDailyRelease();",'guildDailyRelease();')},/running guild search/]
  ];
  for(const [check,source,error] of mutations)await assert.rejects(()=>check(source),error);
  console.log('PASS S2 page integration: engine-only change, identical results, idle pool handoff both ways, active guard, manifest failure; 4 killed mutations');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
