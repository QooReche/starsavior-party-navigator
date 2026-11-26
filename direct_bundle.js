// Execution choices are not a draft, payload, or simulation signature.
function directBundleCondition(){const c=contents[$('content').value],st=cur?.[$('stage').value];return JSON.stringify([c.key,st?.tab,st?.name,MI.hash,simOpt(c.key),SIMQ.n,SIMQ.seed]);}
function directBundleControls(){
  if(!$('direct-with-reco'))return;
  $('direct-with-reco').checked=!!DIRECT.withReco;
  $('direct-with-growth').checked=growthEnabled();
  $('direct-with-growth').disabled=!DIRECT.withReco||!MI.info;
  $('direct-growth-info').hidden=!!MI.info;
  $('direct-with-summary').textContent='같이 볼 것'+(DIRECT.withReco?' · 추천 같이'+(growthEnabled()&&MI.info?' · 육성 포함':''):'');
}
function directBundleInit(){
  DIRECT.withReco=LS.get('direct.with.v1')?.reco===true;
  $('direct-with').open=false;
  $('direct-with').addEventListener('toggle',()=>{ $('direct-with-summary').setAttribute('aria-expanded',String($('direct-with').open)); });
  $('direct-steps-toggle').addEventListener('click',()=>{DIRECT.stepsExpanded=!DIRECT.stepsExpanded;directBundlePaint();});
  $('direct-with-reco').addEventListener('change',e=>{
    DIRECT.withReco=e.target.checked;LS.set('direct.with.v1',{reco:DIRECT.withReco});directBundleControls();
    if(DIRECT.withReco)GwenLane.edit('withReco');
  });
  $('direct-with-growth').addEventListener('change',e=>{
    $('assume-growth').checked=e.target.checked;$('assume-growth').dispatchEvent(new Event('change',{bubbles:true}));
    directBundleControls();if(e.target.checked)GwenLane.edit('withGrowth');
  });
  directBundleControls();
}
function directBundleSync(){
  const b=DIRECT.bundle;
  if(b?.running&&b.condition!==directBundleCondition())directBundleCancel('입력이 바뀜');
  directBundleControls();
}
function directBundleCancel(message='중단함'){
  const b=DIRECT.bundle;if(!b?.running){directCancel(message);return;}
  b.cancelled=true;b.running=false;
  directCancel(message);
  // Joined recommendation-tab work belongs to its original request; detach, do not kill it.
  if(b.ownedTask&&RECO.task===b.ownedTask)recoTaskCancel(message);
  for(const step of b.steps)if(['waiting','running'].includes(step.status)){step.status='cancelled';step.message=message;}
  directResultsPaint();
}
function directBundleSkip(kind){
  const b=DIRECT.bundle;if(!b?.running)return;
  for(const step of b.steps){
    if(step.kind!==kind&&!(kind==='reco'&&step.kind==='growth'))continue;
    if(!['waiting','running'].includes(step.status))continue;
    step.status='skipped';step.message=step.kind!==kind?'자동 추천이 없어 같이 건너뜀':'건너뜀';
    if(step.kind===b.current&&b.ownedTask&&RECO.task===b.ownedTask)recoTaskCancel('건너뜀');
  }
  GwenLane.edit('skip');directResultsPaint();
}
const directPause=ms=>new Promise(ok=>setTimeout(ok,ms));
// Recommendation-tab presentation consumes the same task without launching another pipeline.
function recoProgressPaint(task){
  if(task.owner!=='reco-bundle'||task.done||task.cancelled)return;
  let el=$('out').querySelector('[data-bundle-progress]');
  if(!el){$('out').innerHTML=`<div class="party progress" data-bundle-progress data-state="running"><b class="case-title">추천 편성 확인 중</b><div class="pbar" role="progressbar" aria-valuemin="0" aria-valuemax="100"><i></i></div><p role="status"></p><p class="mut">예선 뒤 상위 팀을 모의 전투함 · 직접 편성과 같은 작업임</p><button type="button" class="sec" data-direct-action="skip" data-kind="reco">건너뛰기</button></div>`;el=$('out').firstElementChild;}
  const alert=scrAlertSync(el,task.sc);   // 관측 경보(훑기) — 상태가 바뀔 때만 DOM 을 바꿈
  if(typeof recheckBundle==='function')recheckBundle(el);   // 현장 재조사(자리·리더 비교) 칸
  el.querySelector('[role=status]').textContent=task.message;
  const value=Math.round((task.progress||0)*100),bar=el.querySelector('.pbar');bar.setAttribute('aria-valuenow',value);bar.firstElementChild.style.width=value+'%';
  recoGwenShow(true,task.progress||0,null,GwenLane.resultId(task)+':'+task.request,scrAlertLane(alert));
}
async function directAwait(b,predicate,step){
  while(!predicate()){
    if(b.cancelled||step?.status==='skipped'||b.condition!==directBundleCondition())throw Error('중단함');
    await directPause(100);
  }
}
function directRecoReady(){
  const c=contents[$('content').value],st=cur?.[$('stage').value];
  if(!st||SIMQ.busy!=null||SIMQ.screening)return false;
  for(let p=1;p<=(c.parties||1);p++){
    const box=LASTQ[p];if(!box?.rows?.length||box.rows.some(t=>!SIMQ.res[simSig(st,t)]))return false;
    if(typeof simArrangeDone==='function'&&!simArrangeDone(box.rows))return false;   // 본선 끝 ~ 자리·리더 비교 시작 사이 틈을 «준비됨»으로 보지 않음
    if((c.parties||1)===1&&!SIMQ.scr[scrKey(st,p)]?.done)return false;
    if(box.rows.every(t=>goalVal(SIMQ.res[simSig(st,t)])<.5)&&box.rows.length<Math.min(9,box.total))return false;
  }
  return true;
}
async function directRun(only=null){
  if(DIRECT.bundle?.running){directBundleCancel();return;}
  if(seasonBlocked(contents[$('content').value]?.key))return;
  if(!directRecoSupported())return;
  if(only==='now'||only==='grown'||!only&&!DIRECT.withReco){DIRECT.bundle=null;return directRunRows(only);}
  if(only==='growth'&&!growthEnabled()&&MI.info){$('assume-growth').checked=true;$('assume-growth').dispatchEvent(new Event('change'));}
  const b={id:(DIRECT.bundleSerial=(DIRECT.bundleSerial||0)+1),running:true,cancelled:false,legacyJoined:SIMQ.busy!=null&&(!RECO.task||RECO.task.done),condition:directBundleCondition(),steps:[],current:null};
  if(!only)b.steps.push({kind:'direct',label:'내 편성',status:'waiting'});
  // A growth-only row needs a real completed recommendation baseline.
  b.steps.push({kind:'reco',label:'자동 추천',status:'waiting'});
  if((only==='growth'||!only&&growthEnabled())&&MI.info)b.steps.push({kind:'growth',label:'육성 포함 추천',status:'waiting'});
  DIRECT.bundle=b;DIRECT.runError='';directResultsPaint();
  for(const step of b.steps){
    if(b.cancelled)break;if(step.status==='skipped')continue;
    b.current=step.kind;step.status='running';b.ownedTask=null;step.message='실행 준비 중';directResultsPaint();
    try{
      if(step.kind==='direct'){
        await directRunRows();await directAwait(b,()=>!DIRECT.active,step);
        const r=DIRECT.rows.now;
        if(r?.status==='done'&&r.sig===DIRECT.expected?.now?.sig){step.message=`완료 · ${Math.round(r.result.clear*100)}%`;b.reportUntil=Date.now()+1800;directResultsPaint();setTimeout(directResultsPaint,1850);}
        else {step.status=r?.status==='error'?'error':'cancelled';step.message=r?.error||'편성이 바뀜';}
      }else if(step.kind==='reco'){
        const joined=SIMQ.busy!=null||SIMQ.screening||RECO.task&&!RECO.task.done;
        if(joined){step.message='추천 탭에서 계산 중 · 끝나면 가져옴';step.joined=true;directResultsPaint();
          await directAwait(b,()=>directRecoReady()||!!SIMQ.err||!REQ&&SIMQ.busy==null,step);
          if(!directRecoReady())throw Error('추천 탭 계산이 끝나지 않았음');
        }
        if(directRecoReady())step.message='추천 탭 결과 사용';
        else {const promise=recoEnsure();b.ownedTask=RECO.task;await promise;step.message='완료';}
        directCollectRecommendation();
      }else{
        const c=contents[$('content').value],st=cur[$('stage').value];
        if(GROW.phase==='running'){
          step.joined=true;step.message='추천 탭에서 계산 중 · 끝나면 가져옴';directResultsPaint();
          await directAwait(b,()=>GROW.phase!=='running',step);
        }
        if(GROW.phase==='done'&&GROW.sig===growthSig(c,st))step.message='추천 탭 결과 사용';
        else {const promise=recoGrowthEnsure();b.ownedTask=RECO.task;await promise;step.message='완료';}
        directCollectGrowth();
      }
      if(step.status==='running')step.status='done';
    }catch(e){if(step.status==='running'){step.status=b.cancelled?'cancelled':'error';step.message='실패 · 다시 시도';step.error=e.message;}
      if(step.kind==='reco')for(const next of b.steps)if(next.kind==='growth'&&next.status==='waiting'){next.status='skipped';next.message='자동 추천이 없어 같이 건너뜀';}
    }
    directResultsPaint();
  }
  b.running=false;b.current=null;b.finished=!b.cancelled;directResultsPaint();
}
function directCollectGrowth(){
  const c=contents[$('content').value],st=cur?.[$('stage').value],r=GROW.result;
  if(!st||GROW.phase!=='done'||!r||GROW.sig!==growthSig(c,st))return;
  // Freeze the actual first recommendation as the comparison baseline; never selected alternatives.
  const first=LASTQ[1]?.rows[0],baseline=first&&SIMQ.res[simSig(st,first)];if(!baseline)return;
  // Adoption shares both the result and its first-recommendation baseline with the tab.
  r.baseline=baseline;r.baselineFirst=true;
  DIRECT.growthCompare={result:r.best,team:r.team?.t,condition:directConditions(c,st),growthSig:GROW.sig,
    metric:simOpt(c.key).star_turns?'t60':'clear',none:!growthBetter(c.key,baseline,r.best),message:growthNoneText(c.key,{...r,baseline}),source:r};
}
function directBundlePaint(){
  const b=DIRECT.bundle,el=$('direct-steps');if(!el)return;
  const toggle=$('direct-steps-toggle');
  toggle.hidden=!b||b.running;el.hidden=!b;
  if(!b){$('direct-stage-number').textContent='';return;}
  if(DIRECT.stepsBundle!==b.id||b.running){DIRECT.stepsBundle=b.id;DIRECT.stepsExpanded=false;}
  toggle.textContent=`${b.steps.filter(s=>s.status==='done').length}단계 완료`;
  toggle.setAttribute('aria-expanded',String(!!DIRECT.stepsExpanded));
  const expanded=b.running||DIRECT.stepsExpanded;
  el.hidden=!expanded&&b.steps.every(s=>s.status==='done');
  const active=RECO.task&&!RECO.task.done?RECO.task:null;
  // Preserve the skip buttons while changing only status text during progress callbacks.
  const shape=b.id+'|'+b.steps.map(s=>s.kind+':'+s.status).join('|');
  if(el.dataset.shape!==shape){el.dataset.shape=shape;el.innerHTML=b.steps.map((s,i)=>`<li data-step="${s.kind}"><b>${i+1}. ${s.label}</b><span role="status"></span>${s.kind!=='direct'&&['waiting','running'].includes(s.status)?`<button type="button" class="sec" data-direct-action="skip" data-kind="${s.kind}"><span>건너뛰기</span><span>건너뜀</span></button>`:''}</li>`).join('');}
  for(const step of b.steps){const row=el.querySelector(`[data-step="${step.kind}"]`),working=step.status==='running';
    const own=working&&step.kind==='direct'&&Object.values(DIRECT.rows).find(r=>r.status==='running');
    row.hidden=!expanded&&step.status==='done';
    // 관측 경보(훑기): 직접 편성 단계 줄에도 같은 표시(문구는 CSS attr 로)
    const alert=working&&step.kind==='reco'&&!step.joined&&active&&!active.cancelled?scrAlertLane(scrAlertOf(active.sc)):'';
    if((row.dataset.alert||'')!==alert){if(alert){row.dataset.alert=alert;row.dataset.alertText=alert==='scan'?SCR_ALERT.title:SCR_ALERT.found(UiShared.numText(active.sc.pool.length));}else{delete row.dataset.alert;delete row.dataset.alertText;}}
    row.dataset.state=step.status;row.querySelector('[role=status]').textContent=own?`계산 중 · ${own.progress||0}/${own.snapshot.runs}판`:working&&step.kind!=='direct'&&!step.joined&&active?active.message:step.message||({waiting:'대기',running:'계산 중',done:'완료',error:'실패 · 다시 시도',cancelled:'중단함',skipped:'건너뜀'}[step.status]);
  }
  $('direct-stage-number').textContent=b.running?`${Math.max(1,b.steps.findIndex(s=>s.kind===b.current)+1)}/${b.steps.length} 단계${active?.remaining?` · 약 ${Math.max(1,Math.ceil(active.remaining/60000))}분 남음`:''}`:'';
}
