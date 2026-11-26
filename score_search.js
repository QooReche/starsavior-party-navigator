// Small score-search parts. Content adapters own policy and orchestration.
(function(root){
  'use strict';
  const compareBy=(...keys)=>(a,b)=>keys.reduce((v,key)=>v||key(a,b),0);
  const descending=value=>(a,b)=>value(b)-value(a);
  const goal=r=>r?(r.t60??r.clear):null;
  const guildRank=compareBy(descending(r=>r.top),descending(r=>r.cap),descending(r=>r.mean));
  const cosmoRank=mode=>{const k=mode==='top'?'top':'mean',o=k==='top'?'mean':'top';return compareBy(descending(r=>r[k]),descending(r=>r[o]),descending(r=>r.clear||0));};
  const recoRank=compareBy(descending(goal),descending(r=>r.clear),descending(r=>r.prog||0));
  function random(seed){let s=seed>>>0;return ()=>{s=(s+0x6D2B79F5)>>>0;let t=s;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};}
  function reservoir(a,e,n,seen,rng){if(a.length<n)a.push(e);else{const j=Math.floor(rng()*seen);if(j<n)a[j]=e;}}
  // Input is already ranked. Tie comparison deliberately excludes the identity key.
  function topRows(rows,n,{id=null,replace=false,ties=null}={}){
    if(id){const seen=new Map();for(const r of rows)if(replace||!seen.has(id(r)))seen.set(id(r),r);rows=[...seen.values()];}
    if(n==null)return rows;
    if(!ties)return rows.slice(0,n);
    const edge=rows[Math.max(0,n-1)];let end=0;
    while(end<rows.length&&(end<n||ties(rows[end],edge)===0))end++;
    return rows.slice(0,end);
  }
  async function fitScreen({learner,S,rows,seed,stale,encoder,makeJobs,evaluate,value}){
    const sample=await learner.sample(S,rows,seed,stale),jobs=makeJobs(sample);
    await evaluate(jobs);
    const model=await learner.train(encoder(),sample,jobs.map(value),S.learned,stale);
    return {sample,jobs,model};
  }
  async function evaluateMissing(jobs,results,valid,run){
    const missing=jobs.filter(j=>!valid(results[j.key]));
    if(missing.length)Object.assign(results,await run(missing));
    return missing.length;
  }
  function expandedSettings(S){const c=S.learned,f=c.fallbackMultiplier;return {...S,learned:{...c,K:c.K*f,M:c.M*f,A:c.A*f}};}
  // Sampling order and rescue/expansion remain adapter policy; this summarizes both strata.
  function placementAudit({sampled,boundary,random,ranked,id,value,edge}){
    const found=new Map();for(const r of ranked)if(value(r)>=edge)found.set(id(r),r);
    const misses=[...found.values()];
    return {misses,summary:{sampled:sampled.length,misses:misses.length,rate:sampled.length?misses.length/sampled.length:0,
      boundarySampled:boundary.length,randomSampled:random.length,randomMisses:random.filter(r=>found.has(id(r))).length}};
  }
  const api={compareBy,descending,goal,guildRank,cosmoRank,recoRank,random,reservoir,topRows,fitScreen,evaluateMissing,expandedSettings,placementAudit};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ScoreSearch=api;
})(typeof window!=='undefined'?window:globalThis);
