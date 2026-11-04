// 길드 방어전 «내 정보로 최고 점수 편성 찾기». 후보 선정·조합·작업 배분·기대 점수 순위만 담은 순수 로직(저장소·화면 접근 없음).
// 시즌이 바뀌면 보스·규칙이 달라지므로 시즌별 값은 data/guild_defense.json 의 search 에 둔다(풀 크기·역할 최소 수·예선/본선 판수·후보 단계·지원).
// 시뮬 자체는 battlesim(guild 옵션)이 하고, 이 파일은 «어떤 팀을 어떤 조건으로 돌릴지»와 «결과를 어떻게 순위 매길지»만 정한다.
(function (root) {
  "use strict";
  const FRONT = ["디펜더", "서포터"];

  // 후보 풀: 내 최종 전투력이 최고의 minPowerRatio 배 이상인 구원자(최대 poolSize 명) + 역할별 최소 인원(minRole: 서포터·디펜더는 전투력이 낮아도 역할 때문에 쓰이므로 따로 보충). rows = [{key, cls, power}]
  function pool(S, results, roster) {
    const ban = new Set(S.banCoop === false ? [] : (S.excluded || []));
    const rows = roster.filter(s => results[s.key] && results[s.key].power > 0 && !ban.has(s.key)).map(s => ({key: s.key, cls: s.cls, power: results[s.key].power}));
    rows.sort((a, b) => b.power - a.power || (a.key < b.key ? -1 : 1));
    const floor = rows.length ? rows[0].power * (S.minPowerRatio || 0) : 0;
    const keep = new Set(rows.filter(r => r.power >= floor).slice(0, S.poolSize).map(r => r.key));
    for (const [cls, n] of Object.entries(S.minRole || {})) {
      let have = rows.filter(r => r.cls === cls && keep.has(r.key)).length;
      for (const r of rows) { if (have >= n) break; if (r.cls === cls && !keep.has(r.key)) { keep.add(r.key); have++; } }
    }
    return rows.filter(r => keep.has(r.key));
  }

  // 4인 조합 전수. 규칙: 앞열 역할(디펜더·서포터) 최소 minFront 명, 딜러(앞열 역할 아님) 최소 minDealer 명
  function combos(S, rows) {
    const out = [], n = rows.length, mf = S.minFront || 0, md = S.minDealer || 0;
    for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) for (let c = b + 1; c < n; c++) for (let d = c + 1; d < n; d++) {
      const t = [rows[a], rows[b], rows[c], rows[d]], fr = t.filter(x => FRONT.includes(x.cls)).length;
      if (fr >= mf && 4 - fr >= md) out.push(t.map(x => x.key));
    }
    return out;
  }

  // 시뮬 칸 순서(앞열 역할 먼저, 같으면 전투력 큰 순) + 내 최종 능력치. 리더는 0번(오프라인 탐색과 같은 규칙)
  function party(keys, results, cls) {
    const order = keys.slice().sort((x, y) => (FRONT.includes(cls[x]) ? 0 : 1) - (FRONT.includes(cls[y]) ? 0 : 1) || results[y].power - results[x].power || (x < y ? -1 : 1));
    return {order, spec: {units: order.map(k => ({key: k, build: "none", stats_override: results[k].stats, stats_final: true, power: results[k].power, myinfo_combat: results[k].combat})), leader: 0}};
  }

  const hasSupporter = (keys, cls) => keys.some(k => cls[k] === "서포터");
  // 예선 지원: 서포터가 있으면 S.screen.supporter(격돌의 돌풍), 없으면 S.screen.other
  const screenSupport = (S, keys, cls) => hasSupporter(keys, cls) ? S.screen.supporter : S.screen.other;
  // 본선 지원 후보: 특정 직업에만 걸리는 지원(S.supportRole: 지원 → 직업)은 팀에 그 직업이 없으면 뺀다
  const finalSupports = (S, keys, cls) => S.final.supports.filter(s => !(S.supportRole || {})[s] || keys.some(k => cls[k] === S.supportRole[s]));

  // 기대 점수(영상으로 확인한 식): (기본+졸개+보스 × 깎은 비율) × (1+추가%). 진행도 prog = 0.5 + 0.5 × 깎은 비율(클리어 1)
  // progs(판별 진행도)가 있으면 판마다 점수를 내 평균한다 — 평균 진행도를 넣으면 «졸개전 패배 + 클리어» 섞인 팀을 크게 낮춰 봄.
  // 졸개전에서 진 판은 처치한 졸개만 점수(근사 k, 시뮬에 처치 수가 따로 없어 깎은 체력 비율에서 추정), 보스 점수 0
  // 판마다 처치한 졸개 수 k 도 반영(V.scoreFromProg: 졸개전 패배 판은 k 근사·보스 0). 이 값은 보조 열(평균)로만 쓰고 순위는 rankStats 로 매김.
  function expected(V, G, level, tiers, prog, progs) {
    const pct = V.extraPct(G, level, tiers), one = p => V.scoreFromProg(G, pct, p);
    if (Array.isArray(progs) && progs.length) return Math.round(progs.reduce((a, p) => a + one(p), 0) / progs.length);
    return one(prog);
  }

  // 순위 기준: 길방은 재도전할 수 있고 단계마다 점수 상한(보스 처치)이 있어 평균은 동점·왜곡이 많다.
  // 상위 점수 = 판별 점수 상위 TOP_Q 비율(올림) 판의 평균(여러 번 도전해 잘 나온 판), 상한 도달률 = 보스를 처치(진행도 1)한 판의 비율.
  // 정렬: 상위 점수 큰 순 -> 상한 도달률 큰 순 -> 평균 큰 순 -> 키. 평균 진행도를 점수식에 넣지 않고 판마다 계산한다.
  const TOP_Q = 0.2, CAP_EPS = 1e-9;
  function rankStats(V, G, level, tiers, prog, progs, clear) {
    const pct = V.extraPct(G, level, tiers);
    const has = Array.isArray(progs) && progs.length;
    const ps = has ? progs : [prog == null ? 0 : prog];
    const sc = ps.map(p => V.scoreFromProg(G, pct, p)).sort((a, b) => b - a);
    const m = Math.max(1, Math.ceil(sc.length * TOP_Q - CAP_EPS));
    const top = Math.round(sc.slice(0, m).reduce((a, b) => a + b, 0) / m);
    const mean = Math.round(sc.reduce((a, b) => a + b, 0) / sc.length);
    const cap = has ? ps.filter(p => p >= 1 - CAP_EPS).length / ps.length : (clear == null ? (prog >= 1 - CAP_EPS ? 1 : 0) : clear);
    return {top, mean, cap};
  }
  const byRank = (a, b) => b.top - a.top || b.cap - a.cap || b.mean - a.mean;

  const jobKey = (keys, level, sup, tiers) => [keys.join("+"), level, sup, (tiers || []).join("")].join("|");

  // 작업 목록 → 작업자 수만큼 나눈 묶음(라운드 로빈). job = {key, party, options:{guild}}
  function split(jobs, n) {
    const out = Array.from({length: Math.max(1, Math.min(n, jobs.length))}, () => []);
    jobs.forEach((j, i) => out[i % out.length].push(j));
    return out;
  }

  function screenJobs(S, G, V, list, results, cls, tiers) {
    return list.map(keys => {
      const sup = screenSupport(S, keys, cls), p = party(keys, results, cls);
      return {key: jobKey(keys, S.screen.level, sup, tiers), keys, level: S.screen.level, sup, party: p.spec, order: p.order, options: {guild: {level: S.screen.level, sets: tiers.slice(), support: sup}}};
    });
  }
  function finalJobs(S, G, V, finalists, results, cls, tiers) {
    const jobs = [];
    for (const keys of finalists) {
      const p = party(keys, results, cls);
      for (const level of S.final.levels) for (const sup of finalSupports(S, keys, cls))
        jobs.push({key: jobKey(keys, level, sup, tiers), keys, level, sup, party: p.spec, order: p.order, options: {guild: {level, sets: tiers.slice(), support: sup}}});
    }
    return jobs;
  }

  // 시뮬에서 협공류(S.banVia, 기본 coop·forced_coop)가 판당 평균 0.05회 이상 나간 팀은 «협공 금지» 규칙에 걸린 것으로 보고 거른다. 장비·조합으로 붙는 협공까지 잡는다.
  const COOP_VIA = ["coop", "forced_coop"], COOP_EPS = 0.05;
  function coopHit(S, r) {
    if (!r || S.banCoop === false) return false;
    const via = r.via || {};
    return (S.banVia || COOP_VIA).some(k => (via[k] || 0) >= COOP_EPS);
  }

  // 협공 때문에 걸러진 팀 수(조합 기준 중복 제거). 화면에 «시뮬에서 협공이 나가 제외된 팀 N개» 로 보여 줌
  function countDropped(S, pairs) {
    const ids = new Set();
    for (const [jobs, res] of pairs) for (const j of jobs) if (coopHit(S, res[j.key])) ids.add(j.keys.slice().sort().join("+"));
    return ids.size;
  }

  // 예선 결과 → 상위 n 팀(상위 점수 → 상한 도달률 → 평균 순, 같으면 키 순). res = {jobKey: {prog, clear, progs}}
  function pickTop(V, G, jobs, res, tiers, n, S) {
    const sc = jobs.filter(j => res[j.key] && !coopHit(S || {}, res[j.key])).map(j => ({keys: j.keys, ...rankStats(V, G, j.level, tiers, res[j.key].prog, res[j.key].progs, res[j.key].clear)}));
    sc.sort((a, b) => byRank(a, b) || (a.keys.join() < b.keys.join() ? -1 : 1));
    return sc.slice(0, n).map(x => x.keys);
  }
  const pickFinalists = (S, V, G, jobs, res, tiers) => pickTop(V, G, jobs, res, tiers, S.finalists, S);

  // 본선 결과 → 팀마다 순위 기준이 가장 좋은 한 줄, 큰 순. score = 상위 점수(순위 기준), mean = 평균(보조), cap = 상한 도달률
  function rank(V, G, jobs, res, tiers, top, S) {
    const best = new Map();
    for (const j of jobs) {
      const r = res[j.key]; if (!r || coopHit(S || {}, r)) continue;
      const st = rankStats(V, G, j.level, tiers, r.prog, r.progs, r.clear), id = j.keys.slice().sort().join("+"), cur = best.get(id);
      if (!cur || byRank(st, {top: cur.score, cap: cur.cap, mean: cur.mean}) < 0) best.set(id, {keys: j.keys, order: j.order, level: j.level, sup: j.sup, score: st.top, mean: st.mean, cap: st.cap, clear: r.clear, prog: r.prog, frac: Math.max(0, Math.min(1, 2 * r.prog - 1)), n: r.n});
    }
    return [...best.values()].sort((a, b) => b.score - a.score || b.cap - a.cap || b.mean - a.mean || (a.order.join() < b.order.join() ? -1 : 1)).slice(0, top || 5);
  }

  // 작업자 풀로 한 단계 실행. makeWorker() → Worker 호환 객체(postMessage/onmessage/terminate). 결과 res[key] = {prog, clear, n}
  // 진행·취소: onProgress(done, total), handle.cancel(). 작업자가 오류를 내면 reject.
  function runPhase({makeWorker, jobs, workers, runs, seed, stage, base, onProgress}) {
    const parts = split(jobs, workers), res = {}, ws = [];
    let done = 0, finished = 0, dead = false, rejectFn;
    const p = new Promise((resolve, reject) => {
      rejectFn = reject;
      if (!jobs.length) { resolve(res); return; }
      parts.forEach((part, wi) => {
        const w = makeWorker(); ws.push(w);
        w.onmessage = e => {
          const m = e.data; if (dead) return;
          if (m.type === "team") { res[m.key] = {prog: m.result.prog == null ? 0 : m.result.prog, clear: m.result.clear, n: m.result.n, via: m.result.via || {}, progs: m.result.progs || null}; done++; if (onProgress) onProgress(done, jobs.length); }
          else if (m.type === "done") { if (++finished === parts.length) { ws.forEach(x => x.terminate()); resolve(res); } }
          else if (m.type === "error") { dead = true; ws.forEach(x => x.terminate()); reject(new Error(m.msg || "작업자 오류")); }
        };
        w.onerror = ev => { if (dead) return; dead = true; ws.forEach(x => x.terminate()); reject(new Error("작업자 오류: " + (ev && ev.message || "알 수 없음"))); };
        w.postMessage({type: "run", id: wi + 1, base, stage, n_runs: runs, seed, options: {build: "standard", rules_override: {power_penalty: "model"}},
          teams: part.map(j => ({key: j.key, party: j.party, options: j.options}))});
      });
    });
    return {promise: p, cancel() { dead = true; ws.forEach(x => x.terminate()); rejectFn(new Error("취소")); }};
  }

  const BASIS = {client: "클라 자료 확인", community: "커뮤니티 근거(중간 신뢰)", inference: "추정"};
  // «제외·주의 구원자» 접이식 목록. notes = [{key, kind: exclude|caution, basis, why}], 제외는 체크박스를 켠 때만 실제로 빠진다
  function notesHtml(st, cx) {
    const notes = cx.notes || [];
    if (!notes.length) return "";
    const esc = cx.esc, on = st.banCoop !== false;
    const row = n => `<li data-k="gd-note-${esc(n.key)}"><b>${esc(cx.label(n.key))}</b> <span class="mut">[${n.kind === "exclude" ? (on ? "제외" : "제외 해제됨") : "주의"} · ${esc(BASIS[n.basis] || n.basis)}]</span><br>${esc(n.why)}</li>`;
    const dropped = st.dropped ? `<div class="gd-small" data-k="gd-search-dropped">시뮬에서 협공이 나가 결과에서 뺀 팀: ${st.dropped}개</div>` : "";
    return `<details class="gd-small" data-k="gd-notes"><summary>제외·주의 구원자 ${notes.length}명 (보스·맵 기믹 때문)</summary><ul>${notes.map(row).join("")}</ul>${dropped}<div class="mut">길방 보스는 정실 어필 뒤 신부 경쟁 보유자 한 명만 정상이고 나머지는 «들러리»가 됩니다. 보호막이 있는 보스를 들러리가 치면 들러리 전원이 큰 연쇄 피해를 받아서, 내 턴이 아닐 때 공격하는 구원자가 위험합니다. 클라 표에 «협공 금지» 규칙 자체는 없고 이 기믹의 결과입니다. 시즌이 바뀌면 보스가 달라져 이 목록도 다시 봐야 합니다.</div></details>`;
  }

  const SUP_NAME = {none: "지원 안 고름", gust: "격돌의 돌풍", focus: "날카로운 집중력", strike: "강인한 타격", mountain: "태산의 의지", fire: "불의 고동"};
  const num = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  // 화면 조각. st = {phase: idle|run|done|err, msg, done, total, rows, sig}, cx = {hasInfo, sig(현재 고른 선택 효과), label(key), esc}
  function html(st, cx) {
    const esc = cx.esc;
    const warn = '<div class="mut gd-small">오토 전투 기준 · 내 정보의 실제 최종 능력치 · 선택 효과는 길방에 없다는 클라 확인에 따라 기본 끔(서버 처리는 미확인) · 시뮬 전체가 아직 실제 플레이와 충분히 대조되지 않았습니다(참고용). 시즌이 바뀌면 보스·규칙이 달라지니 새 시즌 값이 반영된 뒤에 쓰세요.</div>';
    const head = '<b>내 정보로 최고 점수 편성 찾기</b> <span class="gd-est" title="시뮬 기반 추정입니다">추정</span>';
    if (!cx.hasInfo) return `<div class="gd-search" data-k="gd-search">${head}<div class="mut gd-small">먼저 «내 계정 정보 불러오기»로 내 구원자를 불러오세요. 불러온 구원자 중에서 기대 점수가 가장 큰 4인 편성을 찾습니다.</div></div>`;
    const btn = (label) => `<button type="button" data-gs="start">${label}</button>`;
    const ex = cx.excluded || [];
    const notes = notesHtml(st, cx);
    const coop = ex.length ? `${notes}<label class="gd-small" data-k="gd-search-coop"><input type="checkbox" data-gs="coop"${st.banCoop === false ? "" : " checked"}> 협공 구원자 제외(${ex.map(k => esc(cx.label(k))).join(", ")}) <span class="mut">— 길방 EX는 협공 금지라는 글이 많음(스킬 문구로 먼저 빼고, 시뮬에서 협공이 나간 팀도 거름)</span></label>` : "";
    let body;
    if (st.phase === "run") body = `<div data-k="gd-search-progress">${esc(st.msg || "")}${st.total ? ` · ${st.done}/${st.total}` : ""} <button type="button" class="sec" data-gs="cancel">취소</button></div>`;
    else if (st.phase === "err") body = `<div class="bad" data-k="gd-search-err">찾지 못했습니다: ${esc(st.msg || "")}</div>${btn("다시 시도")}`;
    else if (st.phase === "done") {
      const stale = st.sig !== cx.sig ? '<div class="gd-warn" data-k="gd-search-stale">위에서 고른 선택 효과가 바뀌었습니다. 아래 결과는 이전 선택 기준이니 다시 찾아 주세요.</div>' : "";
      const rows = st.rows.map((r, i) => `<tr><td>${i + 1}</td><td>${r.order.map(k => esc(cx.label(k))).join("<br>")}</td><td>${r.level}단계</td><td>${esc(SUP_NAME[r.sup] || r.sup)}</td><td><b>${num(r.score)}</b></td><td>${Math.round(r.clear * 100)}%</td><td>${Math.round(r.frac * 100)}%</td><td>${Math.round((r.cap == null ? r.clear : r.cap) * 100)}%</td><td>${r.mean == null ? "-" : num(r.mean)}</td></tr>`).join("");
      body = `${stale}${coop}<div class="gd-scroll"><table data-k="gd-search-table"><thead><tr><th>순위</th><th>편성(앞열 → 뒤열, 첫 구원자가 리더)</th><th>별의 도전</th><th>알리시아 지원</th><th>상위 점수</th><th>클리어</th><th>보스 깎음</th><th>상한 도달률</th><th>평균 점수</th></tr></thead><tbody>${rows || '<tr><td colspan="9">결과 없음</td></tr>'}</tbody></table></div>
<div class="mut gd-small">후보 ${st.pool}명 → 조합 ${st.combos}개를 짧게 두 번 걸러 상위 ${st.finalists}팀을 고른 뒤, 단계·지원별로 ${st.runs}판씩 돌린 값입니다(표본이 작아 한두 단계·수천 점은 오차). 위에서 고른 선택 효과 기준(기본 끔). 길방은 재도전할 수 있고 단계마다 점수 상한이 있어 평균이 아니라 <b>상위 점수</b>(판별 점수 상위 20%의 평균) 순으로 줄을 세우고, 같으면 <b>상한 도달률</b>(보스를 처치한 판 비율), 그다음 평균 점수 순입니다. 점수는 판마다 확인된 점수식에 넣어 계산하며, 졸개전에서 진 판은 처치한 졸개 수(깎은 체력에서 추정한 근사)만큼만 받습니다.</div>${btn("다시 찾기")}`;
    } else body = coop + "<br>" + btn("최고 점수 편성 찾기") + '<span class="mut gd-small"> 몇 분 걸릴 수 있어요. 탭을 연 채로 기다려 주세요.</span>';
    return `<div class="gd-search" data-k="gd-search">${head}${body}${warn}</div>`;
  }

  const api = {FRONT, TOP_Q, rankStats, pool, combos, party, coopHit, hasSupporter, screenSupport, finalSupports, expected, jobKey, split, screenJobs, finalJobs, pickFinalists, pickTop, rank, runPhase, html, SUP_NAME, countDropped, notesHtml, BASIS};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.GuildSearch = api;
})(typeof window !== "undefined" ? window : globalThis);
