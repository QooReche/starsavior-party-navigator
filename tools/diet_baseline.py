# -*- coding: utf-8 -*-
"""엔진 다이어트 결과 불변 기준선(docs/engine_diet_1122.md) — 콘텐츠별 스테이지 × 대표 파티(표준 육성, 계정 자료 없음) × 시드 3개.

케이스마다 두 진입점의 바이트 해시를 낸다.
  api.simulate(per_run·raw_runs 켬): raw_runs·runs(per_run) 해시, 결과 전체 해시(runtime_ms_per_run 만 뺌)
  web.run_auto(raw_runs 켬): 화면이 받는 JSON 문자열 그대로의 해시
해시 입력은 json.dumps(sort_keys, ensure_ascii=False, 구분자 고정) — 부동소수 repr 까지 같아야 같은 해시.
이후 다이어트 단계(스위치 삭제·log 가드·묶음 경량화)는 모두 tests/golden/diet_baseline.json 과 바이트 일치해야 한다(tests/diet_baseline_test.py).

  python -X utf8 -I tools/diet_baseline.py            # 계산해서 기준선과 비교(불일치 0 이면 종료 코드 0)
  python -X utf8 -I tools/diet_baseline.py --write    # 기준선 다시 쓰기 — 엔진 결과가 «의도적으로» 바뀐 커밋에서만
  python -X utf8 -I tools/diet_baseline.py --json     # 계산 결과를 표준 출력에 JSON 으로(다른 폴더의 엔진으로 돌릴 때: PN_SRC·sys.path 지정)
엔진 위치는 이 파일 기준 저장소가 기본. --engine DIR 이면 DIR/battlesim 을 쓴다(데이터는 PN_SRC 또는 DIR).
"""
import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, 'tests', 'golden', 'diet_baseline.json')

PARTY_A = ['fei', 'professor-m', 'emily', 'wedding-carmen']          # web_test 화면 파티(작전 1-3 권장 파티)
PARTY_B = ['wedding-carmen', 'ceres-sun-supporter', 'amora', 'tyria']  # guild_support_test 길방 파티
# (이름, encounter, 화면 run_auto 의 stage 인자·extra 추가분)
CASES = [
    ('op', {'stage': 'op/NOA 상업지구/SECTOR 1-3'}, 'op/NOA 상업지구/SECTOR 1-3', {}),
    ('clo_moon100', {'stage': 'clo/달 회랑/FLOOR 100'}, 'clo/달 회랑/FLOOR 100', {}),
    ('clo_sun250', {'stage': 'clo/태양 회랑/FLOOR 250'}, 'clo/태양 회랑/FLOOR 250', {}),
    ('cosmo_gille1', {'stage': 'cosmo/길레/길레 1단계'}, 'cosmo/길레/길레 1단계', {}),
    ('cosmo_raid_bask3', {'cosmo_raid': {'boss': 'baskerville', 'step': 3, 'level': 0}}, 'x', {'cosmo_raid': {'boss': 'baskerville', 'step': 3, 'level': 0}}),
    ('guild_l1', {'guild': {'seasonId': 30111, 'level': 1, 'sets': [0, 0, 0, 0], 'support': 'fire'}}, 'x', {'guild': {'seasonId': 30111, 'level': 1, 'sets': [0, 0, 0, 0], 'support': 'fire'}}),
]
PARTIES = [('A', PARTY_A), ('B', PARTY_B)]
SEEDS = [1, 2, 3]
N_RUNS = 8
BASE_OPT = {'build': 'standard', 'rules_override': {'power_penalty': 'model'}}   # 화면(search_executor) 기본 옵션


def _h(x):
    s = x if isinstance(x, str) else json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:20]


def compute(only=None):
    from battlesim.api import simulate
    from battlesim import web
    out = {}
    for name, enc, stage, extra in CASES:
        for pk, units in PARTIES:
            for seed in SEEDS:
                key = '%s/%s/s%d' % (name, pk, seed)
                if only and not any(w in key for w in only):
                    continue
                party = {'units': list(units), 'leader': 0}
                o = dict(BASE_OPT, n_runs=N_RUNS, seed=seed, per_run=True, raw_runs=True)
                r = simulate(party, enc, o)
                full = {k: v for k, v in r.items() if k != 'runtime_ms_per_run'}
                w = web.run_auto(stage, party, N_RUNS, seed, json.dumps(dict(BASE_OPT, raw_runs=True, **extra)))
                out[key] = dict(raw_runs=_h(r['raw_runs']), per_run=_h(r['runs']), result=_h(full), web=_h(w),
                                clear=r['outcome']['clear_p'], prog=r['outcome'].get('progress'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--engine', help='이 폴더의 battlesim 으로 계산')
    ap.add_argument('only', nargs='*')
    a = ap.parse_args()
    if a.write and a.only:
        ap.error('--write 는 전체 케이스로만')
    sys.path.insert(0, a.engine or ROOT)
    got = compute(a.only)
    if a.json:
        print(json.dumps(got, ensure_ascii=False, sort_keys=True))
        return 0
    if a.write:
        doc = dict(_note='엔진 다이어트 결과 불변 기준선(tools/diet_baseline.py --write). 케이스 = 콘텐츠/파티/시드, %d판, 표준 육성, '
                         'rules_override power_penalty=model. 해시 = sha256 앞 20자(raw_runs·runs·결과 전체(runtime 제외)·web.run_auto 문자열)' % N_RUNS,
                   cases=got)
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        with open(GOLDEN, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write('\n')
        print('저장', GOLDEN, len(got), '케이스')
        return 0
    want = json.load(open(GOLDEN, encoding='utf-8'))['cases']
    bad = [k for k in got if got[k] != want.get(k)]
    print('케이스 %d / 불일치 %d %s' % (len(got), len(bad), bad[:5]))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
