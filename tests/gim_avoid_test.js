// gimAvoid(불리한 구원자 표시) 시험: party_template.html 에서 함수만 꺼내 가짜 데이터로 돌린다.
// 실행: node tests/gim_avoid_test.js
const fs = require("fs"), path = require("path"), assert = require("assert");
const tpl = fs.readFileSync(path.join(__dirname, "..", "party_template.html"), "utf8");
const m = tpl.match(/function gimAvoid\(party,types,p\)\{[\s\S]*?\n function?|function gimAvoid\(party,types,p\)\{[\s\S]*?<\/details>`\}\n/);
assert(m, "gimAvoid 를 찾지 못함");
const plain = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "gimmick_plain.json"), "utf8"));
const rules = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "gimmick_rules.json"), "utf8")).types;
const run = (party, types, GIMACT) => new Function("D", "GIMACT", "esc", "face", m[0] + "; return gimAvoid;")(
  {plain, grules: rules}, GIMACT, s => String(s), () => "")(party, types, 1);
const mk = (key, gt) => ({s: {key, name: key, cls: "딜러", gt}});
// 1) 불리한 구원자 없음 -> 빈 문자열
assert.strictEqual(run([mk("a", ["DEALER"])], [["TURN_HIT_REDUCTION", 2]], []), "");
// 2) 기믹 없음 -> 빈 문자열
assert.strictEqual(run([mk("a", ["MULTIHIT"])], [], []), "");
// 3) 연타형 + 감점 대상 -> 이름·이유·점수 반영 배지, 기본 닫힘
const h = run([mk("a", ["MULTIHIT"]), mk("b", ["DEALER"])], [["TURN_HIT_REDUCTION", 2]], [["TURN_HIT_REDUCTION", 2]]);
assert(h.includes("불리한 구원자 1명") && h.includes("연타형") && h.includes("guess scored") && !h.includes(" open"), h);
assert(!h.includes('data-savior="b"'));
// 4) 점수 대상이 아닌 기믹(GIMACT 밖)이면 배지 없음, 추정 유형이면 추정 배지
const h2 = run([mk("a", ["MULTIHIT"])], [["HIT_RETALIATION", 1]], []);
assert(!h2.includes("guess scored") && h2.includes("추정"), h2);
console.log("OK gim_avoid");
