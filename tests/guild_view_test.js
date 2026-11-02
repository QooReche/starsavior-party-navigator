// 길드 방어전 패널 시험: 점수 범위, 시즌 종료 표시(갱신 대기), 단계별 안내, 화면 용어, 이스케이프.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const V = require('../guild_view.js');
const G = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'guild_defense.json'), 'utf8'));
// 화면에 싣는 자료와 같은 모양(내부 출처 제외)
const P = {...G, title: '길드방어전(시즌4 10/29~11/05)', tab: '시즌4 10/29~11/05',
  sources: Object.fromEntries(Object.entries(G.sources).filter(([k]) => k !== 'client'))};
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const T = s => Date.parse(s);
const tests = {
  score() {
    assert.deepEqual(V.score(P, V.extraPct(P, 12, [0, 0, 0, 0])), {A: 66000});
    assert.deepEqual(V.score(P, V.extraPct(P, 12, [3, 3, 3, 3])), {A: 84000});
    assert.deepEqual(V.score(P, 0), {A: 30000});
    assert.equal(V.rangeText({A: 66000, B: 36000}), '36,000 ~ 66,000');   // 범위 표시 함수 자체는 그대로(값이 둘일 때)
    assert.equal(V.rangeText({A: 5, B: 5}), '5');
    assert.deepEqual(V.normSel(P, null), {level: 12, tiers: [3, 3, 3, 3]});
    assert.deepEqual(V.normSel(P, {level: 99, tiers: [9, -1, 'x', 2]}), {level: 12, tiers: [3, 3, 3, 2]});
  },
  state() {
    const s = (t) => V.seasonState(P.season, T(t));
    assert.deepEqual(s('2026-10-30T12:00:00+09:00'), {state: 'active', needsUpdate: false});
    assert.deepEqual(s('2026-11-05T04:00:00+09:00'), {state: 'settling', needsUpdate: true});
    assert.deepEqual(s('2026-11-12T04:00:00+09:00'), {state: 'ended', needsUpdate: true});
  },
  stale() {
    const live = V.panelHtml(P, null, 7, T('2026-10-30T12:00:00+09:00'), esc);
    assert(live.includes('진행 중') && !live.includes('갱신 대기') && !live.includes('data-k="gd-stale"'));
    assert(live.includes('이 시즌 정보는 10/30 기준'), '기준일 표시');
    for (const now of ['2026-11-05T04:00:00+09:00', '2026-11-20T00:00:00+09:00']) {
      const old = V.panelHtml(P, null, 7, T(now), esc);
      assert(old.includes('갱신 대기') && old.includes('data-k="gd-stale"') && old.includes('지난 시즌 기준'), now);
    }
    assert(V.panelHtml(P, null, 7, T('2026-11-06T00:00:00+09:00'), esc).includes('결산 중'));
  },
  ex() {
    const h = V.panelHtml(P, null, 7, T('2026-10-30T12:00:00+09:00'), esc);
    assert(h.includes('최고 점수가 나오는 조합') && h.includes('별의 도전 12단계'));
    assert(h.includes('보스를 다 깎으면 점수 84,000'), '최고 조합 점수');
    assert(h.includes('클리어(보스 100% 처치) 84,000') && !h.includes('가설 B'));
    assert.equal(V.scoreAt(P, 60, 0.999), 47960, '영상으로 확인한 점수식: 29,975 x 1.6');
    assert.equal(V.scoreAt(P, 60, 1), 48000);
    assert(h.includes('gd-est') && h.includes('추정'));
    assert(h.includes('일일 초기화 전까지 다시 쓸 수 없음') && h.includes('화·목·토') && h.includes('50턴'));
    assert(h.includes('(최고 조합)'));
    const low = V.panelHtml(P, {level: 6, tiers: [0, 0, 0, 0]}, 7, T('2026-10-30T12:00:00+09:00'), esc);
    assert(low.includes('추가 점수 60%') && low.includes('<b>48,000</b>'), '도전 6단계: 클리어 점수 48,000');
    assert(low.includes('<option value="6" selected>') && !low.includes('(최고 조합)'));
    // 7~12단계 능력치는 게임 화면으로 확인(2026-11-01)돼 추정 배지가 없고, 옛 공지 값은 툴팁으로만
    assert(h.match(/title="공지 표\(옛 값\): 공격 \+70%, 생명력·방어 \+35%"/));
    const row1 = h.split('<tr').find(r => r.includes('<td>1</td>')), row7 = h.split('<tr').find(r => r.includes('<td>7</td>'));
    assert(!row1.includes('gd-est') && !row7.split('</td>')[1].includes('gd-est'));
    assert(h.includes('보스가 3턴 면역(해제 불가)') && h.includes('스킬을 쓸 때마다'));
  },
  lower_step() {
    const h = V.panelHtml(P, null, 6, T('2026-10-30T12:00:00+09:00'), esc);
    assert(h.includes('6단계에는 별의 도전이 없습니다') && h.includes('<b>15,000</b>') && !h.includes('data-g="level"'));
    assert(h.includes('data-k="gd-rules"'));
  },
  plain_terms() {
    const h = V.panelHtml(P, null, 7, T('2026-10-30T12:00:00+09:00'), esc);
    for (const bad of ['GUILD_DUNGEON', 'DifficultyGroup', 'BATTLE_', 'TARGET_PRIORITY', 'SHIELD_GEN', 'ScaleFactor', 'BossKillPoint', 'client', '2001', 'undefined', 'NaN']) assert(!h.includes(bad), bad);
    assert(!h.includes('href="">'), '빈 링크 없음');
  },
  escape() {
    const evil = JSON.parse(JSON.stringify(P));
    evil.title = '<img src=x onerror=1>';
    const h = V.panelHtml(evil, null, 7, T('2026-10-30T12:00:00+09:00'), esc);
    assert(!h.includes('<img src=x') && h.includes('&lt;img'));
  },
  sim() {
    // 화면 자료 = guild_defense.page_payload 의 sim(tools/build_guild_sim.py 결과를 줄인 것)
    const raw = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'guild_sim.json'), 'utf8'));
    const S = {runs: raw.runs, recPower: raw.recPower, growth: raw.growth, levels: raw.levels, passP: raw.pass_p, basis: raw.basis,
      summary: raw.summary, sets: raw.sets, summaryBySets: raw.summaryBySets, supports: raw.supports, teams: raw.teams};
    // summary 는 rates 에서 다시 계산한 것과 같아야 한다(최고 단계 = 클리어율 passP 이상인 가장 높은 단계)
    for (const g of S.growth) {
      let best = null;
      S.teams.forEach((t, i) => S.supports.forEach(sup => { const r = t.bySupport[sup][String(g)]; let top = -1; r.forEach((p, lv) => { if (p >= S.passP) top = lv; });
        if (top >= 0 && (!best || top > best.level || (top === best.level && r[top] > best.p))) best = {level: top, team: i, p: r[top], support: sup}; }));
      assert.deepEqual(V.simBest(S, g), best, 'summary ' + g);
      const ex = V.simExpect(P, S, g);
      assert(ex, 'expect ' + g);
      // 진행도(= 0.5 + 0.5 x 보스 깎은 비율)로 확인된 점수식에 넣은 최댓값과 같아야 함
      let bv = -1;
      S.teams.forEach(t => Object.entries(S.sets || {off: [0, 0, 0, 0]}).forEach(([set, tiers]) => S.supports.forEach(sup => S.levels.forEach((lv, i) => {
        const tab = set === 'off' ? t : t.bySets[set];
        const f = tab.fracBySupport[sup][String(g)][i];
        bv = Math.max(bv, V.scoreAt(P, V.extraPct(P, lv, tiers), f));
      }))));
      assert.equal(ex.m, bv, 'expected score ' + g);
      // 판별 평균(fracBySupport)이 있어야 하고, 평균의 절단 ≤ 절단의 평균(졸개전 패배 섞인 팀을 낮춰 보지 않음)
      S.teams.forEach(t => S.supports.forEach(sup => S.levels.forEach((lv, i) => {
        assert(t.fracBySupport, 'fracBySupport 없음 — tools/build_guild_sim.py 재실행');
        const fm = t.fracBySupport[sup][String(g)][i], pm = Math.max(0, Math.min(1, 2 * t.progBySupport[sup][String(g)][i] - 1));
        assert(fm >= pm - 1e-3, 'frac ' + fm + ' < ' + pm);
      })));
    }
    const h = V.panelHtml({...P, sim: S}, null, 7, T('2026-10-30T12:00:00+09:00'), esc);
    assert(h.includes('data-k="gd-sim"') && h.includes('시뮬 추정: 깰 수 있는 최고 단계') && h.includes('시뮬 결과는 아직 실제와 대조 중입니다'));
    assert(h.includes('기대 점수가 가장 큰 단계') && h.includes('알리시아 지원 «') && h.includes('지원별 클리어 가능 최고 단계'), '지원·기대 점수 표시');
    assert(h.includes('data-k="gd-dev"'), '개발 중 배너 유지');
    const none = {...S, summary: Object.fromEntries(S.growth.map(g => [String(g), null]))};
    assert(V.panelHtml({...P, sim: none}, null, 7, T('2026-10-30T12:00:00+09:00'), esc).includes('EX도 어려움'));
    const one = {...S, summary: {[String(S.growth[0])]: {level: 3, team: 0, p: 0.7}}};
    const h3 = V.simBox({...P, sim: one}, esc);
    assert(h3.includes('별의 도전 3단계</b>까지') && h3.includes(V.rangeText(V.score(P, V.extraPct(P, 3, [0, 0, 0, 0])))) && h3.includes('클리어 70%'));
    assert.equal(V.simBox(P, esc), '', '시뮬 자료가 없으면 표시 안 함');
  },
  sim_presets() {
    // 클리어율과 평균 진행도를 같게 둬도 판별 frac와 선택 효과 가산으로 승자가 바뀐다.
    const tab = f => ({bySupport: {none: {'2': [0.5]}}, progBySupport: {none: {'2': [0.6]}}, fracBySupport: {none: {'2': [f]}}});
    const t = {...tab(0.7), rates: {'2': [0.5]}, names: ['시험 팀'], src: 'reco', bySets: {max: tab(0.6)}};
    const S = {teams: [t], growth: ['2'], levels: [0], supports: ['none'], sets: {off: [0,0,0,0], max: [3,3,3,3]},
      summary: {'2': {level: 0, team: 0, p: 0.5}}, passP: 0.5, runs: 2, recPower: 1, basis: ''};
    assert.equal(V.simExpect(P, S, 2).set, 'max');
    assert.equal(V.simExpect(P, S, 2).m, V.scoreAt(P, 60, 0.6));
    assert(V.simBox({...P, sim:S}, esc).includes('>모두 최대</span>'));
    t.bySets.max = tab(0.1);
    assert.equal(V.simExpect(P, S, 2).set, 'off', 'max의 실제 frac로 평가해야 함');
    assert(V.simBox({...P, sim:S}, esc).includes('>선택 효과 끔</span>'));
    S.sets.no_void = [3,3,3,0]; t.bySets.no_void = tab(1);
    assert.equal(V.simExpect(P, S, 2).set, 'no_void', '추가 프리셋도 비교');
    assert.equal(V.simExpect(P, S, 2).m, V.scoreAt(P, V.extraPct(P, 0, S.sets.no_void), 1));
    delete t.bySets;
    assert.equal(V.simExpect(P, S, 2).set, 'off', '새 메타+옛 팀 자료는 max에 off 자료를 재사용하지 않음');
    delete S.sets;
    assert.equal(V.simExpect(P, S, 2).m, V.scoreAt(P, 0, 0.7));
    delete t.progBySupport;
    assert.equal(V.simExpect(P, S, 2).m, V.scoreAt(P, 0, 0.7), 'frac만 있어도 사용');
    delete t.fracBySupport;
    assert.equal(V.simExpect(P, S, 2).m, 15000, '옛 클리어율 전용 자료');
    delete t.bySupport;
    assert.equal(V.simExpect(P, S, 2).m, 15000, 'rates 전용 자료');
  },
  mutation() {
    const orig = V.score;
    for (const [key, bad] of [['score', () => ({A: 1, B: 1})], ['seasonState', () => ({state: 'active', needsUpdate: false})]]) {
      const o = V[key]; V[key] = bad;
      let failed = false;
      try { tests.score(); tests.state(); } catch (e) { failed = true; } finally { V[key] = o; }
      assert(failed, 'mutation survived: ' + key);
    }
    assert.equal(V.score, orig);
  },
};
for (const [name, fn] of Object.entries(tests)) { fn(); console.log('ok', name); }
console.log('PASS guild_view_test', Object.keys(tests).length);
