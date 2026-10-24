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

if fails:
    print("\n".join(fails))
    sys.exit(1)
print("OK 기믹 %d · 대처 %d · 성향 %d" % (len(plain["gimmicks"]), len(plain["fixes"]), len(plain["gfix"])))
