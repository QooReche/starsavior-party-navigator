// Shared recommendation stores, with snapshot-owned calculation and injectable notifications.
// DIRECT never calls showReco/runCore to start work or changes the input controls.
// 보유 구원자·브레이크 스킬 서명(SCROWN·예선 키 재료). 화면(party_template.html)과 이 파일이 같이 씀
function scrownOf(own,have){return UiShared.teamKey([...own])+'|'+have.join(',');}
function recoIdentity(){
  const c=contents[$('content').value],st=cur?.[$('stage').value];
  return JSON.stringify([c.key,st?.tab,st?.name,MI.hash,...recommendationPolicyTag(),simOpt(c.key),SIMQ.n,SIMQ.seed,
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
  const x={ck:c.key,guild:c.key==='guild'?copy(guildOptions()):null,rk:rkOf(c.key),sn:starOf(c.key),account:profile?MI.hash:null,growth:growthEnabled()?growthCacheTag():null,party:t=>simParty(t,engineKey)};
  const scrown=scrownOf(own,have),mm=MM||'';
  const screenKey=p=>JSON.stringify([c.key,st.tab,st.name,...(x.guild?[x.guild]:[]),+p,x.rk,x.sn,x.account||'',scrown,mm,...recommendationPolicyTag(),...(x.growth?[x.growth]:[])]);
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
      const k=UiShared.teamKey([...used]);
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
  return {key:recoIdentity(),c,st,info,profile,qi,scoring,defPen,own,breakFor,party:x.party,sig,
    partyAt:(t,arr)=>simParty(t,engineKey,arr),partyRule:t=>simParty(t,engineKey,arrangeOf(t.combo,true)),
    sigRule:t=>simSignature({...x,party:t2=>simParty(t2,engineKey,arrangeOf(t2.combo,true))},st,t,breakFor(t)?.name||null,n,refined),
    sigAt:(t,arr)=>simSignature({...x,party:t2=>simParty(t2,engineKey,arr)},st,t,breakFor(t)?.name||null,n,refined),screenKey,n,seed,options:copy(simOpt(c.key)),plan,result,meta,
    more(p,n){more[p]=n;SIMQ.more[moreKey(st,p)]=n;},excluded:[...EXCL],priority:copy(D.journeyPriority),growth:MI.growth,
    first(){const t=boxes[1]?.rows[0];return t&&result(t)?{team:t,result:result(t),sig:sig(t)}:null;}};
}
function recoTaskCancel(message='중단함'){
  const task=RECO.task;if(!task||task.done)return;
  task.cancelled=true;task.abort?.();task.stop?.();simPoolDrop(task.owner);
  SIMQ.busy=null;SIMQ.screening=false;SIMQ.err=message;
}
function recoEvaluate(snapshot,task,jobs,n,{screen=false,label=null,text=null,onTeam=()=>{}}={}){
  return new Promise((resolve,reject)=>{
    if(!jobs.length){resolve();return;}
    const id=++task.request,ws=scrPool(jobs.length);let ended=false;
    const live=()=>!ended&&!task.cancelled&&RECO.task===task&&snapshot.key===recoIdentity();
    const finish=error=>{if(ended)return;ended=true;task.stop=null;if(error){simPoolDrop(task.owner,id);reject(Error(error));}else resolve();};
    task.stop=()=>finish('중단함');
    const arm=simWatch(ws,()=>simTeamLimit(n),live,ready=>finish(ready?'계산 시간 초과':'계산 엔진 준비 시간 초과'));
    let got=0;task.progress=0;recoProgressPaint(task);
    // 진행·결과 칸 갱신은 SearchExecutor.PAINT_MS 간격으로만(훑기 A-1, 결과 불변). 끝(done)에는 밀린 갱신을 바로 함
    const paint=SearchExecutor.throttle(()=>{recoProgressPaint(task);directResultsPaint();},SearchExecutor.PAINT_MS,live);
    simDispatch(ws,jobs,{owner:task.owner,id,live,arm,chunk:screen?SearchExecutor.chunkSize(jobs.length,ws.capacity):1,     // 훑기·예선 묶음(A-2), 본선은 팀 하나씩
      msg:j=>({type:'run',base:new URL('.',location.href).href,stage:snapshot.c.key+'/'+snapshot.st.tab+'/'+snapshot.st.name,
        n_runs:j.runs||n,seed:j.seed??snapshot.seed,options:{...snapshot.options,...(screen?{rng_streams:true}:{})},
        teams:[{key:j.key,party:j.party,options:j.options}]}),
      stage(w,m){if(m.msg==='준비 끝')SIMQ.loaded=true;if(/^시뮬 \d+\//.test(m.msg||''))w._t=Date.now();},
      team(j,m,w){if(m.result.ver!==task.engine){finish('엔진 버전이 바뀜 · 다시 시도');return;}
        if(w._t)simRateAdd((Date.now()-w._t)/(j.runs||n),screen?'scr':'final');w._t=0;
        onTeam(j,{...m.result,n});got++;task.progress=got/jobs.length;task.message=text?text(got,jobs.length):`${label||(screen?'예선':'본선')} ${got}/${jobs.length}팀`;
        const rate=screen?SIMQ.rateS:SIMQ.rate;task.remaining=rate?(jobs.length-got)*n*rate/Math.max(1,ws.length):null;
        SIMQ.msg=task.message;paint();
      },done(){paint.flush();finish();},error:msg=>{paint.cancel();finish(msg);}});
  });
}
function recoScreenCalculate(snapshot,task,p,box){
  const key=snapshot.screenKey(p),by=new Map(box.all.map(t=>[ckey(t.combo),t]));
  const pool=scrPick(box.all,SCR_RK&&snapshot.options.rekindle?rkQuickTop(snapshot.c,snapshot.st,box.all,SCR_RK,snapshot.qi):null);
  let sc=SIMQ.scr[key];
  if(!sc||sc.done)sc=SIMQ.scr[key]=scrFullInit({done:false,order:[],n:pool.length,total:pool.length,pool,res:{},res2:{},up:null,round:0,left:pool.length},box.all);
  if(pool.length<=3){sc.done=true;sc.order=pool;return Promise.resolve();}
  SIMQ.screening=true;task.message='예선 준비 중';task.sc=sc;   // 관측 경보(scrAlertOf)가 읽음
  return new Promise((resolve,reject)=>{
    const leg=(i,keys,next)=>{
      // i = -1 은 후보 전체 훑기(scrFullInit, 전원 «못 깸» 스테이지만) — 1판. 앞 단계 판 이어 쓰기는 화면과 같은 scrPrior·scrLegOpt
      const n=scrRoundN(i);scrLegEnter(sc,i,keys.length,()=>{if(RECO.task===task){recoProgressPaint(task);directResultsPaint();}});
      const jobs=keys.map(key=>{const t=by.get(key),pr=scrPrior(sc,i,key);return {key,party:snapshot.party(t),runs:pr?n-pr.off:n,
        options:{break_skill:snapshot.breakFor(t),...scrLegOpt(pr)}};});
      recoEvaluate(snapshot,task,jobs,n,{screen:true,...(i<0?{label:SCR_ALERT.label,text:(got,all)=>scrMsg(-1,got,all)}:{}),onTeam(j,r){(i<0?sc.res0:i?sc.res2:sc.res)[j.key]=r;sc.got++;}}).then(next,reject);
    };
    recoScreenSequence(sc,SCR_ROUNDS[1].top,by,leg,()=>{scrClose(sc);SIMQ.screening=false;resolve();});
  });
}
// ── 현장 재조사(11/23): 아래 자리·리더 비교를 화면에 보여 주는 상태 하나. recoArrange 가 단계·끝난 조합 수를 알리고(recheckNote),
// 결과 판 맨 위 재조사 칸·그웬 길(사무실 장면)이 읽는다(party_template.html recheckPaint·recheckLane, recheck_ui.js, gwen_lane.js recheckSync).
// state: work(비교 중) → done(바뀜 changed / 그대로 same) · cancel(«지금 자리로 확정») · error. 비교할 팀이 없으면(보이는 팀이 모두 클리어 100%) 켜지지 않음.
// hold = 화면 «자동 추천» 길(recoArrangeKick)에서 끝날 때까지 카드·수치를 규칙 자리로 둠(arrangeOf) — 끝나는 순간 한 번에 미끄러져 바뀜(slide).
const RECHECK={key:'',p:0,state:'',stage:'',got:0,all:0,teams:0,rows:[],hold:false,forced:false,deep:false,endAt:0,outcome:'',slide:false,view:''};
function recheckNote(key,p,info,{hold=false,forced=false}={}){
  if(info.stage==='enter'){
    recheckTimerClear();
    if(RECHECK.state!=='work'||RECHECK.key!==key||RECHECK.p!==p)Object.assign(RECHECK,{key,p,state:'work',got:0,all:0,hold,forced,deep:false,endAt:0,outcome:'',slide:false,view:''});
    Object.assign(RECHECK,{stage:'enter',teams:info.teams||RECHECK.teams,rows:info.rows||RECHECK.rows});
  }else{if(RECHECK.state!=='work'||RECHECK.key!==key)return;
    Object.assign(RECHECK,{stage:info.stage,got:info.got||0,all:info.all||0});if(info.stage==='final200'||info.deep)RECHECK.deep=true;}
  if(typeof recheckPaint==='function')recheckPaint();
}
// 끝: 화면을 다시 그리는 것은 부른 쪽(run) — 여기서 그리면 카드 미끄러짐이 두 번 그려져 끊김. state '' = 조용히 치움(조건 변경·건너뛰기)
const recheckTimerClear=()=>{if(typeof recheckLane==='function'&&recheckLane.timer){clearTimeout(recheckLane.timer);recheckLane.timer=0;}};   // 끝 장면 타이머(party_template.html)
function recheckEnd(key,state,outcome=''){
  if(RECHECK.state!=='work'||RECHECK.key!==key)return;
  recheckTimerClear();
  if(!state){RECHECK.state='';RECHECK.hold=false;return;}
  Object.assign(RECHECK,{state,outcome,endAt:Date.now(),slide:state==='done'&&outcome==='changed'&&RECHECK.hold,hold:false});
}
const recheckHold=ident=>RECHECK.hold&&RECHECK.state==='work'&&RECHECK.key===ident;
function recheckOutcome(key,box){return box.rows.some(t=>arrGet(key,UiShared.teamKey(t.keys))?.changed)?'changed':'same';}
// 비교 대상(재조사에 들어갈 팀 수): recoArrange 의 건너뛰기 조건과 같음(이미 비교했거나 규칙 자리 본선이 목표·클리어 100%)
function recoArrangeNeed(snapshot,box){
  return box.rows.filter(t=>{const now=snapshot.result(t);return !arrGet(snapshot.key,UiShared.teamKey(t.keys))&&!(now&&goalVal(now)>=1&&now.clear>=1);}).map(t=>UiShared.teamKey(t.keys));
}
// «지금 자리로 확정»: 비교를 멈추고 규칙 자리로 끝냄(recoArrangeKick 의 catch 가 남은 팀을 규칙 자리로 기록)
function recheckConfirm(){
  const task=RECO.task;if(!task||task.done||task.owner!=='reco-arrange')return false;
  task.confirm=true;task.cancelled=true;task.abort?.();task.stop?.();simPoolDrop(task.owner);return true;
}
function recoMeta(snapshot,key,r){
  const meta=JSON.parse(JSON.stringify(snapshot.meta));meta.parts[7].engine=r.ver;meta.condition=JSON.stringify(meta.parts);meta.recommendationKey=snapshot.key;(SIMQ.meta??={})[key]=meta;
}
// ── 자리·리더 비교(11/23): 본선이 끝난 «보이는 팀»마다 전열 6조합 × 리더 4명 = 24가지를 짧게 거르고(RECO_ARR_SCREEN 판)
// 상위 RECO_ARR_KEEP 개 + 규칙 자리를 RECO_ARR_FINAL 판(같은 시드)으로 다시 비교한다. 규칙 자리보다 여유폭 이상 좋을 때만 바꾼다
// (PartyPlacement.race + recoDecide — 흐름·판정은 party_placement.js 한 곳). 결과는 RECO_ARR(party_template.html)에 저장 → arrangeOf·simParty·카드·직접 편집이 같은 자리를 쓴다.
// 비교 판 결과는 표시 캐시(SIMQ.res)에 넣지 않는다 — 표시는 바뀐 자리로 표준 본선(SIMQ.n판·표준 시드)을 다시 돌린 값.
// 근거: 11/23 실측(추천 8팀 × 24가지 × 300판) — 규칙 자리는 7팀에서 1등·운 범위, 45-36 두 팀만 리더 +10.3·전열 +3.1.
// PartyPlacement 가 없는 곳(일부 단위 시험의 가짜 화면)에서는 건너뛴다. 화면은 항상 party_placement.js 를 싣는다.
// 결선 2단계(RECO_ARR_CHECK 판에서 바꿀 근거가 없으면 끝, 아니면 같은 시드로 RECO_ARR_FINAL 판까지 이어 돌림 — 예선과 같은 run_offset·merge_raw 이어 붙이기)
const RECO_ARR_SCREEN=20,RECO_ARR_KEEP=3,RECO_ARR_CHECK=100,RECO_ARR_FINAL=200,RECO_ARR_SEED=7001;
async function recoArrange(snapshot,task,box,notify=()=>{}){
  if(typeof PartyPlacement==='undefined')return;
  const P=PartyPlacement,groups=[];
  for(const t of box.rows){
    const keys=t.keys.slice(),tk=UiShared.teamKey(keys);if(arrGet(snapshot.key,tk))continue;
    const rule=arrangeOf(t.combo,true),brk=snapshot.breakFor(t),now=snapshot.result(t);
    // 규칙 자리 본선이 이미 목표·클리어 100% 면 어떤 자리도 여유폭을 넘을 수 없다(recoBetter) → 비교 없이 유지
    if(now&&goalVal(now)>=1&&now.clear>=1){arrSet(snapshot.key,tk,{order:rule.order,lead:rule.lead,changed:false,skip:true});continue;}
    const job=(p,extra={})=>({key:P.executionKey(keys,p),p,...extra,
      party:snapshot.partyAt(t,{order:DirectParty.toScreen(p.order),lead:p.leaderKey}),options:{break_skill:brk}});
    groups.push({tk,rule,jobs:P.all(keys).map(p=>job(p)),incumbent:job({order:DirectParty.toEngine(rule.order),leaderKey:rule.lead},{rule:true})});
  }
  if(!groups.length)return;
  if(task.cancelled||snapshot.key!==recoIdentity())throw Error('취소');
  notify({stage:'enter',teams:groups.length,rows:groups.map(g=>g.tk)});
  // 팀들을 단계마다 한 번에 돌린다(PartyPlacement.raceMany): 예선 24×팀 수, 결선 (상위 3 + 규칙 자리)×팀 수
  const label=`자리·리더 비교 · ${groups.length}팀`;
  // 비교 판은 판별 난수(rng_streams)로 돌려 이어 붙이기가 «한 번에 돌린 것»과 같게 한다. 1단계 결선은 raw 를 받아 2단계가 이어 쓴다.
  // n 은 판별 값 길이로 다시 적는다(recoEvaluate 는 이번에 돌린 판 수를 적음 — 이어 붙인 결과는 합친 판 수가 맞음)
  // 현장 재조사 표시(RECHECK): 단계 = 예선(screen, 24가지 훑기) → 결선 1단계(check100) → 2단계(final200, 이어 돌림) → 판정(fix). 끝난 조합 수를 같이 알림
  const run=(jobs,n,seed,prior)=>{const res={},stage=n===RECO_ARR_SCREEN?'screen':prior?'final200':'check100';let got=0;
    notify({stage,got,all:jobs.length,teams:groups.length});
    return recoEvaluate(snapshot,task,jobs.map(j=>({...j,runs:n,seed:snapshot.seed+seed,
      options:{...j.options,rng_streams:true,...(prior?{run_offset:prior[j.key].progs.length,merge_raw:prior[j.key].raw}:n===RECO_ARR_CHECK?{raw_runs:true}:{})}})),n,
    {label,onTeam(j,r){res[j.key]={...r,n:r.progs?.length||r.n};notify({stage,got:++got,all:jobs.length,teams:groups.length});}}).then(()=>res);};
  const out=await P.raceMany({groups,run,compare:P.recoCompare,valid:r=>Number.isFinite(r?.clear),
    runs:RECO_ARR_FINAL,screenRuns:RECO_ARR_SCREEN,keep:RECO_ARR_KEEP,seed:RECO_ARR_SEED,decide:P.recoDecide,checkRuns:RECO_ARR_CHECK,stop:P.recoStop});
  if(task.cancelled||snapshot.key!==recoIdentity())throw Error('취소');
  groups.forEach((g,i)=>{const {pick,results}=out[i],rule=g.rule;
    arrSet(snapshot.key,g.tk,pick.rule?{order:rule.order,lead:rule.lead,changed:false}:
      {order:DirectParty.toScreen(pick.p.order),lead:pick.p.leaderKey,changed:true,rule:{order:rule.order,lead:rule.lead},why:{rule:results[g.incumbent.key],pick:results[pick.key]}});});
  notify({stage:'fix',got:0,all:0,teams:groups.length,deep:out.some(o=>!o.stopped)});
}
// 바꾼 자리를 표준 본선(SIMQ.n판·표준 시드)으로 다시 잰 값이 규칙 자리의 표준 본선보다 낮으면(목표 지표, 같으면 클리어율) 규칙 자리로 되돌린다.
// 비교 판과 표준 본선은 시드가 달라 운으로 뒤집힐 수 있다 — 화면에 «바꿨더니 더 낮은» 수치를 내지 않기 위함. 되돌린 수 반환.
function recoArrangeRevert(ident,rows,result,ruleResult){
  let n=0;if(typeof RECO_ARR==='undefined'||!RECO_ARR.size)return 0;   // 비교 기록이 없으면 되돌릴 것도 없음
  for(const t of rows){const k=UiShared.teamKey(t.keys),v=arrGet(ident,k);if(!v?.changed)continue;
    const a=result(t),b=ruleResult(t);if(!a||!b)continue;
    if(goalVal(a)<goalVal(b)||(goalVal(a)===goalVal(b)&&a.clear<b.clear)){
      arrSet(ident,k,{order:v.rule.order,lead:v.rule.lead,changed:false,reverted:{order:v.order,lead:v.lead,shown:a,rule:b}});n++;}}
  return n;
}
// 화면 「자동 추천」 길(simAutoKick → simStart)도 같은 recoArrange 를 쓴다. 보이는 팀이 모두 본선 결과를 가진 뒤 부르며,
// 끝나면 run() 으로 자동 확인을 다시 돌려 바뀐 자리의 표준 본선을 잰다. 취소가 아닌 오류면 남은 팀을 규칙 자리로 기록해 무한 재시도를 막는다.
function recoArrangeKick(p){
  const box=LASTQ[p];if(!box||typeof PartyPlacement==='undefined')return false;
  const snapshot=recoSnapshot(),task={key:snapshot.key,owner:'reco-arrange',request:0,cancelled:false,done:false,message:'자리·리더 비교 준비 중'};
  const need=recoArrangeNeed(snapshot,box),opt={hold:true,forced:!!SIMQ.scr[snapshot.screenKey(p)]?.full};
  // 결과 판을 그대로 둔 채 재조사 칸·사무실 장면으로 들어감(진행 칸으로 바꾸지 않음 — simWaiting)
  if(need.length)recheckNote(snapshot.key,p,{stage:'enter',teams:need.length,rows:need},opt);
  RECO.task=task;SIMQ.busy=p;SIMQ.msg=task.message;run(true);
  task.promise=(async()=>{try{
    task.engine=(await directManifest(task)).ver;
    if(task.cancelled||snapshot.key!==recoIdentity())throw Error('취소');
    await recoArrange(snapshot,task,box,info=>{recheckNote(snapshot.key,p,info,opt);const el=document.querySelector(`.party[data-party="${p}"] [data-k="simstate"]`);if(el)el.textContent=task.message;});
    await recoArrangeMeasure(snapshot,task,box);
    recheckEnd(snapshot.key,'done',recheckOutcome(snapshot.key,box));
  }catch(e){
    // 오류·«지금 자리로 확정»이면 아직 안 정한 팀과 바꾼 팀(표준 본선을 이미 쟀어도 되돌림 판정 전)을 모두 규칙 자리로 기록 —
    // 칸의 «규칙 자리 유지»와 카드가 맞고, 무한 재시도도 막음
    if((task.confirm||!task.cancelled)&&snapshot.key===recoIdentity())for(const t of box.rows){const k=UiShared.teamKey(t.keys),v=arrGet(snapshot.key,k);
      if(!v||v.changed){const r=arrangeOf(t.combo,true);arrSet(snapshot.key,k,{order:r.order,lead:r.lead,changed:false,...(task.confirm?{confirm:true}:{error:e.message})});}}
    recheckEnd(snapshot.key,task.confirm?'cancel':task.cancelled?'':'error');
  }finally{task.done=true;if(RECO.task===task){SIMQ.busy=null;SIMQ.msg='';run();}}})();
  return true;
}
// 바꾼 팀은 표준 본선(SIMQ.n판·표준 시드)으로 다시 잰 뒤 되돌림(recoArrangeRevert)까지 같은 작업 안에서 끝냄 — 재조사 칸이 판정까지 «진행 중»이고,
// 화면 카드는 그동안 규칙 자리(hold)라 «바꿨다가 되돌림»이 화면에 움직임으로 나오지 않음(카드 이동은 되돌림 판정 뒤에만)
async function recoArrangeMeasure(snapshot,task,box){
  const now=t=>{const v=arrGet(snapshot.key,UiShared.teamKey(t.keys));return v?.changed?v:null;};
  const jobs=box.rows.filter(t=>now(t)&&!SIMQ.res[snapshot.sigAt(t,now(t))]).map(t=>({key:snapshot.sigAt(t,now(t)),party:snapshot.partyAt(t,now(t)),options:{break_skill:snapshot.breakFor(t)}}));
  if(jobs.length)await recoEvaluate(snapshot,task,jobs,snapshot.n,{label:'재조사 판정',onTeam(j,r){SIMQ.res[j.key]=r;recoMeta(snapshot,j.key,r);}});
  if(task.cancelled||snapshot.key!==recoIdentity())throw Error('취소');
  recoArrangeRevert(snapshot.key,box.rows,t=>now(t)&&SIMQ.res[snapshot.sigAt(t,now(t))],t=>SIMQ.res[snapshot.sigRule(t)]);
}
async function recoCalculate(snapshot,task){
  return RecommendPipeline.recommendation({parties:snapshot.c.parties||1,screened:(snapshot.c.parties||1)===1,
    arrange:(p,box)=>{if(typeof PartyPlacement==='undefined')return;const need=recoArrangeNeed(snapshot,box),opt={forced:!!SIMQ.scr[snapshot.screenKey(p)]?.full};
      if(need.length)recheckNote(snapshot.key,p,{stage:'enter',teams:need.length,rows:need},opt);
      return recoArrange(snapshot,task,box,info=>recheckNote(snapshot.key,p,info,opt));},
    live:()=>!task.cancelled&&snapshot.key===recoIdentity(),plan:snapshot.plan,screenState:p=>SIMQ.scr[snapshot.screenKey(p)],
    screen:(p,box)=>recoScreenCalculate(snapshot,task,p,box),more:snapshot.more,result:snapshot.result,goal:goalVal,first:snapshot.first,
    async final(p,box){
      SIMQ.busy=p;SIMQ.screening=false;task.message='본선 준비 중';
      const jobs=box.rows.filter(t=>!snapshot.result(t)).map(t=>({key:snapshot.sig(t),party:snapshot.party(t),options:{break_skill:snapshot.breakFor(t)}}));
      await recoEvaluate(snapshot,task,jobs,snapshot.n,{onTeam(j,r){
        SIMQ.res[j.key]=r;recoMeta(snapshot,j.key,r);
      }});
      recoArrangeRevert(snapshot.key,box.rows,snapshot.result,t=>SIMQ.res[snapshot.sigRule(t)]);
      if(RECHECK.state==='work')recheckEnd(snapshot.key,'done',recheckOutcome(snapshot.key,box));   // 재조사가 켜져 있었으면(묶음 길) 판정 뒤 끝
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
  }finally{recheckEnd(snapshot.key,task.cancelled?'':'error');   // 끝나지 않은 재조사만(끝난 것은 그대로)
    task.done=true;if(RECO.task===task){SIMQ.busy=null;SIMQ.screening=false;run(true);}}})();
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
      job:(t,k)=>({id:k,t,party:snapshot.partyRule(t),options:{break_skill:snapshot.breakFor(t)},breakName:snapshot.breakFor(t)?.name||null}),
      seed:snapshot.seed,n:snapshot.n,state,owner:task.owner,nextRequest:()=>++task.request,version:task.engine,options:snapshot.options,
      paint(){task.message=state.msg;task.progress=state.progress;GROW.msg=state.msg;GROW.errors=state.errors;growthPaint();directResultsPaint();}});
    if(!live()||signature!==growthSig(c,st))throw Error('입력이 바뀜');
    GROW.result={...result,baseline,snapshot:grown,kind:c.key,ms:Date.now()-started,baselineFirst:true,condition:directConditions(c,st),
      signature:JSON.stringify(['grown-account',MyInfoReco.OVERWRITE_VERSION,grown.preset,GROW.sig])};GROW.phase='done';return GROW.result;
  }catch(e){if(GROW.id===id){GROW.phase='error';GROW.msg='미완료';GROW.errors.push(e.message);}throw e;
  }finally{task.done=true;if(RECO.task===task){SIMQ.busy=null;GROW.stop=null;growthPaint();directResultsPaint();}}})();return task.promise;
}
