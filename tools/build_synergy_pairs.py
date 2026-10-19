# -*- coding: utf-8 -*-
"""스타세이비어 구원자 스킬 연계(시너지 쌍) 추출.
실행: python -X utf8 -I build_synergy_pairs.py
입력(읽기 전용): databook main.json, partynavigator savior_reco.json / synergy_tags.json
출력: 같은 폴더의 synergy_pairs.json, synergy_pairs_review.md
방향: a = 제공자(부여/버프/생존 지원), b = 소비자(그 효과를 조건/증폭으로 참조). directed=false 면 대칭.
각 레코드의 conf: "확인"(효과 줄 원문의 조건/대상으로 직접 확인) / "추정"(키워드·설명문·수치 휴리스틱).
"""
import json, re, os, collections

import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "rawdata", "databook_main.json")  # 데이터북 data/main.js 를 JSON 으로 푼 파일
TAGS = os.path.join(ROOT, "data", "synergy_tags.json")
RECO = os.path.join(ROOT, "data", "savior_reco.json")
OUT = os.path.join(ROOT, "data")  # synergy_pairs.json (리뷰 md 는 docs/ 로 옮긴다)

# ===================== 규칙(여기만 고치면 됨) =====================
ATTR_STACK = {"점화": "태양", "도약": "별", "냉각": "달", "격동": "혼돈", "통찰": "질서"}
HELPER_WORDS = ("확인용", "체크용", "카운팅", "판별용", "측정용")   # 내부 계산용 가짜 상태
TYPE_NAME = {1: "1:부여→소비", 2: "2:버프증폭", 3: "3:생존연계", 4: "4:쿨감·행동게이지→궁극/특수", 5: "5:속성공유"}
# 아군 대상 판정
ALLY_TG = ("아군 전체", "아군(자동 지정)", "아군 1명(자동 지정)", "자신 제외 아군 전체")
ENEMY_TG = ("적 전체", "적 1명(자동 지정)", "적(자동 지정)")
# 디버프로 보지 않을 이름(제어/표식은 상태 소비 대상이지만 일반 디버프 풀에서는 제외)
NON_DEBUFF = ("도발", "강화 불가", "효과 지속 턴")
# 스탯 키워드 -> 버프 범주
STAT_CAT = {"공격력": "ally_atk", "치명타 확률": "ally_crit", "치명타 피해": "ally_crit",
            "속도": "ally_spd", "방어력": "ally_def"}
# 아군 이벤트(조건 트리거) 접두어
ALLY_TRIG = ("아군",)
# 소비자 효과 가치(payoff) 임계값
PAYOFF_DMG_BIG, PAYOFF_DMG_MID = 30, 15
PAYOFF_AG_BIG, PAYOFF_AG_MID = 30, 15
# 공격력 비례도 임계(스킬 계수와 기본 스탯으로 추정한 공격력 기여 비율)
ATK_SHARE_FULL, ATK_SHARE_PART = 0.7, 0.4
# T1 일반 약화 소비 쌍은 '전담 디버퍼'(디버프 종류 >=2 또는 role/태그)만 연결
DEDICATED_DEBUFF_KINDS = 2
# =====================================================================

U = json.load(open(SRC, encoding="utf8"))["units"]
TG = json.load(open(TAGS, encoding="utf8"))["saviors"]
RC = json.load(open(RECO, encoding="utf8"))
assert len(U) == len(TG)
KEYS = []
for u, t in zip(U, TG):
    assert (u["n"], u["ti"], u["v"]) == (t["name"], t["subtitle"], t["variant"]), (u["n"], t["name"])
    KEYS.append(t["key"])
RECO_KEYS = {s["key"] for s in RC["saviors"]}


def reco_flag(k):
    return k in RECO_KEYS


# gloss: 상태 이름 -> 분류(강화/약화/속성 스택...)
KIND = {}
for u in U:
    for s in u["sk"]:
        for g in s.get("gl", []):
            KIND.setdefault(g["n"], g["k"])


def is_helper(n):
    return any(w in n for w in HELPER_WORDS)


def clip(s, n=110):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n - 1] + "…"


# ---------------- 줄 파서 ----------------
TG_PAT = re.compile(r"^(자신 제외 아군 전체|아군 1명\(자동 지정\)|아군\(자동 지정\)|아군 전체|적 1명\(자동 지정\)|적\(자동 지정\)|적 전체|스킬 대상|자신)에게\s*(.*)$")


