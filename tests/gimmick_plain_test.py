"""스테이지 기믹 박스 쉬운 말 사전(data/gimmick_plain.json) 누락 검사.

사전에 없는 기믹 코드, 대처 슬롯 이름, GFIX 성향 대응 문구가 생기면 실패한다.
실행: python -X utf8 -I tests/gimmick_plain_test.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


rules = json.loads(load("data", "gimmick_rules.json"))["types"]
plain = json.loads(load("data", "gimmick_plain.json"))
tpl = load("party_template.html")
fails = []

for code in rules:
    e = plain["gimmicks"].get(code)
    if not e or not e.get("name") or not e.get("what"):
        fails.append("기믹 사전 누락: " + code)
    elif not e["what"].endswith((".", ")")):
        fails.append("기믹 설명이 문장으로 끝나지 않음: " + code)
extra = set(plain["gimmicks"]) - set(rules)
if extra:
    fails.append("사전에만 있는 기믹: %s" % sorted(extra))

slot_names = {s["name"] for r in rules.values() for s in r["slots"]}
for n in sorted(slot_names):
    e = plain["fixes"].get(n)
    if not e or not e.get("name") or not e.get("tip"):
        fails.append("대처(슬롯) 사전 누락: " + n)

for tag in sorted({a for r in rules.values() for a in r.get("avoid", [])}):
    e = plain.get("avoid", {}).get(tag)
    if not e or not e.get("name") or not e.get("why"):
        fails.append("불리한 구원자(avoid 태그) 사전 누락: " + tag)

m = re.search(r"const GFIX=\{(.*?)\n\};", tpl, re.S)
if not m:
    fails.append("party_template.html 에서 GFIX 를 찾지 못함")
else:
    vals = {v.replace("*", "") for v in re.findall(r':"([^"]+)"', m.group(1))}
    vals.discard("대응 미확인")  # 화면에 나오지 않는 줄
    for v in sorted(vals):
        e = plain["gfix"].get(v)
        if not e or not e.get("name") or not e.get("tip"):
            fails.append("GFIX 사전 누락: " + v)
    gcodes = set(re.findall(r"(\w+):\"", m.group(1)))
    for c in rules:
        if not rules[c]["slots"] and c not in gcodes:
            fails.append("슬롯도 GFIX 도 없는 기믹: " + c)

# 같은 보스 스킬에서 나온 기믹(강화 해제 + 강화 불가)은 추천 점수·상위 목록에 한 번만 들어간다(party_contents.json gimmick.sameSource)
import json as _json
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _ROOT)
import party_reco as _pr
from tools.build_gimmicks import TYPES, SLOT_RULES

# 클라로 확인한 표시 판정이 재생성 때 다시 추정으로 돌아가지 않게 원본과 대조.
for _code in ("STEALTH", "SKILL_NULLIFY"):
    if rules[_code]["conf"] != "확인" or TYPES[_code]["impact_conf"] != "확인":
        fails.append("확인된 대처가 추정으로 돌아감: " + _code)
    for _field in ("good", "bad"):
        if rules[_code][_field] != SLOT_RULES[_code][_field]:
            fails.append("빌더와 공개 문구 불일치: " + _code + "/" + _field)

_cfg = _json.load(open(os.path.join(_ROOT, "party_contents.json"), encoding="utf-8"))
_both = [k for k, v in _pr._json(_pr.GSTAGE).items() if "BUFF_STRIP" in v and "BUFF_BAN" in v]
if not _both:
    fails.append("강화 해제·강화 불가가 함께 붙은 스테이지가 없음(시험 전제)")
for _k in _both:
    _codes = [c for c, _ in _pr.stage_gimmicks(_k, _cfg)]
    if ("BUFF_STRIP" in _codes) == ("BUFF_BAN" in _codes) or "BUFF_BAN" not in _codes:
        fails.append("같은 출처 기믹이 한 번만 세어지지 않음: %s %s" % (_k, _codes))
_c2 = _json.loads(_json.dumps(_cfg))
_c2["gimmick"]["sameSource"] = []
if _both and not all({"BUFF_STRIP", "BUFF_BAN"} <= {c for c, _ in _pr.stage_gimmicks(k, _c2)} for k in _both):
    fails.append("sameSource 를 비우면 둘 다 세어져야 함")

if fails:
    print("\n".join(fails))
    sys.exit(1)
print("OK 기믹 %d · 대처 %d · 성향 %d" % (len(plain["gimmicks"]), len(plain["fixes"]), len(plain["gfix"])))
