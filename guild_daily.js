// Daily policy only. Battle scoring, execution, candidate preservation and packing
// remain in the shared modules; the legacy planner never enters this module.
(function(root){
  'use strict';
  const dep=(file,name)=>typeof module!=='undefined'&&module.exports?require('./'+file):root[name];
  const GS=dep('guild_search.js','GuildSearch'),V=dep('guild_view.js','GuildView');
  const CS=dep('cosmo_search.js','CosmoSearch'),C=dep('score_combinations.js','ScoreCombinations');
  const P=dep('party_placement.js','PartyPlacement'),PS=dep('placement_search.js','PlacementSearch');
  const E=dep('search_executor.js','SearchExecutor');
  const names=['능력치 계산','전체 조합 훑기','후보 정밀','스테이지·별의 도전·지원 비교','겹치지 않는 팀 묶기','결선·브레이크','자리·리더 비교'];
  const clone=x=>JSON.parse(JSON.stringify(x)),unique=xs=>[...new Map(xs.map(j=>[j.key,j])).values()];
  const compare=(a,b)=>b.score-a.score||b.mean-a.mean||a.id.localeCompare(b.id);
  const bundleId=b=>b.teams.map(t=>t.id).sort().join('/');
  const bundleCompare=(a,b)=>b.sum-a.sum||b.teams.reduce((s,t)=>s+t.mean,0)-a.teams.reduce((s,t)=>s+t.mean,0)||bundleId(a).localeCompare(bundleId(b));

  function splits(D,seals,open){
    if(!Number.isInteger(seals)||seals<D.seals.min||seals>D.seals.max)throw Error(`인장은 ${D.seals.min}~${D.seals.max}장 범위여야 함`);
    const out=[];
    for(let ex=open?Math.floor(seals/D.seals.costEx):0;ex>=0;ex--){
      const normal=(seals-ex*D.seals.costEx)/D.seals.costNormal;
      if(Number.isInteger(normal))out.push({ex,normal});
    }
    return D.split.exFirst?out:out.reverse();
  }
  const slots=s=>[...Array(s.ex).fill('ex'),...Array(s.normal).fill('normal')];
  function fitSplit(split,available){
    const s={...split};while(s.ex+s.normal>available){if(s.normal)s.normal--;else s.ex--;}
    return s;
  }
  // Actual client wave rows distinguish bosses and elites (unlike EX-only UI metadata).
  function normalMaximum(G){
    const normal=G.steps.filter(s=>!s.ex).sort((a,b)=>b.step-a.step)[0];
    if(!normal)throw Error('일반 스테이지 점수 자료가 없음');
    return normal.base+normal.waves.flat().reduce((sum,u)=>sum+(u.boss?normal.bossKill:u.elite?normal.eliteKill:normal.kill),0);
  }
  function choosePlacement(incumbent,candidate,margin){
    const value=incumbent.score===candidate.score?r=>r.mean:r=>r.score;
    return PS.incumbentWithMargin(incumbent,candidate,value,Math.abs(value(incumbent))*margin);
  }
  function standardError(xs){
    if(xs.length<2)return 0;
    const mean=xs.reduce((s,x)=>s+x,0)/xs.length;
    return Math.sqrt(xs.reduce((s,x)=>s+(x-mean)**2,0)/(xs.length*(xs.length-1)));
  }
  function closeFinalists(rows){
    if(!rows.length)return [];
    const first=rows[0];
    return rows.filter(r=>{
      const tied=r.score===first.score,metric=tied?'mean':'score',se=tied?'meanSE':'scoreSE';
      return first[metric]-r[metric]<=2*Math.hypot(first[se]||0,r[se]||0);
    });
  }
  function signature(cx,day,pl=plan(cx)){
    return JSON.stringify(['guild-daily-v2',cx.G.season.id,cx.G.dataVersion,day.date,cx.seals??cx.S.daily.seals.default,cx.split||null,
      cx.S,cx.tiers||[],cx.breaks||[],cx.roster,cx.results,cx.growthResults||null,
      {poolLimit:pl.poolLimit,policy:pl.D,placeScope:pl.placeScope,maxCombineChecks:cx.maxCombineChecks??2000000}]);
  }
  function trimPool(S,rows,limit,maxTeams){
    const floor=(rows[0]?.power||0)*(S.minPowerRatio||0);
    const base=new Set(rows.filter(r=>r.power>=floor).slice(0,S.poolSize).map(r=>r.key));
    // Preserve every GS.pool supplement, then the role capacity of all requested teams.
    const keep=new Set(rows.filter(r=>!base.has(r.key)).map(r=>r.key));
    const reserve=(pred,n)=>rows.filter(pred).slice(0,n).forEach(r=>keep.add(r.key));
    for(const [cls,n] of Object.entries(S.minRole||{}))reserve(r=>r.cls===cls,n);
    reserve(r=>GS.FRONT.includes(r.cls),(S.minFront||0)*maxTeams);
    reserve(r=>!GS.FRONT.includes(r.cls),(S.minDealer||0)*maxTeams);
    for(const r of rows){if(keep.size>=limit)break;keep.add(r.key);}
    return rows.filter(r=>keep.has(r.key));
  }
  function comboCount(S,rows){
    const choose=(n,k)=>{if(k>n)return 0;let v=1;for(let i=1;i<=k;i++)v=v*(n-i+1)/i;return v;};
    const front=rows.filter(r=>GS.FRONT.includes(r.cls)).length;
    let count=0;for(let f=S.minFront||0;f<=4-(S.minDealer||0);f++)count+=choose(front,f)*choose(rows.length-front,4-f);
    return count;
  }
  function plan(cx){
    const S={...cx.S,newSearch:false},D=clone(S.daily),day=V.gameDay({...cx.G,search:S},cx.nowMs??Date.now());
    const seals=cx.seals??D.seals.default,allowed=splits(D,seals,day.exOpen);
    const requested=cx.split?allowed.find(s=>s.ex===cx.split.ex&&s.normal===cx.split.normal):allowed[0];
    if(!requested)throw Error('오늘 사용할 수 없는 인장 나눔');
    const options=cx.split?[requested]:allowed;
    const maxTeams=Math.max(...options.map(s=>s.ex+s.normal));
    let rows=GS.pool(S,cx.results,cx.roster);
    const growthRows=cx.growthResults?GS.pool(S,cx.growthResults,cx.roster):[];
    const initialPool=Math.max(rows.length,growthRows.length),passes=cx.growthResults?2:1;
    let poolLimit=initialPool,placeScope='all';const reductions=[];
    const poolFloor=Math.min(initialPool,Math.max(20,maxTeams*4+4,
      trimPool(S,rows,0,maxTeams).length,trimPool(S,growthRows,0,maxTeams).length));
    // Wall seconds/game, including worker reuse: measured 744-game browser batch,
    // docs/cosmo_speed_rd_1110.md, browser table (1/2/4/8 workers). Approximate
    // startup prior only; prefer caller measurement or saved cosmo.speed.v2 data.
    const workers=cx.workers??CS.workerCount(D,cx.env),saved=CS.priorFrom(cx.cosmoSpeed,workers);
    const rate=workers>=8?125.34:workers>=4?103.42:workers>=2?70.19:39.95;
    const measured=Number.isFinite(cx.secondsPerGame)&&cx.secondsPerGame>0;
    const secondsPerGame=measured?cx.secondsPerGame:saved?Math.max(...saved):1/rate;
    const kinds=cx.split?new Set(slots(requested)):new Set(options.flatMap(slots));
    const nBrk=(cx.breaks||[]).length,supports=S.final.supports.filter(s=>s!=='none').length;
    function estimate(){
      const n=poolLimit,combos=Math.max(comboCount(S,trimPool(S,rows,n,maxTeams)),comboCount(S,trimPool(S,growthRows,n,maxTeams)));
      const teamCount=Math.min(Math.floor(n/4),maxTeams);
      const placeTeams=placeScope==='all'?teamCount:Math.min(Math.floor(n/4),requested.ex);
      const sweeps=kinds.size,conditions=(kinds.has('ex')?D.probe.levels.length:0)+(kinds.has('normal')?D.probe.steps.length:0);
      const retry=Math.max(...D.retry.keepMultipliers),keep=Math.min(combos,D.rerank.keep*retry);
      const probe=Math.min(combos,D.probe.teams*D.retry.keepMultipliers.reduce((a,b)=>a+b,0));
      // pickPass preserves boundary ties and per-unit alternatives. In the
      // saturated case every screened team advances; budget that upper bound.
      const games=[0,combos*sweeps*D.screen.runs,combos*sweeps*(D.rerank.runs-D.screen.runs),
        probe*conditions*(supports+1)*D.probe.runs,0,
        options.length*D.combine.top*teamCount*((D.final.closeRuns-D.probe.runs)+nBrk*D.final.closeRuns),
        placeTeams*(25*D.place.runs[0]+(D.place.keep+1)*(D.place.runs[2]-D.place.runs[0])+
          Math.max(D.probe.levels.length,D.probe.steps.length)*(supports+1)*D.place.recheckRuns+(nBrk+1)*D.final.runs)];
      const jobs=[0,combos*sweeps,combos*sweeps,probe*conditions*(supports+1),1,options.length*D.combine.top*teamCount,placeTeams];
      return {combos,jobs,games,total:games.reduce((a,b)=>a+b,0)*passes};
    }
    const over=()=>estimate().total*secondsPerGame>=D.timeCapMin*60;
    if(over()){placeScope='ex';reductions.push('자리·리더 대상: EX 팀만');}
    if(over()&&D.probe.teams>8){D.probe.teams=8;reductions.push('조건 비교: 상위 8팀');}
    if(over()&&D.rerank.keep>200){D.rerank.keep=200;reductions.push('정밀: 상위 200팀');}
    while(over()&&poolLimit>poolFloor)poolLimit--;
    if(poolLimit<initialPool)reductions.push(`풀: ${initialPool}명 → ${poolLimit}명`);
    const est=estimate(),stages=E.planStages(names.map((name,i)=>({id:i+1,name,jobs:est.jobs[i],runs:est.jobs[i]?est.games[i]/est.jobs[i]:0,upper:true,
      condition:i===6?'결선 완료 후, 변경 팀만 조건 재확인':i>=1&&i<=3?'EX 위주 합산이 일반 전체 상한 미만이면 모든 나눔 비교':undefined})));
    const availableTeams=Math.floor(Math.min(rows.length,poolLimit)/4),effectiveSplit=fitSplit(requested,availableTeams);
    return {version:1,preset:'daily',stages,total:est.total,estimatedSec:est.total*secondsPerGame,secondsPerGame,
      estimateFallback:!measured&&!saved,withinCap:!over(),reductions,D,day,seals,requested,options,poolLimit,poolFloor,maxTeams,placeScope,passes,
      effectiveSplit,availableTeams,warnings:effectiveSplit.ex+effectiveSplit.normal<requested.ex+requested.normal?['구원자가 부족해 만들 수 있는 팀 수로 줄였음']:[]};
  }
  async function search(cx){
    const pl=plan(cx);cx.onPlan?.(pl);
    if(!pl.withinCap)throw Object.assign(Error('최소 편성도 예상 시간 상한을 넘음'),{plan:pl,gwenCause:'timeCap'});
    const deadline=(cx.clock||Date.now)()+pl.D.timeCapMin*60000;
    const shared={pool:GS.workerPool(cx.makeWorker),stages:[],eta:null};
    try{
      const result=await searchOne(cx,pl,deadline,shared,0);
      if(cx.growthResults&&!result.partial){
        const growth=await searchOne({...cx,results:cx.growthResults,growthResults:null},pl,deadline,shared,1);
        result.growth=growth;
        if(growth.partial){result.partial=true;result.timeCapped ||= growth.timeCapped;result.flags=[...result.flags,'육성 포함 미평가'];}
      }
      return result;
    }finally{shared.pool.close();}
  }
  async function searchOne(cx,pl,deadline,shared,pass){
    const {G}=cx,D=pl.D,S={...cx.S,newSearch:false},cls=Object.fromEntries(cx.roster.map(r=>[r.key,r.cls]));
    const rows=trimPool(S,GS.pool(S,cx.results,cx.roster),pl.poolLimit,pl.maxTeams),list=GS.combos(S,rows),supports=S.final.supports.filter(s=>s!=='none');
    if(!list.length)throw Object.assign(Error('육성된 보유 구원자 4명 이상 필요'),{gwenCause:'few'});
    const workers=cx.workers??CS.workerCount(D,cx.env),pool=shared.pool,cache=new Map(),hist=[],sweeps=new Map(),warnings=[],executionStages=shared.stages;
    const now=cx.clock||Date.now,tiers=(cx.tiers||G.sets.items.map(()=>0)).slice(),exStep=G.steps.find(s=>s.ex).step;
    let phase=1,checkpoint=null,checkpointStage=0,selectedSplit=fitSplit(pl.requested,Math.floor(rows.length/4)),activeConditions=[],timeCapped=false,placeComplete=false,eta=shared.eta,splitsComplete=false;
    const growthForecast=()=>cx.growthResults?E.planStages([{id:'growth',name:'육성 포함 편성 찾기',jobs:1,runs:pl.total/pl.passes,upper:true}]):[];
    const cancel=()=>Object.assign(Error('취소'),{gwenCause:'cancel'});
    const check=()=>{if(cx.stale?.())throw cancel();if(now()>=deadline){timeCapped=true;throw cancel();}if(cx.partialRequested?.())throw cancel();};
    function announce(stage,name,jobs,runs,games=jobs*runs){
      const index=executionStages.length;
      const current=E.planStages([{id:'daily-'+index,name,jobs,runs,pass}])[0];current.games=games;current.policyStage=stage;
      executionStages.push(current);
      const pendingSweep=!splitsComplete&&pl.options.some(s=>s.normal)&&!sweeps.get('normal')?.multiplier;
      const future=pl.stages.flatMap(s=>{
        if(s.id<stage&&!(pendingSweep&&s.id>=2&&s.id<=4))return [];
        const spent=executionStages.filter(x=>x.pass===pass&&x.policyStage===s.id).reduce((sum,x)=>sum+x.games,0),remaining=Math.max(0,s.games-spent);
        return remaining?[{...s,id:'remaining-'+s.id,jobs:1,runs:remaining,games:remaining,done:0}]:[];
      });
      const stages=[...executionStages,...future,...growthForecast()];
      const cost=eta?.summary()?.at(-1)||pl.secondsPerGame;
      eta=E.etaNew({stages,weights:stages.map(()=>1),prior:stages.map(()=>cost)});
      shared.eta=eta;
      eta.begin(index,games,now()/1000);
      // P1 indices follow execution, including conditional sweeps and retries;
      // semantic policyStage remains 1..7. Future entries are upper estimates.
      cx.onPlan?.({...pl,stages,total:stages.reduce((sum,s)=>sum+s.games,0),eta});
      cx.onPhase?.(name,jobs,{stage:index,policyStage:stage,jobs,teams:jobs,runs,games});
      return current;
    }
    function make(keys,kind,condition,sup='none',brk=null,placement){
      const base=placement||P.baseline(keys,cx.results),p={order:base.order,leaderKey:base.leaderKey||base.order[0]};
      const party=GS.party(keys,cx.results,cls,p),step=kind==='ex'?exStep:condition,level=kind==='ex'?condition:0;
      const effectiveSupport=GS.finalSupports(S,keys,cls).includes(sup)?sup:'none';
      const sets=kind==='ex'?tiers:tiers.map(()=>0);
      const key=step+':'+GS.jobKey(keys,level,effectiveSupport,sets,brk,party,G);
      return {key,id:key+'|assign:'+sup,keys,kind,step,level,sup,effectiveSupport,order:party.order,leaderKey:party.leaderKey,
        party:party.spec,options:{guild:{seasonId:G.season.id,dataVersion:G.dataVersion,step,level,sets,support:effectiveSupport},break_skill:brk}};
    }
    function ranked(jobs,n){
      return jobs.filter(j=>(cache.get(j.key)?.n||0)>=n&&!GS.coopHit(S,cache.get(j.key))).map(j=>{
        const full=cache.get(j.key);
        // A cached 40-game finalist also contains the exact first 20/10 games.
        // Compare every contender at the requested precision, without rerunning.
        const raw=n<full.n?JSON.parse(full.raw).slice(0,n):null;
        const r=raw?{...full,n,progs:raw.map(x=>x[3]),prog:raw.reduce((s,x)=>s+x[3],0)/n,clear:raw.filter(x=>x[0]==='clear').length/n,
          guild:full.guild?{base_scores:raw.map(x=>x[4])}:undefined}:full;
        const scoreG=j.kind==='ex'?G:{...G,defaultStep:j.step};
        const st=GS.rankStats(V,scoreG,j.level,j.options.guild.sets,r.prog,r.progs,r.clear,r.guild);
        const pct=V.extraPct(scoreG,j.level,j.options.guild.sets);
        const scores=r.guild?.base_scores?.map(x=>Math.floor((x*(100+pct)+50)/100))||r.progs.map(x=>V.scoreFromProg(scoreG,pct,x));
        const sorted=scores.slice().sort((a,b)=>b-a),q=Math.ceil(scores.length*.2-1e-9)/scores.length,cut=sorted[Math.ceil(scores.length*.2-1e-9)-1];
        return {...j,score:st.top,mean:st.mean,cap:st.cap,clear:r.clear,prog:r.prog,n:r.n,brk:j.options.break_skill?.name||null,brkLv:j.options.break_skill?.level||null,
          meanSE:standardError(scores),scoreSE:standardError(scores.map(x=>Math.max(0,x-cut)/q)),
          ...(r.unsupported?.length?{unsupported:r.unsupported}:{})};
      }).sort(compare);
    }
    async function run(jobs,runs,stage,label=names[stage-1]){
      check();phase=stage;
      const pending=unique(jobs).filter(j=>(cache.get(j.key)?.n||0)<runs),groups=new Map();
      for(const j of pending){const prior=cache.get(j.key),off=prior?.n||0,n=runs-off;
        if(prior&&!prior.raw)throw Error('이어 돌릴 길드 원시값이 없음');
        const job={...j,options:{...j.options,...(prior?{run_offset:off,merge_raw:prior.raw}:{raw_runs:true})}};
        if(!groups.has(n))groups.set(n,[]);groups.get(n).push(job);
      }
      if(!pending.length)return;
      for(const [n,batch] of groups){
        check();const record={stage,name:label,jobs:batch.length,done:0,runs:n,seed:D.seed,complete:false};hist.push(record);
        const progressStage=announce(stage,label,batch.length,n);
        const old=new Map(batch.map(j=>[j.key,cache.get(j.key)]));
        const h=GS.runPhase({makeWorker:cx.makeWorker,pool,jobs:batch,workers,runs:n,seed:D.seed,stage:cx.stage,base:cx.base,watch:cx.watch,
          retainRaw:true,chunk:E.chunkSize(batch.length,workers),onProgress:d=>{record.done=d;progressStage.done=d;eta.update(d*n,now()/1000);cx.onProgress?.(d,batch.length,eta.estimate(now()/1000));}});
        cx.onHandle?.(h);
        const timer=setTimeout(()=>{timeCapped=true;h.cancel();},Math.max(1,deadline-now()));
        function save(res){for(const j of batch){const r=res[j.key];if(!r)continue;
          if(r.n!==runs||r.progs?.length!==runs||typeof r.raw!=='string'||!Number.isFinite(r.prog))throw Error('길드 판별 결과가 누락됨');
          const prev=old.get(j.key);
          // web.merge_summary carries scores/raw exactly; via describes only the
          // appended games, so preserve its weighted rate for coop filtering.
          if(prev){const via={};for(const k of new Set([...Object.keys(prev.via||{}),...Object.keys(r.via||{})]))via[k]=((prev.via[k]||0)*prev.n+(r.via[k]||0)*n)/runs;r.via=via;}
          cache.set(j.key,r);
        }}
        try{save(await h.promise);record.complete=true;}catch(e){save(h.snapshot());throw e;}finally{clearTimeout(timer);}
        check();
      }
    }
    const conditionJobs=(team,allowed=supports,brk=null)=>
      (team.kind==='ex'?D.probe.levels:D.probe.steps).filter(v=>team.kind==='ex'?v<=G.challenge.levels.length:G.steps.some(s=>s.step===v&&!s.ex))
        .flatMap(condition=>allowed.map(sup=>make(team.keys,team.kind,condition,sup,brk,team)));
    function table(jobs){
      const best=new Map();for(const r of ranked(jobs,D.probe.runs)){const id=P.id(r.keys)+'|'+r.sup;if(!best.has(id))best.set(id,r);}return [...best.values()].sort(compare);
    }
    async function sweep(kind,multiplier=1){
      let data=sweeps.get(kind);
      if(!data){
        const screen=list.map(keys=>make(keys,kind,kind==='ex'?D.screen.exLevel:D.screen.normalStep));
        data={screen,conditions:[],multiplier:0};sweeps.set(kind,data);
        await run(screen,D.screen.runs,2,(kind==='ex'?'EX':'일반')+' 전체 조합 훑기');
      }
      if(data.multiplier>=multiplier)return;
      const summaries=Object.fromEntries(ranked(data.screen,D.screen.runs).map(r=>[r.key,{cosmo:{top:r.score,mean:r.mean,clear:r.cap}}]));
      const eligible=data.screen.filter(j=>summaries[j.key]);
      const pass=CS.pickPass(eligible,summaries,'top',D.rerank.keep*multiplier),ids=new Set(pass.map(t=>P.id(t.keys)));
      const refine=eligible.filter(j=>ids.has(P.id(j.keys)));
      await run(refine,D.rerank.runs,3,(kind==='ex'?'EX':'일반')+' 후보 정밀');
      const teams=ranked(refine,D.rerank.runs).slice(0,D.probe.teams*multiplier);
      data.conditions=teams.flatMap(t=>conditionJobs(t));activeConditions=[...sweeps.values()].flatMap(x=>x.conditions);
      await run(data.conditions,D.probe.runs,4,(kind==='ex'?'EX':'일반')+' 스테이지·별의 도전·지원 비교');
      data.multiplier=multiplier;
    }
    async function combine(split,recovery=false){
      let progressStage;if(!recovery){check();phase=5;progressStage=announce(5,names[4],1,0);}
      const lists=slots(split).map(kind=>table((sweeps.get(kind)?.conditions||[])));
      const budget={remaining:cx.maxCombineChecks??2000000};
      const it=C.steps(lists,D.combine.top,budget,{id:t=>t.id,resources:t=>({units:t.keys,support:[t.sup]}),secondary:t=>t.mean,setId:ts=>ts.map(t=>t.id).sort().join('/')});
      let next,last=now();do{next=it.next();if(!recovery)check();if(now()-last>16){await new Promise(r=>setTimeout(r,0));last=now();}}while(!next.done);
      if(budget.exhausted&&!warnings.includes('묶음 조합 계산 상한에 도달함'))warnings.push('묶음 조합 계산 상한에 도달함');
      if(progressStage)progressStage.done=1;
      return next.value.sort(bundleCompare);
    }
    async function finalBundles(bundles){
      const jobs=[...new Map(bundles.flatMap(b=>b.teams).map(t=>[t.id,t])).values()];await run(jobs,D.final.runs,6);
      const breaks=jobs.flatMap(t=>[null,...(cx.breaks||[])].map(brk=>make(t.keys,t.kind,t.kind==='ex'?t.level:t.step,t.sup,brk,t)));
      await run(breaks,D.final.runs,6,'결선·브레이크');
      const teamId=t=>P.id(t.keys)+'|'+t.kind+'|'+t.step+'|'+t.level+'|'+t.sup;
      function pack(rows,source){
        const best=new Map();for(const t of rows)if(!best.has(teamId(t)))best.set(teamId(t),t);
        return source.flatMap(b=>{const teams=b.teams.map(t=>best.get(teamId(t)));
          return teams.every(Boolean)?[{teams,sum:teams.reduce((s,t)=>s+t.score,0),score:teams.reduce((s,t)=>s+t.score,0),mean:teams.reduce((s,t)=>s+t.mean,0),
            scoreSE:Math.hypot(...teams.map(t=>t.scoreSE)),meanSE:Math.hypot(...teams.map(t=>t.meanSE))}]:[];
        }).sort(bundleCompare);
      }
      const ranked40=ranked(breaks,D.final.runs),finals=pack(ranked40,bundles),near=closeFinalists(finals);
      if(near.length<2||D.final.closeRuns<=D.final.runs)return {rows:finals,complete:finals.length===bundles.length};
      const ids=new Set(near.flatMap(b=>b.teams.map(teamId))),extra=[];
      for(const id of ids)extra.push(...closeFinalists(ranked40.filter(t=>teamId(t)===id)));
      await run(extra,D.final.closeRuns,6,'근접 결선 80판 확인');
      const confirmed=pack(ranked(extra,D.final.closeRuns),near);
      // Dropping distant bundles is intentional, not a coop exclusion requiring
      // candidate recovery. Only invalid teams trigger the outer repack loop.
      return {rows:confirmed,complete:finals.length===bundles.length&&confirmed.length===near.length};
    }
    async function solve(requested){
      let split=fitSplit(requested,Math.floor(rows.length/4));selectedSplit=split;
      const retry=CS.retryPlan({rerank:{keep:D.probe.teams,runs:D.rerank.runs},retry:{...D.retry,maxCandidatesPerBoss:list.length,maxRerankGames:3*list.length*D.rerank.runs,maxTripleChecks:cx.maxCombineChecks??2000000}},list.length);
      async function validFinal(){
        // Excluded 40-game candidates disappear from table() too. Repack the
        // remaining conditions until a valid finalist or candidate exhaustion.
        let best=null;
        for(;;){
          const bundles=await combine(split);if(!bundles.length)return best;
          if(checkpointStage<6){checkpoint=bundles[0];checkpointStage=5;}
          const final=await finalBundles(bundles),finals=final.rows;
          // A previously retained 40-game winner can fail coop at 80 games.
          const invalid=b=>b?.teams.some(t=>GS.coopHit(S,cache.get(t.key)));
          if(invalid(best))best=null;
          if(invalid(checkpoint))checkpoint=null;
          if(finals.length){
            if(!best||bundleCompare(finals[0],best)<0)best=finals[0];
            if(checkpointStage<6||!checkpoint||bundleCompare(best,checkpoint)<0){checkpoint=best;checkpointStage=6;}
          }
          if(final.complete)return best;
          if(checkpointStage<6)checkpoint=null;
        }
      }
      for(let i=0;i<retry.limits.length;i++){
        const mult=D.retry.keepMultipliers[i];for(const kind of new Set(slots(split)))await sweep(kind,mult);
        const best=await validFinal();if(best)return best;
      }
      while(split.ex+split.normal>1){split=fitSplit(split,split.ex+split.normal-1);selectedSplit=split;const best=await validFinal();if(best)return best;}
      return null;
    }
    async function placement(bundle){
      const teams=bundle.teams.slice();
      for(let i=0;i<teams.length;i++){
        const original=teams[i];if(pl.placeScope==='ex'&&original.kind!=='ex')continue;
        const brk=original.options.break_skill,condition=original.kind==='ex'?original.level:original.step;
        const layouts=unique([...P.all(original.keys).map(p=>make(original.keys,original.kind,condition,original.sup,brk,p)),original]);
        await run(layouts,D.place.runs[0],7);
        async function advance(runs){
          for(;;){
            const eligible=ranked(layouts,D.place.runs[0]),inc=eligible.find(t=>t.key===original.key);
            const finalists=[...eligible.filter(t=>t.key!==original.key).slice(0,D.place.keep),...(inc?[inc]:[])];
            if(!finalists.length)return [];
            await run(finalists,runs,7);
            const rr=ranked(finalists,runs);
            if(rr.length===finalists.length)return rr;
          }
        }
        let rr=await advance(D.place.runs[1]),inc=rr.find(t=>t.key===original.key)||rr[0];
        if(!inc){teams[i]=null;continue;}
        let pick=choosePlacement(inc,rr[0],D.place.margin);
        // Close results get the last paired round; a clear improvement can stop at 100.
        const challenger=rr.find(t=>t.key!==inc.key);
        if(pick===inc&&challenger&&choosePlacement(challenger,inc,D.place.margin)===challenger){rr=await advance(D.place.runs[2]);inc=rr.find(t=>t.key===original.key)||rr[0];if(!inc){teams[i]=null;continue;}pick=choosePlacement(inc,rr[0],D.place.margin);}
        if(pick.key===original.key){teams[i]={...inc,placementChanged:false};continue;}
        const taken=new Set(teams.filter((t,j)=>t&&j!==i).map(t=>t.sup)),allowed=supports.filter(s=>!taken.has(s));
        const recheck=conditionJobs(pick,allowed,brk);await run(recheck,D.place.recheckRuns,7,'바뀐 자리의 스테이지·지원 재확인');
        const next=ranked(recheck,D.place.recheckRuns)[0];let chosen=pick;
        if(next&&(next.level!==pick.level||next.step!==pick.step||next.sup!==pick.sup)){
          await run([pick,next],D.final.runs,7,'바뀐 조건 40판 확인');
          const confirmed=ranked([pick,next],D.final.runs)[0];
          if(!confirmed){teams[i]=null;continue;}
          const checks=[null,...(cx.breaks||[])].map(b=>make(confirmed.keys,confirmed.kind,confirmed.kind==='ex'?confirmed.level:confirmed.step,confirmed.sup,b,confirmed));
          await run(checks,D.final.runs,7,'바뀐 조건 브레이크 재비교');chosen=ranked(checks,D.final.runs)[0];
        }
        teams[i]=chosen?{...chosen,placementChanged:true}:null;
      }
      const valid=teams.filter(Boolean);
      placeComplete=pl.placeScope==='all'||valid.every(t=>t.kind==='ex');
      return {teams:valid,sum:valid.reduce((s,t)=>s+t.score,0)};
    }
    let reason='';
    function output(bundle,partial){
      const cost=eta?.summary()?.at(-1)||pl.secondsPerGame;
      const stages=[...executionStages,...(partial?[]:growthForecast())];
      const finalEta=E.etaNew({stages,weights:stages.map(()=>1),prior:stages.map(()=>cost)});
      finalEta.begin(executionStages.length-1,0,now()/1000);
      cx.onPlan?.({...pl,stages,total:stages.reduce((sum,s)=>sum+s.games,0),eta:finalEta,complete:!partial&&!cx.growthResults,stopped:partial});
      const supportComplete=checkpointStage>=5;
      const selectedStage=partial?checkpointStage:phase;
      const evaluation={partial,stage:selectedStage,stageSupportComplete:supportComplete,breakComplete:checkpointStage>=6,placementComplete:placeComplete};
      const flags=[...(!supportComplete?['스테이지·지원 미평가']:[]),...(!placeComplete?['자리·리더 미평가']:[])];
      const teams=(bundle?.teams||[]).map(t=>({...t,evaluation:{...evaluation}})),used=teams.reduce((s,t)=>s+(t.kind==='ex'?D.seals.costEx:D.seals.costNormal),0);
      if(teams.length<pl.requested.ex+pl.requested.normal)warnings.push(`${pl.requested.ex+pl.requested.normal}팀 중 ${teams.length}팀만 만들었음 · 인장 ${pl.seals-used}장 남음`);
      return {preset:'daily',rows:teams,teams,sum:bundle?.sum||0,mean:teams.reduce((s,t)=>s+t.mean,0),reason,flags,partial,timeCapped,
        seals:{requested:pl.seals,used,remaining:pl.seals-used},split:{ex:teams.filter(t=>t.kind==='ex').length,normal:teams.filter(t=>t.kind==='normal').length},
        warnings,plan:pl,signature:signature(cx,pl.day,pl),pool:rows.length,combos:list.length,runs:D.final.runs,
        coverage:{version:1,selectedStage:teams.length?selectedStage:0,stages:hist},evaluation};
    }
    try{
      check();let best=await solve(pl.requested);
      const skipNormal=D.split.exFirst&&best&&best.sum>=pl.seals/D.seals.costNormal*normalMaximum(G);
      if(!cx.split){
        for(const option of pl.options.slice(1)){
          if(skipNormal)break;
          const prior=best;const alternative=await solve(option);
          if(alternative&&(!best||bundleCompare(alternative,best)<0))best=alternative;
          // An unsuccessful alternate must not replace the safe final checkpoint.
          checkpoint=best||prior;
        }
      }
      splitsComplete=true;
      if(cx.split)reason='지정한 인장 나눔을 계산했음';
      else if(!pl.day.exOpen)reason='오늘은 EX가 닫혀 일반 팀을 골랐음';
      else if(!pl.requested.ex)reason='사용할 인장 수에 맞춰 일반 팀을 골랐음';
      else if(skipNormal)reason='EX 위주 합산이 인장 수 × 일반 최고 단계 만점 이상이라 일반 나눔 비교를 생략했음';
      else reason='가능한 인장 나눔을 모두 비교해 합산이 가장 큰 묶음을 골랐음';
      checkpoint=best;
      if(best)best=await placement(best);
      check();return output(best,false);
    }catch(e){
      if(cx.stale?.()||e.gwenCause!=='cancel'||(!cx.partialRequested?.()&&!timeCapped))throw e;
      if(!checkpoint&&phase>=4&&activeConditions.length){
        let split=selectedSplit,bundles=await combine(split,true);
        while(!bundles.length&&split.ex+split.normal>1){split=fitSplit(split,split.ex+split.normal-1);bundles=await combine(split,true);}
        checkpoint=bundles[0]||null;checkpointStage=4;
      }
      return output(phase>=4?checkpoint:null,true);
    }
  }
  const api={search,plan,splits,fitSplit,normalMaximum,choosePlacement,closeFinalists,standardError,signature};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GuildDaily=api;
})(typeof window!=='undefined'?window:globalThis);
