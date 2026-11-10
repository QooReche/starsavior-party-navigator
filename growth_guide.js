// One changed savior per scenario. Pure scheduling, comparison and summary policy.
(function(root){
  'use strict';
  const LIMITS=Object.freeze({screenRuns:4, finalRuns:100, finalists:48, maxRuns:7200, maxMs:120000, companions:16});
  const COMPONENTS=Object.freeze({level:['level'],equipment:['equip'],skills:['skills'],potential:['resonance','journey','potentials']});
  function options(saved={},shared={}) {return {growth:!!(shared.ag??saved.growth),owned:(shared.ao??saved.owned)!==false};}
  const cmp=(a,b)=>b.clear-a.clear||(b.prog??0)-(a.prog??0)||(a.ttk??Infinity)-(b.ttk??Infinity);
  // sim_worker.run_auto + web.run_manual: 4 policy probes, selected policy, replay.
  const finalCost=(n,mode)=>mode==='manual'?2*n+4*Math.max(10,Math.floor(n/3))+1:n;
  function signature(s){return JSON.stringify([s.account,s.options,s.targets,s.preset,s.content,
    [...s.excluded].sort(),s.breaks,s.mode,s.rules,s.engine,s.data,s.modifiers]);}
  // Targets and stage differ across contents; all account/options/rules must agree.
  function compatible(a,b){if(!a||!b)return false;try{
    const context=s=>JSON.parse(s).filter((_,i)=>i!==2&&i!==4);
    return JSON.stringify(context(a))===JSON.stringify(context(b));
  }catch{return a===b;}}
  function interval(r){
    const n=r.n,p=r.clear,z=1.96,d=1+z*z/n,m=(p+z*z/(2*n))/d,
      e=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;
    return [Math.max(0,m-e),Math.min(1,m+e)];
  }
  function compare(result,baseline){
    if(!baseline)return {delta:null,ci:null,confirmed:false};
    const a=interval(result),b=interval(baseline),ci=[100*(a[0]-b[1]),100*(a[1]-b[0])];
    return {delta:100*(result.clear-baseline.clear),ci,confirmed:ci[0]>0};
  }
  // Alternate quick/approximate selections for every target before adding controls.
  function screenPlan(targets){const out=[],seen=new Set();
    for(let i=0;i<2;i++)for(const t of targets){const j=t.candidates?.[i];if(j&&!seen.has(j.id)){seen.add(j.id);out.push(j)}}
    for(const t of targets)for(const j of t.controls||[])if(!seen.has(j.id)){seen.add(j.id);out.push(j)}
    return out;
  }
  async function search({targets,owned,evaluate,mode='auto',limits={},alive=()=>true,now=()=>Date.now(),progress=()=>{}}){
    const L={...LIMITS,...limits},start=now();let runs=0;
    const cost=finalCost(L.finalRuns,mode);
    const screen=screenPlan(targets).slice(0,Math.floor((L.maxRuns-cost)/L.screenRuns));
    const sr=await evaluate(screen,L.screenRuns,17011);runs+=Object.keys(sr).length*L.screenRuns;
    if(!alive())return null;
    const chosen=targets.map(t=>({...t,best:(t.candidates||[]).filter(j=>sr[j.id]).sort((a,b)=>cmp(sr[a.id],sr[b.id]))[0]}));
    // New owned teams discovered by companion re-search may replace the baseline.
    // Always keep the established owned winner. Four-run controls cannot replace
    // its mature estimate or evict it before independent final evaluation.
    const established=owned.filter(j=>j.result).sort((a,b)=>cmp(a.result,b.result))[0];
    const controls=new Map(owned.map(j=>[j.id,j]));
    for(const t of targets)for(const j of t.controls||[])if(sr[j.id]&&!controls.has(j.id))controls.set(j.id,{...j,result:sr[j.id]});
    const rankedOwned=[...controls.values()].filter(j=>j.result&&j.id!==established?.id).sort((a,b)=>cmp(a.result,b.result));
    const bestOwned=(established?[established,...rankedOwned]:rankedOwned).slice(0,Math.min(3,Math.max(0,Math.floor((L.maxRuns-runs)/cost)-1)));
    const slots=Math.max(0,Math.floor((L.maxRuns-runs)/cost)-bestOwned.length);
    const ranked=chosen.filter(t=>t.best).sort((a,b)=>cmp(sr[a.best.id],sr[b.best.id]));
    const bundles=ranked.filter(t=>!t.component),first=bundles.slice(0,Math.min(24,slots));
    const components=first.flatMap(t=>Object.keys(COMPONENTS).map(k=>ranked.find(x=>x.parentId===t.id&&x.component===k)).filter(Boolean));
    const finalists=[...first,...components,...bundles.slice(first.length)].slice(0,Math.min(L.finalists,slots));
    progress('선발 완료 · 같은 판 수로 재평가');
    const jobs=bestOwned.concat(finalists.map(t=>t.best));
    const fr=now()-start<L.maxMs?await evaluate(jobs,L.finalRuns,900001):{};
    runs+=Object.keys(fr).length*cost;
    if(!alive())return null;
    const baselinePending=!!(established&&!fr[established.id]);
    const baselineJob=baselinePending?null:bestOwned.filter(j=>fr[j.id]).sort((a,b)=>cmp(fr[a.id],fr[b.id]))[0];
    const baseline=baselineJob?fr[baselineJob.id]:null;
    const rows=chosen.map(t=>{const result=t.best&&fr[t.best.id];return {id:t.id,key:t.key,kind:t.kind,source:t.source,
      component:t.component,parentId:t.parentId,changes:t.changes,changedFields:t.changedFields,presetId:t.presetId,status:result?'evaluated':t.error?'unsupported':t.best?'screened':'unevaluated',
      error:t.error,errorCode:t.errorCode,result:result||null,team:result?t.best:null,screened:(t.candidates||[]).filter(j=>sr[j.id]).length,
      ...(result?compare(result,baseline):{delta:null,ci:null,confirmed:false})}});
    return {rows,baseline,baselineJob,baselinePending,runs,ms:now()-start,scope:{targets:targets.length,evaluated:rows.filter(r=>r.result).length,
      screened:Object.keys(sr).length,companions:L.companions,maxRuns:L.maxRuns,maxMs:L.maxMs}};
  }
  function summary(result,content,signature,account,version){return {content,signature,account,version,at:Date.now(),
    scope:result.scope,rows:result.rows.filter(r=>!r.component).map(({key,kind,delta,ci,confirmed,status})=>({key,kind,delta,ci,confirmed,status}))};}
  function save(storage,shared,entry){if(shared)return false;
    const old=storage.get('growth.history')||{},next=Object.fromEntries(Object.entries(old).filter(([,v])=>v.account===entry.account&&v.version===entry.version&&compatible(v.signature,entry.signature)));
    next[entry.content]=entry;const latest=Object.entries(next).sort((a,b)=>b[1].at-a[1].at).slice(0,30);
    return storage.set('growth.history',Object.fromEntries(latest));}
  function priority(history,signature){const by=new Map();
    for(const h of Object.values(history).filter(h=>compatible(h.signature,signature)))for(const r of h.rows){const id=r.key+'|'+r.kind;
      if(!by.has(id))by.set(id,{key:r.key,kind:r.kind,contents:[]});by.get(id).contents.push({...r,content:h.content});}
    return [...by.values()].map(r=>({...r,count:new Set(r.contents.filter(c=>c.confirmed).map(c=>c.content.split('/')[0])).size}))
      .sort((a,b)=>b.count-a.count||Math.max(...b.contents.map(c=>c.delta??-Infinity))-Math.max(...a.contents.map(c=>c.delta??-Infinity))||a.key.localeCompare(b.key));
  }
  const api={VERSION:'bundle-slots-v3',LIMITS,COMPONENTS,options,cmp,finalCost,signature,compatible,interval,compare,screenPlan,search,summary,save,priority};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GrowthGuide=api;
})(typeof window!=='undefined'?window:globalThis);