def parse_line(l):
    m = re.match(r"\s*\[([^\]]*)\]\s*(.*)$", l)
    if not m:
        return None
    timing, rest = m.group(1), m.group(2)
    cond = None
    if rest.startswith("(조건: "):
        depth = 0
        for i, ch in enumerate(rest):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    cond = rest[len("(조건: "):i]
                    rest = rest[i + 1:].strip()
                    break
    tgt, eff = None, rest
    m2 = TG_PAT.match(rest)
    if m2:
        tgt, eff = m2.group(1), m2.group(2)
    trig, kv = "", {}
    if cond is not None:
        m3 = re.match(r"^(.*?)(?:\s*\[(.*)\])?$", cond)
        trig = m3.group(1).strip()
        if m3.group(2):
            cur = None
            for part in m3.group(2).split(";"):
                part = part.strip()
                if ": " in part:
                    k, v = part.split(": ", 1)
                    cur = k.strip()
                    kv.setdefault(cur, []).append(v.strip())
                elif cur is not None:
                    kv[cur].append(part)
    sts = re.findall(r"〈([^〉]+)〉", eff)
    stats = []
    mp = re.search(r"〉\s*\(([^)]*)\)", eff)
    if mp and " / " in mp.group(1):
        for it in mp.group(1).split(" / ", 1)[1].split(", "):
            mm = re.match(r"^(.*?)\s*([+-][0-9.]+)%?$", it.strip())
            if mm:
                stats.append((mm.group(1).replace("%", "").strip(), float(mm.group(2))))
    return dict(raw=l.strip(), timing=timing, trig=trig, kv=kv, tgt=tgt, eff=eff, sts=sts, stats=stats)


def names(vlist):
    out = []
    for v in vlist:
        for n in re.split(r",\s*", v):
            n = n.strip()
            if n:
                out.append(n)
    return out


def payoff(eff):
    """소비자 줄 효과의 가치 1~3 (추정 휴리스틱)."""
    if "추가 턴" in eff or "추가 발동" in eff:
        return 3
    m = re.search(r"피해 증가 \+([0-9.]+)%", eff)
    if m:
        n = float(m.group(1))
        if "1개당" in eff:
            return 2
        return 3 if n >= PAYOFF_DMG_BIG else 2 if n >= PAYOFF_DMG_MID else 1
    m = re.search(r"치명타 피해 \+([0-9.]+)%", eff)
    if m:
        return 3 if float(m.group(1)) >= 30 else 2
    if "방어 관통" in eff or "연쇄 피해" in eff or "공격력% +" in eff or "반격" in eff or "쿨타임" in eff and "감소" in eff:
        return 2
    m = re.search(r"행동 게이지 ([0-9.]+)%p 증가", eff)
    if m:
        n = float(m.group(1))
        return 3 if n >= PAYOFF_AG_BIG else 2 if n >= PAYOFF_AG_MID else 1
    return 1


# ---------------- 구원자별 사실 추출 ----------------
class Unit:
    pass


