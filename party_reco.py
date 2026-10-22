# -*- coding: utf-8 -*-
"""콘텐츠별 추천 파티(초안, 콘솔).
사용: python -X utf8 -I party_reco.py <콘텐츠> [보스] [--owned key1,key2,..] [--break 스킬1,스킬2]
점수 = 속성 상성 + 주 사용 콘텐츠 여부 + 팀 기능 태그(synergy_tags). 규칙값은 party_contents.json."""
import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RECO = os.path.join(DATA, "savior_reco.json")
TIER = os.path.join(DATA, "db_tier.json")
TAGS = os.path.join(DATA, "synergy_tags.json")
SYN = os.path.join(DATA, "synergy_pairs.json")
POW = os.path.join(DATA, "power_penalty.json")
GRULES = os.path.join(DATA, "gimmick_rules.json")
GSTAGE = os.path.join(DATA, "stage_gimmicks.json")
DMG = os.path.join(DATA, "damage_index.json")
OVR = os.path.join(DATA, "synergy_overrides.json")
CONT = os.path.join(HERE, "party_contents.json")
FOE = os.path.join(DATA, "foe_stages.json")
FOE_KEYS = {"작전": "op", "작전어려움": "oph", "일일": "daily", "장비": "equip", "큐브": "cube",
            "플래시 포인트": "rush", "회랑": "clo", "코스모 게이트": "cosmo"}
EL = {"sun": "태양", "moon": "달", "star": "별", "order": "질서", "chaos": "혼돈"}
SUPPORT, DEFENDER = "서포터", "디펜더"
FRONT_ROLES = (DEFENDER, SUPPORT)


def _json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load():
    roster = _json(RECO)["saviors"]
    t = _json(TIER)
    tags = {a["key"]: a["tags"] for a in _json(TAGS)["saviors"] if "@" not in a["key"]}
    return roster, t["growth"], t["mainContents"], _json(CONT), tags


_DI = {}
_DM = [0.5, 0.35]  # [광역 비중 wa, 화력 항 가중]


def dmg_units():
    if not _DI:
        _DI.update(_json(DMG))
    return _DI["units"]


def team_damage(keys, wa):
    """팀 10턴 기대 피해(근사): sum(개인 dpt x (1 + 다른 멤버가 주는 피해 증가 %)). 협공 같은 세부 시너지는 놓친다."""
    u = dmg_units()
    tot = 0.0
    for i, k in enumerate(keys):
        e = u.get(k)
        if not e:
            continue
        dpt = e["s"] * (1 - wa) + e["a"] * wa
        mult = 1 + sum(u.get(keys[j], {}).get("g", 0) for j in range(len(keys)) if j != i) / 100
        tot += dpt * mult
    return tot * _DI["turns"]


def dmg_score(keys, wa):
    return min(10.0, 10 * team_damage(keys, wa) / _DI["ref95"])


_MM = [None]  # 상성 방식: None(균형) 또는 "avoid"(역상성 회피 우선)
_GIM = [[]]  # 현재 스테이지의 기믹 [(유형코드, 심각도)] (가중x심각도 상위 N)
_GCACHE = {}


_SB = [[]]  # 현재 스테이지의 시즌 보너스 [{"cond":..., "text":...}]


def season_part(s, cfg):
    """코스모 게이트 시즌 보너스: 속성/직업 조건이 맞으면 효과 수치에 비례해 가산."""
    import re
    sb, tot = cfg["seasonBonus"], 0.0
    for b in _SB[0]:
        if b["cond"] not in (EL[s["element"]], s["className"]):
            continue
        m = re.search(r"(\d+(?:\.\d+)?)%", b["text"])
        if not m:
            continue
        k = next((w for kw, w in sb["kinds"] if kw in b["text"]), 0.02)
        tot += float(m.group(1)) * k
    return min(tot, sb["cap"])


def gimmick_rules():
    if not _GCACHE:
        _GCACHE["r"] = _json(GRULES)
        _GCACHE["s"] = _json(GSTAGE)
    return _GCACHE["r"], _GCACHE["s"]


