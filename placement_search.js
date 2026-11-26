// Joint layout/leader/difficulty/break evaluation. No engine or UI dependencies.
(function(root){
  'use strict';
  const P=typeof module!=='undefined'&&module.exports?require('./party_placement.js'):root.PartyPlacement;
  const group=j=>j.boss+'|'+P.id(j.keys);
  const cmp=mode=>(a,b)=>{const x=a.cosmo,y=b.cosmo,k=mode==='top'?'top':'mean',o=k==='top'?'mean':'top';return y[k]-x[k]||y[o]-x[o]||(y.clear||0)-(x.clear||0);};
  // Adapters own candidate dimensions, ranking (including ties), seeds and run counts.
  // The caller chooses the batch boundary: one guild team or all cosmo teams.
  function perGroup(ranked,group,keep=1,grouped=true){
    const groups=new Map();
    if(!grouped)return ranked.filter(j=>{const k=group(j),n=groups.get(k)||0;groups.set(k,n+1);return n<keep;});
    for(const j of ranked){const k=group(j);if(!groups.has(k))groups.set(k,[]);if(groups.get(k).length<keep)groups.get(k).push(j);}
    return [...groups.values()].flat();
  }
  async function joint({teams,probeJobs,rank,group,jointJobs,revisitJobs,movedJobs,runStage,keep=2,beforeScreen=()=>{},validateProbe=()=>{}}){
    const probe=await runStage('probe',probeJobs);
    validateProbe(probeJobs,probe);
    const jobs=jointJobs(teams,probeJobs,probe);
    beforeScreen();
    const first=await runStage('screen',jobs),selected=perGroup(rank(jobs,first),group,keep);
    const refined=await runStage('refine',selected),best=perGroup(rank(selected,refined),group);
    const revisit=revisitJobs(best),re=await runStage('revisit',revisit);
    const next=perGroup(rank(revisit,re),group),byGroup=new Map(best.map(j=>[group(j),j]));
    const changed=next.filter(j=>j.level!==byGroup.get(group(j)).level),moved=movedJobs(changed);
    const extra=moved.length?perGroup(rank(moved,await runStage('moved',moved)),group,keep,false):[];
    return {probe,selected,extra,conditions:jobs.length,moved:moved.length,changed:changed.length};
  }
  // Prepared for P3 only. Callers must compare paired, equally precise results.
  function incumbentWithMargin(incumbent,candidate,value,margin){
    return value(candidate)-value(incumbent)>margin?candidate:incumbent;
  }
  async function cosmo({teams,makeJob,run,mode,level,maxLevel,auto,breaks,runs,probeRuns,boundaries={},stale=()=>false,settings={}}){
    const allLevels=auto?Array.from({length:maxLevel+1},(_,i)=>i):[level],brks=[null,...breaks];
    const probeJobs=teams.flatMap(t=>allLevels.map(l=>makeJob(t,l,null,t)));
    const stages={probe:[probeRuns,5,'난이도 예비 비교'],screen:[settings.screenRuns||2,6,'배치·리더·난이도·브레이크 결합 비교'],refine:[runs,7,'결합 후보 정밀 비교'],revisit:[probeRuns,8,'개선 배치로 전체 난이도 재확인'],moved:[settings.screenRuns||2,9,'난이도 변경 배치 재비교']};
    const rank=(jobs,res)=>P.best(jobs,res,cmp(mode),r=>!!r?.cosmo);
    const {probe,selected,extra,conditions,moved}=await joint({teams,probeJobs,rank,group,keep:settings.keep||2,
      runStage:(stage,jobs)=>run(jobs,...stages[stage]),validateProbe:rank,
      beforeScreen:()=>{if(stale())throw Error('취소');},
      jointJobs:(teams,probeJobs,probe)=>{
        const jobs=[];
        for(const t of teams){
          const scores=probeJobs.filter(j=>group(j)===group(t)).map(j=>({level:j.level,score:probe[j.key].cosmo[mode]}));
          const levels=auto?P.levels(scores,maxLevel,boundaries[t.boss]||[],2):[level];
          const layouts=settings.enabled===false?[t]:P.all(t.keys);
          // Preserve the rerank winner's within-row order too.
          if(!layouts.some(p=>P.executionKey(t.keys,p)===P.executionKey(t.keys,t)))layouts.push(t);
          for(const p of layouts)for(const l of levels)for(const b of brks)jobs.push(makeJob(t,l,b,p));
        }
        return jobs;
      },
      revisitJobs:best=>best.flatMap(t=>allLevels.map(l=>makeJob(t,l,t.brk,t))),
      movedJobs:changed=>changed.flatMap(t=>(settings.enabled===false?[t]:P.all(t.keys)).flatMap(p=>brks.map(b=>makeJob(t,t.level,b,p))))
    });
    // Shared final seed and run count for every finalist, including unchanged incumbents.
    // Test every break on the selected arrangements at the same precision/seed.
    const finals=[...new Map([...selected,...extra].flatMap(j=>brks.map(b=>makeJob(j,j.level,b,j))).map(j=>[j.key,j])).values()];
    const res=await run(finals,runs,10,'선택 배치 최종 확인');
    const winners=new Map();
    for(const j of P.best(finals,res,cmp(mode),r=>!!r?.cosmo))if(!winners.has(group(j)))winners.set(group(j),j);
    return {teams:[...winners.values()].map(j=>{
      const siblings=finals.filter(x=>group(x)===group(j)&&x.level===j.level&&P.executionKey(x.keys,x)===P.executionKey(j.keys,j));
      const brkTie=brks.length>1&&siblings.length===brks.length&&siblings.every(x=>res[x.key].cosmo.top===res[j.key].cosmo.top&&res[x.key].cosmo.mean===res[j.key].cosmo.mean);
      return {boss:j.boss,keys:j.keys,order:j.order,leaderKey:j.leaderKey,level:j.level,brk:brkTie?null:j.brk?.name||null,brkLv:brkTie?null:j.brk?.level||null,...(brkTie?{brkTie:true}:{}),st:res[j.key].cosmo,...(res[j.key].unsupported?.length?{unsupported:res[j.key].unsupported}:{})};
    }),probe,conditions,moved};
  }
  const api={cosmo,cmp,group,joint,perGroup,incumbentWithMargin};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PlacementSearch=api;
})(typeof window!=='undefined'?window:globalThis);