def build_unit(i):
    u = U[i]
    o = Unit()
    o.i, o.key, o.name, o.ti = i, KEYS[i], u["n"], u["ti"]
    o.attr, o.role = u["a"], u["r"]
    o.tags = set(TG[i]["tags"])
    o.prov = []   # (cat, name, mag, evidence, conf)
    o.cons = []   # (cat, name, payoff, evidence, conf)
    o.self_grants = set()
    o.restrict = {}   # 증거문자열 -> 대상 속성 제한(설명문에 'X 속성 아군'이 있을 때)
    o.multi_action = False
    o.crit_rel = 0
    o.ult_cond = 0
    o.self_stack = collections.Counter()
    atk_c = hp_c = df_c = 0.0
    st = {k: float(re.sub(r"[^0-9.]", "", v) or 0) for k, v in u["st"] if k in ("공격력", "생명력", "방어력")}
    ult_cf = bas_cf = spe_cf = 0.0
    lines = []   # (skill dict, line text, label)
    for s in u["sk"]:
        for l in s.get("ef", []):
            lines.append((s, l, s["n"]))
        if s.get("dm"):
            c = {k: 0.0 for k in ("공격력", "생명력", "방어력")}
            for k, v in re.findall(r"(공격력|생명력|방어력)×([0-9.]+)%", s["dm"]):
                c[k] += float(v) / 100.0
            tot = c["공격력"] * st.get("공격력", 1) + c["생명력"] * st.get("생명력", 1) + c["방어력"] * st.get("방어력", 1)
            w = c["공격력"] * st.get("공격력", 1) / tot if tot else 0
            if s["sl"].endswith("기본기"):
                bas_cf = max(bas_cf, s["cf"][0] / 100.0 if s.get("cf") else 0)
            if s["sl"].endswith("특수기"):
                spe_cf = max(spe_cf, s["cf"][0] / 100.0 if s.get("cf") else 0)
            if s["sl"].endswith("궁극기"):
                ult_cf = max(ult_cf, s["cf"][0] / 100.0 if s.get("cf") else 0)
            atk_c += w * (s["cf"][0] if s.get("cf") else 100)
            hp_c += (s["cf"][0] if s.get("cf") else 100)
    o.atk_share = (atk_c / hp_c) if hp_c else 0.0
    o.cf = (bas_cf, spe_cf, ult_cf)
    o.cd = {s["sl"]: s.get("cd") for s in u["sk"] if s.get("cd")}
    for k, v in (u.get("nb") or {}).items():
        if k in ("desc", "gl", "hl"):
            continue
        for l in v:
            lines.append(({"n": "고유효과(" + k + ")", "tg": "-", "sl": "nb", "d1": ""}, l, "고유효과(" + k + ")"))
    seen = set()
    for s, l, lab in lines:
        p = parse_line(l)
        if not p or (lab, l) in seen:
            continue
        seen.add((lab, l))
        ev = "%s: %s" % (lab, clip(p["raw"]))
        tg = p["tgt"]
        stg = s.get("tg", "")
        ally = tg in ALLY_TG or (tg == "스킬 대상" and (stg.startswith("아군") or stg == "반응 대상(아군)"))
        enemy = tg in ENEMY_TG or (tg == "스킬 대상" and (stg.startswith("적") or "적" in stg))
        if tg == "자신":
            for sn in p["sts"]:
                o.self_grants.add(sn)
            for sn in re.findall(r"'([^']+)'", p["eff"]):
                pass
        # ---- 제공(provides) ----
        if ally:
            rs = set(re.findall(r"(별|달|태양|혼돈|질서) 속성 아군", s.get("d1", ""))) | set(re.findall(r"아군 대상이 (별|달|태양|혼돈|질서) 속성이라면", s.get("d1", "")))
            if rs and tg != "자신":
                o.restrict[ev] = rs
            for sn in p["sts"]:
                if is_helper(sn):
                    continue
                if sn in ATTR_STACK or sn == "냉각 스택":
                    grp = tg in ("아군 전체", "자신 제외 아군 전체")
                    o.prov.append(("ally_stack", sn, 1 if grp else 0.6, ev, "확인"))
                    continue
                if sn == "보호막":
                    o.prov.append(("ally_shield", sn, 1, ev, "확인"))
                    continue
                cats = set()
                mag = 0
                for sk_, v in p["stats"]:
                    for kw, cat in STAT_CAT.items():
                        if sk_.startswith(kw) and v > 0:
                            cats.add(cat)
                            mag = max(mag, v)
                if sn in ("공격력 증가",) and not cats:
                    cats.add("ally_atk")
                if sn in ("수호",) or "피해 분담" in "".join(k for k, _ in p["stats"]) or "서약" in sn:
                    cats.add("ally_guard")
                if tg in ("아군(자동 지정)", "아군 1명(자동 지정)") or (tg == "스킬 대상" and stg == "아군 단일"):
                    mag *= 0.6   # 단일 대상 지원은 수혜 폭이 좁다
                for c in cats:
                    o.prov.append((c, sn, mag, ev, "확인"))
                if "무작위 효과" in p["eff"]:
                    continue   # 4종 중 1개(대상도 무작위)라 특정 버프 제공으로 보지 않는다
                if not cats:
                    o.prov.append(("ally_status", sn, 0, ev, "확인"))
            if "회복 =" in p["eff"] or "지속 회복" in p["eff"]:
                o.prov.append(("ally_heal", "회복", 1, ev, "확인"))
            m = re.search(r"행동 게이지 ([0-9.]+)%p 증가", p["eff"])
            if m and tg != "자신":
                o.prov.append(("ally_ag", "행동 게이지", float(m.group(1)), ev, "확인"))
            if re.search(r"스킬 쿨타임 [0-9]+턴 감소", p["eff"]):
                o.prov.append(("ally_cd", "쿨타임", 1, ev, "확인"))
        if enemy:
            for sn in p["sts"]:
                if is_helper(sn):
                    continue
                o.prov.append(("enemy_status", sn, 0, ev, "확인"))
                if sn == "도발":
                    o.prov.append(("taunt", sn, 1, ev, "확인"))
                    continue
                neg = any(v < 0 and any(sk_.startswith(x) for x in ("공격력", "방어력", "속도", "효과", "명중", "회복")) for sk_, v in p["stats"])
                if (KIND.get(sn) == "약화" or neg or "피해" in p["eff"] and "턴마다" in p["eff"]) and sn not in NON_DEBUFF:
                    o.prov.append(("debuff", sn, 1, ev, "확인"))
            m = re.search(r"행동 게이지 ([0-9.]+)%p 감소", p["eff"])
            if m:
                o.prov.append(("enemy_ag_down", "행동 게이지 감소", float(m.group(1)), ev, "확인"))
        if "강인도" in p["eff"] and "피해" in p["eff"] and tg == "자신":
            pass
        # ---- 소비(consumes) ----
        kv, trig = p["kv"], p["trig"]
        pay = payoff(p["eff"])
        mine = trig.startswith("내 공격") or trig.startswith("내 비공격")
        if mine:
            for key in ("대상이 보유", "특정 효과 보유 적 존재"):
                for n in names(kv.get(key, [])):
                    if not is_helper(n):
                        o.cons.append(("enemy_has", n, pay, ev, "확인"))
            if "대상 약화효과 보유" in kv:
                cnt = names(kv.get("효과 개수 이상", []) + kv.get("효과 개수", []))
                o.cons.append(("enemy_debuff_any", cnt[0] if cnt else "1", pay, ev, "확인"))
            if "대상 브레이크" in kv or "대상 강인도 없음" in kv:
                o.cons.append(("enemy_break", "브레이크", pay, ev, "확인"))
        if "공격 대상의 약화 효과 1개당" in p["eff"]:
            o.cons.append(("enemy_debuff_any", "개수비례", 2, ev, "확인"))
        if "브레이크 대상 피해 증가" in p["eff"]:
            o.cons.append(("enemy_break", "브레이크", 2, ev, "확인"))
        if trig.startswith("아군"):
            hit = ("피격" in trig) or ("피해 받기 직전" in trig)
            got = False
            for key in ("시전자가 보유", "턴 유닛이 보유", "대상이 보유"):
                for n in names(kv.get(key, [])):
                    if not is_helper(n):
                        o.cons.append(("ally_has", n, pay, ev, "확인"))
                        got = True
            for key in ("시전자 속성", "턴 유닛 속성", "대상 속성"):
                for n in names(kv.get(key, [])):
                    o.cons.append(("ally_attr", n, pay, ev + (" [피격시]" if hit else ""), "확인"))
                    got = True
            if "대상 브레이크" in kv:
                o.cons.append(("enemy_break", "브레이크", pay, ev, "확인"))
                got = True
            if hit:
                o.cons.append(("hit_ally", trig, pay, ev, "확인"))
            elif not got:
                o.cons.append(("ally_event", trig, pay, ev, "확인"))
        if trig.startswith("내가 피격") or trig.startswith("내가 피해를 받기 직전"):
            o.cons.append(("hit_self", trig, pay, ev, "확인"))
        if mine or trig.startswith("내 턴") or trig.startswith("내가"):
            if "결과" in kv and any("치명타" in x for x in kv["결과"]):
                o.cons.append(("crit_cond", "치명타", pay, ev, "확인"))
                o.crit_rel += 1
            for sk_ in kv.get("사용 스킬", []):
                if sk_ in ("궁극기", "특수기"):
                    o.ult_cond += 1
                    o.cons.append(("ult_cond", sk_, pay, ev, "확인"))
            if "자신 강화효과 보유" in kv:
                o.cons.append(("buff_cond", "강화효과", pay, ev, "확인"))
            for n in names(kv.get("자신이 보유", [])):
                if n in ATTR_STACK:
                    o.self_stack[n] += 1
                    o.cons.append(("self_stack", n, pay, ev, "확인"))
                elif not is_helper(n):
                    o.cons.append(("self_has", n, pay, ev, "확인"))
        if p["tgt"] == "자신" and any(x in p["eff"] for x in ("추가 턴", "추가 발동", "〈추가 턴〉")):
            o.multi_action = True
        if "치명타 확률 +" in p["eff"] or "치명타 피해 +" in p["eff"] or any(sk_.startswith("치명타") and v > 0 for sk_, v in p["stats"]):
            if p["tgt"] == "자신":
                o.crit_rel += 1
    if o.tags & {"추가턴/연속행동"}:
        o.multi_action = True
    # 설명문(d1) 키워드 추정: 효과 줄에 안 잡히는 아군 지원
    for s in u["sk"]:
        d1 = s.get("d1", "")
        if not d1:
            continue
        ev = "%s: %s" % (s["n"], clip(d1, 90))
        if re.search(r"아군[^.]*생명력을 회복", d1) and not any(c == "ally_heal" for c, *_ in o.prov):
            o.prov.append(("ally_heal", "회복", 1, ev, "추정"))
        if re.search(r"(아군|무작위 아군)[^.]*행동 게이지를[^.]*증가", d1) and not any(c == "ally_ag" for c, *_ in o.prov):
            m = re.search(r"행동 게이지를 \[?([0-9.]+)%?\]?", d1)
            o.prov.append(("ally_ag", "행동 게이지", float(m.group(1)) if m else 9, ev, "추정"))
        if (s.get("tg") == "반응 대상(아군)" or "사랑의 서약" in d1 or "피해 분담" in d1) and "아군" in d1 and not any(c == "ally_guard" for c, *_ in o.prov):
            o.prov.append(("ally_guard", "수호/피해 분담", 1, ev, "확인"))
        if re.search(r"아군[^.]*쿨타임[^.]*감소", d1) and not any(c == "ally_cd" for c, *_ in o.prov):
            o.prov.append(("ally_cd", "쿨타임", 1, ev, "추정"))
    return o


