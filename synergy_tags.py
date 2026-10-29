#!/usr/bin/env python
"""구원자 스킬 텍스트 -> 파티 시너지 기능 태그 분류기.

실행: python -X utf8 -I synergy_tags.py  (인자 없으면 기본 경로 사용)
입력: rawdata/databook_main.json (units[].sk[].ef = 구조화된 효과 줄, d1 = 설명문)
      data/savior_reco.json (key/name/subtitle 매칭)
출력: data/synergy_tags.json, docs/synergy_tags_review.md

규칙은 아래 딕셔너리(RULES_*)에서 고친다. 효과 줄은 "대상 범위(scope)"를 먼저 판정한 뒤
(self=자신, ally=아군(자신 제외 포함), enemy=적) 범위별 정규식 규칙을 적용한다.
정규식은 (줄 본문 + 〈상태이름〉의 사전 설명) 을 합친 텍스트에 건다.
"""
import json
import os
import re
import sys
from collections import defaultdict, Counter


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, str(HERE))
from battlesim.fileio import atomic_open
MAIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "rawdata", "databook_main.json")  # 팬 데이터북 data/main.js 를 JSON 으로 푼 파일(저장소에서 추적함)
RECO = os.path.join(HERE, "data", "savior_reco.json")
OUT_JSON = os.path.join(HERE, "data", "synergy_tags.json")
OUT_MD = os.path.join(HERE, "docs", "synergy_tags_review.md")

# ---------------------------------------------------------------- 규칙 (여기를 고친다)
# scope 별 {태그: 정규식}. 텍스트 = 효과 줄(타이밍/조건 제거) + 〈상태〉 사전 설명.
RULES_ALLY = {   # 아군(자신 제외 또는 아군 전체/1명)에게 걸리는 효과
    "아군공격력증가": r"공격력(?:%|과 [가-힣 ]+)?(?:이|가)? ?[\d.]*%?(?:씩)? ?(?:증가|\+)|공격력%? ?\+\d",
    "속도증가": r"속도(?:와 [가-힣 ]+|가)?(?:이|가)? ?[\d.]*%?(?:씩)? ?(?:증가|\+)|속도 \+\d|행동 게이지 [\d.]+%p 증가",
    "치명증가": r"치명타 (?:확률|피해)(?! ?(?:감소|저항))[^,/)]{0,12}(?:증가|\+)|치명타 (?:확률|피해)%? ?\+",
    "피해증가": r"주는 피해량이 [\d.]+% 증가|(?<!속성 )피해 증가 \+|방어력을 [\d.]+% 관통|방어 관통|피해량이 [\d.]+%(?:씩)? 증가",
    "보호막": r"보호막",
    "부활": r"부활\(",
    "힐": r"회복 =|회복량|생명력을 회복|회복시",
    "해제": r"약화효과 해제|약화 효과를|디버프 해제",
    "도발/방어지원": r"방어력%? ?(?:\+|이 [\d.]+% 증가|증가)|효과 저항(?:이|가)? ?[\d.]*%? ?(?:증가|\+)|받는 피해량이 [\d.]+% 감소|면역|불사|수호|피해 분담|스킬 피해 무효|회피율|부활|은신",
    "쿨타임감소": r"쿨타임 [\d]+턴 감소|쿨타임 초기화",
    "추가턴/연속행동": r"추가 턴|추가 발동",
}
RULES_ENEMY = {  # 적에게 걸리는 효과
    "적방어력감소": r"방어력(?:이|가)? ?[\d.]*%? ?(?:감소|-)|방어력% ?-",
    "디버프부여": r"감소|기절|속박|침묵|도발|빙결|출혈|연소|점화|강화 불가|표적 각인|고립|물폭탄|미지의 주문|뒤엉킨|참극의 가시|명중률|쌓여가는|받는 피해량이 [\d.]+% 증가",
    "피해증가": r"받는 피해량이 [\d.]+% 증가",
    "도발/방어지원": r"〈도발〉",
    "적버프해제": r"강화효과 해제|버프 해제",
    "적행동게이지감소": r"행동 게이지 [\d.]+%p 감소",
    "쿨타임감소": r"쿨타임 [\d]+턴 증가",   # (자리표시: 적 쿨증가는 현재 데이터에 없음)
}
RULES_SELF = {   # 자신에게 걸리는 효과 (자가 생존/자가 운용)
    "자가생존": r"보호막|면역|불사|스킬 피해 무효|받는 피해량이 [\d.]+% 감소|회피율|회복 =|회복\(|현장 대기|은신|파프닐",
    "쿨타임감소": r"쿨타임 [\d]+턴 감소|쿨타임 초기화",
    "추가턴/연속행동": r"추가 턴|추가 발동",
    "도발/방어지원": r"〈수호〉|피해 분담|수호",  # 탱커 성향(자신이 피해 대신 받음)
}
# scope 무관 (모든 효과 줄/설명에 적용)
RULES_ANY = {
    "강인도파괴": r"강인도 (?:피해|고정 피해)|강인도가 격파|강인도 파괴",
    # 속성 스택(점화/냉각/도약 등 vs 속성 +1%)은 전 구원자 공통 메커닉이라 태그에서 제외, 직업 대상·대상 속성 조건만
    "속성대상피해": r"vs (?:디펜더|캐스터|스트라이커|어쌔신|레인저|서포터)|대상 속성",
}
# 스킬 d1(설명문) 보조 규칙: (조건: 스킬 tg 가 아군 계열이고 비공격) 에서만
D1_HEAL = r"(?:생명력을 )?회복"
ALLY_TG = {"아군 단일", "아군 전체", "반응 대상(아군)"}
ENEMY_TG = {"적 단일", "적 전체", "반응 대상(적)"}

