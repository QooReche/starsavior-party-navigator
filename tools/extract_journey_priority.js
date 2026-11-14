// 가이드 DB(starsavior-guide.github.io)의 app-core.js 에서 구원자별 «여정 스탯 우선순위»를 data/journey_priority.json 으로 뽑는다.
//   원본: JOURNEY_STAT_PRIORITY_PATTERNS(직업별 기본) · JOURNEY_STAT_PRIORITY_EXCEPTIONS(구원자별 예외) · getJourneyStatPriorityRows(고르는 규칙) — 가이드 코드를 그대로 실행해 뽑는다
//   (규칙을 여기 옮겨 적지 않는다: 가이드가 바뀌면 다시 뽑기만 하면 된다).
// 산출: {source, grade:"guide", stats:[힘,체력,인내,집중,보호], units:{구원자 key:[{label, note, groups:[[칸 번호,…],…]}]}}
//   groups = 앞 묶음이 더 우선, 같은 묶음 안은 동률. 한 구원자에 줄이 둘이면(일반 디펜더: 퓨어탱커 / 공격력 탱커) 가이드가 둘 중 하나를 고르지 않은 것 — 둘 다 싣는다.
// 쓰는 곳: 「클리어 추천 육성」의 스텔라 아카이브 목표(myinfo_reco.js). 엔진의 표준 육성 기준표(battlesim/rules/builds.json)는 이 표를 쓰지 않는다(HANDOFF 22번).
// 사용: node tools/extract_journey_priority.js [app-core.js 경로, 기본 rawdata/guide_app-core.js]
const fs = require("fs");
const path = require("path");
const {atomicText} = require('./fileio.js');
const root = path.join(__dirname, "..");
const src = process.argv[2] || path.join(root, "rawdata", "guide_app-core.js");
const lines = fs.readFileSync(src, "utf8").split("\n");
const block = (start, end) => {
  const s = lines.findIndex((l) => l.startsWith(start));
  if (s < 0) throw new Error(start + " 를 찾지 못함 (가이드 DB 구조가 바뀌었을 수 있음)");
  let e = s;
  while (e < lines.length && !end.test(lines[e])) e++;
  if (e === lines.length) throw new Error(start + " 끝을 찾지 못함");
  return lines.slice(s, e + 1).join("\n");
};
const code = [block("const JOURNEY_STAT_PRIORITY_PATTERNS =", /^}\);/), block("const JOURNEY_STAT_PRIORITY_EXCEPTIONS =", /^}\);/),
  block("function getJourneyStatPriorityRows(", /^}/)].join("\n");
const rows = new Function(code + "\nreturn getJourneyStatPriorityRows;")();
// SAVIORS 는 다른 함수들을 부르므로 실행하지 않고, 구원자 항목 첫머리의 id·className 줄만 읽는다(들여쓰기 4칸 = 구원자 항목의 바로 아래 값)
const saviors = [];
for (const l of block("const SAVIORS =", /^];/).split("\n")) {
  const id = l.match(/^    "id": "([^"]+)",?\s*$/), cls = l.match(/^    "className": "([^"]+)",?\s*$/);
  if (id) saviors.push({id: id[1], className: null});
  else if (cls && saviors.length && saviors[saviors.length - 1].className === null) saviors[saviors.length - 1].className = cls[1];
}
if (!saviors.length || saviors.some((s) => !s.className)) throw new Error("SAVIORS 의 id·className 을 읽지 못함 (가이드 DB 구조가 바뀌었을 수 있음)");
const STATS = ["힘", "체력", "인내", "집중", "보호"];
const units = {};
for (const s of saviors) {
  const out = rows(s).map((r) => ({label: r.label || "", note: r.note || "", groups: r.groups.map((g) => g.map((n) => {
    const i = STATS.indexOf(n);
    if (i < 0) throw new Error(s.id + ": 모르는 스탯 " + n);
    return i;
  }))}));
  for (const r of out) {
    const flat = r.groups.flat();
    if (flat.length !== 5 || new Set(flat).size !== 5) throw new Error(s.id + ": 다섯 칸이 한 번씩 나와야 함 " + JSON.stringify(r.groups));
  }
  if (!out.length) throw new Error(s.id + ": 우선순위 없음");
  units[s.id] = out;
}
atomicText(path.join(root, "data", "journey_priority.json"), JSON.stringify({
  source: "rawdata/guide_app-core.js: JOURNEY_STAT_PRIORITY_PATTERNS · JOURNEY_STAT_PRIORITY_EXCEPTIONS · getJourneyStatPriorityRows (tools/extract_journey_priority.js)",
  grade: "guide", stats: STATS, units}, null, 1) + "\n");
console.log("여정 스탯 우선순위", Object.keys(units).length, "명, 두 줄(디펜더)", Object.values(units).filter((r) => r.length > 1).length, "명");