units = [build_unit(i) for i in range(len(U))]
by_name = collections.defaultdict(list)
for o in units:
    by_name[o.name].append(o)


def lab(o):
    return "%s(%s)" % (o.name, o.ti)


def same_char(a, b):
    return a.name == b.name


# 인덱스: 제공 범주 -> [(unit, name, mag, ev, conf)]
PROV = collections.defaultdict(list)
for o in units:
    for c, n, m, ev, cf in o.prov:
        PROV[c].append((o, n, m, ev, cf))
debuff_kinds = collections.defaultdict(set)
for o in units:
    for c, n, m, ev, cf in o.prov:
        if c == "debuff":
            debuff_kinds[o.i].add(n)

# ---------------- 쌍 생성 ----------------
cands = []   # dict


def add(a, b, typ, strength, directed, reason, evs, conf, cat):
    if a.i == b.i or same_char(a, b):
        return
    cands.append(dict(a=a.key, b=b.key, type=TYPE_NAME[typ], tn=typ, strength=max(1, min(3, int(strength))),
                      directed=directed, reason=reason, evidence=[clip(e, 120) for e in evs], conf=conf, cat=cat))


# ===== 유형 1: 부여 -> 소비 =====
for b in units:
    for c, n, pay, evb, cfb in b.cons:
        if c == "enemy_has":
            provs = [p for p in PROV["enemy_status"] if p[1] == n and p[0].i != b.i]
            nprov = len({p[0].i for p in provs})
            for a, _, _, eva, cfa in provs:
                s = pay + (1 if nprov <= 3 else 0) - (1 if nprov >= 7 else 0)
                add(a, b, 1, s, True, "%s 이(가) 적에게 부여하는 〈%s〉을 %s 이(가) 대상 조건으로 참조(효과가치 %d, 부여자 %d명)" % (lab(a), n, lab(b), pay, nprov), [eva, evb], "확인", "enemy_has:" + n)
            # 주의: 보호막 보유 적을 조건으로 쓰는 소비자(예: 에핀델 부케 토스)는 적 버프 해제와 오히려 충돌하므로 해제 담당과 연결하지 않는다.
        elif c == "enemy_debuff_any":
            scaling = (n == "개수비례") or (str(n).isdigit() and int(n) >= 2)
            for a, dn, _, eva, cfa in PROV["debuff"]:
                if a.i == b.i:
                    continue
                kinds = debuff_kinds[a.i]
                dedicated = len(kinds) >= DEDICATED_DEBUFF_KINDS or a.role == "디버퍼"
                if not dedicated:
                    continue
                s = 1 + (1 if (scaling or pay >= 3) else 0) + (1 if (scaling and len(kinds) >= 3) else 0)
                s = min(s, 2)   # 범용 조건이라 상한 2 (강도3은 지명된 상태 참조에만)
                add(a, b, 1, s, True, "%s 이(가) 약화효과 %d종(%s)을 부여, %s 이(가) 대상의 약화효과 보유/개수에 비례해 보너스(범용 조건이라 완만)" % (lab(a), len(kinds), "·".join(sorted(kinds))[:30], lab(b)), [eva, evb], "확인", "debuff_any")
        elif c == "enemy_break":
            for a in units:
                if "강인도파괴" in a.tags and a.i != b.i:
                    ev_a = "태그 강인도파괴: " + ", ".join(TG[a.i]["evidence"].get("강인도파괴", []))
                    add(a, b, 1, min(2, pay), True, "%s 이(가) 강인도 파괴(브레이크) 담당(태그), %s 이(가) 브레이크 대상 조건으로 보너스(추정)" % (lab(a), lab(b)), [ev_a, evb], "추정", "break")
        elif c in ("ally_has", "self_has"):
            provs = [p for p in PROV["ally_status"] + PROV["ally_stack"] if p[1] == n and p[0].i != b.i]
            nprov = len({p[0].i for p in provs})
            for a, _, _, eva, cfa in provs:
                s = pay + (1 if nprov <= 2 else 0)
                add(a, b, 1, s, True, "%s 이(가) 아군에게 부여하는 〈%s〉을 %s 이(가) 조건으로 참조" % (lab(a), n, lab(b)), [eva, evb], "확인", "ally_has:" + n)

