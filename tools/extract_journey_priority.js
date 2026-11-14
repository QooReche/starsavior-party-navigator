// 가이드 DB(starsavior-guide.github.io)의 app-core.js 에서 구원자별 «여정 스탯 우선순위»를 data/journey_priority.json 으로 뽑는다.
//   원본: JOURNEY_STAT_PRIORITY_PATTERNS(직업별 기본) · JOURNEY_STAT_PRIORITY_EXCEPTIONS(구원자별 예외) · getJourneyStatPriorityRows(고르는 규칙) — 가이드 코드를 그대로 실행해 뽑는다
//   (규칙을 여기 옮겨 적지 않는다: 가이드가 바뀌면 다시 뽑기만 하면 된다).
// 산출: {source, grade:"guide", stats:[힘,체력,인내,집중,보호], db_fetched, roster, fallback:{key: 직업}, units:{구원자 key:[{label, note, groups:[[칸 번호,…],…]}]}}
//   groups = 앞 묶음이 더 우선, 같은 묶음 안은 동률. 한 구원자에 줄이 둘이면(일반 디펜더: 퓨어탱커 / 공격력 탱커) 가이드가 둘 중 하나를 고르지 않은 것 — 둘 다 싣는다.
// 공략 DB 는 늦게 갱신될 수 있다 → 페이지 로스터(data/savior_reco.json)와 대조한다:
//   · 로스터에는 있는데 DB(SAVIORS)에 없는 구원자(신규 등)는 «직업 기본 우선순위»(가이드의 같은 함수에 직업만 넣은 값)로 채우고 fallback 에 적는다.
//     조용히 대체하지 않는다 — 화면은 «공략 DB 미반영 · 직업 기본값»을 보이고, 이 도구·빌드·시험이 «DB 에 없는 구원자 N명»을 알린다.
//   · db_fetched = rawdata 를 받은 날짜(rawdata/sources.json, tools/fetch_sources.py 가 적음. 없으면 null)
// 쓰는 곳: 「클리어 추천 육성」의 스텔라 아카이브 목표(myinfo_reco.js). 엔진의 표준 육성 기준표(battlesim/rules/builds.json)는 이 표를 쓰지 않는다(HANDOFF 22번).
// 사용: node tools/extract_journey_priority.js [app-core.js 경로] [로스터 json 경로] [산출 경로]   (기본 rawdata/guide_app-core.js · data/savior_reco.json · data/journey_priority.json)
const fs = require("fs");
const path = require("path");
const {atomicText} = require('./fileio.js');
const root = path.join(__dirname, "..");
const src = process.argv[2] || path.join(root, "rawdata", "guide_app-core.js");
const rosterPath = process.argv[3] || path.join(root, "data", "savior_reco.json");
const outPath = process.argv[4] || path.join(root, "data", "journey_priority.json");
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
const convert = (s) => {
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
  return out;
};
const units = {}, fallback = {};
for (const s of saviors) units[s.id] = convert(s);
// 페이지 로스터 대조: DB 에 없는 구원자는 직업 기본값(가이드 함수의 직업 분기) + fallback 표시
const roster = JSON.parse(fs.readFileSync(rosterPath, "utf8")).saviors;
for (const s of roster) {
  if (units[s.key]) continue;
  if (!s.className) throw new Error(s.key + ": 로스터에 직업(className)이 없어 직업 기본값도 정할 수 없음");
  units[s.key] = convert({id: s.key, className: s.className});
  fallback[s.key] = s.className;
}
let fetched = null;
try { fetched = JSON.parse(fs.readFileSync(path.join(root, "rawdata", "sources.json"), "utf8")).fetched || null; } catch (e) { fetched = null; }
atomicText(outPath, JSON.stringify({
  source: "rawdata/guide_app-core.js: JOURNEY_STAT_PRIORITY_PATTERNS · JOURNEY_STAT_PRIORITY_EXCEPTIONS · getJourneyStatPriorityRows (tools/extract_journey_priority.js)",
  grade: "guide", stats: STATS, db_fetched: fetched, roster: "data/savior_reco.json",
  fallback_note: "fallback = 페이지 로스터에는 있으나 공략 DB 에 아직 없는 구원자 — 직업 기본 우선순위로 채움(공략 DB 미반영)",
  fallback, units}, null, 1) + "\n");
const missing = Object.keys(fallback);
console.log("여정 스탯 우선순위", Object.keys(units).length, "명, 두 줄(디펜더)", Object.values(units).filter((r) => r.length > 1).length, "명, DB 받은 날짜", fetched || "기록 없음");
console.log(missing.length ? "[알림] 공략 DB 에 없는 구원자 " + missing.length + "명(직업 기본값으로 채움): " + missing.map((k) => k + "(" + fallback[k] + ")").join(", ")
  : "공략 DB 에 없는 구원자 0명");