def stage_gimmicks(gkey, cfg):
    """스테이지 키('op|탭|스테이지') -> [(코드, 심각도)] 중요도(가중 x 심각도) 상위 N."""
    rules, stages = gimmick_rules()
    items = [(c, sev) for c, sev in stages.get(gkey, {}).items() if c in rules["types"]]
    items.sort(key=lambda it: -rules["types"][it[0]]["w"] * it[1])
    return items[:cfg["gimmick"]["topTypes"]]


def gimmick_part(key, cfg):
    """한 구원자의 기믹 대응 점수(선호 태그 +, 기피 태그 -)."""
    if not _GIM[0]:
        return 0.0
    rules, _ = gimmick_rules()
    tags = set(rules["tags"].get(key, []))
    g, tot = cfg["gimmick"], 0.0
    for code, sev in _GIM[0]:
        t = rules["types"][code]
        w = t["w"] * sev / 2
        pre, avo = len(tags & set(t["prefer"])), len(tags & set(t["avoid"]))
        tot += w * (min(pre, 2) * 0.6 if pre else 0) - w * (min(avo, 2) * 0.6 if avo else 0)
    return max(-g["cap"], min(g["cap"], tot)) * g["weight"]


def gimmick_team(combo, cfg):
    """필요 슬롯을 파티가 채우면 보너스. (점수, [(유형이름, 슬롯이름, 충족한 구원자 이름 또는 None)])"""
    if not _GIM[0]:
        return 0.0, []
    rules, _ = gimmick_rules()
    g, bonus, rep = cfg["gimmick"], 0.0, []
    for code, sev in _GIM[0]:
        t = rules["types"][code]
        w = t["w"] * sev / 2
        for sl in t["slots"]:
            who = next((x["s"]["name"] for x in combo if set(rules["tags"].get(x["s"]["key"], [])) & set(sl["tags_any"])), None)
            if who:
                bonus += g["slotBonus"] * w * 0.5
            rep.append((t["name"], sl["name"], who))
    return min(bonus, g["teamCap"]) * g["weight"], rep


def power_penalty(my, rec):
    """(전투력 비율%, 아군 피해 배율, 적 피해 배율, 경고 등급 이름) 또는 None. 표는 databook 의 것."""
    if not (my and rec):
        return None
    t = _json(POW)
    ratio = my * 10000 // rec
    row = next((r for r in t["pen"] if r[0] <= ratio < r[1]), None)
    a, b = (row[2] / 10000, row[3] / 10000) if row else (1.0, 1.0)
    deficit = 10000 - ratio
    tier = None
    if my < rec:
        tier = next((x for x in t["tribe"] if x[0] <= deficit < x[1]), t["tribe"][-1] if deficit >= t["tribe"][-1][1] else None)
    return ratio / 100, a, b, (tier[2] if tier else None)


def load_synergy():
    """자동 추출 쌍 + 수동 보정(ignore/set/add) 을 합쳐 반환. 개화 변형(@) 키는 제외."""
    pairs = [dict(p) for p in _json(SYN) if "@" not in p["a"] and "@" not in p["b"]]
    ov = _json(OVR) if os.path.exists(OVR) else {}
    ign = {frozenset((o["a"], o["b"])) for o in ov.get("ignore", [])}
    pairs = [p for p in pairs if frozenset((p["a"], p["b"])) not in ign]
    for o in ov.get("set", []):
        for p in pairs:
            if frozenset((p["a"], p["b"])) == frozenset((o["a"], o["b"])):
                p.update({k: v for k, v in o.items() if k in ("strength", "conf", "reason")})
    for o in ov.get("add", []):
        pairs.append({"a": o["a"], "b": o["b"], "type": o.get("type", "3:생존연계"), "strength": o.get("strength", 2),
                      "directed": o.get("directed", False), "reason": o.get("reason", ""),
                      "evidence": o.get("evidence", []), "conf": o.get("conf", "사용자")})
    return pairs


_SYN_IDX = {}