# ===== 유형 2: 버프 증폭 =====
def buff_level(b):
    """ATK 버프 수혜 정도 0~3 (공격력 기여 비율 + 다행동)"""
    if b.atk_share >= ATK_SHARE_FULL:
        lv = 2
    elif b.atk_share >= ATK_SHARE_PART:
        lv = 1
    else:
        return 0
    if b.multi_action:
        lv += 1
    return lv


for a, bn, mag, eva, cfa in PROV["ally_atk"]:
    for b in units:
        if b.i == a.i or b.role in ("서포터",) and b.atk_share < ATK_SHARE_FULL:
            continue
        if a.restrict.get(eva) and b.attr not in a.restrict[eva]:
            continue
        if b.atk_share < ATK_SHARE_FULL:
            continue
        big = mag >= 20
        s = 1 + (1 if (b.multi_action or big) else 0) + (1 if (b.multi_action and big) else 0)
        evb = "공격력 비례도 %.0f%%(스킬계수×기본스탯 추정)%s" % (b.atk_share * 100, ", 추가턴/추가발동 있음" if b.multi_action else "")
        add(a, b, 2, s, True, "%s 의 아군 공격력 증가〈%s〉(+%s%%) 수혜: %s 은(는) 공격력 비례 딜러" % (lab(a), bn, int(mag) if mag else "?", lab(b)), [eva, evb], "추정", "atk")
