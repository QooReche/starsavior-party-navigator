// 코스모 게이트 «3보스 최고 점수 편성 찾기» 순수 로직(저장소·화면 접근 없음). 후보 풀·조합·작업 분배·작업자 실행은 guild_search.js 를 그대로 쓴다.
// 규칙: 같은 구원자를 여러 보스에 쓰지 못한다(3팀 12명 전부 다름). 순위는 평균 점수(기본) 또는 상위 점수. 협공 제외는 코스모에 없어 적용하지 않는다.
// 시즌 값(풀 크기·판 수·K 등)은 data/cosmo_raid.json 의 search. 점수는 시뮬 쪽(battlesim/web.py cosmo_summary)이 판마다 점수식에 넣어 요약값으로 돌려준다.
(function (root) {
  "use strict";
  const GS = typeof require !== "undefined" ? require("./guild_search.js") : root.GuildSearch;
  const TEAM = 4, BOSSES = 3, EPS = 1e-9;

  const MODES = {mean: "평균 점수", top: "상위 점수"};
  // 순위 값: 기준 점수 -> 반대 점수 -> 클리어율. 평균 진행도 같은 중간값을 비선형 식에 넣지 않고 작업자가 낸 점수 요약을 그대로 쓴다
  const metric = (st, mode) => mode === "top" ? st.top : st.mean;
  const other = (st, mode) => mode === "top" ? st.mean : st.top;
  const byRank = mode => (a, b) => metric(b.st, mode) - metric(a.st, mode) || other(b.st, mode) - other(a.st, mode) || (b.st.clear || 0) - (a.st.clear || 0);
  const idOf = keys => keys.slice().sort().join("+");

  const jobKey = (boss, keys, level) => [boss, idOf(keys), level].join("|");

  // 보스 하나의 작업 목록. 구원자 칸 순서·능력치는 guild_search.party 와 같다(리더 0번)
  function bossJobs(S, boss, level, list, results, cls) {
    return list.map(keys => {
      const p = GS.party(keys, results, cls);
      return {key: jobKey(boss, keys, level), boss, keys, order: p.order, level, party: p.spec,
        options: {cosmo_raid: {boss, step: 3, level}, cosmo_top_q: S.topQ}};
    });
  }

  // 작업자 결과 -> 순위 항목 [{keys, order, boss, st:{mean,top,clear,frac,n}}], 큰 순(같으면 키 순). 요약이 없는 결과(작업자 오류 등)는 뺀다
  function pickTop(jobs, res, mode, n) {
    const rows = jobs.filter(j => res[j.key] && res[j.key].cosmo).map(j => ({keys: j.keys, order: j.order, boss: j.boss, st: res[j.key].cosmo}));
    const cmp = byRank(mode);
    rows.sort((a, b) => cmp(a, b) || (idOf(a.keys) < idOf(b.keys) ? -1 : 1));
    return n == null ? rows : rows.slice(0, n);
  }

  // 1단계 -> 2단계로 넘길 상위 n 팀. 그냥 상위 n 개만 자르면 «1위 구원자 X 가 든 팀»만 남아 보스 3명이 모두 X 를 원할 때 겹치지 않는 삼중이 없거나 나빠진다.
  // 그래서 절반(올림)은 순위대로, 나머지는 구원자마다 «그 구원자가 든 가장 좋은 팀»을 돌려 가며 채운다(다양성 확보). n 이상이면 전부.
  function pickDiverse(jobs, res, mode, n) {
    const all = pickTop(jobs, res, mode);
    if (all.length <= n) return all;
    const head = Math.ceil(n / 2), out = all.slice(0, head).map((e, i) => i), used = new Set(out);
    const queues = new Map();
    all.forEach((e, i) => { if (i >= head) e.keys.forEach(k => { if (!queues.has(k)) queues.set(k, {list: [], p: 0}); queues.get(k).list.push(i); }); });
    const qs = [...queues.values()];
    while (out.length < n) {
      let added = false;
      for (const q of qs) {
        while (q.p < q.list.length && used.has(q.list[q.p])) q.p++;
        if (q.p < q.list.length) { used.add(q.list[q.p]); out.push(q.list[q.p]); added = true; if (out.length >= n) break; }
      }
      if (!added) break;
    }
    return out.sort((a, b) => a - b).map(i => all[i]);
  }

  // 겹치지 않는 (A,B,C) 삼중 중 합이 큰 순 n 개(분기한정). lists = 보스별 항목 배열(각각 pickTop 처럼 점수 큰 순 정렬), 항목 = {keys, score}
  // 같은 합이면 세 팀 id 문자열이 작은 순. 구원자는 비트 마스크(30비트 단위)로 겹침을 확인한다.
  function bestTriples(lists, n) {
    if (lists.length !== BOSSES || lists.some(l => !l.length)) return [];
    const index = new Map();
    lists.forEach(l => l.forEach(e => e.keys.forEach(k => { if (!index.has(k)) index.set(k, index.size); })));
    const W = Math.max(1, Math.ceil(index.size / 30));
    const mk = e => { const m = new Array(W).fill(0); e.keys.forEach(k => { const i = index.get(k); m[(i / 30) | 0] |= 1 << (i % 30); }); return m; };
    const L = lists.map(l => l.map(e => ({e, m: mk(e), id: idOf(e.keys)})));
    const top = [], idOfT = t => t.map(x => x.id).join("/");
    const better = (a, b) => { const ia = idOfT(a.t), ib = idOfT(b.t); return a.sum - b.sum || (ia < ib ? 1 : ia > ib ? -1 : 0); };   // >0 이면 a 가 더 좋음(합이 크거나, 같으면 id 가 작음)
    const floor = () => top.length < n ? -Infinity : top[top.length - 1].sum;
    const hit = (x, y) => { for (let w = 0; w < W; w++) if (x[w] & y[w]) return true; return false; };
    const or = (x, y) => x.map((v, w) => v | y[w]);
    function put(sum, t) {
      const c = {sum, t};
      let i = top.length;
      while (i > 0 && better(c, top[i - 1]) > 0) i--;
      top.splice(i, 0, c);
      if (top.length > n) top.pop();
    }
    const c0 = L[2][0].e.score, b0 = L[1][0].e.score;
    for (const a of L[0]) {
      if (a.e.score + b0 + c0 < floor()) break;
      for (const b of L[1]) {
        if (a.e.score + b.e.score + c0 < floor()) break;
        if (hit(a.m, b.m)) continue;
        const ab = or(a.m, b.m), base = a.e.score + b.e.score;
        for (const c of L[2]) {
          if (base + c.e.score < floor()) break;
          if (hit(ab, c.m)) continue;
          put(base + c.e.score, [a, b, c].map(x => ({id: x.id, e: x.e})));
        }
      }
    }
    return top.map(x => ({sum: x.sum, teams: x.t.map(y => y.e)}));
  }

  // 마지막 재시뮬 작업: 삼중에 든 (보스, 조합) 중복 제거
  function finalJobs(S, triples, bosses, level, results, cls) {
    const seen = new Map();
    triples.forEach(t => t.teams.forEach((e, i) => { const k = jobKey(bosses[i], e.keys, level); if (!seen.has(k)) seen.set(k, e.keys); }));
    const jobs = [];
    bosses.forEach(b => {
      const list = [];
      seen.forEach((keys, k) => { if (k.startsWith(b + "|")) list.push(keys); });
      jobs.push(...bossJobs(S, b, level, list, results, cls));
    });
    return jobs;
  }

  // 마지막 재시뮬 결과로 삼중을 다시 매김. 합 = 세 팀 기준 점수의 합. 결과가 빠진 삼중은 뺀다
  function finalRank(triples, bosses, level, res, mode, show) {
    const out = [];
    for (const t of triples) {
      const teams = t.teams.map((e, i) => { const r = res[jobKey(bosses[i], e.keys, level)]; return r && r.cosmo ? {boss: bosses[i], keys: e.keys, order: e.order, st: r.cosmo} : null; });
      if (teams.some(x => !x)) continue;
      out.push({sum: teams.reduce((a, x) => a + metric(x.st, mode), 0), sum2: teams.reduce((a, x) => a + other(x.st, mode), 0), teams});
    }
    out.sort((a, b) => b.sum - a.sum || b.sum2 - a.sum2 || (a.teams.map(x => idOf(x.keys)).join() < b.teams.map(x => idOf(x.keys)).join() ? -1 : 1));
    return out.slice(0, show);
  }

  // 전체 흐름. 1) 보스별 전 조합 짧게 -> 2) 보스별 상위 K 를 더 정확히 -> 3) 겹침 없는 삼중 최대 합 -> 4) 상위 삼중의 팀을 길게 재시뮬
  // cx = {S, bosses:[boss key 3개], level, mode, results, roster, makeWorker, workers, stage, base, onPhase(msg,total), onProgress(done,total), onHandle(handle), stale()}
  async function search(cx) {
    const {S, bosses, level, mode, results, roster} = cx;
    if (bosses.length !== BOSSES) throw new Error("보스는 3명이어야 합니다");
    const rows = GS.pool(Object.assign({}, S, {banCoop: false, excluded: []}), results, roster);
    if (rows.length < TEAM * BOSSES) throw new Error("편성할 수 있는 구원자가 부족합니다(3팀 12명 필요, 내 정보에 육성된 구원자 12명 이상)");
    const list = GS.combos(S, rows), cls = Object.fromEntries(roster.map(s => [s.key, s.cls]));
    if (!list.length) throw new Error("조건에 맞는 4인 조합이 없습니다");
    const run = async (jobs, runs, seed, msg) => {
      if (cx.onPhase) cx.onPhase(msg, jobs.length);
      const h = GS.runPhase({makeWorker: cx.makeWorker, jobs, workers: cx.workers, runs, seed, stage: cx.stage, base: cx.base, onProgress: cx.onProgress});
      if (cx.onHandle) cx.onHandle(h);
      return h.promise;
    };
    const stale = () => cx.stale && cx.stale();
    const jobsA = [].concat(...bosses.map(b => bossJobs(S, b, level, list, results, cls)));
    const resA = await run(jobsA, S.screen.runs, 1, `1단계: 보스 3명 × 조합 ${list.length}개를 훑어보는 중(처음 한 번은 계산 엔진을 내려받느라 1~3분 더 걸립니다)`);
    if (stale()) return null;
    const keep = bosses.map(b => pickDiverse(jobsA.filter(j => j.boss === b), resA, mode, S.rerank.keep));
    const jobsB = [].concat(...keep.map((k, i) => bossJobs(S, bosses[i], level, k.map(e => e.keys), results, cls)));
    const resB = await run(jobsB, S.rerank.runs, 3, `2단계: 보스별 상위 ${S.rerank.keep}팀을 더 정확히 확인 중`);
    if (stale()) return null;
    const lists = bosses.map(b => pickTop(jobsB.filter(j => j.boss === b), resB, mode).map(e => Object.assign({score: metric(e.st, mode)}, e)));
    const triples = bestTriples(lists, S.combine.topTriples);
    if (!triples.length) throw new Error("겹치지 않는 3팀을 찾지 못했습니다(후보가 서로 겹침). 내 정보에 육성된 구원자를 늘려 보세요");
    const jobsC = finalJobs(S, triples, bosses, level, results, cls);
    const resC = await run(jobsC, S.final.runs, 2, `3단계: 합이 큰 ${triples.length}개 편성의 팀 ${jobsC.length}개를 ${S.final.runs}판씩 확인 중`);
    if (stale()) return null;
    return {rows: finalRank(triples, bosses, level, resC, mode, S.combine.show), pool: rows.length, combos: list.length, keep: S.rerank.keep, triples: triples.length, runs: S.final.runs, level, mode, bosses: bosses.slice()};
  }

  const num = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const pct = x => Math.round((x || 0) * 100) + "%";
  // 화면 조각. st = {phase: idle|run|done|err, msg, done, total, rows, level, mode, bosses, ...}, cx = {hasInfo, label(key), esc, bossName(key), levelMax, level, mode}
  function table(r, mode, cx) {
    const esc = cx.esc;
    const body = r.teams.map(t => `<tr><td>${esc(cx.bossName(t.boss))}</td><td>${t.order.map(k => esc(cx.label(k))).join("<br>")}</td><td><b>${num(metric(t.st, mode))}</b></td><td>${num(other(t.st, mode))}</td><td>${pct(t.st.clear)}</td><td>${pct(t.st.frac)}</td></tr>`).join("");
    return `<div class="gd-scroll"><table data-k="cs-table"><thead><tr><th>보스</th><th>편성(앞열 → 뒤열, 첫 구원자가 리더)</th><th>${MODES[mode]}(순위 기준)</th><th>${MODES[mode === "top" ? "mean" : "top"]}</th><th>클리어율</th><th>보스 깎음</th></tr></thead><tbody>${body}<tr><td colspan="2"><b>합계</b></td><td colspan="4"><b data-k="cs-sum">${num(r.sum)}</b></td></tr></tbody></table></div>`;
  }
  function html(st, cx) {
    const esc = cx.esc;
    const head = '<b>3보스 최고 점수 편성 찾기</b> <span class="gd-est" title="시뮬 기반 추정입니다">추정</span>';
    const warn = '<div class="mut gd-small">오토 전투 기준 · 내 정보의 실제 최종 능력치 · 같은 구원자를 여러 보스에 쓰지 않는 3팀(12명) · 점수 합산식은 서버 계산이라 추정이고 시뮬 전체가 아직 실제 플레이와 충분히 대조되지 않았습니다(참고용). 협공 제외는 적용하지 않습니다. 시즌이 바뀌면 새 시즌 값이 반영된 뒤에 쓰세요.</div>';
    if (!cx.hasInfo) return `<div class="gd-search" data-k="cs-search">${head}<div class="mut gd-small">먼저 «내 계정 정보 불러오기»로 내 구원자를 불러오세요. 불러온 구원자 중에서 3보스 점수 합이 가장 큰 3팀을 찾습니다.</div></div>`;
    const lv = Array.from({length: cx.levelMax + 1}, (_, i) => `<option value="${i}"${i === cx.level ? " selected" : ""}>${i === 0 ? "레벨 0(없음)" : "레벨 " + i}</option>`).join("");
    const md = Object.entries(MODES).map(([k, v]) => `<option value="${k}"${k === cx.mode ? " selected" : ""}>${v}</option>`).join("");
    const opt = `<div class="gd-small"><label>난이도 <select data-cs="level">${lv}</select></label> <label>순위 기준 <select data-cs="mode">${md}</select></label> <span class="mut">— 3단계(Step 3) 기준. 상위 점수 = 판별 점수 상위 20%의 평균</span></div>`;
    const btn = label => `<button type="button" data-cs="start">${label}</button>`;
    let body;
    if (st.phase === "run") body = `<div data-k="cs-progress">${esc(st.msg || "")}${st.total ? ` · ${st.done}/${st.total}` : ""} <button type="button" class="sec" data-cs="cancel">취소</button></div>`;
    else if (st.phase === "err") body = `${opt}<div class="bad" data-k="cs-err">찾지 못했습니다: ${esc(st.msg || "")}</div>${btn("다시 시도")}`;
    else if (st.phase === "done") {
      const stale = st.level !== cx.level || st.mode !== cx.mode ? '<div class="gd-warn" data-k="cs-stale">위에서 고른 난이도·순위 기준이 바뀌었습니다. 아래 결과는 이전 선택 기준이니 다시 찾아 주세요.</div>' : "";
      const rows = st.rows || [];
      const first = rows.length ? `<div data-k="cs-best">${table(rows[0], st.mode, cx)}</div>` : '<div class="mut">결과 없음</div>';
      const rest = rows.slice(1).map((r, i) => `<details class="gd-small"><summary>${i + 2}위 · 합계 ${num(r.sum)}</summary>${table(r, st.mode, cx)}</details>`).join("");
      body = `${stale}${opt}${first}${rest}<div class="mut gd-small">후보 ${st.pool}명 → 보스마다 조합 ${st.combos}개를 짧게 훑고, 보스별 상위 ${st.keep}팀을 더 정확히 본 뒤, 겹치지 않는 3팀 중 합이 큰 ${st.triples}개 편성의 팀을 ${st.runs}판씩 다시 돌린 값입니다(표본이 작아 수천 점은 오차). ${MODES[st.mode]} 기준 합계가 가장 큰 순입니다.</div>${btn("다시 찾기")}`;
    } else body = `${opt}${btn("3보스 최고 점수 편성 찾기")}<span class="mut gd-small"> 몇 분 걸릴 수 있어요. 탭을 연 채로 기다려 주세요.</span>`;
    return `<div class="gd-search" data-k="cs-search">${head}${body}${warn}</div>`;
  }

  const api = {MODES, metric, idOf, jobKey, bossJobs, pickTop, pickDiverse, bestTriples, finalJobs, finalRank, search, html, table};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.CosmoSearch = api;
})(typeof window !== "undefined" ? window : globalThis);
