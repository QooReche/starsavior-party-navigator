// One changed savior per scenario. Pure scheduling, comparison and summary policy.
(function(root){
  'use strict';
  const LIMITS=Object.freeze({screenRuns:4, finalRuns:100, finalists:48, maxRuns:7200, maxMs:120000, companions:16});
  const COMPONENTS=Object.freeze({level:['level'],equipment:['equip'],skills:['skills'],potential:['resonance','journey','potentials']});
  function options(saved={},shared={}) {return {growth:!!(shared.ag??saved.growth),owned:(shared.ao??saved.owned)!==false};}
  const cmp=(a,b)=>b.clear-a.clear||(b.prog??0)-(a.prog??0)||(a.ttk??Infinity)-(b.ttk??Infinity);
  // sim_worker.run_auto + web.run_manual: 4 policy probes, selected policy, replay.
  const finalCost=(n,mode)=>mode==='manual'?2*n+4*Math.max(10,Math.floor(n/3))+1:n;
  const completed=r=>r.completed??Object.keys(r).length;
  const VERSION='growth-stage23-v4';
  function signature(s){return JSON.stringify([s.account,s.options,s.targets,s.preset,s.content,
    [...s.excluded].sort(),s.breaks,s.mode,s.rules,s.engine,s.data,s.modifiers,VERSION,
    s.season,s.difficulty,s.support,s.ranking,s.teams,s.equipment,s.policy]);}
  // Targets and stage differ across contents; all account/options/rules must agree.
  function compatible(a,b){if(!a||!b)return false;try{
    const context=s=>{const a=JSON.parse(s);if(a[12]!==VERSION)throw Error('old history');return a.filter((_,i)=>i!==2&&i!==4);};
    return JSON.stringify(context(a))===JSON.stringify(context(b));
  }catch{return false;}}
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
  function screenPlan(targets,width=2){const out=[],seen=new Set();
    for(let i=0;i<width;i++)for(const t of targets){const j=t.candidates?.[i];if(j&&!seen.has(j.id)){seen.add(j.id);out.push(j)}}
    for(const t of targets)for(const j of t.controls||[])if(!seen.has(j.id)){seen.add(j.id);out.push(j)}
    return out;
  }
  async function search({targets,owned,evaluate,mode='auto',limits={},alive=()=>true,now=()=>Date.now(),progress=()=>{},metric=null}){
    const rank=metric?.rank||cmp,screenRank=metric?.screenRank||rank,diff=metric?.compare||compare;
    const L={...LIMITS,...limits},start=now();let runs=0;
    const cost=finalCost(L.finalRuns,mode);
    const screen=screenPlan(targets).slice(0,Math.floor((L.maxRuns-cost)/L.screenRuns));
    const sr=await evaluate(screen,L.screenRuns,17011);runs+=completed(sr)*L.screenRuns;
    if(!alive())return null;
    const chosen=targets.map((t,i)=>({...t,best:(t.candidates||[]).filter(j=>sr[j.id]).sort((a,b)=>screenRank(sr[a.id],sr[b.id],i))[0]}));
    // New owned teams discovered by companion re-search may replace the baseline.
    // Always keep the established owned winner. Four-run controls cannot replace
    // its mature estimate or evict it before independent final evaluation.
    const established=owned.filter(j=>j.result).sort((a,b)=>rank(a.result,b.result))[0];
    const controls=new Map(owned.map(j=>[j.id,j]));
    for(const t of targets)for(const j of t.controls||[])if(sr[j.id]&&!controls.has(j.id))controls.set(j.id,{...j,result:sr[j.id]});
    const rankedOwned=[...controls.values()].filter(j=>j.result&&j.id!==established?.id).sort((a,b)=>screenRank(a.result,b.result));
    const bestOwned=(established?[established,...rankedOwned]:rankedOwned).slice(0,Math.min(3,Math.max(0,Math.floor((L.maxRuns-runs)/cost)-1)));
    const slots=Math.max(0,Math.floor((Math.floor((L.maxRuns-runs)/cost)-bestOwned.length)/(metric?2:1)));
    const ranked=chosen.filter(t=>t.best).sort((a,b)=>screenRank(sr[a.best.id],sr[b.best.id]));
    if(metric){const mean=ranked.slice(),cap=ranked.slice().sort((a,b)=>screenRank(sr[a.best.id],sr[b.best.id],1)),seen=new Set();ranked.length=0;
      for(let i=0;i<mean.length;i++)for(const t of [mean[i],cap[i]])if(!seen.has(t.id)){seen.add(t.id);ranked.push(t);}}
    const bundles=ranked.filter(t=>!t.component),first=bundles.slice(0,Math.min(24,slots));
    const components=first.flatMap(t=>Object.keys(COMPONENTS).map(k=>ranked.find(x=>x.parentId===t.id&&x.component===k)).filter(Boolean));
    const finalists=[...first,...components,...bundles.slice(first.length)].slice(0,Math.min(L.finalists,slots));
    progress('선발 완료 · 같은 판 수로 재평가');
    const jobs=bestOwned.concat(finalists.map(t=>t.best));
    // In four runs, top20 is just a maximum. Keep both mean and cap leaders.
    if(metric)for(const t of finalists){const cap=(t.candidates||[]).filter(j=>sr[j.id]).sort((a,b)=>screenRank(sr[a.id],sr[b.id],1))[0];
      const mean=(t.candidates||[]).filter(j=>sr[j.id]).sort((a,b)=>screenRank(sr[a.id],sr[b.id],0))[0];
      for(const j of [mean,cap])if(j&&!jobs.some(x=>x.id===j.id)&&runs+(jobs.length+1)*cost<=L.maxRuns)jobs.push(j);}
    const fr=now()-start<L.maxMs?await evaluate(jobs,L.finalRuns,900001):{};
    runs+=completed(fr)*cost;
    if(!alive())return null;
    if(metric)for(const t of chosen)t.best=(t.candidates||[]).filter(j=>fr[j.id]).sort((a,b)=>rank(fr[a.id],fr[b.id]))[0]||t.best;
    const baselinePending=!!(established&&!fr[established.id]);
    const baselineJob=baselinePending?null:bestOwned.filter(j=>fr[j.id]).sort((a,b)=>rank(fr[a.id],fr[b.id]))[0];
    const baseline=baselineJob?fr[baselineJob.id]:null;
    const rows=chosen.map(t=>{const result=t.best&&fr[t.best.id];return {id:t.id,key:t.key,kind:t.kind,source:t.source,
      component:t.component,parentId:t.parentId,changes:t.changes,changedFields:t.changedFields,presetId:t.presetId,status:result?'evaluated':t.error?'unsupported':t.best?'screened':'unevaluated',
      error:t.error,errorCode:t.errorCode,result:result||null,team:result?t.best:null,screened:(t.candidates||[]).filter(j=>sr[j.id]).length,
      ...(result?diff(result,baseline):{delta:null,ci:null,confirmed:false})}});
    return {rows,baseline,baselineJob,baselinePending,runs,ms:now()-start,scope:{targets:targets.length,evaluated:rows.filter(r=>r.result).length,
      screened:Object.keys(sr).length,companions:L.companions,maxRuns:L.maxRuns,maxMs:L.maxMs}};
  }
  function summary(result,content,signature,account,version){return {content,signature,account,version,historyVersion:VERSION,
    metric:result.metric||'clear',unit:result.unit||'%p',conditions:result.conditions||null,at:Date.now(),
    scope:result.scope,rows:result.rows.filter(r=>!r.component).map(({key,kind,delta,ci,confirmed,status})=>({key,kind,delta,ci,confirmed,status}))};}
  function save(storage,shared,entry){if(shared)return false;
    const old=storage.get('growth.history')||{},next=Object.fromEntries(Object.entries(old).filter(([,v])=>v.account===entry.account&&v.version===entry.version&&compatible(v.signature,entry.signature)));
    next[entry.content]=entry;const latest=Object.entries(next).sort((a,b)=>b[1].at-a[1].at).slice(0,30);
    return storage.set('growth.history',Object.fromEntries(latest));}
  function priority(history,signature){const by=new Map();
    for(const h of Object.values(history).filter(h=>compatible(h.signature,signature)))for(const r of h.rows){const id=r.key+'|'+r.kind;
      if(!by.has(id))by.set(id,{key:r.key,kind:r.kind,contents:[]});by.get(id).contents.push({...r,content:h.content,unit:h.unit||'%p',metric:h.metric||'clear'});}
    return [...by.values()].map(r=>({...r,count:new Set(r.contents.filter(c=>c.confirmed).map(c=>c.content.split('/')[0])).size}))
      .sort((a,b)=>{if(a.count!==b.count)return b.count-a.count;
        for(const id of [...new Set(a.contents.map(c=>c.content))].sort()){
          const x=a.contents.find(c=>c.content===id),y=b.contents.find(c=>c.content===id&&c.metric===x.metric&&c.unit===x.unit);
          if(y&&x.delta!=null&&y.delta!=null&&x.delta!==y.delta)return y.delta-x.delta;
        }return a.key.localeCompare(b.key)||a.kind.localeCompare(b.kind);});
  }
  // Seeded, independent resampling of individual runs; never score a mean progress.
  function bootstrap(a,b,stat,seed=27011,reps=1000){
    if(!a?.length||!b?.length)return null;
    let state=seed>>>0;const random=()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296;};
    const sample=x=>Array.from({length:x.length},()=>x[Math.floor(random()*x.length)]),ds=[];
    for(let i=0;i<reps;i++)ds.push(stat(sample(a))-stat(sample(b)));
    ds.sort((x,y)=>x-y);return [ds[Math.floor(reps*.025)],ds[Math.min(reps-1,Math.floor(reps*.975))]];
  }
  const topScore=s=>{const a=s.slice().sort((x,y)=>y-x),n=Math.max(1,Math.ceil(a.length*.2-1e-9));return Math.round(a.slice(0,n).reduce((v,x)=>v+x,0)/n);};
  function guildMetric(GS,V,G,level,tiers){return {
    prepare:r=>{if(!r?.progs?.length)return null;return {...r,...GS.rankStats(V,G,level,tiers,r.prog,r.progs,r.clear),
      scores:r.progs.map(p=>V.scoreFromProg(G,V.extraPct(G,level,tiers),p))};},
    rank:(a,b)=>b.top-a.top||b.cap-a.cap||b.mean-a.mean,
    screenRank:(a,b,i=0)=>i%2?(b.cap-a.cap||b.mean-a.mean):(b.mean-a.mean||b.cap-a.cap),
    compare:(r,b)=>{if(!b)return {delta:null,ci:null,confirmed:false};const ci=bootstrap(r.scores,b.scores,topScore);
      return {delta:r.top-b.top,ci,confirmed:!!ci&&ci[0]>0};}
  };}
  const COSMO_LIMITS=Object.freeze({...LIMITS,maxRuns:12000,maxMs:180000});
  // A scenario belongs to exactly one boss. Owned saviors retain their real keys.
  function cosmoTriples(CS,owned,assumed,n=1){return owned.flatMap((_,i)=>CS.bestTriples(
    owned.map((list,k)=>(i===k?assumed[k]:list).slice().sort((a,b)=>b.score-a.score)),n)).sort((a,b)=>b.sum-a.sum).slice(0,n);}
  async function searchCosmo({CS,targets,owned,established=[],evaluate,mode='top',limits={},alive=()=>true,now=()=>Date.now()}){
    const L={...COSMO_LIMITS,...limits},start=now();let runs=0;
    const unique=jobs=>[...new Map(jobs.map(j=>[j.id,j])).values()];
    const allOwned=unique([...owned.flat(),...targets.flatMap(t=>t.controls||[])]);
    const screen=unique([...owned.flat().filter(j=>!j.result),...screenPlan(targets,Math.max(0,...targets.map(t=>t.candidates?.length||0)))]).slice(0,Math.max(0,Math.floor(L.maxRuns*.45/L.screenRuns)));
    const sr=await evaluate(screen,L.screenRuns,17011);runs+=completed(sr)*L.screenRuns;if(!alive())return null;
    const entry=(j,r)=>r?.cosmo?{...j,keys:j.keys,score:CS.metric(r.cosmo,mode),result:r}:null;
    const lists=(jobs,res)=>[0,1,2].map(b=>jobs.filter(j=>j.bossIndex===b).map(j=>entry(j,res[j.id])).filter(Boolean).sort((a,b)=>b.score-a.score));
    const initial=Object.fromEntries(allOwned.filter(j=>j.result).map(j=>[j.id,j.result]));
    const diverse=(list,n)=>{const res=Object.fromEntries(list.map(j=>[j.id,j.result]));
      const keys=new Set(CS.pickDiverse(list.map(j=>({...j,key:j.id})),res,mode,n).map(e=>CS.idOf(e.keys)));
      return list.filter(j=>keys.has(CS.idOf(j.keys))||established.some(e=>e.id===j.id));};
    const ownedLists=lists(allOwned,{...initial,...sr}).map(list=>diverse(list,24));
    const bestOwned=CS.bestTriples(ownedLists,3);
    const keep=unique([...established,...bestOwned.flatMap(t=>t.teams),...ownedLists.flatMap(list=>diverse(list,6))]);
    const chosen=targets.map(t=>({...t,triples:cosmoTriples(CS,ownedLists,lists(t.candidates||[],sr),3)}));
    const ranked=chosen.filter(t=>t.triples.length).sort((a,b)=>Number(!!a.component)-Number(!!b.component)||b.triples[0].sum-a.triples[0].sum);
    // Reserve whole scenarios, including original owned versions of every new team.
    // Discovery changes the baseline as well as the proposed three-team lineup.
    const jobs=new Map(keep.map(j=>[j.id,j])),selected=[];
    for(const t of ranked){const needed=unique([...t.triples.flatMap(x=>x.teams),...(t.controls||[])]);
      const add=needed.filter(j=>!jobs.has(j.id));
      if(selected.length>=L.finalists||runs+(jobs.size+add.length)*L.finalRuns>L.maxRuns)continue;
      add.forEach(j=>jobs.set(j.id,j));selected.push(t.id);
    }
    const affordable=runs+jobs.size*L.finalRuns<=L.maxRuns;
    const fr=affordable&&now()-start<L.maxMs?await evaluate([...jobs.values()],L.finalRuns,900001):{};
    runs+=completed(fr)*L.finalRuns;if(!alive())return null;
    const baselinePending=keep.some(j=>!fr[j.id]);
    const finalOwned=lists(allOwned,fr),baseline=baselinePending?null:CS.bestTriples(finalOwned,1)[0]||null;
    const rows=chosen.map(t=>{
      const complete=selected.includes(t.id)&&(t.controls||[]).every(j=>fr[j.id]);
      const triple=complete?cosmoTriples(CS,finalOwned,lists(t.candidates||[],fr),1)[0]:null;
      return {...t,candidates:undefined,controls:undefined,triples:undefined,team:triple,result:triple?{sum:triple.sum,n:L.finalRuns}:null,
        status:triple?'evaluated':t.error?'unsupported':t.triples.length?'screened':'unevaluated',
        delta:triple&&baseline?triple.sum-baseline.sum:null,ci:null,confirmed:false};
    });
    return {rows,baseline,baselinePending,runs,ms:now()-start,metric:'cosmo-'+mode,unit:'점',
      scope:{targets:targets.length,evaluated:rows.filter(r=>r.result).length,maxRuns:L.maxRuns,maxMs:L.maxMs}};
  }
  const api={VERSION,LIMITS,COSMO_LIMITS,COMPONENTS,options,cmp,finalCost,signature,compatible,interval,compare,screenPlan,search,summary,save,priority,
    bootstrap,topScore,guildMetric,cosmoTriples,searchCosmo};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GrowthGuide=api;
})(typeof window!=='undefined'?window:globalThis);