for a, bn, mag, eva, cfa in PROV["ally_crit"]:
    for b in units:
        if b.i == a.i or b.crit_rel < 1:
            continue
        if a.restrict.get(eva) and b.attr not in a.restrict[eva]:
            continue
        crit_lines = [c for c in b.cons if c[0] == "crit_cond"]
        s = 2 + (1 if len(crit_lines) >= 2 else 0)
        evb = crit_lines[0][3] if crit_lines else "자신 치명 버프 보유 " + str(b.crit_rel) + "줄"
        add(a, b, 2, s - (1 if cfa == "추정" else 0), True, "%s 의 치명 버프〈%s〉 수혜: %s 은(는) 치명타 조건/치명 증가 기믹 보유" % (lab(a), bn, lab(b)), [eva, evb], "확인" if crit_lines else "추정", "crit")
for a, bn, mag, eva, cfa in PROV["ally_spd"]:
    for b in units:
        if b.i == a.i or not b.multi_action:
            continue
        if a.restrict.get(eva) and b.attr not in a.restrict[eva]:
            continue
        ev_b = next((c[3] for c in b.cons if c[0] == "self_stack"), "추가턴/추가발동 보유(스택 5 등 조건)")
        add(a, b, 2, 2 if b.atk_share >= ATK_SHARE_PART else 1, True, "%s 의 아군 속도 증가〈%s〉 → 행동 횟수가 늘수록 이득: %s 은(는) 추가턴/연속행동 기믹" % (lab(a), bn, lab(b)), [eva, ev_b], "추정", "spd")
for a, bn, mag, eva, cfa in PROV["ally_atk"] + PROV["ally_crit"] + PROV["ally_spd"] + PROV["ally_def"] + PROV["ally_shield"]:
    for b in units:
        if b.i == a.i:
            continue
        for c, n, pay, evb, cf in b.cons:
            if c == "buff_cond":
                add(a, b, 2, 2 + (1 if pay >= 3 else 0), True, "%s 이(가) 아군에게 강화효과를 부여 → %s 은(는) '자신 강화효과 보유' 조건에서 보너스" % (lab(a), lab(b)), [eva, evb], "확인", "buff_cond")
# 아군 행동에 반응하는 소비자(속성/보유조건이 없는 일반 이벤트) <- 행동 횟수 많은 구원자
for b in units:
    gen = [c for c in b.cons if c[0] == "ally_event"]
    if not gen:
        continue
    evb = gen[0][3]
    for a in units:
        if a.i == b.i:
            continue
        if any(c in ("ally_spd", "ally_ag") for c, *_ in a.prov):
            add(a, b, 2, 1, True, "%s 의 행동 횟수(추가턴/속도/행동게이지) → %s 의 '아군 행동 시' 효과 누적 가속(범용 조건, 약함)" % (lab(a), lab(b)), [next((p[3] for p in a.prov if p[0] in ("ally_spd", "ally_ag")), "추가턴/연속행동 기믹"), evb], "추정", "ally_event")

# ===== 유형 3: 생존 연계 =====
for b in units:
    hits = [c for c in b.cons if c[0] == "hit_self"]
    if not hits:
        continue
    best = max(hits, key=lambda x: x[2])
    # 일반 힐/보호막은 거의 모든 서포터가 해당하므로 소비자 가치가 높을 때만 한 단계 낮춰 연결, 방어력 증가는 제외
    for cat, w, label in (("ally_guard", 0, "피해분담/수호(서약 대상은 공격력 최고 아군 자동 지정)"), ("ally_heal", -1, "회복"), ("ally_shield", -1, "보호막")):
        for a, n, mag, eva, cfa in PROV[cat]:
            if a.i == b.i:
                continue
            if w < 0 and best[2] < 2:
                continue
            s = best[2] + w
            if cat == "ally_guard":
                # 서약(수호) 대상은 '공격력이 가장 높은 아군'이므로 딜러 역할만 가산, 서포터/디펜더는 감산
                if b.role in ("스트라이커", "레인저", "어쌔신", "캐스터") and b.atk_share >= ATK_SHARE_FULL:
                    s += 1
                else:
                    s -= 1
            if len(hits) >= 3:
                s += 0   # 피격 기믹 줄 수는 참고만
            conf = "확인" if cfa == "확인" else "추정"
            add(a, b, 3, s, True, "%s 의 %s 지원 → %s 은(는) 피격 시 발동하는 기믹(%s)으로 맞아도 이득" % (lab(a), label, lab(b), best[1]), [eva, best[3]], conf, "hit:" + cat)
for b in units:
    hits = [c for c in b.cons if c[0] == "hit_ally"]
    if not hits:
        continue
    best = max(hits, key=lambda x: x[2])
    for a, n, mag, eva, cfa in PROV["taunt"]:
        if a.i == b.i:
            continue
        add(a, b, 3, min(3, best[2] + 1), True, "%s 이(가) 도발로 피격을 유도 → %s 은(는) '아군이 피격될 때' 효과 발동" % (lab(a), lab(b)), [eva, best[3]], "확인", "taunt")

