// Page adapter for the opt-in daily preset. No new persistent selection/result keys.
function guildDailyOptions(){return {S:{...D.guild.search,banCoop:GSR.banCoop},G:D.guild,V:GuildView,
  seals:GSR.sealCount??D.guild.search.daily.seals.default,split:GSR.splitChoice||undefined,nowMs:Date.now(),
  roster:R.filter(s=>!EXCL.has(s.key)),tiers:gsTiers(),breaks:ownedSimBreaks()};}
function guildDailySig(){return JSON.stringify(['daily',guildIdentity(),GuildView.gameDay(D.guild).date,MI.hash,[...EXCL].sort(),
  GSR.sealCount??D.guild.search.daily.seals.default,GSR.splitChoice||null,gsTiers(),GSR.banCoop,ownedSimBreaks(),D.guild.search,growthOptions()]);}
function guildDailyPreview(){
  if(!MI.info||!MI.growth)return null;
  const profile=MI.profiles.op||(MI.profiles.op=MyInfoReco.profile(MI.info,R,MI.growth,'op'));
  const cx={...guildDailyOptions(),results:profile.results};
  // Budget the optional second pass too, before its detailed profile is loaded.
  if(growthEnabled())cx.growthResults=profile.results;
  return GuildDaily.plan(cx);
}
function guildDailyCards(t){
  const before=LEADKEY;LEADKEY=t.leaderKey||t.order[0];
  try{return `<div class="rowcards gs-compact cs-cards">${[2,0,1,3].map((ix,i)=>card({s:BYKEY[t.order[ix]]},i===0||i===3?'back':'front')).join('')}</div>`;}finally{LEADKEY=before;}
}
function guildDailyHtml(){return GuildDailyUI.html(GSR,{G:D.guild,esc,hasInfo:!!MI.info,sig:guildDailySig(),plan:guildDailyPreview(),
  cards:guildDailyCards,breakBar:t=>seasonBreakBar(t,true),label:k=>BYKEY[k]?.name||k,say:Ux.gwenSay,
  work:()=>GwenStage.slot('guildSearch','board'),report:()=>GwenStage.slot('guildSearch','board')+GwenStage.slot('guildSearch','result'),error:Ux.gwenError});}
function guildDailyInput(){
  const day=GuildView.gameDay(D.guild),choices=GuildDaily.splits(D.guild.search.daily,GSR.sealCount??D.guild.search.daily.seals.default,day.exOpen);
  if(GSR.splitChoice&&!choices.some(s=>s.ex===GSR.splitChoice.ex&&s.normal===GSR.splitChoice.normal))GSR.splitChoice=null;
}
async function guildDailyStart(target=GSR,profileOverride=null){
  if(seasonBlocked('guild')||!MI.info||target.phase==='run'||SIMQ.busy!=null||CSR.phase==='run')return;
  growthCancel();guildGwenClaim('guildSearch');guildDailyInput();
  const id=++target.id,stale=()=>target.id!==id,paint=()=>renderGuildSearch(true),sig=guildDailySig(),cx=guildDailyOptions();
  const tick=SearchExecutor.throttle(paint,SearchExecutor.PAINT_MS,()=>!stale()&&target.phase==='run');
  Object.assign(target,{phase:'run',msg:'내 구원자 능력치 계산 중',done:0,total:0,rows:[],teams:[],growth:null,plan:null,eta:null,partial:false,coverage:null,stopRequested:false,stageIndex:null,sig});paint();
  try{
    const growth=await miGrowth();if(stale())return;
    const profile=profileOverride||MI.profiles.op||(MI.profiles.op=MyInfoReco.profile(MI.info,R,growth,'op'));
    let growthResults=null;
    if(growthEnabled()&&!profileOverride){
      const slots=await fetch('data/myinfo_slots.json').then(r=>{if(!r.ok)throw Error('장비 부위 확인 실패');return r.json();});if(stale())return;
      growthResults=MyInfoReco.overwrite(MI.info,R,growth,'op',{excluded:[...EXCL],slots,priority:D.journeyPriority}).profile.results;
    }
    if(target.stopRequested){target.phase='idle';paint();return;}
    const out=await GuildPlanner.search({...cx,results:profile.results,growthResults,cosmoSpeed:LS.get("cosmo.speed.v2"),
      base:location.href.replace(/[?#].*$/,'').replace(/[^/]*$/,''),stage:'guild',
      env:{cores:navigator.hardwareConcurrency,memGB:navigator.deviceMemory,mobile:csMobile()},makeWorker:()=>SearchExecutor.createWorker(),stale,partialRequested:()=>target.stopRequested,
      watch:{hidden:()=>document.hidden,limit:r=>simTeamLimit(r),loadMs:()=>SIMQ.LOAD_MS||180000},
      onPlan:pl=>{if(stale())return;target.plan=pl;target.eta=pl.eta||null;},
      onHandle:h=>{if(stale()||target.stopRequested){h.cancel();return;}target.handle=h;},
      onPhase:(msg,total,meta)=>{if(stale())return;target.phaseSerial=(target.phaseSerial||0)+1;Object.assign(target,{msg,done:0,total,stageIndex:meta.stage,runs:meta.runs});paint();},
      onProgress:(done,total)=>{if(stale())return;Object.assign(target,{done,total});tick();}});
    if(stale())return;tick.cancel();
    Object.assign(target,out,{sig,eta:null,handle:null,phase:out.rows.length?'done':'idle'});paint();return target;
  }catch(e){if(stale())return;target.handle=null;target.errorCause=e.gwenCause||'other';target.phase=e.gwenCause==='cancel'?'idle':'err';target.msg=e.message||String(e);paint();}
  finally{tick.cancel();}
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
  DIRECT.guildSearchSource={season:D.guild.season.id,date:source.plan.day.date,flags:GuildDailyUI.flags(t),partial:source.partial};
  directSave();saveSel();showInfo();showPow();condChanged();directNavigate('direct');guildDailySourcePaint();
}
function guildDailySourcePaint(){
  let el=$('direct-guild-source');const source=DIRECT.guildSearchSource,on=contents[$('content').value]?.key==='guild'&&source?.season===D.guild.season.id;
  if(!on){if(el)el.hidden=true;return;}
  if(!el){el=document.createElement('p');el.id='direct-guild-source';$('direct-panel').prepend(el);}
  const changed=source.date!==GuildView.gameDay(D.guild).date;
  el.className=source.partial||source.flags.length||changed?'gd-warn':'gd-small';
  el.hidden=false;el.textContent=['오늘 편성 찾기에서 가져옴',source.partial?'부분 결과':'',...source.flags,changed?'날짜 바뀜 · '+source.date+' 출정 기준':''].filter(Boolean).join(' · ');
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
