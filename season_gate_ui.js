const SEASON_KEYS=['guild','cosmo','clash'];
function seasonData(key){return key==='guild'?D.guild?.season:key==='cosmo'?D.cosmoRaid?.seasonPeriod:key==='clash'?D.contents.find(c=>c.key==='clash')?.seasonPeriod:null;}
function seasonStatus(key){return SEASON_KEYS.includes(key)?SeasonGate.state(seasonData(key),Date.now(),location.search):{blocked:false,label:'',message:''};}
function seasonBlocked(key){return seasonStatus(key).blocked;}
function seasonPaint(){
  const key=contents[$('content').value]?.key,state=seasonStatus(key),s=seasonData(key);
  for(const [i,c] of contents.entries()){
    const label=seasonStatus(c.key).label;
    $('content').options[i].textContent=(c.title||c.name)+(label?' ['+label+']':'');
  }
  const badge=$('season-chip'),note=$('season-note');
  badge.hidden=!state.label;badge.textContent=state.label;
  badge.title=s?`${s.name||s.label||('시즌 '+(key==='cosmo'?D.cosmoRaid.season%1000:s.id))} · 종료 ${s.end||'기간 미확인'}`:'';
  note.hidden=!state.message;note.textContent=state.message;
}
function seasonApplyPanel(panel,key){
  const blocked=seasonBlocked(key);panel.classList.toggle('season-closed',blocked);
  if(!blocked)return;
  panel.querySelectorAll('button[data-gs="start"],button[data-cs="start"],button[data-go]').forEach(b=>b.disabled=true);
}
let seasonLastState=null;
function seasonRefresh(){
  const key=contents[$('content').value]?.key,tag=JSON.stringify(SEASON_KEYS.map(seasonStatus));
  if(seasonLastState===null){seasonLastState=tag;seasonPaint();return;}
  if(tag===seasonLastState)return;
  seasonLastState=tag;
  seasonPaint();
  if(seasonBlocked(key)){
    // simInvalidate -> growthCancel -> GROW.stop also cancels the copied seasonal growth search.
    simInvalidate();REQ=false;SIMQ.kick=false;
    for(const target of [GSR,CSR]){target.id++;target.handle?.cancel();target.handle=null;target.phase='idle';}
  }
  renderGuild();renderCosmoSearch();run();
}
