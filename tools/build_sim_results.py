# -*- coding: utf-8 -*-
"""P4: 추천 후보 팀을 확률 전투 엔진(battlesim.simulate)으로 미리 돌려 웹 페이지가 읽을 data/sim/*.json 을 만든다.
느리다(대표 스테이지 전체: 프로세스 2개·낮은 우선순위로 약 65분, 1개면 약 2시간). tools/update.py 는 --sim 을 줄 때만 이 단계를 부른다.

사용:
  python -X utf8 -I tools/build_sim_results.py                      # 대표 스테이지 전부(설계 battlesim_design.md 「P4 상세」)
  python -X utf8 -I tools/build_sim_results.py --contents cosmo,rush  # 일부 콘텐츠만(그 콘텐츠 파일만 다시 씀)
  python -X utf8 -I tools/build_sim_results.py --stage "cosmo/길레/길레 2단계" --out E:/tmp/sim   # 한 스테이지(시험용)
  옵션: --workers N(기본 1, 최대 2 권장) --seed S(기본 20261020) --quick(판 수를 크게 줄인 시험용) --stages all(전 스테이지, 결과 수십 MB)

처리(스테이지마다, 파티마다):
  1) 웹과 같은 근사 점수로 상위 10팀(party_reco.top_parties = 웹 topParties) + 보존 후보 최대 3팀(힐·보호막 서포터 포함 최고,
     디펜더 포함 최고, 근사 11~40위 중 시드 고정 무작위 1팀).
  2) 오토 선별 32판 -> 관문 순위(클리어 확률 5%p 단위 묶음 -> 처치 턴 -> 근사 점수) -> 1위와 클리어 확률 95% 범위가 겹치는 팀(최소 3, 최대 5)을
     별도 시드 200판으로 다시 돌려 확정. 1·2위 차이가 표본 오차 안이면 close=true(우열 불확실).
  3) 수동: 정책 4종(대상 보스 우선/HP 최저 x 노바 버스트 다음 공격/궁극기만)을 16판씩(별도 시드) 굴려 최고 정책을 고르고,
     그 정책을 또 다른 시드로 평가(오토와 같은 판 수). 상위 3팀은 대표 1판(처치 턴이 중앙값에 가장 가까운 클리어 판)의 서순을 저장.
  4) 민감도: 확정 후보(최대 5팀)를 가정 6종으로 64판(같은 시드로 기준도 64판) -> 1위가 바뀌는 가정 = depends_on.
결과에는 근사 점수·편성 순서·리더·판 수·시드·데이터/규칙 버전이 함께 들어간다. 결과가 없으면 웹은 숫자를 지어내지 않고 「시뮬 없음」을 보인다."""
import argparse
import hashlib
import json
import math
import multiprocessing as mp
import os
import random
import sys
import time
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import party_reco as pr  # noqa: E402
from build_party_html import CONTENT_META  # noqa: E402

SCHEMA = "p4-2"   # p4-2: 실행 정보(meta)를 스테이지마다 둔다
DATA_PATCH = "2.50 (2026-10-15 패치)"   # 데이터를 다시 받으면(tools/fetch_sources.py) 이 라벨도 고칠 것
CONDITIONS = "Lv200 · 공명 10 · 각인 0 · 장비·잠재력·여정 없음 · 브레이크 미구현"
DEFAULT_SEED = 20261020
RUNS = dict(screen=32, final=200, msearch=16, meval_screen=32, meval_final=200, sens=64)
QUICK_RUNS = dict(screen=8, final=16, msearch=4, meval_screen=8, meval_final=16, sens=8)
K_TOP = 10
MIN_FINAL, MAX_FINAL = 3, 5
SEQ_TEAMS = 3
SEQ_TURNS = 12
CLEAR_BIN = 20          # 클리어 확률 묶음 = 1/20 = 5%p(실용 허용차)
CLOSE_TTK = 0.5         # 1·2위 처치 턴 차가 이보다 작고 클리어 확률 범위가 겹치면 「우열 불확실」
POLICIES = [("boss_first", "any_attack"), ("boss_first", "ult_only"), ("lowest_hp", "any_attack"), ("lowest_hp", "ult_only")]
SENS = [
    ("enemy_x185_off", "적 공격 ×1.85 없음", {"rules_override": {"enemy_same_formula": False}}),
    ("start_cd_0", "전투 시작 쿨타임 0", {"rules_override": {"init_cd_frac": 0.0, "enemy_init_cd": 0.0}}),
    ("x185_off_cd_0", "×1.85 없음 + 시작 쿨타임 0", {"rules_override": {"enemy_same_formula": False, "init_cd_frac": 0.0, "enemy_init_cd": 0.0}}),
    ("def_x1", "디펜더 가중 ×1", {"rules_override": {"target_defender_mult": 1.0}}),
    ("def_x4", "디펜더 가중 ×4", {"rules_override": {"target_defender_mult": 4.0}}),
    ("coop_cap_100", "협공 확률 상한 100%", {"formula_override": {"COOP_CAP": 1.0}}),
]
NOVA_SENS = ("nova_unit", "노바 포스 개인 풀(수동)", {"nova_pool": "unit"})
SEEDS = dict(screen=0, final=1, msearch=2, meval=3, sens=4)
ROLE_SUPPORT, ROLE_DEF = "서포터", "디펜더"
SUSTAIN_TAGS = ("힐", "보호막")


