// Daily presentation. The planner owns dates, feasible splits and all result values.
(function(root){
  'use strict';
  const node=typeof module!=='undefined'&&module.exports;
  const U=node?require('./ui_shared'):root.UiShared,V=node?require('./guild_view'):root.GuildView;
  const Recheck=node?require('./recheck_ui'):root.RecheckUi,Result=U.seasonUi;
  const GS=node?require('./guild_search'):root.GuildSearch;
  const splitText=s=>[s.ex?`EX ${s.ex}팀`:'',s.normal?`일반 ${s.normal}팀`:''].filter(Boolean).join(' + ')||'팀 없음';
  function chips(G,t){
    const support=G.supports.find(s=>String(s.id)===String(t.sup)),role=G.search.supportRole?.[t.sup];
    const scope=t.effectiveSupport==='none'?'해당 직업 없음':role?role+' 한정':'파티 전체';
    return Result.chip(U.esc(t.kind==='ex'?`★ 별의 도전 ${t.level}`:`스테이지 ${t.step}단계`))+
      Result.chip(t.sup==='none'?'지원 없음':`알리시아 지원 · ${U.esc(support?.name||t.sup)} · ${U.esc(scope)}`);
  }
  function flags(t){
    const e=t.evaluation;
    return [...(e&&!e.stageSupportComplete?['스테이지·지원 미평가']:[]),...(e&&!e.placementComplete?['자리·리더 미평가']:[])];
  }
  function draft(t,grown=false){return {v:1,slots:t.order.map(key=>({key,grown})),leader:t.leaderKey||t.order[0],brk:t.brk?{name:t.brk,level:t.brkLv}:null};}
  function sayKey(st,pl,day){
    if(st.following)return 'guildFollow';
    if(st.partial)return 'guildPartial';
    if(st.phase==='done')return st.warnings?.length?'guildShort':st.seals.remaining?'guildFollow':'guildDone';
    if(pl?.warnings.length)return 'guildShort';
    return day.exOpen?'guildPlan':'guildClosed';
  }
  function result(st,cx,grown=false){
    const {G,esc}=cx,teams=st.teams||st.rows||[],warn=xs=>(xs||[]).map(x=>Result.warning(esc(x))).join('');
    const blocks=teams.map((t,i)=>Result.team({title:`${i+1}팀`,attrs:`data-gs-team="${i}"`,chips:chips(G,t),
      score:`상위 점수 <b>${U.num(t.score)}</b> · 평균 점수 ${U.num(t.mean)} · 클리어율 ${U.pctText(t.clear)}`,
      body:GS.unsupportedHtml([t],esc)+(t.evaluation?.partial?Result.warning('중단 · 부분 결과'):'')+warn(flags(t))+
        cx.cards(t,grown?st.snapshot:null)+cx.breakBar(t)+placementResult(t)+
        Result.edit(`data-gs="edit" data-team="${i}" data-grown="${grown}"`)
    })).join('');
    const detail=`<div class="mut gd-small">인장 ${st.seals.used}장 사용 · ${splitText(st.split)} · 지원 겹침 없음<br>${esc(st.reason||'팀마다 평가한 후보 중 최고 점수를 골랐음.')}${teams.map((t,i)=>`<br>${i+1}팀: ${esc(t.kind==='ex'?`★ 별의 도전 ${t.level} · 추가 점수 +${V.extraPct(G,t.level,t.tiers||[])}%`:`스테이지 ${t.step}단계`)}`).join('')}</div>`;
    return `<div data-k="gs-daily-result">${Result.score(`${grown?'육성했다면 · ':''}${teams.length}팀 합산 점수`,U.num(st.sum),'gs-score','상위 점수 기준')}${st.partial?Result.warning('중단 · 부분 결과'):''}${warn(st.flags)}${warn(st.warnings)}${blocks}${Result.basis(grown?'gs-grown-detail':'gs-result-detail',detail,'탐색 결과 상세')}</div>`;
  }
  function placementResult(t){
    // 결과에 완료 여부와 실제 선택이 남아 있을 때만 유지/변경으로 표시함.
    if(!t.evaluation?.placementComplete||typeof t.placementChanged!=='boolean')return '';
    const changed=t.placementChanged;
    return Recheck.strip({state:'done',outcome:changed?'changed':'same',teams:1},{readonly:true,
      summary:changed?'자리·리더 비교 결과 적용':'지금 자리·리더 그대로',
      record:changed?'현장 재조사 기록: 후보를 대조해 선택한 자리·리더로 바꿈':'현장 재조사 기록: 후보를 대조했고 확실히 더 좋은 자리는 없었음'});
  }
  function html(st,cx){
    const {G,esc}=cx,pl=cx.plan,day=V.gameDay(G,cx.nowMs),sealConfig=G.search.daily.seals;
    const ex=day.exOpen,count=1;
    const dayline=`${day.day}요일 · EX ${day.exOpen?'열림':`닫힘${day.nextEx?' · 다음 EX는 '+day.nextEx+'요일':''}`}`;
    const stale=st.phase==='done'&&st.sig!==cx.sig?'<div class="gd-warn" data-k="gd-search-stale">계산 조건이 바뀌었음. 아래 결과는 이전 선택 기준이므로 다시 찾기 필요.</div>':'';
    const changed=st.plan?.day.date&&st.plan.day.date!==day.date?'<div class="gd-warn" data-k="gs-date-changed">날짜 바뀜 · 아래 편성은 출정 날짜 '+esc(st.plan.day.date)+' 기준임. 오늘 조건으로 다시 찾기 필요.</div>':'';
    let body='';
    if(st.phase==='run')body=`${cx.work()}${U.planHtml('길드 오늘 편성 찾기 전체 진행')}<p data-k="gd-search-prog"></p><ol class="gd-small" data-k="gs-stages"></ol><button type="button" class="sec" data-gs="partial">중단</button>`;
    else if(st.phase==='done')body=`${stale}${cx.report()}${result(st,cx)}${st.growth?`<details class="season-options" data-fold="gs-grown"><summary>육성했다면 · 합산 점수 ${U.num(st.growth.sum)}</summary>${result(st.growth,cx,true)}</details>`:''}`;
    else if(st.phase==='err')body=`${cx.error(st.errorCause||'other')}<p class="bad">찾지 못했음: ${esc(st.msg||'')}</p>`;
    if(st.phase==='done'&&st.teams?.length&&st.seals.remaining>0&&!stale&&!changed)
      body+=`<button type="button" class="sec" data-gs="follow">남은 인장으로 일반 1팀 이어서 찾기</button>`;
    if(st.followError)body+=`<p class="gd-warn">${esc(st.followError)}</p>`;
    const input=`<p class="gd-small">인장 ${sealConfig.dailyGrant}장(기본 지급) · 3장째는 구매 1회 성광석 ${sealConfig.purchaseCost}</p>
      <p class="${ex?'good':'warn'}" data-k="gs-day">${dayline}</p><p class="gd-small">출정 날짜는 한국시간 새벽 4시에 바뀜.</p>
      <p class="gd-small">${ex?'EX 1팀 · 인장 2장':'일반 1팀 · 가장 점수 높은 스테이지'} · 구원자 4명 필요</p>
      ${(pl?.warnings||[]).map(w=>`<p class="gd-warn">${esc(w)}</p>`).join('')}`;
    const start=st.phase==='run'?'':`<button type="button" data-gs="start"${pl&&!pl.withinCap?' disabled':''}>${st.phase==='done'?'다시 찾기 · ':''}오늘 편성 찾기 (${count}팀)</button><span class="season-wait">${pl?'약 '+U.durTextSec(pl.estimatedSec)+' 예상':'시작하면 예상 시간 표시'} · 탭을 열어 둬야 함</span>${pl&&!pl.withinCap?'<p class="gd-warn">예상 시간이 상한을 넘음. 탐색 대상을 줄여야 함.</p>':''}`;
    return `<div class="gd-search" data-k="gd-search" data-daily="true" data-state="${st.phase}"><h3 class="season-title">오늘 편성 찾기</h3>${cx.say(changed?'guildReset':sayKey(st,pl,day))}${changed}${cx.hasInfo?input:'<p class="gd-small">먼저 «내 계정 정보 불러오기»로 내 구원자 불러오기 필요.</p>'}${cx.hasInfo?body+start:''}${Result.basis('gs-basis',`<span class="gd-est">추정</span><p class="mut gd-small">오토 전투 · 내 정보의 최종 능력치와 지금 낀 장비 기준. 구원자와 지원이 팀끼리 겹치지 않음. 판별 점수 상위 20% 평균을 팀마다 구해 합산함. 평가한 후보 중 최고이며 전체 최적을 보장하지 않음. 실제 플레이 대조와 서버 반올림은 미확인임.</p>${(st.plan?.reductions||pl?.reductions||[]).map(x=>`<p class="gd-small">${esc(x)}</p>`).join('')}`)}</div>`;
  }
  function progressPaint(host,st){
    const stop=host.querySelector('[data-gs="partial"]');if(stop)stop.disabled=!!st.stopRequested;
    const list=host.querySelector('[data-k="gs-stages"]');if(!list)return;
    const stages=st.plan?.stages||[];
    // Reuse existing nodes: progress updates never replace controls, folds or the lane.
    while(list.children.length<stages.length)list.appendChild(list.ownerDocument.createElement('li'));
    while(list.children.length>stages.length)list.lastElementChild.remove();
    stages.forEach((s,i)=>{const el=list.children[i];el.textContent=(i<st.stageIndex?'✓ ':'')+s.name;el.dataset.current=String(i===st.stageIndex);});
  }
  const api={splitText,chips,flags,draft,sayKey,result,placementResult,html,progressPaint};
  if(node)module.exports=api;else root.GuildDailyUI=api;
})(typeof window!=='undefined'?window:globalThis);
