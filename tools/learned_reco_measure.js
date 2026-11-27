// Measurement only. Production functions are captured by stage_reco_check collect --learned.
// Both Node/native and browser/Pyodide run this exact policy; no Python search implementation.
(function(root){
'use strict';
const node=typeof module!=='undefined'&&module.exports;
const dep=(file,name)=>node?require('../'+file):root[name];
const L=dep('cosmo_learned.js','CosmoLearned'),P=dep('party_placement.js','PartyPlacement');
const U=dep('ui_shared.js','UiShared'),DP=dep('direct_party.js','DirectParty');
const MR=dep('myinfo_reco.js','MyInfoReco'),Q=dep('quick.js','Quick');
const Pipeline=dep('recommend_pipeline.js','RecommendPipeline');
const Executor=dep('search_executor.js','SearchExecutor');
const id=U.teamKey;

function runtime(input,D,evaluate,seed){
 const declarations=Object.entries(input.sources).map(([k,v])=>`const ${k}=(${v});`).join('\n');
 const factory=new Function('input','D','evaluate','seed','UiShared','PartyPlacement','DirectParty','MyInfoReco','Quick',`
 const CFG=D.cfg,QK={d:{sv:input.unitQuick}},bkeys=Object.keys(CFG.breakSkills).filter(k=>!k.startsWith('_'));
 const {${Object.keys(input.constants).join(',')}}=input.constants;
 const SYN=new Map();D.syn.forEach((p,i)=>{p._i=i;const k=p.a<p.b?p.a+'|'+p.b:p.b+'|'+p.a;(SYN.get(k)||SYN.set(k,[]).get(k)).push(p)});
 const RECO_ARR=new Map(),ckey=combo=>UiShared.teamKey(combo.map(x=>x.s.key)),goalVal=PartyPlacement.goalOf;
 const recoIdentity=()=>String(seed),recheckHold=()=>false;
 const contents=[input.c],$=()=>({value:0}),BRSEL=input.selected,SHARE=input.shared,SESSION_BR=input.sessionBreak;
 const breakOwned=()=>input.breaks,brkLv=k=>input.levels[k]||5;
 const ekey=k=>!input.profile?.results[k]&&input.bloom[k]&&QK.d.sv[k+'@개화(SSR)']?k+'@개화(SSR)':k;
 const recoEvaluate=async(snapshot,task,jobs,n,{onTeam=()=>{}}={})=>{
   const res=await evaluate(jobs.map(j=>({...j,runs:j.runs||n,seed:j.seed??seed,options:{...input.options,...j.options}})));
   jobs.forEach((j,i)=>onTeam(j,{...res[i],n}));
 };
 ${declarations}
 return {${Object.keys(input.sources).join(',')},goalVal,ckey,ekey,RECO_ARR};
 `);
 const r=factory(input,D,evaluate,seed,U,P,DP,MR,Q),by=new Map(input.cands.map(x=>[x.s.key,x]));
 const make=(keys,extra={})=>{
   const ek=keys.map(r.ekey),b=input.profile?{growth:1,power:null,...MR.team(keys,input.profile,r.ekey)}:{growth:input.qi.growth,power:input.qi.power,powers:null};
   return {keys,combo:keys.map(k=>by.get(k)),ek,b,base:b.power||(input.qi.qs.bp?input.qi.qs.bp*b.growth:null),...extra};
 };
 const qt=input.qt.map(t=>make(t.keys,t)),known=new Map(qt.map(t=>[id(t.keys),t]));
 r.team=keys=>known.get(id(keys))||make(keys);
 r.qt=qt;
 r.add=keys=>{const k=id(keys);if(!known.has(k)){const t=make(keys,{v:0,vd:'hard'});known.set(k,t);qt.push(t);}return known.get(k);};
 for(const x of input.parity){const t=r.team(x.keys);
   if(JSON.stringify(r.simParty(t))!==JSON.stringify(x.party)||JSON.stringify(r.teamBreak(t))!==JSON.stringify(x.brk))throw Error('Collected screen spec mismatch');}
 return r;
}

// Explicit general-stage encoder: actual simParty engine order, actual leader and chosen break.
// No quick output, power, stats or candidate score is a regression feature.
function encoder(rows,r){
 const ix=new Map(),meta=new Map(rows.map(x=>[x.key,x])),index=k=>{if(!ix.has(k))ix.set(k,ix.size);return ix.get(k);};
 for(const x of rows)for(const kind of ['unit','front','back','leader'])index(kind+':'+x.key);
 for(const field of ['cls','el']){const vs=[...new Set(rows.map(x=>x[field]))].sort();for(let a=0;a<vs.length;a++)for(let b=a;b<vs.length;b++)index(field+':'+vs[a]+'/'+vs[b]);}
 for(const b of r.breaks)index('break:'+b);index('break:');
 function encode(keys){const t=r.team(keys),p=r.simParty(t),out=new Map(),add=k=>{const i=ix.get(k);if(i===undefined)throw Error('Unknown feature '+k);out.set(i,(out.get(i)||0)+1);};
   p.units.forEach((u,i)=>{const k=t.keys.find(k=>r.ekey(k)===u.key);add('unit:'+k);add((i<2?'front:':'back:')+k);if(i===p.leader)add('leader:'+k);});
   for(let a=0;a<4;a++)for(let b=a+1;b<4;b++)for(const f of ['cls','el'])add(f+':'+[meta.get(keys[a])[f],meta.get(keys[b])[f]].sort().join('/'));
   add('break:'+(r.teamBreak(t)?.name||''));return [...out];
 }
 return {encode,size:ix.size};
}
function fallbackRequired(c,rho,rate){return rho===null||!Number.isFinite(rho)||rho<c.minCorrelation||rate>c.missThreshold;}
async function fixedEvaluation(winner,others,evaluate){
 const frozen=JSON.parse(JSON.stringify(winner));
 const result=await evaluate(frozen);
 const diagnostics=[];for(const team of others)diagnostics.push({team,result:await evaluate(team)});
 return {winner:frozen,result,diagnostics};
}

async function run(input,D,settings,method,seed,evaluate,onPhase=()=>{},{selectionOnly=false}={}){
 const start=performance.now(),phases=[];let games=0;
 const ev=async(jobs,label='battle')=>{const t=performance.now();games+=jobs.reduce((n,j)=>n+j.runs,0);const res=await evaluate(jobs);
   phases.push({label,teams:jobs.length,runs:jobs.reduce((n,j)=>n+j.runs,0),seconds:(performance.now()-t)/1000});onPhase(label,games);return res;};
 const r=runtime(input,D,ev,seed);r.breaks=input.breaks;
 const full=()=>r.scrFullInit({done:false,order:[],n:input.initial.length,total:input.initial.length,pool:input.initial.slice(),res:{},res2:{},up:null,round:0},r.qt.slice(0,input.qt.length));
 let sc=full(),audit=null,learned=null;
 if(!sc.full)return {excluded:'quick_not_all_hard',method,seed,id:input.id,private:input.private,stage:input.c.key+'/'+input.st.tab+'/'+input.st.name};
 const job=(keys,runs=1,options={},s=seed)=>{const t=r.team(keys);return {key:id(keys),party:r.simParty(t),runs,seed:s,screen:runs<=32&&!!options.rng_streams,options:{...input.options,break_skill:r.teamBreak(t),...options}};};
 const outsideN=method==='U120'?120:method==='U360'?360:0;
 if(!['F','A','C','U120','U360'].includes(method))throw Error('Unknown measurement method');
 if(method!=='F'){
   const S=structuredClone(settings);S.learned.K=sc.fullN;
   const pool=new Set(input.pool),rows=input.cands.filter(x=>method==='C'||outsideN||pool.has(x.s.key)).map(x=>({key:x.s.key,cls:x.s.cls,el:x.s.el}));
   const c=L.config(S,rows.length),observed=new Map(),lt=performance.now();
   async function observe(teams,label){const todo=teams.filter(k=>!observed.has(id(k))),res=await ev(todo.map(k=>job(k,1,{rng_streams:true,raw_runs:true})),label);todo.forEach((k,i)=>observed.set(id(k),{keys:k,result:res[i]}));}
   const sample=await L.sample(S,rows,seed);await observe(sample,'sample');
   const model=await L.train(encoder(rows,r),sample,sample.map(k=>observed.get(id(k)).result.prog),c);
   if(outsideN){
     // Same C sample/fit; only outside-pool predictions compete for this fixed extra budget.
     const top=new L.Heap(outsideN);
     await L.scan(S,rows,keys=>{if(keys.some(k=>!pool.has(k)))top.put({keys,id:L.id(keys),score:model.predict(keys)});},()=>false);
     const outside=top.sorted();
     // Charge all sample + N_out games separately, even when a selected team was sampled.
     const extra=await ev(outside.map(x=>job(x.keys,1,{rng_streams:true,...r.scrLegOpt(null)})),'outside');
     const baseKeys=sc.full.slice(),base=await ev(baseKeys.map(k=>job(k.split(','),1,{rng_streams:true,...r.scrLegOpt(null)})),'full');
     baseKeys.forEach((k,i)=>sc.res0[k]={...base[i],n:1});
     outside.forEach((x,i)=>{r.add(x.keys);const k=id(x.keys);sc.full.push(k);sc.res0[k]={...extra[i],n:1};});
     // Original F tie positions precede extras; promotion count and comparator are unchanged.
     sc.pool=r.scrFullRank(sc).slice(0,sc.fullN);sc.total=sc.pool.length;sc.fullDone=true;
     learned={settings:c,roster:rows.length,sampled:sample.length,outsideN,selected:outside.length,rho:model.rho,
       outside:outside.map(x=>id(x.keys)),promotedOutside:sc.pool.filter(k=>k.split(',').some(x=>!pool.has(x))),seconds:(performance.now()-lt)/1000};
   }else{
   const sel=await L.select(S,rows,model);await observe([...sel.core.values()].map(x=>x.keys),'selected');
   const a=await L.auditSample(S,rows,sel,seed+100003);await observe(a.teams,'audit');
   audit=L.audit(c,model.rho,[...sel.core.values()].map(x=>observed.get(id(x.keys)).result.prog),a.teams.map(k=>observed.get(id(k)).result.prog),a.teams.length,a.excluded,sc.fullN);
   audit.fallback ||= fallbackRequired(c,model.rho,audit.rate);
   learned={settings:c,roster:rows.length,sampled:sample.length,selected:sel.core.size,audit,seconds:(performance.now()-lt)/1000};
   if(audit.fallback){sc=full();onPhase('fallback',games);}else{
     // Every actually observed clear (including sample/audit) can compete under scrCmp.
     const candidates=[...observed.values()].filter(x=>sel.core.has(L.id(x.keys))||x.result.clear>0);
     candidates.sort((a,b)=>r.scrCmp(a.result,b.result)||id(a.keys).localeCompare(id(b.keys)));
     const promoted=candidates.slice(0,sc.fullN);promoted.forEach(x=>r.add(x.keys));
     sc={...sc,full:promoted.map(x=>id(x.keys)),fullDone:true,pool:promoted.map(x=>id(x.keys)),res0:Object.fromEntries(promoted.map(x=>[id(x.keys),x.result]))};
   }
   }
 }
 if(selectionOnly)return {sc,learned,fallback:!!audit?.fallback,additions:r.qt.slice(input.qt.length).map(t=>t.keys),phases,searchGames:games};
 await new Promise((resolve,reject)=>r.recoScreenSequence(sc,input.constants.SCR_ROUNDS[1].top,new Map(r.qt.map(t=>[id(t.keys),t])),async(i,keys,next)=>{
   try{const n=r.scrRoundN(i),jobs=keys.map(k=>{const pr=r.scrPrior(sc,i,k);return job(k.split(','),pr?n-pr.off:n,{rng_streams:true,...r.scrLegOpt(pr)});});
     const res=await ev(jobs,i<0?'full':i?'screen32':'screen8');keys.forEach((k,j)=>(i<0?sc.res0:i?sc.res2:sc.res)[k]={...res[j],n});next();}catch(e){reject(e);}
 },()=>{r.scrClose(sc);resolve();}));
 const results=new Map(),ident=String(seed),task={cancelled:false};let more=3,box;
 const sig=(t,arr)=>JSON.stringify(r.simParty(t,r.ekey,arr));
 const result=t=>results.get(sig(t));
 const snapshot={key:ident,seed,n:100,options:input.options,breakFor:r.teamBreak,result,
   partyAt:(t,a)=>r.simParty(t,r.ekey,a),partyRule:t=>r.simParty(t,r.ekey,r.arrangeOf(t.combo,true))};
 const plan=()=>box={all:r.qt,rows:r.quickRows(r.qt,input.st,1,{n:more,sc,result,joint:null}),total:r.qt.length};
 const first=await Pipeline.recommendation({parties:1,screened:false,live:()=>true,plan,more:(_,n)=>{more=n;},result,goal:r.goalVal,
   async final(_,b){const todo=b.rows.filter(t=>!result(t)),res=await ev(todo.map(t=>job(t.keys,100)),'final100');todo.forEach((t,i)=>results.set(sig(t),res[i]));
     r.recoArrangeRevert(ident,b.rows,result,t=>results.get(sig(t,r.arrangeOf(t.combo,true))));},
   arrange:(_,b)=>r.recoArrange(snapshot,task,b),
   first:()=>{const t=box.rows[0];return {keys:t.keys,party:r.simParty(t),brk:r.teamBreak(t),result:result(t)};}});
 const seconds=(performance.now()-start)/1000,searchGames=games;
 // Freeze before independently measuring. The top-five diagnostic never changes first.
 const candidates=box.rows.slice(0,5).map(t=>({keys:t.keys,party:r.simParty(t),brk:r.teamBreak(t)}));
 const others=candidates.filter(t=>id(t.keys)!==id(first.keys));let independent;
 const frozen=await fixedEvaluation(first,others,async t=>{
   if(!independent){const all=[t,...others],res=await ev(all.map(t=>({key:id(t.keys),party:t.party,runs:400,seed:20261127,options:{...input.options,break_skill:t.brk,raw_runs:true,rng_streams:true}})),'independent400');independent=new Map(all.map((t,i)=>[id(t.keys),res[i]]));}
   return independent.get(id(t.keys));
 });
 return {method,seed,id:input.id,private:input.private,stage:input.c.key+'/'+input.st.tab+'/'+input.st.name,options:input.options,
   fullN:sc.fullN,learned,fallback:!!audit?.fallback,seconds,searchGames,evaluationGames:games-searchGames,phases,screen:{pool:sc.pool,order:sc.order,up:sc.up},...frozen};
}
function workerPool(makeWorker,count,stage,base=''){
 const workers=Array.from({length:count},makeWorker);
 async function evaluate(jobs){
   const out=new Array(jobs.length);let next=0;
   await Promise.all(workers.map(w=>new Promise((resolve,reject)=>{
     let batch=[];
     const send=()=>{if(next>=jobs.length){resolve();return;}
       batch=[next++];const first=jobs[batch[0]],chunk=first.screen?Executor.chunkSize(jobs.length,count):1;
       while(batch.length<chunk&&next<jobs.length&&jobs[next].runs===first.runs&&jobs[next].seed===first.seed)batch.push(next++);
       w.postMessage({type:'run',id:batch[0],base,stage,n_runs:first.runs,seed:first.seed,teams:batch.map(i=>({...jobs[i],key:String(i)}))});};
     w.onerror=e=>reject(Error(e.message||e));
     w.onmessage=e=>{const m=e.data;if(m.type==='team')out[+m.key]=m.result;else if(m.type==='done')send();else if(m.type==='error')reject(Error(m.msg));};
     send();
   })));
   if(Array.from(out).some(x=>!x))throw Error('Missing worker result');return out;
 }
 return {evaluate,close:()=>workers.forEach(w=>w.terminate())};
}
const api={runtime,encoder,fallbackRequired,fixedEvaluation,run,workerPool};
if(node)module.exports=api;else root.LearnedRecoMeasure=api;
})(typeof window!=='undefined'?window:globalThis);
