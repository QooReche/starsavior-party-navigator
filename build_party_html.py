# -*- coding: utf-8 -*-
"""party_template.html 에 데이터를 넣어 단일 HTML 을 만든다. 사용: python -X utf8 -I build_party_html.py [출력경로]"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I 는 스크립트 폴더를 경로에서 뺀다
import party_reco as pr  # noqa: E402

PORTRAIT_ROOT = "https://starsavior-guide.github.io/"  # 가이드 DB 초상화(온라인일 때만 표시, 없으면 글자 배지)
OUT_DEFAULT = os.path.join(pr.HERE, "..", "release", "party_preview", "index.html")
CONTENT_META = {  # foe key -> (표시 이름, 주 사용 콘텐츠명, 파티 수)
    "op": ("작전 (일반)", "작전", 1), "oph": ("작전 (어려움)", "작전", 1),
    "clo": ("성간 회랑", "회랑", 1), "rush": ("플래시 포인트", "플래시 포인트", 1),
    "cosmo": ("코스모 게이트", "코스모 게이트", 2), "daily": ("일일 재화 던전", None, 1),
    "equip": ("장비 탐사", None, 1), "cube": ("큐브 팰리스", None, 1)}


def image_urls(roster):
    """가이드 DB 의 구원자별 초상화/일러스트 주소 ({key: url}, {key: url})."""
    idx = pr._json(os.path.join(pr.DATA, "saviors_index.json"))
    por = {v["key"]: v["profile"]["portrait"].replace("./", PORTRAIT_ROOT, 1)
           for v in idx.values() if v.get("profile", {}).get("portrait")}
    art = {v["key"]: v["profile"]["illustration"].replace("./", PORTRAIT_ROOT, 1)
           for v in idx.values() if v.get("profile", {}).get("illustration")}
    # 인덱스에 key 가 'source-<id>' 로만 들어 있는 구원자(예: 아모라)는 이름으로 연결한다
    by_name = {}
    for s in roster:
        by_name.setdefault(s["name"], []).append(s["key"])
    for v in idx.values():
        if not str(v.get("key", "")).startswith("source-"):
            continue
        ks = [k for k in by_name.get(v.get("profile", {}).get("name"), []) if k not in por]
        if len(ks) == 1:
            if v["profile"].get("portrait"):
                por[ks[0]] = v["profile"]["portrait"].replace("./", PORTRAIT_ROOT, 1)
            if v["profile"].get("illustration"):
                art[ks[0]] = v["profile"]["illustration"].replace("./", PORTRAIT_ROOT, 1)
    return por, art


def main():
    roster, growth, mains, cfg, tags = pr.load()
    por, art = image_urls(roster)
    # 저장소에 내려받아 둔 이미지(tools/fetch_images.py)가 있으면 그것을 상대 경로로 쓴다
    for s in roster:
        for d, suf in ((por, "face"), (art, "art")):
            rel = f"assets/savior/{s['key']}_{suf}.webp"
            if os.path.exists(os.path.join(pr.HERE, rel)):
                d[s["key"]] = rel
    r = []
    for s in roster:
        g = growth.get(s["key"])
        r.append({"key": s["key"], "name": s["name"], "sub": s["subtitle"], "el": s["element"],
                  "cls": s["className"], "tier": g["tier"] if g else None,
                  "mains": mains.get(s["key"]), "tags": tags.get(s["key"], []), "img": por.get(s["key"], ""), "art": art.get(s["key"], "")})
    contents = []
    for c in pr._json(pr.FOE)["contents"]:
        name, main, parties = CONTENT_META[c["key"]]
        stages = []
        for tab in c["tabs"]:
            # 작전은 게임 화면의 '섹터 변경' 처럼 번호로 표시(예: SECTOR 36 · 아가논 시가지)
            label = f'SECTOR {tab["section"]} · {tab["tab"]}' if tab.get("section") else tab["tab"]
            for st in tab["stages"]:
                w = {}
                for e in st["enemies"]:
                    w[e["element"]] = w.get(e["element"], 0) + e["count"] * (2 if e["boss"] else 1)
                stages.append({"tab": tab["tab"], "tabLabel": label, "name": st["name"], "lv": st["level"], "n": st["enemy_total"],
                               "w": w, "aoe": round(st["aoe_ratio"], 2), "def": round(st["defender_ratio"], 2)})
        contents.append({"name": name, "main": main, "parties": parties, "boss": c["key"] in ("cosmo", "rush"), "stages": stages})
    out_cfg = {k: cfg[k] for k in ("advantage", "tierScore", "weights", "tagWeights", "breakSkills", "templates", "pairs", "synergy")}
    out_cfg["defPenByContent"] = {"코스모 게이트": cfg["contents"]["코스모 게이트"].get("defenderPenalty", 3.0)}
    icons = {}
    for kor, fn in {"스트라이커": "role_striker", "레인저": "role_ranger", "캐스터": "role_caster", "어쌔신": "role_assassin",
                    "디펜더": "role_defender", "서포터": "role_supporter", "sun": "attr_sun", "moon": "attr_moon",
                    "star": "attr_star", "order": "attr_order", "chaos": "attr_chaos"}.items():
        with open(os.path.join(pr.HERE, "assets", "ui_icons", fn + ".webp"), "rb") as f:
            icons[kor] = "data:image/webp;base64," + base64.b64encode(f.read()).decode()
    # 어나더/코즈믹 분류: databook rel.u[id].t (N 일반 / C 코즈믹 / A 어나더), 이름+부제로 연결
    kinds = {(k["name"], k["sub"]): k["kind"] for k in pr._json(os.path.join(pr.DATA, "kinds.json"))}
    for x in r:
        k = kinds.get((x["name"], x["sub"]))
        if k:
            x["kind"] = k
    bicons = {}
    bdir = os.path.join(pr.HERE, "assets", "break_icons")
    for fn in os.listdir(bdir):
        if fn.endswith(".jpg"):
            with open(os.path.join(bdir, fn), "rb") as f:
                bicons[fn[:-4]] = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    syn = [{"a": p["a"], "b": p["b"], "t": int(p["type"].split(":")[0]), "tn": p["type"].split(":", 1)[1], "s": p["strength"],
            "c": p.get("conf", "추정"), "d": bool(p.get("directed")), "r": p.get("reason", ""),
            "e": [e[:110] for e in p.get("evidence", [])[:2]]}
           for p in pr.load_synergy()]
    data = json.dumps({"roster": r, "contents": contents, "cfg": out_cfg, "icons": icons, "bicons": bicons, "syn": syn}, ensure_ascii=False, separators=(",", ":"))
    html = open(os.path.join(pr.HERE, "party_template.html"), encoding="utf-8").read()
    assert html.count("/*DATA*/null") == 1
    html = html.replace("/*DATA*/null", data.replace("</", "<\/"))
    out = sys.argv[1] if len(sys.argv) > 1 else OUT_DEFAULT
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(out, len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
