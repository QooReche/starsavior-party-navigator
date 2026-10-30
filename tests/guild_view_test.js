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
    assert.deepEqual(V.score(P, V.extraPct(P, 12, [0, 0, 0, 0])), {A: 66000, B: 36000});
    assert.deepEqual(V.score(P, V.extraPct(P, 12, [3, 3, 3, 3])), {A: 84000, B: 39000});
    assert.deepEqual(V.score(P, 0), {A: 30000, B: 30000});
    assert.equal(V.rangeText({A: 66000, B: 36000}), '36,000 ~ 66,000');
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
    assert(h.includes('39,000 ~ 84,000'), '최고 조합 범위');
    assert(h.includes('가설 A 84,000') && h.includes('가설 B 39,000'));
    assert(h.includes('gd-est') && h.includes('추정'));
    assert(h.includes('일일 초기화 전까지 다시 쓸 수 없음') && h.includes('화·목·토') && h.includes('50턴'));
    assert(h.includes('(최고 조합)'));
    const low = V.panelHtml(P, {level: 6, tiers: [0, 0, 0, 0]}, 7, T('2026-10-30T12:00:00+09:00'), esc);
    assert(low.includes('추가 점수 60%') && low.includes('<b>33,000 ~ 48,000</b>'), '도전 6단계: 가설 B 33,000 ~ 가설 A 48,000');
    assert(low.includes('<option value="6" selected>') && !low.includes('(최고 조합)'));
    // 7~12단계 능력치는 추정 배지 + 공지 값 툴팁, 1~6단계는 없음
    assert(h.match(/title="공지 표: 공격 \+70%, 생명력·방어 \+35%"/));
    const row1 = h.split('<tr').find(r => r.includes('<td>1</td>')), row7 = h.split('<tr').find(r => r.includes('<td>7</td>'));
    assert(!row1.includes('gd-est') && row7.includes('gd-est'));
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
