// Page transport for the pure placement candidates; shares the physical worker pool.
let placementSerial=0;
function placementCompare(a,b){return b.cosmo&&a.cosmo?PlacementSearch.cmp(typeof CSR==='undefined'?'top':CSR.optMode||'top')(a,b):
  (b.t60??b.clear)-(a.t60??a.clear)||b.clear-a.clear||(b.prog||0)-(a.prog||0)||(a.ttk??Infinity)-(b.ttk??Infinity);}
function placementRun({party,stage,options,brk,owner='placement',live=()=>true,onProgress=()=>{},register=()=>{},runs=8}){
  const id='placement-'+(++placementSerial),keys=party.units.map(u=>u.key),jobs=PartyPlacement.all(keys).map(p=>({key:PartyPlacement.executionKey(keys,p),p,party:PartyPlacement.reorder(party,p)}));
  return new Promise((resolve,reject)=>{
    const ws=scrPool(2),res={};let ended=false;
    const finish=error=>{if(ended)return;ended=true;clearInterval(watch);if(error){simPoolDrop(owner,id);reject(Error(error));}else{
      try{resolve(PartyPlacement.best(jobs,res,placementCompare,r=>Number.isFinite(r?.clear))[0]);}catch(e){reject(e);}
    }};
    const watch=setInterval(()=>{if(!live())finish('입력이 바뀌어 배치 비교를 중단함');},200);
    register(()=>finish('배치 비교를 취소함'));
    const arm=simWatch(ws,()=>simTeamLimit(runs),()=>!ended&&live(),()=>finish('배치 비교 시간 초과'));
    simDispatch(ws,jobs,{owner,id,live:()=>!ended&&live(),arm,
      msg:j=>({type:'run',base:new URL('.',location.href).href,stage,n_runs:runs,seed:77123,options,
        teams:[{key:j.key,party:j.party,options:{break_skill:brk}}]}),
      team(j,m){res[j.key]=m.result;onProgress(Object.keys(res).length,jobs.length);},done:()=>finish(),error:finish});
  });
}
// Content/tab/stage edits invalidate a running comparison even if the user switches back (ABA).
function placementCancelInput(){if(typeof DIRECT!=='undefined')DIRECT.placement?.cancel?.();if(typeof CDIRECT!=='undefined')CDIRECT.placement?.cancel?.();}
async function directArrangeSim(){
  if(DIRECT.placement){DIRECT.placement.cancel?.();return;}
  const c=contents[$('content').value],st=cur?.[$('stage').value];
  if(!st||!DirectParty.validate(DIRECT.draft,directContext()).ok)return;
  const input=directInputKey(),state={};DIRECT.placement=state;
  const live=()=>DIRECT.placement===state&&directInputKey()===input;
  state.cancel=()=>{if(DIRECT.placement===state)DIRECT.placement=null;paint();};
  const paint=()=>{$('direct-arrange').textContent=DIRECT.placement?`배치 비교 ${DIRECT.placement.done||0}/24 · 취소`:'자리 자동 배치';};paint();
  try{
    const values=directValues();
    if(!values||values.errors?.length||MI.error||DIRECT.error)throw Error('계정 능력치 자료를 확인한 뒤 다시 배치 필요');
    const party=DirectParty.serialize(DIRECT.draft,values.profile?.results||{});
    const auto=pickBreak(DIRECT.draft.slots.map(m=>({s:BYKEY[m.key]})),c.name,ownedSimBreaks().map(b=>b.name));
    const brk=DIRECT.draft.brk==='auto'?(auto?{name:auto[1],level:brkLv(auto[1])}:null):DIRECT.draft.brk;
    const winner=await placementRun({party,stage:c.key+'/'+st.tab+'/'+st.name,options:simOpt(c.key),brk,owner:'placement-direct',
      live,register:f=>{state.cancel=()=>{if(DIRECT.placement===state)DIRECT.placement=null;f();paint();};},onProgress:d=>{state.done=d;paint();}});
    if(live()){DIRECT.placement=null;directChange({type:'arrange',order:winner.p.order,leaderKey:winner.p.leaderKey},{record:true});}
  }catch(e){if(DIRECT.placement===state){DIRECT.runError=e.message;directResultsPaint();}}finally{if(DIRECT.placement===state)DIRECT.placement=null;paint();}
}
async function cdArrangeSim(boss){
  if(CDIRECT.placement){CDIRECT.placement.cancel?.();return;}
  cdSync();const job=CDIRECT.jobs?.[boss];if(!job)return;
  const input=cdInput(),state={boss};CDIRECT.placement=state;
  const live=()=>CDIRECT.placement===state&&cdInput()===input;
  state.cancel=()=>{if(CDIRECT.placement===state)CDIRECT.placement=null;paint();};
  const paint=()=>{const b=$('cosmo-direct-panel').querySelector('[data-cd-act="arrange"]');if(b)b.textContent=CDIRECT.placement?`배치 비교 ${CDIRECT.placement.done||0}/24 · 취소`:'자리 자동 배치';};paint();
  try{
    const winner=await placementRun({party:job.party,stage:job.stage,options:job.options,brk:job.options.break_skill,owner:'placement-cosmo',
      live,register:f=>{state.cancel=()=>{if(CDIRECT.placement===state)CDIRECT.placement=null;f();paint();};},onProgress:d=>{state.done=d;paint();}});
    if(live()){CDIRECT.placement=null;cdChange({type:'draft',boss,action:{type:'arrange',order:winner.p.order,leaderKey:winner.p.leaderKey}},{record:true});}
  }catch(e){if(CDIRECT.placement===state){CDIRECT.error=e.message;cdPaint();}}finally{if(CDIRECT.placement===state)CDIRECT.placement=null;paint();}
}
