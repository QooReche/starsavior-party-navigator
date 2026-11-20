// Page adapter. Drafts, request ownership and caches never alias ordinary DIRECT.
const CDIRECT={state:null,shared:false,undo:{},rows:{},cache:new Map(),id:0,active:null,input:null,viewKey:null,error:'',saveError:'',loading:null,loadError:'',versions:null};
function cdSeason(){const c=D.cosmoRaid;return {id:c.season,levelMax:c.levelMax,bosses:c.bosses.map(b=>({...b,element:({태양:'sun',달:'moon',별:'star',질서:'order',혼돈:'chaos'})[b.element]||b.element}))};}
function cdInit(){
  const season=cdSeason();
  if(CDIRECT.state?.seasonId===season.id)return;
  cdCancel();CDIRECT.shared=!!SHARE.cd;
  CDIRECT.state=CosmoDirect.restore(SHARE.cd||LS.get(CosmoDirect.STORAGE_KEY),season);
  CDIRECT.undo={};CDIRECT.rows={};CDIRECT.input=null;CDIRECT.viewKey=null;
}
function cdSave(){if(!CDIRECT.shared)CDIRECT.saveError=LS.set(CosmoDirect.STORAGE_KEY,CosmoDirect.storage(CDIRECT.state))?'':'초안 저장 실패 · 이 세션에서만 유지됨';}
function cdCancel(){const a=CDIRECT.active;if(!a)return;CDIRECT.active=null;CDIRECT.id++;a.abort?.();simPoolDrop('cdirect',a.id);}
function cdChange(action,{record=false}={}){
  CDIRECT.placement?.cancel?.();
  const previous=CDIRECT.state,next=CosmoDirect.edit(previous,action);
  // An applied arrangement owns one undo entry even when the winner equals the current team.
  if(JSON.stringify(previous)===JSON.stringify(next)){if(record&&action.boss){CDIRECT.undo[action.boss]=previous.teams[action.boss];cdPaint();}return;}
  if(action.type!=='team'){
    cdCancel();CDIRECT.error='';
    for(const boss of Object.keys(previous.teams))if(JSON.stringify(previous.teams[boss])!==JSON.stringify(next.teams[boss]))CDIRECT.undo[boss]=previous.teams[boss];
  }
  CDIRECT.state=next;cdSave();cdPaint();
}
function cdUndo(boss){
  const team=CDIRECT.undo[boss];if(!team)return;
  CDIRECT.placement?.cancel?.();
  // A vacated member may have since been placed in another team. Never steal it.
  const used=CosmoDirect.usedBy(CDIRECT.state);
  if(team.draft.slots.some(m=>m&&used.has(m.key)&&used.get(m.key)!==boss)){CDIRECT.error='되돌릴 구원자가 다른 팀에서 사용 중임';cdPaint();return;}
  cdCancel();CDIRECT.state=CosmoDirect.restore({...CDIRECT.state,teams:{...CDIRECT.state.teams,[boss]:team}},cdSeason());
  delete CDIRECT.undo[boss];CDIRECT.error='';cdSave();cdPaint();
}
function cdArrange(boss){return cdArrangeSim(boss);}
function cdContext(){return {roster:R,info:MI.info,growth:MI.growth,slots:D.growthView.itemSlots,priority:D.journeyPriority,
  breaks:ownedSimBreaks(),options:simOpt('cosmo'),resolveBreak(draft){
    const automatic=pickBreak(draft.slots.filter(Boolean).map(m=>({s:BYKEY[m.key]})),'코스모 게이트',ownedSimBreaks().map(b=>b.name));
    return automatic?{name:automatic[1],level:brkLv(automatic[1])}:null;
  }};}
