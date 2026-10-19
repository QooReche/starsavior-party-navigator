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
    v += sum(wt for t, wt in cfg["tagWeights"].items() if t in got)
    v += min(sum(h[0] for h in party_synergy([x["s"]["key"] for x in combo], cfg)), cfg["synergy"]["cap"])
    return v, got


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


def recommend(content, boss=None, owned=None, have_break=None, out=print, stage=None):
    roster, growth, mains, cfg, tags = load()
    c = cfg["contents"][content]
    enemies = c.get("enemies", [])
    note = c.get("note", "")
    if boss:
        b = c["bosses"][boss]
        enemies, note = b["enemies"], f'{boss}: {EL[b["enemies"][0]]} {b["role"]} {b["atk"]} {b.get("note", "")}'
    if stage:
        hits = find_stages(content, stage)
        if not hits:
            out(f"스테이지 '{stage}' 없음 (콘텐츠 {content})")
            return
        tab, st = hits[0]
        enemies = stage_enemies(st)
        note = (f'{tab} {st["name"]} Lv{st["level"]} 적 {st["enemy_total"]}체 / 지배 속성 '
                f'{EL.get(st["dominant_element"], "?")} / 광역 {st["aoe_ratio"]:.0%} / 디펜더 {st["defender_ratio"]:.0%}'
                f' (일치 {len(hits)}건 중 첫 번째)')
    def_pen = c.get("defenderPenalty", cfg["weights"]["defenderPenalty"])
    out(f"== {content} {boss or ''} (적 속성: {'/'.join(sorted({EL[e] for e in enemies})) or '미지정'}) {note}")
    used = set()
    for p in range(1, c.get("parties", 1) + 1):
        cands = []
        for s in roster:
            if s["key"] in used or (owned is not None and s["key"] not in owned):
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
        for label, grp in (("전열", front), ("후열", back)):
            for x in grp:
                out(f"  [{label}] " + fmt(x))
                a = alts(x, party, cands, cfg, tags, def_pen, used)
                if a:
                    out("        대체: " + " > ".join(y["s"]["name"] for y in a))
        bk = pick_break(party, cfg, content, note, have_break)
        if bk:
            out(f"  [브레이크 스킬] {bk[1]} - {bk[2]} (직업 구성 기준 추정)")
    templates(cfg, owned, out)
    out("(자동 계산한 참고용. 가중치·브레이크 추천은 추정치)")


if __name__ == "__main__":
    argv = sys.argv[1:]
    opts = {}
    for flag in ("--owned", "--break", "--stage"):
        if flag in argv:
            i = argv.index(flag)
            opts[flag] = set(argv[i + 1].split(","))
            del argv[i:i + 2]
    recommend(argv[0], argv[1] if len(argv) > 1 else None, opts.get("--owned"), opts.get("--break"),
              stage=next(iter(opts["--stage"]), None) if "--stage" in opts else None)
