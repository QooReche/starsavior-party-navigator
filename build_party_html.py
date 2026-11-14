# -*- coding: utf-8 -*-
"""party_template.html 에 데이터를 넣어 단일 HTML 을 만든다. 사용: python -X utf8 -I build_party_html.py [출력경로]"""
import base64
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I 는 스크립트 폴더를 경로에서 뺀다
import guild_defense as gd  # noqa: E402
import party_reco as pr  # noqa: E402
from battlesim.fileio import atomic_text
from battlesim.starsavior.foe import load_extra
from battlesim.starsavior.savior_ids import uid_resolver

PORTRAIT_ROOT = "https://starsavior-guide.github.io/"  # 가이드 DB 초상화(온라인일 때만 표시, 없으면 글자 배지)
OUT_DEFAULT = os.path.join(pr.HERE, "..", "release", "party_preview", "index.html")
CONTENT_META = {  # foe key -> (표시 이름, 주 사용 콘텐츠명, 파티 수)
    "op": ("작전 (일반)", "작전", 1), "oph": ("작전 (어려움)", "작전", 1),
    "clo": ("성간 회랑", "회랑", 1), "rush": ("플래시 포인트", "플래시 포인트", 1),
    "cosmo": ("코스모 게이트", "코스모 게이트", 2), "daily": ("일일 재화 던전", None, 1),
    "equip": ("장비 탐사", None, 1), "cube": ("큐브 팰리스", None, 1), "clash": ("격전 의뢰", None, 1)}


_UNI = {"\u2160": "I", "\u2161": "II", "\u2162": "III", "\u2163": "IV", "\u2164": "V", "\u2165": "VI", "\u2166": "VII",
        "\u2167": "VIII", "\u2168": "IX", "\u2169": "X", "\u216a": "XI", "\u216b": "XII", "\u216c": "L", "\u216d": "C"}
_RV = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def numerize(name):
    """이름 끝의 로마 숫자(유니코드 Ⅰ~Ⅻ 와 ASCII 혼용 가능)를 아라비아 숫자로. 예: '혹한의 습격 XVI' -> '혹한의 습격 16'."""
    head, _, tail = name.rpartition(" ")
    t = "".join(_UNI.get(ch, ch) for ch in tail)
    if not head or not t or any(ch not in _RV for ch in t):
        return name
    tot = 0
    for i, ch in enumerate(t):
        v = _RV[ch]
        tot += -v if i + 1 < len(t) and _RV[t[i + 1]] > v else v
    return f"{head} {tot}"


def image_urls(roster, idx=None):
    """가이드 DB 의 구원자별 초상화/일러스트 주소 ({key: url}, {key: url})."""
    if idx is None:
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


def cosmo_raid_payload():
    """코스모 게이트 «3보스 최고 점수 편성 찾기» 화면 자료: 시즌·보스 이름·난이도 최대 레벨·탐색 설정(data/cosmo_raid.json 의 search). 스탯·챌린지 표 등은 싣지 않는다(시뮬 쪽이 읽음)."""
    g = pr._json(os.path.join(pr.DATA, "cosmo_raid.json"))
    return {"season": g["season"]["id"], "seasonPeriod": {k: g["season"].get(k) for k in ("start", "end")},
            "bosses": [{"key": b["key"], "name": b["name"], "element": b["element"]} for b in g["bosses"]],
            "levelMax": min(len(b["levels"]) for b in g["bosses"]), "search": g["search"], "scoreConf": g["score"]["conf"]}


