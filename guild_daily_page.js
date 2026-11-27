// Page adapter for the opt-in daily preset. No new persistent selection/result keys.
function guildDailyOptions(){return {S:{...D.guild.search,banCoop:GSR.banCoop},G:D.guild,V:GuildView,
  nowMs:Date.now(),
  roster:R.filter(s=>!EXCL.has(s.key)),tiers:gsTiers(),breaks:ownedSimBreaks()};}
function guildDailySig(){return JSON.stringify(['daily',guildIdentity(),GuildView.gameDay(D.guild).date,MI.hash,[...EXCL].sort(),
  gsTiers(),GSR.banCoop,ownedSimBreaks(),D.guild.search,growthOptions()]);}
function guildDailyPreview(){
  if(!MI.info||!MI.growth)return null;
  const profile=MI.profiles.op||(MI.profiles.op=MyInfoReco.profile(MI.info,R,MI.growth,'op'));
  const cx={...guildDailyOptions(),results:profile.results};
  // Budget the optional second pass too, before its detailed profile is loaded.
  if(growthEnabled())cx.growthResults=profile.results;
  const sig=JSON.stringify([guildDailySig(),cx.roster,profile.results,!!cx.growthResults]);
  if(guildDailyPreview.cached?.sig===sig)return guildDailyPreview.cached.plan;
  const plan=GuildDaily.plan(cx);guildDailyPreview.cached={sig,plan};return plan;
}
function guildDailySummary(st,gwen=''){
  const teams=st.teams||[],names=GuildDailyUI.teamNames(teams);
  const bosses=teams.map((t,i)=>({key:'t'+i,name:names[i],short:names[i],label:names[i]}));
  const state={active:'t0',teams:Object.fromEntries(teams.map((t,i)=>['t'+i,{level:0,draft:GuildDailyUI.draft(t)}]))};
  const summary={total:st.sum,done:teams.length,teams:Object.fromEntries(teams.map((t,i)=>['t'+i,
    {status:'done',score:t.score,clear:t.clear,mode:'top',other:t.mean,levelText:GuildDailyUI.levelText(t),brk:t.brk?{name:t.brk,level:t.brkLv}:null}]))};
  return CosmoDirectUI.summaryHtml({state,season:{bosses,levelMax:0},roster:R,summary},
    {gwen,sumKey:'gs-score',tabsKey:'gs-team-summary',totalLabel:`${teams.length}팀 합계`});
}
function guildDailyHtml(){return GuildDailyUI.html(GSR,{G:D.guild,esc,hasInfo:!!MI.info,sig:guildDailySig(),plan:guildDailyPreview(),
  cards:(t,snapshot)=>seasonTeam(t,false,snapshot),summary:st=>guildDailySummary(st,GwenStage.slot('guildSearch','result')),
  work:()=>GwenStage.slot('guildSearch','board'),report:()=>GwenStage.slot('guildSearch','board'),error:Ux.gwenError});}
