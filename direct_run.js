// DIRECT execution owns snapshots/results only; physical workers belong to simDispatch.
Object.assign(DIRECT,{requestId:0,active:null,cache:new Map(),rows:{},versions:null,runError:'',compare:null});
const directCopy=x=>JSON.parse(JSON.stringify(x));
function directInputKey(){const c=contents[$('content').value],st=cur?.[$('stage').value];
  return JSON.stringify([DIRECT.draft,MI.hash,MI.error,c.key,st?.tab,st?.name,simOpt(c.key),SIMQ.seed,SIMQ.n,ownedSimBreaks(),MI.growth?.assumed?.version]);}
function directConditions(c,st,versions=DIRECT.versions){return JSON.stringify([c.key,st.tab,st.name,MI.hash||null,simOpt(c.key),SIMQ.seed,SIMQ.n,versions,MyInfoReco.OVERWRITE_VERSION]);}
function directRecoMeta(c,st,runs){const versions={engine:null,data:MyInfoReco.hash([D,QK.d,MI.growth])};return {parts:JSON.parse(directConditions(c,st,versions)),seed:SIMQ.seed,runs};}
function directSnapshots(){
  const ctx=directContext(),c=contents[$('content').value],st=cur?.[$('stage').value],values=directValues();
  if(!st||!values||!DIRECT.versions||!DirectParty.validate(DIRECT.draft,ctx).ok||MI.error||DIRECT.error||values.errors.length)return {};
  const draft=DirectParty.draft(DIRECT.draft),account=directCopy(MI.info),original=account?MyInfoReco.profile(account,R,MI.growth,c.key):null;
  const combo=draft.slots.map(m=>({s:BYKEY[m.key]}));
  const automatic=pickBreak(combo,c.name,ownedSimBreaks().map(b=>b.name));
  const brk=draft.brk==='auto'?(automatic?{name:automatic[1],level:brkLv(automatic[1])}:null):draft.brk;
  if(brk&&!ownedSimBreaks().some(b=>b.name===brk.name&&b.level===brk.level))return {};
  const common={stage:c.key+'/'+st.tab+'/'+st.name,brk:directCopy(brk),seed:SIMQ.seed,runs:SIMQ.n,options:directCopy(simOpt(c.key)),
    versions:{...DIRECT.versions,account:MI.hash||null,policy:MyInfoReco.OVERWRITE_VERSION,preset:MI.growth?.assumed?.version||'standard'},
    condition:directConditions(c,st),draft,account,content:directCopy(c),stageInfo:directCopy(st),revision:DIRECT.revision};
  const make=(kind,profile)=>{const snap={...common,kind,profile:directCopy(profile),party:DirectParty.serialize(draft,profile?.results||{})};
    snap.sig=DirectParty.signature(snap);return directCopy(snap);};
  const out={now:make('now',original)};
  if(draft.starLink||draft.slots.some(m=>m.grown))out.grown=make('grown',values.profile);
  return out;
}
function directCancel(message='중단함'){
  const active=DIRECT.active;if(!active)return;
  DIRECT.active=null;DIRECT.requestId++;
  active.abort?.();
  simPoolDrop('direct',active.id);
  for(const row of Object.values(DIRECT.rows))if(['waiting','running'].includes(row.status)){row.status='cancelled';row.error=message;}
  directResultsPaint();
}
function directSync(){
  const key=directInputKey();
  if(DIRECT.inputKey!==key){const changed=DIRECT.inputKey!=null;DIRECT.inputKey=key;DIRECT.expectedKey=null;DIRECT.runError='';if(changed){DIRECT.revision++;directCancel('입력이 바뀜');}}
  const expectedKey=JSON.stringify([key,DIRECT.versions,!!MI.growth,!!DIRECT.slots,!!QK.d,DIRECT.error]);
  if(DIRECT.expectedKey===expectedKey)return;
  DIRECT.expectedKey=expectedKey;
  let snaps={};try{snaps=directSnapshots();}catch(e){DIRECT.runError=e.message;}
  DIRECT.expected=snaps;
  for(const kind of ['now','grown']){
    const snap=snaps[kind],cached=snap&&DIRECT.cache.get(snap.sig),row=DIRECT.rows[kind];
    if(row&&!row.result&&row.sig!==snap?.sig)delete DIRECT.rows[kind];
    if(cached&&(!row||row.sig!==snap.sig||!['waiting','running','error'].includes(row.status)))DIRECT.rows[kind]={...cached,snapshot:snap,status:'done'};
  }
}
async function directManifest(active){
  const controller=new AbortController();let timer,timedOut=false;
  const arm=()=>{const due=Date.now()+SIMQ.LOAD_MS;timer=setTimeout(()=>{
    if(document.hidden||Date.now()-due>5000){arm();return;}
    timedOut=true;controller.abort();
  },SIMQ.LOAD_MS);};
  active.abort=()=>{clearTimeout(timer);controller.abort();};arm();
  try{const response=await fetch('sim/manifest.json',{cache:'no-cache',signal:controller.signal});if(!response.ok)throw Error('계산 엔진 자료 오류');return await response.json();}
  catch(e){if(timedOut)throw Error('계산 엔진 준비 시간 초과');throw e;}
  finally{clearTimeout(timer);delete active.abort;}
}
async function directRun(only=null){
  if(DIRECT.active){directCancel();return;}
  directSync();
  let values=null;try{values=directValues();}catch(e){DIRECT.error=e.message;}
  if(MI.error||DIRECT.error||!DirectParty.validate(DIRECT.draft,directContext()).ok||!values||values.errors.length)return;
  const input=directInputKey(),id=++DIRECT.requestId;
  DIRECT.active={id,revision:DIRECT.revision};DIRECT.runError='';directResultsPaint();
  try{
    const manifest=await directManifest(DIRECT.active);
    if(DIRECT.requestId!==id||input!==directInputKey())return;
    DIRECT.versions={engine:manifest.ver,data:MyInfoReco.hash([D,QK.d,MI.growth])};
    directSync();const snaps=DIRECT.expected;
    if(!snaps.now)throw Error('편성 또는 계산 자료 확인 필요');
    const jobs=[],seen=new Map();
    for(const [kind,snap] of Object.entries(snaps)){
      if(only&&kind!==only)continue;
      const cached=DIRECT.cache.get(snap.sig);
      if(cached){DIRECT.rows[kind]={...cached,snapshot:snap,status:'done'};continue;}
      const row={sig:snap.sig,snapshot:snap,status:'waiting',progress:0,result:null,error:''};DIRECT.rows[kind]=row;
      if(seen.has(snap.sig))seen.get(snap.sig).kinds.push(kind);else{const j={key:kind,snapshot:snap,kinds:[kind]};seen.set(snap.sig,j);jobs.push(j);}
    }
    if(!jobs.length){DIRECT.active=null;directResultsPaint();return;}
    // Each row has its own watchdog/error; one failed row cannot discard its sibling.
    let left=jobs.length;
    const live=()=>DIRECT.requestId===id&&DIRECT.active?.id===id&&input===directInputKey();
    const finish=()=>{if(--left===0&&live())DIRECT.active=null;directResultsPaint();};
    for(const job of jobs){
      const ws=scrPool(1),snap=job.snapshot;
      const fail=msg=>{if(!live())return;simPoolDrop('direct',id,job.key);for(const k of job.kinds){DIRECT.rows[k].status='error';DIRECT.rows[k].error=msg;}finish();};
      const arm=simWatch(ws,()=>simTeamLimit(snap.runs),live,ready=>fail(ready?'계산 시간 초과':'계산 엔진 준비 시간 초과'));
      simDispatch(ws,[job],{owner:'direct',id,revision:snap.revision,group:job.key,live,arm,
        msg:()=>({type:'run',base:new URL('.',location.href).href,stage:snap.stage,n_runs:snap.runs,seed:snap.seed,options:snap.options,progress:true,
          teams:[{key:job.key,party:snap.party,options:{break_skill:snap.brk}}]}),
        assigned(){for(const k of job.kinds)DIRECT.rows[k].status='running';directResultsPaint();},
        stage(w,m){for(const k of job.kinds){const row=DIRECT.rows[k];row.progress=m.completed??row.progress;row.message=m.msg;}directResultsPaint();},
        team(j,m){if(m.result.ver!==snap.versions.engine){fail('엔진 버전이 바뀜 · 다시 시도');return;}
          const entry={sig:snap.sig,snapshot:snap,result:directCopy(m.result),status:'done',progress:snap.runs};
          DIRECT.cache.set(snap.sig,entry);for(const k of job.kinds)DIRECT.rows[k]={...entry,snapshot:snaps[k]};},
        done:finish,error:fail});
    }
    directResultsPaint();
  }catch(e){if(DIRECT.requestId===id){DIRECT.active=null;DIRECT.runError='계산 실패 · 다시 시도: '+e.message;directResultsPaint();}}
}
// Only the completed first recommendation, never growthBaseline's selected alternative.
function directCollectRecommendation(){
  if(!DIRECT.draft||SIMQ.busy!=null||SIMQ.screening)return;
  const c=contents[$('content').value],st=cur?.[$('stage').value],rows=LASTQ[1]?.rows;
  if(!st||!rows?.length||!rows.every(t=>SIMQ.res[simSig(st,t)]))return;
  const first=rows[0],sig=simSig(st,first),result=SIMQ.res[sig],meta=SIMQ.meta?.[sig];
  if(!meta||meta.runs!==SIMQ.n||meta.seed!==SIMQ.seed)return;
  if(!DIRECT.versions&&meta.parts?.[7]){DIRECT.versions={...meta.parts[7]};DIRECT.expectedKey=null;directSync();}
  DIRECT.compare={result,sig,condition:meta.condition,metric:meta.parts?.[4]?.star_turns?'t60':'clear',power:result.power??first.q.power,label:'자동 추천 1안',source:'추천 탭 결과'};
}
function directDifference(result,baseline,metric){
  if(!result||!baseline||!Number.isFinite(result[metric])||!Number.isFinite(baseline[metric]))return '';
  const diff=GrowthGuide.compare({...result,clear:result[metric]},{...baseline,clear:baseline[metric]});
  return `${Math.abs(diff.delta)<5?'거의 같음 · ':''}${Ux.signed(Math.round(diff.delta*10)/10)}%p · 보수적 비교 범위 ${diff.ci.map(v=>Ux.signed(Math.round(v*10)/10)).join(' ~ ')}%p`;
}
function directResultsPaint(){
  if(!DIRECT.draft||!$('direct-results'))return;
  directSync();directCollectRecommendation();
  const expected=DIRECT.expected||{},now=DIRECT.rows.now,validNow=now?.sig===expected.now?.sig&&now?.status==='done',metric=expected.now?.options.star_turns?'t60':'clear';
  const past=(row,kind='now')=>!!row?.result&&row.sig!==expected[kind]?.sig;
  let values=null;try{values=directValues();}catch(e){DIRECT.error=e.message;}
  const runnable=!!DirectParty.validate(DIRECT.draft,directContext()).ok&&!MI.error&&!DIRECT.error&&!!values&&!values.errors.length;
  $('direct-run').disabled=!DIRECT.active&&!runnable;
  $('direct-run').textContent=DIRECT.active?'취소':now&&!validNow?'다시 실행':'모의 전투 실행';
  const error=MI.error?'내 정보 계산 자료를 불러오지 못했음 · '+MI.error+' · 평균 육성으로 대신 계산하지 않음. 네트워크를 확인한 뒤 다시 시도 필요.':DIRECT.runError;
  const activeRows=Object.values(DIRECT.rows),waiting=activeRows.some(r=>r.status==='waiting'),running=activeRows.find(r=>r.status==='running');
  $('direct-standard').hidden=!!MI.info;
  $('direct-run-state').textContent=[error,DIRECT.active?(waiting?'대기 중 · 진행 중인 추천 팀이 끝나면 우선 계산':running?`계산 중 · ${running.progress||0}/${running.snapshot.runs}판`:'실행 준비 중'):'',!MI.info?'내 정보 없음 · 표준 육성 기준':''].filter(Boolean).join(' · ');
  const summary=$('direct-result-summary');
  summary.dataset.state='done';
  summary.classList.toggle('direct-past',past(now));
  summary.innerHTML=`${past(now)?'<div class="direct-past-band">지난 결과 · 현재 편성과 다를 수 있음</div>':''}<div class="verdict-main"><b class="verdict-number"><small>클리어</small>${now?.result?Math.round(now.result.clear*100)+'%':'조사 대기'}</b>${now?.result?`<span class="tag">${Ux.verdict(now.result.clear)[1]}</span>`:''}</div><div class="verdict-stats"><div><b>${now?.result?.ta??now?.result?.ttk??'—'}</b><small>예상 턴</small></div><div><b id="direct-summary-power">${miNum(values?.total||0)}</b><small>편성 전투력</small></div></div>`;
  const entries=['now','grown'].filter(k=>expected[k]||DIRECT.rows[k]).map(k=>({kind:k,label:k==='now'?'내 편성·지금':'내 편성·육성 가정',row:DIRECT.rows[k],stale:past(DIRECT.rows[k],k)}));
  const c=contents[$('content').value],st=cur?.[$('stage').value],reco=DIRECT.compare,compatible=!!reco&&!!st&&reco.condition===directConditions(c,st);
  entries.push({kind:'reco',label:'자동 추천 1안',row:reco?{...reco,status:'done'}:null,stale:!!reco&&!compatible});
  $('direct-results').innerHTML=`<table class="direct-comparison"><caption>${metric==='t60'?'60턴 내 클리어(3별)':'클리어'} 비교 ${Ux.help('보수적 비교 범위','각 결과의 Wilson 95% 구간 끝점을 빼서 구한 보수적 범위임. 짝지은 차이의 신뢰구간이 아님. 점 추정 차이가 5%p 미만이면 거의 같음으로 표시함.')}</caption><thead><tr><th scope="col">편성</th><th scope="col">결과</th></tr></thead><tbody>${entries.map(({kind,label,row,stale})=>{
    const r=row?.result,working=['waiting','running'].includes(row?.status),state=working?(row.status==='waiting'?'대기 중 · 먼저 실행한 팀이 끝나면 계산':`계산 중 · ${row.progress||0}/${row.snapshot.runs}판`):row?.status==='error'?`계산 실패 · 다시 시도`:row?.status==='cancelled'?row.error:r?'계산 완료':'미계산';
    const diff=r&&!stale&&validNow&&kind!=='now'?directDifference(r,now.result,metric):'';
    const rowMetric=stale?(row.snapshot?(row.snapshot.options.star_turns?'t60':'clear'):row.metric):metric;
    return `<tr data-direct-row="${kind}" class="${stale?'direct-past':''}"><th scope="row">${label}${stale?'<span class="direct-past-band">지난 결과</span>':''}${kind==='reco'&&r?'<small>추천 탭 결과</small>':''}</th><td><span role="status">${state}</span>${r?`<b>${rowMetric==='t60'?'60턴 내 ':''}${Math.round((r[rowMetric]??r.clear)*100)}%</b><small>클리어 ${Math.round(r.clear*100)}% · ${r.ta??r.ttk??'—'}턴 · 전투력 ${miNum(r.power??row.power??0)}</small>`:''}${diff?`<small>${esc(diff)}</small>`:''}${row?.status==='error'?`<button type="button" class="sec" data-direct-action="run-row" data-kind="${kind}" ${DIRECT.active?'disabled':''}>다시 시도</button>`:''}</td></tr>`;
  }).join('')}</tbody></table>`;
  $('direct-recommend').hidden=compatible;
  const gwenError=!!error||activeRows.some(r=>r.status==='error');
  const phase=gwenError?'error':DIRECT.active?'work':validNow?'result':'idle';
  $('direct-progress-lane').hidden=phase!=='work';$('direct-progress').hidden=phase!=='work';
  const memberCount=DIRECT.draft.slots.filter(Boolean).length;
  $('direct-result-lane').hidden=!(['result','error'].includes(phase)||phase==='idle'&&memberCount>0&&memberCount<4);
  $('direct-progress').value=running?.progress||0;
  GwenLane.sync({mode:DIRECT.mode,phase,result:validNow?GwenLane.resultId(now.result):null,clear:now?.result?.clear,
    progress:running?.progress>0?running.progress/running.snapshot.runs:null,count:DIRECT.draft.slots.filter(Boolean).length,
    stale:past(now),better:compatible&&validNow&&now.result[metric]>reco.result[metric]});

  const detail=$('direct-detail'),detailKey=JSON.stringify(entries.slice(0,-1).map(e=>[e.row?.result?e.row.sig:null,e.stale]));
  if(detail.dataset.key!==detailKey){detail.dataset.key=detailKey;detail.innerHTML=entries.filter(e=>e.kind!=='reco'&&e.row?.result).map(({label,row,stale})=>{
    const snap=row.snapshot,r=row.result;
    return `<details class="${stale?'direct-past':''}"><summary>${label} 상세${stale?' · 지난 결과':''}</summary><p>브레이크 스킬: ${esc(r.bs?.name||snap.brk?.name||'없음')}${snap.brk?' Lv.'+snap.brk.level:''}</p><div class="rowcards">${DirectParty.toScreen([0,1,2,3]).map(i=>{const key=snap.draft.slots[i].key;return card({s:BYKEY[key]},i<2?'front':'back',r,null,{leader:snap.draft.leader,final:snap.profile?.results[key]||null});}).join('')}</div></details>`;
  }).join('');}
}
