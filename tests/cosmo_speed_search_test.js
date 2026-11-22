const assert=require('node:assert/strict');
const C=require('../cosmo_search.js'),G=require('../data/cosmo_raid.json');
// 빠른 탐색(대리 점수)·공통 난수(rngStreams)·워커 재사용 스위치는 11/22 삭제 — 워커 재사용만 남김(항상 켬)
const roster=Array.from({length:18},(_,i)=>({key:'u'+String(i).padStart(2,'0'),cls:i%2?'서포터':'캐스터'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:1000-i*40,stats:{atk:1000-i*40}}]));
const settings=()=>{const s=JSON.parse(JSON.stringify(G.search));
 s.learned.value=false; // 전수 경로 회귀
 s.rerank.keep=60;s.combine.topTriples=5;return s;};
function factory(state){return ()=>{
 const w={onmessage:null,onerror:null,terminated:false,terminate(){this.terminated=true;state.closed++;},postMessage(m){
  assert(!this.terminated);state.sent.push(m);
  setImmediate(()=>{if(this.terminated)return;
   for(const t of m.teams){const bi=G.season.bossOrder.indexOf(t.options.cosmo_raid.boss);
    const score=t.party.units.reduce((v,u)=>v+1000-((+u.key.slice(1)+bi*6)%18)*40,0);
    this.onmessage({data:{id:m.id,type:'team',key:t.key,result:{prog:.5,progs:null,via:{},clear:0,n:m.n_runs,
     cosmo:{mean:score,top:score,clear:0,frac:.5,n:m.n_runs}}}});}
   this.onmessage({data:{id:m.id,type:'done'}});
  });
 }};state.created++;return w;
};}
const state=()=>({created:0,closed:0,sent:[]});
async function search(s,st,over={}){
 return C.search({S:s,bosses:G.season.bossOrder,level:6,mode:'top',results,roster,workers:3,
   makeWorker:factory(st),stage:'cosmo',base:'',...over});
}
async function main(){
 assert.equal(G.search.speed,undefined,'speed switches removed from data');
 const s=settings(),a=state(),messages=[];
 const out=await search(s,a,{onPhase:m=>messages.push(m)});
 assert(out.rows.length>0);
 assert(messages[0].includes('처음 한 번은 계산 엔진을 내려받느라 1~3분 더 걸림'),'halved screening explains first download');
 assert.equal(a.created,3,'workers are reused across stages');assert.equal(a.closed,a.created);
 assert(a.sent.length>0&&a.sent.every(m=>m.teams.every(t=>t.options.rng_streams==null)),'search leaves RNG policy unchanged');
 assert.deepEqual(await search(settings(),state()),out,'same input, same result');
 // Error, cancellation, stale return, and synchronous construction failure release every worker.
 for(const kind of ['error','cancel','stale','throw']){
  const st=state();
  const overrides={onHandle:h=>{if(kind==='cancel')h.cancel();},stale:()=>kind==='stale'};
  if(kind==='error'||kind==='throw')overrides.makeWorker=()=>{
   if(kind==='throw'&&st.created===1)throw new Error('construct');
   st.created++;return {terminate(){st.closed++;},postMessage(m){setImmediate(()=>this.onmessage({data:{type:'error',id:m.id,msg:'failure'}}));}};
  };
  if(kind==='stale')assert.equal(await search(settings(),st,overrides),null);
  else await assert.rejects(search(settings(),st,overrides));
  assert.equal(st.closed,st.created,kind+' releases pool');
 }
 const pl=C.plan(settings(),roster,0);
 assert(pl.halved&&!('fast' in pl)&&C.preText(pl,null).includes('기본 '));
 const eta=C.etaNew({stages:pl.stages,warmup:0});eta.begin(0,100,0);eta.update(20,1);eta.update(40,3);eta.begin(0,200,4);
 assert.equal(eta.state().st[0].done,40,'restart keeps measured completed work');
 assert.equal(eta.state().st[0].games,200);
 console.log('PASS cosmo_speed_search_test');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
