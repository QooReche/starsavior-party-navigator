// Shared recommendation stores, with snapshot-owned calculation and injectable notifications.
// DIRECT never calls showReco/runCore to start work or changes the input controls.
function recoIdentity(){
  const c=contents[$('content').value],st=cur?.[$('stage').value];
  return JSON.stringify([c.key,st?.tab,st?.name,MI.hash,simOpt(c.key),SIMQ.n,SIMQ.seed,
    [...document.querySelectorAll('#own input:checked')].map(x=>x.dataset.k),breakOwned(),MI.brkLv,
    [...EXCL],MM,BLOOM,PW,$('grow').value,$('mypow').value,growthOptions(),MI.growth?.assumed?.version,
    Object.hasOwn(SHARE,'b')?SESSION_BR:BRSEL]);
}
function recoSnapshot(){
  const copy=x=>JSON.parse(JSON.stringify(x)),c=copy(contents[$('content').value]),st=copy(cur[$('stage').value]);
  const info=copy(MI.info),profile=miMode()?MyInfoReco.profile(info,R,MI.growth,c.key):null;
  const own=new Set([...document.querySelectorAll('#own input:checked')].map(x=>x.dataset.k));
  if(!info&&!own.size)for(const s of R)if(!EXCL.has(s.key))own.add(s.key);
  const have=breakOwned().slice(),levels=copy(MI.brkLv||{}),selected=copy(Object.hasOwn(SHARE,'b')?SESSION_BR:BRSEL),shared=Object.hasOwn(SHARE,'b'),sharedBreak=SHARE.b;
  const breakFor=t=>{
    const k=c.key+'|'+ckey(t.combo),saved=Object.hasOwn(selected,k)?selected[k]:shared?sharedBreak:undefined;
    const automatic=pickBreak(t.combo,c.name,have),name=saved!==undefined&&(saved===''||have.includes(saved))?saved:automatic?.[1];
    return name?{name,level:levels[name]||5}:null;
  };
  const bloom=copy(BLOOM),sv=QK.d.sv,engineKey=k=>!(profile?.results[k])&&bloom[k]&&sv[k+BLV]?k+BLV:k;
  const qi=copy(quickIn(c,st));if(!info){qi.growth=1;qi.power=null;}
  const x={ck:c.key,rk:rkOf(c.key),sn:starOf(c.key),account:profile?MI.hash:null,growth:growthEnabled()?growthCacheTag():null,party:t=>simParty(t,engineKey)};
  const scrown=[...own].sort().join(',')+'|'+have.join(','),mm=MM||'';
  const screenKey=p=>JSON.stringify([c.key,st.tab,st.name,+p,x.rk,x.sn,x.account||'',scrown,mm,...(x.growth?[x.growth]:[])]);
  const n=SIMQ.n,seed=SIMQ.seed,refined=new Set(SIMQ.refined||[]);
  const sig=t=>simSignature(x,st,t,breakFor(t)?.name||null,n,refined);
  const scoring={gim:gimTop(c,st),season:st.sb||[],damage:[Math.min(1,(st.n-1)/2),c.boss?CFG.damage.weightBoss:CFG.damage.weightMob]};
  const defPen=CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty;
  // Candidates and serialized stats are fixed before any asynchronous worker callback.
  const initial=recoCandidates(c,st,own,new Set(),defPen,qi,profile,scoring);
  const picks=copy(PICK),boxes={},plans=new Map(),more={};
  plans.set('',initial);
  const result=t=>SIMQ.res[sig(t)];
  let joint=growthScoreEnv(scoring,()=>jointPick(c,st,own,defPen,initial.qt));
  function plan(wanted){
    const used=new Set();
    for(let p=1;p<=wanted;p++){
      const k=[...used].sort().join(',');
      if(!plans.has(k))plans.set(k,recoCandidates(c,st,own,used,defPen,qi,profile,scoring));
      const qt=plans.get(k).qt;if(!qt?.length)return null;
      const mk=moreKey(st,p),rows=quickRows(qt,st,p,{n:more[p]||SIMQ.more[mk]||3,sc:SIMQ.scr[screenKey(p)],result,joint});
      boxes[p]=LASTQ[p]={all:qt,rows,total:new Set(qt.map(t=>ckey(t.combo))).size};
      const forced=picks[c.key+'|'+st.tab+'|'+st.name+'|'+p],chosen=forced&&qt.find(t=>ckey(t.combo)===forced)||rows[0];
      chosen?.keys.forEach(k=>used.add(k));
    }
    SCROWN=scrown;JOINT=joint;return boxes[wanted];
  }
  const meta=directRecoMeta(c,st,n);
  return {key:recoIdentity(),c,st,info,profile,qi,scoring,defPen,own,breakFor,party:x.party,sig,screenKey,n,seed,options:copy(simOpt(c.key)),plan,result,meta,
    more(p,n){more[p]=n;SIMQ.more[moreKey(st,p)]=n;},excluded:[...EXCL],priority:copy(D.journeyPriority),growth:MI.growth,
    first(){const t=boxes[1]?.rows[0];return t&&result(t)?{team:t,result:result(t),sig:sig(t)}:null;}};
}
function recoTaskCancel(message='중단함'){
  const task=RECO.task;if(!task||task.done)return;
  task.cancelled=true;task.abort?.();task.stop?.();simPoolDrop(task.owner);
  SIMQ.busy=null;SIMQ.screening=false;SIMQ.err=message;
}
function recoEvaluate(snapshot,task,jobs,n,{screen=false,onTeam=()=>{}}={}){
  return new Promise((resolve,reject)=>{
    if(!jobs.length){resolve();return;}
    const id=++task.request,ws=scrPool(jobs.length);let ended=false;
    const live=()=>!ended&&!task.cancelled&&RECO.task===task&&snapshot.key===recoIdentity();
    const finish=error=>{if(ended)return;ended=true;task.stop=null;if(error){simPoolDrop(task.owner,id);reject(Error(error));}else resolve();};
    task.stop=()=>finish('중단함');
    const arm=simWatch(ws,()=>simTeamLimit(n),live,ready=>finish(ready?'계산 시간 초과':'계산 엔진 준비 시간 초과'));
    let got=0;task.progress=0;recoProgressPaint(task);
    simDispatch(ws,jobs,{owner:task.owner,id,live,arm,
      msg:j=>({type:'run',base:new URL('.',location.href).href,stage:snapshot.c.key+'/'+snapshot.st.tab+'/'+snapshot.st.name,
        n_runs:j.runs||n,seed:snapshot.seed,options:{...snapshot.options,...(screen?{rng_streams:true}:{})},
        teams:[{key:j.key,party:j.party,options:j.options}]}),
      stage(w,m){if(m.msg==='준비 끝')SIMQ.loaded=true;if(/^시뮬 \d+\//.test(m.msg||''))w._t=Date.now();},
      team(j,m,w){if(m.result.ver!==task.engine){finish('엔진 버전이 바뀜 · 다시 시도');return;}
        if(w._t)simRateAdd((Date.now()-w._t)/(j.runs||n),screen?'scr':'final');w._t=0;
        onTeam(j,{...m.result,n});got++;task.progress=got/jobs.length;task.message=`${screen?'예선':'본선'} ${got}/${jobs.length}팀`;
        const rate=screen?SIMQ.rateS:SIMQ.rate;task.remaining=rate?(jobs.length-got)*n*rate/Math.max(1,ws.length):null;
        SIMQ.msg=task.message;recoProgressPaint(task);directResultsPaint();
      },done(){finish();},error:msg=>finish(msg)});
  });
}
function recoScreenCalculate(snapshot,task,p,box){
  const key=snapshot.screenKey(p),by=new Map(box.all.map(t=>[ckey(t.combo),t]));
  const pool=scrPick(box.all,SCR_RK&&snapshot.options.rekindle?rkQuickTop(snapshot.c,snapshot.st,box.all,SCR_RK,snapshot.qi):null);
  let sc=SIMQ.scr[key];
  if(!sc||sc.done)sc=SIMQ.scr[key]={done:false,order:[],n:pool.length,total:pool.length,pool,res:{},res2:{},up:null,round:0,left:pool.length};
  if(pool.length<=3){sc.done=true;sc.order=pool;return Promise.resolve();}
  SIMQ.screening=true;task.message='예선 준비 중';
  return new Promise((resolve,reject)=>{
    const leg=(i,keys,next)=>{
      const n=SCR_ROUNDS[i].n;sc.round=i;sc.left=keys.length;sc.got=0;
      const jobs=keys.map(key=>{const t=by.get(key),raw=i?sc.res[key]?.raw:null;return {key,party:snapshot.party(t),runs:raw?n-SCR_ROUNDS[0].n:n,
        options:{break_skill:snapshot.breakFor(t),...(raw?{run_offset:SCR_ROUNDS[0].n,merge_raw:raw}:{raw_runs:true})}};});
      recoEvaluate(snapshot,task,jobs,n,{screen:true,onTeam(j,r){(i?sc.res2:sc.res)[j.key]=r;sc.got++;}}).then(next,reject);
    };
    recoScreenSequence(sc,SCR_ROUNDS[1].top,by,leg,()=>{scrClose(sc);SIMQ.screening=false;resolve();});
  });
}
async function recoCalculate(snapshot,task){
  return RecommendPipeline.recommendation({parties:snapshot.c.parties||1,screened:(snapshot.c.parties||1)===1,
    live:()=>!task.cancelled&&snapshot.key===recoIdentity(),plan:snapshot.plan,screenState:p=>SIMQ.scr[snapshot.screenKey(p)],
    screen:(p,box)=>recoScreenCalculate(snapshot,task,p,box),more:snapshot.more,result:snapshot.result,goal:goalVal,first:snapshot.first,
    async final(p,box){
      SIMQ.busy=p;SIMQ.screening=false;task.message='본선 준비 중';
      for(const t of box.rows.filter(t=>!snapshot.result(t))){
        const party=snapshot.party(t),key=t.placementKey;if(PLACEMENT_CACHE.has(key))continue;
        task.message='배치·리더 24조건 비교 중';recoProgressPaint(task);
        const winner=await placementRun({party,stage:snapshot.c.key+'/'+snapshot.st.tab+'/'+snapshot.st.name,options:snapshot.options,brk:snapshot.breakFor(t),owner:task.owner,
          live:()=>!task.cancelled&&snapshot.key===recoIdentity(),register:f=>task.stop=f,onProgress:d=>{task.progress=d/24;recoProgressPaint(task);}});
        rememberPlacement(t,key,winner.p);task.stop=null;
      }
      const jobs=box.rows.filter(t=>!snapshot.result(t)).map(t=>({key:snapshot.sig(t),party:snapshot.party(t),options:{break_skill:snapshot.breakFor(t)}}));
      await recoEvaluate(snapshot,task,jobs,snapshot.n,{onTeam(j,r){
        SIMQ.res[j.key]=r;const meta=JSON.parse(JSON.stringify(snapshot.meta));meta.parts[7].engine=r.ver;meta.condition=JSON.stringify(meta.parts);meta.recommendationKey=snapshot.key;(SIMQ.meta??={})[j.key]=meta;
      }});
    }});
}
async function recoEnsure(){
  if(RECO.task&&!RECO.task.done&&RECO.task.key===recoIdentity())return RECO.task.promise;
  if(!MI.info)RECO.standard=true;
  const snapshot=recoSnapshot(),task={key:snapshot.key,owner:'reco-bundle',request:0,cancelled:false,done:false,message:'실행 준비 중'};
  RECO.task=task;REQ=true;SIMQ.kick=true;SIMQ.err='';SIMQ.busy=1;
  recoProgressPaint(task);
  task.promise=(async()=>{try{
    const manifest=await directManifest(task);task.engine=manifest.ver;
    if(task.cancelled||snapshot.key!==recoIdentity())throw Error('입력이 바뀜');
    return await recoCalculate(snapshot,task);
  }finally{task.done=true;if(RECO.task===task){SIMQ.busy=null;SIMQ.screening=false;run(true);}}})();
  return task.promise;
}
async function recoGrowthEnsure(){
  const c=contents[$('content').value],st=cur[$('stage').value];
  if(GROW.phase==='done'&&GROW.sig===growthSig(c,st))return GROW.result;
  const snapshot=recoSnapshot(),task={key:snapshot.key,owner:'growth-bundle',request:0,cancelled:false,done:false,message:'육성 준비 중'};
  RECO.task=task;const id=++GROW.id;GROW.phase='running';GROW.errors=[];GROW.msg='육성 계획 탐색';SIMQ.busy='growth';
  task.promise=(async()=>{try{
    const manifest=await directManifest(task);task.engine=manifest.ver;
    const live=()=>!task.cancelled&&GROW.id===id&&snapshot.key===recoIdentity();
    if(!live())throw Error('입력이 바뀜');
    GROW.versions={engine:manifest.ver,data:MyInfoReco.hash([GrowthGuide.VERSION,MI.growth,D,QK.d])};GROW.historyEngine=manifest.ver;GROW.sig=growthSig(c,st);
    const signature=GROW.sig,baseline=LASTQ[1]?.rows[0]&&SIMQ.res[simSig(st,LASTQ[1].rows[0])];
    if(!baseline)throw Error('자동 추천 완료 결과 필요');
    const grown=MyInfoReco.overwrite(snapshot.info,R,snapshot.growth,c.key,{excluded:snapshot.excluded,slots:DIRECT.slots,priority:snapshot.priority});
    const plan=recoCandidates(snapshot.c,snapshot.st,new Set(Object.keys(grown.profile.results).filter(k=>!snapshot.excluded.includes(k))),new Set(),snapshot.defPen,snapshot.qi,grown.profile,snapshot.scoring);
    const keys=scrPick(plan.qt||[],SCR_RK&&snapshot.options.rekindle?rkQuickTop(c,st,plan.qt,SCR_RK,snapshot.qi):null);
    const state={errors:[],stop:null,msg:'',progress:0};
    task.stop=()=>state.stop?.();GROW.stop=()=>{task.cancelled=true;state.stop?.();simPoolDrop(task.owner);};
    const started=Date.now(),result=await growthStageSearch(snapshot.c,snapshot.st,grown.profile,id,{live,qi:snapshot.qi,candidates:plan.cands,all:plan.qt||[],keys,
      job:(t,k)=>({id:k,t,party:snapshot.party(t),options:{break_skill:snapshot.breakFor(t)},breakName:snapshot.breakFor(t)?.name||null}),
      seed:snapshot.seed,n:snapshot.n,state,owner:task.owner,nextRequest:()=>++task.request,version:task.engine,options:snapshot.options,
      paint(){task.message=state.msg;task.progress=state.progress;GROW.msg=state.msg;GROW.errors=state.errors;growthPaint();directResultsPaint();}});
    if(!live()||signature!==growthSig(c,st))throw Error('입력이 바뀜');
    GROW.result={...result,baseline,snapshot:grown,kind:c.key,ms:Date.now()-started,baselineFirst:true,condition:directConditions(c,st),
      signature:JSON.stringify(['grown-account',MyInfoReco.OVERWRITE_VERSION,grown.preset,GROW.sig])};GROW.phase='done';return GROW.result;
  }catch(e){if(GROW.id===id){GROW.phase='error';GROW.msg='미완료';GROW.errors.push(e.message);}throw e;
  }finally{task.done=true;if(RECO.task===task){SIMQ.busy=null;GROW.stop=null;growthPaint();directResultsPaint();}}})();return task.promise;
}