def synergy_index():
    if not _SYN_IDX:
        for p in load_synergy():
            _SYN_IDX.setdefault(frozenset((p["a"], p["b"])), []).append(p)
    return _SYN_IDX


def party_synergy(keys, cfg):
    """파티(키 목록) 안의 시너지 쌍 목록 [(점수, 쌍)] 점수 내림차순."""
    sw = cfg["synergy"]
    idx, hits = synergy_index(), []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            for p in idx.get(frozenset((keys[i], keys[j])), []):
                pts = sw["typeWeight"][p["type"].split(":")[0]] * p["strength"] * sw["confWeight"].get(p.get("conf"), 0.6)
                hits.append((pts, p))
    return sorted(hits, key=lambda h: -h[0])


def score(s, growth, mains, cfg, main_name, enemies, boss=True):
    w = cfg["weights"]
    mw = cfg["matchupModes"]["avoid"] if _MM[0] == "avoid" else w
    a_w = mw["advantage"] if boss else mw["advantageMob"]
    d_w = mw["disadvantage"] if boss else mw["disadvantageMob"]
    parts = {}
    sp = season_part(s, cfg) if _SB[0] else 0.0
    if sp:
        parts["시즌 보너스"] = sp
    gp = gimmick_part(s["key"], cfg)
    if gp:
        parts["기믹 대응"] = gp
    if main_name and main_name not in mains.get(s["key"], ["미정"]):
        parts["주사용 아님"] = -w["notMainContent"]
    adv = cfg["advantage"]
    el = s["element"]
    if enemies:
        win = sum(1 for e in enemies if adv.get(el) == e)
        # 질서↔혼돈은 서로 유리(나무위키 표기)라 불리로 세지 않는다
        lose = sum(1 for e in enemies if adv.get(e) == el and adv.get(el) != e)
        if win:
            parts["상성 유리"] = a_w * win / len(enemies)
        if lose:
            parts["상성 불리"] = -d_w * lose / len(enemies)
    return sum(parts.values()), parts


def team_value(combo, cfg, tags, def_pen):
    w = cfg["weights"]
    v = sum(x["score"] for x in combo)
    roles = [x["s"]["className"] for x in combo]
    if SUPPORT in roles:
        v += w["supportBonus"]
    v -= def_pen * max(0, roles.count(DEFENDER) - 1)  # 2번째 디펜더부터 감점
    if roles.count(SUPPORT) > 1:
        v -= 4
    got = set()
    for x in combo:
        got.update(tags.get(x["s"]["key"], []))
    v += sum(wt for t, wt in cfg["tagWeights"].items() if t in got)
    v += min(sum(h[0] for h in party_synergy([x["s"]["key"] for x in combo], cfg)), cfg["synergy"]["cap"])
    v += gimmick_team(combo, cfg)[0]
    v += _DM[1] * dmg_score([x["s"]["key"] for x in combo], _DM[0])
    return v, got


LEAD_OPEN_TAGS = ("힐", "보호막", "속도증가", "적방어력감소", "아군공격력증가")  # 첫 턴에 먼저 나가면 이득인 효과


def leader_pick(party, cfg, tags):
    """리더(속도 +10) 추천: 팀 동료에게 제공하는 연계(유형 1~4) 점수가 가장 큰 구성원. (구성원, 점수, 이유 목록) 또는 None."""
    keys = [x["s"]["key"] for x in party]
    gain = {k: 0.0 for k in keys}
    why = {k: [] for k in keys}
    for pts, p in party_synergy(keys, cfg):
        if int(p["type"].split(":")[0]) > 4:
            continue
        givers = [p["a"]] if p.get("directed") else [p["a"], p["b"]]
        for g in givers:
            gain[g] += pts / len(givers)
            why[g].append(p["reason"])
    for x in party:  # 동률이면 첫 턴 지원 효과(힐·보호막 등)가 있는 쪽
        gain[x["s"]["key"]] += 0.3 * sum(1 for t in tags.get(x["s"]["key"], []) if t in LEAD_OPEN_TAGS)
    k = max(keys, key=lambda k: gain[k])
    if gain[k] <= 0:
        return None
    return next(x for x in party if x["s"]["key"] == k), gain[k], why[k][:2]


