# -*- coding: utf-8 -*-
"""근사 점수 추천(party_reco)을 웹과 같은 규칙으로 부르는 도우미 — 시험(tests/e2e 의 파이썬·JS 대조)용.
옛 사전 계산 도구(tools/build_sim_results.py, 2026-10-20 퇴역)에서 필요한 부분만 옮겼다."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
import party_reco as pr  # noqa: E402
from build_party_html import CONTENT_META  # noqa: E402

_CACHE = {}


def base():
    if not _CACHE:
        roster, growth, mains, cfg, tags = pr.load()
        fs = pr._json(pr.FOE)
        _CACHE.update(roster=roster, growth=growth, mains=mains, cfg=cfg, tags=tags, fs=fs)
    return _CACHE


def stage_obj(foe_key, tab, name):
    for c in base()["fs"]["contents"]:
        if c["key"] != foe_key:
            continue
        for t in c["tabs"]:
            if t["tab"] != tab:
                continue
            for st in t["stages"]:
                if st["name"] == name:
                    return st
    raise KeyError("%s/%s/%s" % (foe_key, tab, name))


def candidates(foe_key, tab, st, used=()):
    b = base()
    cfg = b["cfg"]
    cname, main, _ = CONTENT_META[foe_key]
    boss = foe_key in ("cosmo", "rush")
    pr.set_stage(foe_key, tab, st, boss, cfg)
    rest = cfg["contents"]["회랑"].get("restrictTabs", {}).get(tab) if cname == "성간 회랑" else None
    enemies = pr.stage_enemies(st)
    out = []
    for s in b["roster"]:
        if s["key"] in used or (rest and s["element"] != rest):
            continue
        v, parts = pr.score(s, b["growth"], b["mains"], cfg, main, enemies, boss)
        out.append({"s": s, "g": b["growth"].get(s["key"]), "score": v, "parts": parts})
    def_pen = cfg["contents"]["코스모 게이트"].get("defenderPenalty", 3.0) if cname == "코스모 게이트" else cfg["weights"]["defenderPenalty"]
    return out, def_pen


def ckey(combo):
    return ",".join(sorted(x["s"]["key"] for x in combo))
