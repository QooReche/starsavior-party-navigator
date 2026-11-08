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

  const AUTO = -1;   // 난이도 선택값: 자동(가장 점수가 높은 난이도)
  const jobKey = (boss, keys, level, brk) => [boss, idOf(keys), level].concat(brk ? [brk.name] : []).join("|");

  // 보스 하나의 작업 목록. 구원자 칸 순서·능력치는 guild_search.party 와 같다(리더 0번)
  function bossJobs(S, boss, level, list, results, cls, brk) {
    return list.map(keys => {
      const p = GS.party(keys, results, cls);
      return {key: jobKey(boss, keys, level, brk), boss, keys, order: p.order, level, brk: brk || null, party: p.spec,
        options: Object.assign({cosmo_raid: {boss, step: 3, level}, cosmo_top_q: S.topQ}, brk ? {break_skill: {name: brk.name, level: brk.level}} : {})};
    });
  }

  // 작업자 결과 -> 순위 항목 [{keys, order, boss, st:{mean,top,clear,frac,n}}], 큰 순(같으면 키 순). 요약이 없는 결과(작업자 오류 등)는 뺀다
  function pickTop(jobs, res, mode, n) {
    const rows = jobs.filter(j => res[j.key] && res[j.key].cosmo).map(j => ({keys: j.keys, order: j.order, boss: j.boss, st: res[j.key].cosmo}));
    const cmp = byRank(mode);
    rows.sort((a, b) => cmp(a, b) || (idOf(a.keys) < idOf(b.keys) ? -1 : 1));
    return n == null ? rows : rows.slice(0, n);
  }

  // 1단계 «순차 반감»: 모든 조합을 firstRuns 판만 돌려 순위를 매긴 뒤 상위 n 팀(경계 동점은 전부 포함)만 남은 판을 더 돌린다.
  // 통과 = (가) 순위 상위 n 팀 + 경계와 순위 값(기준 점수·반대 점수·클리어율)이 똑같은 팀 전부, (나) 구원자마다 «그 구원자가 든 상위 m 팀»(역시 경계 동점 포함).
  // (가)만 쓰면 «한 구원자가 3보스 모두 1위권»일 때 통과팀이 전부 그 구원자를 포함해 겹치지 않는 삼중이 없어지므로(pickDiverse 와 같은 이유) (나)로 구원자별 대안을 보장한다.
  // 동점을 자르면 «같은 점수인데 운으로 탈락»이 되므로 모두 통과시킨다(예: 벨그라스는 59~64% 팀이 최저 점수 동률이라 경계가 그 동률 안에 들어오면 사실상 전부 통과 = 안전).
  function pickPass(jobs, res, mode, n) {
    const all = pickTop(jobs, res, mode);
    if (all.length <= n) return all;
    const cmp = byRank(mode), keep = new Array(all.length).fill(false), edge = all[Math.max(0, n - 1)];
    for (let i = 0; i < all.length && (i < n || cmp(all[i], edge) === 0); i++) keep[i] = true;
    const units = new Set(); all.forEach(e => e.keys.forEach(k => units.add(k)));
    const m = Math.max(1, Math.ceil(0.25 * n / Math.max(1, units.size))), cnt = new Map(), edgeOf = new Map();
    all.forEach((e, i) => {
      for (const k of e.keys) {
        const c = cnt.get(k) || 0;
        if (c < m) { cnt.set(k, c + 1); if (c + 1 === m) edgeOf.set(k, i); keep[i] = true; }
        else if (cmp(e, all[edgeOf.get(k)]) === 0) keep[i] = true;
      }
    });
    return all.filter((e, i) => keep[i]);
  }
  const halfUp = x => Math.floor(x + 0.5);
  // 같은 팀의 두 요약(각각 n 판)을 하나로: 평균·클리어율·깎음은 판 수 가중 평균, 상위 점수는 두 요약이 모두 1판일 때 정확히(상위 판 수 m = ceil(2q) 가 1 이면 큰 쪽, 2 이면 평균),
  // 그 밖의 판 수 조합은 상위 점수의 가중 평균으로 근사한다(기본 설정은 1판+1판이라 근사를 쓰지 않는다).
  function mergeSummary(a, b, q) {
    const n = a.n + b.n, w = (x, y) => (x * a.n + y * b.n) / n;
    let top;
    if (a.n === 1 && b.n === 1) { const m = Math.max(1, Math.ceil(2 * q - 1e-9)); top = m === 1 ? Math.max(a.top, b.top) : halfUp((a.top + b.top) / 2); }
    else top = halfUp(w(a.top, b.top));
    return {mean: halfUp(w(a.mean, b.mean)), top, clear: Math.round(w(a.clear || 0, b.clear || 0) * 1e4) / 1e4, frac: Math.round(w(a.frac || 0, b.frac || 0) * 1e4) / 1e4, n};
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

  // 팀마다 난이도(levelOf)와 브레이크 스킬(brks 중 점수가 큰 것, 같으면 앞쪽 = 장착 안 함)을 고른 마지막 순위. 결과가 빠진 삼중은 뺀다
  function finalRankBrk(triples, bosses, levelOf, brks, res, mode, show) {
    const out = [];
    for (const t of triples) {
      const teams = t.teams.map((e, i) => {
        const lv = levelOf(bosses[i], e.keys);
        let pick = null;
        for (const b of brks) { const r = res[jobKey(bosses[i], e.keys, lv, b)]; if (r && r.cosmo && (!pick || metric(r.cosmo, mode) > metric(pick.st, mode))) pick = {st: r.cosmo, brk: b ? b.name : null, brkLv: b ? b.level : null, bs: r.bs || null}; }
        return pick ? {boss: bosses[i], keys: e.keys, order: e.order, level: lv, st: pick.st, brk: pick.brk, brkLv: pick.brkLv} : null;
      });
      if (teams.some(x => !x)) continue;
      out.push({sum: teams.reduce((a, x) => a + metric(x.st, mode), 0), sum2: teams.reduce((a, x) => a + other(x.st, mode), 0), teams});
    }
    out.sort((a, b) => b.sum - a.sum || b.sum2 - a.sum2 || (a.teams.map(x => idOf(x.keys)).join() < b.teams.map(x => idOf(x.keys)).join() ? -1 : 1));
    return out.slice(0, show);
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

  // ---- 후보 풀·계획(판 수)·남은 시간 -------------------------------------------------------------
  // 기본은 전수: 내 정보에서 육성된(전투력>0) 보유 구원자 전부. 전투력 하한·역할 보충 없음.
  // 안전 장치로 S.maxPool(숫자)을 주면 그때만 «전투력 상위 maxPool 명 + minRole 보충(minPowerRatio 이상)»으로 자른다. 기본 null.
  function poolAll(S, results, roster) {
    const capped = S.maxPool > 0;
    return GS.pool({banCoop: false, excluded: [], poolSize: capped ? S.maxPool : undefined, minPowerRatio: capped ? S.minPowerRatio || 0 : 0, minRole: capped ? S.minRole || {} : {}}, results, roster);
  }
  const isFront = r => GS.FRONT.includes(r.cls);
  // 4인 조합 수(열거 없이 계산): 앞열 역할 수 fr 가 minFront 이상, 딜러 4-fr 가 minDealer 이상인 것
  function choose(n, k) { if (k < 0 || k > n) return 0; let r = 1; for (let i = 1; i <= k; i++) r = r * (n - k + i) / i; return Math.round(r); }
  function countCombos(S, rows) {
    const F = rows.filter(isFront).length, D = rows.length - F, mf = S.minFront || 0, md = S.minDealer || 0;
    let n = 0;
    for (let fr = 0; fr <= TEAM; fr++) if (fr >= mf && TEAM - fr >= md) n += choose(F, fr) * choose(D, TEAM - fr);
    return n;
  }
  // 시작 전 확인: 3팀(12명)을 만들 수 없으면 이유를 정확히 알려 주는 문구, 가능하면 null
  function feasibility(S, rows) {
    const F = rows.filter(isFront).length, D = rows.length - F, mf = S.minFront || 0, md = S.minDealer || 0, pool = S.maxPool > 0 ? ` (탐색 풀을 ${S.maxPool}명으로 제한한 설정)` : "";
    if (rows.length < TEAM * BOSSES) return `편성할 수 있는 구원자가 부족합니다(육성된 보유 구원자 ${rows.length}명, 3팀 ${TEAM * BOSSES}명 필요)${pool}`;
    if (F < BOSSES * mf) return `앞열 역할(디펜더·서포터) 구원자가 부족합니다(육성된 ${F}명, 3팀에 팀마다 최소 ${mf}명씩 ${BOSSES * mf}명 필요)${pool}`;
    if (D < BOSSES * md) return `딜러(디펜더·서포터가 아닌 구원자)가 부족합니다(육성된 ${D}명, 3팀에 팀마다 최소 ${md}명씩 ${BOSSES * md}명 필요)${pool}`;
    return null;
  }
  // 2단계로 넘길 팀 수: 조합 수가 keep 의 2배 이하면 «상위 자르기+다양성 채우기»가 거의 의미가 없고 분할이 불발하므로 조합 전체를 넘긴다
  const effKeep = (S, L) => L <= 2 * S.rerank.keep ? L : S.rerank.keep;
  // 순차 반감에서 보스마다 두 번째 판을 돌릴 팀 수(동점 포함 전의 기준 수). 반감을 쓰지 않으면(firstRuns 가 없거나 판 수 이상) 조합 전체.
  // 2단계 후보가 keep 보다 적어지면 «상위 자르기+다양성 채우기»가 불발하므로 최소 passMinMult×keep 팀은 통과시킨다.
  function passCount(S, L, keep) {
    const sc = S.screen || {}, fr = sc.firstRuns | 0;
    if (!(fr >= 1 && fr < sc.runs)) return L;
    return Math.min(L, Math.max(Math.ceil((sc.passFrac > 0 ? sc.passFrac : 0.1) * L), (sc.passMinMult > 0 ? sc.passMinMult : 3) * keep));
  }
  // 단계별 판 수 계획(시작 전에 알 수 있음). 3단계 팀 수는 삼중이 정해져야 알 수 있어 상한(topTriples×3팀)으로 두고 단계 전환 때 바로잡는다.
  function plan(S, rows, nBrk) {   // nBrk = 브레이크 스킬 후보 수(마지막 단계는 팀마다 «장착 안 함 + 후보» 각각을 돌림)
    const L = countCombos(S, rows), keep = effKeep(S, L), t4 = BOSSES * S.combine.topTriples * (1 + (nBrk | 0)), pass = passCount(S, L, keep), halved = pass < L, fr = halved ? S.screen.firstRuns | 0 : 0;
    // 단계: 0 = 1단계 첫 판(전 조합), 1 = 1단계 보충 판(상위 pass 팀 + 경계 동점 + 구원자별 대안이라 실제 팀 수는 달라질 수 있어 단계 전환 때 바로잡음), 2 = 상위 keep 팀 정밀, 3 = 삼중 팀 재시뮬
    const stages = [{id: 1, teams: BOSSES * L, runs: halved ? fr : S.screen.runs}, {id: 2, teams: halved ? BOSSES * pass : 0, runs: halved ? S.screen.runs - fr : 0, upper: true},
      {id: 3, teams: BOSSES * Math.min(keep, L), runs: S.rerank.runs}, {id: 4, teams: t4, runs: S.final.runs, upper: true}];
    stages.forEach(s => { s.games = s.teams * s.runs; });
    return {pool: rows.length, combos: L, keep, pass, halved, stages, total: stages.reduce((a, s) => a + s.games, 0)};
  }

  // 남은 시간 계산(순수). 단계마다 한 판 비용이 다르므로 단계 가중치 w[s] 로 아직 안 해 본 단계의 속도를 현재 속도에서 추정하고, 자기 단계 속도가 측정되면 그 값으로 바꾼다.
  //  - 시간 단위는 초(호출자가 일관되게 넘김). 판 수는 «판» 단위(팀 수 × 판 수).
  //  - 속도 = 최근 window 초의 이동 구간 (처음 결과가 도착한 뒤 warmup 초까지는 측정값을 쓰지 않는다: 작업자가 제각각 시작해 초반 속도가 흔들림)
  //  - 단계 전환: 새 단계가 자기 속도를 얻기 전에는 이전 단계 실측 × (w[새]/w[이전])을 쓰고, 단계 시작~첫 결과 지연(엔진 준비)을 남은 단계 수만큼 더한다.
  //  - prior(저장된 이 PC 속도, 단계별 초/판)가 있으면 실측 전에 그 값을 쓴다.
  const DEF_W = [1, 1, 0.6, 0.25];
  const NSTAGE = 4;
  function etaNew(o) {
    const W = (o.weights || DEF_W).slice(), warm = o.warmup == null ? 3 : o.warmup, win = o.window == null ? 20 : o.window, prior = o.prior || null, GAP = 0.25, blend = o.blend == null ? 0 : o.blend, frac = o.winFrac == null ? 0 : o.winFrac;
    const st = o.stages.map(s => ({games: s.games, done: 0, samples: [], cur: null, first: null, c: null, cAvg: null, lat: null, startT: null}));
    let cur = -1;
    const obs = s => s.cAvg != null && s.done >= s.games ? s.cAvg : s.c;      // 끝난 단계는 구간 전체 평균(더 안정적), 진행 중이면 최근 구간
    function begin(i, games, t) {
      cur = i; const s = st[i];
      if (games != null) s.games = games;
      s.startT = t; s.done = 0; s.samples = []; s.cur = null; s.first = null;
    }
    function update(done, t) {
      const s = st[cur]; if (!s) return;
      s.done = done;
      if (s.first == null) { if (done > 0) { s.first = {t, g: done}; s.lat = t - s.startT; s.samples = [{t, g: done}]; s.cur = {t, g: done}; } return; }
      s.cur = {t, g: done};
      const last = s.samples[s.samples.length - 1], el = t - s.first.t, span = Math.max(win, frac * el);
      if (t - last.t >= Math.max(GAP, 0.02 * el)) s.samples.push({t, g: done});          // 오래 갈수록 표본 간격을 늘려 개수를 제한
      while (s.samples.length > 2 && s.samples[1].t < t - 2 * span) s.samples.shift();
      if (done > s.first.g && t > s.first.t) s.cAvg = (t - s.first.t) / (done - s.first.g);
      if (el >= warm) {
        let ref = s.samples[0];
        for (const x of s.samples) { if (x.t >= t - span) { ref = x; break; } ref = x; }
        if (ref.t >= t) ref = s.first;
        if (done > ref.g && t > ref.t) s.c = (t - ref.t) / (done - ref.g);
      }
    }
    // 단계 s 의 한 판 비용(초). 기준 = 자기 실측 > 가장 가까운 이전 단계 실측 × 가중치 비 > 저장된 prior > 없음
    function cost(s) {
      if (s <= cur && obs(st[s]) != null) {
        const m = obs(st[s]);
        // 저장된 속도가 있으면 측정 초반(blend 초)에는 둘을 섞는다: 초반 속도는 엔진 데워지는 중이라 낮게 나옴
        if (prior && prior[s] > 0 && s === cur && st[s].cur && blend > 0) { const a = Math.min(1, (st[s].cur.t - st[s].first.t) / blend); return a * m + (1 - a) * prior[s]; }
        return m;
      }
      for (let r = Math.min(cur, st.length - 1); r >= 0; r--) { const c = obs(st[r]); if (c != null) return c * W[s] / W[r]; }
      return prior && prior[s] > 0 ? prior[s] : null;
    }
    function estimate(t) {
      if (cur < 0) return {ready: false};
      let lat = 0;
      for (let i = st.length - 1; i >= 1; i--) if (st[i].lat != null) { lat = st[i].lat; break; }
      let rem = 0;
      for (let s = cur; s < st.length; s++) {
        const c = cost(s); if (c == null) return {ready: false};
        const left = s === cur ? Math.max(0, st[s].games - st[s].done) : st[s].games;
        rem += left * c + (s > cur ? lat : 0);
      }
      return {ready: true, remainSec: rem, finishAt: t + rem, stage: cur, cost: st.map((_, s) => cost(s))};
    }
    // 저장용: 단계별 초/판(실측 없는 단계는 실측 있는 단계 × 가중치 비). 실측이 하나도 없으면 null
    function summary() {
      let ref = -1;
      st.forEach((s, i) => { if (s.cAvg != null) ref = i; });      // 가장 나중에 실측한 단계를 기준으로 비어 있는 단계를 채운다
      if (ref < 0) return null;
      return st.map((s, i) => s.cAvg != null ? s.cAvg : st[ref].cAvg * W[i] / W[ref]);
    }
    return {begin, update, estimate, summary, state: () => ({cur, st})};
  }
  // 저장된 {sec:[3], workers} -> 지금 작업자 수에 맞춰 환산한 단계별 초/판. 값이 이상하면 null
  function priorFrom(saved, workers) {
    if (!saved || !Array.isArray(saved.sec) || saved.sec.length !== NSTAGE || !(saved.workers > 0) || !(workers > 0)) return null;      // 단계 구성이 다른 옛 저장값(3단계)은 버린다
    if (!saved.sec.every(x => typeof x === "number" && isFinite(x) && x > 0)) return null;
    return saved.sec.map(x => x * saved.workers / workers);
  }
  function fmtDur(sec) {
    const s = Math.max(0, Math.round(sec));
    if (s < 60) return `약 ${s}초`;
    if (s < 3600) { const m = Math.floor(s / 60), r = s % 60; return `약 ${m}분${r ? " " + r + "초" : ""}`; }
    const h = Math.floor(s / 3600), m = Math.round((s % 3600) / 60);
    return `약 ${h}시간${m ? " " + m + "분" : ""}`;
  }
  const clock = ms => { const d = new Date(ms), p = n => String(n).padStart(2, "0"); return `${p(d.getHours())}:${p(d.getMinutes())}`; };
  // est = etaNew().estimate(..), nowMs = 지금 시각(ms)
  function etaLine(est, nowMs) {
    if (!est || !est.ready) return "남은 시간 계산 중 (계산 엔진을 준비하거나 처음 몇 초를 재는 중입니다)";
    return `남은 시간 ${fmtDur(est.remainSec)} · 전체 완료 예상 ${clock(nowMs + est.remainSec * 1000)}`;
  }
  // 시작 전 안내. pl = plan(), prior = priorFrom(...) 또는 null
  function preText(pl, prior) {
    const g = `조합 ${num(pl.combos)}개 · 총 ${num(pl.total)}판`;
    if (!prior) return `시작하면 몇 초 뒤 예상 시간이 표시됩니다 (${g})`;
    const sec = pl.stages.reduce((a, s, i) => a + s.games * prior[i], 0);
    return `이 PC의 지난 실행 속도 기준 예상 ${fmtDur(sec)} (${g})`;
  }

  // 작업 순서를 고정 시드로 섞는다. 조합이 전투력 순으로 나열돼 있으면 앞쪽(강한 팀, 오래 싸움)과 뒤쪽(약한 팀, 빨리 끝남)의 판당 시간이 달라
  // 남은 시간이 초반에 한쪽으로 치우친다(실측: 초반 +70%). 결과는 팀 키로 모으므로 순서와 무관하고, 같은 입력이면 같은 순서다.
  function shuffled(jobs, seed) {
    const a = jobs.slice(); let s = seed >>> 0;
    const rnd = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; }
    return a;
  }

  // 전체 흐름. 1) 보스별 전 조합 짧게 -> 2) 보스별 상위 K 를 더 정확히 -> 3) 겹침 없는 삼중 최대 합 -> 4) 상위 삼중의 팀을 길게 재시뮬
  // cx = {S, bosses:[boss key 3개], level, mode, results, roster, makeWorker, workers, stage, base, onPlan(plan), onPhase(msg,total,{stage,teams,runs,games}), onProgress(done,total), onHandle(handle), stale()}
  async function search(cx) {
    const {S, bosses, mode, results, roster} = cx;
    const auto = cx.level === AUTO, level = auto ? (S.auto && S.auto.screenLevel) || 6 : cx.level;   // 자동이면 1·2단계는 대표 난이도로
    if (bosses.length !== BOSSES) throw new Error("보스는 3명이어야 합니다");
    if (auto && !(Number.isInteger(cx.levelMax) && cx.levelMax >= 1)) throw new Error("난이도 최대값(levelMax)이 없습니다");   // 긴 계산을 돌리기 전에 막는다
    const rows = poolAll(S, results, roster);
    const bad = feasibility(S, rows);
    if (bad) throw new Error(bad);
    const pl = plan(S, rows, (cx.breaks || []).length);
    if (!pl.combos) throw new Error("조건에 맞는 4인 조합이 없습니다");
    if (S.maxCombos > 0 && pl.combos > S.maxCombos) throw new Error(`4인 조합이 ${num(pl.combos)}개로 안전 상한(${num(S.maxCombos)}개)을 넘습니다. 추천에서 뺄 구원자를 늘리거나 설정의 maxPool/maxCombos 를 조정하세요`);
    const list = GS.combos(S, rows), cls = Object.fromEntries(roster.map(s => [s.key, s.cls]));
    if (cx.onPlan) cx.onPlan(pl);
    const run = async (jobs, runs, seed, msg, idx) => {
      if (cx.onPhase) cx.onPhase(msg, jobs.length, {stage: idx, teams: jobs.length, runs, games: jobs.length * runs});
      const h = GS.runPhase({makeWorker: cx.makeWorker, jobs, workers: cx.workers, runs, seed, stage: cx.stage, base: cx.base, onProgress: cx.onProgress, chunk: Math.max(1, Math.min(50, Math.ceil(jobs.length / (cx.workers * 40))))});
      if (cx.onHandle) cx.onHandle(h);
      return h.promise;
    };
    const stale = () => cx.stale && cx.stale();
    const jobsA = [].concat(...bosses.map(b => bossJobs(S, b, level, list, results, cls)));
    let resA, jobsK, passed = list.length;      // jobsK = 2단계 후보를 뽑을 작업 목록(반감이면 보충 판을 돌린 팀만), resA = 그 팀들의 결과
    if (!pl.halved) {
      resA = await run(shuffled(jobsA, 20261106), S.screen.runs, 1, `1단계: 보스 3명 × 조합 ${list.length}개를 훑어보는 중(처음 한 번은 계산 엔진을 내려받느라 1~3분 더 걸립니다)`, 0);
      if (stale()) return null;
      jobsK = jobsA;
    } else {
      const fr = S.screen.firstRuns, more = S.screen.runs - fr;
      const res1 = await run(shuffled(jobsA, 20261106), fr, 1, `1단계 (1/2): 보스 3명 × 조합 ${list.length}개를 ${fr}판씩 훑어보는 중(처음 한 번은 계산 엔진을 내려받느라 1~3분 더 걸립니다)`, 0);
      if (stale()) return null;
      // 보스마다 첫 판 순위 상위 pl.pass 팀(경계 동점 포함)만 남은 판을 돌린다. 시드는 첫 판과 다른 값(같은 난수로 같은 판을 되풀이하지 않도록)
      const keepJobs = bosses.map(b => { const jb = jobsA.filter(j => j.boss === b), ks = new Set(pickPass(jb, res1, mode, pl.pass).map(e => idOf(e.keys))); return jb.filter(j => ks.has(idOf(j.keys))); });
      jobsK = [].concat(...keepJobs);
      passed = Math.max(...keepJobs.map(k => k.length));
      const res2 = await run(shuffled(jobsK, 20261108), more, 4, `1단계 (2/2): 첫 판 상위 약 ${num(pl.pass)}팀(동점 포함 보스당 최대 ${num(passed)}팀)을 ${more}판 더 확인 중`, 1);
      if (stale()) return null;
      resA = {};
      for (const j of jobsK) {
        const a = res1[j.key], b = res2[j.key];
        if (a && a.cosmo && b && b.cosmo) resA[j.key] = Object.assign({}, b, {cosmo: mergeSummary(a.cosmo, b.cosmo, S.topQ)});
        else if (a && a.cosmo) resA[j.key] = a;
      }
    }
    const keep = bosses.map(b => pickDiverse(jobsK.filter(j => j.boss === b), resA, mode, pl.keep));
    const jobsB = [].concat(...keep.map((k, i) => bossJobs(S, bosses[i], level, k.map(e => e.keys), results, cls)));
    const resB = await run(shuffled(jobsB, 20261107), S.rerank.runs, 3, `2단계: 보스별 상위 ${pl.keep}팀을 더 정확히 확인 중`, 2);
    if (stale()) return null;
    const lists = bosses.map(b => pickTop(jobsB.filter(j => j.boss === b), resB, mode).map(e => Object.assign({score: metric(e.st, mode)}, e)));
    let triples = bestTriples(lists, S.combine.topTriples);
    if (!triples.length) throw new Error("겹치지 않는 3팀을 찾지 못했습니다(후보가 서로 겹침). 내 정보에 육성된 구원자를 늘려 보세요");
    // 난이도 자동: 보스마다 난이도를 따로 고를 수 있으므로(게임이 허용), 뽑은 삼중의 모든 팀을 난이도 0~최대에서 짧게 돌려 팀별로 점수가 가장 큰 난이도를 정하고
    // 그 합이 큰 순으로 삼중을 다시 매긴다. 이 뒤 단계는 시간 안내(ETA) 단계에 없어 stage=null 로 알린다(화면은 안내를 끈다)
    let probe = null, levelOf = () => level;
    if (auto) {
      const lvls = Array.from({length: cx.levelMax + 1}, (_, i) => i), pr = S.auto.probeRuns | 0 || 10;
      const jobsP = [].concat(...lvls.map(l => finalJobs(S, triples, bosses, l, results, cls)));
      const resP = await run(jobsP, pr, 5, `난이도 비교: 후보 편성을 난이도 0~${cx.levelMax}에서 ${pr}판씩 확인 중`, null);
      if (stale()) return null;
      const best = new Map();   // 보스|조합 -> 점수가 가장 큰 난이도(같으면 낮은 난이도)
      for (const t of triples) t.teams.forEach((e, i) => {
        const id = bosses[i] + "|" + idOf(e.keys);
        if (best.has(id)) return;
        let bl = 0, bv = -1;
        for (const l of lvls) { const r = resP[jobKey(bosses[i], e.keys, l)]; const v = r && r.cosmo ? metric(r.cosmo, mode) : -1; if (v > bv) { bv = v; bl = l; } }
        best.set(id, {level: bl, v: bv});
      });
      levelOf = (b, keys) => best.get(b + "|" + idOf(keys)).level;
      probe = lvls.map(l => { const f = finalRank(triples, bosses, l, resP, mode, 1)[0]; return {level: l, sum: f ? f.sum : 0}; });
    }
    // 마지막 확인: 팀마다 (고른 난이도) × (브레이크 스킬 없음 + 보유·시뮬 지원 스킬 각각). 팀별로 점수가 큰 브레이크 스킬을 고른다
    const brks = [null].concat(cx.breaks || []);
    const seen = new Map();
    triples.forEach(t => t.teams.forEach((e, i) => { const l = levelOf(bosses[i], e.keys), k = jobKey(bosses[i], e.keys, l); if (!seen.has(k)) seen.set(k, {boss: bosses[i], keys: e.keys, level: l}); }));
    const jobsC = [];
    seen.forEach(v => brks.forEach(b => jobsC.push(...bossJobs(S, v.boss, v.level, [v.keys], results, cls, b))));
    const resC = await run(jobsC, S.final.runs, 2, `${auto ? "마지막 확인" : "3단계"}: 합이 큰 ${triples.length}개 편성의 팀 ${seen.size}개${brks.length > 1 ? "를 브레이크 스킬 " + (brks.length - 1) + "종과 함께" : ""} ${S.final.runs}판씩 확인 중`, auto ? null : 3);
    if (stale()) return null;
    const rows2 = finalRankBrk(triples, bosses, levelOf, brks, resC, mode, S.combine.show);
    return {rows: rows2, pool: rows.length, capped: S.maxPool > 0, combos: list.length, keep: pl.keep, triples: triples.length, runs: S.final.runs, level: auto ? null : level, reqLevel: cx.level, probe, mode, bosses: bosses.slice(),
      halved: pl.halved, firstRuns: pl.halved ? S.screen.firstRuns : S.screen.runs, screenRuns: S.screen.runs, passed};
  }

  const num = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const pct = x => Math.round((x || 0) * 100) + "%";
  // 화면 조각. st = {phase: idle|run|done|err, msg, done, total, rows, level, mode, bosses, ...}, cx = {hasInfo, label(key), esc, bossName(key), levelMax, level, mode}
  function table(r, mode, cx) {
    const esc = cx.esc;
    if (cx.team) {   // 화면이 카드 모양(앞열·뒤열·리더·브레이크 스킬)을 그려 준다: 보스마다 한 덩어리
      const blocks = r.teams.map(t => `<div class="cs-boss" data-k="cs-team"><div class="cs-bh"><b>${esc(cx.bossName(t.boss))}</b>${t.level != null ? ` <span class="cs-lv">난이도 ${t.level}</span>` : ""}<span class="cs-sc">${MODES[mode]} <b>${num(metric(t.st, mode))}</b> · ${MODES[mode === "top" ? "mean" : "top"]} ${num(other(t.st, mode))} · 클리어율 ${pct(t.st.clear)} · 보스 깎음 ${pct(t.st.frac)}</span></div>${cx.team(t)}</div>`).join("");
      return `<div data-k="cs-table">${blocks}<div class="cs-sum"><b>합계 <span data-k="cs-sum">${num(r.sum)}</span></b></div></div>`;
    }
    const body = r.teams.map(t => `<tr><td>${esc(cx.bossName(t.boss))}${t.level != null ? "<br>난이도 " + t.level : ""}${t.brk ? "<br>" + esc(t.brk) : ""}</td><td>${t.order.map(k => esc(cx.label(k))).join("<br>")}</td><td><b>${num(metric(t.st, mode))}</b></td><td>${num(other(t.st, mode))}</td><td>${pct(t.st.clear)}</td><td>${pct(t.st.frac)}</td></tr>`).join("");
    return `<div class="gd-scroll"><table data-k="cs-table"><thead><tr><th>보스</th><th>편성(앞열 → 뒤열, 첫 구원자가 리더)</th><th>${MODES[mode]}(순위 기준)</th><th>${MODES[mode === "top" ? "mean" : "top"]}</th><th>클리어율</th><th>보스 깎음</th></tr></thead><tbody>${body}<tr><td colspan="2"><b>합계</b></td><td colspan="4"><b data-k="cs-sum">${num(r.sum)}</b></td></tr></tbody></table></div>`;
  }
  const progText = st => `${st.msg || ""}${st.total ? ` · ${num(st.done)}/${num(st.total)}` : ""}`;
  function html(st, cx) {
    const esc = cx.esc;
    const head = '<b>3보스 최고 점수 편성 찾기</b> <span class="gd-est" title="시뮬 기반 추정입니다">추정</span>';
    const warn = '<div class="mut gd-small">오토 전투 기준 · 내 정보의 실제 최종 능력치 · 같은 구원자를 여러 보스에 쓰지 않는 3팀(12명) · 점수 합산식은 서버 계산이라 추정이고 시뮬 전체가 아직 실제 플레이와 충분히 대조되지 않았습니다(참고용). 협공 제외는 적용하지 않습니다. 시즌이 바뀌면 새 시즌 값이 반영된 뒤에 쓰세요.</div>';
    if (!cx.hasInfo) return `<div class="gd-search" data-k="cs-search">${head}<div class="mut gd-small">먼저 «내 계정 정보 불러오기»로 내 구원자를 불러오세요. 불러온 구원자 중에서 3보스 점수 합이 가장 큰 3팀을 찾습니다.</div></div>`;
    const lv = [`<option value="-1"${cx.level === AUTO ? " selected" : ""}>자동 (최고 점수 난이도)</option>`].concat(Array.from({length: cx.levelMax + 1}, (_, i) => `<option value="${i}"${i === cx.level ? " selected" : ""}>${i === 0 ? "레벨 0(없음)" : "레벨 " + i}</option>`)).join("");
    const md = Object.entries(MODES).map(([k, v]) => `<option value="${k}"${k === cx.mode ? " selected" : ""}>${v}</option>`).join("");
    const opt = `<div class="gd-small"><label>난이도 <select data-cs="level">${lv}</select></label> <label>순위 기준 <select data-cs="mode">${md}</select></label> <span class="mut">— 3단계(Step 3) 기준. 상위 점수 = 판별 점수 상위 20%의 평균</span></div>`;
    const btn = label => `<button type="button" data-cs="start">${label}</button>`;
    const pre = cx.preEta ? `<div class="mut gd-small" data-k="cs-eta-pre">${esc(cx.preEta)}</div>` : "";
    let body;
    // 진행 표시: 글자 칸(cs-prog, cs-eta)만 갱신하고 취소 버튼은 다시 만들지 않는다(클릭 유실 방지)
    if (st.phase === "run") body = `<div data-k="cs-progress"><span data-k="cs-prog">${esc(progText(st))}</span><div class="mut gd-small" data-k="cs-eta">${esc(st.etaText || "")}</div><button type="button" class="sec" data-cs="cancel">취소</button></div>`;
    else if (st.phase === "err") body = `${opt}<div class="bad" data-k="cs-err">찾지 못했습니다: ${esc(st.msg || "")}</div>${pre}${btn("다시 시도")}`;
    else if (st.phase === "done") {
      const stale = (st.reqLevel != null ? st.reqLevel : st.level) !== cx.level || st.mode !== cx.mode ? '<div class="gd-warn" data-k="cs-stale">위에서 고른 난이도·순위 기준이 바뀌었습니다. 아래 결과는 이전 선택 기준이니 다시 찾아 주세요.</div>' : "";
      const old = cx.sig != null && st.sig !== cx.sig ? '<div class="gd-warn" data-k="cs-old">낡은 결과: 내 정보를 다시 불러왔거나 추천에서 뺄 구원자 목록이 바뀌었습니다. 아래 결과는 이전 기준이니 다시 찾아 주세요.</div>' : "";
      const rows = st.rows || [];
      const lvInfo = st.probe ? '<div class="mut gd-small" data-k="cs-level">난이도는 보스마다 점수가 가장 높은 값을 따로 골랐습니다(보스별 난이도·브레이크 스킬은 아래 편성에 표시, 짧은 표본이라 참고용).</div>' : "";
      const first = rows.length ? `${lvInfo}<div data-k="cs-best">${table(rows[0], st.mode, cx)}</div>` : '<div class="mut">결과 없음</div>';
      const rest = rows.slice(1).map((r, i) => `<details class="gd-small"><summary>${i + 2}위 · 합계 ${num(r.sum)}</summary>${table(r, st.mode, cx)}</details>`).join("");
      const scr = st.halved ? `보스마다 조합 ${num(st.combos)}개를 ${st.firstRuns}판씩 훑고 첫 판 순위 상위 약 ${Math.round(100 * (st.passed / st.combos))}%(동점은 모두 포함, 보스당 최대 ${num(st.passed)}팀)만 ${st.screenRuns - st.firstRuns}판 더 돌려 ${st.screenRuns}판 평균으로 비교하고` : `보스마다 조합 ${num(st.combos)}개를 짧게 훑고`;
      body = `${old}${stale}${opt}${first}${rest}<div class="mut gd-small">후보 ${st.pool}명${st.capped ? "(탐색 풀 제한 설정)" : "(보유 육성 구원자 전부)"} → ${scr}, 보스별 상위 ${st.keep}팀을 더 정확히 본 뒤, 겹치지 않는 3팀 중 합이 큰 ${st.triples}개 편성의 팀을 ${st.runs}판씩 다시 돌린 값입니다(표본이 작아 수천 점은 오차). ${MODES[st.mode]} 기준 합계가 가장 큰 순입니다. 보스별 상위 팀 안에서 고른 최적이라 전체 조합의 수학적 최적은 아닐 수 있습니다.</div>${pre}${btn("다시 찾기")}`;
    } else body = `${opt}${pre}${btn("3보스 최고 점수 편성 찾기")}<span class="mut gd-small"> 보유 구원자가 많으면 오래 걸립니다. 탭을 연 채로 기다려 주세요.</span>`;
    return `<div class="gd-search" data-k="cs-search">${head}${body}${warn}</div>`;
  }

  // 작업자 수 자동 결정(순수 함수, 시험 대상). env = {cores: 논리 코어 수(navigator.hardwareConcurrency, 없으면 null), memGB: navigator.deviceMemory(없으면 null), mobile: 모바일 여부}
  // 설정 W = S.workers(data/cosmo_raid.json): coreFrac(논리 코어 중 쓰는 비율. 나머지는 화면·다른 프로그램용), memFrac·perWorkerMB(메모리의 몇 %를 작업자당 몇 MB로 나눠 쓰는가),
  // unknownMemGB(deviceMemory 를 모르는 브라우저의 보수적 기본), min·max(하한·상한), mobileMax(모바일 상한).
  // deviceMemory 는 브라우저가 최대 8 로 잘라서 알려 주므로 8 이상 기계도 8 로 계산된다(보수적).
  function workerCount(S, env) {
    const W = Object.assign({coreFrac: 0.75, memFrac: 0.5, perWorkerMB: 250, unknownMemGB: 4, min: 1, max: 24, mobileMax: 2}, (S && S.workers) || {}), e = env || {};
    const cores = e.cores > 0 ? Math.floor(e.cores) : 4, mem = e.memGB > 0 ? e.memGB : W.unknownMemGB;
    const byCore = Math.floor(cores * W.coreFrac), byMem = Math.floor(mem * 1024 * W.memFrac / W.perWorkerMB);
    let n = Math.min(byCore, byMem, W.max);
    if (e.mobile) n = Math.min(n, W.mobileMax);
    return Math.max(W.min, Math.floor(n));
  }

  const api = {MODES, workerCount, pickPass, passCount, mergeSummary, shuffled, poolAll, countCombos, feasibility, effKeep, plan, etaNew, priorFrom, fmtDur, etaLine, preText, progText, metric, idOf, jobKey, bossJobs, pickTop, pickDiverse, bestTriples, finalJobs, finalRank, finalRankBrk, search, html, table};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.CosmoSearch = api;
})(typeof window !== "undefined" ? window : globalThis);