# ------------------------------------------------------------------ 순위(웹 party_template.html 의 gateKey 와 같은 규칙)
def gate_key(r, approx):
    """관문 순위 키(작을수록 앞): 계산 가능 -> 클리어 확률 5%p 묶음(높을수록) -> 처치 턴 중앙값(빠를수록) -> 근사 점수(높을수록).
    전멸 확률은 가중합에 넣지 않는다(클리어 확률에 이미 들어 있음)."""
    if not r or not r.get("g"):
        return (1, 0, 1e9, -approx)
    b = int(math.floor(r["c"] * CLEAR_BIN + 1e-9))
    return (0, -b, r["t"] if r.get("t") is not None else 1e9, -approx)


def rank_keys(teams, keys, mode="auto"):
    return sorted(keys, key=lambda k: (gate_key(teams[k].get(mode), teams[k]["a"]), k))


def is_close(r1, r2):
    """1·2위 차이가 표본 오차 안인가: 클리어 확률 95% 범위가 겹치고, 처치 턴 차가 CLOSE_TTK 미만(한쪽이 없으면 클리어 범위만)"""
    if not (r1 and r2 and r1.get("g") and r2.get("g")):
        return False
    (a_lo, a_hi), (b_lo, b_hi) = r1["ci"], r2["ci"]
    if a_lo > b_hi or b_lo > a_hi:
        return False
    if r1.get("t") is None or r2.get("t") is None:
        return True
    return abs(r1["t"] - r2["t"]) < CLOSE_TTK


# ------------------------------------------------------------------ 후보(웹 run() 과 같은 근사 점수)
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


def arrange(combo):
    """웹과 같은 배치·리더: 화면 순서 [후열1, 전열1, 전열2, 후열2], 시뮬 칸 [전열1, 전열2, 후열1, 후열2]"""
    b = base()
    front, back = pr.place(list(combo))
    ld = pr.leader_pick(list(combo), b["cfg"], b["tags"])
    lead = ld[0]["s"]["key"] if ld else None
    sim = [front[0], front[1], back[0], back[1]]
    keys = [x["s"]["key"] for x in sim]
    return dict(o=[back[0]["s"]["key"], front[0]["s"]["key"], front[1]["s"]["key"], back[1]["s"]["key"]], L=lead,
                sim=keys, li=keys.index(lead) if lead else None)


