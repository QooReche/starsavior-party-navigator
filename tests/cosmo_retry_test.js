// 합성 점수가 특정 구원자에 집중된 실제 search/작업자 경로. 계정 자료는 사용하지 않는다.
const assert = require('node:assert/strict');
const C = require('../cosmo_search.js'), GS = require('../guild_search.js');
const G = require('../data/cosmo_raid.json');
const roster = Array.from({length: 13}, (_, i) => ({key: 'u' + i, name: i ? '대안' + i : '집중구원자', cls: i % 2 ? '서포터' : '캐스터'}));
const results = Object.fromEntries(roster.map((r, i) => [r.key, {power: 1000 - i, stats: {atk: 1000 - i}}]));
const teams = [[0,1,2,3], [0,4,5,6], [0,7,8,9], [0,10,11,12], [4,5,6,7], [8,9,10,11]].map(t => t.map(i => 'u' + i));
const score = keys => 100 + (keys.includes('u0') ? 10000 : 0) + teams.length - teams.findIndex(t => C.idOf(t) === C.idOf(keys));
function settings() {
  const S = structuredClone(G.search);
  S.learned.value = false; // 기존 전수·빠른 탐색의 겹침 재시도 회귀
  S.minFront = S.minDealer = 0; S.maxPool = null;
  S.screen = {runs: 2, firstRuns: 1, passFrac: .001, passMinMult: 1};
  S.rerank = {keep: 1, runs: 3}; S.final.runs = 4; S.combine = {topTriples: 2, show: 2};
  S.retry = {keepMultipliers: [1, 3, null], maxCandidatesPerBoss: 100, maxRerankGames: 900, maxTripleChecks: 10000};
  S.speed.workerReuse.value = true; S.speed.surrogate.value = false;
  return S;
}
async function run(S = settings(), onlyHot = false, missing = false, cancel = false) {
  const original = GS.combos, sent = [], phases = [], progress = [], listsSeen = [];
  GS.combos = () => onlyHot ? teams.slice(0, 4) : teams;
  let eta, time = 0, idx, closed = 0, created = 0, stop = false;
  try {
    const out = await C.search({S, bosses: G.season.bossOrder, level: 3, mode: 'mean', results, roster, workers: 2, stage: 'cosmo', base: '',
      onPlan: p => eta = C.etaNew({stages: p.stages, prior: [1,1,1,1], warmup: 0}),
      onPhase: (msg, total, info) => { idx = info.stage; eta.begin(idx, info.games, ++time); phases.push({msg, total, info, estimate: eta.estimate(time)}); },
      onProgress: (d, t) => { eta.update(d * (idx === 2 ? S.rerank.runs : idx === 3 ? S.final.runs : 1), ++time); progress.push([idx,d,t]); },
      stale: () => stop,
      onLists: lists => listsSeen.push(lists),
      makeWorker: () => {
        created++;
        return {terminate() { closed++; }, postMessage(m) {
          sent.push(m);
          setImmediate(() => {
            if (cancel && phases.some(p => p.msg.startsWith('후보 확대'))) stop = true;
            for (const t of m.teams) {
              const keys = t.party.units.map(u => u.key), v = score(keys);
              if (missing && m.seed === 3) continue;
              this.onmessage({data: {id: m.id, type: 'team', key: t.key, result: {prog: .5, progs: null, via: {}, n: m.n_runs, clear: .5,
                cosmo: {mean: v, top: v, frac: .5, clear: .5, n: m.n_runs}}}});
            }
            this.onmessage({data: {id: m.id, type: 'done'}});
          });
        }};
      }});
    return {out, sent, phases, progress, listsSeen};
  } catch (error) { return {error, sent, phases, progress}; }
  finally { GS.combos = original; assert.equal(closed, created, '성공·실패·취소 모두 작업자 반환'); }
}
const jobs = (r, seed) => r.sent.filter(m => m.seed === seed).flatMap(m => m.teams);
async function main() {
  assert.deepEqual(G.search.retry.keepMultipliers, [1,3,null], '시즌 자료의 재시도 설정');
  const r = await run();
  assert(!r.error, r.error?.stack);
  assert.equal(r.out.attempts.length, 3, '초기·3배 실패 뒤 전체 후보 복귀');
  assert.deepEqual(r.out.attempts.map(a => a.triples > 0), [false,false,true]);
  assert(r.out.rows[0].sum > 0 && r.out.rows[0].teams.every(t => t.st.frac > 0));
  assert.equal(new Set(r.out.rows[0].teams.flatMap(t => t.keys)).size, 12);
  const calls = jobs(r, 3).map(t => t.key);
  assert.equal(calls.length, 18);
  assert.equal(new Set(calls).size, calls.length, '확대 시 기존 정밀 job 재요청 없음');
  assert.equal(jobs(r, 1).length, 18, '첫 판을 재요청하지 않음');
  assert(jobs(r, 4).length < 18, '반감으로 떨어진 후보까지 실제 복귀');
  const pp = r.phases.filter(p => p.info.stage === 2);
  assert.deepEqual(pp.map(p => p.info.games), [9,27,54], 'ETA는 추가 계산을 누계에 반영');
  assert(pp.slice(1).every(p => p.msg.includes('후보 확대') && p.msg.includes('재사용') && p.estimate.ready && p.estimate.remainSec > 0));
  assert(r.progress.some(p => p[0] === 2 && p[1] === 3 && p[2] === 9), '재시도 진행 표시가 기존 완료 건수를 유지');
  assert.equal(r.out.growthOwned.length, 18, '육성 비교에도 확대 결과 재사용');
  console.log('PASS retry success, halving recovery, reuse, ETA, growth');

  const fast = settings();
  Object.assign(fast.speed.surrogate, {value:true, ratio:.5, minPerUnit:0, minAudit:0, auditFrac:0, missThreshold:1});
  const recovered = await run(fast);
  assert(!recovered.error, recovered.error?.stack);
  assert(jobs(recovered, 1).length < 18 && jobs(recovered, 3).length === 18, '빠른 선별에서 미계산한 후보도 확대 시 복귀');
  assert.equal(new Set(recovered.out.rows[0].teams.flatMap(t => t.keys)).size, 12);
  console.log('PASS surrogate uncomputed candidate recovery');

  const none = await run(settings(), true);
  assert.equal(none.error?.gwenCause, 'empty');
  assert.equal(none.error.attempts.length, 3);
  assert.match(none.error.message, /집중구원자.*대신 쓸 구원자.*난이도를 낮춰/);
  assert.match(none.error.message, /후보 확대 후에도/);
  const html = C.html({phase: 'err', msg: none.error.message, errorCause: none.error.gwenCause},
    {hasInfo: true, levelMax: 18, level: 3, mode: 'mean', esc: s => String(s), error: c => `<i data-cause="${c}"></i>`});
  assert.match(html, /data-k="cs-err"/); assert.match(html, /data-cause="empty"/); assert.match(html, /집중구원자/);
  console.log('PASS exhausted candidates, named guidance, Gwen error');

  for (const [name, value] of [['maxCandidatesPerBoss',3], ['maxRerankGames',27], ['maxTripleChecks',1]]) {
    const S = settings(); S.retry[name] = value;
    const capped = await run(S);
    assert.match(capped.error?.message || '', /계산 상한/, name);
    const evaluated = jobs(capped, 3);
    if (name === 'maxCandidatesPerBoss') assert(evaluated.length <= 9, name);
    if (name === 'maxRerankGames') assert(evaluated.length * S.rerank.runs <= value, name);
    if (name === 'maxTripleChecks') assert.equal(capped.error.attempts.length, 3, '앞 두 단계는 호환 목록이 비어 검사 예산을 쓰지 않음');
    assert(capped.error.attempts.length <= 3);
  }
  const budget = {remaining: 2, exhausted: false};
  C.bestTriples(Array.from({length:3}, () => teams.map(keys => ({keys, score: 1}))), 2, budget);
  assert(budget.exhausted && budget.remaining === -1);
  const one = settings(); one.retry.maxCandidatesPerBoss = 1;
  assert.equal((await run(one)).error.attempts.length, 1, '같은 상한 단계는 한 번만 실행');
  const bad = settings(); bad.retry.keepMultipliers = [1,3,9,null];
  assert.equal((await run(bad)).sent.length, 0, '잘못된 설정은 계산 전에 차단');
  console.log('PASS candidate/game/triple/stage caps');

  // 실제 search 호출부도 정확히 0으로 완료되면 경고를 만들지 않아야 함.
  const counted = {remaining: 10000};
  for (const lists of r.listsSeen) C.bestTriples(lists, 2, counted);
  const exact = settings(); exact.retry.maxTripleChecks = 10000 - counted.remaining;
  const completed = await run(exact);
  assert(!completed.error && !completed.out.combineLimited, '정확히 마지막 확인에서 예산 0: 소진 오탐 금지');
  assert.deepEqual(completed.out.rows, r.out.rows);
  let certificateCap = null;
  for (let cap = 1; cap < exact.retry.maxTripleChecks; cap++) {
    const b = {remaining: cap}; let found;
    for (const lists of r.listsSeen) {
      found = C.bestTriples(lists, 2, b);
      if (found.length || b.exhausted) break;
    }
    if (b.exhausted && !C.triplesLimited(found, 2, b)) { certificateCap = cap; break; }
  }
  assert(certificateCap != null, '합성 목록에도 소진 후 상위 확정 경로가 있어야 함');
  const certified = settings(); certified.retry.maxTripleChecks = certificateCap;
  const proven = await run(certified);
  assert(!proven.error && !proven.out.combineLimited, '상한이 하한보다 작으면 실제 결과 경고 생략');
  assert.deepEqual(proven.out.rows, r.out.rows);

  const partial = settings(); partial.retry.maxTripleChecks = 3;
  const limited = await run(partial);
  assert(!limited.error && limited.out.rows.length > 0 && limited.out.combineLimited, '검사 상한까지 일부 삼중은 찾은 경우');
  const limitedHtml = C.html({...limited.out, phase:'done'}, {hasInfo:true, level:3, levelMax:18, mode:'mean', esc:String, label:k=>k, bossName:k=>k});
  assert.match(limitedHtml, /data-k="cs-limit"/); assert.match(limitedHtml, /더 높은 점수의 조합이 남아/);
  assert(!limitedHtml.includes('고른 최적'), '상한 내 결과를 후보 전체의 최적이라고 단정하지 않음');
  assert.match(limitedHtml, /이번 결과는/);
  assert.match(limitedHtml, /2단계 후보 점수 기준/);
  console.log('PASS partial success limit notice');

  const broken = await run(settings(), false, true);
  assert.equal(broken.error?.gwenCause, 'calculation');
  assert.match(broken.error.message, /결과가 누락/);
  const canceled = await run(settings(), false, false, true);
  assert.equal(canceled.out, null); assert.equal(jobs(canceled, 2).length, 0);
  console.log('PASS missing results, cancellation');
}
main().catch(e => { console.error(e); process.exitCode = 1; });
