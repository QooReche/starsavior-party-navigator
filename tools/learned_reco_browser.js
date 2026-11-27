// Measurement-only injection into the actual page. Product files are never edited.
// The normal recoEnsure -> recoCalculate -> real worker pool/UI remains in charge.
window.runLearnedRecoBrowser=async function(input,method,seed,onPhase){
 const M=LearnedRecoMeasure,uid=UiShared.teamKey,originalScreen=recoScreenCalculate,originalEvaluate=recoEvaluate,originalCandidates=recoCandidates;
 let prepared=null;const phases=[];let searchGames=0;
 const additions=new Map();
 const augment=all=>{const seen=new Set(all.map(t=>uid(t.keys)));for(const [key,t] of additions)if(!seen.has(key))all.push(t);};
 // run(true) rebuilds candidates after completion. Keep the measured outside-pool teams visible
 // for this one measurement, otherwise the final page redraw would silently drop C's winner.
 if(method==='C'||method.startsWith('U'))recoCandidates=(...args)=>{const result=originalCandidates(...args);
   if(args[0].key===input.c.key&&args[1].tab===input.st.tab&&args[1].name===input.st.name&&result.qt)augment(result.qt);
   return result;};
 SIMQ.seed=seed;SIMQ.n=100;
 recoEvaluate=async(snapshot,task,jobs,n,options={})=>{
   const started=performance.now(),games=jobs.reduce((s,j)=>s+(j.runs||n),0);
   searchGames+=games;
   try{return await originalEvaluate(snapshot,task,jobs,n,options);}
   finally{const label=options.label||(options.screen?'screen':'final/placement');phases.push({label,teams:jobs.length,runs:games,seconds:(performance.now()-started)/1000});onPhase(label,searchGames);}
 };
 if(method!=='F')recoScreenCalculate=async(snapshot,task,p,box)=>{
   const evaluate=jobs=>new Promise((resolve,reject)=>{
     const res=new Map();
     // Learning observations are all one-run jobs; the actual UI executor and chunk policy dispatch them.
     if(jobs.some(j=>j.runs!==1||j.seed!==seed))throw Error('Unexpected learning request');
     recoEvaluate(snapshot,task,jobs,1,{screen:true,label:'학습 선별 측정',onTeam:(j,r)=>res.set(j.key,r)})
       .then(()=>resolve(jobs.map(j=>res.get(j.key))),reject);
   });
   prepared=await M.run(input,D,D.cosmoRaid.search,method,seed,evaluate,onPhase,{selectionOnly:true});
   if(prepared.excluded)throw Error(prepared.excluded);
   const by=new Map(input.cands.map(x=>[x.s.key,x]));
   for(const keys of prepared.additions){
     const t=quickRank([{combo:keys.map(k=>by.get(k)),v:0,got:null}],snapshot.qi,snapshot.profile)[0];
     if(!t)throw Error('Outside-pool team cannot be serialized');additions.set(uid(keys),t);
   }
   augment(box.all);
   SIMQ.scr[snapshot.screenKey(p)]=prepared.sc;
   await originalScreen(snapshot,task,p,box);
 };
 const started=performance.now();
 try{
   await directRun('reco');
   if(!DIRECT.bundle?.steps.every(s=>s.status==='done'))throw Error('Actual recommendation bundle failed: '+JSON.stringify(DIRECT.bundle?.steps));
   const completed=await RECO.task.promise;
   await new Promise(requestAnimationFrame);
   const seconds=(performance.now()-started)/1000,c=contents[$('content').value],st=cur[$('stage').value],sc=SIMQ.scr[scrKey(st,1)];
   const spec=t=>({keys:t.keys,party:simParty(t),brk:teamBreak(t),result:SIMQ.res[simSig(st,t)]});
   if(uid(completed.team.keys)!==uid(LASTQ[1].rows[0].keys))throw Error('Final page redraw changed the locked winner');
   const winner=spec(LASTQ[1].rows[0]);if(!winner.result)throw Error('Actual page has no finalized winner');
   const others=LASTQ[1].rows.slice(0,5).map(spec).filter(t=>uid(t.keys)!==uid(winner.keys));
   // End the product search before independent evaluation; only one worker pool is resident.
   simPoolTrimIdle();
   const pool=M.workerPool(()=>new Worker('sim_worker.js'),8,c.key+'/'+st.tab+'/'+st.name,new URL('.',location.href).href);
   let independent,evaluationGames=0;
   try{
     const frozen=await M.fixedEvaluation(winner,others,async t=>{
       if(!independent){const all=[t,...others],jobs=all.map(t=>({key:uid(t.keys),party:t.party,runs:400,seed:20261127,
         options:{...input.options,break_skill:t.brk,raw_runs:true,rng_streams:true}}));
         evaluationGames=jobs.length*400;const res=await pool.evaluate(jobs);independent=new Map(all.map((t,i)=>[uid(t.keys),res[i]]));onPhase('independent400',searchGames+evaluationGames);}
       return independent.get(uid(t.keys));
     });
     return {method,seed,id:input.id,private:input.private,stage:c.key+'/'+st.tab+'/'+st.name,options:input.options,fullN:sc.fullN,
       learned:prepared?.learned||null,fallback:!!prepared?.fallback,seconds,searchGames,evaluationGames,phases,
       screen:{pool:sc.pool,order:sc.order,up:sc.up},...frozen,browserEntry:'actual directRun(reco) -> recoEnsure + UI + product executor'};
   }finally{pool.close();}
 }finally{recoScreenCalculate=originalScreen;recoEvaluate=originalEvaluate;recoCandidates=originalCandidates;}
};
