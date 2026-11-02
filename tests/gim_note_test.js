// 실제 사전·규칙을 기믹 박스에 연결: 확인된 대처와 조건부 대처를 구분한다.
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const tpl = fs.readFileSync(require.resolve('../party_template.html'), 'utf8');
const plain = require('../data/gimmick_plain.json');
const rules = require('../data/gimmick_rules.json').types;
const stages = require('../data/stage_gimmicks.json');
const start = tpl.indexOf('const GFIX={'), end = tpl.indexOf('let LEADKEY=', start);
assert(start >= 0 && end > start, '기믹 표시 함수가 있어야 함');
const esc = s => String(s).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;');
const ctx = vm.createContext({D: {plain, grules: rules, gim: {}, bosses: []}, GIMACT: [],
  CFG: {restrict: {}, advantage: {}}, EL: {}, esc, face: () => '', elText: () => '', sbText: () => ''});
vm.runInContext(tpl.slice(start, end), ctx);
function row(code, tags) {
  const key = Object.keys(stages).find(k => stages[k][code]);
  assert(key, code + ' 실제 스테이지가 있어야 함');
  const [content, tab, name] = key.split('|');
  ctx.D.gim = {[key]: {[code]: stages[key][code]}};
  const party = tags.map((gt, i) => ({s: {key: 'member' + i, name: '구원자' + i, gt}}));
  const html = ctx.gimNote(party, {key: content, name: content}, {tab, name, n: 1, rp: 1, ec: {}}, 0);
  const offset = html.indexOf('<div class="gimrow"');
  assert(offset >= 0, '실제 기믹 행이 렌더되어야 함: ' + code);
  return html.slice(offset);
}
for (const code of ['STEALTH', 'SKILL_NULLIFY']) {
  const html = row(code, [['AOE'], ['DEALER']]);
  assert.match(html, /data-savior="member0"/, '전체 공격 담당 연결');
  assert.doesNotMatch(html, /data-savior="member1"/, '일반 딜러를 전체 공격 담당으로 넣지 않음');
  assert.doesNotMatch(html, /class="gimq"|class="guess"|미확인/, code + ' 확인된 대처');
  assert.match(row(code, [['DEALER']]), /class="nobody"/, '담당이 없을 때의 경고 유지');
}
const guard = row('INVULN_GUARD', [['DISPEL']]);
assert.match(guard, /해제 가능한 강화만 지우기/);
assert.match(guard, /해제 불가 상태는 강화 해제로 지울 수 없습니다/);
assert.match(guard, /class="guess"/);
assert.match(row('SELF_BUFF_DEPENDENT', [['DISPEL']]), /적 버프 지우기/);
const cooldown = row('COOLDOWN_DISRUPT', [['CD_REDUCE'], ['CLEANSE']]);
assert.match(cooldown, /면역·쿨타임 줄이기/);
assert.match(cooldown, /강제 적용 제외/);
assert.match(cooldown, /약화 해제로 되돌릴 수 없습니다/);
assert.match(cooldown, /data-savior="member0"/);
assert.doesNotMatch(cooldown, /data-savior="member1"/);
assert.match(cooldown, /class="guess"/);
for (const code of ['SHIELD_GEN', 'SHIELD_GATED']) {
  const html = row(code, [['BREAK'], ['DEF_PEN']]);
  assert.match(html, /브레이크가 모든 보호막을 지우지는 않습니다/);
  assert.match(html, /class="guess"/);
}
for (const code of ['BUFF_STRIP', 'BUFF_BAN']) {
  const html = row(code, [['CLEANSE'], ['CD_REDUCE']]);
  assert.match(html, /재부여가 보장되지는 않습니다/);
  assert.match(html, /class="guess"/);
}
for (const code of ['SELF_DESTRUCT', 'ALLY_DEATH_TRIGGER', 'UNDYING', 'STANCE_CYCLE',
  'SLOT_DAMAGE_REDUCTION', 'CONDITIONAL_DAMAGE_REDUCTION', 'EXTRA_ACTION']) {
  assert.match(row(code, [['AOE', 'BURST', 'GAUGE_DOWN']]), /class="guess"/, code + ' 미확인 유지');
}
console.log('OK gim_note: 실제 자료의 확인·추정 표시, 조건부 대처, 담당 연결');
