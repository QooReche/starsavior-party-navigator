const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const GS=require('../guild_search'),P=require('../guild_planner'),V=require('../guild_view'),E=require('../search_executor');
const G=require('./guild_fixture')(30111),S={...G.search,banCoop:false,poolSize:6,minPowerRatio:0,minRole:{},screen2:{keep:4,runs:3},finalists:2,final:{levels:[0,6,12],supports:['none'],runs:4}};
S.screen={...S.screen,level:6,supporter:'none',other:'none'};
const roster=Array.from({length:6},(_,i)=>({key:'u'+i,cls:i%2?'캐스터':'서포터'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:1000-i,stats:{hp:1000,atk:100,def:100,spd:100},combat:{}}]));
const raw=m=>({prog:.8,progs:Array(m.n_runs).fill(.8),clear:0,n:m.n_runs,via:{trigger:1}});
async function scenario({stop=0,cancel=false,stale=false,empty=false,planner=P}={}){
 let phase=0,partial=false,invalid=false,handle,live=0,max=0,late;const progress=[],plans=[];
 try{
  const out=await planner.search({S,G,V,results,roster,tiers:[0,0,0,0],breaks:[{name:'synthetic',level:1}],workers:1,stage:'synthetic',base:'',
   stale:()=>invalid,partialRequested:()=>partial,onPlan:p=>plans.push(p),onPhase:()=>phase++,onHandle:h=>{handle=h;if(empty&&phase===stop){partial=true;h.cancel();}},
   onProgress:(d,t)=>{progress.push([phase,d,t]);if(phase===stop&&d===1){partial=!cancel;invalid=stale;handle.cancel();}},
   makeWorker(){live++;max=Math.max(max,live);let dead=false;return {terminate(){if(!dead){dead=true;live--}},postMessage(m){setImmediate(()=>{
    const fn=this.onmessage;late=()=>fn({data:{type:'team',id:m.id,key:m.teams.at(-1).key,result:raw(m)}});
    for(const t of m.teams){if(dead)return;fn({data:{type:'team',id:m.id,key:t.key,result:raw(m)}});}if(!dead)fn({data:{type:'done',id:m.id}});
   })}};}
  });
  assert.equal(plans.length,1);assert.equal(max,1);assert.equal(live,0);
  const frozen=JSON.stringify(out);late?.();assert.equal(JSON.stringify(out),frozen);
  return {out,progress};
 }finally{assert.equal(live,0);}
}
async function partialChecks(planner=P){
 for(const stop of [1,2,3,4]){
  const {out,progress}=await scenario({stop,planner});assert.equal(out.partial,true);assert(out.rows.length&&out.rows[0].score>0);
  assert.equal(out.coverage.selectedStage,stop);assert.equal(out.coverage.stages.length,stop);
  assert.equal(out.coverage.stages.at(-1).done,1);assert.equal(out.coverage.stages.at(-1).complete,false);
  assert.equal(out.coverage.stages.filter(s=>s.complete).length,stop-1);
  assert(out.rows.every(r=>r.evaluation.partial&&r.evaluation.stage===stop));assert.equal(out.rows[0].evaluation.stageSupportComplete,stop===4);
  const text=GS.coverageText(out);assert(text.includes('부분 결과'));if(stop<3)assert(text.includes('스테이지·지원 미평가(★ 별의 도전 6·지원 없음 기준)'));
  if(stop===3)assert(text.includes('일부만 평가'));if(stop===4)assert(text.includes('브레이크 비교 미완료'));
  assert.equal(progress.at(-1)[0],stop);
 }
}
function painting(){
 const pl=P.plan(S,15,1),eta=GS.progressNew(pl,1,{sec:[2,3,4,5],workers:2});eta.begin(0,30,0);
 assert.equal(eta.estimate(0).cost[0],4);eta.update(2,1);eta.update(10,6);assert(eta.summary().every(x=>x>0));
 const invalid=GS.progressNew(pl,1,{sec:[NaN,1,2,3],workers:1});invalid.begin(0,30,0);assert.equal(invalid.estimate(0).ready,false);
 const step={},time={},fill={style:{}},bar={firstElementChild:fill,setAttribute:(k,v)=>bar[k]=v},button={};
 const el={querySelector:s=>s.includes('plan-step')?step:s.includes('plan-eta')?time:bar};
 const host={querySelector:s=>s.includes('partial')?button:el};
 GS.progressPaint(host,{plan:pl,stageIndex:1,done:1,total:4,eta});assert(step.textContent.startsWith('2/4'));assert(time.textContent.startsWith('남은 시간'));
 assert(bar['aria-valuenow']>0&&bar['aria-valuenow']<100);assert(fill.style.transform.startsWith('scaleX('));
 GS.progressPaint(host,{plan:pl,stageIndex:3,done:1,total:1,eta,stopRequested:true});assert.equal(button.disabled,true);assert.equal(bar['aria-valuenow'],99);
 assert.equal(GS.SPEED_KEY,'guild.speed.v1');
}
async function pageChecks(){
 const src=fs.readFileSync(require.resolve('../party_template.html'),'utf8'),a=src.indexOf('async function guildSearchStart('),b=src.indexOf('$("guild-search").addEventListener',a);
 let resolveSearch,seen=[],saved=[],growth=0;
 const ctx={GSR:{id:0,phase:'idle',stopRequested:true,partial:true},D:{guild:{...G,search:S}},GuildSearch:GS,GuildView:V,SearchExecutor:E,
  GuildPlanner:{search:cx=>{seen.push(cx);cx.onPlan(P.plan(S,15,1));cx.onPhase('phase',15,{stage:0,runs:2,games:30});return new Promise(r=>resolveSearch=r)}},
  MI:{info:{},profiles:{op:{results}}},SIMQ:{busy:null},CSR:{phase:'idle'},R:roster,EXCL:new Set(),contents:[{key:'guild'}],cur:[{tab:'EX',name:'7'}],$:()=>({value:0}),
  seasonBlocked:()=>false,growthCancel(){},guildGwenClaim(){},renderGuildSearch(){},growthPaint(){},miGrowth:async()=>({}),
  gsTiers:()=>[0,0,0,0],ownedSimBreaks:()=>[],gsSig:()=> 'stable-signature',growthOwnedContext:()=> 'stable-context',growthEnabled:()=>true,growthStart:()=>growth++,
  navigator:{hardwareConcurrency:2},location:{href:'http://synthetic.test/index.html'},LS:{get:()=>null,set:(...v)=>saved.push(v)}};
 vm.runInNewContext(src.slice(a,b)+';globalThis.start=guildSearchStart',ctx);
 const first=ctx.start();await new Promise(setImmediate);assert.equal(ctx.GSR.stopRequested,false);assert.equal(ctx.GSR.partial,false);
 // Old response arrives after a replacement run. Even callbacks must not mutate it.
 const old=resolveSearch,oldCx=seen[0];ctx.GSR.id++;ctx.GSR.phase='idle';const second=ctx.start();await new Promise(setImmediate);
 oldCx.onProgress(99,99);old({rows:[{score:999}]});await first;assert.notEqual(ctx.GSR.done,99);assert.equal(ctx.GSR.phase,'run');
 resolveSearch({rows:[{score:10}],partial:true,coverage:{stages:[]}});await second;assert.equal(ctx.GSR.rows[0].score,10);assert.equal(ctx.GSR.phase,'done');assert.equal(growth,0);
 assert.equal(ctx.GSR.sig,'stable-signature');
 ctx.GSR.phase='idle';const full=ctx.start();await new Promise(setImmediate);const e=ctx.GSR.eta;e.begin(0,30,0);e.update(2,1);e.update(10,6);
 resolveSearch({rows:[{score:20}],partial:false});await full;assert.equal(growth,1);assert.equal(saved[0][0],GS.SPEED_KEY);
 const target={id:0,phase:'idle'};const grown=ctx.start(target,{results});await new Promise(setImmediate);const n=saved.length;
 resolveSearch({rows:[{score:30}],partial:false});await grown;assert.equal(ctx.GSR.rows[0].score,20);assert.equal(target.rows[0].score,30);assert.equal(saved.length,n);assert.equal(growth,1);
 const growthSrc=fs.readFileSync(require.resolve('../growth_ui.js'),'utf8');const from=growthSrc.indexOf('function growthSeasonReady('),to=growthSrc.indexOf('\nfunction ',from+1);
 vm.runInNewContext(growthSrc.slice(from,to)+';globalThis.ready=growthSeasonReady',ctx);ctx.GSR.context='stable-context';ctx.GSR.partial=true;assert.equal(ctx.ready({key:'guild'}),false);
}
(async()=>{
 await partialChecks();const full=(await scenario()).out;assert.equal(full.partial,false);assert.equal(full.coverage.stages.length,4);assert(full.coverage.stages.every(s=>s.complete));
 const empty=(await scenario({stop:1,empty:true})).out;assert.equal(empty.rows.length,0);assert(GS.coverageText(empty).includes('완료된 적격 후보 없음'));
 const fallback=(await scenario({stop:3,empty:true})).out;assert.equal(fallback.coverage.selectedStage,2);assert.equal(fallback.rows[0].evaluation.stageSupportComplete,false);
 await assert.rejects(()=>scenario({stop:1,cancel:true}),/취소/);await assert.rejects(()=>scenario({stop:2,stale:true}),/취소/);
 const cx={esc:String,label:String,hasInfo:true,sig:''};const part=(await scenario({stop:2})).out;
 const html=GS.html({...part,phase:'done'},cx);assert(html.includes('미평가'));assert(!html.includes('단계·지원별로 3판씩 돌린 값임'));
 const run=GS.html({phase:'run'},cx);assert(run.includes('role="progressbar"'));assert(run.includes('지금까지 결과로 보기'));
 painting();await pageChecks();
 const src=fs.readFileSync(require.resolve('../guild_planner'),'utf8'),anchor='stage:(selected?.stage??-1)+1';assert(src.includes(anchor));
 const ctx={module:{exports:{}},require:n=>require('../'+n)};vm.runInNewContext(src.replace(anchor,'stage:3'),ctx);
 await assert.rejects(()=>partialChecks(ctx.module.exports),assert.AssertionError);
 console.log('PASS guild progress: 4 stop phases, empty/fallback/cancel/stale/full, row coverage mutation, ETA/prior/painter, page restart/growth/cache isolation');
})().catch(e=>{console.error(e);process.exitCode=1});
