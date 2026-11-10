const assert=require('node:assert/strict');
const C=require('../cosmo_search.js'),GS=require('../guild_search.js'),G=require('../data/cosmo_raid.json');
const roster=Array.from({length:18},(_,i)=>({key:'u'+String(i).padStart(2,'0'),cls:i%2?'서포터':'캐스터'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:1000-i*40,stats:{atk:1000-i*40}}]));
const cls=Object.fromEntries(roster.map(r=>[r.key,r.cls]));
const settings=()=>{const s=JSON.parse(JSON.stringify(G.search));
 s.speed.workerReuse.value=false;s.speed.surrogate.value=false;s.speed.rngStreams.value=false;
 s.rerank.keep=60;s.combine.topTriples=5;return s;};
function factory(state,constant=false){return ()=>{
 const w={onmessage:null,onerror:null,terminated:false,terminate(){this.terminated=true;state.closed++;},postMessage(m){
  assert(!this.terminated);state.sent.push(m);
  setImmediate(()=>{if(this.terminated)return;
   for(const t of m.teams){const bi=G.season.bossOrder.indexOf(t.options.cosmo_raid.boss);
    const score=constant?100:t.party.units.reduce((v,u)=>v+1000-((+u.key.slice(1)+bi*6)%18)*40,0);
    this.onmessage({data:{id:m.id,type:'team',key:t.key,result:{prog:.5,progs:null,via:{},clear:0,n:m.n_runs,
     cosmo:{mean:score,top:score,clear:0,frac:.5,n:m.n_runs}}}});}
   this.onmessage({data:{id:m.id,type:'done'}});
  });
 }};state.created++;return w;
};}
const state=()=>({created:0,closed:0,sent:[]});
async function search(s,st,constant=false,over={}){
 return C.search({S:s,bosses:G.season.bossOrder,level:6,mode:'top',results,roster,workers:3,
   makeWorker:factory(st,constant),stage:'cosmo',base:'',...over});
}
async function main(){
 const s=settings(), jobs=GS.combos(s,roster).map(keys=>({key:C.idOf(keys),keys,boss:'belgras'}));
 Object.assign(s.speed.surrogate,{value:true,ratio:.01,auditFrac:.03,minAudit:20,minPerUnit:3});
 const selected=C.surrogateSelect(s,jobs,results,71);
 assert(selected.jobs.length<jobs.length*.3,'actually prunes');
 for(const r of roster)assert(selected.core.filter(j=>j.keys.includes(r.key)).length>=3,'minimum per savior '+r.key);
 assert.deepEqual(C.surrogateSelect(s,jobs,results,71),selected,'deterministic sample');
 assert.deepEqual(C.surrogateSelect(s,jobs.slice().reverse(),results,71).audit,selected.audit,'audit independent of execution order');
 const core=new Set(selected.core.map(j=>j.key));
 assert(selected.audit.length>0&&selected.audit.every(j=>!core.has(j.key)),'uniform sample only from excluded');
 const res=Object.fromEntries(selected.jobs.map(j=>[j.key,{cosmo:{top:core.has(j.key)?100:200,mean:core.has(j.key)?100:200,n:1}}]));
 const audit=C.surrogateAudit(s,selected,res,'top',50);
 assert.equal(audit.fallback,true);assert.equal(audit.rate,1);
 for(const j of selected.audit)res[j.key].cosmo={top:0,mean:0,n:1};
 assert.equal(C.surrogateAudit(s,selected,res,'top',50).fallback,false);
 delete res[selected.audit[0].key];assert(C.surrogateAudit(s,selected,res,'top',50).fallback,'missing result cannot pass');
 const legacy=settings(), reused=settings();reused.speed.workerReuse.value=true;
 const a=state(),b=state();const before=await search(legacy,a),after=await search(reused,b);
 assert.deepEqual(after,before,'worker reuse leaves every result unchanged');
 assert(a.created>b.created);assert.equal(b.created,3);assert.equal(b.closed,b.created);
 const streams=settings();streams.speed.rngStreams.value=true;
 const crn=state();await search(streams,crn);
 assert(crn.sent.length>0&&crn.sent.every(m=>m.teams.every(t=>t.options.rng_streams===true)),'CRN switch reaches every battle');
 assert(a.sent.every(m=>m.teams.every(t=>t.options.rng_streams==null)),'legacy leaves RNG policy unchanged');
 // Force the monitor threshold: all three bosses must return to exhaustive screening.
 const fallback=settings();fallback.speed.surrogate.value=true;fallback.speed.workerReuse.value=true;
 fallback.speed.surrogate.missThreshold=-1;
 const f=state(),l=state();const fast=await search(fallback,f),full=await search(legacy,l);
 assert(fast.audit.every(x=>x.fallback),'audit triggers full fallback');
 assert.deepEqual(fast.rows,full.rows,'fallback uses identical seeds and full candidate set');
 assert.equal(f.closed,f.created);
 const first=f.sent.filter(m=>m.seed===1).flatMap(m=>m.teams.map(t=>t.key));
 assert.equal(first.length,new Set(first).size,'no duplicate initial battles on fallback');
 assert.equal(first.length,3*jobs.length);
 fallback.speed.surrogate.missThreshold=.02;
 const pruned=state();const p=await search(fallback,pruned);
 assert(p.audit.some(x=>!x.fallback),'nonfallback path is exercised');
 assert(pruned.sent.filter(m=>m.seed===1).reduce((n,m)=>n+m.teams.length,0)<3*jobs.length);
 assert(p.rows.length>0);
 const small=settings();small.screen.runs=1;small.speed.surrogate.value=true;
 const noPrune=await search(small,state());
 assert(noPrune.fast&&noPrune.audit.length===0,'requested experiment remains selected when no halving is needed');
 const pl=C.plan(fallback,roster,0);assert(pl.fast&&pl.total<C.plan(legacy,roster,0).total);
 assert(C.preText(pl,null).includes('전수'));
 // Error, cancellation, stale return, and synchronous construction failure release every worker.
 for(const kind of ['error','cancel','stale','throw']){
  const st=state();let handle;
  const overrides={onHandle:h=>{handle=h;if(kind==='cancel')h.cancel();},stale:()=>kind==='stale'};
  if(kind==='error'||kind==='throw')overrides.makeWorker=()=>{
   if(kind==='throw'&&st.created===1)throw new Error('construct');
   st.created++;return {terminate(){st.closed++;},postMessage(m){setImmediate(()=>this.onmessage({data:{type:'error',id:m.id,msg:'failure'}}));}};
  };
  if(kind==='stale')assert.equal(await search(reused,st,false,overrides),null);
  else await assert.rejects(search(reused,st,false,overrides));
  assert.equal(st.closed,st.created,kind+' releases pool');
 }
 const eta=C.etaNew({stages:pl.stages,warmup:0});eta.begin(0,100,0);eta.update(20,1);eta.update(40,3);eta.begin(0,200,4);
 assert.equal(eta.state().st[0].done,40,'fallback keeps measured completed work');
 assert.equal(eta.state().st[0].games,200);
 console.log('PASS cosmo_speed_search_test');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
