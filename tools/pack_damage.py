# -*- coding: utf-8 -*-
"""tools/sim_damage.py index 가 만든 큰 지표(tools/raw/damage_index.json)에서 엔진·웹용 압축 데이터 data/damage_index.json 을 만든다.
사용: python -X utf8 -I tools/pack_damage.py"""
import sys
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, str(ROOT))
from battlesim.fileio import atomic_open, read_json


def main():
    full = read_json(os.path.join(ROOT, "tools", "raw", "damage_index.json"))
    old = read_json(os.path.join(ROOT, "data", "damage_index.json"))
    comp = {}
    for k, v in full.items():
        if "@" in k or not isinstance(v, dict) or "single_dpt" not in v:
            continue
        comp[k] = {"s": round(v["single_dpt"]), "a": round(v["aoe_dpt"]), "g": v["ally_dmg_gain_pct"], "h": v["hits_per_turn"],
                   "x": v["extra_hit_dmg_share"], "d": bool(v.get("ally_dependent"))}
    old["units"] = comp  # ref95(무작위 4딜러 팀 95백분위)는 기준값이라 유지한다. 구원자 풀이 크게 바뀌면 sim_report.md 방법으로 다시 구할 것
    with atomic_open(os.path.join(ROOT, "data", "damage_index.json")) as f:
        json.dump(old, f, ensure_ascii=False, separators=(",", ":"))
    print("화력 지표", len(comp), "명")


if __name__ == "__main__":
    main()
