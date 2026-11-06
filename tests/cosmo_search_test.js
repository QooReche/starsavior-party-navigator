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
const mkS = over => JSON.parse(JSON.stringify(Object.assign({}, SE, {poolSize: 99, minRole: {}, rerank: {keep: 100000, runs: 10}, combine: {topTriples: 10, show: 5}}, over || {})));
const cxOf = (S, log, over) => Object.assign({S, bosses: BOSSES, level: 6, mode: 'mean', results, roster, makeWorker: factory(log), workers: 3, stage: 'x', base: ''}, over || {});

// 전수 비교용: 보스별 모든 조합의 점수 -> 겹치지 않는 모든 삼중 -> 합 큰 순 n 개(같으면 id 작은 순)
function brute(S, mode, n) {
  const rows = GS.pool(Object.assign({}, S, {excluded: []}), results, roster), list = GS.combos(S, rows);
  const f = (b, keys) => { const s = fakeScore(b, keys); return mode === 'top' ? fakeTop(s) : s; };
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
    for (const k of ['poolSize', 'minPowerRatio', 'minRole', 'minFront', 'minDealer', 'screen', 'rerank', 'combine', 'final', 'topQ', 'defaultMode', 'defaultLevel']) assert(k in SE, k);
    assert(SE.poolSize >= 12, '풀은 3팀 12명 이상');
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
      const naive = BOSSES.map(b => { let best = null; for (const keys of GS.combos(S, GS.pool(S, results, roster))) { const s = fakeScore(b, keys); if (!best || s > best.s) best = {s, keys}; } return best.keys; });
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
      // 판 수·옵션: 1단계 2판(전 조합), 2단계 10판, 3단계 40판. 모든 작업이 Step 3·고른 레벨·보스 키로 나감
      const runs = [...new Set(log.map(m => m.n_runs))];
      assert.deepEqual(runs, [SE.screen.runs, SE.rerank.runs, SE.final.runs]);
      const sent = log.flatMap(m => m.teams);
      assert(sent.every(t => t.options.cosmo_raid.step === 3 && t.options.cosmo_raid.level === 6 && BOSSES.includes(t.options.cosmo_raid.boss) && t.options.cosmo_top_q === SE.topQ));
      assert(sent.every(t => t.party.units.length === 4 && t.party.units.every(u => u.stats_final === true && u.stats_override === results[u.key].stats)), '내 최종 능력치가 그대로 작업자에게 감');
      const nCombos = GS.combos(S, GS.pool(S, results, roster)).length;
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
    const rows = GS.pool(mkS(), results, roster), list = GS.combos(mkS(), rows);
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
  html() {
    const cx = {hasInfo: true, label: k => '이름-' + k, esc, bossName: k => '보스-' + k, levelMax: 18, level: 6, mode: 'mean'};
    assert(C.html({phase: 'idle'}, cx).includes('data-cs="start"') && C.html({phase: 'idle'}, cx).includes('value="18"') && !C.html({phase: 'idle'}, cx).includes('value="19"'));
    assert(/<option value="6" selected>/.test(C.html({phase: 'idle'}, cx)));
    assert(!C.html({phase: 'idle'}, {...cx, hasInfo: false}).includes('data-cs="start"'));
    assert(C.html({phase: 'run', msg: '1단계', done: 3, total: 10}, cx).includes('3/10') && C.html({phase: 'run'}, cx).includes('data-cs="cancel"'));
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