POOL_N = 24


def party_pool(cands, cfg, tags):
    """조합을 만들 후보 풀(최대 POOL_N명). 티어 같은 개인 서열로 거르지 않고 역할별 상위(단일·광역 화력, 아군 피해 증가, 개인 점수)를
    고르고, 연계가 강한 쌍은 둘 다 넣는다. 웹 JS(party_template.html 의 partyPool)와 같은 규칙 — 한쪽을 고치면 다른 쪽도 고칠 것."""
    by_score = sorted(cands, key=lambda x: -x["score"])
    if len(cands) <= POOL_N:
        return by_score
    du = dmg_units()
    pool = []

    def add(x):
        if len(pool) < POOL_N and x not in pool:
            pool.append(x)

    def top(f, n):
        for x in sorted(cands, key=lambda x: -f(du.get(x["s"]["key"], {})))[:n]:
            add(x)

    top(lambda e: e.get("s", 0), 6)
    top(lambda e: e.get("a", 0), 4)
    top(lambda e: e.get("g", 0) or 0, 3)
    for x in by_score[:4]:
        add(x)
    pr = []
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            pts = sum(h[0] for h in party_synergy([cands[i]["s"]["key"], cands[j]["s"]["key"]], cfg))
            if pts >= 4:
                pr.append((pts, i, j))
    pr.sort(key=lambda e: (-e[0], e[1], e[2]))
    for _, i, j in pr:
        if len(pool) > POOL_N - 2:
            break
        add(cands[i])
        add(cands[j])
    for x in by_score:
        add(x)
    return sorted(pool, key=lambda x: -x["score"])


def top_parties(cands, cfg, tags, def_pen, k=10, size=4):
    """근사 점수 상위 k 팀 [(combo, 점수, 팀 태그)]. 같은 점수면 조합을 만든 순서(앞선 것 먼저).
    웹 JS(party_template.html 의 topParties)와 같은 규칙 — 한쪽을 고치면 다른 쪽도 고칠 것."""
    pool = party_pool(cands, cfg, tags)
    scored = []
    for i, combo in enumerate(itertools.combinations(pool, size)):
        v, got = team_value(combo, cfg, tags, def_pen)
        scored.append((-v, i, combo, got))
    scored.sort(key=lambda e: (e[0], e[1]))
    return [(c, -nv, got) for nv, _, c, got in scored[:k]]


def best_party(cands, cfg, tags, def_pen, size=4):
    top = top_parties(cands, cfg, tags, def_pen, 1, size)
    if not top:
        return None, -1e9, set()
    return top[0]


def place(party):
    """전열 2/후열 2: 디펜더·서포터를 앞에, 나머지는 뒤(게임 공략 정석: 딜러/디펜더/서포터/딜러)."""
    order = sorted(party, key=lambda x: (x["s"]["className"] not in FRONT_ROLES, -x["score"]))
    return order[:2], order[2:]


def alts(member, party, cands, cfg, tags, def_pen, used):
    """member 가 없을 때 나머지 3명을 두고 대신 들어갈 후보: 팀 점수가 높은 순 2명(직업 무관)."""
    rest = [y for y in party if y is not member]
    pool = [x for x in cands if x["s"]["key"] not in used]
    return sorted(pool, key=lambda x: -team_value(rest + [x], cfg, tags, def_pen)[0])[:2]


def pick_break(party, cfg, content, boss_note, have=None):
    bs = cfg["breakSkills"]
    roles = [x["s"]["className"] for x in party]
    best = None
    for name, b in bs.items():
        if name.startswith("_") or (have and name not in have) or (b.get("unreleased") and not have):
            continue
        n = sum(roles.count(r) for r in b["bonusRoles"])
        if name == "차원 강습" and content == "코스모 게이트":
            n += 1  # 강인도 피해 +1: 브레이크가 핵심인 코스모 게이트 가산(추정)
        if best is None or n > best[0]:
            best = (n, name, b["text"])
    return best


