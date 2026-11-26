(function(root){
  'use strict';
  const GS=typeof module!=='undefined'&&module.exports?require('./guild_search.js'):root.GuildSearch;
  const L=typeof module!=='undefined'&&module.exports?require('./cosmo_learned.js'):root.CosmoLearned;
  const P=typeof module!=='undefined'&&module.exports?require('./party_placement.js'):root.PartyPlacement;
  const E=typeof module!=='undefined'&&module.exports?require('./search_executor.js'):root.SearchExecutor;
  const PS=typeof module!=='undefined'&&module.exports?require('./placement_search.js'):root.PlacementSearch;
  function plan(S,combos,nBrk){
    const second=Math.min(combos,S.screen2.keep),finalists=Math.min(second,S.finalists);
    const stages=E.planStages([
      {id:1,name:'조합 훑기',jobs:combos,runs:S.screen.runs},
      {id:2,name:'상위 후보 확인',jobs:second,runs:S.screen2.runs,upper:true},
      {id:3,name:'별의 도전 단계·지원 비교',jobs:finalists*S.final.levels.length*S.final.supports.length,runs:S.final.runs,upper:true},
      {id:4,name:'브레이크 비교',jobs:nBrk?Math.min(GS.BREAK_CHECK.teams,finalists)*3*(1+nBrk):0,runs:GS.BREAK_CHECK.runs,upper:true,p:nBrk?1:0,condition:'보유 브레이크와 적격 후보가 있을 때'}
    ]);
    return {version:1,stages,total:stages.reduce((n,s)=>n+s.games,0)};
  }
  function job(S,keys,results,cls,tiers,level,sup,brk,p){
    const party=GS.party(keys,results,cls,(p?.leaderKey?p:undefined)||(S.placement?.baseline?P.baseline(keys,results):undefined));
    return {key:GS.jobKey(keys,level,sup,tiers,brk,party,S),keys,order:party.order,leaderKey:party.leaderKey,level,sup,party:party.spec,options:{guild:{seasonId:S.seasonId,dataVersion:S.dataVersion,level,sets:tiers.slice(),support:sup},break_skill:brk}};
  }
  // 200c2d3 page pipeline: preserve candidates, ordering, seeds, runs and break recheck.
  async function searchLegacy(cx){
    const {S,G,V,results,roster,tiers}=cx,cls=Object.fromEntries(roster.map(r=>[r.key,r.cls]));
    const rows=GS.pool(S,results,roster),combos=GS.combos(S,rows);
    if(!combos.length)throw Object.assign(Error('편성할 수 있는 구원자가 부족함(내 정보에 육성된 구원자 4명 이상 필요)'),{gwenCause:'few'});
    const stale=cx.stale||(()=>false);
    const pl=plan(S,combos.length,(cx.breaks||[]).length);cx.onPlan?.(pl);
    let phase=0,fin=[],history=[];
    const run=async(jobs,runs,seed,msg)=>{
      if(stale())throw Object.assign(Error('취소'),{gwenCause:'cancel'});
      if(cx.partialRequested?.())throw Object.assign(Error('취소'),{gwenCause:'cancel'});
      const stage=phase++;cx.onPhase?.(msg,jobs.length,{stage,jobs:jobs.length,teams:jobs.length,runs,games:jobs.length*runs});
      const h=GS.runPhase({makeWorker:cx.makeWorker,jobs,workers:Math.max(1,Math.min(2,cx.workers||2)),runs,seed,stage:cx.stage,base:cx.base,watch:cx.watch,onProgress:cx.onProgress});
      const record={jobs,runs,seed,stage,handle:h,res:null};history.push(record);
      cx.onHandle?.(h);const res=await h.promise;record.res=res;
      if(stale())throw Object.assign(Error('취소'),{gwenCause:'cancel'});
      return res;
    };
    const coverage=selectedStage=>({version:1,selectedStage,stages:history.map(r=>{const res=r.res||r.handle.snapshot();return {stage:r.stage+1,name:pl.stages[r.stage].name,jobs:r.jobs.length,
      done:r.jobs.filter(j=>res[j.key]).length,runs:r.runs,seed:r.seed,complete:!!r.res};})});
    try{
    const jobsA=GS.screenJobs(S,G,V,combos,results,cls,tiers,G);
    const resA=await run(jobsA,S.screen.runs,1,`1단계: 조합 ${jobsA.length}개 훑어보는 중(처음 한 번은 계산 엔진을 내려받느라 1~3분 더 걸림)`);
    const keep2=GS.pickTop(V,G,jobsA,resA,tiers,S.screen2.keep,S),jobsA2=GS.screenJobs(S,G,V,keep2,results,cls,tiers,G);
    const resA2=await run(jobsA2,S.screen2.runs,3,`2단계: 상위 ${jobsA2.length}팀을 더 정확히 확인 중`);
    fin=GS.pickFinalists(S,V,G,jobsA2,resA2,tiers);const jobsB=GS.finalJobs(S,G,V,fin,results,cls,tiers,G);
    const resB=await run(jobsB,S.final.runs,2,`3단계: 상위 ${fin.length}팀을 단계·지원별로 확인 중`);
    const pairs=[[jobsA,resA],[jobsA2,resA2],[jobsB,resB]];
    let ranked=GS.rank(V,G,jobsB,resB,tiers,GS.BREAK_CHECK.teams,S);
    const jobsC=GS.breakJobs(ranked,cx.breaks||[],results,cls,tiers,G);
    if(jobsC.length){
      const resC=await run(jobsC,GS.BREAK_CHECK.runs,2,'4단계: 브레이크 스킬 확인 중');
      pairs.push([jobsC,resC]);ranked=GS.rank(V,G,jobsC,resC,tiers,5,S);
    }
    return {rows:ranked.slice(0,5),dropped:GS.countDropped(S,pairs),pool:rows.length,combos:combos.length,finalists:fin.length,runs:jobsC.length?GS.BREAK_CHECK.runs:S.final.runs,partial:false,coverage:coverage(jobsC.length?4:3)};
    }catch(e){
      if(stale()||e.gwenCause!=='cancel'||!cx.partialRequested?.())throw e;
      const pairs=history.map(r=>[r.jobs,r.res||r.handle.snapshot()]);let selected=null,ranked=[];
      for(let i=history.length-1;i>=0;i--){
        const [jobs,res]=pairs[i];ranked=GS.rank(V,G,jobs.filter(j=>res[j.key]),res,tiers,5,S);
        if(ranked.length){selected=history[i];break;}
      }
      const evaluation={partial:true,stage:(selected?.stage??-1)+1,stageSupportComplete:!!history[2]?.res,breakComplete:!!history[3]?.res};
      return {rows:ranked.map(r=>({...r,evaluation:{...evaluation}})),dropped:GS.countDropped(S,pairs),pool:rows.length,combos:combos.length,
        finalists:fin.length,runs:selected?.runs||0,partial:true,coverage:coverage(evaluation.stage)};
    }
  }
  async function search(cx){
    cx={...cx,S:{...cx.S,seasonId:cx.G.season?.id,dataVersion:cx.G.dataVersion}};
    if(cx.S.newSearch !== true)return searchLegacy(cx);
    const {S,G,V,results,roster,tiers}=cx,rows=GS.pool(S,results,roster),cls=Object.fromEntries(roster.map(r=>[r.key,r.cls]));
    if(rows.length<4)throw Object.assign(Error('육성된 보유 구원자 4명 이상 필요'),{gwenCause:'few'});
    const combos=rows.length*(rows.length-1)*(rows.length-2)*(rows.length-3)/24;
    if(combos>S.learned.maxScoreCombos)throw Error('학습 순회 조합 상한을 넘음');
    const pool=GS.workerPool(cx.makeWorker),stale=cx.stale||(()=>false);
    const run=async(jobs,runs,seed,msg)=>{
      if(stale())throw Error('취소');cx.onPhase?.(msg,jobs.length);
      const h=GS.runPhase({makeWorker:cx.makeWorker,pool,jobs,workers:Math.max(1,Math.min(2,cx.workers||2)),runs,seed,stage:cx.stage,base:cx.base,watch:cx.watch,chunk:S.execution?.chunk||8,onProgress:cx.onProgress});cx.onHandle?.(h);
      const r=await h.promise;if(stale())throw Error('취소');if(jobs.some(j=>!Number.isFinite(r[j.key]?.prog)||!Array.isArray(r[j.key]?.progs)))throw Error('길드 계산 결과가 누락됨');return r;
    };
    const make=(keys,level=S.screen.level,sup=S.screen.support||'none',brk=null,p)=>job(S,keys,results,cls,tiers,level,sup,brk,p);
    const score=(j,r)=>GS.rankStats(V,G,j.level,tiers,r.prog,r.progs,r.clear,r.guild);
    const ranked=(jobs,res)=>jobs.map(j=>({...j,...score(j,res[j.key])})).sort((a,b)=>b.top-a.top||b.cap-a.cap||b.mean-a.mean||a.key.localeCompare(b.key));
    try{
      const sample=await L.sample(S,rows,cx.sampleSeed||20261120,stale),sj=sample.map(k=>make(k));
      const sr=await run(sj,S.screen.runs,1,'길드 전원 표본 학습');
      const model=await L.train(L.encoder(rows,results,roster,S.placement),sample,sj.map(j=>score(j,sr[j.key]).top),S.learned,stale);
      let selection=await L.select(S,rows,model,stale),audit=await L.auditSample(S,rows,selection,(cx.sampleSeed||20261120)+1,stale);
      let jobs=[...selection.core.values()].map(e=>make(e.keys)),aj=audit.teams.map(k=>make(k)),res={...sr};
      const evaluate=async list=>{const missing=list.filter(j=>!res[j.key]);if(missing.length)Object.assign(res,await run(missing,S.screen.runs,1,'길드 학습 후보·감사'));};
      await evaluate([...jobs,...aj]);
      const quality=L.audit(S.learned,model.rho,jobs.map(j=>score(j,res[j.key]).top),aj.map(j=>score(j,res[j.key]).top),aj.length,audit.excluded,S.screen2.keep);
      if(quality.fallback){
        const c=S.learned,f=c.fallbackMultiplier,expanded={...S,learned:{...c,K:c.K*f,M:c.M*f,A:c.A*f}};
        selection=await L.select(expanded,rows,model,stale);
        jobs=[...selection.core.values()].map(e=>make(e.keys));
        const more=await L.auditSample(expanded,rows,selection,(cx.sampleSeed||20261120)+2,stale);
        aj=[...new Map([...aj,...more.teams.map(k=>make(k))].map(j=>[j.key,j])).values()];
        await evaluate([...jobs,...aj]);quality.expanded=true;quality.expandedAudit=more.teams.length;
      }
      const known=[...new Map([...jobs,...aj,...sj].map(j=>[j.key,j])).values()];
      const rankedKnown=ranked(known,res).map(j=>({...j,score:j.top}));
      const top=L.preserve(rankedKnown,rankedKnown.slice(0,S.screen2.keep),S.learned.M,new Set()).map(j=>j.keys);
      // Audit representative level/support and alternative layouts on excluded samples.
      const selected=new Set(top.map(P.id)),auditN=S.placement?.enabled?(S.placement.auditTeams??12):0;
      const auditBoundary=rankedKnown.filter(j=>!selected.has(P.id(j.keys))).slice(0,Math.floor(auditN/2)),boundaryIds=new Set(auditBoundary.map(j=>P.id(j.keys)));
      const random=aj.filter(j=>!selected.has(P.id(j.keys))&&!boundaryIds.has(P.id(j.keys))).slice(0,auditN-auditBoundary.length),sampled=[...auditBoundary,...random],auditJobs=[];
      for(const j of sampled)for(const p of P.variants(j.keys,results,Object.fromEntries(roster.map(r=>[r.key,r.placementTraits||[]]))))for(const leaderKey of j.keys)for(const level of [0,S.screen.level,G.challenge.levels.length])for(const sup of GS.finalSupports(S,j.keys,cls))auditJobs.push(make(j.keys,level,sup,null,leaderKey?{...p,leaderKey}:undefined));
      let representative={sampled:sampled.length,misses:0,rate:0};const rescued=[];
      if(auditJobs.length){const ar=await run(auditJobs,S.screen.runs,1,'길드 대표 단계·지원·배치 놓침 감사'),edge=ranked(known,res)[Math.min(S.screen2.keep,known.length)-1]?.top||0,miss=new Map();
        for(const j of ranked(auditJobs,ar))if(j.top>=edge)miss.set(P.id(j.keys),j.keys);
        representative={sampled:sampled.length,misses:miss.size,rate:miss.size/sampled.length,boundarySampled:auditBoundary.length,randomSampled:random.length,randomMisses:random.filter(j=>miss.has(P.id(j.keys))).length};for(const k of miss.values()){top.push(k);rescued.push(k);}
        if(representative.rate>S.learned.missThreshold){for(const j of rankedKnown.slice(0,S.screen2.keep*2))if(!top.some(k=>P.id(k)===P.id(j.keys)))top.push(j.keys);representative.expanded=true;}
      }
      const traits=Object.fromEntries(roster.map(r=>[r.key,r.placementTraits||[]]));
      let second=top.flatMap(k=>(S.placement?.enabled?P.variants(k,results,traits):[GS.party(k,results,cls,S.placement?.baseline?P.baseline(k,results):undefined)]).flatMap(p=>(representative.expanded?k:[p.leaderKey]).map(leaderKey=>make(k,undefined,undefined,null,leaderKey?{...p,leaderKey}:undefined))));
      if(representative.expanded){const sr=await run(second,S.placement?.screenRuns||2,13,'길드 확대 후보 배치·리더 예비 비교'),seen=new Map();
        second=ranked(second,sr).filter(j=>{const k=P.id(j.keys),n=seen.get(k)||0;seen.set(k,n+1);return n<(S.placement?.keep||2);});}
      const rr=await run(second,S.screen2.runs,3,'길드 후보 복수 배치 비교');
      const finalists=[...new Map([...GS.pickTop(V,G,second,rr,tiers,S.finalists,S),...rescued].map(k=>[P.id(k),k])).values()],keep=[];
      let conditions=0,moved=0;
      const boundary=[0,...G.challenge.levels.filter((l,i,a)=>i&&['skillStack','hpDrain','speed','immune'].some(k=>JSON.stringify(l[k])!==JSON.stringify(a[i-1][k]))).map(l=>l.level)];
      // Build and release one team's cross product at a time.
      for(const keys of finalists){
        const winner=ranked(second.filter(j=>P.id(j.keys)===P.id(keys)),rr)[0];
        const supports=GS.finalSupports(S,keys,cls),brks=[null,...(cx.breaks||[])];
        const pre=[...new Set([0,...S.final.levels])].flatMap(level=>supports.map(sup=>make(keys,level,sup,null,winner)));
        const stages={probe:[Math.min(10,S.final.runs),4,'길드 단계·지원 예비 비교'],screen:[S.placement?.screenRuns||2,5,'길드 배치·리더·단계·지원·브레이크 결합 비교'],refine:[S.final.runs,6,'길드 결합 후보 정밀 비교'],revisit:[Math.min(10,S.final.runs),7,'길드 개선 배치로 전체 단계 재확인'],moved:[S.placement?.screenRuns||2,8,'길드 변경 단계 결합 재비교']};
        const joint=await PS.joint({teams:[winner],probeJobs:pre,rank:ranked,group:j=>P.id(j.keys),keep:S.placement?.keep||2,
          runStage:(stage,jobs)=>run(jobs,...stages[stage]),
          jointJobs:(_,pre,pr)=>{
            const levels=P.levels(ranked(pre,pr).map(j=>({level:j.level,score:j.top})),G.challenge.levels.length,boundary,2),jobs=[];
            for(const p of (S.placement?.enabled?[...P.all(keys),winner]:[winner]))for(const level of levels)for(const sup of supports)for(const brk of brks)jobs.push(make(keys,level,sup,brk,p));
            return [...new Map(jobs.map(j=>[j.key,j])).values()];
          },
          revisitJobs:([best])=>Array.from({length:G.challenge.levels.length+1},(_,level)=>make(keys,level,best.sup,best.options.break_skill,best)),
          movedJobs:changed=>changed.flatMap(next=>(S.placement?.enabled?P.all(keys):[winner]).flatMap(p=>supports.flatMap(sup=>brks.map(brk=>make(keys,next.level,sup,brk,p)))))
        });
        conditions+=joint.conditions;moved+=joint.changed;keep.push(...joint.selected,...joint.extra);
      }
      const finalJobs=[...new Map(keep.map(j=>[j.key,j])).values()];
      const final=await run(finalJobs,S.final.runs,9,'길드 결합 후보 정밀 비교');
      return {rows:GS.rank(V,G,finalJobs,final,tiers,5,S),dropped:0,pool:rows.length,combos,finalists:finalists.length,runs:S.final.runs,audit:quality,representative,placement:{version:P.VERSION,conditions,moved},growthOwned:second.map(j=>({...j,result:rr[j.key]}))};
    }finally{pool.close();}
  }
  const api={search,job,plan};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GuildPlanner=api;
})(typeof window!=='undefined'?window:globalThis);
