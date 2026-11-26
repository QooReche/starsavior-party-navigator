// Daily presentation. The planner owns dates, feasible splits and all result values.
(function(root){
  'use strict';
  const node=typeof module!=='undefined'&&module.exports;
  const U=node?require('./ui_shared'):root.UiShared,V=node?require('./guild_view'):root.GuildView;
  const Daily=node?require('./guild_daily'):root.GuildDaily;
  const splitText=s=>[s.ex?`EX ${s.ex}팀`:'',s.normal?`일반 ${s.normal}팀`:''].filter(Boolean).join(' + ')||'팀 없음';
  function chips(G,t){
    const ex=t.kind==='ex',pct=G.challenge.levels.find(l=>l.level===t.level)?.score??G.challenge.levels[t.level-1]?.score??0;
    return `<span class="gs-stage${ex?' ex':''}">${ex?'EX 스테이지':`스테이지 ${t.step}단계`}</span><span class="gs-star${ex&&t.level?'':' mut'}">★ 별의 도전 ${ex&&t.level?`${t.level} · 추가 점수 +${pct}%`:'없음'}</span>`;
  }
  function flags(t){
    const e=t.evaluation;
    return [...(e&&!e.stageSupportComplete?['스테이지·지원 미평가']:[]),...(e&&!e.placementComplete?['자리·리더 미평가']:[])];
  }
  function draft(t,grown=false){return {v:1,slots:t.order.map(key=>({key,grown})),leader:t.leaderKey||t.order[0],brk:t.brk?{name:t.brk,level:t.brkLv}:null};}
  function sayKey(st,pl,seals,day){
    if(st.partial)return 'guildPartial';
    if(st.phase==='done')return st.warnings?.length?'guildShort':'guildDone';
    if(pl?.warnings.length)return 'guildShort';
    if(!day.exOpen)return 'guildClosed';
    if(seals===4)return 'guildCharge';
    if(seals<3)return 'guildFew';
    return st.splitChoice?'guildIdle':'guildPlan';
  }
  function result(st,cx,grown=false){
    const {G,esc}=cx,teams=st.teams||st.rows||[],warn=xs=>(xs||[]).map(x=>`<div class="gd-warn">${esc(x)}</div>`).join('');
    return `<div class="season-result" data-k="gs-daily-result"><div class="season-score"><span>${grown?'육성했다면 · ':''}${teams.length}팀 합산 점수 · 평가한 후보 중 최고</span><b data-k="gs-score">${U.num(st.sum)}</b><small>점 · 상위 점수 기준</small></div>
      <div class="season-chips"><span class="tag">인장 ${st.seals.used}장 사용</span><span class="tag">${splitText(st.split)}</span><span class="tag">지원 겹침 없음</span></div>${st.partial?'<div class="gd-warn">중단 · 부분 결과</div>':''}${warn(st.flags)}${warn(st.warnings)}<p class="gd-small">${esc(st.reason||'선택한 나눔에서 평가한 후보 중 합산 점수가 가장 큰 묶음임.')}</p>
      ${teams.map((t,i)=>{const role=G.search.supportRole?.[t.sup],support=G.supports.find(s=>String(s.id)===String(t.sup));
        return `<section class="cs-boss" data-gs-team="${i}"><div class="cs-bh"><b>${i+1}팀</b>${chips(G,t)}<span class="tag">인장 ${t.kind==='ex'?G.search.daily.seals.costEx:G.search.daily.seals.costNormal}장</span></div>${warn(flags(t))}
          <p class="cs-sc">상위 점수 ${U.num(t.score)} · 평균 ${U.num(t.mean)} · 클리어 ${Math.round(t.clear*100)}%</p>${cx.cards(t)}
          <div class="season-chips"><span class="tag">${esc(support?.name||t.sup)} <small class="${role?'warn':'mut'}">${esc(role?role+' 한정':'파티 전체')}${t.effectiveSupport==='none'?' · 해당 직업 없음, 효과 없음':''}</small></span><span class="tag">리더 ${esc(cx.label(t.leaderKey||t.order[0]))} · ${t.order.indexOf(t.leaderKey||t.order[0])<2?'전열':'후열'}</span></div>
          ${cx.breakBar(t)}<button type="button" class="sec" data-gs="edit" data-team="${i}" data-grown="${grown}">${i+1}팀을 직접 편성에서 고치기</button></section>`;
      }).join('')}</div>`;
  }
  function html(st,cx){
    const {G,esc}=cx,pl=cx.plan,day=V.gameDay(G,cx.nowMs),seals=st.sealCount??G.search.daily.seals.default;
    const choices=Daily.splits(G.search.daily,seals,day.exOpen),choice=st.splitChoice||choices[0],effective=pl?.effectiveSplit||choice;
    const count=effective.ex+effective.normal,disabled=st.phase==='run'?' disabled':'';
    const dayline=`${day.day}요일 · EX ${day.exOpen?'열림':`닫힘${day.nextEx?' · 다음 EX는 '+day.nextEx+'요일':''}`}`;
    const stale=st.phase==='done'&&st.sig!==cx.sig?'<div class="gd-warn" data-k="gd-search-stale">계산 조건이 바뀌었음. 아래 결과는 이전 선택 기준이므로 다시 찾기 필요.</div>':'';
    const changed=st.plan?.day.date&&st.plan.day.date!==day.date?'<div class="gd-warn" data-k="gs-date-changed">날짜 바뀜 · 아래 편성은 출정 날짜 '+esc(st.plan.day.date)+' 기준임. 오늘 조건으로 다시 찾기 필요.</div>':'';
    let body='';
    if(st.phase==='run')body=`${cx.work()}${U.planHtml('길드 오늘 편성 찾기 전체 진행')}<p data-k="gd-search-prog"></p><ol class="gd-small" data-k="gs-stages"></ol><button type="button" class="sec" data-gs="partial">중단</button>`;
    else if(st.phase==='done')body=`${stale}${cx.report()}${result(st,cx)}${st.growth?`<details class="season-options" data-fold="gs-grown"><summary>육성했다면 · 합산 점수 ${U.num(st.growth.sum)}</summary>${result(st.growth,cx,true)}</details>`:''}`;
    else if(st.phase==='err')body=`${cx.error(st.errorCause||'other')}<p class="bad">찾지 못했음: ${esc(st.msg||'')}</p>`;
    const input=`<div class="gd-small">오늘 쓸 인장</div><div class="seal-stepper"><button type="button" data-gs="minus" aria-label="인장 한 장 줄이기"${seals<=1?' disabled':disabled}>−</button><output aria-live="polite">${seals}장</output><button type="button" data-gs="plus" aria-label="인장 한 장 늘리기"${seals>=4?' disabled':disabled}>+</button></div>${seals===4?'<span class="tag" style="color:var(--gold)">충전 1회 = 성광석 30개</span>':''}
      <p class="${day.exOpen?'good':'warn'}" data-k="gs-day">${dayline}</p><p class="gd-small">출정 날짜는 한국시간 새벽 4시에 바뀜.${!day.exOpen?' 오늘은 일반 스테이지만 찾음.':seals===1?' EX 스테이지는 인장 2장이 필요함.':''}</p>
      <div class="option-chips" role="group" aria-label="인장 나누기"><label><input type="radio" name="gs-split" data-gs="split" value="auto"${!st.splitChoice?' checked':''}${disabled}>자동(추천)</label>${choices.map(s=>`<label><input type="radio" name="gs-split" data-gs="split" value="${s.ex}"${st.splitChoice?.ex===s.ex?' checked':''}${disabled}>${splitText(s)}</label>`).join('')}</div>
      <p class="gd-small">인장 ${seals}장 → ${splitText(effective)} · 구원자 ${count*4}명 필요${pl?`(현재 풀로 최대 ${pl.availableTeams}팀)`:''}${!st.splitChoice&&day.exOpen&&choice.ex?' · EX 우선, 약하면 일반 나눔도 비교':''}</p>
      ${(pl?.warnings||[]).map(w=>`<p class="gd-warn">${esc(w)} · 인장이 남을 수 있음</p>`).join('')}
      <div class="season-boss-summary">${[...Array(effective.ex).fill(true),...Array(effective.normal).fill(false)].map((ex,i)=>`<div><b>${i+1}팀</b><span class="gs-stage${ex?' ex':''}">${ex?'EX 스테이지':'스테이지 자동 1~6단계'}</span><span class="gs-star${ex?'':' mut'}">★ 별의 도전 ${ex?'자동':'없음'}</span><span class="sub">인장 ${ex?2:1}장 · 지원 자동</span></div>`).join('')}</div>`;
    const start=st.phase==='run'?'':`<button type="button" data-gs="start"${pl&&!pl.withinCap?' disabled':''}>${st.phase==='done'?'다시 찾기 · ':''}오늘 편성 찾기 (${count}팀)</button><span class="season-wait">${pl?'약 '+U.durTextSec(pl.estimatedSec)+' 예상':'시작하면 예상 시간 표시'} · 탭을 열어 둬야 함</span>${pl&&!pl.withinCap?'<p class="gd-warn">예상 시간이 상한을 넘음. 인장 수나 탐색 대상을 줄여야 함.</p>':''}`;
    return `<div class="gd-search" data-k="gd-search" data-daily="true" data-state="${st.phase}"><h3 class="season-title">오늘 편성 찾기</h3>${cx.say(changed?'guildReset':sayKey(st,pl,seals,day))}${changed}${cx.hasInfo?input:'<p class="gd-small">먼저 «내 계정 정보 불러오기»로 내 구원자 불러오기 필요.</p>'}${cx.hasInfo?body+start:''}<details class="season-options" data-fold="gs-basis"><summary>계산 기준</summary><span class="gd-est">추정</span><p class="gd-small">오토 전투 · 내 정보의 최종 능력치와 지금 낀 장비 기준. 구원자와 지원이 팀끼리 겹치지 않음. 판별 점수 상위 20% 평균을 팀마다 구해 합산함. 평가한 후보 중 최고이며 전체 최적을 보장하지 않음. 실제 플레이 대조와 서버 반올림은 미확인임.</p>${(st.plan?.reductions||pl?.reductions||[]).map(x=>`<p class="gd-small">${esc(x)}</p>`).join('')}</details></div>`;
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
  const api={splitText,chips,flags,draft,sayKey,result,html,progressPaint};
  if(node)module.exports=api;else root.GuildDailyUI=api;
})(typeof window!=='undefined'?window:globalThis);