def fmt(x):
    s = x["s"]
    t = x["g"]["tier"] if x["g"] else "?"
    why = ", ".join(f"{k}{v:+.0f}" for k, v in x["parts"].items() if k != "티어")
    return f'{s["name"]}({s["subtitle"]}) {EL[s["element"]]}/{s["className"]} {t}' + (f" [{why}]" if why else "")


def find_stages(content, query):
    """foe_stages.json 에서 이름(탭 포함)에 query 가 들어 있는 스테이지를 찾는다(최대 5개 반환)."""
    key = FOE_KEYS.get(content)
    hits = []
    for c in _json(FOE)["contents"]:
        if c["key"] != key:
            continue
        for tab in c["tabs"]:
            for st in tab["stages"]:
                if query in st["name"] or query in f'{tab["tab"]} {st["name"]}':
                    hits.append((tab["tab"], st))
    return hits


def stage_enemies(st):
    """적 속성 리스트: 개수 가중, 보스는 2배(점수에 상성 비중으로 쓰임)."""
    out = []
    for e in st["enemies"]:
        out += [e["element"]] * (e["count"] * (2 if e["boss"] else 1))
    return out


def set_stage(foe_key, tab, st, boss, cfg):
    """웹 JS run() 과 같은 스테이지 문맥(기믹·시즌 보너스·화력 가중, 전투력 보정 없음)을 전역에 잡는다.
    foe_key = foe_stages.json 콘텐츠 키(op·cosmo 등), boss = 보스 콘텐츠(코스모·플래시) 여부."""
    _MM[0] = None
    _GIM[0] = stage_gimmicks(f"{foe_key}|{tab}|{st['name']}", cfg)
    _SB[0] = (st.get("season_bonus_latest") or {}).get("bonuses", [])
    _DM[0] = min(1.0, (st["enemy_total"] - 1) / 2)
    _DM[1] = cfg["damage"]["weightBoss"] if boss else cfg["damage"]["weightMob"]


