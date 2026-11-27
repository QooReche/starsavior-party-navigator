// 코스모 게이트 «3보스 최고 점수 편성 찾기» 순수 로직(저장소·화면 접근 없음). 후보 풀·조합·작업 분배·작업자 실행은 guild_search.js 를 그대로 쓴다.
// 규칙: 같은 구원자를 여러 보스에 쓰지 못한다(3팀 12명 전부 다름). 순위는 평균 점수(기본) 또는 상위 점수. 협공 제외는 코스모에 없어 적용하지 않는다.
// 시즌 값(풀 크기·판 수·K 등)은 data/cosmo_raid.json 의 search. 점수는 시뮬 쪽(battlesim/web.py cosmo_summary)이 판마다 점수식에 넣어 요약값으로 돌려준다.
(function (root) {
  "use strict";
  const Combinations=typeof module!=='undefined'&&module.exports?require('./score_combinations.js'):root.ScoreCombinations;
  const SS=typeof module!=='undefined'&&module.exports?require('./score_search.js'):root.ScoreSearch;
  const Executor = typeof module !== "undefined" && module.exports ? require("./search_executor.js") : root.SearchExecutor;
  const {num, teamId, pctText, durTextSec, seasonUi} = typeof module !== "undefined" && module.exports ? require("./ui_shared.js") : root.UiShared;
  const GS = typeof require !== "undefined" ? require("./guild_search.js") : root.GuildSearch;
  const Learned = typeof require !== "undefined" ? require("./cosmo_learned.js") : root.CosmoLearned;
  const Placement = typeof require !== "undefined" ? require("./party_placement.js") : root.PartyPlacement;
  const PlacementSearch = typeof require !== "undefined" ? require("./placement_search.js") : root.PlacementSearch;
  const TEAM = 4, BOSSES = 3, EPS = 1e-9;
  function searchSettings(S, learned) {
    const out = Object.assign({}, S);
    if (learned != null && S.learned) out.learned = Object.assign({}, S.learned, {value: !!learned});
    return out;
  }

  const MODES = {mean: "평균 점수", top: "상위 점수"};
  // 순위 값: 기준 점수 -> 반대 점수 -> 클리어율. 평균 진행도 같은 중간값을 비선형 식에 넣지 않고 작업자가 낸 점수 요약을 그대로 쓴다
  const metric = (st, mode) => mode === "top" ? st.top : st.mean;
  const other = (st, mode) => mode === "top" ? st.mean : st.top;
  const byRank = mode => {const cmp=SS.cosmoRank(mode);return (a,b)=>cmp(a.st,b.st);};
  const idOf = teamId;

  const AUTO = -1;   // 난이도 선택값: 자동(가장 점수가 높은 난이도)
  const jobKey = (boss, keys, level, brk, p=null) => Placement.jobKey(keys,p,()=>[boss,idOf(keys),level].concat(brk?[brk.name]:[]).join('|'),[level,brk?[brk.name,brk.level]:null],boss+'|');

  // 보스 하나의 작업 목록. 구원자 칸 순서·능력치는 guild_search.party 와 같다(leaderKey 별도)
  function bossJobs(S, boss, level, list, results, cls, brk, placement) {
    return list.map(keys => {
      const p = GS.party(keys, results, cls, placement||(S.placement?.baseline?Placement.baseline(keys,results):undefined));
      return {key: jobKey(boss, keys, level, brk, p), boss, keys, order: p.order, leaderKey:p.leaderKey, level, brk: brk || null, party: p.spec,
        options: Object.assign({cosmo_raid: {boss, step: 3, level}, cosmo_top_q: S.topQ}, brk ? {break_skill: {name: brk.name, level: brk.level}} : {})};
    });
  }

  // 작업자 결과 -> 순위 항목 [{keys, order, boss, st:{mean,top,clear,frac,n}}], 큰 순(같으면 키 순). 요약이 없는 결과(작업자 오류 등)는 뺀다
  function pickTop(jobs, res, mode, n, uniqueTeams=false) {
    const rows = jobs.filter(j => res[j.key] && res[j.key].cosmo).map(j => ({keys: j.keys, order: j.order, leaderKey:j.leaderKey, boss: j.boss, st: res[j.key].cosmo}));
    const cmp = byRank(mode);
    rows.sort(SS.compareBy(cmp,(a,b)=>idOf(a.keys)<idOf(b.keys)?-1:1));
    return SS.topRows(rows,n,uniqueTeams?{id:r=>idOf(r.keys)}:{});
  }

  // 1단계 «순차 반감»: 모든 조합을 firstRuns 판만 돌려 순위를 매긴 뒤 상위 n 팀(경계 동점은 전부 포함)만 남은 판을 더 돌린다.
  // 통과 = (가) 순위 상위 n 팀 + 경계와 순위 값(기준 점수·반대 점수·클리어율)이 똑같은 팀 전부, (나) 구원자마다 «그 구원자가 든 상위 m 팀»(역시 경계 동점 포함).
  // (가)만 쓰면 «한 구원자가 3보스 모두 1위권»일 때 통과팀이 전부 그 구원자를 포함해 겹치지 않는 삼중이 없어지므로(pickDiverse 와 같은 이유) (나)로 구원자별 대안을 보장한다.
  // 동점을 자르면 «같은 점수인데 운으로 탈락»이 되므로 모두 통과시킨다(예: 벨그라스는 59~64% 팀이 최저 점수 동률이라 경계가 그 동률 안에 들어오면 사실상 전부 통과 = 안전).
  function pickPass(jobs, res, mode, n) {
    const all = pickTop(jobs, res, mode);
    if (all.length <= n) return all;
    const cmp = byRank(mode), keep = new Array(all.length).fill(false);
    SS.topRows(all,n,{ties:cmp}).forEach((_,i)=>{keep[i]=true;});
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
    return diverseRows(pickTop(jobs, res, mode), n);
  }
  function diverseRows(all, n) {
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
  function* tripleSteps(lists,n,budget){
    if(lists.length!==BOSSES)return [];
    return yield* Combinations.steps(lists,n,budget,{id:e=>idOf(e.keys)});
  }
  function bestTriples(lists, n, budget) {
    const steps = tripleSteps(lists, n, budget);
    let step; do { step = steps.next(); } while (!step.done);
    return step.value;
  }
  // 동일한 탐색·횟수·동점 순서. 시간은 결과를 자르지 않고 화면/취소 응답만 양보함.
  async function bestTriplesAsync(lists, n, budget, stale = () => false) {
    const steps = tripleSteps(lists, n, budget);
    let since = performance.now();
    for (;;) {
      if (stale()) throw Object.assign(new Error('취소'), {gwenCause: 'cancel'});
      const step = steps.next();
      if (step.done) return step.value;
      if (performance.now() - since >= 16) {
        await new Promise(resolve => setTimeout(resolve, 0));
        since = performance.now();
      }
    }
  }
  function triplesLimited(triples, n, budget) {
    return !!budget.exhausted && !(triples.length >= n && budget.upperBound < triples[n - 1].sum);
  }

  // 마지막 재시뮬 작업: 삼중에 든 (보스, 조합) 중복 제거
  function finalJobs(S, triples, bosses, level, results, cls) {
    const seen = new Map();
    triples.forEach(t=>t.teams.forEach((e,i)=>{
      const p=e.order&&e.leaderKey?e:undefined;
      const j=bossJobs(S,bosses[i],level,[e.keys],results,cls,null,p)[0];seen.set(j.key,j);
    }));
    const jobs=bosses.flatMap(b=>[...seen.values()].filter(j=>j.boss===b));
    return jobs;
  }

  // 브레이크는 기준 점수 → 반대 점수 → 클리어율 순. 모든 후보의 두 점수가 같으면 장착 차이 없음으로 표시함.
  function finalRankBrk(triples, bosses, levelOf, brks, res, mode, show) {
    const out = [];
    for (const t of triples) {
      const teams = t.teams.map((e, i) => {
        const lv = levelOf(bosses[i], e.keys);
        const candidates = brks.flatMap(b => {
          const r = res[jobKey(bosses[i], e.keys, lv, b, e.leaderKey?e:undefined)];
          return r?.cosmo ? [{st:r.cosmo,brk:b?.name||null,brkLv:b?.level||null,...GS.unsupportedFields(r)}] : [];
        });
        candidates.sort(byRank(mode));
        const pick=candidates[0];
        // 미장착 포함 전체 후보를 확인했을 때만 선언함. 후보 하나·결과 누락은 동점 근거가 아님.
        const brkTie=candidates.length>1 && candidates.length===brks.length && brks.includes(null)
          && candidates.every(c=>metric(c.st,mode)===metric(pick.st,mode) && other(c.st,mode)===other(pick.st,mode));
        return pick ? {boss: bosses[i], keys: e.keys, order: e.order, ...(e.leaderKey?{leaderKey:e.leaderKey}:{}), level: lv, st: pick.st, brk: pick.brk, brkLv: pick.brkLv, ...(brkTie?{brkTie:true}:{}), ...GS.unsupportedFields(pick)} : null;
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
      const teams = t.teams.map((e, i) => { const r = res[jobKey(bosses[i], e.keys, level,null,e.leaderKey?e:undefined)]; return r && r.cosmo ? {boss: bosses[i], keys: e.keys, order: e.order, ...(e.leaderKey?{leaderKey:e.leaderKey}:{}), st: r.cosmo, ...GS.unsupportedFields(r)} : null; });
      if (teams.some(x => !x)) continue;
      out.push({sum: teams.reduce((a, x) => a + metric(x.st, mode), 0), sum2: teams.reduce((a, x) => a + other(x.st, mode), 0), teams});
    }
    out.sort((a, b) => b.sum - a.sum || b.sum2 - a.sum2 || (a.teams.map(x => idOf(x.keys)).join() < b.teams.map(x => idOf(x.keys)).join() ? -1 : 1));
    return out.slice(0, show);
  }

  // ---- 후보 풀·계획(판 수)·남은 시간 -------------------------------------------------------------
  // 기본은 전수: 내 정보에서 육성된(전투력>0) 보유 구원자 전부. 전투력 하한·역할 보충 없음.
  // 안전 장치로 S.maxPool(숫자)을 주면 그때만 «전투력 상위 maxPool 명»으로 자른다. 기본 null.
  function poolAll(S, results, roster) {
    const rows=GS.pool({newSearch:true},results,roster);
    return !S.learned?.value&&S.maxPool>0?rows.slice(0,S.maxPool):rows;
  }
  const isFront = r => GS.FRONT.includes(r.cls);
  // 4인 조합 수. 직업 구성 제한 없음.
  function choose(n, k) { if (k < 0 || k > n) return 0; let r = 1; for (let i = 1; i <= k; i++) r = r * (n - k + i) / i; return Math.round(r); }
  function countCombos(S, rows) {
    return choose(rows.length,4);
  }
  function feasibility(S,rows){
    return rows.length<12?`편성할 수 있는 구원자가 부족함(육성된 보유 구원자 ${rows.length}명, 3팀 12명 필요)`:null;
  }
  // 2단계로 넘길 팀 수: 조합 수가 keep 의 2배 이하면 «상위 자르기+다양성 채우기»가 거의 의미가 없고 분할이 불발하므로 조합 전체를 넘긴다
  const effKeep = (S, L) => L <= 2 * S.rerank.keep ? L : S.rerank.keep;
  // 단계·계산 상한은 시즌 설정이 정본. 옛 자료에는 재시도 없이 기존 후보만 사용한다.
  function retryPlan(S, L) {
    const cfg = S.retry;
    if (!cfg) return {limits: [effKeep(S, L)], maxChecks: Infinity};
    const positive = x => Number.isSafeInteger(x) && x > 0;
    if (!Array.isArray(cfg.keepMultipliers) || cfg.keepMultipliers.length > 3 || cfg.keepMultipliers[0] !== 1 ||
        cfg.keepMultipliers.some(x => x !== null && !positive(x)) ||
        ![cfg.maxCandidatesPerBoss, cfg.maxRerankGames, cfg.maxTripleChecks, S.rerank.runs].every(positive))
      throw Object.assign(new Error("후보 확대 설정이 올바르지 않음"), {gwenCause: "calculation"});
    const cap = Math.min(L, cfg.maxCandidatesPerBoss, Math.floor(cfg.maxRerankGames / (BOSSES * S.rerank.runs)));
    if (cap < 1) throw Object.assign(new Error("후보 확대 계산 상한이 너무 작음"), {gwenCause: "calculation"});
    const base = Math.min(effKeep(S, L), cap), limits = [];
    for (const m of cfg.keepMultipliers) {
      const k = m === null ? cap : Math.min(cap, base * m);
      if (!limits.length || k > limits[limits.length - 1]) limits.push(k);
    }
    return {limits, maxChecks: cfg.maxTripleChecks};
  }
  // 보스별 상위 20팀의 과반에서 사용하고, 둘 이상 보스에 집중된 구원자 최대 2명.
  function overlapMessage(lists, roster, limited) {
    const counts = new Map(), names = new Map(roster.map(r => [r.key, (r.name || r.key) + (r.sub ? `(${r.sub})` : "")]));
    for (const list of lists) {
      const top = list.slice(0, 20), local = new Map();
      for (const e of top) for (const k of e.keys) local.set(k, (local.get(k) || 0) + 1);
      for (const [k, n] of local) if (n > top.length / 2) {
        const c = counts.get(k) || {bosses: 0, ratio: 0};
        c.bosses++; c.ratio += n / top.length; counts.set(k, c);
      }
    }
    const keys = [...counts].filter(([, c]) => c.bosses >= 2)
      .sort((a, b) => b[1].bosses - a[1].bosses || b[1].ratio - a[1].ratio || a[0].localeCompare(b[0])).slice(0, 2).map(([k]) => names.get(k));
    const who = keys.join("·"), reason = who ? `여러 보스의 상위 팀이 ${who}에 몰려 있음` : "보스별 후보 팀의 구원자가 서로 겹침";
    return `겹치지 않는 3팀을 찾지 못했음 · ${reason}${limited ? " · 계산 상한에 도달해 일부 후보·조합은 확인하지 못했음" : " · 후보 확대 후에도 3팀을 나누지 못했음"}. ${who ? who + " 대신 쓸 구원자" : "다른 구원자"}를 더 키우거나 난이도를 낮춰 보세요`;
  }
  // 순차 반감에서 보스마다 두 번째 판을 돌릴 팀 수(동점 포함 전의 기준 수). 반감을 쓰지 않으면(firstRuns 가 없거나 판 수 이상) 조합 전체.
  // 2단계 후보가 keep 보다 적어지면 «상위 자르기+다양성 채우기»가 불발하므로 최소 passMinMult×keep 팀은 통과시킨다.
  function passCount(S, L, keep) {
    const sc = S.screen || {}, fr = sc.firstRuns | 0;
    if (!(fr >= 1 && fr < sc.runs)) return L;
    return Math.min(L, Math.max(Math.ceil((sc.passFrac > 0 ? sc.passFrac : 0.1) * L), (sc.passMinMult > 0 ? sc.passMinMult : 3) * keep));
  }
  // 단계별 판 수 계획(시작 전에 알 수 있음). 3단계 팀 수는 삼중이 정해져야 알 수 있어 상한(topTriples×3팀)으로 두고 단계 전환 때 바로잡는다.
  function plan(S, rows, nBrk) {   // nBrk = 브레이크 스킬 후보 수(마지막 단계는 팀마다 «장착 안 함 + 후보» 각각을 돌림)
    if (S.learned?.value) {
      const c=Learned.config(S,rows.length), L=countCombos(S,rows), first=Math.min(L,c.S+c.K+rows.length*c.M+c.overlapStarts*(c.overlapKeep+2)+c.A);
      const keep=retryPlan(S,L).limits[0], pass=passCount(S,first,keep), fr=S.screen.firstRuns||1;
      const stages=[{id:1,teams:3*first,runs:fr,upper:true},{id:2,teams:3*first,runs:Math.max(0,S.screen.runs-fr),upper:true},
        {id:3,teams:3*Math.min(L,keep+rows.length*c.M+c.overlapStarts*(c.overlapKeep+2)),runs:S.rerank.runs,upper:true},
        {id:4,teams:3*S.combine.topTriples*(1+(nBrk|0)),runs:S.final.runs,upper:true}];
      stages.forEach(s=>s.games=s.teams*s.runs);
      return {pool:rows.length,combos:L,keep,pass,halved:true,learned:true,stages,total:stages.reduce((a,s)=>a+s.games,0)};
    }
    const L = countCombos(S, rows), keep = retryPlan(S, L).limits[0], t4 = BOSSES * S.combine.topTriples * (1 + (nBrk | 0)), pass = passCount(S, L, keep), halved = pass < L, fr = halved ? S.screen.firstRuns | 0 : 0;
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
  const etaNew = o => Executor.etaNew({...o,weights:o.weights||DEF_W});
  // 저장된 {sec:[3], workers} -> 지금 작업자 수에 맞춰 환산한 단계별 초/판. 값이 이상하면 null
  function priorFrom(saved, workers) {
    if (!saved || !Array.isArray(saved.sec) || saved.sec.length !== NSTAGE || !(saved.workers > 0) || !(workers > 0)) return null;      // 단계 구성이 다른 옛 저장값(3단계)은 버린다
    if (!saved.sec.every(x => typeof x === "number" && isFinite(x) && x > 0)) return null;
    return saved.sec.map(x => x * saved.workers / workers);
  }
  const fmtDur = durTextSec;
  const clock = ms => { const d = new Date(ms), p = n => String(n).padStart(2, "0"); return `${p(d.getHours())}:${p(d.getMinutes())}`; };
  // est = etaNew().estimate(..), nowMs = 지금 시각(ms)
  function etaLine(est, nowMs) {
    if (!est || !est.ready) return "남은 시간 계산 중 (계산 엔진을 준비하거나 처음 몇 초를 재는 중)";
    return `남은 시간 ${fmtDur(est.remainSec)} · 전체 완료 예상 ${clock(nowMs + est.remainSec * 1000)}`;
  }
  // 시작 전 안내. pl = plan(), prior = priorFrom(...) 또는 null
  function preText(pl, prior) {
    const g = `조합 ${num(pl.combos)}개 · ${pl.learned ? "학습 선별 기본 예상 " : "기본 "}${num(pl.total)}판 · 후보가 겹치면 확대 재시도하며 예상 시간도 늘어남${pl.learned ? " · 예측 확인 부족 시 전수 확인 또는 후보 확대만큼 늘어남" : ""}`;
    if (!prior) return `시작하면 몇 초 뒤 예상 시간이 표시됨 (${g})`;
    const sec = pl.stages.reduce((a, s, i) => a + s.games * prior[i], 0);
    return `이 PC의 지난 실행 속도 기준 예상 ${fmtDur(sec)} (${g})`;
  }

  // 작업 순서를 고정 시드로 섞는다. 조합이 전투력 순으로 나열돼 있으면 앞쪽(강한 팀, 오래 싸움)과 뒤쪽(약한 팀, 빨리 끝남)의 판당 시간이 달라
  // 남은 시간이 초반에 한쪽으로 치우친다(실측: 초반 +70%). 결과는 팀 키로 모으므로 순서와 무관하고, 같은 입력이면 같은 순서다.
  function shuffled(jobs, seed) {
    const a = jobs.slice();
    const rnd = SS.random(seed);
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; }
    return a;
  }

  // 전체 흐름. 1) 보스별 전 조합 짧게 -> 2) 보스별 상위 K 를 더 정확히 -> 3) 겹침 없는 삼중 최대 합 -> 4) 상위 삼중의 팀을 길게 재시뮬
  // cx = {S, bosses:[boss key 3개], level, mode, results, roster, makeWorker, workers, stage, base, onPlan(plan), onPhase(msg,total,{stage,teams,runs,games}), onProgress(done,total), onHandle(handle), stale()}
  async function search(cx) {
    const {S, bosses, mode, results, roster} = cx;
    const bossName = cx.bossName || (key => key);
    const auto = cx.level === AUTO, level = auto ? (S.auto && S.auto.screenLevel) || 6 : cx.level;   // 자동이면 1·2단계는 대표 난이도로
    if (bosses.length !== BOSSES) throw new Error("보스는 3명이어야 함");
    if (auto && !(Number.isInteger(cx.levelMax) && cx.levelMax >= 1)) throw new Error("난이도 최대값(levelMax)이 없음");   // 긴 계산을 돌리기 전에 막는다
    const rows = poolAll(S, results, roster);
    const bad = feasibility(S, rows);
    if (bad) throw Object.assign(new Error(bad),{gwenCause:"few"});
    const pl = plan(S, rows, (cx.breaks || []).length);
    if (!pl.combos) throw Object.assign(new Error("조건에 맞는 4인 조합이 없음"),{gwenCause:"few"});
    const learned=!!S.learned?.value;
    const comboCap=learned ? S.learned.maxScoreCombos : S.maxCombos;
    if (comboCap > 0 && pl.combos > comboCap) throw new Error(`4인 조합이 ${num(pl.combos)}개로 안전 상한(${num(comboCap)}개)을 넘음. 추천에서 뺄 구원자를 늘리거나 설정의 ${learned ? 'learned.maxScoreCombos' : 'maxPool/maxCombos'} 를 조정해야 함`);
    const list = learned ? {length:pl.combos} : GS.combos({...S,newSearch:true}, rows), cls = Object.fromEntries(roster.map(s => [s.key, s.cls]));
    if (cx.onPlan) cx.onPlan(pl);
    const session=cx.session||Executor.createSession(cx.makeWorker);
    session.resume(JSON.stringify([cx.base,cx.dataVersion,cx.engineVersion]));
    const workersPool=session.pool;
    const battles=cx.battles||(cx.reuseBattles?(session.caches.get('battles')||new Map()):null);
    if(cx.reuseBattles)session.caches.set('battles',battles);
    let completed=false;
    try {
    const run = async (jobs, runs, seed, msg, idx, carry = 0, expected = jobs.length + carry) => {
      if (cx.onPhase) cx.onPhase(msg, expected, {stage: idx, teams: expected, runs, games: expected * runs});
      if (carry && cx.onProgress) cx.onProgress(carry, expected);
      const cache=battles?SS.battleCache(battles,{base:cx.base,stage:cx.stage,seed,runs}):null;
      const reused={},todo=[],hits=[];
      for(const j of jobs){const hit=cache?.get(j);if(hit)hits.push([j,hit]);else todo.push(j);}
      let completed=0,canceled=false;
      if(hits.length){
        cx.onHandle?.({cancel(){canceled=true;}});
        for(const [j,hit] of hits){
          reused[j.key]=hit;completed++;cx.onProgress?.(completed+carry,expected);
          if(completed%256===0)await new Promise(resolve=>setTimeout(resolve,0));
          if(canceled||cx.stale?.())throw Object.assign(new Error('취소'),{gwenCause:'cancel'});
        }
      }
      if(!todo.length)return reused;
      const h = GS.runPhase({makeWorker: cx.makeWorker, pool: workersPool, jobs:todo, workers: cx.workers, runs, seed, stage: cx.stage, base: cx.base, watch:cx.watch,
        onProgress: cx.onProgress ? d => cx.onProgress(d + completed + carry, expected) : null, chunk: Executor.chunkSize(todo.length,cx.workers)});
      if (cx.onHandle) cx.onHandle(h);
      const fresh=await h.promise;
      if(cache)for(const j of todo)if(fresh[j.key])cache.set(j,fresh[j.key]);
      return Object.assign(reused,fresh);
    };
    const stale = () => cx.stale && cx.stale();
    let jobsA = learned ? [] : [].concat(...bosses.map(b => bossJobs(S, b, level, list, results, cls))), auditInfo = null;
    let allJobs = jobsA, learnedSelections=null;
    let firstResults;
    let resA, jobsK, passed = list.length;      // jobsK = 2단계 후보를 뽑을 작업 목록(반감이면 보충 판을 돌린 팀만), resA = 그 팀들의 결과
    if (learned) {
      const c=S.learned, fr=S.screen.firstRuns||1, res1={}, models=[], selections=[], enc=Learned.encoder(rows,results,roster,S.placement);
      let completed=0, stageTeams=pl.stages[0].teams;
      const evaluate=async (jobs,msg)=>{
        completed+=await SS.evaluateMissing(jobs,res1,r=>!!r?.cosmo,missing=>run(missing,fr,1,msg,0,completed,stageTeams));
        if(stale())throw Object.assign(new Error('취소'),{gwenCause:'cancel'});
        if(jobs.some(j=>!res1[j.key]?.cosmo))throw new Error('학습 선별 결과가 누락됨');
      };
      for(let b=0;b<3;b++){
        const {model}=await SS.fitScreen({learner:Learned,S,rows,seed:(cx.sampleSeed||20261119)+b,stale,encoder:()=>enc,
          makeJobs:sample=>bossJobs(S,bosses[b],level,sample,results,cls),
          evaluate:jobs=>evaluate(jobs,`표본 학습: ${bossName(bosses[b])} · ${num(jobs.length)}팀`),value:j=>metric(res1[j.key].cosmo,mode)});models.push(model);
        if(cx.onPhase)cx.onPhase(`예측 채점: ${bossName(bosses[b])} · 전체 ${num(pl.combos)}조합`,stageTeams,{stage:0,teams:stageTeams,runs:fr,games:stageTeams*fr});
        if(cx.onProgress)cx.onProgress(completed,stageTeams);
        selections.push(await Learned.select(S,rows,model,stale));
      }
      await Learned.overlap(S,rows,models,selections,(lists,n,budget)=>bestTriplesAsync(lists,n,budget,stale),stale);
      const prepared=[],plannedByBoss=[];
      for(let b=0;b<3;b++){
        const sel=selections[b],audit=await Learned.auditSample(S,rows,sel,(cx.sampleSeed||20261119)+100+b,stale);
        const core=bossJobs(S,bosses[b],level,[...sel.core.values()].map(e=>e.keys),results,cls),aj=bossJobs(S,bosses[b],level,audit.teams,results,cls);
        const keys=new Set(Object.keys(res1).filter(k=>k.startsWith(bosses[b]+'|')));for(const j of [...core,...aj])keys.add(j.key);
        plannedByBoss.push(keys.size);prepared.push({sel,audit,core,aj});
      }
      stageTeams=plannedByBoss.reduce((a,b)=>a+b,0);
      auditInfo=[];
      for(let b=0;b<3;b++){
        const {sel,audit,core,aj}=prepared[b];
        await evaluate([...core,...aj],`1단계: 학습 후보·무작위 감사 ${bossName(bosses[b])}`);
        const info=Learned.audit(c,models[b].rho,core.map(j=>metric(res1[j.key].cosmo,mode)),aj.map(j=>metric(res1[j.key].cosmo,mode)),aj.length,audit.excluded,passCount(S,core.length,pl.keep));
        const record={boss:bosses[b],...info,core:core.length,overlap:sel.overlap.size};
        auditInfo.push(record);
        if(info.fallback && S.maxCombos > 0 && pl.combos > S.maxCombos){
          const factor=c.fallbackMultiplier;
          const expanded=SS.expandedSettings(S);
          if(cx.onPhase)cx.onPhase(`후보 확대 복귀: ${bossName(bosses[b])} · 예측 재선별 ${num(factor)}배`,stageTeams,{stage:0,teams:stageTeams,runs:fr,games:stageTeams*fr});
          if(cx.onProgress)cx.onProgress(completed,stageTeams);
          const wider=await Learned.select(expanded,rows,models[b],stale);
          // 기존 겹침 회피 후보도 유지한다. 이미 계산한 표본·감사 결과는 evaluate가 재사용한다.
          for(const [id,e] of sel.core)wider.core.set(id,e);
          wider.overlap=sel.overlap;
          const extraAudit=await Learned.auditSample(expanded,rows,wider,(cx.sampleSeed||20261119)+100+b,stale);
          const extraCore=bossJobs(S,bosses[b],level,[...wider.core.values()].map(e=>e.keys),results,cls);
          const extraJobs=bossJobs(S,bosses[b],level,extraAudit.teams,results,cls);
          stageTeams+=[...extraCore,...extraJobs].filter(j=>!res1[j.key]?.cosmo).length;
          await evaluate([...extraCore,...extraJobs],`후보 확대 복귀: ${bossName(bosses[b])} · 후보·감사 ${num(factor)}배 확인 (결과 재사용)`);
          selections[b]=wider;
          Object.assign(record,{expanded:true,multiplier:factor,expandedCore:extraCore.length,
            expandedAudit:Learned.audit(expanded.learned,models[b].rho,extraCore.map(j=>metric(res1[j.key].cosmo,mode)),extraJobs.map(j=>metric(res1[j.key].cosmo,mode)),extraJobs.length,extraAudit.excluded,passCount(S,extraCore.length,pl.keep))});
        } else if(info.fallback){
          stageTeams+=pl.combos-plannedByBoss[b];
          // 복귀도 작업은 512팀씩 생성. 이미 완료한 표본·후보의 첫 판은 그대로 재사용.
          let batch=[];
          for(const keys of GS.iterateCombos({...S,newSearch:true},rows)){
            batch.push(keys);
            if(batch.length===512){await evaluate(bossJobs(S,bosses[b],level,batch,results,cls),`학습 감사 복귀: ${bossName(bosses[b])} 전수 확인 (결과 재사용)`);batch=[];}
          }
          if(batch.length)await evaluate(bossJobs(S,bosses[b],level,batch,results,cls),`학습 감사 복귀: ${bossName(bosses[b])} 전수 확인 (결과 재사용)`);
        }
      }
      // 결과 인덱스에는 가벼운 조합 정보만 유지한다. party/options는 실제 실행 직전에 생성.
      for(let i=0;i<3;i++){
        const b=bosses[i],eligible=new Set([...prepared[i].core,...prepared[i].aj].map(j=>j.key));
        for(const keys of GS.iterateCombos({...S,newSearch:true},rows)){
          const p=GS.party(keys,results,cls,S.placement?.baseline?Placement.baseline(keys,results):undefined),key=jobKey(b,keys,level,null,p);
          if(res1[key]?.cosmo&&(auditInfo[i].fallback||eligible.has(key)))jobsA.push({key,boss:b,keys,order:p.order,leaderKey:p.leaderKey});
        }
      }
      learnedSelections=selections;allJobs=jobsA;firstResults=res1;
      jobsK=[];
      bosses.forEach((b,i)=>{const jb=jobsA.filter(j=>j.boss===b),n=passCount(S,jb.length,pl.keep),ranked=pickTop(jb,res1,mode),keep=Learned.preserve(ranked,pickPass(jb,res1,mode,n),c.M*(auditInfo[i].multiplier||1),selections[i].overlap);pushAll(jobsK, bossJobs(S,b,level,keep.map(e=>e.keys),results,cls));});
      passed=Math.max(...bosses.map(b=>jobsK.filter(j=>j.boss===b).length));
      const more=S.screen.runs-fr,res2=more>0?await run(shuffled(jobsK,20261108),more,4,'1단계 보충: 학습 후보·구원자별 대안·겹침 회피 확인',1):{};
      if(stale())return null;resA={};for(const j of jobsK){const a=res1[j.key],b=res2[j.key];if(more>0&&!b?.cosmo)throw new Error('보충 계산 결과가 누락됨');resA[j.key]=b?{...b,cosmo:mergeSummary(a.cosmo,b.cosmo,S.topQ)}:a;}
    } else if (!pl.halved) {
      resA = await run(shuffled(jobsA, 20261106), S.screen.runs, 1, `1단계: 보스 3명 × 조합 ${num(list.length)}개를 훑어보는 중(처음 한 번은 계산 엔진을 내려받느라 1~3분 더 걸림)`, 0);
      if (stale()) return null;
      jobsK = jobsA;
      firstResults = resA;
    } else {
      const fr = S.screen.firstRuns, more = S.screen.runs - fr;
      const res1 = await run(shuffled(jobsA, 20261106), fr, 1, `1단계 (1/2): 전체 조합 확인 · ${num(jobsA.length)}팀을 ${num(fr)}판씩 훑는 중(처음 한 번은 계산 엔진을 내려받느라 1~3분 더 걸림)`, 0);
      firstResults = res1;
      if (stale()) return null;
      // 보스마다 첫 판 순위 상위 pl.pass 팀(경계 동점 포함)만 남은 판을 돌린다. 시드는 첫 판과 다른 값(같은 난수로 같은 판을 되풀이하지 않도록)
      const keepJobs = bosses.map(b => { const jb = jobsA.filter(j => j.boss === b), ks = new Set(pickPass(jb, res1, mode, pl.pass).map(e => idOf(e.keys))); return jb.filter(j => ks.has(idOf(j.keys))); });
      jobsK = [].concat(...keepJobs);
      passed = Math.max(...keepJobs.map(k => k.length));
      const res2 = await run(shuffled(jobsK, 20261108), more, 4, `1단계 (2/2): 첫 판 상위 약 ${num(pl.pass)}팀(동점 포함 보스당 최대 ${num(passed)}팀)을 ${num(more)}판 더 확인 중`, 1);
      if (stale()) return null;
      resA = {};
      for (const j of jobsK) {
        const a = res1[j.key], b = res2[j.key];
        if (a && a.cosmo && b && b.cosmo) resA[j.key] = Object.assign({}, b, {cosmo: mergeSummary(a.cosmo, b.cosmo, S.topQ)});
        else if (a && a.cosmo) resA[j.key] = a;
      }
    }
    const traits=Object.fromEntries(roster.map(r=>[r.key,r.placementTraits||[]]));
    const representative=[],tacticalByBoss=new Map();
    // Audit both the rerank boundary and uniform excluded samples; keep strata visible.
    for(const [bi,b] of (S.placement?.enabled?bosses:[]).entries()){
      const selected=new Set(jobsK.filter(j=>j.boss===b).map(j=>idOf(j.keys))),samples=[];
      const rng=Learned.random((cx.sampleSeed||20261119)+900+bi),n=S.placement?.auditTeams??12;
      const ranked=pickTop(jobsK.filter(j=>j.boss===b),resA,mode),boundary=ranked.slice(pl.keep,pl.keep+Math.floor(n/2)).map(t=>t.keys),randomN=n-boundary.length;let seen=0;
      for(const keys of GS.iterateCombos({...S,newSearch:true},rows))if(!selected.has(idOf(keys))){
        SS.reservoir(samples,keys,randomN,++seen,rng);
      }
      const random=samples.slice();pushAll(samples,boundary);
      const levels=auto?[...new Set([0,level,cx.levelMax,...(cx.boundaries?.[b]||[])])]:[level],auditJobs=[];
      for(const keys of samples)for(const p of Placement.variants(keys,results,traits))for(const leaderKey of keys)for(const l of levels)
        pushAll(auditJobs,bossJobs(S,b,l,[keys],results,cls,null,leaderKey?{...p,leaderKey}:undefined));
      if(!auditJobs.length){representative.push({boss:b,sampled:0,misses:0,rate:0});continue;}
      const ar=await run(auditJobs,S.screen.runs,11,'예선 대표 난이도·배치 놓침 감사',null);
      if(stale())return null;
      if(auditJobs.some(j=>!ar[j.key]?.cosmo))throw Error('배치 감사 결과가 누락됨');
      const edge=metric(ranked[Math.min(pl.keep,ranked.length)-1]?.st||{},mode)||0;
      const audit=SS.placementAudit({sampled:samples,boundary,random,ranked:pickTop(auditJobs,ar,mode,undefined,true),
        id:t=>idOf(Array.isArray(t)?t:t.keys),value:t=>metric(t.st,mode),edge}),misses=audit.misses;
      // Recover sampled tactical teams at the representative level before reranking.
      tacticalByBoss.set(b,misses);
      const recovered=bossJobs(S,b,level,misses.map(t=>t.keys),results,cls);
      if(recovered.length){const rr=await run(recovered,S.screen.runs,12,'감사에서 찾은 후보 복귀',null);Object.assign(resA,rr);
        for(const target of new Set([jobsK,allJobs])){const existing=new Set(target.map(j=>j.key));pushAll(target,recovered.filter(j=>!existing.has(j.key)));}}
      representative.push({boss:b,...audit.summary,expanded:audit.summary.rate>(S.learned?.missThreshold??.04)});
    }
    const searchS=representative.some(a=>a.expanded)?{...S,rerank:{...S.rerank,keep:S.rerank.keep*2}}:S;
    const retry = retryPlan(searchS, list.length), budget = {remaining: retry.maxChecks, exhausted: false};
    const jobsB = [], resB = {}, evaluated = new Set(), attempts = [];
    const screening = Object.assign({}, firstResults, resA);
    let triples = [], lists = [], kept = pl.keep, rerankSpent=0;
    for (const [attempt, limit] of retry.limits.entries()) {
      let extra = [];
      bosses.forEach(b => {
        const source = (attempt ? allJobs : jobsK).filter(j => j.boss === b);
        const ranked = pickTop(source, attempt ? screening : resA, mode);
        // 빠른 선별에서 한 번도 계산하지 않은 후보도 복귀한다. 정밀 계산은 여기서 한 번만 한다.
        const rankedIds = new Set(ranked.map(e => idOf(e.keys)));
        if (attempt) for (const j of source) if (!rankedIds.has(idOf(j.keys))) ranked.push(j);
        const selected = learned ? Learned.preserve(ranked,diverseRows(ranked,limit),S.learned.M*(auditInfo[bosses.indexOf(b)].multiplier||1),learnedSelections[bosses.indexOf(b)].overlap) : diverseRows(ranked, limit), have = new Set(jobsB.filter(j => j.boss === b).map(j=>idOf(j.keys))).size;
        const pending=selected.filter(e => !evaluated.has(b+"|"+idOf(e.keys)));
        if(learned && have+pending.length>retry.limits[retry.limits.length-1])throw new Error('구원자별 보장을 유지하기에 정밀 후보 상한이 부족함');
        const fresh = learned ? pending : pending.slice(0, Math.max(0, limit - have));
        const leaders=representative.find(a=>a.boss===b)?.expanded;
        for(const e of fresh)for(const p of (S.placement?.enabled?Placement.variants(e.keys,results,traits):[GS.party(e.keys,results,cls,S.placement?.baseline?Placement.baseline(e.keys,results):undefined)]))for(const leaderKey of (leaders?e.keys:[p.leaderKey]))pushAll(extra,bossJobs(S,b,level,[e.keys],results,cls,null,leaderKey?{...p,leaderKey}:undefined));
      });
      extra=[...new Map(extra.map(j=>[j.key,j])).values()];
      if (!extra.length) continue;
      // A missed tactical screen expands leaders, not the number of full 20-run trials.
      // Compare every variant/leader briefly, then refine two layouts per composition.
      if(representative.some(a=>a.expanded)){
        const shortRuns=Math.min(S.rerank.runs,S.placement?.screenRuns||2);
        if(S.retry&&rerankSpent+extra.length*shortRuns>S.retry.maxRerankGames)throw Error('복수 배치 정밀 계산 상한에 도달함');
        const screened=await run(extra,shortRuns,13,'확대 후보 배치·리더 예비 비교',null);rerankSpent+=extra.length*shortRuns;
        const seen=new Map();extra=Placement.best(extra,screened,PlacementSearch.cmp(mode),r=>!!r?.cosmo).filter(j=>{const k=j.boss+'|'+idOf(j.keys),n=seen.get(k)||0;seen.set(k,n+1);return n<(S.placement?.keep||2);});
      }
      const carry = jobsB.length;
      if(S.retry && rerankSpent+extra.length*S.rerank.runs>S.retry.maxRerankGames)throw Object.assign(Error('복수 배치 정밀 계산 상한에 도달함'),{gwenCause:'calculation'});
      const msg = attempt ? `후보 확대 ${attempt}/${retry.limits.length - 1}: 겹침 없는 3팀을 위해 보스별 최대 ${num(limit)}팀 확인 중(기존 결과 재사용)` : `2단계: 보스별 상위 ${num(limit)}팀을 더 정확히 확인 중`;
      Object.assign(resB, await run(shuffled(extra, 20261107), S.rerank.runs, 3, msg, 2, carry));
      rerankSpent+=extra.length*S.rerank.runs;
      if (stale()) return null;
      if (extra.some(j => !resB[j.key] || !resB[j.key].cosmo))
        throw Object.assign(new Error("정밀 계산 결과가 누락됨. 다시 시도 필요"), {gwenCause: "calculation"});
      extra.forEach(j => evaluated.add(j.boss+"|"+idOf(j.keys))); pushAll(jobsB, extra);
      lists = bosses.map(b => pickTop(jobsB.filter(j => j.boss === b), resB, mode,undefined,true).map(e => Object.assign({score: metric(e.st, mode)}, e)));
      if(S.placement?.enabled)lists=lists.map((list,i)=>{
        const by=new Map(list.map(t=>[idOf(t.keys),t]));
        for(const t of tacticalByBoss.get(bosses[i])||[]){const old=by.get(idOf(t.keys));if(!old||metric(t.st,mode)>old.score)by.set(idOf(t.keys),{...t,score:metric(t.st,mode)});}
        return [...by.values()].sort((a,b)=>b.score-a.score||idOf(a.keys).localeCompare(idOf(b.keys)));
      });
      if (cx.onLists) cx.onLists(lists, {attempt, bosses: bosses.slice()});
      kept = Math.max(...lists.map(l => l.length));
      triples = await bestTriplesAsync(lists, S.combine.topTriples, budget, stale);
      attempts.push({limit, added: extra.length, teams: jobsB.length, triples: triples.length});
      if ((learned ? triples.length >= S.combine.topTriples : triples.length) || budget.exhausted) break;
    }
    if (!triples.length) throw Object.assign(new Error(overlapMessage(lists, roster, budget.exhausted || kept < list.length)), {gwenCause: "empty", attempts});
    let rows2,probe=null,joint=null,finalBudget=null;
    if(S.placement?.enabled){
    const unique=new Map();
    triples.forEach(t=>t.teams.forEach((e,i)=>unique.set(bosses[i]+'|'+idOf(e.keys),{...e,boss:bosses[i]})));
    joint=await PlacementSearch.cosmo({teams:[...unique.values()],
      makeJob:(t,l,b,p)=>bossJobs(S,t.boss,l,[t.keys],results,cls,b,p)[0],
      run:(jobs,runs,seed,msg)=>run(jobs,runs,seed,msg,null),mode,level,maxLevel:cx.levelMax,auto,
      breaks:cx.breaks||[],runs:S.final.runs,probeRuns:S.auto?.probeRuns||10,boundaries:cx.boundaries||{},stale,settings:S.placement||{}});
    const finalLists=bosses.map(b=>joint.teams.filter(t=>t.boss===b).map(t=>({...t,score:metric(t.st,mode)})).sort((a,b)=>b.score-a.score));
    finalBudget={remaining:retry.maxChecks};
    rows2=(await bestTriplesAsync(finalLists,S.combine.show,finalBudget,stale)).map(r=>({...r,sum2:r.teams.reduce((s,t)=>s+other(t.st,mode),0)}));

    }else{
    // 난이도 자동: 보스마다 난이도를 따로 고를 수 있으므로(게임이 허용), 뽑은 삼중의 모든 팀을 난이도 0~최대에서 짧게 돌려 팀별로 점수가 가장 큰 난이도를 정하고
    // 그 합이 큰 순으로 삼중을 다시 매긴다. 이 뒤 단계는 시간 안내(ETA) 단계에 없어 stage=null 로 알린다(화면은 안내를 끈다)
    let levelOf = () => level;
    if (auto) {
      const lvls = Array.from({length: cx.levelMax + 1}, (_, i) => i), pr = S.auto.probeRuns | 0 || 10;
      const jobsP = [].concat(...lvls.map(l => finalJobs(S, triples, bosses, l, results, cls)));
      const resP = await run(jobsP, pr, 5, `난이도 비교: 후보 편성을 난이도 0~${num(cx.levelMax)}에서 ${num(pr)}판씩 확인 중`, null);
      if (stale()) return null;
      const best = new Map();   // 보스|조합 -> 점수가 가장 큰 난이도(같으면 낮은 난이도)
      for (const t of triples) t.teams.forEach((e, i) => {
        const id = bosses[i] + "|" + idOf(e.keys);
        if (best.has(id)) return;
        let bl = 0, bv = -1;
        for (const l of lvls) { const r = resP[jobKey(bosses[i], e.keys, l,null,e.leaderKey?e:undefined)]; const v = r && r.cosmo ? metric(r.cosmo, mode) : -1; if (v > bv) { bv = v; bl = l; } }
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
    seen.forEach(v => brks.forEach(b => pushAll(jobsC, bossJobs(S, v.boss, v.level, [v.keys], results, cls, b))));
    const resC = await run(jobsC, S.final.runs, 2, `${auto ? "마지막 확인" : "3단계"}: 합이 큰 ${num(triples.length)}개 편성의 팀 ${num(seen.size)}개${brks.length > 1 ? "를 브레이크 스킬 " + num(brks.length - 1) + "종과 함께" : ""} ${num(S.final.runs)}판씩 확인 중`, auto ? null : 3);
    if (stale()) return null;
    rows2 = finalRankBrk(triples, bosses, levelOf, brks, resC, mode, S.combine.show);
    }
    completed=true;
    return {rows: rows2, growthOwned: jobsB.map(j=>({...j,result:resB[j.key]})), pool: rows.length, capped: !learned && S.maxPool > 0, combos: list.length, keep: kept, attempts, combineLimited: triplesLimited(triples, S.combine.topTriples, budget)||(finalBudget?triplesLimited(rows2,S.combine.show,finalBudget):false), triples: triples.length, runs: S.final.runs, level: auto ? null : level, reqLevel: cx.level, probe, mode, bosses: bosses.slice(),
      halved: pl.halved, ...(joint?{representative,placement:{version:Placement.VERSION,conditions:joint.conditions,moved:joint.moved}}:{}), firstRuns: pl.halved ? S.screen.firstRuns : S.screen.runs, screenRuns: S.screen.runs, passed,
      ...(learned ? {learned:true,audit:auditInfo} : {})};
    } finally { if (!cx.session||!completed) session.close(); }
  }

  // 큰 배열을 push(...arr) 로 넘기면 함수 인자 한도(약 12만~)를 넘어 RangeError — 하나씩 넣는다
  function pushAll(out, items) { for (const x of items) out.push(x); return out; }
  const pct = x => pctText(x || 0);
  // 화면 조각. st = {phase: idle|run|done|err, msg, done, total, rows, level, mode, bosses, ...}, cx = {hasInfo, label(key), esc, bossName(key), levelMax, level, mode}
  function table(r, mode, cx, index=0, extra={}) {
    const esc = cx.esc;
    const warning = GS.unsupportedHtml(r.teams, esc);
    if (cx.team) {   // 화면이 카드 모양(앞열·뒤열·리더·브레이크 스킬)을 그려 준다: 보스마다 한 덩어리
      const blocks = r.teams.map(t => seasonUi.team({title:esc(cx.bossName(t.boss)),chips:t.level != null ? ` ${seasonUi.chip(`난이도 ${t.level}`)}` : "",score:`${cx.summary ? "" : `${MODES[mode]} <b>${num(metric(t.st, mode))}</b> · `}${MODES[mode === "top" ? "mean" : "top"]} ${num(other(t.st, mode))}${cx.summary ? "" : ` · 클리어율 ${pct(t.st.clear)}`} · 보스 깎음 ${pct(t.st.frac)}`,body:cx.team(t)})).join("");
      const summary=cx.summary?cx.summary(r,mode,index):seasonUi.score('3팀 합산 점수',num(r.sum),'cs-sum',`${MODES[mode]} 기준`);
      return `${warning}<div data-k="cs-table">${summary}${cx.summary?seasonUi.actions(seasonUi.edit(`data-cs="edit" data-row="${index}"`)+(extra.buttons||''),extra.fold||'',`${MODES[mode]} 기준`):''}${blocks}</div>`;
    }
    const body = r.teams.map(t => `<tr><td>${esc(cx.bossName(t.boss))}${t.level != null ? "<br>난이도 " + t.level : ""}${t.brkTie ? "<br>브레이크 스킬: 점수 차이 없음(아무거나 장착 가능)" : t.brk ? "<br>" + esc(t.brk) : ""}</td><td>${t.order.map(k => esc(cx.label(k))+(k===t.leaderKey?" (리더)":"")).join("<br>")}</td><td><b>${num(metric(t.st, mode))}</b></td><td>${num(other(t.st, mode))}</td><td>${pct(t.st.clear)}</td><td>${pct(t.st.frac)}</td></tr>`).join("");
    return `${warning}<div class="gd-scroll"><table data-k="cs-table"><thead><tr><th>보스</th><th>편성(앞열 → 뒤열, 리더 별도 표시)</th><th>${MODES[mode]}(순위 기준)</th><th>${MODES[mode === "top" ? "mean" : "top"]}</th><th>클리어율</th><th>보스 깎음</th></tr></thead><tbody>${body}<tr><td colspan="2"><b>합계</b></td><td colspan="4"><b data-k="cs-sum">${num(r.sum)}</b></td></tr></tbody></table></div>`;
  }
  const progText = st => `${st.msg || ""}${st.total ? ` · ${num(st.done)}/${num(st.total)}` : ""}`;
  function html(st, cx) {
    const esc = cx.esc;
    const work = (...args) => cx.work ? cx.work(...args) : "";
    const error = cause => cx.error ? cx.error(cause) : work("error");
    const head = '<h3 class="season-title">코스모 게이트</h3>';
    const warn = '<div class="mut gd-small">오토 전투 기준 · 내 정보의 실제 최종 능력치 · 같은 구원자를 여러 보스에 쓰지 않는 3팀(12명) · 점수 합산식은 서버 계산이라 추정이고 시뮬 전체가 아직 실제 플레이와 충분히 대조되지 않았음(참고용). 협공 제외는 적용하지 않음. 시즌이 바뀌면 새 시즌 값이 반영된 뒤에 사용해야 함.</div>';
    if (!cx.hasInfo) return `<div class="gd-search" data-k="cs-search">${head}<div class="mut gd-small">먼저 «내 계정 정보 불러오기»로 내 구원자 불러오기 필요. 불러온 구원자 중에서 3보스 점수 합이 가장 큰 3팀을 찾음.</div></div>`;
    const lv = [`<option value="-1"${cx.level === AUTO ? " selected" : ""}>자동 (최고 점수 난이도)</option>`].concat(Array.from({length: cx.levelMax + 1}, (_, i) => `<option value="${i}"${i === cx.level ? " selected" : ""}>${i === 0 ? "레벨 0(없음)" : "레벨 " + i}</option>`)).join("");
    const md = Object.entries(MODES).map(([k, v]) => `<option value="${k}"${k === cx.mode ? " selected" : ""}>${v}</option>`).join("");
    const opt = `<details class="season-options" data-fold="cs-options"><summary>탐색 설정 <span class="tag">${cx.level===AUTO?'난이도 자동':'난이도 '+cx.level} · ${MODES[cx.mode]}${cx.learned?' · 학습 선별':''}</span></summary><div class="season-fields"><label>난이도 <select data-cs="level">${lv}</select></label> <label>순위 기준 <select data-cs="mode">${md}</select></label> <label><input type="checkbox" data-cs="learned"${cx.learned ? " checked" : ""}> 계정별 점수 학습 선별</label></div><p class="mut">3단계(Step 3) 기준. 상위 점수 = 판별 점수 상위 20%의 평균. 학습 선별을 끄면 기존 전수 탐색으로 돌아감. 예측 확인이 부족하면 전수 상한 이하는 전수 확인하고, 초과하면 후보를 넓혀 찾음.</p></details>`;
    const btn = label => `<button type="button" data-cs="start">${label}</button>`;
    const pre = cx.preEta ? `<div class="mut gd-small" data-k="cs-eta-pre">${esc(cx.preEta)}</div>` : "";
    let body;
    // 진행 표시: 글자 칸(cs-prog, cs-eta)만 갱신하고 취소 버튼은 다시 만들지 않는다(클릭 유실 방지)
    if (st.phase === "run") body = `<div data-k="cs-progress">${work(cx.workMode || "long")}<span data-k="cs-prog">${esc(progText(st))}</span><div class="mut gd-small" data-k="cs-eta">${esc(st.etaText || "")}</div><button type="button" class="sec" data-cs="cancel">취소</button></div>`;
    else if (st.phase === "err") body = `<div class="bad" data-k="cs-err">${error(st.errorCause||"other")}찾지 못했음: ${esc(st.msg || "")}</div>${btn("다시 시도")}${opt}`;
    else if (st.phase === "done") {
      const stale = (st.reqLevel != null ? st.reqLevel : st.level) !== cx.level || st.mode !== cx.mode || !!st.learned !== !!cx.learned ? seasonUi.warning('고른 탐색 설정이 바뀌었음. 아래 결과는 이전 선택 기준이므로 다시 찾기 필요.','data-k="cs-stale"') : "";
      const old = cx.sig != null && st.sig !== cx.sig ? seasonUi.warning('낡은 결과: 내 정보를 다시 불러왔거나 추천에서 뺄 구원자 목록이 바뀌었음. 아래 결과는 이전 기준이므로 다시 찾기 필요.','data-k="cs-old"') : "";
      const rows = st.rows || [];
      const lvInfo = st.probe ? '<div class="mut gd-small" data-k="cs-level">난이도는 보스마다 점수가 가장 높은 값을 따로 골랐음(보스별 난이도·브레이크 스킬은 아래 편성에 표시, 짧은 표본이라 참고용).</div>' : "";

      const expanded = (st.audit || []).filter(a=>a.expanded).map(a=>`<div class="gd-warn" data-k="cs-expanded">${esc(cx.bossName(a.boss))}: 이 보스는 예측 확인이 부족해 후보를 넓혀 찾았음</div>`).join("");
      const rest = expanded + (st.combineLimited ? '<div class="gd-warn" data-k="cs-limit">조합 검사 상한에 도달했음. 이번 결과는 2단계 후보 점수 기준으로 확인한 조합 중에서 골랐으며, 더 높은 점수의 조합이 남아 있을 수 있음.</div>' : '') + rows.slice(1).map((r, i) => `<details class="gd-small"><summary>${i + 2}위 · 합계 ${num(r.sum)}</summary>${table(r, st.mode, cx, i+1)}</details>`).join("");
      const scr = st.learned ? `계정별 표본 학습·예측 선별·무작위 감사를 거쳐${st.audit.some(a=>a.fallback&&!a.expanded)?" 품질 미달 보스는 전수 확인으로 복귀하고":""} 후보를 ${st.screenRuns}판씩 확인하고` : st.halved ? `보스마다 조합 ${num(st.combos)}개를 ${st.firstRuns}판씩 훑고 첫 판 순위 상위 약 ${Math.round(100 * (st.passed / st.combos))}%(동점은 모두 포함, 보스당 최대 ${num(st.passed)}팀)만 ${st.screenRuns - st.firstRuns}판 더 돌려 ${st.screenRuns}판 평균으로 비교하고` : `보스마다 조합 ${num(st.combos)}개를 짧게 훑고`;
      const fold = `<details class="season-options" data-fold="cs-result-basis"><summary>탐색 결과 상세</summary>${lvInfo}<div class="mut gd-small">후보 ${st.pool}명${st.capped ? "(탐색 풀 제한 설정)" : "(보유 육성 구원자 전부)"} → ${scr}, 보스별 상위 ${st.keep}팀을 더 정확히 본 뒤, 겹치지 않는 3팀 중 합이 큰 ${st.triples}개 편성의 팀을 ${st.runs}판씩 다시 돌린 값임(표본이 작아 수천 점은 오차). ${MODES[st.mode]} 기준 합계가 가장 큰 순임. 확인한 후보 조합 중에서 골랐으므로 전체 조합의 수학적 최적은 아닐 수 있음.</div></details>`;
      const first = rows.length ? `${cx.report?.(st.rows)||""}<div data-k="cs-best">${table(rows[0], st.mode, cx,0,{buttons:btn("다시 찾기"),fold})}</div>` : `${error('empty')}<div class="mut">결과 없음</div>`;
      body = `${old}${stale}${first}${rest}${cx.summary&&cx.team&&rows.length?opt:btn("다시 찾기")+opt+fold}`;
    } else body = `${btn("보스 3마리 편성 찾기")}<span class="mut season-wait">몇 분 걸림 · 탭을 열어 둬야 함</span>${opt}`;
    return `<div class="gd-search" data-k="cs-search" data-state="${st.phase}">${head}${body}${seasonUi.basis('cs-basis',`<span class="gd-est">추정</span>${pre}${warn}`)}</div>`;
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

  const api = {MODES, pushAll, searchSettings, workerCount, pickPass, passCount, mergeSummary, shuffled, poolAll, countCombos, feasibility, effKeep, plan, etaNew, priorFrom, fmtDur, etaLine, preText, progText, metric, idOf, jobKey, bossJobs, pickTop, pickDiverse, bestTriples, bestTriplesAsync, triplesLimited, finalJobs, finalRank, finalRankBrk, search, html, table};
  api.retryPlan=retryPlan;
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.CosmoSearch = api;
})(typeof window !== "undefined" ? window : globalThis);
