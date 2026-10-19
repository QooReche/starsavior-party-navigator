// 가이드 DB(starsavior-guide.github.io)의 app-core.js 에서 PVE 티어(GROWTH_PRIORITY)와 주 사용 콘텐츠(MAIN_CONTENTS)를 data/db_tier.json 으로 뽑는다.
// 사용: node tools/extract_guide_tier.js [app-core.js 경로, 기본 rawdata/guide_app-core.js]
const fs = require("fs");
const path = require("path");
const root = path.join(__dirname, "..");
const src = process.argv[2] || path.join(root, "rawdata", "guide_app-core.js");
const lines = fs.readFileSync(src, "utf8").split("\n");
const grab = (name) => {
  const s = lines.findIndex((l) => l.startsWith("const " + name + " ="));
  if (s < 0) throw new Error(name + " 를 찾지 못함 (가이드 DB 구조가 바뀌었을 수 있음)");
  let e = s;
  while (!/^};/.test(lines[e])) e++;
  return new Function(lines.slice(s, e + 1).join("\n") + "\nreturn " + name + ";")();
};
const growth = grab("GROWTH_PRIORITY"), mainContents = grab("MAIN_CONTENTS");
fs.writeFileSync(path.join(root, "data", "db_tier.json"), JSON.stringify({ growth, mainContents }, null, 1));
console.log("티어", Object.keys(growth).length, "주 사용 콘텐츠", Object.keys(mainContents).length);
