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
    if(!Number.isInteger(seals)||seals<D.seals.min||seals>D.seals.max)throw Error('인장은 1~4장 범위여야 함');
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
  function signature(cx,day){
    return JSON.stringify(['guild-daily-v1',cx.G.season.id,cx.G.dataVersion,day.date,cx.seals??cx.S.daily.seals.default,cx.split||null,
      cx.S,cx.tiers||[],cx.breaks||[],cx.roster,cx.results,cx.growthResults||null]);
  }
  function plan(cx){
    const S={...cx.S,newSearch:false},D=clone(S.daily),day=V.gameDay({...cx.G,search:S},cx.nowMs??Date.now());
    const seals=cx.seals??D.seals.default,allowed=splits(D,seals,day.exOpen);
    const requested=cx.split?allowed.find(s=>s.ex===cx.split.ex&&s.normal===cx.split.normal):allowed[0];
    if(!requested)throw Error('오늘 사용할 수 없는 인장 나눔');
    const options=cx.split?[requested]:allowed;
    let rows=GS.pool(S,cx.results,cx.roster);
    const growthRows=cx.growthResults?GS.pool(S,cx.growthResults,cx.roster):[];
    const initialPool=Math.max(rows.length,growthRows.length),passes=cx.growthResults?2:1;
    let poolLimit=initialPool,placeScope='all';const reductions=[];
    // Seconds per game is wall time at the chosen worker count, from the caller's
    // device measurement. An unmeasured device uses a conservative 1s estimate.
    const secondsPerGame=Number.isFinite(cx.secondsPerGame)&&cx.secondsPerGame>0?cx.secondsPerGame:1;
    const kinds=cx.split?new Set(slots(requested)):new Set(options.flatMap(slots));
    const nBrk=(cx.breaks||[]).length,supports=S.final.supports.filter(s=>s!=='none').length;
    function estimate(){
      const n=poolLimit,combos=n<4?0:n*(n-1)*(n-2)*(n-3)/24;
      const maxTeams=Math.min(Math.floor(n/4),Math.max(...options.map(s=>s.ex+s.normal)));
      const placeTeams=placeScope==='all'?maxTeams:Math.min(Math.floor(n/4),requested.ex);
      const sweeps=kinds.size,conditions=(kinds.has('ex')?D.probe.levels.length:0)+(kinds.has('normal')?D.probe.steps.length:0);
      const retry=Math.max(...D.retry.keepMultipliers),keep=Math.min(combos,D.rerank.keep*retry);
      const probe=Math.min(combos,D.probe.teams*D.retry.keepMultipliers.reduce((a,b)=>a+b,0));
      // pickPass preserves boundary ties and per-unit alternatives. In the
      // saturated case every screened team advances; budget that upper bound.
      const games=[0,combos*sweeps*D.screen.runs,combos*sweeps*(D.rerank.runs-D.screen.runs),
        probe*conditions*(supports+1)*D.probe.runs,0,
        options.length*D.combine.top*maxTeams*((D.final.runs-D.probe.runs)+nBrk*D.final.runs),
        placeTeams*(25*D.place.runs[0]+(D.place.keep+1)*(D.place.runs[2]-D.place.runs[0])+
          Math.max(D.probe.levels.length,D.probe.steps.length)*(supports+1)*D.place.recheckRuns+(nBrk+1)*D.final.runs)];
      const jobs=[0,combos*sweeps,combos*sweeps,probe*conditions*(supports+1),1,options.length*D.combine.top*maxTeams,placeTeams];
      return {combos,jobs,games,total:games.reduce((a,b)=>a+b,0)*passes};
    }
    const over=()=>estimate().total*secondsPerGame>=D.timeCapMin*60;
    if(over()){placeScope='ex';reductions.push('자리·리더 대상: EX 팀만');}
    if(over()&&D.probe.teams>8){D.probe.teams=8;reductions.push('조건 비교: 상위 8팀');}
    if(over()&&D.rerank.keep>200){D.rerank.keep=200;reductions.push('정밀: 상위 200팀');}
    while(over()&&poolLimit>4)poolLimit--;
    if(poolLimit<initialPool)reductions.push(`풀: ${initialPool}명 → ${poolLimit}명`);
    const est=estimate(),stages=E.planStages(names.map((name,i)=>({id:i+1,name,jobs:est.jobs[i],runs:est.jobs[i]?est.games[i]/est.jobs[i]:0,upper:true,
      condition:i===6?'결선 완료 후, 변경 팀만 조건 재확인':i>=1&&i<=3?'필요한 EX·일반 훑기, 약한 EX이면 일반 추가':undefined})));
    const availableTeams=Math.floor(Math.min(rows.length,poolLimit)/4),effectiveSplit=fitSplit(requested,availableTeams);
    return {version:1,preset:'daily',stages,total:est.total,estimatedSec:est.total*secondsPerGame,secondsPerGame,
      estimateFallback:secondsPerGame===1&&!(cx.secondsPerGame>0),withinCap:!over(),reductions,D,day,seals,requested,options,poolLimit,placeScope,passes,
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
    const rows=GS.pool(S,cx.results,cx.roster).slice(0,pl.poolLimit),list=GS.combos(S,rows),supports=S.final.supports.filter(s=>s!=='none');
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
      const base=placement||GS.party(keys,cx.results,cls),p={order:base.order,leaderKey:base.leaderKey||base.order[0]};
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
        return {...j,score:st.top,mean:st.mean,cap:st.cap,clear:r.clear,prog:r.prog,n:r.n,brk:j.options.break_skill?.name||null,brkLv:j.options.break_skill?.level||null,
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
      const best=new Map();for(const t of ranked(breaks,D.final.runs)){const id=P.id(t.keys)+'|'+t.kind+'|'+t.step+'|'+t.level+'|'+t.sup;if(!best.has(id))best.set(id,t);}
      return bundles.map(b=>{const teams=b.teams.map(t=>best.get(P.id(t.keys)+'|'+t.kind+'|'+t.step+'|'+t.level+'|'+t.sup));return {teams,sum:teams.reduce((s,t)=>s+t.score,0)};}).sort(bundleCompare);
    }
    async function solve(requested){
      let split=fitSplit(requested,Math.floor(rows.length/4));selectedSplit=split;
      const retry=CS.retryPlan({rerank:{keep:D.probe.teams,runs:D.rerank.runs},retry:{...D.retry,maxCandidatesPerBoss:list.length,maxRerankGames:3*list.length*D.rerank.runs,maxTripleChecks:cx.maxCombineChecks??2000000}},list.length);
      let bundles=[];
      for(let i=0;i<retry.limits.length;i++){
        const mult=D.retry.keepMultipliers[i];for(const kind of new Set(slots(split)))await sweep(kind,mult);
        bundles=await combine(split);if(bundles.length)break;
      }
      while(!bundles.length&&split.ex+split.normal>1){split=fitSplit(split,split.ex+split.normal-1);selectedSplit=split;bundles=await combine(split);}
      if(!bundles.length)return null;
      if(checkpointStage<6){checkpoint=bundles[0];checkpointStage=5;}
      const finals=await finalBundles(bundles);
      if(checkpointStage<6||bundleCompare(finals[0],checkpoint)<0){checkpoint=finals[0];checkpointStage=6;}
      return finals[0];
    }
    async function placement(bundle){
      const teams=bundle.teams.slice();
      for(let i=0;i<teams.length;i++){
        const original=teams[i];if(pl.placeScope==='ex'&&original.kind!=='ex')continue;
        const brk=original.options.break_skill,condition=original.kind==='ex'?original.level:original.step;
        const layouts=unique([...P.all(original.keys).map(p=>make(original.keys,original.kind,condition,original.sup,brk,p)),original]);
        await run(layouts,D.place.runs[0],7);
        const finalists=[...ranked(layouts,D.place.runs[0]).filter(t=>t.key!==original.key).slice(0,D.place.keep),original];
        await run(finalists,D.place.runs[1],7);
        let rr=ranked(finalists,D.place.runs[1]),inc=rr.find(t=>t.key===original.key),pick=choosePlacement(inc,rr[0],D.place.margin);
        // Close results get the last paired round; a clear improvement can stop at 100.
        const challenger=rr.find(t=>t.key!==inc.key);
        if(pick===inc&&challenger&&choosePlacement(challenger,inc,D.place.margin)===challenger){await run(finalists,D.place.runs[2],7);rr=ranked(finalists,D.place.runs[2]);inc=rr.find(t=>t.key===original.key);pick=choosePlacement(inc,rr[0],D.place.margin);}
        if(pick.key===original.key){teams[i]={...inc,placementChanged:false};continue;}
        const taken=new Set(teams.filter((_,j)=>j!==i).map(t=>t.sup)),allowed=supports.filter(s=>!taken.has(s));
        const recheck=conditionJobs(pick,allowed,brk);await run(recheck,D.place.recheckRuns,7,'바뀐 자리의 스테이지·지원 재확인');
        const next=ranked(recheck,D.place.recheckRuns)[0];let chosen=pick;
        if(next&&(next.level!==pick.level||next.step!==pick.step||next.sup!==pick.sup)){
          await run([pick,next],D.final.runs,7,'바뀐 조건 40판 확인');
          const confirmed=ranked([pick,next],D.final.runs)[0];
          const checks=[null,...(cx.breaks||[])].map(b=>make(confirmed.keys,confirmed.kind,confirmed.kind==='ex'?confirmed.level:confirmed.step,confirmed.sup,b,confirmed));
          await run(checks,D.final.runs,7,'바뀐 조건 브레이크 재비교');chosen=ranked(checks,D.final.runs)[0];
        }
        teams[i]={...chosen,placementChanged:true};
      }
      placeComplete=pl.placeScope==='all'||teams.every(t=>t.kind==='ex');
      return {teams,sum:teams.reduce((s,t)=>s+t.score,0)};
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
        warnings,plan:pl,signature:signature(cx,pl.day),pool:rows.length,combos:list.length,runs:D.final.runs,
        coverage:{version:1,selectedStage:teams.length?selectedStage:0,stages:hist},evaluation};
    }
    try{
      check();let best=await solve(pl.requested);
      if(!cx.split){
        for(const option of pl.options.slice(1)){
          if(D.split.exFirst&&best&&!best.teams.some(t=>t.kind==='ex'&&t.score<normalMaximum(G)*D.seals.costEx/D.seals.costNormal*D.split.weakExRatio))break;
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
      else if(best?.teams.some(t=>t.kind==='ex'&&t.score<normalMaximum(G)*2*D.split.weakExRatio))reason='EX 팀 점수가 낮아 일반 나눔도 비교했고 EX 묶음 합산이 더 높았음';
      else if(best?.teams.filter(t=>t.kind==='ex').length<pl.requested.ex)reason=`EX 팀 점수가 낮아 일반 ${best.teams.filter(t=>t.kind==='normal').length}팀이 더 높았음`;
      else reason='EX 한 팀 점수가 일반 두 팀 최대치보다 높아 EX를 골랐음';
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
  const api={search,plan,splits,fitSplit,normalMaximum,choosePlacement,signature};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GuildDaily=api;
})(typeof window!=='undefined'?window:globalThis);
