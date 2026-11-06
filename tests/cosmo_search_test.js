// 코스모 게이트 «3보스 최고 점수 편성 찾기» 로직 시험: 설정, 겹침 없는 삼중 탐색(분기한정) = 전수 비교, 가짜 작업자로 전체 흐름(겹침 금지·최적성·판 수), 화면 조각.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const C = require('../cosmo_search.js'), GS = require('../guild_search.js');
const G = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'cosmo_raid.json'), 'utf8'));
const SE = G.search;
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const BOSSES = G.season.bossOrder;

// 가짜 로스터 13명(딜러 7, 서포터 4, 디펜더 2): 3팀 12명을 채우고 1명이 남는다
const roster = [], results = {};
let pw = 1000;
function add(key, cls) { roster.push({key, cls}); results[key] = {power: pw, stats: {atk: pw}, combat: {x: 1}}; pw -= 10; }
for (let i = 0; i < 7; i++) add('d' + i, i % 2 ? '스트라이커' : '캐스터');
for (let i = 0; i < 4; i++) add('s' + i, '서포터');
for (let i = 0; i < 2; i++) add('f' + i, '디펜더');
const cls = Object.fromEntries(roster.map(r => [r.key, r.cls]));

// 가짜 점수: 보스마다 구원자 값 + 짝 가산(비선형). d0 은 모든 보스에서 압도적이라 보스별 1위 팀이 전부 겹친다.
const val = {};
BOSSES.forEach((b, bi) => roster.forEach((r, ri) => { val[b + r.key] = ((ri * 7 + bi * 13 + 5) * 37) % 101 * 10; }));
BOSSES.forEach(b => { val[b + 'd0'] = 5000; });
function fakeScore(boss, keys) {
  let s = 0;
  for (const k of keys) s += val[boss + k];
  const ks = keys.slice().sort();
  for (let i = 0; i < 4; i++) for (let j = i + 1; j < 4; j++) s += ((ks[i].charCodeAt(0) * 31 + ks[i].charCodeAt(1) * 7 + ks[j].charCodeAt(1) * 11 + boss.length * 3) % 17) * 10;
  return s;
}
const fakeTop = s => s + (s * 7) % 13;     // 상위 점수는 평균과 다른 값
function factory(log, score = fakeScore) {
  return () => ({
    terminate() {}, onmessage: null,
    postMessage(m) {
      log.push(m);
      setTimeout(() => {
        for (const t of m.teams) {
          const keys = t.party.units.map(u => u.key), boss = t.options.cosmo_raid.boss, s = score(boss, keys);
          this.onmessage({data: {type: 'team', key: t.key, result: {prog: 0.5, clear: 0.4, n: m.n_runs, via: {}, progs: null, cosmo: {mean: s, top: fakeTop(s), clear: 0.4, frac: 0.5, n: m.n_runs}}}});
        }
        this.onmessage({data: {type: 'done'}});
      }, 1);
    }
  });
}
const mkS = over => JSON.parse(JSON.stringify(Object.assign({}, SE, {rerank: {keep: 100000, runs: 10}, combine: {topTriples: 10, show: 5}}, over || {})));
const cxOf = (S, log, over) => Object.assign({S, bosses: BOSSES, level: 6, mode: 'mean', results, roster, makeWorker: factory(log), workers: 3, stage: 'x', base: ''}, over || {});

