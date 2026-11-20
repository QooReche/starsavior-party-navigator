(function(root){
  'use strict';
  const GS=typeof module!=='undefined'&&module.exports?require('./guild_search.js'):root.GuildSearch;
  const L=typeof module!=='undefined'&&module.exports?require('./cosmo_learned.js'):root.CosmoLearned;
  const P=typeof module!=='undefined'&&module.exports?require('./party_placement.js'):root.PartyPlacement;
  function job(S,keys,results,cls,tiers,level,sup,brk,p){
    const party=GS.party(keys,results,cls,p);
    return {key:GS.jobKey(keys,level,sup,tiers,brk,party),keys,order:party.order,leaderKey:party.leaderKey,level,sup,party:party.spec,options:{guild:{level,sets:tiers.slice(),support:sup},break_skill:brk}};
  }
  async function search(cx){
    const {S,G,V,results,roster,tiers}=cx,rows=GS.pool(S,results,roster),cls=Object.fromEntries(roster.map(r=>[r.key,r.cls]));
    if(rows.length<4)throw Object.assign(Error('육성된 보유 구원자 4명 이상 필요'),{gwenCause:'few'});
    const combos=rows.length*(rows.length-1)*(rows.length-2)*(rows.length-3)/24;
    if(combos>S.learned.maxScoreCombos)throw Error('학습 순회 조합 상한을 넘음');
    const pool=GS.workerPool(cx.makeWorker),stale=cx.stale||(()=>false);
    const run=async(jobs,runs,seed,msg)=>{
      if(stale())throw Error('취소');cx.onPhase?.(msg,jobs.length);
      const h=GS.runPhase({makeWorker:cx.makeWorker,pool,jobs,workers:Math.max(1,Math.min(2,cx.workers||2)),runs,seed,stage:cx.stage,base:cx.base,chunk:8,onProgress:cx.onProgress});cx.onHandle?.(h);
      const r=await h.promise;if(stale())throw Error('취소');if(jobs.some(j=>!Number.isFinite(r[j.key]?.prog)||!Array.isArray(r[j.key]?.progs)))throw Error('길드 계산 결과가 누락됨');return r;
    };
    const make=(keys,level=S.screen.level,sup=S.screen.support||'none',brk=null,p)=>job(S,keys,results,cls,tiers,level,sup,brk,p);
    const score=(j,r)=>GS.rankStats(V,G,j.level,tiers,r.prog,r.progs,r.clear);
    const ranked=(jobs,res)=>jobs.map(j=>({...j,...score(j,res[j.key])})).sort((a,b)=>b.top-a.top||b.cap-a.cap||b.mean-a.mean||a.key.localeCompare(b.key));
    try{
      const sample=await L.sample(S,rows,cx.sampleSeed||20261120,stale),sj=sample.map(k=>make(k));
      const sr=await run(sj,S.screen.runs,1,'길드 전원 표본 학습');
      const model=await L.train(L.encoder(rows,results,roster),sample,sj.map(j=>score(j,sr[j.key]).top),S.learned,stale);
      let selection=await L.select(S,rows,model,stale),audit=await L.auditSample(S,rows,selection,(cx.sampleSeed||20261120)+1,stale);
      let jobs=[...selection.core.values()].map(e=>make(e.keys)),aj=audit.teams.map(k=>make(k)),res={...sr};
      const evaluate=async list=>{const missing=list.filter(j=>!res[j.key]);if(missing.length)Object.assign(res,await run(missing,S.screen.runs,1,'길드 학습 후보·감사'));};
      await evaluate([...jobs,...aj]);
      const quality=L.audit(S.learned,model.rho,jobs.map(j=>score(j,res[j.key]).top),aj.map(j=>score(j,res[j.key]).top),aj.length,audit.excluded,S.screen2.keep);
      if(quality.fallback){
        const c=S.learned,f=c.fallbackMultiplier,expanded={...S,learned:{...c,K:c.K*f,M:c.M*f,A:c.A*f}};
        selection=await L.select(expanded,rows,model,stale);
        jobs=[...selection.core.values()].map(e=>make(e.keys));
        await evaluate(jobs);quality.expanded=true;
      }
      const known=[...new Map([...jobs,...aj,...sj].map(j=>[j.key,j])).values()];
      const rankedKnown=ranked(known,res).map(j=>({...j,score:j.top}));
      const top=L.preserve(rankedKnown,rankedKnown.slice(0,S.screen2.keep),S.learned.M,new Set()).map(j=>j.keys);
      // Audit representative level/support and alternative layouts on excluded samples.
      const selected=new Set(top.map(P.id)),sampled=aj.filter(j=>!selected.has(P.id(j.keys))).slice(0,S.placement?.auditTeams??12),auditJobs=[];
      for(const j of sampled)for(const p of P.variants(j.keys,results,Object.fromEntries(roster.map(r=>[r.key,r.placementTraits||[]]))))for(const leaderKey of j.keys)for(const level of [0,S.screen.level,12])for(const sup of GS.finalSupports(S,j.keys,cls))auditJobs.push(make(j.keys,level,sup,null,{...p,leaderKey}));
      let representative={sampled:sampled.length,misses:0,rate:0};const rescued=[];
      if(auditJobs.length){const ar=await run(auditJobs,S.screen.runs,1,'길드 대표 단계·지원·배치 놓침 감사'),edge=ranked(known,res)[Math.min(S.screen2.keep,known.length)-1]?.top||0,miss=new Map();
        for(const j of ranked(auditJobs,ar))if(j.top>=edge)miss.set(P.id(j.keys),j.keys);
        representative={sampled:sampled.length,misses:miss.size,rate:miss.size/sampled.length};for(const k of miss.values()){top.push(k);rescued.push(k);}
        if(representative.rate>S.learned.missThreshold){for(const j of rankedKnown.slice(0,S.screen2.keep*2))if(!top.some(k=>P.id(k)===P.id(j.keys)))top.push(j.keys);representative.expanded=true;}
      }
      const traits=Object.fromEntries(roster.map(r=>[r.key,r.placementTraits||[]])),second=top.flatMap(k=>P.variants(k,results,traits).flatMap(p=>(representative.expanded?k:[p.leaderKey]).map(leaderKey=>make(k,undefined,undefined,null,{...p,leaderKey}))));
      const rr=await run(second,S.screen2.runs,3,'길드 후보 복수 배치 비교');
      const finalists=[...new Map([...GS.pickTop(V,G,second,rr,tiers,S.finalists,S),...rescued].map(k=>[P.id(k),k])).values()],keep=[];
      let conditions=0,moved=0;
      const boundary=[0,...G.challenge.levels.filter((l,i,a)=>i&&['skillStack','hpDrain','speed','immune'].some(k=>JSON.stringify(l[k])!==JSON.stringify(a[i-1][k]))).map(l=>l.level)];
      // Build and release one team's cross product at a time.
      for(const keys of finalists){
        const winner=ranked(second.filter(j=>P.id(j.keys)===P.id(keys)),rr)[0];
        const supports=GS.finalSupports(S,keys,cls),brks=[null,...(cx.breaks||[])];
        const pre=[...new Set([0,...S.final.levels])].flatMap(level=>supports.map(sup=>make(keys,level,sup,null,winner)));
        const pr=await run(pre,Math.min(10,S.final.runs),4,'길드 단계·지원 예비 비교');
        const levels=P.levels(ranked(pre,pr).map(j=>({level:j.level,score:j.top})),12,boundary,2);
        const joint=[];
        for(const p of [...P.all(keys),winner])for(const level of levels)for(const sup of supports)for(const brk of brks)joint.push(make(keys,level,sup,brk,p));
        const unique=[...new Map(joint.map(j=>[j.key,j])).values()];conditions+=unique.length;
        const jr=await run(unique,S.placement?.screenRuns||2,5,'길드 배치·리더·단계·지원·브레이크 결합 비교');
        const selected=ranked(unique,jr).slice(0,S.placement?.keep||2);
        const refined=await run(selected,S.final.runs,6,'길드 결합 후보 정밀 비교'),best=ranked(selected,refined)[0];
        const revisit=Array.from({length:13},(_,level)=>make(keys,level,best.sup,best.options.break_skill,best));
        const rv=await run(revisit,Math.min(10,S.final.runs),7,'길드 개선 배치로 전체 단계 재확인'),next=ranked(revisit,rv)[0];
        if(next.level!==best.level){const extra=[];moved++;
          for(const p of P.all(keys))for(const sup of supports)for(const brk of brks)extra.push(make(keys,next.level,sup,brk,p));
          const er=await run(extra,S.placement?.screenRuns||2,8,'길드 변경 단계 결합 재비교');selected.push(...ranked(extra,er).slice(0,S.placement?.keep||2));
        }
        keep.push(...selected);
      }
      const finalJobs=[...new Map(keep.map(j=>[j.key,j])).values()];
      const final=await run(finalJobs,S.final.runs,9,'길드 결합 후보 정밀 비교');
      return {rows:GS.rank(V,G,finalJobs,final,tiers,5,S),pool:rows.length,combos,finalists:finalists.length,runs:S.final.runs,audit:quality,representative,placement:{version:P.VERSION,conditions,moved},growthOwned:second.map(j=>({...j,result:rr[j.key]}))};
    }finally{pool.close();}
  }
  const api={search,job};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GuildPlanner=api;
})(typeof window!=='undefined'?window:globalThis);