# 파생 역할 (태그 -> 역할). 하나라도 있으면 부여
DERIVED_ROLES = {
    "힐러": ["힐"],
    "버퍼": ["아군공격력증가", "속도증가", "치명증가", "피해증가"],
    "디버퍼": ["적방어력감소", "디버프부여"],
    "탱커/가드": ["도발/방어지원", "보호막"],
}
# 확실도: 태그별 판정 신뢰(리뷰 문서에 표기). strong=구조화 효과줄 근거, weak=정규식 추정
WEAK_TAGS = {"디버프부여", "도발/방어지원", "피해증가", "자가생존"}
# ----------------------------------------------------------------------------------

TIMING_RE = re.compile(r"^\[[^\]]*\]\s*")
COND_RE = re.compile(r"\(조건:(?:[^\[\)]|\[[^\]]*\])*\)\s*")
HP_RE = re.compile(r"^\(자신 HP[^)]*\)\s*")
NAME_RE = re.compile(r"〈([^〉]+)〉")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def norm_line(e):
    e = TIMING_RE.sub("", e)
    e = COND_RE.sub("", e)
    e = HP_RE.sub("", e)
    return e.strip()


def scope_of(line, tg, kind):
    """효과 줄 머리말로 self/ally/enemy 판정. kind=사전 분류(강화/약화/None)."""
    if line.startswith("자신 제외 아군") or line.startswith("아군"):
        return "ally"
    if line.startswith("적"):
        return "enemy"
    if line.startswith("스킬 대상"):
        if tg in ALLY_TG:
            return "ally"
        if tg in ENEMY_TG:
            return "enemy"
        if tg == "자신":
            return "self"
        return "enemy" if kind == "약화" else "ally"   # tg '-' (패시브): 약화면 적, 아니면 아군 추정
    return "self"