# ===== 유형 4: 쿨감/행동게이지 -> 궁극/특수 의존 =====
def ult_dep(b):
    # 궁극/특수 사용에 걸린 보너스 줄(payoff>=2)이 있어야 '의존'으로 본다. 단순 스킬계수 비교는 모두에게 해당해 제외.
    strong = [c for c in b.cons if c[0] == "ult_cond" and c[2] >= 2]
    score = 0
    if b.ult_cond >= 1:
        score += 1
    if len(strong) >= 1:
        score += 1
    if len(strong) >= 3:
        score += 1
    return score


for a, n, mag, eva, cfa in PROV["ally_cd"] + PROV["ally_ag"]:
    for b in units:
        if b.i == a.i:
            continue
        sc = ult_dep(b)
        if sc == 0:
            continue
        if a.restrict.get(eva) and b.attr not in a.restrict[eva]:
            continue
        s = 1 + (1 if sc >= 2 else 0) + (1 if (sc >= 3 and (mag >= 20 or n == "쿨타임")) else 0)
        cdtxt = ", ".join("%s CD%s" % (k, v) for k, v in b.cd.items())
        evb = next((c[3] for c in b.cons if c[0] == "ult_cond" and c[2] >= 2), None) or next(c[3] for c in b.cons if c[0] == "ult_cond")
        evb += " [쿨타임 %s]" % cdtxt
        add(a, b, 4, s - (1 if cfa == "추정" else 0), True, "%s 의 %s 지원 → %s 은(는) 궁극/특수 의존도 %d (추정)" % (lab(a), "쿨타임 감소" if n == "쿨타임" else "행동게이지 증가", lab(b), sc), [eva, evb], "추정", "cd_ag")

# ===== 유형 5: 속성/스택 공유 =====
# (a) 속성 조건 이벤트 소비자 <- 해당 속성 아군
for b in units:
    for c, n, pay, evb, cf in b.cons:
        if c == "ally_attr":
            for a in units:
                if a.attr == n and a.i != b.i:
                    bonus = 1 if (a.multi_action and "[피격시]" not in evb) or ("[피격시]" in evb and ("taunt" in {x[0] for x in a.prov} or a.role == "디펜더")) else 0
                    add(a, b, 5, pay + bonus, True, "%s 은(는) %s 속성 아군이 행동/피격할 때 이득을 받음 → 같은 속성 %s 와 연계" % (lab(b), n, lab(a)), ["%s 속성: %s/%s" % (n, lab(a), a.ti), evb], "확인", "attr:" + n)
# (b) 아군에게 속성 스택을 직접 부여
for a, sn, mag, eva, cfa in PROV["ally_stack"]:
    el = ATTR_STACK.get(sn.replace(" 스택", ""))
    for b in units:
        if b.i == a.i or not b.self_stack:
            continue
        if a.restrict.get(eva) and b.attr not in a.restrict[eva]:
            continue
        if b.self_stack.get(sn.replace(" 스택", ""), 0) > 0:
            add(a, b, 5, 3 if mag >= 1 else 2, True, "%s 이(가) 아군에게 〈%s〉 스택을 직접 부여 → 같은 스택을 쓰는 %s 의 조건이 빨리 충족" % (lab(a), sn, lab(b)), [eva, next(c[3] for c in b.cons if c[0] == "self_stack" and c[1] == sn.replace(" 스택", ""))], "확인", "stack:" + sn)
# (c) 같은 속성 스택 사용자끼리(기본 약연계, 공통 속성상성 피해 증가)
pairs_seen = set()
for x in units:
    for y in units:
        if y.i <= x.i or x.attr != y.attr or same_char(x, y):
            continue
        sx, sy = sum(x.self_stack.values()), sum(y.self_stack.values())
        if sx < 1 or sy < 1:
            continue
        el = [k for k, v in ATTR_STACK.items() if v == x.attr]
        big = lambda o: any(c[0] == "self_stack" and c[2] >= 3 for c in o.cons)
        if not (big(x) or big(y)):
            continue
        s = 1 + (1 if big(x) and big(y) and sx >= 3 and sy >= 3 else 0)
        evx = next((c[3] for c in x.cons if c[0] == "self_stack"), "")
        evy = next((c[3] for c in y.cons if c[0] == "self_stack"), "")
        add(x, y, 5, s, False, "같은 %s 속성: 〈%s〉 스택이 모두 같은 속성 상성 피해 증가로 작용(스택 공유는 아님, 약연계)" % (x.attr, el[0] if el else "?"), [evx, evy], "추정", "same_attr")

# ---------------- 병합 ----------------
merged = {}
for c in cands:
    k = (c["a"], c["b"], c["tn"], c["directed"]) if c["directed"] else (min(c["a"], c["b"]), max(c["a"], c["b"]), c["tn"], False)
    m = merged.get(k)
    if not m:
        merged[k] = dict(c, cats={c["cat"]}, okcats={c["cat"]} if c["conf"] == "확인" else set(), evs=list(c["evidence"]), reasons=[c["reason"]])
    else:
        m["cats"].add(c["cat"])
        if c["conf"] == "확인":
            m["okcats"].add(c["cat"])
        for e in c["evidence"]:
            if e not in m["evs"]:
                m["evs"].append(e)
        if c["strength"] > m["strength"]:
            m["strength"] = c["strength"]
            m["reasons"].insert(0, c["reason"])
        else:
            m["reasons"].append(c["reason"])
        if c["conf"] == "확인":
            m["conf"] = "확인"
