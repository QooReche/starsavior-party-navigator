# -*- coding: utf-8 -*-
"""길드 방어전(시즌제) 자료 도우미. 시즌·단계·별의 도전·선택 효과·점수 가설은 data/guild_defense.json 한 곳에만 둔다.
이 모듈은 그 자료를 (1) 추천 로직이 읽는 스테이지 모양(foe_stages.json 과 같은 형식)으로 바꾸고, (2) 점수 범위를 계산하고,
(3) 시즌 종료 여부로 「갱신 대기」를 판정하고, (4) 자료 일관성을 검사한다. 화면 쪽 계산은 guild_view.js 가 같은 규칙으로 한다
(tests/guild_defense_test.py 가 두 구현의 일치를 확인)."""
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "data", "guild_defense.json")
KST = datetime.timezone(datetime.timedelta(hours=9))
CONTENT_KEY = "guild"        # 화면·추천 안에서 쓰는 콘텐츠 키(foe key)
CONTENT_NAME = "길드방어전"  # party_contents.json 의 콘텐츠 이름(시즌과 무관한 고정 이름)
EX_STEP = 7
MAX_SET_TIER = 3


def load(path=PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_time(s):
    """'2026-11-05T04:00:00+09:00' 또는 날짜만('2026-10-29' = 한국 시간 0시) -> aware datetime."""
    if "T" not in s:
        s += "T00:00:00+09:00"
    return datetime.datetime.fromisoformat(s)


def range_label(g):
    """'시즌4 10/29~11/05' (시작·끝 날짜는 한국 시간 기준, 끝이 04:00 이전이면 전날이 아니라 공지 표기대로 끝 날짜)"""
    s, e = parse_time(g["season"]["start"]).astimezone(KST), parse_time(g["season"]["end"]).astimezone(KST)
    return f'{g["season"]["label"]} {s.month:02d}/{s.day:02d}~{e.month:02d}/{e.day:02d}'


def content_title(g):
    return f"{CONTENT_NAME}({range_label(g)})"


def season_state(g, now):
    """now(aware datetime) 기준 시즌 상태. state = upcoming / active / settling / ended.
    needs_update = 시즌 종료 시각이 지나 이 자료가 지난 시즌 것일 수 있음(갱신 대기)."""
    se = g["season"]
    start, end, settle = parse_time(se["start"]), parse_time(se["end"]), parse_time(se["settleEnd"])
    if now < start:
        st = "upcoming"
    elif now < end:
        st = "active"
    elif now < settle:
        st = "settling"
    else:
        st = "ended"
    return {"state": st, "needs_update": now >= end}


def ex_step(g):
    return next(s for s in g["steps"] if s["ex"])


def base_total(g):
    """EX 기본 합계 = 기본 점수 + 졸개 처치 점수 + 보스 처치 점수."""
    ex = ex_step(g)
    return ex["base"] + g["stepsMeta"]["minions"] * ex["kill"] + ex["bossKill"]


def extra_pct(g, level, tiers=(0, 0, 0, 0)):
    """추가 점수 % = 별의 도전 단계(0 이면 도전 없음) + 선택 효과 단계(효과별 0~3)의 합."""
    pct = 0
    if level:
        pct += g["challenge"]["levels"][level - 1]["score"]
    for item, t in zip(g["sets"]["items"], tiers):
        if t:
            pct += item["tiers"][t - 1]["add"]
    return pct


def score(g, pct):
    """{가설 id: 점수}. A = 합계 전체 x (1+pct%), B = 보스 처치 점수를 뺀 나머지만 x (1+pct%)."""
    ex = ex_step(g)
    boss = ex["bossKill"]
    total = base_total(g)
    out = {}
    for h in g["score"]["hypotheses"]:
        if h["bossExcluded"]:
            out[h["id"]] = round((total - boss) * (100 + pct) / 100 + boss)
        else:
            out[h["id"]] = round(total * (100 + pct) / 100)
    return out


def best_selection(g):
    """점수가 가장 높은 선택(두 가설 모두 단조 증가): 도전 최고 단계 + 선택 효과 모두 최대 단계."""
    return len(g["challenge"]["levels"]), tuple(MAX_SET_TIER for _ in g["sets"]["items"])


def foe_content(g):
    """추천 로직이 읽는 콘텐츠(foe_stages.json 의 contents 항목과 같은 모양). EX 를 맨 앞에 둔다(기본 선택 = 최고 단계)."""
    boss = g["season"]["boss"]
    tab = range_label(g)
    stages = []
    for s in sorted(g["steps"], key=lambda x: -x["step"]):
        n = 1 + g["stepsMeta"]["minions"]
        stages.append({
            "name": stage_name(s), "level": s["battleLevel"], "recommended_power": s["power"], "wave_count": 2,
            "enemy_total": n, "dominant_element": boss["element"], "element_counts": {boss["element"]: 1},
            "role_counts": {"ranger": 1}, "aoe_ratio": 0.0, "defender_ratio": 0.0, "has_boss": True,
            "enemies": [{"name": boss["name"], "title": "", "element": boss["element"], "role": "ranger", "role_kr": boss["role"],
                         "attackType": "", "boss": True, "elite": False, "level": s["battleLevel"], "count": 1}]})
    return {"key": CONTENT_KEY, "tabs": [{"tab": tab, "section": None, "stages": stages}]}


def stage_name(step):
    return f'{step["step"]}단계 EX' if step["ex"] else f'{step["step"]}단계'


def stage_gimmicks(g):
    """{'guild|탭|스테이지': {코드: 심각도}} (stage_gimmicks.json 과 같은 모양)."""
    tab = range_label(g)
    names = {s["step"]: stage_name(s) for s in g["steps"]}
    out = {}
    for it in g["gimmicks"]["items"]:
        for st in it["steps"]:
            out.setdefault(f"{CONTENT_KEY}|{tab}|{names[st]}", {})[it["code"]] = it["severity"]
    return out


def validate(g, grules=None):
    """자료 일관성 검사. 문제 문장 목록(비면 정상)."""
    bad = []
    se = g["season"]
    try:
        s, e, d = parse_time(se["start"]), parse_time(se["end"]), parse_time(se["settleEnd"])
        if not s < e < d:
            bad.append("시즌 시작 < 종료 < 결산 종료 순서가 아님")
    except (ValueError, KeyError) as ex:
        bad.append(f"시즌 날짜 형식 오류: {ex}")
    for k in ("asOf", "gameBuild"):
        if not g.get(k):
            bad.append(f"{k} 없음")
    src = g.get("sources", {})

    def chk(block, name):
        if block.get("conf") not in ("확인", "추정", "낮음"):
            bad.append(f"{name}: conf 가 확인/추정/낮음이 아님")
        for k in block.get("src", []):
            if k not in src:
                bad.append(f"{name}: 알 수 없는 출처 {k}")
    for name in ("season", "rules", "stepsMeta", "exBoss", "challenge", "sets", "score", "gimmicks", "community"):
        chk(g[name], name)
    for it in g["community"]["items"] + g["gimmicks"]["items"]:
        for k in it.get("src", []):
            if k not in src:
                bad.append(f"출처 {k} 없음")
    steps = g["steps"]
    if [x["step"] for x in steps] != list(range(1, len(steps) + 1)):
        bad.append("단계 번호가 1부터 연속이 아님")
    if sum(1 for x in steps if x["ex"]) != 1 or not steps[-1]["ex"]:
        bad.append("EX 단계는 마지막 하나여야 함")
    for a, b in zip(steps, steps[1:]):
        if b["bossKill"] <= a["bossKill"] or b["power"] <= a["power"] or b["battleLevel"] <= a["battleLevel"]:
            bad.append(f'{b["step"]}단계 값이 앞 단계보다 커지지 않음')
    levels = g["challenge"]["levels"]
    if [x["level"] for x in levels] != list(range(1, len(levels) + 1)):
        bad.append("별의 도전 단계 번호가 1부터 연속이 아님")
    prev = None
    for x in levels:
        if prev:
            for f in ("atk", "hp", "def", "score", "skillStack", "hpDrain", "speed", "immune"):
                if x[f] < prev[f]:
                    bad.append(f'별의 도전 {x["level"]}단계 {f} 가 누적(비감소)이 아님')
        prev = x
    for it in g["sets"]["items"]:
        adds = [t["add"] for t in it["tiers"]]
        if len(adds) != MAX_SET_TIER or adds != sorted(adds):
            bad.append(f'선택 효과 {it["name"]} 단계 값이 3단계 증가가 아님')
    if len(g["score"]["hypotheses"]) < 1 or any(h["id"] not in ("A", "B") for h in g["score"]["hypotheses"]):
        bad.append("점수 가설 id 는 A/B")
    names = {s["step"] for s in steps}
    for it in g["gimmicks"]["items"]:
        if not set(it["steps"]) <= names:
            bad.append(f'기믹 {it["code"]} 의 단계가 없음')
        if grules is not None and it["code"] not in grules:
            bad.append(f'기믹 코드 {it["code"]} 가 gimmick_rules 에 없음')
        if not 1 <= it["severity"] <= 3:
            bad.append(f'기믹 {it["code"]} 심각도 범위 오류')
    return bad


def page_payload(g):
    """화면에 실을 자료(출처 이름은 화면용으로 풀어 둠). 내부 표 이름·코드는 싣지 않는다."""
    keep = {k: g[k] for k in ("asOf", "season", "rules", "steps", "stepsMeta", "exBoss", "challenge", "sets", "score", "community")}
    keep["title"] = content_title(g)
    keep["tab"] = range_label(g)
    keep["bestSet"] = list(best_selection(g)[1])
    keep["baseTotal"] = base_total(g)
    keep["sources"] = {k: {"name": v["name"], "url": v["url"]} for k, v in g["sources"].items() if k != "client"}
    sim = sim_payload(g)
    if sim:
        keep["sim"] = sim
    return keep


SIM_PATH = os.path.join(HERE, "data", "guild_sim.json")


def sim_payload(g, path=SIM_PATH):
    """시뮬 추정 표(tools/build_guild_sim.py 결과)를 화면용으로 줄임. 같은 시즌이 아니면 싣지 않는다(옛 시즌 결과 표시 금지)."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        s = json.load(f)
    if s.get("season") != g["season"]["id"]:
        return None
    return {"runs": s["runs"], "recPower": s["recPower"], "growth": s["growth"], "levels": s["levels"], "passP": s["pass_p"],
            "basis": s["basis"], "summary": s["summary"],
            "teams": [{"names": t["names"], "src": t["src"], "rates": t["rates"]} for t in s["teams"]]}


def sim_best(sim, growth_key):
    """(최고 단계, 팀 번호, 클리어율) 또는 None — guild_view.js simBest 와 같은 규칙"""
    b = (sim or {}).get("summary", {}).get(growth_key)
    return (b["level"], b["team"], b["p"]) if b else None