def classify_unit(u, eff_desc):
    tags = defaultdict(list)   # tag -> [근거 스킬명]
    notes = []                 # 애매한 판정 메모
    prim = {"특수기": None, "궁극기": None}

    def add(tag, skill, why=""):
        if skill not in tags[tag]:
            tags[tag].append(skill)

    for s in u["sk"]:
        sname = s["n"]
        tg = s.get("tg", "-")
        # 광역/단일 (특수기/궁극기 기준)
        if s.get("act") == "공격" and s["sl"] in ("특수기", "궁극기", "변형 특수기", "변형 궁극기"):
            prim_key = "광역" if tg == "적 전체" else ("단일" if tg == "적 단일" else None)
            if prim_key:
                add(prim_key, sname)
        # 효과 줄 분석
        for e in s.get("ef", []):
            line = norm_line(e)
            names = NAME_RE.findall(line)
            desc = " ".join(eff_desc.get(n, ("", ""))[1] for n in names)
            kind = next((eff_desc[n][0] for n in names if n in eff_desc), None)
            if kind and kind.startswith("속성 스택"):
                desc = ""   # 속성 스택 사전 설명(주는 피해량 +1%)은 딜포터가 아님
            text = line + " " + desc
            sc = scope_of(line, tg, kind)
            rules = {"ally": RULES_ALLY, "enemy": RULES_ENEMY, "self": RULES_SELF}[sc]
            # 강화 줄인데 적 scope, 약화 줄인데 아군 scope 이면 메모
            if kind == "무작위 효과":
                notes.append(f"{sname}: 무작위 효과 포함(확정 아님) {line[:50]}")
            if sc == "enemy" and kind == "강화":
                notes.append(f"{sname}: 적 대상 강화효과? {line[:60]}")
            for tag, rx in rules.items():
                if tag == "디버프부여" and sc == "enemy":
                    # 해제/증가 줄을 디버프로 오인하지 않도록
                    if re.search(r"해제", line) and not re.search(r"〈", line.replace("〈버프 해제〉", "")):
                        continue
                    if kind == "강화":
                        continue
                if re.search(rx, text):
                    # 아군 scope 에서 힐 규칙: '받는 회복량' 만 있는 보정 줄도 힐 보조로 인정
                    add(tag, sname)
            for tag, rx in RULES_ANY.items():
                if re.search(rx, text):
                    add(tag, sname)
            # 자신 제외 아군 속도(행동게이지) 등은 위 ally 규칙에서 처리됨
        # 설명문 보조: 아군 대상 비공격 스킬의 회복 서술
        if tg in ALLY_TG and s.get("act") == "비공격" and re.search(D1_HEAL, s.get("d1", "")):
            add("힐", sname)
        if tg == "자신" and re.search(D1_HEAL, s.get("d1", "")):
            add("자가생존", sname)
        # 공격 스킬 d1 에 강인도
        if "강인도" in s.get("d1", ""):
            add("강인도파괴", sname)
    # 아군 쿨감은 ally scope 에서만 잡히므로 구분 메모 생략
    # 파생 역할
    derived = [r for r, ts in DERIVED_ROLES.items() if any(t in tags for t in ts)]
    # 단일/광역 정리: 광역이 하나라도 있으면 단일 태그는 둘 다 보존(혼합형)
    return tags, derived, notes