def keepers(cands, ranked40, def_pen, stage_label):
    """근사 선별이 버린 역할 후보(설계 4절): 힐/보호막 서포터 포함 최고팀, 디펜더 포함 최고팀(개인 상위 14 밖에서도), 11~40위 무작위 1팀"""
    import itertools
    b = base()
    cfg, tags = b["cfg"], b["tags"]
    have = {ckey(c) for c, _, _ in ranked40[:K_TOP]}
    by = sorted(cands, key=lambda x: -x["score"])
    top14 = by[:14]
    out = []
    preds = (("sustain", lambda x: x["s"]["className"] == ROLE_SUPPORT and set(tags.get(x["s"]["key"], [])) & set(SUSTAIN_TAGS)),
             ("defender", lambda x: x["s"]["className"] == ROLE_DEF))
    for kind, pred in preds:
        need = [x for x in by if pred(x)][:3]
        if not need:
            continue
        pool = top14 + [x for x in need if x not in top14]
        best, bv = None, -1e18
        for combo in itertools.combinations(pool, 4):
            if not any(pred(x) for x in combo):
                continue
            v, _ = pr.team_value(combo, cfg, tags, def_pen)
            if v > bv:
                best, bv = combo, v
        if best is not None and ckey(best) not in have:
            have.add(ckey(best))
            out.append((best, bv, kind))
    tail = [(c, v) for c, v, _ in ranked40[K_TOP:] if ckey(c) not in have]
    if tail:
        rng = random.Random(zlib.crc32(stage_label.encode("utf-8")))
        c, v = rng.choice(tail)
        out.append((c, v, "random"))
    return out


# ------------------------------------------------------------------ 시뮬
def run_sim(stage_str, team, runs, seed, policy=None, extra=None, **kw):
    from battlesim.api import simulate, EventLimitError
    over = {}
    opts = dict(seed=seed, n_runs=runs)
    if policy:
        over.update(nova_policy="manual", ally_auto_target=policy[0], manual_burst=policy[1])
    for k, v in (extra or {}).items():
        if k == "rules_override":
            over.update(v)
        elif k == "formula_override":
            opts["formula_override"] = v
        else:
            over[k] = v
    opts["rules_override"] = over
    opts.update(kw)
    try:
        return simulate({"units": team["sim"], "leader": team["li"]}, {"stage": stage_str}, opts), None
    except EventLimitError as e:
        return None, "이벤트 한도 초과: %s" % e
    except Exception as e:   # 결과를 지어내지 않는다 — 오류는 그대로 기록
        return None, "%s: %s" % (type(e).__name__, str(e)[:120])


def summarize(res, team, err=None):
    if res is None:
        return dict(g=False, us=[err or "계산 실패"], n=0)
    o = res["outcome"]
    names = list(res["per_unit"])
    pu = [res["per_unit"][n] for n in names]
    u = {team["sim"][i]: [round(p["dmg_share"], 3), round(p["death_p"], 3)] for i, p in enumerate(pu)}
    fdi = max(range(len(pu)), key=lambda i: (pu[i]["first_death_p"], -i))
    fd = None
    if pu[fdi]["first_death_p"] > 0:
        fd = dict(k=team["sim"][fdi], p=round(pu[fdi]["first_death_p"], 3), t=pu[fdi]["death_turn_median"])
    crit = res["unsupported"]["critical"]
    us = []
    for x in crit:
        s = "%s 「%s」" % (x["unit"], (x.get("raw") or x.get("reason") or "")[:40])
        if s not in us:
            us.append(s)
    r = dict(c=o["clear_p"], ci=o["ci95"]["clear"], w=o["wipe_p"], to=o["timeout_p"], t=o["ttk_median"], tr=o["ttk_p10_p90"],
             n=o["n_runs"], nc=o["n_clear"], fd=fd, nd=round(max(0.0, 1 - sum(p["first_death_p"] for p in pu)), 3), u=u,
             g=bool(res["unsupported"]["gate_ok"]))
    if us:
        r["us"] = us[:3]
    return r


def seq_from_timeline(tl, team, max_turns=SEQ_TURNS):
    """타임라인 -> 서순 행: 「모델 기준 턴」(100틱) 하나 = 한 행, 칸 = 화면 카드 순서(4칸), 칸마다 행동 목록"""
    col = {k: team["o"].index(k) for k in team["sim"]}
    rows = {}
    last = 0
    for e in tl:
        if e.get("side") != 0 or "pos" not in e:
            continue
        turn = max(1, int(math.ceil(e["turn"] - 1e-9)))
        last = max(last, turn)
        if turn > max_turns:
            continue
        sl = e["skill"]
        k = "U" if sl.startswith("궁극기") else "S" if sl.startswith("특수기") else "B"
        if e.get("all"):
            tg = "전체"
        elif e.get("tgt_side") == 1:
            tg = "보스" if e.get("tgt_boss") else (e["targets"][0] if e.get("targets") else "")
        elif e.get("tgt_side") == 0:
            tg = "아군 " + e["targets"][0] if e.get("targets") else ""
        else:
            tg = ""
        a = {"k": k, "tg": tg}
        if e.get("via"):
            a["v"] = e["via"]
        if e.get("nb"):
            a["nb"] = 1
        c = col[team["sim"][e["pos"]]]
        row = rows.setdefault(turn, {"t": turn, "c": [[], [], [], []]})
        row["c"][c].append(a)
        if e.get("nb"):
            row.setdefault("nb", []).append([c, k])
    return dict(rows=[rows[t] for t in sorted(rows)], turns=last)


