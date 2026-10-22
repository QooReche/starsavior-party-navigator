# -*- coding: utf-8 -*-
"""build_gimmicks.py 의 큰 산출물(tools/raw/gimmicks/)에서 엔진·웹이 쓰는 압축 데이터를 만든다.
  data/gimmick_rules.json  : 유형 카탈로그(이름·선호/기피 태그·가중치·필요 슬롯), 구원자 태그
  data/stage_gimmicks.json : {콘텐츠|탭|스테이지: {유형코드: 심각도}}
사용: python -X utf8 -I tools/pack_gimmicks.py [산출물 폴더]"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, str(ROOT))
from battlesim.fileio import atomic_open, read_json
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "tools", "raw", "gimmicks")


def load(n):
    return read_json(os.path.join(SRC, n))


def main():
    cat = load("enemy_gimmicks.json")["type_catalog"]
    cnt = load("gimmick_counters.json")
    rules = {}
    for code, t in cat.items():
        rules[code] = {"name": t["name"], "w": t.get("weight", 1), "prefer": t.get("prefer_savior_tags", []),
                       "avoid": t.get("avoid_savior_tags", []), "slots": t.get("slots", []),
                       "good": t.get("good_structure", ""), "bad": t.get("bad_structure", ""), "conf": t.get("impact_confidence", "추정")}
    out = {"_note": "적 기믹 유형별 구원자 태그 선호/기피와 필요 슬롯(적 스킬 원문을 읽어 만든 유형 체계, 영향 방향은 대부분 추정). tags 는 구원자 스킬에서 뽑은 성향.",
           "_tagNotes": cnt["_meta"].get("tag_notes", ""), "types": rules,
           "tags": {k: sorted(v) for k, v in cnt["savior_tags"].items()}}
    with atomic_open(os.path.join(ROOT, "data", "gimmick_rules.json")) as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    st = {}
    for k, v in load("stage_gimmicks.json").items():
        if v.get("types"):
            st[k] = {c: x["sev"] for c, x in v["types"].items()}
    with atomic_open(os.path.join(ROOT, "data", "stage_gimmicks.json")) as f:
        json.dump(st, f, ensure_ascii=False, separators=(",", ":"))
    print("유형", len(rules), "구원자 태그", len(out["tags"]), "스테이지", len(st))


if __name__ == "__main__":
    main()
