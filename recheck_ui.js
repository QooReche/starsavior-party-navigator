// 현장 재조사(자동 추천 끝의 자리·리더 비교, 11/23) 화면 조각. 상태는 recommend_runtime.js RECHECK, 그리는 때는 party_template.html(runCore·recheckPaint).
// 재조사 칸(결과 판 맨 위 한 줄 — 끝나도 같은 높이의 기록 줄)·카드 칩·요약의 이전→지금 줄·카드 미끄러짐(FLIP)·대안 줄 표시.
// 스타일은 recheck.css 한 곳. 움직임은 transform·opacity 만. DOM 을 만지는 것은 sync·decorate·snap·flip 뿐이고 나머지는 글자만 만든다.
(function(root){
  'use strict';
  const END_MS=1200;   // 끝 장면(끄덕임·금빛 띠) 뒤 길을 접고 그웬이 결과 자리로
  const POS=['back','front','front','back'],KO={back:'후열',front:'전열'};   // 화면 자리 순서(arrangeOf order)
  const STEP={enter:0,screen:0,check100:1,final200:1,fix:2};
  const LOG={enter:'[FIELD] 좌표 고정 — 승리 루트 재진입',screen:'[SCAN] 전열 6조합 × 리더 4명 — 24가지 대조 시작',half:'[SCAN] 24가지 중 절반 대조 — 유력 후보 표시',
    check100:'[CHECK] 유력 3개 + 지금 자리 — 100판 정밀 대조',final200:'[CHECK] 차이 확인 — 200판까지 이어서 확인',fix:'[FIX] 판정 중'};
  const esc=v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  const pct=r=>Math.round((r?.clear||0)*100)+'%';
  // 단계별 진행도(재조사 칸 막대·창밖 고리): 훑기 0~50%, 1단계 결선 50~80%, 2단계 80~95%, 판정 95%
  function progress(r){
    if(!r?.state)return 0;if(r.state!=='work')return 1;const f=r.all?Math.min(1,r.got/r.all):0;
    return Math.round(({enter:0,screen:.5*f,check100:.5+.3*f,final200:.8+.15*f,fix:.95}[r.stage]??0)*1000)/1000;
  }
  const screened=r=>r.stage==='enter'?0:r.stage==='screen'?(r.all?Math.round(24*Math.min(1,r.got/r.all)):0):24;
  // 기록 줄은 단계가 바뀔 때만 바뀜(훑기 절반에서 한 번 더) — 숫자를 매번 바꾸지 않음
  const logKey=r=>r.stage==='screen'&&r.all&&r.got*2>=r.all?'half':LOG[r.stage]?r.stage:'enter';
  // 받침에 맞춘 조사(을/를·으로/로)
  function josa(word,pair){const c=String(word).charCodeAt(String(word).length-1)-0xAC00,jong=c>=0&&c<11172?c%28:0;
    if(pair==='로')return jong&&jong!==8?'으로':'로';return jong?pair[0]:pair[2];}
  // 규칙 자리 → 지금 자리: 역할(전열·후열)이 바뀐 구원자와 새 리더. key → {from,to,lead}
  function moves(rule,now){
    const out={};now.order.forEach((k,i)=>{const from=POS[rule.order.indexOf(k)],to=POS[i],lead=now.lead===k&&rule.lead!==k;if(from!==to||lead)out[k]={from,to,lead};});return out;
  }
  function story(rule,now,name){
    const m=moves(rule,now),fr=now.order.filter(k=>m[k]&&m[k].to==='front'&&m[k].from==='back').map(name),parts=[];
    if(fr.length)parts.push(fr.join('·')+josa(fr.at(-1),'을/를')+' 전열'+josa('전열','로'));
    if(now.lead&&now.lead!==rule.lead)parts.push('리더를 '+name(now.lead)+josa(name(now.lead),'로'));
    return parts.length?parts.join(', ')+' 바꿈':'';
  }
  const steps=r=>{const i=STEP[r.stage]??0,s=j=>j<i?' data-s="done"':j===i?' data-s="now"':'';
    return `<span${s(0)}>① 24가지 훑기 <em>${screened(r)}/24</em></span><span${s(1)}>② 유력 3개 정밀 대조</span><span${s(2)}>③ 확정</span>`;};
  // 재조사 칸. d = {rows:[{label,from,to}](바뀐 팀), story, teams, reverted, view, fresh, bundle}
  function strip(r,d={}){
    const head=`class="rc-strip" data-k="recheck" data-state="${esc(r.state)}"${d.fresh?' data-new=""':''}`;
    if(r.state==='work'){const p=progress(r);
      return `<div ${head} data-stage="${esc(r.stage)}"><div class="rc-head"><b class="rc-title"><i class="rc-tick" aria-hidden="true"></i>현장 재조사 — 자리·리더 맞추는 중</b><span class="rc-sub">찾아낸 승리 루트로 돌아와 전열 6조합 × 리더 4명을 다시 대조함</span></div>
<div class="rc-mid"><div class="rc-steps" data-rc="steps">${steps(r)}</div><div class="rc-pbar" role="progressbar" aria-label="현장 재조사 진행" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(p*100)}"><i style="transform:scaleX(${p.toFixed(3)})"></i></div><code class="rc-log" data-log="${logKey(r)}">${LOG[logKey(r)]}</code></div>
<div class="rc-side"><span>${d.teams||r.teams}팀 · 팀마다 24가지</span>${d.bundle?'':'<button type="button" class="sec" data-recheck-stop>지금 자리로 확정</button>'}</div></div>`;}
    if(r.state==='done'&&r.outcome==='changed'){
      const nums=d.summary!=null?esc(d.summary):(d.rows||[]).map(x=>`${esc(x.label)} 클리어 <em>${pct(x.from)} → ${pct(x.to)}</em>`).join(' · ');
      return `<div ${head} data-end="changed"><div class="rc-end"><b><span class="rc-stamp">진형 재정렬</span>${nums}</b><span>${d.record?esc(d.record):`현장 재조사 기록: 24가지 대조 → 유력 3개 ${r.deep?200:100}판 확인.${d.story?' '+esc(d.story):''}`}</span></div>
${d.readonly?'':`<div class="rc-side"><button type="button" class="sec" data-recheck-view>${d.view==='rule'?'지금 자리로 보기':'이전 자리로 보기'}</button></div>`}</div>`;}
    if(r.state==='done'){const t=d.teams||r.teams;
      return `<div ${head} data-end="same"><div class="rc-end"><b><span class="rc-stamp">현 진형 유지</span>${d.summary!=null?esc(d.summary):d.reverted?'지금 자리·리더 그대로':'지금 자리·리더가 가장 좋음'}</b><span>${d.record?esc(d.record):d.reverted
        ?`현장 재조사 기록: ${t}팀 × 24가지를 대조함. 바꾼 자리가 표준 판정에서 높지 않아 지금 자리로 되돌림`
        :`현장 재조사 기록: ${t}팀 × 24가지를 대조했고 확실히 더 좋은 자리는 없었음`}</span></div>${d.skipped?`<div class="rc-side"><span>${esc(d.skipped)}</span></div>`:''}</div>`;}
    return `<div ${head} data-end="${r.state==='cancel'?'cancel':'error'}"><div class="rc-end"><b>${r.state==='cancel'?'재조사 중단 — 규칙 자리 유지':'재조사를 끝내지 못함 — 규칙 자리 유지'}</b><span>${r.state==='cancel'?'«지금 자리로 확정»으로 비교를 멈췄음':'자리·리더 비교 중 오류가 나서 원래 자리로 표시함'}</span></div></div>`;
  }
  // 진행 중 칸을 다시 그리지 않고 바뀐 곳만 고침(막대·단계·기록 줄). 기록 줄은 바뀔 때만 새 노드(나타나는 움직임 1회)
  function sync(el,r){
    if(!el||r.state!=='work')return;const p=progress(r),bar=el.querySelector('.rc-pbar');
    if(bar){bar.setAttribute('aria-valuenow',Math.round(p*100));bar.firstElementChild.style.transform=`scaleX(${p.toFixed(3)})`;}
    el.dataset.stage=r.stage;const st=el.querySelector('[data-rc=steps]'),html=steps(r);if(st&&st.innerHTML!==html)st.innerHTML=html;
    const log=el.querySelector('.rc-log'),k=logKey(r);
    if(log&&log.dataset.log!==k){const n=log.cloneNode(false);n.dataset.log=k;n.textContent=LOG[k];log.replaceWith(n);}
  }
  // 요약의 이전 → 지금 줄: 얼굴 4개 두 묶음(테두리 주황 = 전열, 파랑 = 후열, 금색 = 리더) + 클리어
  function swap(rule,now,src,{from,to}={}){
    const faces=(a,cmp)=>a.order.map((k,i)=>`<span class="rc-f" data-pos="${POS[i]}"${a.lead===k?' data-lead=""':''}${cmp&&POS[cmp.order.indexOf(k)]!==POS[i]?' data-moved=""':''}>${src(k)?`<img src="${esc(src(k))}" alt="" loading="lazy">`:''}</span>`).join('');
    return `<div class="rc-swap" data-k="recheck-swap"><span class="rc-was"><span class="rc-row">${faces(rule)}</span><small>이전</small></span><span class="rc-to" aria-hidden="true">→</span><span class="rc-now"><span class="rc-row">${faces(now,rule)}</span><small>지금</small></span>${from&&to?`<b class="rc-num"><s>${pct(from)}</s> → ${pct(to)}</b>`:''}</div>`;
  }
  // 카드 칩(«후열 → 전열 · 리더», 좁은 화면은 «→ 전열»)·대안 줄 표시. el = .party[data-party]
  function decorate(el,{chips=null,tags={}}={}){
    if(!el)return;
    if(chips)for(const [k,v] of Object.entries(chips)){const c=el.querySelector(`.rowcards .gc[data-key="${esc(k)}"]`),card=c?.querySelector('.card');if(!card)continue;
      c.dataset.rcMove='';const role=v.from!==v.to;
      card.insertAdjacentHTML('beforeend',`<span class="rc-chip">${role?`<span class="rc-from">${KO[v.from]} </span>→ ${KO[v.to]}`:''}${v.lead?`${role?' · ':''}리더`:''}</span>`);}
    for(const [k,t] of Object.entries(tags)){const q=el.querySelector(`.alternatives .qrow[data-key="${esc(k)}"] .qt`);if(q)q.insertAdjacentHTML('afterbegin',`<span class="rc-tag" data-t="${esc(t[0])}">${t[1]}</span> `);}
  }
  // 카드 미끄러짐(옛 자리를 재고 그만큼 되돌려 놓은 뒤 0으로, 0.7초): 다시 그리기 전 snap → 그린 뒤 flip
  function snap(el){const m=new Map();el?.querySelectorAll('.rowcards .gc[data-key]').forEach(e=>m.set(e.dataset.key,e.getBoundingClientRect()));return m;}
  function flip(el,before){
    if(!el||!before?.size)return 0;let n=0;
    el.querySelectorAll('.rowcards .gc[data-key]').forEach(e=>{const a=before.get(e.dataset.key);if(!a)return;const b=e.getBoundingClientRect(),dx=a.left-b.left,dy=a.top-b.top;
      if(Math.abs(dx)<1&&Math.abs(dy)<1)return;n++;
      e.style.transition='none';e.style.transform=`translate(${dx.toFixed(1)}px,${dy.toFixed(1)}px)`;e.getBoundingClientRect();
      e.style.transition='transform .7s cubic-bezier(.2,.8,.2,1)';e.style.transform='';e.addEventListener('transitionend',()=>{e.style.transition='';},{once:true});});
    return n;
  }
  const api={END_MS,POS,LOG,progress,screened,logKey,josa,moves,story,strip,sync,swap,decorate,snap,flip};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.RecheckUi=api;
})(typeof window!=='undefined'?window:globalThis);