function cdInput(){return JSON.stringify([CDIRECT.state.seasonId,CDIRECT.state.teams,MI.hash,MI.error,!!MI.growth,ownedSimBreaks(),simOpt('cosmo'),SIMQ.seed,SIMQ.n,D.cosmoRaid]);}
function cdSync(){
  const input=cdInput();
  if(input!==CDIRECT.input){if(CDIRECT.input!==null)cdCancel();CDIRECT.input=input;CDIRECT.error='';}
  const viewKey=JSON.stringify([input,CDIRECT.versions,CDIRECT.loadError]);if(viewKey===CDIRECT.viewKey)return;
  CDIRECT.viewKey=viewKey;
  const ctx=cdContext(),validation=CosmoDirect.validate(CDIRECT.state,ctx),powers={},jobs={};
  let problem=MI.error||CDIRECT.loadError||(MI.info&&!MI.growth?'성장표를 불러오는 중':'');
  if(!problem){
    for(const [boss,t] of Object.entries(CDIRECT.state.teams)){
      try{
        const values=DirectParty.powers(t.draft,{...ctx,content:'cosmo'});powers[boss]=values.values.map(v=>v?.power??null);
        for(const job of CosmoDirect.jobs(CDIRECT.state,{...ctx,boss})){
          const snap={...job,stage:'코스모 게이트',brk:job.options.break_skill,seed:SIMQ.seed,runs:SIMQ.n,
            versions:{...CDIRECT.versions,season:CDIRECT.state.seasonId,account:MI.hash||null,policy:MyInfoReco.OVERWRITE_VERSION,preset:MI.growth?.assumed?.version||'standard'}};
          snap.sig=DirectParty.signature(snap);jobs[job.boss]=snap;
        }
      }catch(e){validation.teams[boss].ok=false;validation.teams[boss].errors.push({code:'data',message:e.message});}
    }
  }
  if(problem)for(const v of Object.values(validation.teams)){v.ok=false;v.errors.push({code:'data',message:problem});}
  validation.ok=Object.values(validation.teams).every(v=>v.ok);
  CDIRECT.validation=validation;CDIRECT.powers=powers;CDIRECT.jobs=problem?{}:jobs;
}
function cdResults(){return Object.fromEntries(Object.entries(CDIRECT.jobs||{}).flatMap(([boss,j])=>{
  const entry=CDIRECT.cache.get(j.sig);return entry?[[boss,entry.result]]:[];
}));}
function cdRefresh(){
  if(!D.cosmoRaid)return;cdInit();
  if(MI.growth||!MI.info)CDIRECT.loadError='';
  if(MI.info&&!MI.growth&&!CDIRECT.loading&&!MI.error){
    CDIRECT.loading=miGrowth().then(()=>{CDIRECT.loadError='';}).catch(e=>{CDIRECT.loadError=e.message;}).finally(()=>{CDIRECT.loading=null;cdPaint();});
  }
  cdPaint();
}
function cdPaint(){
  if(!CDIRECT.state)return;cdSync();
  const host=$('cosmo-direct-panel');
  if(host.hidden){GwenStage.destroy('cdirect');host.replaceChildren();return;}
  const results=cdResults(),summary=CosmoDirect.summary(CDIRECT.state,results),boss=CDIRECT.state.active;
  for(const [b,r] of Object.entries(results))summary.teams[b].turn=r.ta??r.ttk;
  const owned=new Set(MI.info?.units.map(u=>u.id)||[]);
  CosmoDirectUI.render(host,{state:CDIRECT.state,season:cdSeason(),validation:CDIRECT.validation,summary,
    roster:R.map(s=>({...s,owned:!MI.info||owned.has(s.uid)})),usedBy:CosmoDirect.usedBy(CDIRECT.state),
    running:!!CDIRECT.active,powers:CDIRECT.powers,breaks:ownedSimBreaks(),canUndo:!!CDIRECT.undo[boss]},
    {onTeam:boss=>cdChange({type:'team',boss}),onPickerJump:boss=>cdChange({type:'team',boss}),
      onLevel:(boss,level)=>cdChange({type:'level',boss,level}),onLevelAll:level=>cdChange({type:'levelAll',level}),
      onDraft:(boss,action)=>cdChange({type:'draft',boss,action}),onArrange:cdArrange,onUndo:cdUndo,onRunTeam:cdRun,onRunAll:()=>cdRun()});
  let status=host.querySelector('[data-cd-status]');
  if(!status){status=document.createElement('div');status.dataset.cdStatus='';status.setAttribute('role','status');host.querySelector('.cd-run').append(status);}
  const rows=Object.values(CDIRECT.rows),active=CDIRECT.active;
  status.textContent=CDIRECT.saveError||CDIRECT.error||rows.filter(r=>r.sig===CDIRECT.jobs[r.boss]?.sig&&r.error).map(r=>csBoss(r.boss)+': '+r.error).join(' · ')||
    (active?`확인 중 · ${active.bosses.reduce((n,b)=>n+(CDIRECT.rows[b]?.progress||0),0)}/${active.bosses.length*SIMQ.n}판`:!MI.info?'내 정보 없음 · 표준 육성 기준':'');
  if(MI.info&&!MI.growth&&(MI.error||CDIRECT.loadError)){const retry=document.createElement('button');retry.type='button';retry.className='sec';retry.textContent='자료 다시 불러오기';retry.dataset.cdRetry='';retry.onclick=()=>{MI.error='';CDIRECT.loadError='';cdRefresh();};status.append(retry);}
  if(active){const cancel=document.createElement('button');cancel.type='button';cancel.className='sec';cancel.textContent='취소';cancel.onclick=()=>{cdCancel();cdPaint();};status.append(cancel);}
  const stage=GwenStage.mount(host,{mode:'cdirect'});
  const r=results[boss];stage.update({mode:'cdirect',phase:active?'work':r?'result':'idle',
    result:r?GwenLane.resultId(r):null,clear:r?.cosmo?.clear??r?.clear,count:CDIRECT.state.teams[boss].draft.slots.filter(Boolean).length,
    progress:active?active.bosses.reduce((n,b)=>n+(CDIRECT.rows[b]?.progress||0),0)/(active.bosses.length*SIMQ.n):null});
}
async function cdRun(only=null){
  cdInit();cdSync();if(CDIRECT.active)return;
  const wanted=only?[only]:Object.keys(CDIRECT.state.teams);
  if(wanted.some(b=>!CDIRECT.jobs[b]))return;
  const id=++CDIRECT.id,input=cdInput(),active={id,bosses:wanted};CDIRECT.active=active;CDIRECT.error='';cdPaint();
  const live=()=>CDIRECT.active===active&&CDIRECT.id===id&&cdInput()===input;
  try{
    const manifest=await directManifest(active);if(!live())return;
    CDIRECT.versions={engine:manifest.ver,data:MyInfoReco.hash([D,QK.d,MI.growth])};cdSync();
    const jobs=wanted.map(b=>CDIRECT.jobs[b]).filter(j=>!CDIRECT.cache.has(j.sig));
    if(!jobs.length){CDIRECT.active=null;cdPaint();return;}
    active.bosses=jobs.map(j=>j.boss);let left=jobs.length;
    const finish=()=>{if(--left===0&&live())CDIRECT.active=null;cdPaint();};
    for(const snap of jobs){
      const boss=snap.boss,ws=scrPool(1),job={key:boss};
      CDIRECT.rows[boss]={boss,sig:snap.sig,progress:0,status:'waiting'};
      const fail=msg=>{if(!live())return;simPoolDrop('cdirect',id,boss);CDIRECT.rows[boss].error=msg;CDIRECT.rows[boss].status='error';finish();};
      const arm=simWatch(ws,()=>simTeamLimit(snap.runs),live,ready=>fail(ready?'계산 시간 초과':'계산 엔진 준비 시간 초과'));
      simDispatch(ws,[job],{owner:'cdirect',id,group:boss,live,arm,
        msg:()=>({type:'run',base:new URL('.',location.href).href,stage:snap.stage,n_runs:snap.runs,seed:snap.seed,options:snap.options,progress:true,
          teams:[{key:boss,party:snap.party,options:snap.options}]}),
        assigned(){CDIRECT.rows[boss].status='running';cdPaint();},
        stage(w,m){CDIRECT.rows[boss].progress=m.completed??CDIRECT.rows[boss].progress;cdPaint();},
        team(j,m){if(m.result.ver!==snap.versions.engine){fail('엔진 버전이 바뀜 · 다시 시도');return;}
          if(!Number.isFinite(m.result.cosmo?.mean)){fail('코스모 점수 결과 없음 · 다시 시도');return;}
          CDIRECT.cache.set(snap.sig,{result:directCopy(m.result)});Object.assign(CDIRECT.rows[boss],{status:'done',progress:snap.runs});},
        done:finish,error:fail});
    }
    cdPaint();
  }catch(e){if(live()){CDIRECT.active=null;CDIRECT.error='계산 실패 · 다시 시도: '+e.message;cdPaint();}}
}
function cdFromSearch(row){
  if(!row)return;cdInit();cdCancel();CDIRECT.state=CosmoDirect.fromSearch(row,cdSeason());CDIRECT.undo={};CDIRECT.error='';
  cdSave();directNavigate('direct');
}
function cdSearchSummary(row,mode){
  const season=cdSeason(),state=CosmoDirect.fromSearch(row,season),results=Object.fromEntries(row.teams.map(t=>[t.boss,{cosmo:t.st}]));
  return CosmoDirectUI.summaryHtml({state,season,roster:R,summary:CosmoDirect.summary(state,results,mode)});
}