// 전수 비교용: 보스별 모든 조합의 점수 -> 겹치지 않는 모든 삼중 -> 합 큰 순 n 개(같으면 id 작은 순)
function brute(S, mode, n) {
  const rows = C.poolAll(S, results, roster), list = GS.combos(S, rows);
  const f =(b, keys) => { const s = fakeScore(b, keys); return mode === 'top' ? fakeTop(s) : s; };
  const L = BOSSES.map(b => list.map(keys => ({keys, id: C.idOf(keys), s: f(b, keys)})));
  const out = [];
  for (const a of L[0]) for (const b of L[1]) {
    if (a.keys.some(k => b.keys.includes(k))) continue;
    for (const c of L[2]) {
      if (c.keys.some(k => a.keys.includes(k) || b.keys.includes(k))) continue;
      out.push({sum: a.s + b.s + c.s, id: [a.id, b.id, c.id].join('/')});
    }
  }
  out.sort((x, y) => y.sum - x.sum || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
  return out.slice(0, n);
}
const idOfTriple = t => t.teams.map(e => C.idOf(e.keys)).join('/');
const disjoint = teams => { const all = teams.flatMap(t => t.keys); return all.length === 12 && new Set(all).size === 12; };

const tests = {
  config() {
    for (const k of ['maxPool', 'maxCombos', 'minPowerRatio', 'minRole', 'minFront', 'minDealer', 'screen', 'rerank', 'combine', 'final', 'topQ', 'defaultMode', 'defaultLevel', 'etaWeights', 'etaWarmupSec', 'etaWindowSec', 'etaBlendSec']) assert(k in SE, k);
    assert.equal(SE.maxPool, null, '기본은 전수(풀 제한 없음)');
    assert(SE.maxCombos >= 1000, '안전 상한은 설정으로 있고 기본은 충분히 큼');
    assert(SE.etaWeights.length === 3 && SE.etaWeights.every(w => w > 0) && SE.etaWarmupSec >= 0 && SE.etaWindowSec > SE.etaWarmupSec);
    assert(SE.screen.runs >= 1 && SE.rerank.keep >= 1 && SE.rerank.runs >= 1 && SE.final.runs >= 1 && SE.combine.topTriples >= 1 && SE.combine.show >= 1 && SE.combine.show <= SE.combine.topTriples);
    assert(SE.topQ > 0 && SE.topQ <= 1 && C.MODES[SE.defaultMode]);
    assert(Number.isInteger(SE.defaultLevel) && SE.defaultLevel >= 0 && SE.defaultLevel <= G.bosses[0].levels.length);
    assert.deepEqual(BOSSES, ['belgras', 'tyria', 'carnelia']);
    // 앞열 역할 최소 인원 × 3팀 = 풀의 앞열 역할이 3명 이상이어야 3팀이 나온다
    assert((SE.minRole['서포터'] || 0) + (SE.minRole['디펜더'] || 0) >= 3 * (SE.minFront || 0));
  },
  bestTriples_small() {
    const e = (keys, score) => ({keys, score});
    const A = [e(['a', 'b', 'c', 'd'], 100), e(['e', 'f', 'g', 'h'], 90)];
    const B = [e(['a', 'b', 'x', 'y'], 100), e(['i', 'j', 'k', 'l'], 50)];     // 첫 항목은 A[0] 과 겹침
    const Cc = [e(['e', 'f', 'm', 'n'], 100), e(['m', 'n', 'o', 'p'], 10)];     // 첫 항목은 A[1] 과 겹침
    const r = C.bestTriples([A, B, Cc], 3);
    // 가능한 삼중: A0+B1+C0=250, A1+B0+C1=200, A0+B1+C1=160, A1+B1+C1=150 (나머지는 겹침)
    assert.deepEqual(r.map(t => t.sum), [250, 200, 160]);
    assert.deepEqual(C.bestTriples([A, B, Cc], 9).map(t => t.sum), [250, 200, 160, 150]);
  },
  bestTriples_vs_brute() {
    // 무작위 목록(동점 많음)에서 분기한정 결과 = 전수 결과(합·id 순서까지)
    let seed = 12345;
    const rnd = n => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed % n; };
    const pool = Array.from({length: 15}, (_, i) => 'u' + String(i).padStart(2, '0'));
    for (let trial = 0; trial < 40; trial++) {
      const lists = [0, 1, 2].map(() => {
        const L = [], seen = new Set();
        for (let i = 0; i < 40; i++) {
          const ks = pool.slice().sort(() => rnd(3) - 1).slice(0, 4);
          const id = C.idOf(ks); if (seen.has(id)) continue; seen.add(id);
          L.push({keys: ks, score: rnd(12) * 10});         // 점수 12가지 -> 동점 많음
        }
        return L.sort((a, b) => b.score - a.score);
      });
      const n = [1, 5, 10][trial % 3];
      const want = [];
      for (const a of lists[0]) for (const b of lists[1]) for (const c of lists[2]) {
        const all = [...a.keys, ...b.keys, ...c.keys];
        if (new Set(all).size !== 12) continue;
        want.push({sum: a.score + b.score + c.score, id: [a, b, c].map(x => C.idOf(x.keys)).join('/')});
      }
      want.sort((x, y) => y.sum - x.sum || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
      const got = C.bestTriples(lists, n);
      assert.deepEqual(got.map(t => [t.sum, idOfTriple(t)]), want.slice(0, n).map(x => [x.sum, x.id]), 'trial ' + trial);
      assert(got.every(t => disjoint(t.teams)));
    }
  },
  bestTriples_edge() {
    assert.deepEqual(C.bestTriples([[], [], []], 5), []);
    const same = [{keys: ['a', 'b', 'c', 'd'], score: 5}];
    assert.deepEqual(C.bestTriples([same, same, same], 5), [], '같은 팀뿐이면 삼중 없음');
    // 30명을 넘는 구원자(마스크 2단어 이상)도 겹침을 제대로 본다
    const mk = base => ({keys: [0, 1, 2, 3].map(i => 'z' + (base + i)), score: 1});
    const r = C.bestTriples([[mk(0)], [mk(30)], [mk(60)]], 1);
    assert.equal(r.length, 1);
    assert.deepEqual(C.bestTriples([[mk(0)], [mk(2)], [mk(60)]], 1), [], 'z2·z3 겹침');
  },
  async search_optimal_and_disjoint() {
    for (const mode of ['mean', 'top']) {
      const S = mkS(), log = [];
      const naive = BOSSES.map(b => { let best = null; for (const keys of GS.combos(S, C.poolAll(S, results, roster))) { const s = fakeScore(b, keys); if (!best || s > best.s) best = {s, keys}; } return best.keys; });
      assert(new Set(naive.flat()).size < 12, '전제: 보스별 1위 팀을 따로 고르면 겹친다(d0)');
      const out = await C.search(cxOf(S, log, {mode}));
      assert(out.rows.length > 0 && out.rows.length <= S.combine.show);
      for (const r of out.rows) {
        assert(disjoint(r.teams), '겹침 금지: ' + r.teams.map(t => t.keys.join()).join(' | '));
        assert.deepEqual(r.teams.map(t => t.boss), BOSSES);
        assert.equal(r.sum, r.teams.reduce((a, t) => a + C.metric(t.st, mode), 0));
      }
      assert(out.rows.every((r, i) => !i || out.rows[i - 1].sum >= r.sum), '합 큰 순');
      // 최적성: 전수 탐색의 1위 합과 같고, 상위 목록의 합도 같은 순서
      const want = brute(S, mode, out.rows.length);
      assert.deepEqual(out.rows.map(r => r.sum), want.map(w => w.sum), mode);
      assert.equal(idOfTriple({teams: out.rows[0].teams}), want[0].id);
      // 판 수·옵션: 1단계 2판(전 조합), 2단계·3단계 판 수는 S 설정대로. 모든 작업이 Step 3·고른 레벨·보스 키로 나감
      const runs = [...new Set(log.map(m => m.n_runs))];
      assert.deepEqual(runs, [S.screen.runs, S.rerank.runs, S.final.runs]);
      const sent = log.flatMap(m => m.teams);
      assert(sent.every(t => t.options.cosmo_raid.step === 3 && t.options.cosmo_raid.level === 6 && BOSSES.includes(t.options.cosmo_raid.boss) && t.options.cosmo_top_q === SE.topQ));
      assert(sent.every(t => t.party.units.length === 4 && t.party.units.every(u => u.stats_final === true && u.stats_override === results[u.key].stats)), '내 최종 능력치가 그대로 작업자에게 감');
      const nCombos = GS.combos(S, C.poolAll(S, results, roster)).length;
      assert.equal(log.filter(m => m.n_runs === SE.screen.runs).reduce((a, m) => a + m.teams.length, 0), nCombos * 3, '1단계는 보스 3 × 전 조합');
      assert(log.filter(m => m.n_runs === SE.final.runs).reduce((a, m) => a + m.teams.length, 0) <= out.triples * 3);
    }
  },
  async search_small_keep_still_disjoint() {
    // K 를 작게 해도 겹침 금지는 유지된다(최적은 보장 못 해도 합은 전수 1위 이하)
    const S = mkS({rerank: {keep: 200, runs: 10}}), log = [];
    const out = await C.search(cxOf(S, log));
    assert(out.rows.length > 0 && out.rows.every(r => disjoint(r.teams)));
    assert(out.rows[0].sum <= brute(mkS(), 'mean', 1)[0].sum);
    assert.equal(log.filter(m => m.n_runs === 10).reduce((a, m) => a + m.teams.length, 0), 600, '2단계는 보스당 K 팀');
  },
  pickDiverse_keeps_alternatives() {
    // 상위 팀이 전부 u0 를 포함해도, u0 가 없는 좋은 팀이 후보에 남는다(보스 3명이 u0 를 원할 때 대안)
    const jobs = [], res = {};
    const units = Array.from({length: 8}, (_, i) => 'u' + i);
    let n = 0;
    for (let a = 0; a < 8; a++) for (let b = a + 1; b < 8; b++) for (let c = b + 1; c < 8; c++) for (let d = c + 1; d < 8; d++) {
      const keys = [units[a], units[b], units[c], units[d]], key = keys.join('+'); n++;
      jobs.push({key, keys, order: keys, boss: 'x'});
      res[key] = {cosmo: {mean: (a === 0 ? 10000 : 0) + 1000 - n, top: 0, clear: 0, frac: 0, n: 2}};
    }
    const top = C.pickTop(jobs, res, 'mean', 20), div = C.pickDiverse(jobs, res, 'mean', 20);
    assert(top.every(e => e.keys.includes('u0')), '전제: 단순 상위는 전부 u0');
    assert.equal(div.length, 20);
    assert(div.some(e => !e.keys.includes('u0')), '다양성: u0 없는 팀 포함');
    assert.deepEqual(div.slice(0, 10).map(e => e.keys), top.slice(0, 10).map(e => e.keys), '절반은 순위대로');
    assert.equal(new Set(div.map(e => e.keys.join())).size, 20, '중복 없음');
    assert.equal(C.pickDiverse(jobs, res, 'mean', 1000).length, jobs.length, 'n 이 더 크면 전부');
  },
  async search_errors_and_cancel() {
    const few = Object.fromEntries(Object.entries(results).slice(0, 11));
    await assert.rejects(C.search(cxOf(mkS(), [], {results: few})), /부족/);
    // 앞열 역할이 3명 미만이라 팀 규칙(앞열 1명 이상)을 3팀이 못 맞추면 겹치지 않는 삼중 없음
    const noFront = roster.filter(r => r.key.startsWith('d')).concat(roster.filter(r => r.key.startsWith('s')).slice(0, 2)).concat(roster.filter(r => r.key.startsWith('f')).slice(0, 1));
    await assert.rejects(C.search(cxOf(mkS({minFront: 1, minDealer: 1}), [], {roster: noFront.slice(0, 12)})), /겹치지 않는|부족/);
    // stale 이면 결과를 내지 않고 null
    const r = await C.search(cxOf(mkS(), [], {stale: () => true}));
    assert.equal(r, null);
    // 작업자 오류는 reject
    const bad = () => ({terminate() {}, onmessage: null, postMessage() { setTimeout(() => this.onmessage({data: {type: 'error', msg: '터짐'}}), 1); }});
    await assert.rejects(C.search(cxOf(mkS(), [], {makeWorker: bad})), /터짐/);
    // 취소: onHandle 로 받은 핸들을 cancel 하면 reject(취소)
    let h; const slow = () => ({terminate() {}, onmessage: null, postMessage() {}});
    const p = C.search(cxOf(mkS(), [], {makeWorker: slow, onHandle: x => { h = x; }}));
    setTimeout(() => h.cancel(), 5);
    await assert.rejects(p, /취소/);
  },
  progress_and_phase_callbacks() {
    return (async () => {
      const phases = [], prog = [];
      const out = await C.search(cxOf(mkS(), [], {onPhase: (m, t) => phases.push([m, t]), onProgress: (d, t) => prog.push([d, t])}));
      assert.equal(phases.length, 3);
      assert(/1단계/.test(phases[0][0]) && /2단계/.test(phases[1][0]) && /3단계/.test(phases[2][0]));
      assert(prog.length > 0 && out.rows.length > 0);
    })();
  },
  jobs_distinct_and_summary_only() {
    const rows = C.poolAll(mkS(), results, roster), list = GS.combos(mkS(), rows);
    const jobs = C.bossJobs(mkS(), 'tyria', 7, list, results, cls);
    assert.equal(new Set(jobs.map(j => j.key)).size, jobs.length);
    assert(jobs.every(j => j.key.startsWith('tyria|') && j.options.cosmo_raid.level === 7));
    // 같은 조합을 다른 보스에 쓰면 키가 다르다(보스 결과가 섞이지 않음)
    assert.notEqual(C.bossJobs(mkS(), 'belgras', 7, [list[0]], results, cls)[0].key, jobs.find(j => j.keys === list[0]).key);
    // 판별 배열 없는 요약만 다음 단계로: 요약이 없는 결과는 순위에서 빠진다
    const res = {[jobs[0].key]: {cosmo: {mean: 5, top: 9, clear: 1, frac: 1, n: 2}}, [jobs[1].key]: {prog: 1, cosmo: null}};
    assert.deepEqual(C.pickTop(jobs, res, 'mean').map(r => r.keys), [jobs[0].keys]);
  },
  pickTop_modes() {
    const mk = (id, mean, top) => ({key: id, keys: [id], order: [id], boss: 'b'});
    const jobs = ['a', 'b', 'c'].map(x => mk(x));
    const res = {a: {cosmo: {mean: 100, top: 300, clear: 0.1}}, b: {cosmo: {mean: 200, top: 250, clear: 0.2}}, c: {cosmo: {mean: 200, top: 260, clear: 0.0}}};
    assert.deepEqual(C.pickTop(jobs, res, 'mean').map(r => r.keys[0]), ['c', 'b', 'a'], '평균 같으면 상위 점수');
    assert.deepEqual(C.pickTop(jobs, res, 'top').map(r => r.keys[0]), ['a', 'c', 'b']);
    assert.equal(C.pickTop(jobs, res, 'mean', 2).length, 2);
  },
  pool_is_full_by_default() {
    // 전투력이 아주 낮은 구원자와 전투력 0(미육성)이 섞여 있어도: 기본은 전투력>0 전부, 역할 보충·하한 없음
    const rs = roster.concat([{key: 'low', cls: '캐스터'}, {key: 'zero', cls: '캐스터'}]);
    const rr = Object.assign({}, results, {low: {power: 1, stats: {atk: 1}, combat: {}}, zero: {power: 0, stats: {atk: 0}, combat: {}}});
    const rows = C.poolAll(SE, rr, rs);
    assert.equal(rows.length, 14, '13명 + 낮은 전투력 1명 (미육성 제외)');
    assert(rows.some(r => r.key === 'low') && !rows.some(r => r.key === 'zero'));
    // 풀 제한 설정(maxPool)을 줬을 때만 자르고, 앞열 역할을 보충한다
    const capped = C.poolAll(Object.assign({}, SE, {maxPool: 6, minPowerRatio: 0, minRole: {'서포터': 2, '디펜더': 2}}), rr, rs);
    assert(capped.length >= 6 && capped.filter(r => r.cls === '서포터').length >= 2 && capped.filter(r => r.cls === '디펜더').length >= 2 && !capped.some(r => r.key === 'low'));
  },
  countCombos_matches_enumeration() {
    for (const over of [{}, {minFront: 0, minDealer: 0}, {minFront: 2, minDealer: 1}, {minFront: 1, minDealer: 3}]) {
      const S = mkS(over), rows = C.poolAll(S, results, roster);
      assert.equal(C.countCombos(S, rows), GS.combos(S, rows).length, JSON.stringify(over));
    }
  },
  feasibility_messages() {
    const S = mkS(), rowsOf = keys => C.poolAll(S, results, roster.filter(r => keys.includes(r.key)));
    const dealers = roster.filter(r => r.key[0] === 'd').map(r => r.key);       // 7명
    assert.equal(C.feasibility(S, C.poolAll(S, results, roster)), null);
    assert.match(C.feasibility(S, rowsOf(dealers.concat(['s0', 's1']))), /부족.*9명.*12명 필요/, '인원 부족');
    assert.equal(C.feasibility(S, rowsOf(dealers.concat(['s0', 's1', 'f0', 'f1', 's2']))), null, '앞열 5명이면 가능');
    // 딜러 부족: 인원은 충분하고 딜러만 모자란 경우(앞열 10 딜러 2)
    const S0 = mkS({minFront: 1, minDealer: 1}), many = Array.from({length: 10}, (_, i) => ({key: 'x' + i, cls: '서포터'})).concat([{key: 'y0', cls: '캐스터'}, {key: 'y1', cls: '캐스터'}]);
    const rr = Object.fromEntries(many.map((r, i) => [r.key, {power: 100 - i, stats: {}, combat: {}}]));
    const rows = C.poolAll(S0, rr, many);
    assert.match(C.feasibility(S0, rows), /딜러.*부족.*2명.*3명 필요/);
    assert.equal(C.countCombos(S0, rows), GS.combos(S0, rows).length);
  },
  async search_fails_fast_when_roles_short() {
    const log = [];
    const many = Array.from({length: 10}, (_, i) => ({key: 'x' + i, cls: '서포터'})).concat([{key: 'y0', cls: '캐스터'}, {key: 'y1', cls: '캐스터'}]);
    const rr = Object.fromEntries(many.map((r, i) => [r.key, {power: 100 - i, stats: {}, combat: {}}]));
    await assert.rejects(C.search(cxOf(mkS(), log, {roster: many, results: rr})), /딜러.*부족/);
    const fronts = Array.from({length: 2}, (_, i) => ({key: 'x' + i, cls: '서포터'})).concat(Array.from({length: 10}, (_, i) => ({key: 'y' + i, cls: '캐스터'})));
    const r2 = Object.fromEntries(fronts.map((r, i) => [r.key, {power: 100 - i, stats: {}, combat: {}}]));
    await assert.rejects(C.search(cxOf(mkS(), log, {roster: fronts, results: r2})), /앞열 역할.*부족.*2명.*3명 필요/);
    assert.equal(log.length, 0, '작업자를 띄우기 전에 안내');
  },
  async search_maxcombos_guard() {
    const log = [];
    await assert.rejects(C.search(cxOf(mkS({maxCombos: 100}), log)), /안전 상한/);
    assert.equal(log.length, 0);
  },
  async keep_raised_when_combos_small() {
    // 조합 665개: keep 400(2배 800 이상)이면 전체를 넘기고, keep 200(2배 400 미만)이면 200
    for (const [keep, want] of [[400, 665], [200, 200]]) {
      const S = mkS({rerank: {keep, runs: 10}}), log = [], rows = C.poolAll(S, results, roster);
      assert.equal(C.countCombos(S, rows), 665);
      assert.equal(C.effKeep(S, 665), want);
      const out = await C.search(cxOf(S, log));
      assert.equal(out.keep, want);
      assert.equal(log.filter(m => m.n_runs === 10).reduce((a, m) => a + m.teams.length, 0), 3 * want);
      assert(out.rows.length > 0 && out.rows.every(r => disjoint(r.teams)));
    }
    // 조합이 keep 보다 적은 경우(keep > L)도 L 로
    assert.equal(C.effKeep({rerank: {keep: 300}}, 120), 120);
    assert.equal(C.effKeep({rerank: {keep: 300}}, 601), 300);
    assert.equal(C.effKeep({rerank: {keep: 300}}, 600), 600);
  },
  async plan_matches_actual_jobs() {
    const S = mkS({rerank: {keep: 200, runs: 10}}), log = [], phases = [], done = [];
    let planned;
    const out = await C.search(cxOf(S, log, {onPlan: p => { planned = p; }, onPhase: (m, t, info) => phases.push(info), onProgress: (d, t) => done.push([d, t])}));
    assert(planned && planned.stages.length === 3 && planned.total === planned.stages.reduce((a, s) => a + s.games, 0));
    // 1·2단계 판 수는 시작 전 계획과 정확히 같고, 3단계는 상한 이하
    assert.equal(phases[0].games, planned.stages[0].games);
    assert.equal(phases[1].games, planned.stages[1].games);
    assert(phases[2].games <= planned.stages[2].games && phases[2].games > 0);
    assert.deepEqual(phases.map(p => p.stage), [0, 1, 2]);
    assert.equal(planned.stages[0].games, 3 * 665 * S.screen.runs);
    assert.equal(planned.combos, 665);
    assert.equal(out.combos, 665);
    // 진행 콜백의 마지막 값 = 단계 팀 수
    assert(done.some(([d, t]) => d === t && t === phases[0].teams));
  },
  async jobs_are_shuffled_but_results_unchanged() {
    const a = Array.from({length: 500}, (_, i) => i), s1 = C.shuffled(a, 7), s2 = C.shuffled(a, 7);
    assert.deepEqual(s1, s2, '같은 시드는 같은 순서');
    assert.deepEqual(s1.slice().sort((x, y) => x - y), a, '원소 보존');
    assert(s1.filter((v, i) => v === i).length < 20 && s1 !== a, '실제로 섞임');
    assert.deepEqual(a, Array.from({length: 500}, (_, i) => i), '원본 불변');
    // 1단계로 나간 작업 순서가 전투력 순(조합 열거 순)이 아니고 보스가 뒤섞여 있다. 최적성은 search_optimal_and_disjoint 가 그대로 확인
    const log = [], S = mkS();
    await C.search(cxOf(S, log, {workers: 1}));
    const first = log.find(m => m.n_runs === SE.screen.runs).teams.slice(0, 60);
    assert(new Set(first.map(t => t.options.cosmo_raid.boss)).size === 3, '초반 작업에 보스 3명이 섞임');
    const rank = t => t.party.units.reduce((acc, u) => acc + parseInt(u.key.slice(1), 10), 0);
    assert(first.some((t, i) => i && rank(t) < rank(first[i - 1])) && first.some((t, i) => i && rank(t) > rank(first[i - 1])), '정렬되어 있지 않음');
  },
  // ---- 남은 시간 ----
  eta_blend_with_prior() {
    // 실제 속도 0.01초/판, 저장값 0.02초/판. 측정 초반엔 저장값과 섞이고 blend 초가 지나면 측정값만 쓴다.
    const mk = blend => { const e = C.etaNew({stages: [{games: 10000}, {games: 100}, {games: 100}], weights: [1, 1, 1], warmup: 1, window: 20, prior: [0.02, 0.02, 0.02], blend}); e.begin(0, 10000, 0); for (let t = 1; t <= 6; t += 0.5) e.update(Math.round(100 * t), t); return e; };
    const none = mk(0).estimate(6).remainSec, mid = mk(20).estimate(6).remainSec, full = mk(5).estimate(6).remainSec;
    assert(Math.abs(none - full) < 1e-6, '블렌드 시간이 지나면 측정값만');
    assert(mid > none * 1.1 && mid < none * 2, '섞이면 측정값보다 크고 저장값보다 작음 ' + [none, mid]);
  },
  eta_known_speed_and_weights() {
    // 단계 판 수 [1000, 600, 100], 가중치 [1, 2, 2], 첫 결과 t=1, 이후 초당 100판(= 0.01초/판)
    const mk = o => C.etaNew(Object.assign({stages: [{games: 1000}, {games: 600}, {games: 100}], weights: [1, 2, 2], warmup: 3, window: 20}, o || {}));
    const e = mk();
    e.begin(0, 1000, 0);
    assert.equal(e.estimate(0).ready, false, '아직 결과 없음');
    for (let t = 1; t <= 5; t += 0.5) e.update(Math.round(100 * t), t);
    // t=5: 500판 끝. 남은 = 500×0.01 + 600×(0.01×2) + 100×(0.01×2) = 5 + 12 + 2
    const r = e.estimate(5);
    assert(r.ready);
    assert(Math.abs(r.remainSec - 19) < 1e-6, String(r.remainSec));
    assert(Math.abs(r.finishAt - 24) < 1e-6);
    // 가중치가 다르면 값이 달라진다(가중치가 실제로 쓰임)
    const e2 = mk({weights: [1, 1, 1]}); e2.begin(0, 1000, 0);
    for (let t = 1; t <= 5; t += 0.5) e2.update(Math.round(100 * t), t);
    assert(Math.abs(e2.estimate(5).remainSec - (5 + 6 + 1)) < 1e-6);
  },
  eta_warmup_and_prior() {
    const stages = [{games: 1000}, {games: 600}, {games: 100}];
    const e = C.etaNew({stages, weights: [1, 2, 2], warmup: 3, window: 20});
    e.begin(0, 1000, 0);
    // 처음 결과가 t=1 에 폭주로 몰려 와도(500판) 첫 결과 후 3초가 지나기 전에는 표시하지 않는다
    e.update(500, 1); e.update(520, 2); e.update(540, 3.5);
    assert.equal(e.estimate(3.5).ready, false, '초반 보정: 측정값 미사용');
    e.update(560, 4.0); e.update(580, 4.5);
    assert.equal(e.estimate(4.5).ready, true, '첫 결과 3초 뒤부터 표시');
    // 저장된 속도(prior)가 있으면 측정 전에도 그 값으로 표시, 측정이 시작되면 측정값으로 바뀐다
    const p = C.etaNew({stages, weights: [1, 2, 2], warmup: 3, window: 20, prior: [0.01, 0.02, 0.02]});
    p.begin(0, 1000, 0);
    assert(Math.abs(p.estimate(0).remainSec - (10 + 12 + 2)) < 1e-9, '시작 직후 prior 로 24초');
    for (let t = 1; t <= 8; t += 0.5) p.update(Math.round(50 * t), t);        // 실제는 0.02초/판(prior 보다 2배 느림)
    const r = p.estimate(8);
    // 측정 0.02초/판: 남은 (1000-400)×0.02 + 600×0.04 + 100×0.04 = 12 + 24 + 4 = 40
    assert(Math.abs(r.remainSec - 40) < 0.2, String(r.remainSec));
  },
  eta_speed_change_moving_window() {
    const e = C.etaNew({stages: [{games: 100000}, {games: 100}, {games: 100}], weights: [1, 1, 1], warmup: 3, window: 20});
    e.begin(0, 100000, 0);
    let g = 0;
    for (let t = 1; t <= 10; t += 0.5) { g = Math.round(100 * t); e.update(g, t); }       // 초당 100판
    const c1 = e.estimate(10).cost[0];
    assert(Math.abs(c1 - 0.01) < 1e-6);
    for (let t = 10.5; t <= 40; t += 0.5) { g += 25; e.update(g, t); }                    // 이후 초당 50판
    // t=40, 창 20초: 20~40 구간은 전부 초당 50판 -> 0.02초/판
    assert(Math.abs(e.estimate(40).cost[0] - 0.02) < 1e-6, String(e.estimate(40).cost[0]));
    // 창 안에서 속도가 바뀐 중간(t=15): 0.01 과 0.02 사이
    const m = C.etaNew({stages: [{games: 100000}, {games: 100}, {games: 100}], weights: [1, 1, 1], warmup: 3, window: 20}); m.begin(0, 100000, 0);
    g = 0;
    for (let t = 1; t <= 10; t += 0.5) { g = Math.round(100 * t); m.update(g, t); }
    for (let t = 10.5; t <= 15; t += 0.5) { g += 25; m.update(g, t); }
    const c = m.estimate(15).cost[0];
    assert(c > 0.0105 && c < 0.0195, String(c));
  },
  eta_stage_transition_recalibrates() {
    const e = C.etaNew({stages: [{games: 1000}, {games: 600}, {games: 100}], weights: [1, 2, 2], warmup: 3, window: 20});
    e.begin(0, 1000, 0);
    for (let t = 1; t <= 10; t += 0.5) e.update(Math.round(100 * t), t);     // 0.01초/판, t=10 에 1000판 끝
    // 2단계 시작 직후(결과 없음): 1단계 실측 × (2/1) = 0.02 → 600×0.02 + 100×0.02 = 14
    e.begin(1, 600, 12);
    assert(Math.abs(e.estimate(12).remainSec - 14) < 1e-6, String(e.estimate(12).remainSec));
    // 실제 2단계는 0.03초/판(가중치 예상 0.02 보다 느림): 첫 결과 t=14(지연 2초) 뒤 측정
    for (let t = 14; t <= 20; t += 0.5) e.update(Math.round(100 / 3 * (t - 13)), t);
    const r = e.estimate(20), done = Math.round(100 / 3 * 7);
    // 단계 2 남은 (600-done)×0.03 + 3단계 100 × (0.03×2/2) + 3단계 시작 지연(2단계에서 잰 지연 2초)
    const want = (600 - done) * 0.03 + 100 * 0.03 + 2;
    assert(Math.abs(r.remainSec - want) < 0.15, r.remainSec + ' vs ' + want);
    // 3단계 판 수가 계획 상한(예: 100)보다 적게 판명되면 begin 에서 바로잡는다
    e.begin(2, 40, 40);
    assert(Math.abs(e.estimate(40).remainSec - 40 * 0.03) < 0.05, String(e.estimate(40).remainSec));
    // 저장용 요약: 실측 단계는 평균, 없는 단계는 가중치 비
    const sm = e.summary();
    assert(Math.abs(sm[0] - 0.01) < 1e-6 && Math.abs(sm[1] - 0.03) < 0.002 && Math.abs(sm[2] - 0.03) < 0.002, JSON.stringify(sm));
    assert.equal(C.etaNew({stages: [{games: 1}, {games: 1}, {games: 1}]}).summary(), null);
  },
  eta_formatting_and_prior() {
    assert.equal(C.fmtDur(7), '약 7초');
    assert.equal(C.fmtDur(59.6), '약 1분');
    assert.equal(C.fmtDur(60), '약 1분');
    assert.equal(C.fmtDur(125), '약 2분 5초');
    assert.equal(C.fmtDur(3600 * 2 + 60 * 29), '약 2시간 29분');
    assert.equal(C.fmtDur(3600), '약 1시간');
    const now = new Date(2026, 10, 6, 14, 5, 0).getTime();
    const line = C.etaLine({ready: true, remainSec: 125}, now);
    assert(line.includes('남은 시간 약 2분 5초') && line.includes('전체 완료 예상 14:07'), line);
    assert(C.etaLine({ready: false}, now).includes('계산 중'));
    assert.deepEqual(C.priorFrom({sec: [0.1, 0.2, 0.2], workers: 4}, 8), [0.05, 0.1, 0.1], '작업자 수 비례 환산');
    assert.equal(C.priorFrom({sec: [0.1, 0, 0.2], workers: 4}, 8), null);
    assert.equal(C.priorFrom({sec: [0.1, 0.2], workers: 4}, 8), null);
    assert.equal(C.priorFrom(null, 8), null);
    const pl = {combos: 1820, total: 20000, stages: [{games: 10000}, {games: 9000}, {games: 1000}]};
    assert(/시작하면 몇 초 뒤 예상 시간이 표시됩니다/.test(C.preText(pl, null)));
    const t = C.preText(pl, [0.01, 0.02, 0.02]);    // 100 + 180 + 20 = 300초
    assert(t.includes('예상 약 5분') && t.includes('20,000판'), t);
  },
  html() {
    const cx = {hasInfo: true, label: k => '이름-' + k, esc, bossName: k => '보스-' + k, levelMax: 18, level: 6, mode: 'mean'};
    assert(C.html({phase: 'idle'}, cx).includes('data-cs="start"') && C.html({phase: 'idle'}, cx).includes('value="18"') && !C.html({phase: 'idle'}, cx).includes('value="19"'));
    assert(/<option value="6" selected>/.test(C.html({phase: 'idle'}, cx)));
    assert(!C.html({phase: 'idle'}, {...cx, hasInfo: false}).includes('data-cs="start"'));
    const run = C.html({phase: 'run', msg: '1단계', done: 3, total: 10, etaText: '남은 시간 약 5초'}, cx);
    assert(run.includes('3/10') && C.html({phase: 'run'}, cx).includes('data-cs="cancel"'));
    assert(run.includes('data-k="cs-prog"') && run.includes('data-k="cs-eta"') && run.includes('남은 시간 약 5초'), '진행 글자·남은 시간 칸 분리(취소 버튼 재생성 없이 갱신)');
    assert(C.html({phase: 'idle'}, {...cx, preEta: '시작하면 몇 초 뒤 예상 시간이 표시됩니다'}).includes('cs-eta-pre'));
    assert(!C.html({phase: 'idle'}, cx).includes('cs-eta-pre'));
    const done0 = {phase: 'done', rows: [], level: 6, mode: 'mean', sig: 'a|', pool: 14, combos: 1000, keep: 300, triples: 10, runs: 40};
    assert(!C.html(done0, {...cx, sig: 'a|'}).includes('cs-old') && C.html(done0, {...cx, sig: 'b|'}).includes('cs-old'), '내 정보·제외 서명이 달라지면 낡은 결과');
    assert(C.html(done0, {...cx, sig: 'b|'}).includes('낡은 결과'));
    assert(C.html({phase: 'err', msg: '<x>'}, cx).includes('&lt;x&gt;'));
    const t = (boss, ks, mean, top) => ({boss, keys: ks, order: ks, st: {mean, top, clear: 0.5, frac: 0.75, n: 40}});
    const rows = [{sum: 3000, teams: [t('belgras', ['a', 'b', 'c', 'd'], 1000, 1200), t('tyria', ['e', 'f', 'g', 'h'], 1000, 1100), t('carnelia', ['i', 'j', 'k', 'l'], 1000, 1300)]},
                  {sum: 2900, teams: [t('belgras', ['a', 'b', 'c', 'd'], 900, 1200), t('tyria', ['e', 'f', 'g', 'h'], 1000, 1100), t('carnelia', ['i', 'j', 'k', 'l'], 1000, 1300)]}];
    const st = {phase: 'done', rows, level: 6, mode: 'mean', pool: 16, combos: 1820, keep: 300, triples: 10, runs: 40};
    const h = C.html(st, cx);
    assert(h.includes('보스-belgras') && h.includes('이름-a') && h.includes('3,000') && h.includes('합계') && h.includes('50%') && h.includes('75%') && h.includes('추정') && h.includes('2위'));
    assert(!h.includes('cs-stale'));
    assert(C.html(st, {...cx, level: 7}).includes('cs-stale') && C.html(st, {...cx, mode: 'top'}).includes('cs-stale'), '난이도·기준이 바뀌면 낡은 결과 표시');
    const ht = C.html({...st, mode: 'top'}, {...cx, mode: 'top'});
    assert(ht.includes('상위 점수(순위 기준)') && ht.includes('1,300'), '기준에 따라 열이 바뀜');
    assert(C.html({...st, rows: []}, cx).includes('결과 없음'));
  },
};
(async () => {
  let fail = 0;
  for (const [n, f] of Object.entries(tests)) {
    try { await f(); console.log('ok', n); } catch (e) { fail++; console.log('FAIL', n, e.message); console.log(e.stack.split('\n').slice(0, 4).join('\n')); }
  }
  if (fail) { console.log('FAILED', fail); process.exit(1); }
  console.log('PASS cosmo_search_test', Object.keys(tests).length);
})();