def main():
    d = load(MAIN)
    reco = load(RECO)["saviors"]
    eff_desc = {x["n"]: (x["k"], x["d"]) for x in d["dict"]["eff"]}
    reco_by = defaultdict(list)
    for r in reco:
        reco_by[(r["name"], r["subtitle"])].append(r)

    results, unmatched_units, used = [], [], set()
    for u in d["units"]:
        name, sub = u["n"], u["ti"]
        rs = reco_by.get((name, sub), [])
        variant = u.get("v", "기본")
        key = None
        if rs and variant == "기본":
            key = rs[0]["key"]
            used.add(key)
        elif rs and variant != "기본":
            key = rs[0]["key"] + "@" + variant
            used.add(rs[0]["key"])   # 기본형이 안 잡히는 경우 대비
        else:
            unmatched_units.append(f"{name} 「{sub}」 [{variant}] id={u['id']}")
            # reco(가이드 구원자 목록)에 없는 유닛: 키가 None 이면 이후 단계(쌍·빠른 계산)가 죽으므로 id<번호> 로 이어 간다.
            # 이 보고(unmatched_units)가 나오면 savior_reco.json 을 갱신할 것(docs/PORTING.md)
            key = "id%s" % u["id"] if variant == "기본" else "id%s@%s" % (u["id"], variant)
        tags, derived, notes = classify_unit(u, eff_desc)
        order = ["힐", "보호막", "아군공격력증가", "속도증가", "치명증가", "피해증가", "적방어력감소", "디버프부여",
                 "해제", "부활", "도발/방어지원", "광역", "단일", "강인도파괴", "속성대상피해", "쿨타임감소",
                 "추가턴/연속행동", "자가생존", "적버프해제", "적행동게이지감소"]
        tl = [t for t in order if t in tags] + [t for t in tags if t not in order]
        results.append({
            "key": key, "name": name, "subtitle": sub, "variant": variant, "id": u["id"],
            "roles": [u["r"]] + derived, "class": u["r"], "attribute": u["a"],
            "tags": tl, "evidence": {t: tags[t] for t in tl}, "notes": notes,
        })
    unmatched_reco = [f"{r['key']} ({r['name']} 「{r['subtitle']}」)" for r in reco if r["key"] not in used]

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with atomic_open(OUT_JSON) as f:
        json.dump({"unmatched_units": unmatched_units, "unmatched_reco": unmatched_reco,
                   "saviors": results}, f, ensure_ascii=False, indent=1)
        f.write("\n")

    # ---- 리뷰 문서
    cnt = Counter(t for r in results for t in r["tags"])
    L = ["# 시너지 태그 리뷰 (자동 생성)", "",
         f"구원자 {len(results)}건 (reco 매칭 실패 유닛 {len(unmatched_units)}, reco 미사용 {len(unmatched_reco)})", "",
         "## 태그별 구원자 수", "", "| 태그 | 수 | 신뢰 |", "|---|---|---|"]
    for t, c in cnt.most_common():
        L.append(f"| {t} | {c} | {'추정' if t in WEAK_TAGS else '효과줄 근거'} |")
    L += ["", "## 구원자별 태그", "", "| key | 이름 | 직업 | 파생역할 | 태그 |", "|---|---|---|---|---|"]
    for r in results:
        nm = r["name"] + (" (" + r["variant"] + ")" if r["variant"] != "기본" else "") + f" 「{r['subtitle']}」"
        L.append(f"| {r['key']} | {nm} | {r['class']} | {','.join(r['roles'][1:])} | {', '.join(r['tags'])} |")
    L += ["", "## 애매한 판정 / 메모", ""]
    any_note = False
    for r in results:
        for n in r["notes"]:
            L.append(f"- {r['name']}: {n}")
            any_note = True
    # 추정 태그 근거 목록(사람 검토용)
    L += ["", "## 추정 태그 근거 (디버프부여/도발방어지원/피해증가/자가생존)", ""]
    for r in results:
        for t in WEAK_TAGS:
            if t in r["evidence"]:
                L.append(f"- {r['name']} 「{r['subtitle']}」 {t}: {', '.join(r['evidence'][t])}")
    L += ["", "## 매칭 실패", "", "units 에서 reco 를 못 찾음:"] + [f"- {x}" for x in unmatched_units]
    L += ["", "reco 에서 units 를 못 찾음:"] + [f"- {x}" for x in unmatched_reco]
    with atomic_open(OUT_MD) as f:
        f.write("\n".join(L) + "\n")

    print("units", len(results), "unmatched_units", len(unmatched_units), "unmatched_reco", len(unmatched_reco))
    for t, c in cnt.most_common():
        print(f"{c:3d} {t}")


if __name__ == "__main__":
    main()
