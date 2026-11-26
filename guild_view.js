// 길드 방어전 안내 패널(순수 함수: 저장소·네트워크 접근 없음). 규칙은 guild_defense.py 와 같다(tests/guild_defense_test.py 가 일치 확인).
(function (root) {
  "use strict";
  const MAX_TIER = 3;
  // Game day is KST 04:00, independent of the browser's local timezone.
  function gameDay(G, nowMs=Date.now()) {
    const reset=G.search.daily.reset, names=['일','월','화','수','목','금','토'];
    const d=new Date(nowMs+(reset.utcOffsetHours-reset.hour)*3600000), weekday=d.getUTCDay();
    const days=G.rules.entryDaysEx||[];
    let next=1;while(next<=7&&!days.includes(names[(weekday+next)%7]))next++;
    return {date:d.toISOString().slice(0,10),weekday,day:names[weekday],exOpen:days.includes(names[weekday]),nextEx:next<=7?names[(weekday+next)%7]:null};
  }
  const {num, pctText} = typeof module !== "undefined" && module.exports ? require("./ui_shared.js") : root.UiShared;
  function parseTime(s) { return Date.parse(/T/.test(s) ? s : s + "T00:00:00+09:00"); }
  function md(s) { const d = new Date(parseTime(s) + 9 * 3600 * 1000); return String(d.getUTCMonth() + 1).padStart(2, "0") + "/" + String(d.getUTCDate()).padStart(2, "0"); }
  // state: upcoming / active / settling / ended, needsUpdate = 시즌 종료 시각이 지남(갱신 대기)
  function seasonState(season, nowMs) {
    const s = parseTime(season.start), e = parseTime(season.end), d = parseTime(season.settleEnd);
    const state = nowMs < s ? "upcoming" : nowMs < e ? "active" : nowMs < d ? "settling" : "ended";
    return {state, needsUpdate: nowMs >= e};
  }
  function exStep(G) { return G.steps.find(s => s.step===G.defaultStep) || G.steps.find(s => s.ex); }
  function baseTotal(G) { return scoreAt(G,0,1); }
  function extraPct(G, level, tiers) {
    let pct = level ? G.challenge.levels[level - 1].score : 0;
    G.sets.items.forEach((it, i) => { const t = (tiers || [])[i] || 0; if (t) pct += it.tiers[t - 1].add; });
    return pct;
  }
  // 확인된 점수식(영상 2026-11-01): (기본 + 졸개 + 보스 점수 × 보스 깎은 비율) × (1 + 추가 점수%)
  // 보스 점수(정수): 클라 실시간 점수처럼 비율을 1/10000 내림 + 정수 나눗셈 내림. guild_defense.py boss_points 와 같다(1e-9 = 부동소수 보정)
  function bossPoints(G, f) {
    const q = Math.floor(Math.max(0, Math.min(1, f)) * 10000 + 1e-9);
    return Math.floor(exStep(G).bossKill * q / 10000);
  }
  // kills = 처치한 졸개 수(생략 = 전부). 단계 보너스 곱셈 뒤 반올림은 서버 계산이라 미확인(기존 사사오입 유지)
  function scoreAt(G, pct, f, kills) {
    const ex = exStep(G), n = G.stepsMeta.minions;
    const k = kills == null ? n : Math.max(0, Math.min(n, Math.trunc(kills)));
    const elites=kills==null?(G.stepsMeta.eliteCount||0):0;
    return Math.floor(((ex.base + (k-elites) * ex.kill + elites*(ex.eliteKill||0) + bossPoints(G, f)*(G.stepsMeta.bossCount??1)) * (100 + pct) + 50) / 100);
  }
  // 판별 진행도 -> {k, f}. 졸개전(prog<0.5)은 깎은 체력 d=2p 에서 k=floor(졸개 수×d)로 근사(같은 체력·차례로 처치 가정), 보스 비율 0
  function progParts(G, prog) {
    const n = G.stepsMeta.minions, p = Math.max(0, Math.min(1, prog));
    const threshold=(G.stepsMeta.bossWave??1)/(G.stepsMeta.waveCount??2);
    if (p >= threshold) return {k: n, f: Math.max(0, Math.min(1, (p-threshold)/(1-threshold)))};
    return {k: Math.min(n, Math.floor(n*p/threshold+1e-9)), f: 0};
  }
  function scoreFromProg(G, pct, prog) { const r = progParts(G, prog); return scoreAt(G, pct, r.f, r.k); }
  function score(G, pct) {
    const out = {};
    for (const h of G.score.hypotheses) out[h.id] = scoreAt(G, pct, 1);
    return out;
  }
  // 클라 길드 요청은 선택 목록을 보내지 않음. UI 재개는 시즌 플래그로만 허용함.
  function setsUi(G) { return G.sets.ui === true; }
  function bestSelection(G) { return {level: G.challenge.levels.length, tiers: G.sets.items.map(() => 0)}; }
  function normSel(G, sel) {
    const b = bestSelection(G);
    const level = Number.isInteger(sel && sel.level) && sel.level >= 0 && sel.level <= b.level ? sel.level : b.level;
    const tiers = G.sets.items.map((_, i) => { const t = sel && sel.tiers && sel.tiers[i]; return setsUi(G) && Number.isInteger(t) && t >= 0 && t <= MAX_TIER ? t : b.tiers[i]; });
    const supports = supportChoices(G);
    const support = supports.some(s=>s.id===String(sel?.support))?String(sel.support):'none';
    return {level, tiers, support};
  }
  function supportChoices(G) {
    const ids=G.search?.final?.supports||['none',...(G.supports||[]).map(s=>String(s.id))];
    return ids.map(id=>({id:String(id),name:(G.supports||[]).find(s=>String(s.id)===String(id))?.name||SUP_NAME[id]||String(id)}));
  }
  function battleOptions(G, sel, step) {
    const s=normSel(G,sel),ex=exStep(G);
    return {seasonId:G.season.id,dataVersion:G.dataVersion,step,level:step===ex.step?s.level:0,sets:step===ex.step?s.tiers:G.sets.items.map(()=>0),support:s.support};
  }
  function range(sc) { const v = Object.values(sc); return [Math.min(...v), Math.max(...v)]; }
  function rangeText(sc) { const [a, b] = range(sc); return a === b ? num(a) : num(a) + " ~ " + num(b); }
  function levelEffects(G, lv) {
    const T = G.challenge.effectText, out = [];
    if (lv.skillStack) out.push(T.skillStack.replace("{v}", lv.skillStack));
    if (lv.hpDrain) out.push(T.hpDrain.replace("{v}", lv.hpDrain));
    if (lv.speed) out.push(T.speed.replace("{v}", lv.speed));
    if (lv.immune) out.push(T.immune.replace("{v}", lv.immune));
    return out;
  }
  const STATE_TEXT = {upcoming: "시작 전", active: "진행 중", settling: "결산 중(플레이 불가)", ended: "종료"};
  const EL = {sun: "태양", moon: "달", star: "별", order: "질서", chaos: "혼돈"};
  const EST = '<span class="gd-est" title="공식 수치가 아니라 계산·해석으로 얻은 값임">추정</span>';

  function seasonBox(G, nowMs, esc) {
    const st = seasonState(G.season, nowMs), s = G.season;
    return `<div class="gd-head"><b>길드 방어전 · ${esc(s.label)}</b><span class="gd-state ${st.state}">${STATE_TEXT[st.state]}</span>${help('시즌 정보', `${G.title} · 이 시즌 정보는 ${md(G.asOf)} 기준. 진행 ${md(s.start)} ~ ${md(s.end)} 04:00 · 결산 ~${md(s.settleEnd)} 04:00 · 보스 ${s.boss.name}(${EL[s.boss.element] || ''} ${s.boss.role})`, esc)}</div>`+
      (st.needsUpdate?'<p class="mut gd-small" data-k="gd-stale">갱신 대기 · 아래는 지난 시즌 기준임</p>':'');
  }
  const help = (title, text, esc) => `<button type="button" class="ux-help" aria-label="${esc(title)} 설명" aria-expanded="false" data-help="${esc(text)}">ⓘ</button>`;
  // Reference table only: never present preset power as the user's account result.
  function simUi(G) { return G.sim?.ui === true; }
  function overview(G, esc) {
    if (!simUi(G)) return '';
    const S=G.sim;
    if(!S)return '<p class="mut">단계·점수 자료 없음</p>';
    const g=S.growth.find(x=>Number(x)===2)??S.growth[0], b=simBest(S,g), e=simExpect(G,S,g);
    const baseLabel=exStep(G).ex?'EX':exStep(G).step+'단계',supportName=id=>(G.supports||[]).find(s=>String(s.id)===id)?.name||SUP_NAME[id]||id;
    const level=b=>b?(b.level?b.level+'단계':baseLabel+' 기본'):baseLabel+'도 어려움';
    const power=g=>'약 '+Math.round(S.recPower*g/10000)+'만';
    const detail=(b,expect)=>b?`${expect?'별의 도전 '+b.level+'단계 · ':''}클리어 ${pct(b.p)} · 지원 ${supportName(b.support)}`:'클리어 기준 미달';
    const rows=S.growth.map(g=>{const b=simBest(S,g),e=simExpect(G,S,g);return `<tr><th>${power(g)}</th><td><b>${level(b)}</b><small>${b?pct(b.p):'—'} ${help('클리어 편성·지원',b?S.teams[b.team].names.join(' · ')+' · '+detail(b,false):'클리어 기준 미달',esc)}</small></td><td><b>${e?num(e.m):'—'}</b><small>${e?level(e)+' · '+pct(e.p):'—'} ${help('점수 편성·지원',e?S.teams[e.team].names.join(' · ')+' · '+detail(e,true):'자료 없음',esc)}</small></td></tr>`;}).join('');
    return `<div data-k="gd-overview"><p class="season-basis">기준표 · 전투력 ${power(g)} ${help('기준표','내 계정 결과가 아닌 표준 육성 후보의 모의 전투 기준임. 두 지표는 서로 다른 편성·단계·지원일 수 있음. 지원과 편성은 각 ⓘ에서 확인 가능. 내 구원자는 편성 찾기로 계산함.',esc)}</p>
<div class="season-kpis"><div><span>최고 클리어 단계</span><b data-k="gd-clear-kpi">${level(b)}</b><small>${b?'클리어 '+pct(b.p):'기준 미달'}</small></div><div><span>최대 기대 점수</span><b data-k="gd-score-kpi">${e?num(e.m):'—'}</b><small>${e?level(e)+' · 클리어 '+pct(e.p):'자료 없음'}</small></div></div>
<table class="season-reference" data-k="gd-summary-table"><thead><tr><th>전투력</th><th>클리어 단계 · 지원</th><th>기대 점수 · 지원</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }
  function rulesBox(G, esc) {
    const r = G.rules;
    return `<ul class="gd-rules" data-k="gd-rules"><li>한 판 최대 ${r.turnLimit}턴 · 파티 ${r.partyCount}개(${r.partySize}명)</li>
<li><b>${esc(r.reuse)}</b> — 같은 구원자를 여러 번 쓸 수 없으니 날마다 쓸 구원자를 나눠 정해야 함</li>
<li>${esc(r.abandon)}</li>
<li>EX는 ${r.entryDaysEx.join("·")}요일만 입장 · 입장 재화 ${r.entryItemEx}개${r.skipEx ? "" : " · 전투 건너뛰기 불가"}</li></ul>`;
  }
  function stepsTable(G, cur, esc) {
    const rows = G.steps.slice().reverse().map(s => {
      const total = s.base + G.stepsMeta.minions * s.kill + s.bossKill;
      return `<tr${s.step === cur ? ' class="cur"' : ""}><td>${s.ex?'EX 스테이지':'스테이지 '+s.step+'단계'}</td><td>${num(s.power)}</td><td>${num(total)}</td></tr>`;
    }).join("");
    return `<details class="gd-steps"><summary>단계별 기본 점수</summary><div class="gd-scroll"><table><thead><tr><th>단계</th><th>권장 전투력</th><th>기본+졸개+보스 처치</th></tr></thead><tbody>${rows}</tbody></table></div><div class="mut gd-small">${esc(G.stepsMeta.minionsNote)}</div></details>`;
  }
  function levelTable(G, sel, esc) {
    const rows = G.challenge.levels.map(lv => {
      const sc = score(G, extraPct(G, lv.level, [0, 0, 0, 0]));
      const big = lv.level >= 7;
      const tip = big && Number.isFinite(lv.noticeAtk) && Number.isFinite(lv.noticeHp) ? ` title="공지 표(옛 값): 공격 +${lv.noticeAtk}%, 생명력·방어 +${lv.noticeHp}%"` : "";
      return `<tr${lv.level === sel.level ? ' class="cur"' : ""}><td>${lv.level}</td><td${tip}>공격 +${lv.atk}% · 생명력·방어 +${lv.hp}%</td><td>+${lv.score}%</td><td>${rangeText(sc)}</td><td class="gd-fx">${levelEffects(G, lv).map(esc).join("<br>")}</td></tr>`;
    }).join("");
    return `<div class="gd-scroll"><table class="gd-levels" data-k="gd-levels"><thead><tr><th>★ 별의 도전</th><th>보스 능력치</th><th>추가 점수</th><th>점수(보스 다 깎음)</th><th>누적 효과</th></tr></thead><tbody>${rows}</tbody></table></div>
<div class="mut gd-small">${esc(G.challenge.note)} ${esc(G.challenge.statNote)}</div>`;
  }
  function selectBox(G, sel) {
    const opt = (n, cur, label) => `<option value="${n}"${n === cur ? " selected" : ""}>${label}</option>`;
    const lv = `<label>별의 도전<select data-g="level">${opt(0, sel.level, "★ 별의 도전 없음")}${G.challenge.levels.map(l => opt(l.level, sel.level, "★ 별의 도전 " + l.level + " · 추가 점수 +" + l.score + "%")).join("")}</select></label>`;
    const sets = G.sets.items.map((it, i) => `<label>${it.name}<select data-g="set" data-i="${i}">${opt(0, sel.tiers[i], "끔")}${it.tiers.map((t, j) => opt(j + 1, sel.tiers[i], (j + 1) + "단계 +" + t.add + "% · " + t.text)).join("")}</select></label>`).join("");
    return `<div class="gd-sel">${lv}${setsUi(G)?sets:''}<button type="button" class="sec" data-g="best">최고 점수 조합으로</button></div>`;
  }
  // 시뮬 추정(tools/build_guild_sim.py → G.sim): 육성 배수마다 클리어율 passP 이상인 최고 단계와 그 단계 점수 범위(선택 효과 끔)
  const SUP_NAME = {none: "지원 안 고름", gust: "격돌의 돌풍", focus: "날카로운 집중력", strike: "강인한 타격", mountain: "태산의 의지", fire: "불의 고동"};
  function simBest(S, g) { const b = S && S.summary && S.summary[String(g)]; return b ? {level: b.level, team: b.team, p: b.p, support: b.support || "none"} : null; }
  // 팀·지원별 클리어율 행(구버전 자료는 rates 만 있음 = 지원 안 고름)
  function simRates(S, t, sup, g) { const bs = t.bySupport; const r = bs ? (bs[sup] || {})[String(g)] : (sup === "none" && t.rates ? t.rates[String(g)] : null); return r || null; }
  // 팀·지원별 진행도 행(= 0.5 + 0.5 × 보스 깎은 비율, 클리어 1). 구버전 자료는 없음
  function simProg(S, t, sup, g) { const ps = t.progBySupport; return ps && ps[sup] ? ps[sup][String(g)] || null : null; }
  // 판별 «보스 깎은 비율» 평균(build_guild_sim fracBySupport). 있으면 이것을 점수식에 넣는다(점수가 이 값에 선형이라 정확)
  function simFrac(S, t, sup, g) { const fs = t.fracBySupport; return fs && fs[sup] ? fs[sup][String(g)] || null : null; }
  // 프리셋·팀·지원·단계 중 기대 점수 최대. 판별 frac 우선, 옛 자료는 진행도 → 클리어율 순으로 대체.
  // 선택 효과는 길방에 없으므로(클라 확인) 기본은 off 만 비교. opts.allSets 로 옛 데이터의 다른 프리셋(가정)도 비교할 수 있다
  // 시뮬 표는 평균값(fracBySupport)뿐이라 처치 졸개 수 k 가 없다 -> 졸개 전부 처치로 계산(졸개전 패배 판이 있으면 조금 높게 봄)
  function simExpect(G, S, g, opts) {
    let best = null;
    const all = S.sets || {off: [0, 0, 0, 0]};
    const presets = opts && opts.allSets ? all : {off: all.off || [0, 0, 0, 0]};
    S.teams.forEach((t, ti) => Object.entries(presets).forEach(([set, tiers]) => {
      const tab = set === "off" ? t : (t.bySets || {})[set];
      if (!tab) return;
      (S.supports || ["none"]).forEach(sup => {
        const r = simRates(S, tab, sup, g), pr = simProg(S, tab, sup, g), fr = simFrac(S, tab, sup, g);
        if (!r) return;
        S.levels.forEach((lv, i) => {
          const pc = extraPct(G, lv, tiers);
          const f = fr ? fr[i] : pr ? Math.max(0, Math.min(1, 2 * pr[i] - 1)) : r[i];
          const v = tab.scoreBySupport?.[sup]?.[String(g)]?.[i] ?? (fr || pr ? scoreAt(G, pc, f) : Math.round(scoreAt(G, pc, 1) * r[i]));
          if (r[i] >= 0 && (!best || v > best.m)) best = {m: v, team: ti, support: sup, level: lv, set, p: r[i], f, e: {A: v}};
        });
      });
    }));
    return best;
  }
  const pct = pctText;
  function simBox(G, esc) {
    if (!simUi(G)) return '';
    const S = G.sim;
    if (!S) return "";
    const lines = S.growth.map(g => {
      const b = simBest(S, g), pw = "권장 전투력 ×" + g + " (약 " + Math.round(S.recPower * g / 10000) + "만)";
      if (!b) return `<li>${pw}: <b>EX도 어려움</b> <span class="mut">(모든 후보 클리어율 ${pct(S.passP)} 미만)</span></li>`;
      const t = S.teams[b.team], lv = b.level ? "별의 도전 " + b.level + "단계" : "별의 도전 없이(0단계)";
      return `<li>${pw}: <b>${lv}</b>까지 · 점수 <b>${rangeText(score(G, extraPct(G, b.level, [0, 0, 0, 0])))}</b> ${EST}<br><span class="mut">${esc(t.names.join(" · "))} · 알리시아 지원 «${SUP_NAME[b.support]}» · 클리어 ${pct(b.p)}</span></li>`;
    }).join("");
    const ex = S.growth.map(g => {
      const e = simExpect(G, S, g);
      if (!e) return "";
      const t = S.teams[e.team];
      const label = e.set === "off" ? "선택 효과 끔" : e.set === "max" ? "모두 최대(가정)" : "선택 효과 " + S.sets[e.set].join("·") + "(가정)";
      return `<li>×${g}: 별의 도전 <b>${e.level}단계</b> · 기대 점수 <b>${rangeText(e.e)}</b> ${setsUi(G)?`<span class="gd-state" data-k="gd-sim-set">${esc(label)}</span> `:''}<span class="mut">(${esc(t.names.join("·"))} · «${SUP_NAME[e.support]}» · 보스 평균 ${pct(e.f)} 깎음 · 클리어 ${pct(e.p)})</span></li>`;
    }).join("");
    const head = S.levels.map(l => `<th>${l}</th>`).join("");
    const sups = S.supports || ["none"];
    // 후보별 표: 지원이 여러 개면 팀마다 클리어 가능한 최고 단계가 가장 높은 지원 한 줄만(전체 비교는 아래 «지원별»)
    const topLv = r => { let m = -1; r.forEach((p, i) => { if (p >= S.passP) m = i; }); return m; };
    const rows = S.teams.map(t => S.growth.map(g => {
      const sup = sups.reduce((a, s) => { const ra = simRates(S, t, a, g), rs = simRates(S, t, s, g); return ra && rs && topLv(rs) > topLv(ra) ? s : a; }, sups[0]);
      return `<tr><td>${esc(t.names.join("·"))}${t.src === "community" ? " (커뮤니티 사례 근사)" : ""}</td><td>×${g}</td><td>${SUP_NAME[sup]}</td>${simRates(S, t, sup, g).map(p => `<td>${pct(p)}</td>`).join("")}</tr>`;
    }).join("")).join("");
    const gMid = S.growth.find(g => Number(g) === 2) || S.growth[S.growth.length - 1]; // 지원 비교는 기존 ×2 유지
    const supRows = S.teams.map(t => `<tr><td>${esc(t.names.join("·"))}</td>${sups.map(s => { const r = simRates(S, t, s, gMid); const m = r ? topLv(r) : -1; return `<td>${m < 0 ? "-" : m + "단계"}</td>`; }).join("")}</tr>`).join("");
    const supTab = sups.length > 1 ? `<details class="gd-simtab"><summary>알리시아 지원별 클리어 가능 최고 단계 (×${gMid})${setsUi(G)?' · 선택 효과 끔':''}</summary><div class="gd-scroll"><table><thead><tr><th>파티</th>${sups.map(s => `<th>${SUP_NAME[s]}</th>`).join("")}</tr></thead><tbody>${supRows}</tbody></table></div></details>` : "";
    return `<div class="gd-sim" data-k="gd-sim"><b>시뮬 추정: 깰 수 있는 최고 단계</b> ${EST} ${setsUi(G)?'<span class="mut">선택 효과 끔</span> ':''}<ul>${lines}</ul>
${ex ? `<b>기대 점수가 가장 큰 단계</b> ${EST} <span class="mut">${setsUi(G)?'선택 효과 끔 · ':''}졸개 2기 처치로 계산</span><ul>${ex}</ul>` : ""}
<div class="mut gd-small">${esc(S.basis)} · 오토 전투 기준 · 단계당 ${S.runs}판(표본이 작아 한 단계쯤은 오차) · 클리어율 ${pct(S.passP)} 이상을 «깰 수 있음»으로 봄 · 기대 점수 = 시뮬에서 보스를 깎은 평균 비율을 영상으로 확인한 점수식에 넣은 값(패배해도 깎은 만큼 받음). 점수식은 실제 플레이 1판으로 확인했지만 시뮬 결과는 아직 실제와 대조 중. 수동 조작(행동 게이지 조절·브레이크 타이밍)은 반영하지 않아 실제보다 낮게 나올 수 있음. 알리시아 지원은 게임 표 값으로 넣었고 일부 해석(발동 확률·경계값)은 추정임.</div>
${supTab}<details class="gd-simtab"><summary>후보별 단계 클리어율${setsUi(G)?' (선택 효과 끔)':''}</summary><div class="gd-scroll"><table><thead><tr><th>파티</th><th>육성</th><th>지원</th>${head}</tr></thead><tbody>${rows}</tbody></table></div></details></div>`;
  }
  function panelHtml(G, sel0, step, nowMs, esc) {
    const sel = normSel(G, sel0), ex = exStep(G);
    if(G.season.boss.engine==='client'){
      const st=G.steps.find(s=>s.step===step),pct=extraPct(G,sel.level,sel.tiers);
      return (G.season.start&&G.season.end&&G.season.settleEnd?seasonBox(G,nowMs,esc):
        `<div class="gd-head"><b>길드 방어전 · ${esc(G.season.label)}</b></div>`)+
        `<p class="mut">${esc(G.season.boss.name)} · ${st.ex?'EX 스테이지':'스테이지 '+st.step+'단계'} · 최대 ${st.turnLimit}턴 · ${st.waves.length}웨이브</p>`+
        (step===ex.step?overview(G,esc):'')+
        `<div data-k="gd-details"><details class="season-options" data-fold="gd-effects"><summary>단계별 보스 능력치·효과·지원</summary>`+
        (step===ex.step?selectBox(G,sel)+`<p>클리어 기준 점수 ${num(scoreAt(G,pct,1))}</p>`+levelTable(G,sel,esc):'')+
        (setsUi(G)?`<p>${esc(G.sets.note)}</p>`:'')+`<p>시즌 지원: ${(G.supports||[]).map(s=>esc(s.name)).join(' · ')}</p></details>`+
        `<details class="season-options" data-fold="gd-rules"><summary>전투·점수 자료</summary>${stepsTable(G,step,esc)}<p>${esc(G.score.note)}</p></details></div>`;
    }
    let html = seasonBox(G, nowMs, esc)+(step===ex.step?overview(G,esc):'');
    if(step!==ex.step)html+=`<p class="mut">${step}단계 · 별의 도전 없음. 편성 탐색은 EX(${ex.step}단계)를 선택해야 함.</p>`;
    html += `<div data-k="gd-details"><details class="season-options" data-fold="gd-effects"><summary>단계별 보스 능력치·효과·지원</summary><div class="gd-dev" data-k="gd-dev" role="note"><b>개발 중 · 테스트 중인 기능임</b><br>점수 계산과 고단계 수치는 확인되지 않았음.${simUi(G)?' 시뮬 추정은 실제 플레이와 대조하지 않았음.':''} 참고용으로만 활용.</div>`;
    if (step === ex.step) {
      const pct = extraPct(G, sel.level, sel.tiers), sc = score(G, pct), b = bestSelection(G), bsc = score(G, extraPct(G, b.level, b.tiers));
      const hyp = G.score.hypotheses.map(h => `${h.name} ${num(sc[h.id])}`).join(" · ");   // 보스를 다 깎았을 때 점수
      const isBest = sel.level === b.level && sel.tiers.every((t, i) => t === b.tiers[i]);
      html += `<div class="gd-best" data-k="gd-best"><b>최고 점수가 나오는 조합</b>: 별의 도전 ${b.level}단계${setsUi(G)?' + 선택 효과 끔':''}(추가 점수 ${extraPct(G, b.level, b.tiers)}%) → 보스를 다 깎으면 점수 ${rangeText(bsc)}<br>
<span class="mut">패배해도 보스를 깎은 비율만큼 보스 점수(최대 ${num(ex.bossKill)})를 받고, 추가 점수는 합계 전체에 곱해짐(실제 영상으로 확인). 그래서 못 깰 단계라도 높은 단계가 점수에 유리할 수 있음. 추천 파티는 단계와 관계없이 보스 속성·특징 기준임.${simUi(G)?' 단계별 기대 점수는 아래 «시뮬 추정»에서 확인.':''}</span></div>
${simBox(G, esc)}${selectBox(G, sel)}
<div class="gd-now" data-k="gd-now">고른 조합: 추가 점수 ${pct}% → 보스를 다 깎으면 <b>${rangeText(sc)}</b>${isBest ? " (최고 조합)" : ""}<br><span class="mut">${esc(hyp)} · ${esc(G.score.hypotheses.map(h => h.name + ": " + h.desc).join(" / "))}</span></div>
<div class="mut gd-small">${esc(G.score.note)}${setsUi(G)?' '+esc(G.sets.note):''}</div>${levelTable(G, sel, esc)}`;
    } else {
      const s = G.steps.find(x => x.step === step);
      const total = s.base + G.stepsMeta.minions * s.kill + s.bossKill;
      html += `<div class="gd-now" data-k="gd-now">${step}단계에는 별의 도전이 없음. 기본 ${num(s.base)} + 졸개 처치 ${num(G.stepsMeta.minions * s.kill)} + 보스 처치 ${num(s.bossKill)} = <b>${num(total)}</b><br><span class="mut">최고 점수는 EX(${ex.step}단계)에서 나옴. 스테이지에서 EX를 선택해야 함.</span></div>`;
    }
    html += '</details><details class="season-options" data-fold="gd-rules"><summary>입장 규칙·점수 계산 방식·출처</summary>'+rulesBox(G, esc) + stepsTable(G, step, esc);
    const b = G.exBoss;
    html += `<div class="mut gd-small" data-k="gd-boss">EX 보스 기준값(별의 도전 전) 생명력 ${num(b.hp)} · 속도 ${b.speed} · 공격 ${num(b.atk)} · 방어 ${num(b.def)} · 슈퍼아머 ${b.superArmor} ${EST}</div>`;
    const src = Object.values(G.sources).filter(s => s.url).map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a>`).join("<br>");
    html += `<details class="gd-comm" data-k="gd-comm"><summary>커뮤니티 정보 <span class="gd-est">추정·낮은 신뢰</span></summary><ul>${G.community.items.map(i => `<li>${esc(i.text)}</li>`).join("")}</ul><div class="mut gd-small">${esc(G.community.note)}</div></details>
<details class="gd-src"><summary>출처</summary><div class="gd-small">${src}</div></details>`;
    return html+'</details></div>';
  }
  const api = {gameDay, num, parseTime, seasonState, baseTotal, extraPct, score, scoreAt, bossPoints, progParts, scoreFromProg, bestSelection, normSel, supportChoices, battleOptions, rangeText, levelEffects, simBest, simExpect, simBox, panelHtml};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.GuildView = api;
})(typeof window !== "undefined" ? window : globalThis);
