// 길방 «내 정보로 최고 점수 편성 찾기» 로직 시험: 후보 풀·조합 규칙·작업 배분·순위·가짜 작업자 실행·화면 조각.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const S = require('../guild_search.js'), V = require('../guild_view.js');
const G = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'guild_defense.json'), 'utf8'));
const SE = G.search;
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

// 가짜 로스터: 딜러 12명(전투력 100..), 서포터 3, 디펜더 3
const roster = [];
const results = {};
let pw = 1000;
function add(key, cls) { roster.push({key, cls}); results[key] = {power: pw, stats: {atk: pw}, combat: {x: 1}}; pw -= 10; }
for (let i = 0; i < 12; i++) add('d' + i, i % 2 ? '스트라이커' : '캐스터');
for (let i = 0; i < 3; i++) add('s' + i, '서포터');
for (let i = 0; i < 3; i++) add('f' + i, '디펜더');
const cls = Object.fromEntries(roster.map(r => [r.key, r.cls]));

const tests = {
  config() {
    // 시즌 설정이 코드가 쓰는 모양인지(시즌 갱신 때 빠뜨리면 여기서 걸림)
    for (const k of ['poolSize', 'minPowerRatio', 'minRole', 'screen2', 'minFront', 'minDealer', 'screen', 'finalists', 'final', 'supportRole']) assert(k in SE, k);
    for (const k of ['level', 'runs', 'supporter', 'other']) assert(k in SE.screen, k);
    for (const k of ['keep', 'runs']) assert(k in SE.screen2, k);
    for (const k of ['runs', 'levels', 'supports']) assert(k in SE.final, k);
    assert(SE.final.levels.every(l => l >= 0 && l <= G.challenge.levels.length));
    for (const s of [SE.screen.supporter, SE.screen.other, ...SE.final.supports]) assert(S.SUP_NAME[s], s);
  },
  pool() {
    const rows = S.pool({poolSize: 6, minRole: {'서포터': 2, '디펜더': 1}}, results, roster);
    const keys = rows.map(r => r.key);
    assert.deepEqual(keys.slice(0, 6), ['d0', 'd1', 'd2', 'd3', 'd4', 'd5']);   // 전투력 순 상위 6
    assert(keys.includes('s0') && keys.includes('s1') && keys.includes('f0'), '역할 최소 인원 보충');
    assert.equal(keys.length, 9);
    // 전투력 하한: 최고의 0.985배 이상만(= d0,d1) + 역할 보충
    const r3 = S.pool({poolSize: 99, minPowerRatio: 0.985, minRole: {'서포터': 1}}, results, roster).map(r => r.key);
    assert(r3.includes('d0') && r3.includes('d1') && !r3.includes('d5') && r3.includes('s0'), r3.join());
    // 협공 구원자 제외(S.excluded), 끄면(banCoop=false) 포함
    const ex = S.pool({poolSize: 99, excluded: ['d0', 's1']}, results, roster).map(r => r.key);
    assert(!ex.includes('d0') && !ex.includes('s1') && ex.includes('d1'));
    assert(S.pool({poolSize: 99, excluded: ['d0'], banCoop: false}, results, roster).map(r => r.key).includes('d0'));
    // 능력치 없는 구원자(미보유)는 뺀다
    const r2 = S.pool({poolSize: 99}, {d0: results.d0}, roster);
    assert.deepEqual(r2.map(r => r.key), ['d0']);
  },
  combos() {
    const rows = S.pool({poolSize: 99}, results, roster);
    const all = S.combos({minFront: 0, minDealer: 0}, rows);
    assert.equal(all.length, 3060);   // C(18,4)
    const ok = S.combos({minFront: 1, minDealer: 1}, rows);
    assert(ok.every(t => t.some(k => S.FRONT.includes(cls[k])) && t.some(k => !S.FRONT.includes(cls[k]))));
    assert(ok.length < all.length && !ok.some(t => t.every(k => k[0] === 'd')));
  },
  party() {
    const p = S.party(['d3', 's1', 'd0', 'f2'], results, cls);
    // 앞열 역할 먼저(전투력 큰 순), 다음 딜러(전투력 큰 순) — s1(990-... 낮음) vs f2: 전투력은 key 생성 순서상 s1 > f2
    assert.deepEqual(p.order, ['s1', 'f2', 'd0', 'd3']);
    assert.equal(p.spec.leader, 0);
    assert.deepEqual(Object.keys(p.spec.units[0]).sort(), ['build', 'key', 'myinfo_combat', 'power', 'stats_final', 'stats_override']);
    assert(p.spec.units.every(u => u.build === 'none' && u.stats_final === true));
  },
  supports() {
    assert.equal(S.screenSupport(SE, ['s0', 'd0', 'd1', 'd2'], cls), SE.screen.supporter);
    assert.equal(S.screenSupport(SE, ['f0', 'd0', 'd1', 'd2'], cls), SE.screen.other);
    const noSup = S.finalSupports(SE, ['f0', 'd1', 'd3', 'd5'], cls);   // 서포터·캐스터 없음 → gust·focus 제외
    assert(!noSup.includes('gust') && !noSup.includes('focus') && noSup.includes('fire') && noSup.includes('strike'));
    const withSup = S.finalSupports(SE, ['s0', 'd0', 'd1', 'd2'], cls);
    assert(withSup.includes('gust') && withSup.includes('focus'));
  },
  split() {
    const parts = S.split([1, 2, 3, 4, 5], 2);
    assert.deepEqual(parts, [[1, 3, 5], [2, 4]]);
    assert.equal(S.split([1], 4).length, 1);
    assert.equal(S.split([], 4).length, 1);
  },
  rank() {
    const tiers = [3, 3, 3, 3];
    const list = [['d0', 'd1', 's0', 'f0'], ['d2', 'd3', 's1', 'f1']];
    const jobsA = S.screenJobs(SE, G, V, list, results, cls, tiers);
    assert.equal(jobsA.length, 2);
    assert.deepEqual(jobsA[0].options.guild, {level: SE.screen.level, sets: tiers, support: SE.screen.supporter});
    const resA = {[jobsA[0].key]: {prog: 0.6, clear: 0}, [jobsA[1].key]: {prog: 0.9, clear: 0.1}};
    const fin = S.pickFinalists({...SE, finalists: 1}, V, G, jobsA, resA, tiers);
    assert.deepEqual(S.pickTop(V, G, jobsA, resA, tiers, 2), [list[1], list[0]]);
    assert.deepEqual(fin, [list[1]]);   // 진행도 큰 팀
    const jobsB = S.finalJobs(SE, G, V, list, results, cls, tiers);
    assert.equal(new Set(jobsB.map(j => j.key)).size, jobsB.length, '작업 키 유일');
    const resB = {};
    jobsB.forEach(j => { resB[j.key] = {prog: j.level === 4 && j.sup === 'fire' ? 0.99 : 0.5, clear: 0, n: SE.final.runs}; });
    const top = S.rank(V, G, jobsB, resB, tiers, 5);
    assert.equal(top.length, 2);
    assert(top.every(t => t.level === 4 && t.sup === 'fire'));
    assert(top[0].score >= top[1].score);
    // 시뮬에서 협공이 나간 팀은 예선 선발·최종 순위에서 빠진다(banCoop 끄면 포함)
    const resC = {[jobsA[0].key]: {prog: 0.6, clear: 0}, [jobsA[1].key]: {prog: 0.9, clear: 0.1, via: {forced_coop: 2}}};
    assert.deepEqual(S.pickTop(V, G, jobsA, resC, tiers, 2, SE), [list[0]]);
    assert.deepEqual(S.pickTop(V, G, jobsA, resC, tiers, 2, {...SE, banCoop: false}), [list[1], list[0]]);
    const resD = {}; jobsB.forEach(j => { resD[j.key] = {prog: 0.9, clear: 0, n: 1, via: j.keys === list[1] ? {coop: 1} : {reaction: 3}}; });
    assert.deepEqual(S.rank(V, G, jobsB, resD, tiers, 5, SE).map(t => t.keys), [list[0]]);
    // 걸러낸 팀 수: 단계마다 같은 팀이 또 걸려도 한 번만 센다
    assert.equal(S.countDropped(SE, [[jobsA, resC], [jobsA, resC]]), 1);
    assert.equal(S.countDropped({...SE, banCoop: false}, [[jobsA, resC]]), 0);
    // 기대 점수(평균) = 확인된 식: 진행도 0.5 → 보스 0% 깎음, 1 → 100%
    assert.equal(S.expected(V, G, 4, tiers, 0.5), V.scoreAt(G, V.extraPct(G, 4, tiers), 0));
    assert.equal(S.expected(V, G, 4, tiers, 1), V.scoreAt(G, V.extraPct(G, 4, tiers), 1));
    assert(S.expected(V, G, 4, tiers, 0.9) > S.expected(V, G, 4, tiers, 0.6));
    // 판별 진행도: 졸개전 패배(0.25) + 클리어(1) 반반 → 평균 진행도(0.625)로 낸 값보다 큼(판마다 점수식 후 평균)
    const pc = V.extraPct(G, 4, tiers), mix = S.expected(V, G, 4, tiers, 0.625, [0.25, 1]);
    assert.equal(mix, Math.round((V.scoreAt(G, pc, 0, 1) + V.scoreAt(G, pc, 1)) / 2), '졸개전 패배 판(0.25)은 졸개 1기만 처치');
    assert(mix > S.expected(V, G, 4, tiers, 0.625));
  },
  rank_top_and_cap() {
    // 순위 기준 = 상위 20% 판 평균(상위 점수) -> 상한 도달률 -> 평균. 평균을 점수식에 넣지 않고 판마다 계산.
    const tiers = [0, 0, 0, 0], pc = V.extraPct(G, 4, tiers), cap = V.scoreAt(G, pc, 1), lo = V.scoreAt(G, pc, 0);
    // 10판: A = 2판 클리어 + 8판 졸개전 패배(prog 0), B = 1판 클리어 + 9판 보스 0.5 깎음
    const A = [1, 1, ...Array(8).fill(0)], B = [1, ...Array(9).fill(0.75)];
    const sa = S.rankStats(V, G, 4, tiers, 0.5, A), sb = S.rankStats(V, G, 4, tiers, 0.5, B);
    assert.equal(sa.top, cap, '상위 20% = 2판 모두 상한'); assert.equal(sb.top, Math.round((cap + V.scoreAt(G, pc, 0.5)) / 2));
    assert.equal(sa.cap, 0.2); assert.equal(sb.cap, 0.1);
    assert(sa.mean < sb.mean, '평균은 B가 높지만 순위는 A가 위(상위 점수)');
    const list = [['d0', 'd1', 's0', 'f0'], ['d2', 'd3', 's1', 'f1']];
    const jobs = S.finalJobs({...SE, final: {...SE.final, levels: [4], supports: ['fire']}}, G, V, list, results, cls, tiers);
    const res = {[jobs[0].key]: {prog: 0.5, clear: 0.1, progs: B, n: 10}, [jobs[1].key]: {prog: 0.5, clear: 0.2, progs: A, n: 10}};
    const top = S.rank(V, G, jobs, res, tiers, 5);
    assert.deepEqual(top.map(t => t.keys), [list[1], list[0]]);
    assert.equal(top[0].score, cap); assert.equal(top[0].cap, 0.2); assert.equal(top[0].mean, sa.mean);
    assert.deepEqual(S.pickTop(V, G, jobs, res, tiers, 1), [list[1]]);
    // 상한 동점이면 상한 도달률, 그다음 평균
    const C = Array(10).fill(1), D2 = [...Array(3).fill(1), ...Array(7).fill(0.5)];
    const sc = S.rankStats(V, G, 4, tiers, 1, C), sd = S.rankStats(V, G, 4, tiers, 1, D2);
    assert.equal(sc.top, sd.top); assert(sc.cap > sd.cap);
    // progs 없으면 prog·clear 로 대체
    const one = S.rankStats(V, G, 4, tiers, 0.25, null, 0.1);
    assert.equal(one.top, V.scoreAt(G, pc, 0, 1)); assert.equal(one.cap, 0.1); assert(lo > 0);
  },
  async runPhase() {
    // 가짜 작업자: 받은 팀마다 결과를 돌려주고 done
    let made = 0, terminated = 0;
    const mk = () => {
      made++;
      const w = {terminate() { terminated++; }, onmessage: null, postMessage(m) {
        setTimeout(() => {
          for (const t of m.teams) w.onmessage({data: {type: 'team', id: m.id, key: t.key, result: {prog: 0.7, clear: 0.2, n: m.n_runs, progs: [0.5, 0.9], via: t.key === 'k3' ? {coop: 1.5} : {}}}});
          w.onmessage({data: {type: 'done', id: m.id}});
        }, 1);
      }};
      return w;
    };
    const jobs = Array.from({length: 7}, (_, i) => ({key: 'k' + i, party: {}, options: {}}));
    const seen = [];
    const h = S.runPhase({makeWorker: mk, jobs, workers: 3, runs: 5, seed: 1, stage: 'x', base: '', onProgress: (d, t) => seen.push([d, t])});
    const res = await h.promise;
    assert.equal(Object.keys(res).length, 7);
    assert.equal(made, 3); assert.equal(terminated, 3);
    assert.deepEqual(seen[seen.length - 1], [7, 7]);
    // 작업자 결과의 via·progs 가 끊기지 않고 실려 협공 배제까지 이어짐(끊기면 이 줄이 실패)
    assert.deepEqual(res.k3.via, {coop: 1.5}); assert.deepEqual(res.k0.progs, [0.5, 0.9]);
    assert(S.coopHit({banCoop: true}, res.k3) && !S.coopHit({banCoop: true}, res.k0), '협공 난 팀만 걸러짐');
    // 작업자 오류 → reject
    const bad = () => ({terminate() {}, onmessage: null, postMessage(m) { setTimeout(() => this.onmessage({data: {type: 'error', msg: '터짐'}}), 1); }});
    await assert.rejects(S.runPhase({makeWorker: bad, jobs, workers: 2, runs: 5, seed: 1, stage: 'x', base: ''}).promise, /터짐/);
    // 취소
    const slow = () => ({terminate() {}, onmessage: null, postMessage() {}});
    const hc = S.runPhase({makeWorker: slow, jobs, workers: 2, runs: 5, seed: 1, stage: 'x', base: ''});
    hc.cancel();
    await assert.rejects(hc.promise, /취소/);
    assert.deepEqual(await S.runPhase({makeWorker: mk, jobs: [], workers: 2, runs: 5, seed: 1, stage: 'x', base: ''}).promise, {});
  },
  async runPhaseChunk() {
    // 작업 큐(chunk): 느린 작업자 1명 + 빠른 작업자 3명 -> 빠른 쪽이 더 많이 처리(정적 분할이면 모두 같은 수). 결과는 전부 나옴.
    const per = [];
    let n = 0;
    const mk = () => {
      const me = n++, cnt = (per[me] = {teams: 0, runs: 0});
      const w = {terminate() {}, onmessage: null, postMessage(m) {
        cnt.runs++;
        setTimeout(() => {
          for (const t of m.teams) { cnt.teams++; w.onmessage({data: {type: 'team', id: m.id, key: t.key, result: {prog: 0.5, clear: 0, n: m.n_runs}}}); }
          w.onmessage({data: {type: 'done', id: m.id}});
        }, me === 0 ? 20 : 1);
      }};
      return w;
    };
    const jobs = Array.from({length: 120}, (_, i) => ({key: 'k' + i, party: {}, options: {}}));
    const seen = [];
    const res = await S.runPhase({makeWorker: mk, jobs, workers: 4, runs: 2, seed: 1, stage: 'x', base: '', chunk: 3, onProgress: (d, t) => seen.push(d)}).promise;
    assert.equal(Object.keys(res).length, 120);
    assert.deepEqual(seen, Array.from({length: 120}, (_, i) => i + 1), '진행 수가 1씩 늘어 120');
    assert.equal(per.reduce((a, c) => a + c.teams, 0), 120);
    assert(per[0].teams < 30 && per[1].teams > 30, '느린 작업자가 덜 받음 ' + JSON.stringify(per));
    assert(per[1].runs > 1, '작업자가 run 메시지를 여러 번 받음');
    // 작업이 chunk 보다 적으면 작업자도 필요한 만큼만 띄움
    n = 0; per.length = 0;
    await S.runPhase({makeWorker: mk, jobs: jobs.slice(0, 5), workers: 4, runs: 2, seed: 1, stage: 'x', base: '', chunk: 3}).promise;
    assert.equal(per.length, 2);
  },
  html() {
    const cx = {hasInfo: true, sig: '3333', label: k => '이름-' + k, esc};
    assert(S.html({phase: 'idle'}, cx).includes('data-gs="start"'));
    assert(!S.html({phase: 'idle'}, {...cx, hasInfo: false}).includes('data-gs="start"'), '내 정보 없으면 버튼 없음');
    assert(S.html({phase: 'run', msg: '1단계', done: 3, total: 10}, cx).includes('3/10'));
    assert(S.html({phase: 'err', msg: '<x>'}, cx).includes('&lt;x&gt;'), '이스케이프');
    const rows = [{order: ['a', 'b', 'c', 'd'], level: 4, sup: 'fire', score: 59500, clear: 0.93, frac: 1}];
    const h = S.html({phase: 'done', rows, sig: '3333', pool: 14, combos: 900, finalists: 12, runs: 40}, cx);
    assert(h.includes('상위 점수') && h.includes('상한 도달률') && h.includes('평균 점수') && h.includes('상위 20%'), '순위 기준 설명');
    assert(h.includes('59,500') && h.includes('불의 고동') && h.includes('이름-a') && h.includes('93%') && !h.includes('gd-search-stale'));
    assert(S.html({phase: 'done', rows, sig: '2222', pool: 14, combos: 9, finalists: 1, runs: 1}, cx).includes('gd-search-stale'), '선택 효과가 바뀌면 낡은 결과 표시');
    assert(h.includes('추정') && h.includes('새 시즌'), '추정·시즌 경고');
    const hc = S.html({phase: 'idle'}, {...cx, excluded: ['d0']});
    assert(hc.includes('data-gs="coop"') && /data-gs="coop" checked/.test(hc) && hc.includes('이름-d0'), '협공 제외 체크(기본 켬)');
    assert(!/data-gs="coop" checked/.test(S.html({phase: 'idle', banCoop: false}, {...cx, excluded: ['d0']})), '끄면 체크 해제');
    // 제외·주의 구원자 목록: 이유·근거 수준 표시, 걸러낸 팀 수, 체크 해제 시 «제외 해제됨»
    const notes = [{key: 'd0', kind: 'exclude', basis: 'client', why: '이유-가'}, {key: 'd1', kind: 'caution', basis: 'community', why: '이유-나'}];
    const hn = S.html({phase: 'done', rows, sig: '3333', pool: 1, combos: 1, finalists: 1, runs: 1, dropped: 7}, {...cx, excluded: ['d0'], notes});
    assert(hn.includes('data-k="gd-notes"') && hn.includes('이유-가') && hn.includes('이유-나') && hn.includes('클라 자료 확인') && hn.includes('커뮤니티 근거') && hn.includes('[제외 ·') && hn.includes('[주의 ·'));
    assert(hn.includes('data-k="gd-search-dropped"') && hn.includes('7개'), '걸러낸 팀 수');
    assert(S.html({phase: 'idle', banCoop: false}, {...cx, excluded: ['d0'], notes}).includes('제외 해제됨'));
    assert(!S.html({phase: 'idle'}, {...cx, excluded: ['d0'], notes}).includes('gd-search-dropped'), '0이면 숨김');
    assert(!S.html({phase: 'idle'}, cx).includes('data-gs="coop"'), '제외 대상 없으면 체크 없음');
  },
};
(async () => {
  let fail = 0;
  for (const [n, f] of Object.entries(tests)) {
    try { await f(); console.log('ok', n); } catch (e) { fail++; console.log('FAIL', n, e.message); console.log(e.stack.split('\n').slice(0, 4).join('\n')); }
  }
  if (fail) { console.log('FAILED', fail); process.exit(1); }
  console.log('PASS guild_search_test', Object.keys(tests).length);
})();
