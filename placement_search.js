// Joint layout/leader/difficulty/break evaluation. No engine or UI dependencies.
(function(root){
  'use strict';
  const P=typeof module!=='undefined'&&module.exports?require('./party_placement.js'):root.PartyPlacement;
  const group=j=>j.boss+'|'+P.id(j.keys);
  const cmp=mode=>(a,b)=>{const x=a.cosmo,y=b.cosmo,k=mode==='top'?'top':'mean',o=k==='top'?'mean':'top';return y[k]-x[k]||y[o]-x[o]||(y.clear||0)-(x.clear||0);};
  async function cosmo({teams,makeJob,run,mode,level,maxLevel,auto,breaks,runs,probeRuns,boundaries={},stale=()=>false,settings={}}){
    const allLevels=auto?Array.from({length:maxLevel+1},(_,i)=>i):[level],brks=[null,...breaks];
    const probeJobs=teams.flatMap(t=>allLevels.map(l=>makeJob(t,l,null,t)));
    const probe=await run(probeJobs,probeRuns,5,'난이도 예비 비교');
    P.best(probeJobs,probe,cmp(mode),r=>!!r?.cosmo);
    const jobs=[];
    for(const t of teams){
      const scores=probeJobs.filter(j=>group(j)===group(t)).map(j=>({level:j.level,score:probe[j.key].cosmo[mode]}));
      const levels=auto?P.levels(scores,maxLevel,boundaries[t.boss]||[],2):[level];
      const layouts=P.all(t.keys);
      // Keep the rerank winner too: within-row tie order can matter in the engine.
      if(!layouts.some(p=>P.executionKey(t.keys,p)===P.executionKey(t.keys,t)))layouts.push(t);
      for(const p of layouts)for(const l of levels)for(const b of brks)jobs.push(makeJob(t,l,b,p));
    }
    if(stale())throw Error('취소');
    const first=await run(jobs,settings.screenRuns||2,6,'배치·리더·난이도·브레이크 결합 비교');
    const ranked=P.best(jobs,first,cmp(mode),r=>!!r?.cosmo),groups=new Map();
    for(const j of ranked){const k=group(j);if(!groups.has(k))groups.set(k,[]);if(groups.get(k).length<(settings.keep||2))groups.get(k).push(j);}
    const selected=[...groups.values()].flat();
    const refined=await run(selected,runs,7,'결합 후보 정밀 비교');
    const best=new Map();
    for(const j of P.best(selected,refined,cmp(mode),r=>!!r?.cosmo))if(!best.has(group(j)))best.set(group(j),j);
    // Revisit every level with the improved arrangement and break. If the optimum moves,
    // all 24 arrangements and all breaks are compared again at that level.
    const reJobs=[...best.values()].flatMap(t=>allLevels.map(l=>makeJob(t,l,t.brk,t)));
    const re=await run(reJobs,probeRuns,8,'개선 배치로 전체 난이도 재확인');
    const reBest=new Map();
    for(const j of P.best(reJobs,re,cmp(mode),r=>!!r?.cosmo))if(!reBest.has(group(j)))reBest.set(group(j),j);
    const moved=[];
    for(const [k,t] of reBest)if(t.level!==best.get(k).level)for(const p of P.all(t.keys))for(const b of brks)moved.push(makeJob(t,t.level,b,p));
    let extra=[];
    if(moved.length){
      const r=await run(moved,settings.screenRuns||2,9,'난이도 변경 배치 재비교'),seen=new Map();
      for(const j of P.best(moved,r,cmp(mode),v=>!!v?.cosmo)){const k=group(j),n=seen.get(k)||0;if(n<(settings.keep||2)){extra.push(j);seen.set(k,n+1);}}
    }
    // Shared final seed and run count for every finalist, including unchanged incumbents.
    const finals=[...new Map([...selected,...extra].map(j=>[j.key,j])).values()];
    const res=await run(finals,runs,10,'선택 배치 최종 확인');
    const winners=new Map();
    for(const j of P.best(finals,res,cmp(mode),r=>!!r?.cosmo))if(!winners.has(group(j)))winners.set(group(j),j);
    return {teams:[...winners.values()].map(j=>({boss:j.boss,keys:j.keys,order:j.order,leaderKey:j.leaderKey,level:j.level,brk:j.brk?.name||null,brkLv:j.brk?.level||null,st:res[j.key].cosmo,...(res[j.key].unsupported?.length?{unsupported:res[j.key].unsupported}:{})})),probe,conditions:jobs.length,moved:moved.length};
  }
  const api={cosmo,cmp,group};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PlacementSearch=api;
})(typeof window!=='undefined'?window:globalThis);
