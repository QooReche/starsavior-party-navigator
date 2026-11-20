// Draft edits and immediate power. Execution snapshots live in direct_run.js.
const DIRECT={mode:'home',draft:null,shared:false,selected:null,undo:null,revision:0,slots:null,loading:null,error:'',valueKey:null,values:null};
function directInit(){
  Object.assign(DIRECT,DirectParty.restore(LS.get('direct.v1'),SHARE.dp));
  DIRECT.mode=SHARE.pm||((SHARE.dp||SHARE.cd)?'direct':(SHARE.c||AUTO||/[#&]shared=/.test(location.hash))?'reco':'home');
  history.replaceState({...history.state,pnMode:DIRECT.mode},'',location.href);
  directDragInit();directBundleInit();
  document.addEventListener('click',e=>{
    if(e.target.closest('#start-screen [data-miopen]')){setDrawer(true);return;}
    const mode=e.target.closest('[data-pn-mode]');if(mode){directNavigate(mode.dataset.pnMode,mode);return;}
    const choice=e.target.closest('[data-pn-choice]');
    if(choice&&!e.target.closest('button,input,label,a,summary,details')){directNavigate(choice.dataset.pnChoice,choice);return;}
    const b=e.target.closest('[data-direct-action]');if(!b||b.disabled)return;
    const a=b.dataset.directAction,i=Number(b.dataset.slot);
    if(a==='compare-toggle'){const panel=$(b.getAttribute('aria-controls')),open=b.getAttribute('aria-expanded')!=='true';b.setAttribute('aria-expanded',String(open));panel.hidden=!open;return;}
    if(a==='run'){directRun();return;}
    if(a==='run-row'){directRun(b.dataset.kind);return;}
    if(a==='skip'){directBundleSkip(b.dataset.kind);return;}
    if(a==='view-reco'){directNavigate('reco');run(true);return;}
    if(a==='view-growth'){directNavigate('reco');run(true);$('result-tab-growth')?.click();return;}
    if(a==='recommend'){directNavigate('reco');return;}
    if(a==='deselect'){const i=DIRECT.selected;DIRECT.selected=null;directPaint();$('direct-board').querySelector(`[data-direct-action=slot][data-slot="${i}"]`)?.focus();return;}
    if(a==='unowned'){const status=b.closest('[data-direct-picker]').querySelector('[data-direct-pick-status]')||$('direct-state');status.textContent='보유하지 않음 · 고를 수 없음';return;}
    if(a==='slot'){
      const swapping=DIRECT.selected!==null&&DIRECT.selected!==i;
      if(swapping){directChange({type:'swap',a:DIRECT.selected,b:i});DIRECT.selected=null;}
      else DIRECT.selected=DIRECT.selected===i?null:i;
      directPaint();if(!swapping)GwenLane.edit('focus',i);
      if(!DIRECT.draft.slots[i]&&DIRECT.selected===i&&innerWidth<=760){$('direct-picker-dialog').showModal();$('direct-picker-dialog').querySelector('input').focus();}return;
    }
    if(a==='pick'){
      directChange({type:'put',key:b.dataset.key,slot:DIRECT.selected});DIRECT.selected=null;directPaint();return;
    }
    if(a==='remove')directChange({type:'remove',slot:i});
    if(a==='leader')directChange({type:'leader',key:b.dataset.key});
    if(a==='grown')directChange({type:'grown',slot:i,value:!DIRECT.draft.slots[i].grown});
    if(a==='clear'){DIRECT.selected=null;directChange({type:'clear'});}
    if(a==='undo'&&DIRECT.undo){const d=DIRECT.undo;DIRECT.undo=null;DIRECT.draft=d;DIRECT.revision++;directSave();directPaint();GwenLane.edit('undo');}
    if(a==='arrange')directArrangeSim();
    if(a==='open'){$('direct-picker-dialog').showModal();$('direct-picker-dialog').querySelector('input').focus();}
    if(a==='close')$('direct-picker-dialog').close();
    if(a==='retry'){DIRECT.error='';DIRECT.valueKey=null;directRefresh();}
  });
  document.addEventListener('change',e=>{
    if(e.target.matches('[data-direct-unowned]')){DIRECT.showUnowned=e.target.checked;document.querySelectorAll('[data-direct-unowned]').forEach(x=>x.checked=e.target.checked);document.querySelectorAll('[data-direct-picker]').forEach(h=>directList(h,h.querySelector('[data-direct-search]').value));}
    if(e.target.id==='direct-break')directChange({type:'brk',value:e.target.value==='auto'?'auto':e.target.value===''?null:{name:e.target.value,level:brkLv(e.target.value)}});
  });
  document.querySelectorAll('[data-direct-search]').forEach(input=>input.addEventListener('input',()=>directList(input.closest('[data-direct-picker]'),input.value)));
  window.addEventListener('popstate',()=>{DIRECT.mode=new URLSearchParams(location.search).get('pm')||'home';directRefresh();});
  directRefresh();
}
function directNavigate(mode,source){
  if(!['home','reco','direct'].includes(mode))return;
  const before=source?.closest('.start-choice')?.getBoundingClientRect();
  if(mode==='home'&&history.state?.pnModeEntry){history.back();return;}
  const wasHome=DIRECT.mode==='home',u=new URL(location.href);u.searchParams.set('pm',mode);
  // A received draft remains session-only even after edits. Remove it from navigation URLs
  // only on returning home; copying a link explicitly emits the current allowlisted draft.
  if(mode==='home'){u.searchParams.delete('dp');u.searchParams.delete('cd');u.searchParams.delete('auto');}
  const state={...history.state,pnMode:mode,pnModeEntry:mode==='home'?false:(wasHome||!!history.state?.pnModeEntry)};
  history[wasHome&&mode!=='home'?'pushState':'replaceState'](state,'',u);
  DIRECT.mode=mode;directRefresh();
  const target=$(mode==='direct'?(contents[$('content').value]?.key==='cosmo'?'cosmo-direct-panel':'direct-panel'):mode==='reco'?'out':'start-screen');
  if(before&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
    const after=target.getBoundingClientRect();if(after.width&&after.height)target.animate([
      {transformOrigin:'top left',transform:`translate(${before.x-after.x}px,${before.y-after.y}px) scale(${before.width/after.width},${before.height/after.height})`,opacity:.6},
      {transformOrigin:'top left',transform:'none',opacity:1}],{duration:250,easing:'ease-out'});
  }
}
function directVisibility(){
  if(!DIRECT.draft)return;
  const info=!$('mi-panel').hidden,cosmo=contents[$('content').value]?.key==='cosmo';
  $('start-screen').hidden=info||DIRECT.mode!=='home';$('direct-panel').hidden=info||DIRECT.mode!=='direct'||cosmo;
  const cdPanel=$('cosmo-direct-panel'),cdWasHidden=cdPanel.hidden;
  cdPanel.hidden=info||DIRECT.mode!=='direct'||!cosmo;
  // A hidden editor is emptied by late callbacks (cdPaint); repaint it when it becomes visible again.
  if(cdWasHidden&&!cdPanel.hidden&&typeof cdPaint==='function')cdPaint();
  if(cosmo&&$('direct-picker-dialog').open)$('direct-picker-dialog').close();
  $('mode-strip').hidden=info||DIRECT.mode==='home';$('out').hidden=info||DIRECT.mode!=='reco';
  document.body.dataset.partyMode=DIRECT.mode;
  for(const b of $('mode-strip').querySelectorAll('[data-pn-mode]'))b.setAttribute('aria-pressed',String(b.dataset.pnMode===DIRECT.mode));
  if($('result-tabs'))$('result-tabs').hidden=info||DIRECT.mode!=='reco';
  GwenLane.activate(info?null:DIRECT.mode==='direct'&&cosmo?'cdirect':DIRECT.mode);
  recoGwenVisibility();growthControlPlace();
}
function directHome(){
  const home=$('start-screen'),stamp=String(!!MI.info);
  if(home.dataset.account===stamp)return;
  // Move the one live growth control out before replacing its temporary home.
  $('growth-control-home').append($('growth-control'));
  home.dataset.account=stamp;
  home.innerHTML=`<div class="start-choice start-reco" data-pn-choice="reco"><p class="case-tag">그웬에게 맡기기</p><h2>자동 추천</h2>
    <p>내 구원자로 스테이지를 깰 편성을 찾음.</p><button type="button" data-pn-mode="reco">자동 추천</button>
    ${!MI.info?'<div class="case-request"><h3>사건 의뢰서 · 접수 대기</h3><p>내 정보를 불러오면 내 구원자에 맞춰 추천함.</p><button type="button" class="sec" data-miopen="1">계정 정보 불러오기</button><p class="mut">정보 없이도 표준 육성으로 추천 가능</p></div>':''}<div id="start-growth"></div></div>
    <div class="start-gwen"><div id="home-gwen-lane" class="gwen-lane" aria-label="그웬 길"></div><p>단장님, 어떤 방법으로 골라 볼까?<br>후후후, 나만 믿어!</p></div>
    <div class="start-choice start-direct" data-pn-choice="direct"><p class="case-tag">내가 고르기</p><h2>직접 편성</h2><p>구원자와 자리, 리더를 직접 고름.</p><button type="button" data-pn-mode="direct">직접 편성</button><p class="mut">${MI.info?'내 구원자 기준':'내 정보 없이도 표준 육성 기준으로 가능'} · 편성만 직접 고름</p></div>`;
  GwenLane.registerStage('home',{board:document.getElementById('home-gwen-lane')});
}
function directSave(){const payload=DirectParty.storage(DIRECT);if(payload&&!LS.set('direct.v1',payload))DIRECT.error='초안 저장 실패 · 이 세션에서만 유지됨';}
function directChange(action){
  DIRECT.placement?.cancel?.();
  const next=DirectParty.edit(DIRECT.draft,action);if(JSON.stringify(next)===JSON.stringify(DIRECT.draft))return;
  const changedSlot=action.type==='put'?next.slots.findIndex((s,i)=>s?.key!==DIRECT.draft.slots[i]?.key):action.slot;
  DIRECT.undo=DIRECT.draft;DIRECT.draft=next;DIRECT.revision++;directSave();directPaint();GwenLane.edit(action.type,changedSlot);
}
function directContext(){const c=contents[$('content').value],st=cur?.[$('stage').value];return {roster:R,info:MI.info,content:c.key,restrict:(CFG.restrict[c.name]||{})[st?.tab]};}
function directPaintInput(){const c=contents[$('content').value],st=cur?.[$('stage').value];return JSON.stringify([DIRECT.draft,MI.hash,!!MI.growth,!!DIRECT.slots,!!QK.d,DIRECT.error,c.key,st?.tab,st?.name,rkOf(c.key),starOf(c.key),ownedSimBreaks()]);}
function directRefresh(){
  if(!DIRECT.draft)return;
  directSync();
  // A reserved auto/share recommendation has not started yet. Switching away
  // must not launch it later; already running jobs/results remain untouched.
  if(DIRECT.mode!=='reco'&&RECO.timer){recoClearTimer();RECO.sharedPending=false;}
  directHome();directVisibility();cdRefresh();
  if(DIRECT.mode==='direct'&&contents[$('content').value]?.key!=='cosmo'){
    if(!DIRECT.slots&&!DIRECT.loading&&!DIRECT.error){
      DIRECT.loading=Promise.all([MI.info?miGrowth():Promise.resolve(),fetch('data/myinfo_slots.json').then(r=>{if(!r.ok)throw Error('장비 부위 자료 오류');return r.json();})])
        .then(([,slots])=>{DIRECT.slots=slots;}).catch(e=>{DIRECT.error=e.message;}).finally(()=>{DIRECT.loading=null;directPaint();});
    }
    // Recommendation progress/result callbacks may call run() in the background.
    // Keep the editor's live controls intact unless its own inputs changed.
    if(DIRECT.paintInput!==directPaintInput())directPaint();
  }
  directResultsPaint();
}
function directValues(){
  const context=directContext(),cache=JSON.stringify([DIRECT.draft,context.content,MI.hash,!!MI.growth,!!DIRECT.slots,!!QK.d]);
  if(cache===DIRECT.valueKey)return DIRECT.values;
  if(MI.info&&(!MI.growth||!DIRECT.slots))return null;
  const standard=Object.fromEntries(R.map(s=>{const u=QK.d?.sv[s.key];return [s.key,u?{power:Math.floor(u[5]*Quick.MUL+.5),stats:{atk:u[1],hp:u[2],def:u[3],spd:u[4]}}:null];}));
  DIRECT.values=DirectParty.powers(DIRECT.draft,{...context,growth:MI.growth,slots:DIRECT.slots,priority:D.journeyPriority,standard});DIRECT.valueKey=cache;return DIRECT.values;
}
function directList(host,query=''){
  const ctx=directContext(),owned=new Set(MI.info?.units.map(u=>u.id)),keys=new Set(DIRECT.draft.slots.filter(Boolean).map(s=>s.key));
  host.querySelector('[data-direct-list]').innerHTML=R.filter(s=>(!MI.info||DIRECT.showUnowned||owned.has(s.uid))&&s.name.toLowerCase().includes(query.toLowerCase())).map(s=>{
    const reason=MI.info&&!owned.has(s.uid)?'미보유':ctx.restrict&&s.el!==ctx.restrict?'속성 제한':keys.has(s.key)?'편성됨':'';
    return `<button type="button" class="sec direct-candidate${reason==='미보유'?' direct-unowned':''}" data-direct-action="${reason==='미보유'?'unowned':'pick'}" data-key="${esc(s.key)}" ${reason&&reason!=='미보유'?'disabled':''}><img src="${esc(s.img)}" alt="" loading="lazy"><span>${esc(s.name)}<small>${esc(reason||EL[s.el]+' · '+s.cls)}</small></span></button>`;
  }).join('');
}
function directPaint(){
  if(!DIRECT.draft)return;
  if(DIRECT.drag){DIRECT.paintDeferred=true;return;}
  const focus=document.activeElement,focusId=focus?.id,action=focus?.dataset.directAction,slot=focus?.dataset.slot,key=focus?.dataset.key,picker=focus?.closest('[data-direct-picker]');
  const ctx=directContext(),check=DirectParty.validate(DIRECT.draft,ctx);let values=null;
  try{values=directValues();}catch(e){DIRECT.error=e.message;}
  const power=r=>r?(r.power>=1000?(r.power/1000).toFixed(1)+'k':miNum(r.power)):'—',labels=['전열1','전열2','후열1','후열2'];
  $('direct-board').innerHTML=DirectParty.toScreen([0,1,2,3]).map(i=>{
    const m=DIRECT.draft.slots[i],s=m&&BYKEY[m.key],v=values?.values[i],old=values?.before[i];
    const leader=!!m&&DIRECT.draft.leader===m.key,linked=values?.linked?.includes(m?.key);
    const changes=(values?.changes[m?.key]?.changedFields||[]).filter(f=>f!=='level').map(f=>({equip:'장비',skills:'스킬',resonance:'공명',journey:'기록',potentials:'잠재력',favor:'호감도'}[f]||f));
    if(linked)changes.unshift('스타링크 등록 가정 포함');
    return `<section class="direct-slot${DIRECT.selected===i?' selected':''}${leader?' direct-leader':''}" data-pos="${i<2?'front':'back'}" data-direct-slot="${i}">
      <div class="direct-card-wrap"><button type="button" class="direct-member sec${!s?' direct-vacant':''}" data-direct-action="slot" data-slot="${i}" aria-pressed="${DIRECT.selected===i}" aria-label="${labels[i]} ${esc(s?.name||'빈 칸')} 선택">
      ${s?`<span class="fallback">${esc(s.name[0])}</span>${art(s)}<span class="direct-name" title="${esc(s.name)}">${dia(s,20)}<span>${esc(s.name)}</span></span>`:'<span class="direct-empty">＋</span><span class="direct-name">구원자 넣기</span>'}
      <b class="direct-position">${labels[i]}</b></button>
      ${m?`<button type="button" class="sec direct-leader-toggle" data-direct-action="leader" data-key="${esc(m.key)}" aria-label="${labels[i]} 리더 지정" aria-pressed="${leader}"><span aria-hidden="true">${leader?'★':'☆'}</span>${leader?`<span class="crown" aria-hidden="true">${CROWN}<span>리더</span></span>`:''}</button>`:''}
      <div class="direct-slot-tools"><button type="button" class="sec" data-direct-action="remove" data-slot="${i}" ${!m?'disabled':''} aria-label="${labels[i]} 빼기">✕</button></div></div>
      <button type="button" class="sec direct-grow" data-direct-action="grown" data-slot="${i}" aria-pressed="${!!m?.grown}" ${!MI.info?'title="내 정보 필요"':''} ${!m||!MI.info||!values?'disabled':''}><b class="direct-power" data-direct-power="${i}">${v&&old&&v.power!==old.power?power(old)+'→':''}${power(v)}</b><span>${m?.grown?'☑':'☐'} 육성했다면</span></button>
      ${values?.prelink?.[m?.key]?`<small class="direct-level-note" data-direct-level-note>${esc(values.prelink[m.key].text)}</small>`:''}
      ${values?.levelUnknown?.includes(m?.key)?'<small class="direct-level-note" data-direct-level-note>레벨 확인 불가 · 다시 불러오기 필요 · 레벨 가정 없음</small>':''}
      ${m?`<details class="direct-stats"><summary aria-label="${labels[i]} 능력치·육성 상세">ⓘ <span>상세</span></summary>${v?['atk','hp','def','spd'].map((k,j)=>`<div>${['공','생','방','속'][j]} ${miNum(v.stats[k]||0)}</div>`).join(''):''}<p>${values?.prelink?.[m.key]?`적용 Lv.${values.prelink[m.key].target}${values.prelink[m.key].aboveCap?` · 현재 레벨이 돌파 상한 Lv.${values.prelink[m.key].cap}보다 높아 유지(자료 불일치)`:''} · `:''}${m.grown?'추천 육성과 같은 기준 · '+esc(changes.join(' · ')||'이미 목표 충족'):'현재 상태'}</p></details>`:''}
      ${check.errors.filter(e=>e.slot===i).map(e=>`<small class="direct-invalid">${esc(e.message)}</small>`).join('')}</section>`;
  }).join('');
  $('direct-total').textContent=values?miNum(values.total):'—';$('direct-summary-power').textContent=$('direct-total').textContent;
  $('direct-state').textContent=[check.ok?'편성 중 · 4/4명':check.errors.filter(e=>e.slot==null).map(e=>e.message).join(' · '),!MI.info?'내 정보 없음 · 표준 육성 기준':'내 구원자 기준',DIRECT.shared?'공유받은 초안 · 로컬 저장 안 함':'',...(values?.warnings||[]).filter(w=>w!=='내 정보 없음 · 표준 육성 기준'),...values?.errors.map(e=>e.reason)||[],DIRECT.error||(!values?'전투력 자료를 불러오는 중':'')].filter(Boolean).join(' · ');
  $('direct-retry').hidden=!DIRECT.error;$('direct-undo').disabled=!DIRECT.undo;$('direct-arrange').disabled=DIRECT.draft.slots.filter(Boolean).length!==4;
  const chosenMember=DIRECT.selected==null?null:DIRECT.draft.slots[DIRECT.selected];
  $('direct-selection').hidden=!chosenMember;
  $('direct-selection').innerHTML=chosenMember?`<small>고른 칸: ${labels[DIRECT.selected]} ${esc(BYKEY[chosenMember.key]?.name||'')}</small><div><button type="button" class="sec" data-direct-action="leader" data-key="${chosenMember.key}">★ 리더로</button><button type="button" class="sec" data-direct-action="remove" data-slot="${DIRECT.selected}">✕ 빼기</button><button type="button" class="sec" data-direct-action="deselect">선택 취소</button></div>`:'';
  $('direct-conditions').textContent=`오토 100판 · ${contents[$('content').value].title||contents[$('content').value].name} · ${cur?.[$('stage').value]?.label||cur?.[$('stage').value]?.name||'스테이지 미선택'}${contents[$('content').value].parties>1?' · 파티 1만':''}${rkOf(ctx.content)?' · 재점화 '+rkOf(ctx.content):''}${starOf(ctx.content)?' · '+starOf(ctx.content)+'턴 3별 목표':''}`;
  const brks=ownedSimBreaks(),chosen=DIRECT.draft.brk?.name;
  $('direct-break').innerHTML='<option value="auto">자동 선택</option><option value="">없음</option>'+brks.map(b=>`<option value="${esc(b.name)}">${esc(b.name)} Lv.${b.level}</option>`).join('')+(chosen&&!brks.some(b=>b.name===chosen)?`<option value="${esc(chosen)}" disabled>${esc(chosen)} · 미보유/지원 안 함</option>`:'');
  $('direct-break').value=DIRECT.draft.brk==='auto'?'auto':chosen||'';
  document.querySelectorAll('[data-direct-picker]').forEach(host=>directList(host,host.querySelector('input').value));
  if(focusId)$(focusId)?.focus({preventScroll:true});
  else if(action&&slot!=null)$('direct-board').querySelector(`[data-direct-action="${action}"][data-slot="${slot}"]`)?.focus({preventScroll:true});
  else if(action==='leader'&&key)$('direct-board').querySelector(`[data-direct-action="leader"][data-key="${key}"]`)?.focus({preventScroll:true});
  else if(picker)(picker.querySelector('[data-direct-action="pick"]:enabled')||picker.querySelector('input')).focus({preventScroll:true});
  DIRECT.paintInput=directPaintInput();
  directResultsPaint();
}
