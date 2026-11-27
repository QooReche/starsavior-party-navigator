// Daily presentation. The planner owns dates, feasible splits and all result values.
(function(root){
  'use strict';
  const node=typeof module!=='undefined'&&module.exports;
  const U=node?require('./ui_shared'):root.UiShared,V=node?require('./guild_view'):root.GuildView;
  const Result=U.seasonUi,GS=node?require('./guild_search'):root.GuildSearch;
  const splitText=s=>[s.ex?`EX ${s.ex}팀`:'',s.normal?`일반 ${s.normal}팀`:''].filter(Boolean).join(' + ')||'팀 없음';
  function teamNames(teams){let normal=0;return teams.map(t=>t.kind==='ex'?'EX 팀':`일반 ${++normal}팀`);}
  const levelText=t=>t.kind==='ex'?`EX ${t.level}`:`${t.step}단계`;
  const chips=(G,t)=>Result.chip(U.esc(levelText(t)));
  function supportLine(G,t){const support=G.supports.find(s=>String(s.id)===String(t.sup));
    return `알리시아 지원 · ${U.esc(t.sup==='none'?'없음':support?.name||t.sup)}`;}
  function flags(t){
    const e=t.evaluation;
    return [...(e&&!e.stageSupportComplete?['스테이지·지원 미평가']:[]),...(e&&!e.placementComplete?['자리·리더 미평가']:[])];
  }
  function draft(t,grown=false){return {v:1,slots:t.order.map(key=>({key,grown})),leader:t.leaderKey||t.order[0],brk:t.brk?{name:t.brk,level:t.brkLv}:null};}
  function result(st,cx,grown=false,buttons=''){
    const {G,esc}=cx,teams=st.teams||st.rows||[];
    const blocks=teams.map((t,i)=>Result.team({title:`${i+1}팀`,attrs:`data-gs-team="${i}"`,chips:chips(G,t),
      score:`평균 점수 ${U.num(t.mean)} · 클리어율 ${U.pctText(t.clear)}<br>${Result.scoreLine(supportLine(G,t))}`,
      body:cx.cards(t,grown?st.snapshot:null)+`<div class="cs-foot">${GS.unsupportedHtml([t],esc)}${t.evaluation?.placementComplete&&t.placementChanged?Result.scoreLine('자리·리더 바꿔 넣음'):''}${Result.edit(`data-gs="edit" data-team="${i}" data-grown="${grown}"`)}</div>`
    })).join('');
    if(grown)return blocks;
    const unevaluated=[...new Set(teams.flatMap(flags).map(x=>x.replace(' 미평가','')))];
    const detail=`<div class="mut gd-small">인장 ${st.seals.used}장 사용 · ${splitText(st.split)} · 지원 겹침 없음<br>${esc(st.reason||'팀마다 평가한 후보 중 최고 점수를 골랐음.')}${teams.map((t,i)=>`<br>${i+1}팀: ${esc(levelText(t))}`).join('')}${unevaluated.length?`<br>자료상 미평가: ${esc(unevaluated.join(', '))}`:''}${(st.warnings||[]).map(x=>`<br>${esc(x)}`).join('')}</div>`;
    return `<div data-k="gs-daily-result">${cx.summary(st)}${Result.actions(buttons,Result.basis('gs-result-detail',detail,'탐색 결과 상세'),'상위 점수 기준')}${blocks}</div>`;
  }
  function html(st,cx){
    const {G,esc}=cx,pl=cx.plan,day=V.gameDay(G,cx.nowMs),seals=G.search.daily.seals;
    const ex=day.exOpen,cost=ex?seals.costEx:seals.costNormal;
    const dayline=`${day.day}요일 · EX ${ex?'열림':`닫힘${day.nextEx?' · 다음 EX는 '+day.nextEx+'요일':''}`}`;
    const stale=st.phase==='done'&&st.sig!==cx.sig?'<div class="gd-warn" data-k="gd-search-stale">계산 조건이 바뀌었음. 아래 결과는 이전 선택 기준이므로 다시 찾기 필요.</div>':'';
    const changed=st.plan?.day.date&&st.plan.day.date!==day.date?'<div class="gd-warn" data-k="gs-date-changed">날짜 바뀜 · 아래 편성은 출정 날짜 '+esc(st.plan.day.date)+' 기준임. 오늘 조건으로 다시 찾기 필요.</div>':'';
    const start=`<button type="button" data-gs="start"${pl?.withinCap===false?' disabled':''}>${st.phase==='done'?'다시 찾기':'오늘 편성 찾기'}</button>`;
    let body='';
    if(st.phase==='run')body=`<div data-k="gd-search-progress">${cx.work()}<span data-k="gs-step">탐색 준비 중</span><span data-k="gd-search-prog"></span><div class="mut gd-small" data-k="gs-eta">남은 시간 계산 중</div><button type="button" class="sec" data-gs="partial">중단</button></div>`;
    else if(st.phase==='done'){
      const follow=st.teams?.length&&st.seals.remaining>0&&!stale&&!changed?'<button type="button" class="sec" data-gs="follow">남은 인장으로 일반 1팀 이어서 찾기</button>':'';
      body=`${stale}${st.partial?Result.warning('중단함 · 여기까지 찾은 결과'):''}${cx.report()}${result(st,cx,false,follow+start)}${st.growth?`<details class="season-options" data-fold="gs-grown"><summary>육성했다면 · 합산 점수 ${U.num(st.growth.sum)}</summary>${result(st.growth,cx,true)}</details>`:''}`;
    }else{
      if(st.phase==='err')body=`${cx.error(st.errorCause||'other')}<p class="bad">찾지 못했음: ${esc(st.msg||'')}</p>`;
      body+=start+'<span class="mut season-wait">탭을 열어 둬야 함</span>';
    }
    if(st.followError)body+=`<p class="gd-warn">${esc(st.followError)}</p>`;
    if(st.phase!=='run'&&pl?.withinCap===false)body+=Result.warning('예상 시간이 상한을 넘음. 탐색 대상을 줄여야 함.');
    const opt=`<details class="season-options" data-fold="gs-options"><summary>탐색 설정 <span class="tag">${day.day}요일 EX ${ex?'열림':'닫힘'} · ${ex?'EX':'일반'} 1팀 · 인장 ${cost}장</span></summary><p class="gd-small">인장 ${seals.dailyGrant}장(기본 지급) · 3장째는 구매 1회 성광석 ${seals.purchaseCost}</p><p class="gd-small" data-k="gs-day">${dayline}</p><p class="gd-small">출정 날짜는 한국시간 새벽 4시에 바뀜.</p><p class="gd-small">${ex?'EX 1팀':'일반 1팀 · 가장 점수 높은 스테이지'} · 인장 ${cost}장 사용 · 구원자 4명 필요</p>${(pl?.warnings||[]).map(w=>`<p class="gd-warn">${esc(w)}</p>`).join('')}</details>`;
    return `<div class="gd-search" data-k="gd-search" data-daily="true" data-state="${st.phase}"><h3 class="season-title">오늘 편성 찾기</h3>${changed}${cx.hasInfo?body:'<p class="gd-small">먼저 «내 계정 정보 불러오기»로 내 구원자 불러오기 필요.</p>'}${opt}${Result.basis('gs-basis',`<span class="gd-est">추정</span><p class="mut gd-small">오토 전투 · 내 정보의 최종 능력치와 지금 낀 장비 기준. 구원자와 지원이 팀끼리 겹치지 않음. 판별 점수 상위 20% 평균을 팀마다 구해 합산함. 평가한 후보 중 최고이며 전체 최적을 보장하지 않음. 실제 플레이 대조와 서버 반올림은 미확인임.</p>${(st.plan?.reductions||pl?.reductions||[]).map(x=>`<p class="gd-small">${esc(x)}</p>`).join('')}`,'계산 기준 <i class="ux-help-mark" aria-hidden="true"></i>')}</div>`;
  }
  function progressPaint(host,st){
    const stop=host.querySelector('[data-gs="partial"]');if(stop)stop.disabled=!!st.stopRequested;
    const {step,eta}=GS.progressInfo(st),el=host.querySelector('[data-k="gs-step"]'),time=host.querySelector('[data-k="gs-eta"]');
    if(el)el.textContent=step.includes('단계 · ')?step.split(' · ')[0]+' · ':step;
    if(time)time.textContent=eta;
  }
  const api={splitText,teamNames,levelText,supportLine,chips,flags,draft,result,html,progressPaint};
  if(node)module.exports=api;else root.GuildDailyUI=api;
})(typeof window!=='undefined'?window:globalThis);