out = []
for m in merged.values():
    st = m["strength"]
    # (같은 제공자의 힐+수호처럼 독립이 아닌 근거가 겹칠 수 있어 근거 중복 가산은 하지 않는다)
    out.append({"a": m["a"], "b": m["b"], "type": m["type"], "strength": st, "directed": m["directed"],
                "reason": m["reasons"][0] + (" (외 근거 %d)" % (len(m["cats"]) - 1) if len(m["cats"]) > 1 else ""),
                "evidence": m["evs"][:4], "conf": m["conf"]})
out.sort(key=lambda r: (-r["strength"], r["type"], r["a"], r["b"]))
os.makedirs(OUT, exist_ok=True)
json.dump(out, open(os.path.join(OUT, "synergy_pairs.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)

# ---------------- 리뷰 문서 ----------------
nm = {o.key: "%s(%s)" % (o.name, o.ti) for o in units}
cnt = collections.Counter(r["type"] for r in out)
sc = collections.Counter((r["type"], r["strength"]) for r in out)
pair_sum = collections.defaultdict(lambda: [0, set()])
for r in out:
    k = tuple(sorted((r["a"], r["b"]))) if not r["directed"] else (r["a"], r["b"])
    pair_sum[k][0] += r["strength"] * (1.0 if r["conf"] == "확인" else 0.6)
    pair_sum[k][1].add(r["type"].split(":")[0])
top = sorted(pair_sum.items(), key=lambda kv: (-kv[1][0], -len(kv[1][1])))[:20]
L = ["# 구원자 스킬 시너지 쌍 리뷰", "", "생성: build_synergy_pairs.py (전체 %d쌍, 구원자 %d명)" % (len(out), len(units)), "", "## 유형별 건수 (강도 1/2/3)", ""]
for t in TYPE_NAME.values():
    L.append("- %s: %d건 (강도1 %d / 2 %d / 3 %d)" % (t, cnt[t], sc[(t, 1)], sc[(t, 2)], sc[(t, 3)]))
conf_c = collections.Counter(r["conf"] for r in out)
L += ["", "신뢰도: 확인 %d건 / 추정 %d건" % (conf_c["확인"], conf_c["추정"]), "", "## 상위 20쌍 (방향 있는 쌍 기준, 유형별 강도 합)", ""]
for (a, b), (s, ts) in top:
    L.append("- %s → %s : 가중합 %.1f(확인 1.0/추정 0.6), 유형 %s" % (nm[a], nm[b], s, ",".join(sorted(ts))))
    best = [r for r in out if (r["a"], r["b"]) == (a, b) or (not r["directed"] and {r["a"], r["b"]} == {a, b})]
    for r in sorted(best, key=lambda r: -r["strength"])[:2]:
        L.append("    - [%s s%d %s] %s" % (r["type"].split(":")[0], r["strength"], r["conf"], r["reason"]))
L += ["", "## 불확실한 판정 (키워드·수치 추정, 유형별 대표 10건)", ""]
for t in TYPE_NAME.values():
    est = [r for r in out if r["type"] == t and r["conf"] == "추정"]
    L.append("### %s : 추정 %d건" % (t, len(est)))
    for r in est[:10]:
        L.append("- s%d %s → %s : %s" % (r["strength"], nm[r["a"]], nm[r["b"]], r["reason"]))
    L.append("")
L += ["## 규칙/한계", "",
      "- 확인 = 효과 줄의 조건·대상 필드에서 직접 읽은 연결. 추정 = 설명문 키워드, 태그, 스킬계수×기본스탯 공격력 비례도, 궁극/특수 의존도 등 휴리스틱.",
      "- 효과 줄(ef)에 없는 아군 회복/행동게이지는 설명문(d1) 키워드로 보강(추정). 잠재·아르카나·장비 효과는 미포함.",
      "- 같은 이름 구원자(예: 샤를 변형)끼리는 한 파티에 못 넣는다고 보고 쌍에서 제외.",
      "- '약화효과 보유' 같은 범용 조건은 전담 디버퍼(디버프 2종 이상·태그·역할)만 연결하고 강도 상한 2.",
      "- 속성 공유(5-c)는 스택이 공유되는 것이 아니라 같은 속성 상성 보너스를 같은 적에게 쓰는 약연계라 강도 1~2.", ""]
ver = os.path.join(ROOT, "docs", "synergy_pairs_verification.md")
if os.path.exists(ver):
    L += [open(ver, encoding="utf8").read()]
open(os.path.join(ROOT, "docs", "synergy_pairs_review.md"), "w", encoding="utf8").write("\n".join(L))
print("pairs", len(out), dict(cnt), dict(conf_c))
