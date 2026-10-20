# -*- coding: utf-8 -*-
"""게임 업데이트 후 데이터를 한 번에 다시 만든다(구조도·추천이 데이터에서 자동 갱신되도록).
사용: python -X utf8 -I tools/update.py [databook main.json(기본 rawdata/databook_main.json)] [--no-html] [--sim] [--sim-workers N]
  1) data/kinds.json (어나더/코즈믹)·data/power_penalty.json (전투력 보정 표)   2) synergy_tags.py (기능 태그)   3) tools/build_synergy_pairs.py (스킬 연계)
  4) tools/raw/foe.js 가 있으면 tools/build_foe.py (스테이지별 적 정보)
  5) --sim 이면 tools/build_sim_results.py (전투 시뮬 사전 계산 data/sim/*.json — 느림: 수 시간, 낮은 우선순위. 기본 프로세스 1개)
  6) build_party_html.py index.html
  주의: 데이터가 바뀌었는데 --sim 을 안 돌리면 웹은 버전이 다른 시뮬 결과를 숨기고 「시뮬 결과 없음」을 보인다(가짜 숫자 금지).
입력(저장소에 없음): 팬 데이터북 data/main.js 를 JSON 으로 푼 파일(`window.__SSD.x={...}` 를 json.JSONDecoder().raw_decode 로 파싱),
                    tools/raw/foe.js (데이터북 data/foe.js). 가이드 DB 가 바뀌면 data/db_tier.json·savior_reco.json·saviors_index.json 은 따로 갱신.
수동 보정은 data/synergy_overrides.json 에 적으면 다시 돌려도 유지된다."""
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PY = [sys.executable, "-X", "utf8", "-I"]


def run(*args):
    print("$", " ".join(os.path.basename(a) if os.sep in a else a for a in args))
    subprocess.run(PY + list(args), check=True, cwd=ROOT)


def load(p):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def main():
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--sim-workers"]
    src = os.path.abspath(args[0]) if args else os.path.join(ROOT, "rawdata", "databook_main.json")
    old_syn = load(os.path.join(ROOT, "data", "synergy_pairs.json"))
    old_roster = {p["a"] for p in old_syn} | {p["b"] for p in old_syn}

    dbm = json.load(open(src, encoding="utf-8"))
    kinds = []
    for u in dbm["units"]:
        t = dbm["rel"]["u"].get(str(u["id"]), {}).get("t")
        if t in ("C", "A"):
            kinds.append({"name": u["n"], "sub": u["ti"], "kind": t})
    with open(os.path.join(ROOT, "data", "kinds.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(kinds, f, ensure_ascii=False, indent=1)
    print("kinds:", len(kinds))
    pp = {"_note": "databook topics.pen: [비율하한, 비율상한(만분율), 아군 피해 배율(만분율), 적 피해 배율]. 전투력 비율 = 내 파티 전투력 / 권장 전투력. 90% 이상은 보정 없음. 회복·보호막은 적용 안 됨.",
          "pen": dbm["topics"]["pen"], "tribe": dbm["topics"]["tribe"]}
    with open(os.path.join(ROOT, "data", "power_penalty.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(pp, f, ensure_ascii=False, separators=(",", ":"))
    print("power_penalty:", len(pp["pen"]), "구간")

    run("synergy_tags.py", src)
    run(os.path.join("tools", "build_synergy_pairs.py"), src)
    if os.path.exists(os.path.join(ROOT, "rawdata", "foe.js")):
        run(os.path.join("tools", "build_foe.py"))
        run(os.path.join("tools", "build_gimmicks.py"), "--savior", src)
        run(os.path.join("tools", "pack_gimmicks.py"))
        run(os.path.join("tools", "sim_damage.py"), "index", "--out", os.path.join(ROOT, "tools", "raw", "damage_index.json"))
        run(os.path.join("tools", "pack_damage.py"))
    else:
        print("rawdata/foe.js 없음 -> 적 정보(data/foe_stages.json)는 그대로 둠")

    new_syn = load(os.path.join(ROOT, "data", "synergy_pairs.json"))
    key = lambda p: (p["a"], p["b"], p["type"])
    o, n = {key(p): p for p in old_syn}, {key(p): p for p in new_syn}
    changed = [k for k in n if k in o and (o[k]["strength"], o[k].get("conf")) != (n[k]["strength"], n[k].get("conf"))]
    new_chars = ({p["a"] for p in new_syn} | {p["b"] for p in new_syn}) - old_roster
    print(f"시너지 쌍: {len(old_syn)} -> {len(new_syn)} (추가 {len(set(n) - set(o))}, 삭제 {len(set(o) - set(n))}, 강도/신뢰 변경 {len(changed)}), 신규 구원자 키 {sorted(new_chars) or '없음'}")
    if "--sim" in sys.argv:
        w = sys.argv[sys.argv.index("--sim-workers") + 1] if "--sim-workers" in sys.argv else "1"
        run(os.path.join("tools", "build_sim_results.py"), "--workers", w)
    if "--no-html" not in sys.argv:
        run("build_party_html.py", "index.html")


if __name__ == "__main__":
    main()
