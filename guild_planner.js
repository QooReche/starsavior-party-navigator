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
      const h=GS.runPhase({makeWorker:cx.makeWorker,pool,jobs,workers:Math.min(4,cx.workers||2),runs,seed,stage:cx.stage,base:cx.base,chunk:8,onProgress:cx.onProgress});cx.onHandle?.(h);
      const r=await h.promise;if(stale())throw Error('취소');if(jobs.some(j=>!r[j.key]))throw Error('길드 계산 결과가 누락됨');return r;
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
      const top=GS.pickTop(V,G,known,res,tiers,S.screen2.keep,S);
      // Audit representative level/support and alternative layouts on excluded samples.
      const selected=new Set(top.map(P.id)),sampled=aj.filter(j=>!selected.has(P.id(j.keys))).slice(0,12),auditJobs=[];
      for(const j of sampled)for(const p of P.variants(j.keys,results,Object.fromEntries(roster.map(r=>[r.key,r.placementTraits||[]]))))for(const level of [0,S.screen.level,12])for(const sup of GS.finalSupports(S,j.keys,cls))auditJobs.push(make(j.keys,level,sup,null,p));
      let representative={sampled:sampled.length,misses:0,rate:0};
      if(auditJobs.length){const ar=await run(auditJobs,S.screen.runs,1,'길드 대표 단계·지원·배치 놓침 감사'),edge=ranked(known,res)[Math.min(S.screen2.keep,known.length)-1]?.top||0,miss=new Map();
        for(const j of ranked(auditJobs,ar))if(j.top>=edge)miss.set(P.id(j.keys),j.keys);
        representative={sampled:sampled.length,misses:miss.size,rate:miss.size/sampled.length};for(const k of miss.values())top.push(k);
      }
      const traits=Object.fromEntries(roster.map(r=>[r.key,r.placementTraits||[]])),second=top.flatMap(k=>P.variants(k,results,traits).map(p=>make(k,undefined,undefined,null,p)));
      const rr=await run(second,S.screen2.runs,3,'길드 후보 복수 배치 비교');
      const finalists=GS.pickTop(V,G,second,rr,tiers,S.finalists,S),pre=[];
      for(const keys of finalists)for(const level of S.final.levels)for(const sup of GS.finalSupports(S,keys,cls))pre.push(make(keys,level,sup));
      const pr=await run(pre,Math.min(10,S.final.runs),4,'길드 단계·지원 예비 비교');
      const joint=[];
      // Effect boundaries from current season data, never role-based tactical rules.
      const boundary=G.challenge.levels.filter((l,i,a)=>i&&['skillStack','hpDrain','speed','immune'].some(k=>l[k]!==a[i-1][k])).map(l=>l.level);
      for(const keys of finalists){const scores=ranked(pre.filter(j=>P.id(j.keys)===P.id(keys)),pr).map(j=>({level:j.level,score:j.top})),levels=P.levels(scores,12,boundary,2);
        for(const p of P.all(keys))for(const level of levels)for(const sup of GS.finalSupports(S,keys,cls))for(const brk of [null,...(cx.breaks||[])])joint.push(make(keys,level,sup,brk,p));
      }
      const jr=await run(joint,S.placement?.screenRuns||2,5,'길드 배치·리더·단계·지원·브레이크 결합 비교'),counts=new Map(),keep=[];
      for(const j of ranked(joint,jr)){const k=P.id(j.keys),n=counts.get(k)||0;if(n<2){keep.push(j);counts.set(k,n+1);}}
      const final=await run(keep,S.final.runs,6,'길드 선택 후보 정밀 확인');
      return {rows:GS.rank(V,G,keep,final,tiers,5,S),pool:rows.length,combos,finalists:finalists.length,runs:S.final.runs,audit:quality,representative,placement:{version:P.VERSION,conditions:joint.length},growthOwned:second.map(j=>({...j,result:rr[j.key]}))};
    }finally{pool.close();}
  }
  const api={search,job};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GuildPlanner=api;
})(typeof window!=='undefined'?window:globalThis);
