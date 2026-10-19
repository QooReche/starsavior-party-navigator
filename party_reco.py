# -*- coding: utf-8 -*-
"""콘텐츠별 추천 파티(초안, 콘솔).
사용: python -X utf8 -I party_reco.py <콘텐츠> [보스] [--owned key1,key2,..] [--break 스킬1,스킬2]
점수 = DB 티어 + 속성 상성 + 주 사용 콘텐츠 여부 + 팀 기능 태그(synergy_tags). 규칙값은 party_contents.json."""
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


_POWK = [1.0]  # 지원 태그 가중 배수(전투력이 부족할 때만 1 초과)
_GIM = [[]]  # 현재 스테이지의 기믹 [(유형코드, 심각도)] (가중x심각도 상위 N)
_GCACHE = {}


_SB = [[]]  # 현재 스테이지의 시즌 보너스 [{"cond":..., "text":...}]
_ELKO = {"sun": "태양", "moon": "달", "star": "별", "order": "질서", "chaos": "혼돈"}


def season_part(s, cfg):
    """코스모 게이트 시즌 보너스: 속성/직업 조건이 맞으면 효과 수치에 비례해 가산."""
    import re
    sb, tot = cfg["seasonBonus"], 0.0
    for b in _SB[0]:
        if b["cond"] not in (_ELKO[s["element"]], s["className"]):
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
    a_w = w["advantage"] if boss else w["advantageMob"]
    d_w = w["disadvantage"] if boss else w["disadvantageMob"]
    g = growth.get(s["key"])
    parts = {"티어": cfg["tierScore"].get(g["tier"], 3) if g else 3}
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
    keys = {x["s"]["key"] for x in combo}
    paired = False
    for pr_ in cfg.get("pairs", []):
        if all(k in keys for k in pr_["keys"]):
            v += pr_["bonus"]
            paired = True
    if roles.count(SUPPORT) > 1 and not paired:  # 시너지 쌍(예: 웨딩 카르멘+아세라)이면 서포터 2명도 허용
        v -= 4
    got = set()
    for x in combo:
        got.update(tags.get(x["s"]["key"], []))
    sus = cfg["power"]["sustainTags"]
    v += sum(wt * (_POWK[0] if t in sus else 1.0) for t, wt in cfg["tagWeights"].items() if t in got)
    v += min(sum(h[0] for h in party_synergy([x["s"]["key"] for x in combo], cfg)), cfg["synergy"]["cap"])
    v += gimmick_team(combo, cfg)[0]
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


def best_party(cands, cfg, tags, def_pen, size=4):
    pool = sorted(cands, key=lambda x: -x["score"])[:14]
    for pr_ in cfg.get("pairs", []):  # 시너지 쌍의 구성원은 점수가 낮아도 후보에 넣는다
        pool += [x for x in cands if x["s"]["key"] in pr_["keys"] and x not in pool]
    # 시너지로 이어진 후보도 풀에 넣는다(개인 점수 상위 14명 밖이어도 연계가 크면 후보, 조합 수 폭증을 막으려 4명까지)
    top = pool[:14]
    extra = []
    for x in cands:
        if x in pool:
            continue
        sy = sum(h[0] for h in party_synergy([x["s"]["key"], *[t["s"]["key"] for t in top]], cfg) if x["s"]["key"] in (h[1]["a"], h[1]["b"]))
        if sy >= 4:
            extra.append((sy, x))
    pool += [x for _, x in sorted(extra, key=lambda e: -e[0])[:4]]
    best, best_v, best_tags = None, -1e9, set()
    for combo in itertools.combinations(pool, size):
        v, got = team_value(combo, cfg, tags, def_pen)
        if v > best_v:
            best, best_v, best_tags = combo, v, got
    return best, best_v, best_tags


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


def templates(cfg, owned, out):
    shown = False
    for name, t in cfg["templates"].items():
        if name.startswith("_"):
            continue
        if owned is not None and not all(any(k in owned for k in n.split("|")) for n in t["need"]):
            continue
        if not shown:
            out("-- 뉴비 편성 유형(arca.live 공략 기준, 보유 시 참고)")
            shown = True
        out(f"  · {name}: {t['desc']}")


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


def recommend(content, boss=None, owned=None, have_break=None, out=print, stage=None, power=None):
    roster, growth, mains, cfg, tags = load()
    c = cfg["contents"][content]
    enemies = c.get("enemies", [])
    note = c.get("note", "")
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
    _POWK[0] = 1.0
    _GIM[0] = []
    _SB[0] = []
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
    templates(cfg, owned, out)
    out("(자동 계산한 참고용. 가중치·브레이크 추천은 추정치)")


if __name__ == "__main__":
    argv = sys.argv[1:]
    opts = {}
    for flag in ("--owned", "--break", "--stage", "--power"):
        if flag in argv:
            i = argv.index(flag)
            opts[flag] = set(argv[i + 1].split(","))
            del argv[i:i + 2]
    recommend(argv[0], argv[1] if len(argv) > 1 else None, opts.get("--owned"), opts.get("--break"),
              stage=next(iter(opts["--stage"]), None) if "--stage" in opts else None,
              power=int(next(iter(opts["--power"]))) if "--power" in opts else None)