def representative_seq(stage_str, team, policy, runs_res, seed):
    """대표 1판: 클리어한 판 중 처치 턴이 중앙값에 가장 가까운 판(같으면 앞 번호), 클리어가 없으면 첫 판(실패 예시)"""
    runs = runs_res.get("runs") or []
    clears = [(i, t) for i, (r, t) in enumerate(runs) if r == "clear"]
    if clears:
        ts = sorted(t for _, t in clears)
        med = ts[(len(ts) - 1) // 2]
        idx = min(clears, key=lambda it: (abs(it[1] - med), it[0]))[0]
        kind = "clear"
    else:
        idx, kind = 0, (runs[0][0] if runs else "wipe")
    res, err = run_sim(stage_str, team, 1, seed, policy=policy, run_offset=idx, timeline=True)
    if res is None:
        return None
    sq = seq_from_timeline(res.get("timeline") or [], team)
    sq.update(run=idx, kind=kind, ttk=(runs[idx][1] if runs else None))
    return sq


# ------------------------------------------------------------------ 스테이지 1개
def stage_job(job):
    foe_key, tab, name, seed, runs = job
    t0 = time.perf_counter()
    stage_str = "%s/%s/%s" % (foe_key, tab, name)
    st = stage_obj(foe_key, tab, name)
    nparties = CONTENT_META[foe_key][2]
    S = {k: seed + v for k, v in SEEDS.items()}
    teams = {}
    parties = []
    out = dict(lv=st["level"], n=st["enemy_total"], tl=st.get("turn_limit"), teams=teams, parties=parties)

    def add_team(combo, approx):
        k = ckey(combo)
        if k not in teams:
            teams[k] = dict(arrange(combo), a=round(approx, 3))
        return k

    def screen(keys):
        for k in keys:
            if "auto" not in teams[k]:
                res, err = run_sim(stage_str, teams[k], runs["screen"], S["screen"])
                teams[k]["auto"] = summarize(res, teams[k], err)

    def party_pool(used):
        cands, def_pen = candidates(foe_key, tab, st, used)
        if len(cands) < 4:
            return None
        ranked = pr.top_parties(cands, base()["cfg"], base()["tags"], def_pen, 40)
        top = [add_team(c, v) for c, v, _ in ranked[:K_TOP]]
        keep = [[add_team(c, v), kind] for c, v, kind in keepers(cands, ranked, def_pen, stage_str + "#%d" % len(used))]
        return top, keep

    def finalize(keys):
        """선별 판(screen) -> 경쟁 후보(1위와 클리어 범위 겹침, 최소 3·최대 5)를 별도 시드 final 판으로 확정"""
        screen(keys)
        order = rank_keys(teams, keys)
        lead = teams[order[0]]["auto"]
        cont = []
        for k in order:
            r = teams[k]["auto"]
            if not r.get("g"):
                continue
            overlap = lead.get("g") and r["ci"][1] >= lead["ci"][0]
            if len(cont) < MIN_FINAL or (overlap and len(cont) < MAX_FINAL):
                cont.append(k)
        for k in cont:
            if teams[k]["auto"]["n"] < runs["final"]:
                res, err = run_sim(stage_str, teams[k], runs["final"], S["final"])
                teams[k]["auto"] = summarize(res, teams[k], err)
                teams[k]["fin"] = 1
        return rank_keys(teams, keys), cont

    # 파티 1(코스모는 파티 2 도 — 파티 1 상위 3 시나리오마다 후보를 모은다)
    p1 = party_pool(set())
    if p1 is None:
        return stage_str, out, time.perf_counter() - t0
    top1, keep1 = p1
    keys1 = top1 + [k for k, _ in keep1]
    screen(keys1)
    gate_ok = any(teams[k]["auto"].get("g") for k in keys1)
    if not gate_ok:   # 미지원 생존 기믹(스테이지 단위) — 숫자를 내지 않는다
        out["gate"] = False
        out["why"] = teams[keys1[0]]["auto"].get("us", [])
        for k in keys1:
            teams[k].pop("auto", None)
        parties.append(dict(top=top1, keep=keep1))
        return stage_str, out, time.perf_counter() - t0
    order1, cont1 = finalize(keys1)
    parties.append(dict(top=top1, keep=keep1, rank=order1, cont=cont1))
    if nparties > 1:
        top2u, keep2u, main2 = [], [], None
        for scen in [k for k in order1 if teams[k]["auto"].get("g")][:3]:
            members = set(scen.split(","))
            p2 = party_pool(members)
            if p2 is None:
                continue
            t2, k2 = p2
            finalize(t2 + [k for k, _ in k2])
            if main2 is None:
                main2 = (members, t2)
            top2u += [k for k in t2 if k not in top2u]
            keep2u += [kk for kk in k2 if kk not in keep2u]
        order2, cont2 = [], []
        if main2:   # 웹과 같게: 파티 1 1위 기준 상위 10 + (모든 시나리오의) 보존 후보 중 파티 1 과 겹치지 않는 팀
            members, t2 = main2
            order2, cont2 = finalize(t2 + [k for k, _ in keep2u if not members & set(k.split(","))])
        parties.append(dict(top=top2u, keep=keep2u, rank=order2, cont=cont2))

    # 수동: 정책 탐색(별도 시드) -> 최고 정책 평가(또 다른 시드, 오토와 같은 판 수)
    for k, tm in teams.items():
        if "auto" not in tm or not tm["auto"].get("g"):
            continue
        best = None
        for pol in POLICIES:
            res, err = run_sim(stage_str, tm, runs["msearch"], S["msearch"], policy=pol)
            r = summarize(res, tm, err)
            key = gate_key(r, 0)
            if best is None or key < best[0]:
                best = (key, pol)
        pol = best[1]
        n = runs["meval_final"] if tm.get("fin") else runs["meval_screen"]
        res, err = run_sim(stage_str, tm, n, S["meval"], policy=pol, per_run=True)
        m = summarize(res, tm, err)
        m["pol"] = list(pol)
        a = tm["auto"]
        m["d"] = dict(c=round(m.get("c", 0) - a["c"], 3) if m.get("g") else None,
                      t=round(m["t"] - a["t"], 2) if (m.get("t") is not None and a.get("t") is not None) else None)
        tm["man"] = m
        tm["_mres"] = res

    # 서순(상위 3팀, 파티마다)
    for p in parties:
        for k in [k for k in p.get("rank", []) if teams[k].get("man", {}).get("g")][:SEQ_TEAMS]:
            tm = teams[k]
            if "seq" in tm or tm.get("_mres") is None:
                continue
            sq = representative_seq(stage_str, tm, tuple(tm["man"]["pol"]), tm["_mres"], S["meval"])
            if sq:
                tm["seq"] = sq

    # 민감도(파티마다 확정 후보): 같은 시드로 기준·변형을 100판씩 -> 1위가 바뀌는 가정
    for p in parties:
        cont = p.get("cont") or []
        if len(cont) < 2:
            continue
        def top_of(results):
            return sorted(cont, key=lambda k: (gate_key(results[k], teams[k]["a"]), k))[0]
        basev = {}
        for k in cont:
            res, err = run_sim(stage_str, teams[k], runs["sens"], S["sens"])
            basev[k] = summarize(res, teams[k], err)
        btop = top_of(basev)
        sens = [dict(id="base", label="기본 가정", top=btop, c={k: basev[k].get("c") for k in cont}, t={k: basev[k].get("t") for k in cont})]
        for sid, label, extra in SENS:
            v = {}
            for k in cont:
                res, err = run_sim(stage_str, teams[k], runs["sens"], S["sens"], extra=extra)
                v[k] = summarize(res, teams[k], err)
            vtop = top_of(v)
            sens.append(dict(id=sid, label=label, top=vtop, flip=vtop != btop, c={k: v[k].get("c") for k in cont},
                             t={k: v[k].get("t") for k in cont}))
            if vtop != btop:
                for kk in (btop, vtop):
                    dep = teams[kk].setdefault("dep", [])
                    if sid not in dep:
                        dep.append(sid)
        # 노바 포스 개인 풀(수동 결과에만 영향): 1위 팀 수동 정책을 개인 풀로
        tk = p["rank"][0] if p.get("rank") else None
        if tk and teams[tk].get("man", {}).get("g"):
            tm = teams[tk]
            res, err = run_sim(stage_str, tm, runs["sens"], S["sens"], policy=tuple(tm["man"]["pol"]), extra={"rules_override": NOVA_SENS[2]})
            r = summarize(res, tm, err)
            res0, err0 = run_sim(stage_str, tm, runs["sens"], S["sens"], policy=tuple(tm["man"]["pol"]))
            r0 = summarize(res0, tm, err0)
            sens.append(dict(id=NOVA_SENS[0], label=NOVA_SENS[1], man=1, top=tk, flip=False,
                             c={tk: r.get("c")}, t={tk: r.get("t")}, c0={tk: r0.get("c")}, t0={tk: r0.get("t")}))
        p["sens"] = sens
    for p in parties:
        if p.get("rank"):
            r1 = teams[p["rank"][0]].get("auto")
            r2 = teams[p["rank"][1]].get("auto") if len(p["rank"]) > 1 else None
            p["close"] = is_close(r1, r2)
            p["allzero"] = all((teams[k].get("auto") or {}).get("c", 0) == 0 for k in p["rank"] if (teams[k].get("auto") or {}).get("g"))
    for tm in teams.values():
        tm.pop("_mres", None)
        tm.pop("sim", None)
        tm.pop("li", None)
        tm.pop("fin", None)
    return stage_str, out, time.perf_counter() - t0


# ------------------------------------------------------------------ 범위·버전·출력
def pick_stages(mode, contents=None):
    out = []
    for c in base()["fs"]["contents"]:
        k = c["key"]
        if contents and k not in contents:
            continue
        for t in c["tabs"]:
            sts = t["stages"]
            if mode == "all" or k in ("cosmo", "rush", "cube"):
                ch = sts
            elif k == "op":
                ch = [sts[0], sts[-1]] if len(sts) > 1 else sts
            elif k == "clo":
                ch = [s for i, s in enumerate(sts) if (i + 1) % 50 == 0]
                if sts[-1] not in ch:
                    ch.append(sts[-1])
            else:
                ch = [sts[-1]]
            out += [(k, t["tab"], s["name"]) for s in ch]
    return out


def _norm_hash(paths):
    h = hashlib.sha1()
    for p in paths:
        with open(p, "rb") as f:
            h.update(f.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def sim_version():
    """시뮬 결과에 영향을 주는 입력: 적·구원자 원본, 규칙 파일, 엔진 코드(줄바꿈 차이 무시)"""
    from battlesim.api import SCHEMA_VERSION
    bs = os.path.join(ROOT, "battlesim")
    code = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(bs) if "__pycache__" not in dp for f in fs if f.endswith(".py"))
    foe_src = pr._json(pr.FOE).get("_source", "")
    return dict(engine=SCHEMA_VERSION, foe_js=foe_src.rsplit("v=", 1)[-1] if "v=" in foe_src else _norm_hash([os.path.join(ROOT, "rawdata", "foe.js")]),
                databook=_norm_hash([os.path.join(ROOT, "rawdata", "databook_main.json")]),
                rules=_norm_hash([os.path.join(bs, "rules", "default.json")]), code=_norm_hash(code))


def low_priority():
    """이 프로세스(와 이후 만드는 자식)를 낮은 우선순위로 — 다른 작업을 방해하지 않게(Windows: IDLE_PRIORITY_CLASS)"""
    try:
        if os.name == "nt":
            import ctypes
            k = ctypes.windll.kernel32
            k.SetPriorityClass(k.GetCurrentProcess(), 0x40)
        else:
            os.nice(19)
    except Exception:
        pass


def stage_meta(selv, simv, seed, runs, quick):
    """스테이지마다 붙는 실행 정보(이 스테이지 결과를 만든 실행의 것 — 부분 재생성에서도 다른 스테이지 것으로 덮지 않는다)"""
    return dict(sel=selv, sv=dict(simv), seed=seed, runs=dict(runs), quick=bool(quick), patch=DATA_PATCH)


def merge_stages(prev, recs, selv):
    """--stage 부분 재생성: 기존 스테이지는 자기 meta 를 그대로 두고 새 스테이지만 덮는다.
    추천 입력이 달라진(meta.sel != 지금) 기존 스테이지와 meta 가 없는 옛 형식은 버린다(옛 후보로 계산된 결과라)."""
    merged = {}
    if prev.get("schema_version") == SCHEMA:
        for sk, rec in prev.get("stages", {}).items():
            if (rec.get("meta") or {}).get("sel") == selv:
                merged[sk] = rec
    merged.update(recs)
    return merged


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--contents", default="")
    ap.add_argument("--stage", action="append", default=[])
    ap.add_argument("--stages", default="repr", choices=("repr", "all"))
    ap.add_argument("--workers", type=int, default=1, help="프로세스 수(기본 1, 이 PC 규칙상 최대 2)")
    ap.add_argument("--normal-priority", action="store_true", help="기본은 낮은 우선순위(Idle)로 실행")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "sim"))
    a = ap.parse_args(argv)
    if not a.normal_priority:
        low_priority()
    runs = QUICK_RUNS if a.quick else RUNS
    contents = [x for x in a.contents.split(",") if x] or None
    if a.stage:
        stages = [tuple(s.split("/", 2)) for s in a.stage]
    else:
        stages = pick_stages(a.stages, contents)
    os.makedirs(a.out, exist_ok=True)
    jobs = [(k, t, n, a.seed, runs) for k, t, n in stages]
    print("스테이지 %d개, 프로세스 %d, 판 수 %s" % (len(jobs), a.workers, runs), flush=True)
    results = {}
    t0 = time.perf_counter()
    times = []
    if a.workers > 1 and len(jobs) > 1:
        with mp.Pool(a.workers) as pool:
            for i, (ss, rec, dt) in enumerate(pool.imap_unordered(stage_job, jobs)):
                results[ss] = rec
                times.append(dt)
                print("[%d/%d] %s %.1fs" % (i + 1, len(jobs), ss, dt), flush=True)
    else:
        for i, j in enumerate(jobs):
            ss, rec, dt = stage_job(j)
            results[ss] = rec
            times.append(dt)
            print("[%d/%d] %s %.1fs" % (i + 1, len(jobs), ss, dt), flush=True)
    wall = time.perf_counter() - t0
    by = {}
    for k, t, n in stages:
        by.setdefault(k, {})["%s|%s" % (t, n)] = results["%s/%s/%s" % (k, t, n)]
    idx_path = os.path.join(a.out, "index.json")
    old = pr._json(idx_path) if os.path.exists(idx_path) else {}
    files = dict(old.get("contents", {})) if old.get("schema_version") == SCHEMA else {}
    selv, simv = pr.selection_version(), sim_version()
    meta = stage_meta(selv, simv, a.seed, runs, a.quick)
    for k, recs in by.items():
        fn = "%s.json" % k
        path = os.path.join(a.out, fn)
        for rec in recs.values():
            rec["meta"] = dict(meta)
        prev = pr._json(path) if (a.stage and os.path.exists(path)) else {}
        merged = merge_stages(prev, recs, selv)
        doc = dict(schema_version=SCHEMA, content=k, stages=merged)
        write_json(path, doc)
        files[k] = dict(file=fn, stages=len(merged), bytes=os.path.getsize(path))
    idx = dict(schema_version=SCHEMA, conditions=CONDITIONS, k_top=K_TOP, clear_bin=CLEAR_BIN,
               policies=[list(p) for p in POLICIES], sens=[[s[0], s[1]] for s in SENS] + [[NOVA_SENS[0], NOVA_SENS[1]]],
               seq_turns=SEQ_TURNS, contents=files,
               last_run=dict(meta, stages=len(jobs), only=bool(a.stage), contents=sorted(by)))
    write_json(idx_path, idx)
    print("완료: %d 스테이지, 벽시계 %.0fs, 스테이지당 중앙 %.1fs(최대 %.1fs) -> %s" % (
        len(jobs), wall, sorted(times)[len(times) // 2] if times else 0, max(times) if times else 0, a.out), flush=True)
    return idx


if __name__ == "__main__":
    main()