def recommend(content, boss=None, owned=None, have_break=None, out=print, stage=None, power=None):
    roster, growth, mains, cfg, tags = load()
    c = cfg["contents"][content]
    enemies = c.get("enemies", [])
    note = c.get("note", "")
    if boss and boss not in c.get("bosses", {}):
        # 보스 표가 없는 콘텐츠(플래시 포인트 등)는 보스 이름을 스테이지 검색어로 쓴다(이전: KeyError 'bosses')
        if not stage:
            stage = boss
        boss = None
    if boss:
        b = c["bosses"][boss]
        enemies, note = b["enemies"], f'{boss}: {EL[b["enemies"][0]]} {b["role"]} {b["atk"]} {b.get("note", "")}'
    rest = None  # 속성 제한 콘텐츠(예: 태양 회랑은 태양 속성만)
    if stage:
        hits = find_stages(content, stage)
        if not hits:
            out(f"스테이지 '{stage}' 없음 (콘텐츠 {content})")
            return
        tab, st = hits[0]
        rest = c.get("restrictTabs", {}).get(tab)
        if rest:
            out(f"※ {tab}: {EL[rest]} 속성 구원자만 편성 가능")
        enemies = stage_enemies(st)
        note = (f'{tab} {st["name"]} Lv{st["level"]} 적 {st["enemy_total"]}체 / 지배 속성 '
                f'{EL.get(st["dominant_element"], "?")} / 광역 {st["aoe_ratio"]:.0%} / 디펜더 {st["defender_ratio"]:.0%}'
                f' (일치 {len(hits)}건 중 첫 번째)')
    def_pen = c.get("defenderPenalty", cfg["weights"]["defenderPenalty"])
    _GIM[0] = []
    _SB[0] = []
    _DM[0] = min(1.0, (st["enemy_total"] - 1) / 2) if stage else 0.5
    _DM[1] = cfg["damage"]["weightBoss"] if (c.get("boss", False) or bool(boss)) else cfg["damage"]["weightMob"]
    if stage:
        _SB[0] = (st.get("season_bonus_latest") or {}).get("bonuses", [])
        if _SB[0]:
            sbk = st["season_bonus_latest"]
            out("시즌 보너스(" + str(sbk.get("season", "")) + "): " + " / ".join(f"{b['cond']} {b['text']}" for b in _SB[0]))
    if stage:
        _GIM[0] = stage_gimmicks(f"{FOE_KEYS[content]}|{tab}|{st['name']}", cfg)
        if _GIM[0]:
            rl, _ = gimmick_rules()
            out("스테이지 기믹: " + ", ".join(f"{rl['types'][c]['name']}(심각도{sv})" for c, sv in _GIM[0]))
    if stage and power:
        rec = st.get("recommended_power")
        pp = power_penalty(power, rec)
        if pp:
            ratio, a, b, warn = pp
            out(f"전투력 {power:,} / 권장 {rec:,} = {ratio:.1f}% -> " + (f"아군 피해 x{a:.3f}, 적 피해 x{b:.3f}" + (f" [{warn}]" if warn else "") if a < 1 else "보정 없음 (90% 이상)"))
            if a < 1:
                out("  (참고용: 추천 편성은 전투력을 반영하지 않습니다. 편성을 바꾸면 전투력도 달라지므로)")
    out(f"== {content} {boss or ''} (적 속성: {'/'.join(sorted({EL[e] for e in enemies})) or '미지정'}) {note}")
    used = set()
    for p in range(1, c.get("parties", 1) + 1):
        cands = []
        for s in roster:
            if s["key"] in used or (owned is not None and s["key"] not in owned) or (rest and s["element"] != rest):
                continue
            v, parts = score(s, growth, mains, cfg, c["main"], enemies, c.get("boss", False) or bool(boss))
            cands.append({"s": s, "g": growth.get(s["key"]), "score": v, "parts": parts})
        if len(cands) < 4:
            out(f"-- 파티 {p}: 후보가 4명 미만")
            break
        party, v, got = best_party(cands, cfg, tags, def_pen)
        out(f"-- 파티 {p} (점수 {v:.1f}) 팀 기능: {', '.join(sorted(got)) or '-'}")
        used |= {x["s"]["key"] for x in party}
        front, back = place(party)
        out(f"  [화력 지표] {dmg_score([x['s']['key'] for x in party], _DM[0]):.1f}/10 (10턴 기대 피해 근사, 장비 제외 상대 비교용)")
        ld = leader_pick(party, cfg, tags)
        if ld:
            out(f"  [리더 추천] {ld[0]['s']['name']}({ld[0]['s']['subtitle']}) - 속도 +10 으로 먼저 행동해 팀에 줄 효과가 가장 많음(추정, 점수 {ld[1]:.1f})")
        for label, grp in (("전열", front), ("후열", back)):
            for x in grp:
                out(f"  [{label}] " + fmt(x))
                a = alts(x, party, cands, cfg, tags, def_pen, used)
                if a:
                    out("        대체: " + " > ".join(y["s"]["name"] for y in a))
        if _GIM[0]:
            for tn, sn, who in gimmick_team(party, cfg)[1]:
                out(f"  [기믹 슬롯] {tn} / {sn}: " + (who if who else "비어 있음"))
        bk = pick_break(party, cfg, content, note, have_break)
        if bk:
            out(f"  [브레이크 스킬] {bk[1]} - {bk[2]} (직업 구성 기준 추정)")
    out("(자동 계산한 참고용. 가중치·브레이크 추천은 추정치)")


if __name__ == "__main__":
    argv = sys.argv[1:]
    opts = {}
    if "--avoid-reverse" in argv:
        _MM[0] = "avoid"
        argv.remove("--avoid-reverse")
    for flag in ("--owned", "--break", "--stage", "--power"):
        if flag in argv:
            i = argv.index(flag)
            opts[flag] = set(argv[i + 1].split(","))
            del argv[i:i + 2]
    recommend(argv[0], argv[1] if len(argv) > 1 else None, opts.get("--owned"), opts.get("--break"),
              stage=next(iter(opts["--stage"]), None) if "--stage" in opts else None,
              power=int(next(iter(opts["--power"]))) if "--power" in opts else None)
