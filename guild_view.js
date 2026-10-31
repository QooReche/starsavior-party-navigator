// 길드 방어전 안내 패널(순수 함수: 저장소·네트워크 접근 없음). 규칙은 guild_defense.py 와 같다(tests/guild_defense_test.py 가 일치 확인).
(function (root) {
  "use strict";
  const MAX_TIER = 3;
  const num = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  function parseTime(s) { return Date.parse(/T/.test(s) ? s : s + "T00:00:00+09:00"); }
  function md(s) { const d = new Date(parseTime(s) + 9 * 3600 * 1000); return String(d.getUTCMonth() + 1).padStart(2, "0") + "/" + String(d.getUTCDate()).padStart(2, "0"); }
  // state: upcoming / active / settling / ended, needsUpdate = 시즌 종료 시각이 지남(갱신 대기)
  function seasonState(season, nowMs) {
    const s = parseTime(season.start), e = parseTime(season.end), d = parseTime(season.settleEnd);
    const state = nowMs < s ? "upcoming" : nowMs < e ? "active" : nowMs < d ? "settling" : "ended";
    return {state, needsUpdate: nowMs >= e};
  }
  function exStep(G) { return G.steps.find(s => s.ex); }
  function baseTotal(G) { const ex = exStep(G); return ex.base + G.stepsMeta.minions * ex.kill + ex.bossKill; }
  function extraPct(G, level, tiers) {
    let pct = level ? G.challenge.levels[level - 1].score : 0;
    G.sets.items.forEach((it, i) => { const t = (tiers || [])[i] || 0; if (t) pct += it.tiers[t - 1].add; });
    return pct;
  }
  function score(G, pct) {
    const ex = exStep(G), total = baseTotal(G), out = {};
    for (const h of G.score.hypotheses)
      out[h.id] = Math.round(h.bossExcluded ? (total - ex.bossKill) * (100 + pct) / 100 + ex.bossKill : total * (100 + pct) / 100);
    return out;
  }
  function bestSelection(G) { return {level: G.challenge.levels.length, tiers: G.sets.items.map(() => MAX_TIER)}; }
  function normSel(G, sel) {
    const b = bestSelection(G);
    const level = Number.isInteger(sel && sel.level) && sel.level >= 0 && sel.level <= b.level ? sel.level : b.level;
    const tiers = G.sets.items.map((_, i) => { const t = sel && sel.tiers && sel.tiers[i]; return Number.isInteger(t) && t >= 0 && t <= MAX_TIER ? t : b.tiers[i]; });
    return {level, tiers};
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
  const EST = '<span class="gd-est" title="공식 수치가 아니라 계산·해석으로 얻은 값입니다">추정</span>';

  function seasonBox(G, nowMs, esc) {
    const st = seasonState(G.season, nowMs), s = G.season;
    const stale = st.needsUpdate
      ? `<div class="gd-warn" data-k="gd-stale"><b>갱신 대기</b> · 이 시즌(${esc(G.tab)})은 ${md(s.end)} 04:00에 끝났습니다. 아래 수치는 지난 시즌 기준이며 새 시즌에는 달라질 수 있습니다.</div>` : "";
    const dev = `<div class="gd-dev" data-k="gd-dev" role="note"><b>⚠ 개발 중 · 테스트 중인 기능입니다</b><br>점수 계산과 고단계 수치는 확인되지 않았고, 시뮬 추정은 실제 플레이와 대조하지 않았습니다. 참고용으로만 봐 주세요.</div>`;
    return `${dev}<div class="gd-head"><b>${esc(G.title)}</b> <span class="gd-state ${st.state}">${STATE_TEXT[st.state]}</span><span class="mut"> · 이 시즌 정보는 ${md(G.asOf)} 기준</span></div>${stale}
<div class="mut gd-small">진행 ${md(s.start)} ~ ${md(s.end)} 04:00 · 결산 ~${md(s.settleEnd)} 04:00 · 보스 ${esc(s.boss.name)}(${EL[s.boss.element] || ""} ${esc(s.boss.role)})</div>`;
  }
  function rulesBox(G, esc) {
    const r = G.rules;
    return `<ul class="gd-rules" data-k="gd-rules"><li>한 판 최대 ${r.turnLimit}턴 · 파티 ${r.partyCount}개(${r.partySize}명)</li>
<li><b>${esc(r.reuse)}</b> — 같은 구원자를 여러 번 쓸 수 없으니 날마다 쓸 구원자를 나눠 정하세요</li>
<li>${esc(r.abandon)}</li>
<li>EX는 ${r.entryDaysEx.join("·")}요일만 입장 · 입장 재화 ${r.entryItemEx}개${r.skipEx ? "" : " · 전투 건너뛰기 불가"}</li></ul>`;
  }
  function stepsTable(G, cur, esc) {
    const rows = G.steps.slice().reverse().map(s => {
      const total = s.base + G.stepsMeta.minions * s.kill + s.bossKill;
      return `<tr${s.step === cur ? ' class="cur"' : ""}><td>${s.step}단계${s.ex ? " EX" : ""}</td><td>${num(s.power)}</td><td>${num(total)}</td></tr>`;
    }).join("");
    return `<details class="gd-steps"><summary>단계별 기본 점수</summary><div class="gd-scroll"><table><thead><tr><th>단계</th><th>권장 전투력</th><th>기본+졸개+보스 처치</th></tr></thead><tbody>${rows}</tbody></table></div><div class="mut gd-small">${esc(G.stepsMeta.minionsNote)}</div></details>`;
  }
  function levelTable(G, sel, esc) {
    const rows = G.challenge.levels.map(lv => {
      const sc = score(G, extraPct(G, lv.level, [0, 0, 0, 0]));
      const big = lv.level >= 7;
      const tip = big ? ` title="공지 표(옛 값): 공격 +${lv.noticeAtk}%, 생명력·방어 +${lv.noticeHp}%"` : "";
      return `<tr${lv.level === sel.level ? ' class="cur"' : ""}><td>${lv.level}</td><td${tip}>공격 +${lv.atk}% · 생명력·방어 +${lv.hp}%</td><td>+${lv.score}%</td><td>${rangeText(sc)}</td><td class="gd-fx">${levelEffects(G, lv).map(esc).join("<br>")}</td></tr>`;
    }).join("");
    return `<div class="gd-scroll"><table class="gd-levels" data-k="gd-levels"><thead><tr><th>단계</th><th>보스 능력치</th><th>추가 점수</th><th>점수 ${EST}</th><th>누적 효과</th></tr></thead><tbody>${rows}</tbody></table></div>
<div class="mut gd-small">${esc(G.challenge.note)} ${esc(G.challenge.statNote)}</div>`;
  }
  function selectBox(G, sel) {
    const opt = (n, cur, label) => `<option value="${n}"${n === cur ? " selected" : ""}>${label}</option>`;
    const lv = `<label>별의 도전<select data-g="level">${opt(0, sel.level, "없음")}${G.challenge.levels.map(l => opt(l.level, sel.level, l.level + "단계")).join("")}</select></label>`;
    const sets = G.sets.items.map((it, i) => `<label>${it.name}<select data-g="set" data-i="${i}">${opt(0, sel.tiers[i], "끔")}${it.tiers.map((t, j) => opt(j + 1, sel.tiers[i], (j + 1) + "단계 +" + t.add + "% · " + t.text)).join("")}</select></label>`).join("");
    return `<div class="gd-sel">${lv}${sets}<button type="button" class="sec" data-g="best">최고 점수 조합으로</button></div>`;
  }
  // 시뮬 추정(tools/build_guild_sim.py → G.sim): 육성 배수마다 클리어율 passP 이상인 최고 단계와 그 단계 점수 범위(선택 효과 끔)
  const SUP_NAME = {none: "지원 안 고름", gust: "격돌의 돌풍", focus: "날카로운 집중력", strike: "강인한 타격", mountain: "태산의 의지", fire: "불의 고동"};
  function simBest(S, g) { const b = S && S.summary && S.summary[String(g)]; return b ? {level: b.level, team: b.team, p: b.p, support: b.support || "none"} : null; }
  // 팀·지원별 클리어율 행(구버전 자료는 rates 만 있음 = 지원 안 고름)
  function simRates(S, t, sup, g) { const bs = t.bySupport; const r = bs ? (bs[sup] || {})[String(g)] : (sup === "none" ? t.rates[String(g)] : null); return r || null; }
  // 기대 점수 최대 조합: 클리어율 × 점수(실패하면 0점 가정 — 실패 시 점수 인정 여부는 미확인). 가설 A/B 평균이 가장 큰 조합을 고르고, 두 가설 값을 범위로 보여 줌
  function simExpect(G, S, g) {
    let best = null;
    S.teams.forEach((t, ti) => (S.supports || ["none"]).forEach(sup => {
      const r = simRates(S, t, sup, g);
      if (!r) return;
      S.levels.forEach((lv, i) => {
        const sc = score(G, extraPct(G, lv, [0, 0, 0, 0])), e = {};
        for (const k of Object.keys(sc)) e[k] = Math.round(sc[k] * r[i]);
        const m = Object.values(e).reduce((a, b) => a + b, 0) / Object.keys(e).length;
        if (r[i] > 0 && (!best || m > best.m)) best = {m, team: ti, support: sup, level: lv, p: r[i], e};
      });
    }));
    return best;
  }
  const pct = p => Math.round(p * 100) + "%";
  function simBox(G, esc) {
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
      return `<li>×${g}: 별의 도전 <b>${e.level}단계</b> · 기대 점수 <b>${rangeText(e.e)}</b> <span class="mut">(${esc(t.names.join("·"))} · «${SUP_NAME[e.support]}» · 클리어 ${pct(e.p)})</span></li>`;
    }).join("");
    const head = S.levels.map(l => `<th>${l}</th>`).join("");
    const sups = S.supports || ["none"];
    // 후보별 표: 지원이 여러 개면 팀마다 클리어 가능한 최고 단계가 가장 높은 지원 한 줄만(전체 비교는 아래 «지원별»)
    const topLv = r => { let m = -1; r.forEach((p, i) => { if (p >= S.passP) m = i; }); return m; };
    const rows = S.teams.map(t => S.growth.map(g => {
      const sup = sups.reduce((a, s) => { const ra = simRates(S, t, a, g), rs = simRates(S, t, s, g); return ra && rs && topLv(rs) > topLv(ra) ? s : a; }, sups[0]);
      return `<tr><td>${esc(t.names.join("·"))}${t.src === "community" ? " (커뮤니티 사례 근사)" : ""}</td><td>×${g}</td><td>${SUP_NAME[sup]}</td>${simRates(S, t, sup, g).map(p => `<td>${pct(p)}</td>`).join("")}</tr>`;
    }).join("")).join("");
    const gMid = S.growth[S.growth.length - 1];
    const supRows = S.teams.map(t => `<tr><td>${esc(t.names.join("·"))}</td>${sups.map(s => { const r = simRates(S, t, s, gMid); const m = r ? topLv(r) : -1; return `<td>${m < 0 ? "-" : m + "단계"}</td>`; }).join("")}</tr>`).join("");
    const supTab = sups.length > 1 ? `<details class="gd-simtab"><summary>알리시아 지원별 클리어 가능 최고 단계 (×${gMid})</summary><div class="gd-scroll"><table><thead><tr><th>파티</th>${sups.map(s => `<th>${SUP_NAME[s]}</th>`).join("")}</tr></thead><tbody>${supRows}</tbody></table></div></details>` : "";
    return `<div class="gd-sim" data-k="gd-sim"><b>시뮬 추정: 깰 수 있는 최고 단계</b> ${EST}<ul>${lines}</ul>
${ex ? `<b>기대 점수가 가장 큰 단계</b> ${EST}<ul>${ex}</ul>` : ""}
<div class="mut gd-small">${esc(S.basis)} · 오토 전투 기준 · 단계당 ${S.runs}판(표본이 작아 한 단계쯤은 오차) · 클리어율 ${pct(S.passP)} 이상을 «깰 수 있음»으로 봄 · 점수는 가설 A/B 범위(선택 효과 끔) · 기대 점수는 «클리어율 × 점수»이고 실패하면 0점으로 계산(실패 시 점수 인정 여부는 확인 안 됨). 실제 플레이·점수와 대조하지 않았습니다. 수동 조작(행동 게이지 조절·브레이크 타이밍)은 반영하지 않아 실제보다 낮게 나올 수 있습니다. 알리시아 지원은 게임 표 값으로 넣었고 일부 해석(발동 확률·경계값)은 추정입니다.</div>
${supTab}<details class="gd-simtab"><summary>후보별 단계 클리어율</summary><div class="gd-scroll"><table><thead><tr><th>파티</th><th>육성</th><th>지원</th>${head}</tr></thead><tbody>${rows}</tbody></table></div></details></div>`;
  }
  function panelHtml(G, sel0, step, nowMs, esc) {
    const sel = normSel(G, sel0), ex = exStep(G);
    let html = seasonBox(G, nowMs, esc);
    if (step === ex.step) {
      const pct = extraPct(G, sel.level, sel.tiers), sc = score(G, pct), b = bestSelection(G), bsc = score(G, extraPct(G, b.level, b.tiers));
      const hyp = G.score.hypotheses.map(h => `${h.name} ${num(sc[h.id])}`).join(" · ");
      const isBest = sel.level === b.level && sel.tiers.every((t, i) => t === b.tiers[i]);
      html += `<div class="gd-best" data-k="gd-best"><b>최고 점수가 나오는 조합</b>: 별의 도전 ${b.level}단계 + 선택 효과 모두 최대 단계(추가 점수 ${extraPct(G, b.level, b.tiers)}%) → 점수 ${rangeText(bsc)} ${EST}<br>
<span class="mut">단, 보스를 쓰러뜨려야 보스 처치 점수(${num(ex.bossKill)})를 받습니다. 못 깨는 단계라면 깰 수 있는 가장 높은 단계가 최선입니다. 추천 파티는 단계와 관계없이 보스 속성·특징 기준입니다. 단계별 클리어 가능성은 아래 «시뮬 추정»을 보세요.</span></div>
${simBox(G, esc)}${selectBox(G, sel)}
<div class="gd-now" data-k="gd-now">고른 조합: 추가 점수 ${pct}% → <b>${rangeText(sc)}</b> ${EST}${isBest ? " (최고 조합)" : ""}<br><span class="mut">${esc(hyp)} · ${esc(G.score.hypotheses.map(h => h.name + ": " + h.desc).join(" / "))}</span></div>
<div class="mut gd-small">${esc(G.score.note)} ${esc(G.sets.note)}</div>${levelTable(G, sel, esc)}`;
    } else {
      const s = G.steps.find(x => x.step === step);
      const total = s.base + G.stepsMeta.minions * s.kill + s.bossKill;
      html += `<div class="gd-now" data-k="gd-now">${step}단계에는 별의 도전이 없습니다. 기본 ${num(s.base)} + 졸개 처치 ${num(G.stepsMeta.minions * s.kill)} + 보스 처치 ${num(s.bossKill)} = <b>${num(total)}</b><br><span class="mut">최고 점수는 EX(${ex.step}단계)에서 나옵니다. 스테이지에서 EX를 고르세요.</span></div>`;
    }
    html += rulesBox(G, esc) + stepsTable(G, step, esc);
    const b = G.exBoss;
    html += `<div class="mut gd-small" data-k="gd-boss">EX 보스 기준값(별의 도전 전) 생명력 ${num(b.hp)} · 속도 ${b.speed} · 공격 ${num(b.atk)} · 방어 ${num(b.def)} · 슈퍼아머 ${b.superArmor} ${EST}</div>`;
    const src = Object.values(G.sources).filter(s => s.url).map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a>`).join("<br>");
    html += `<details class="gd-comm" data-k="gd-comm"><summary>커뮤니티 정보 <span class="gd-est">추정·낮은 신뢰</span></summary><ul>${G.community.items.map(i => `<li>${esc(i.text)}</li>`).join("")}</ul><div class="mut gd-small">${esc(G.community.note)}</div></details>
<details class="gd-src"><summary>출처</summary><div class="gd-small">${src}</div></details>`;
    return html;
  }
  const api = {num, parseTime, seasonState, baseTotal, extraPct, score, bestSelection, normSel, rangeText, levelEffects, simBest, simExpect, simBox, panelHtml};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.GuildView = api;
})(typeof window !== "undefined" ? window : globalThis);
