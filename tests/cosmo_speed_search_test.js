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
 const a=state(),b=state(),messages=[];const before=await search(legacy,a,false,{onPhase:m=>messages.push(m)}),after=await search(reused,b);
 assert(messages[0].includes('처음 한 번은 계산 엔진을 내려받느라 1~3분 더 걸립니다'),'halved screening explains first download');
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
 assert.deepEqual(fast.rows,full.rows,'fallback preserves final ranking with the full candidate set');
 assert.equal(f.closed,f.created);
 const first=f.sent.filter(m=>m.seed===1).flatMap(m=>m.teams.map(t=>t.key));
 assert.equal(first.length,new Set(first).size,'no duplicate initial battles on fallback');
 assert.equal(first.length,3*jobs.length);
 const firstAssignments=st=>st.sent.filter(m=>m.seed===1).flatMap(m=>m.teams.map(t=>[t.key,m.seed,m.n_runs])).sort((x,y)=>x[0].localeCompare(y[0]));
 assert.deepEqual(firstAssignments(f),firstAssignments(l),'every first battle keeps its seed and run count on fallback');
 // Drop one otherwise winning core result after workers finish. It must be retried,
 // then reach the supplementary phase; testing the audit flag alone misses this bug.
 for(const kind of ['absent','no-cosmo','repeated']){
  const originalRun=GS.runPhase,calls=[];let dropped;
  GS.runPhase=o=>{
   calls.push(o);const h=originalRun(o);
   return {...h,promise:h.promise.then(res=>{
    if(calls.length===1){
     dropped=o.jobs.filter(j=>j.boss===G.season.bossOrder[0]).sort((x,y)=>res[y.key].cosmo.top-res[x.key].cosmo.top)[0];
     if(kind==='no-cosmo')res[dropped.key]={prog:.5,n:o.runs};else delete res[dropped.key];
    }else if(kind==='repeated'&&o.seed===1)delete res[dropped.key];
    return res;
   })};
  };
  const st=state();
  try{
   if(kind==='repeated')await assert.rejects(search(fallback,st),/전수 확인 결과가 누락/);
   else{
    const recovered=await search(fallback,st);
    assert(recovered.audit.find(x=>x.boss===dropped.boss).fallback,'missing result triggers recovery');
    const retried=calls.filter(o=>o.seed===1&&o.jobs.some(j=>j.key===dropped.key));
    assert.equal(retried.length,2,'missing team is actually evaluated again: '+kind);
    assert(retried.every(o=>o.runs===fallback.screen.firstRuns),'retry preserves first run count');
    assert(calls.some(o=>o.seed===4&&o.jobs.some(j=>j.key===dropped.key)),'recovered winning team reaches supplementary phase');
    assert.deepEqual(recovered.rows,full.rows,'missing response recovery restores final ranking');
   }
   assert.equal(st.closed,st.created,'recovery releases workers');
  }finally{GS.runPhase=originalRun;}
 }
 fallback.speed.surrogate.missThreshold=.02;
 const pruned=state();const p=await search(fallback,pruned);
 assert(p.audit.some(x=>!x.fallback),'nonfallback path is exercised');
 assert(pruned.sent.filter(m=>m.seed===1).reduce((n,m)=>n+m.teams.length,0)<3*jobs.length);
 assert(p.rows.length>0);
 const small=settings();small.screen.runs=1;small.speed.surrogate.value=true;
 const noPrune=await search(small,state());
 assert(noPrune.fast&&noPrune.fastSkipped&&noPrune.audit.length===0,'requested experiment stays selected but is explicitly skipped without halving');
 const near=settings();near.rerank.keep=120;near.speed.surrogate.value=true;
 const smallRoster=roster.slice(0,12),smallPlan=C.plan(near,smallRoster,0);
 assert(smallPlan.halved&&!smallPlan.fast&&smallPlan.fastSkipped,'small pool skips surrogate when pass reaches core boundary');
 const nearLegacy=settings(),nearState=state();nearLegacy.rerank.keep=120;
 assert.equal(smallPlan.total,C.plan(nearLegacy,smallRoster,0).total,'small pool estimate uses exhaustive work');
 assert(C.preText(smallPlan,null).includes('적어 빠른 탐색을 적용하지 않고 전수 확인'));
 const nearResult=await search(near,nearState,false,{roster:smallRoster});
 const nearFull=await search(nearLegacy,state(),false,{roster:smallRoster});
 assert.deepEqual(nearResult.rows,nearFull.rows,'small pool result stays exhaustive');
 assert.equal(nearState.sent.filter(m=>m.seed===1).flatMap(m=>m.teams).length,3*smallPlan.combos,'no extra audit or fallback phase in small pool');
 assert(!C.html({...nearResult,phase:'done'},{hasInfo:true,esc:x=>x,bossName:x=>x,label:x=>x,level:6,mode:'top',fast:true,levelMax:12}).includes('대리 선별·무작위 확인'),'skipped experiment is not described as pruned');
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