function guildDailyRelease(target=GSR){target.session?.close();target.session=null;}
function guildDailyInput(){
  if(GSR.session&&GSR.phase!=='run'&&GSR.sig!==guildDailySig())guildDailyRelease();
}
async function guildDailyStart(target=GSR,profileOverride=null,follow=false){
  if(seasonBlocked('guild')||!MI.info||target.phase==='run'||SIMQ.busy!=null||CSR.phase==='run')return;
  if(follow&&(target.phase!=='done'||target.sig!==guildDailySig()||!target.teams?.length||target.seals.remaining<1))return;
  const previous=follow?{...target}:null;
  if(!follow)target.session?.reset();
  target.session ||= GuildDaily.createSession(()=>SearchExecutor.createWorker(),()=>{
    if(typeof simPoolTrimIdle==='function')simPoolTrimIdle();
    if(typeof CSR!=='undefined'&&CSR.phase!=='run'&&!CSR.session?.active&&typeof csSessionRelease==='function')csSessionRelease();
  });
  const session=target.session;
  growthCancel();guildGwenClaim('guildSearch');
  const id=++target.id,stale=()=>target.id!==id,paint=()=>renderGuildSearch(true),sig=guildDailySig(),cx=guildDailyOptions();
  const tick=SearchExecutor.throttle(paint,SearchExecutor.PAINT_MS,()=>!stale()&&target.phase==='run');
  Object.assign(target,{phase:'run',msg:'내 구원자 능력치 계산 중',done:0,total:0,rows:previous?.rows||[],teams:previous?.teams||[],growth:previous?.growth||null,following:follow,followError:null,plan:previous?.plan||null,eta:null,partial:false,coverage:null,stopRequested:false,stageIndex:null,sig});paint();
  try{
    const growth=await miGrowth();if(stale())return;
    const profile=profileOverride||MI.profiles.op||(MI.profiles.op=MyInfoReco.profile(MI.info,R,growth,'op'));
    let growthResults=null,growthSnapshot=null;
    if(growthEnabled()&&!profileOverride){
      const slots=await fetch('data/myinfo_slots.json').then(r=>{if(!r.ok)throw Error('장비 부위 확인 실패');return r.json();});if(stale())return;
      growthSnapshot=MyInfoReco.overwrite(MI.info,R,growth,'op',{excluded:[...EXCL],slots,priority:D.journeyPriority});
      growthResults=growthSnapshot.profile.results;
    }
    // Revalidate on every click: guild data can stay identical across engine deployments.
    const response=await fetch('sim/manifest.json',{cache:'no-cache'});
    if(!response.ok)throw Error('계산 엔진 버전 확인 실패');
    const manifest=await response.json();if(stale())return;
    if(typeof manifest.ver!=='string'||!manifest.ver)throw Error('계산 엔진 버전 확인 실패');
    if(target.stopRequested){if(previous)Object.assign(target,previous,{id,following:false,handle:null});else{target.phase='idle';guildDailyRelease(target);}paint();return;}
    if(typeof CSR!=='undefined'&&CSR.phase!=='run'&&!CSR.session?.active&&typeof csSessionRelease==='function')csSessionRelease();
    if(typeof simPoolTrimIdle==='function')simPoolTrimIdle();
    const out=await GuildPlanner.search({...cx,session,previous,engineVersion:manifest.ver,results:profile.results,growthResults,progressEta:false,cosmoSpeed:LS.get("cosmo.speed.v2"),
      base:location.href.replace(/[?#].*$/,'').replace(/[^/]*$/,''),stage:'guild',
      env:{cores:navigator.hardwareConcurrency,memGB:navigator.deviceMemory,mobile:csMobile()},makeWorker:()=>SearchExecutor.createWorker(),stale,partialRequested:()=>target.stopRequested,
      watch:{hidden:()=>document.hidden,limit:r=>simTeamLimit(r),loadMs:()=>SIMQ.LOAD_MS||180000},
      onPlan:pl=>{if(stale())return;target.plan=pl;target.eta=pl.eta||null;},
      onHandle:h=>{if(stale()||target.stopRequested){h.cancel();return;}target.handle=h;},
      onPhase:(msg,total,meta)=>{if(stale())return;target.phaseSerial=(target.phaseSerial||0)+1;Object.assign(target,{msg,done:0,total,stageIndex:meta.stage,runs:meta.runs});paint();},
      onProgress:(done,total)=>{if(stale())return;Object.assign(target,{done,total});tick();}});
    if(stale())return;tick.cancel();
    if(out.growth)out.growth.snapshot=growthSnapshot||previous?.growth?.snapshot;
    Object.assign(target,out,{sig,eta:null,handle:null,following:false,phase:out.rows.length?'done':'idle'});
    if(!out.rows.length)guildDailyRelease(target);paint();return target;
  }catch(e){if(stale())return;if(previous){Object.assign(target,previous,{id,following:false,handle:null,followError:e.message||String(e)});paint();return;}guildDailyRelease(target);target.handle=null;target.errorCause=e.gwenCause||'other';target.phase=e.gwenCause==='cancel'?'idle':'err';target.msg=e.message||String(e);paint();}
  finally{tick.cancel();if(stale()){session.close();if(target.session===session)target.session=null;}}
}
function guildDailyFromSearch(index,grown=false){
  const source=grown?GSR.growth:GSR,t=source?.teams?.[index];if(!t)return;
  if(!contents[$('content').value].stages.some(s=>parseInt(s.name,10)===t.step))return;
  if(!cur.some(s=>parseInt(s.name,10)===t.step)){$('q').value='';refreshStages();}
  const stageIndex=cur.findIndex(s=>parseInt(s.name,10)===t.step);
  DIRECT.placement?.cancel?.();directCancel();
  $('stage').value=String(stageIndex);
  GS.sel=GuildView.normSel(D.guild,{level:t.level,tiers:t.tiers,support:t.sup});LS.set(guildStoreKey(),GS.sel);
  DIRECT.undo=DIRECT.draft;DIRECT.draft=DirectParty.draft(GuildDailyUI.draft(t,grown));DIRECT.revision++;
  DIRECT.guildSearchSource={team:index+1,season:D.guild.season.id,date:t.date||source.plan.day.date,flags:GuildDailyUI.flags(t),partial:!!t.evaluation?.partial,signature:t.signature};
  directSave();saveSel();showInfo();showPow();condChanged();directNavigate('direct');guildDailySourcePaint();
}
function guildDailySourcePaint(){
  let el=$('direct-guild-source');const source=DIRECT.guildSearchSource,on=contents[$('content').value]?.key==='guild'&&source?.season===D.guild.season.id;
  if(!on){if(el)el.hidden=true;return;}
  if(!el){el=document.createElement('p');el.id='direct-guild-source';$('direct-panel').prepend(el);}
  const changed=source.date!==GuildView.gameDay(D.guild).date;
  el.className=source.partial||changed?'gd-warn':'gd-small';
  el.hidden=false;el.textContent=[`오늘 편성 찾기 ${source.team}팀에서 가져옴`,source.partial?'중단한 결과':'',changed?'날짜 바뀜 · '+source.date+' 출정 기준':''].filter(Boolean).join(' · ');
}
function guildDailyDateTick(){
  if(D.guild?.search?.preset!=='daily'||contents[$('content').value]?.key!=='guild')return;
  const day=GuildView.gameDay(D.guild).date;
  if(guildDailyDateTick.day==null)guildDailyDateTick.day=GSR.plan?.day.date||day;
  if(guildDailyDateTick.day===day)return;guildDailyDateTick.day=day;
  guildDailyInput();if(GSR.phase!=='run')renderGuildSearch(true);
  else{const host=$('guild-search'),el=host.querySelector('[data-k="gs-day"]');if(el)el.textContent='날짜 바뀜 · 진행 중인 찾기는 시작한 출정 날짜 기준임.';}
  guildDailySourcePaint();
}