def main(out=None):
    roster, growth, mains, cfg, tags = pr.load()
    idx = pr._json(os.path.join(pr.DATA, "saviors_index.json"))
    por, art = image_urls(roster, idx)
    grules = pr._json(pr.GRULES)
    # 저장소에 내려받아 둔 이미지(tools/fetch_images.py)가 있으면 그것을 상대 경로로 쓴다
    for s in roster:
        for d, suf in ((por, "face"), (art, "art")):
            rel = f"assets/savior/{s['key']}_{suf}.webp"
            if os.path.exists(os.path.join(pr.HERE, rel)):
                d[s["key"]] = rel
    # 게임 구원자 ID(uid): 내 정보 불러오기(myinfo_import.js)가 보유 구원자를 연결할 때 쓴다
    idx.pop("_meta", None)
    resolve_uid = uid_resolver(idx)

    def uid_of(s):
        return resolve_uid(s["key"], s["name"])
    r = []
    for s in roster:
        g = growth.get(s["key"])
        r.append({"key": s["key"], "uid": uid_of(s), "name": s["name"], "sub": s["subtitle"], "el": s["element"],
                  "cls": s["className"], "tier": g["tier"] if g else None,
                  "mains": mains.get(s["key"]), "tags": tags.get(s["key"], []), "gt": grules["tags"].get(s["key"], []), "img": por.get(s["key"], ""), "art": art.get(s["key"], "")})
    contents = []
    bosses, bpos = [], {}

    def bidx(name, role):
        if (name, role) not in bpos:
            bpos[(name, role)] = len(bosses)
            bosses.append([name, role])
        return bpos[(name, role)]
    def stages_of(c):
        stages = []
        for tab in c["tabs"]:
            # 작전은 게임 화면의 '섹터 변경' 처럼 번호로 표시(예: SECTOR 36 · 아가논 시가지)
            label = f'SECTOR {tab["section"]} · {tab["tab"]}' if tab.get("section") else tab["tab"]
            for st in tab["stages"]:
                w = {}
                for e in st["enemies"]:
                    w[e["element"]] = w.get(e["element"], 0) + e["count"] * (2 if e["boss"] else 1)
                stages.append({"tab": tab["tab"], "tabLabel": label, "name": st["name"], "label": numerize(st["name"]), "sb": (st.get("season_bonus_latest") or {}).get("bonuses", []), "sbn": (st.get("season_bonus_latest") or {}).get("season", ""), "lv": st["level"], "n": st["enemy_total"], "rp": st.get("recommended_power") or 0,
                               # 보스 = [보스 목록 번호, 수] (이름·직업은 맨 위 "bosses" 에 한 번만)
                               "bn": [[bidx(e["name"], e["role_kr"]), e["count"]] for e in st["enemies"] if e["boss"]],
                               "ec": st["element_counts"],
                               "w": w, "aoe": round(st["aoe_ratio"], 2), "def": round(st["defender_ratio"], 2)})
        return stages
    for c in pr._json(pr.FOE)["contents"]:
        if c['key'] == 'guild':
            continue  # 2.70 과거 시즌 목록. 현재 길방은 아래 guild_defense.json으로 한 번만 구성.
        name, main, parties = CONTENT_META[c["key"]]
        entry = {"key": c["key"], "name": name, "main": main, "parties": parties, "boss": c["key"] in ("cosmo", "rush", "clash"), "stages": stages_of(c)}
        if c["key"] == "cosmo":
            # 시즌제 화면: 목록에는 «코스모 게이트(시즌 N)» 로 보이고, 섹터·스테이지 선택 없이 시즌 패널만 쓴다. name 은 설정 키라 그대로 둔다
            entry["raid"] = True
            entry["title"] = f'{name}(시즌 {pr._json(os.path.join(pr.DATA, "cosmo_raid.json"))["season"]["id"] % 1000})'
        if c["key"] == "clash":
            # 기간 한정 콘텐츠: 공지 기준 기간(data/foe_clash.json period)을 게이트가 읽는다. 끝나면 «미오픈» 처리
            entry["seasonPeriod"] = ((load_extra(pr.HERE) or {}).get("period"))
        contents.append(entry)
    # 길드 방어전(시즌제): 시즌·단계 자료(data/guild_defense.json)에서 만든다. 일관성 검사를 통과해야 빌드된다
    gdef = gd.load()
    problems = gd.validate(gdef, grules["types"])
    assert not problems, "guild_defense.json 오류: " + "; ".join(problems)
    contents.append({"key": gd.CONTENT_KEY, "name": gd.content_title(gdef), "main": cfg["contents"][gd.CONTENT_NAME]["main"], "parties": gdef["rules"]["partyCount"],
                     "boss": True, "seasonal": True, "stages": stages_of(gd.foe_content(gdef))})
    out_cfg = {k: cfg[k] for k in ("advantage", "weights", "tagWeights", "breakSkills", "synergy", "power", "gimmick", "seasonBonus", "matchupModes", "damage")}
    out_cfg["restrict"] = {"성간 회랑": cfg["contents"]["회랑"]["restrictTabs"]}
    # mc._break_skill_rule: 표 기반 스킬 + 기존 평면 규칙을 쓰는 큐브 예외.
    mc_rules = pr._json(os.path.join(pr.HERE, "battlesim", "rules", "default.json"))["mc"]
    out_cfg["breakSupported"] = ["큐브 과부하", *mc_rules["break_skills"]]
    out_cfg["defPenByContent"] = {"코스모 게이트": cfg["contents"]["코스모 게이트"].get("defenderPenalty", 3.0)}
    icons = {}
    for kor, fn in {"스트라이커": "role_striker", "레인저": "role_ranger", "캐스터": "role_caster", "어쌔신": "role_assassin",
                    "디펜더": "role_defender", "서포터": "role_supporter", "sun": "attr_sun", "moon": "attr_moon",
                    "star": "attr_star", "order": "attr_order", "chaos": "attr_chaos"}.items():
        with open(os.path.join(pr.HERE, "assets", "ui_icons", fn + ".webp"), "rb") as f:
            icons[kor] = "data:image/webp;base64," + base64.b64encode(f.read()).decode()
    # 표시 태그: 이름+부제로 복수 행을 모음. kind는 기존 단일 관측 분류 호환용.
    kinds = {}
    for k in pr._json(os.path.join(pr.DATA, "kinds.json")):
        tags = kinds.setdefault((k["name"], k["sub"]), [])
        if k["kind"] not in tags:
            tags.append(k["kind"])
    for x in r:
        k = kinds.get((x["name"], x["sub"]))
        if k:
            x["kinds"] = k
            x["kind"] = next((t for t in k if t in ("C", "A")), None)
    bicons = {}
    bdir = os.path.join(pr.HERE, "assets", "break_icons")
    for fn in os.listdir(bdir):
        if fn.endswith(".jpg"):
            with open(os.path.join(bdir, fn), "rb") as f:
                bicons[fn[:-4]] = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    raw_syn = pr.load_synergy()
    syn = [{"a": p["a"], "b": p["b"], "t": int(p["type"].split(":")[0]), "tn": p["type"].split(":", 1)[1], "s": p["strength"],
            "c": p.get("conf", "추정"), "d": bool(p.get("directed")), "r": p.get("reason", "")}
           for p in raw_syn]
    # 근거 문장(e)은 선 탭 시 요청하도록 별도 분리. D.syn에는 포함하지 않음.
    syn_detail = [[e[:110] for e in p.get("evidence", [])[:2]] for p in raw_syn]
    syn_detail_str = json.dumps(syn_detail, ensure_ascii=False, separators=(",", ":"))
    syn_detail_bytes = syn_detail_str.encode("utf-8")
    syn_detail_url = "data/syn_detail.json?v=" + hashlib.sha256(syn_detail_bytes).hexdigest()[:12]
    atomic_text(os.path.join(pr.HERE, "data", "syn_detail.json"), syn_detail_str)
    # Cytoscape 지연 로드용 콘텐츠 해시 URL
    cyto_path = os.path.join(pr.HERE, "lib", "cytoscape.min.js")
    with open(cyto_path, "rb") as f:
        cyto_bytes = f.read()
    cyto_url = "lib/cytoscape.min.js?v=" + hashlib.sha256(cyto_bytes).hexdigest()[:12]
    # 스킬·성장표는 필요할 때 요청함. quick.json은 페이지 시작 시 요청함.
    skill_path = os.path.join(pr.DATA, "savior_skills.json")
    with open(skill_path, "rb") as f:
        skill_bytes = f.read()
    skills = json.loads(skill_bytes)
    assert all(str(s["uid"]) in skills for s in r), "Missing public skills for roster uid"
    skill_url = "data/savior_skills.json?v=" + hashlib.sha256(skill_bytes).hexdigest()[:12]
    # 별도 생성 단계 tools/build_myinfo_view.py가 공개 설명 자료를 담당함.
    power = pr._json(pr.POW)
    data = json.dumps({"roster": r, "archiveGrades": pr._json(os.path.join(pr.DATA, "archive_grades.json")), "growthView": {**pr._json(os.path.join(pr.DATA, "myinfo_view.json")), "itemSlots": pr._json(os.path.join(pr.DATA, "myinfo_slots.json"))}, "journeyPriority": pr._json(os.path.join(pr.DATA, "journey_priority.json")), "skillsUrl": skill_url, "skillIcons": pr._json(os.path.join(pr.DATA, "skill_icons.json"))["units"], "synDetailUrl": syn_detail_url, "cytoUrl": cyto_url,
                       "contents": contents, "cfg": out_cfg, "icons": icons, "bicons": bicons, "syn": syn, "bosses": bosses,
                       "pen": power["pen"], "tribe": power["tribe"],
                       "grules": grules["types"], "plain": pr._json(os.path.join(pr.DATA, "gimmick_plain.json")), "gim": pr.gimmick_rules()[1],"dmg": pr._json(pr.DMG), "guild": gd.page_payload(gdef), "cosmoRaid": cosmo_raid_payload()}, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(pr.HERE, "party_template.html"), encoding="utf-8") as f:
        html = f.read()
    assert html.count("/*DATA*/null") == 1
    html = html.replace("/*DATA*/null", data.replace("</", "<\\/"))
    out = out or (sys.argv[1] if len(sys.argv) > 1 else OUT_DEFAULT)
    atomic_text(out, html)
    print(out, len(html.encode('utf-8')), "bytes (UTF-8)")
    # 여정 스탯 우선순위(공략 DB): 로스터에 있는데 표에 없으면 다시 뽑아야 하고(중단), 공략 DB 에 아직 없어 직업 기본값으로 채운 구원자는 알린다
    jp = pr._json(os.path.join(pr.DATA, "journey_priority.json"))
    stale = [s["key"] for s in roster if s["key"] not in jp["units"]]
    if stale:
        raise SystemExit("여정 스탯 우선순위에 없는 구원자 %d명: %s — node tools/extract_journey_priority.js 를 다시 실행" % (len(stale), ", ".join(stale)))
    if jp.get("fallback"):
        print("[알림] 여정 스탯 우선순위: 공략 DB 에 없는 구원자 %d명(직업 기본값으로 판단, DB 받은 날짜 %s): %s" % (
            len(jp["fallback"]), jp.get("db_fetched") or "기록 없음", ", ".join("%s(%s)" % kv for kv in jp["fallback"].items())))


if __name__ == "__main__":
    main()
