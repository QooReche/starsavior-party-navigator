# -*- coding: utf-8 -*-
"""codex 지적 재현: 옛 진입점(sim_damage)에서 상태·상수를 바꾸면 실제 엔진에 반영되는가."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import sim_damage as sd
import battlesim.starsavior.data as data
import battlesim.metrics as metrics
import battlesim.engine as engine

ok = True
def check(name, cond):
    global ok
    print(("PASS" if cond else "FAIL"), name)
    ok = ok and cond

# 1) _DB 실시간 읽기
db = sd.get_db()
check("get_db 후 sd._DB 가 실제 DB", sd._DB is db and data._DB is db)
# 2) _DB 재할당이 get_db 에 반영
sd._DB = None
check("sd._DB=None 이 실제 모듈에 반영", data._DB is None)
db2 = sd.get_db()
check("다시 읽으면 새 DB", db2 is not db and sd._DB is db2)
# 3) _CACHE 재할당 반영
sd._CACHE = {}
check("sd._CACHE 재할당이 metrics 에 반영", metrics._CACHE is sd._CACHE)
# 4) 상수 교체가 엔진에 반영 (그웬 피해가 0)
base = sd.unit_metrics("gwen", 10, None, 0)["single_dpt"]
sd.BASE_MULT = 0
sd._CACHE = {}
zero = sd.unit_metrics("gwen", 10, None, 0)["single_dpt"]
check("sd.BASE_MULT=0 -> 엔진 상수도 0", engine.BASE_MULT == 0)
check("그웬 단일 피해가 줄어듦 (%.0f -> %.0f)" % (base, zero), zero < base * 0.5)
sd.BASE_MULT = 1.85
sd._CACHE = {}
again = sd.unit_metrics("gwen", 10, None, 0)["single_dpt"]
check("되돌리면 원래 값 (%.3f)" % again, abs(again - base) < 1e-9)
# 5) 함수 교체 전달 (unit_def 를 감싸면 metrics 쪽도 바뀜)
orig = sd.unit_def
calls = []
def wrapped(*a, **k):
    calls.append(1)
    return orig(*a, **k)
sd.unit_def = wrapped
sd._CACHE = {}
sd.simulate_party(["gwen", "amora", "fei", "professor-m"], None, 10, None, 0)
check("sd.unit_def 교체가 metrics 내부 호출에 반영", len(calls) > 0)
sd.unit_def = orig
check("원복", metrics.unit_def is orig)
print("ALL", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
