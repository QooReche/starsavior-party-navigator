# -*- coding: utf-8 -*-
"""예선 1차 판 재사용 시험 — 나눠 돌려 합친 요약(8판 + run_offset 8 의 24판) == 처음부터 한 번에 돌린 32판.

화면은 1차(8판) 결과의 raw(판별 원시값 문자열)를 보관했다가 2차 요청에 merge_raw 로 되돌려 주고, 작업자는 24판만 더 돌려
battlesim/web.py merge_summary 로 합친다. 순위에 쓰는 값(clear·t60·prog·ttk)과 함께 나가는 값(ta·wipe·timeout·ci·progs·n)이
한 번에 돌린 것과 글자 그대로 같아야 한다(반올림·합 순서 포함).

사용: python -X utf8 -I tests/screen_merge_test.py
일부러 깨뜨려 보기(각각 이 시험이 실패해야 함):
  - web.merge_summary 의 prog 를 round(sum(prog) / n, 3) 으로, 또는 clear 를 올림으로 바꾼다
  - web.run_auto 에서 raw = (prior or []) + ... 의 prior 를 빼먹는다
  - api._simulate 의 raw_runs.append 에서 처치 턴을 round(…, 3) 으로 바꾼다
시험 안의 대조군: 판 번호를 안 밀고(run_offset 0) 합치면 달라져야 한다 — 같으면 이 시험이 아무것도 못 잡는다는 뜻."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from battlesim import web  # noqa: E402

# 화면 예선과 같은 옵션(rng_streams), 재점화·N턴 이내 클리어(t60)도 섞는다
STAGES = [('op/아가논 시가지/SECTOR 36-36', '아가논 시가지|SECTOR 36-36', {}),
          ('op/해식 동굴/SECTOR 41-36', '해식 동굴|SECTOR 41-36', {'star_turns': 60}),
          ('op/레이븐 월/SECTOR 31-36', '레이븐 월|SECTOR 31-36', {'rekindle': 3}),
          ('op/NOA 상업지구/SECTOR 1-3', 'NOA 상업지구|SECTOR 1-3', {'star_turns': 30})]
KEYS = ('clear', 't60', 'prog', 'ttk', 'ta', 'wipe', 'timeout', 'ci', 'n', 'progs')
FIRST, FULL = 8, 32


def teams(q):
    ks = sorted(q['sv'])
    return [['emily', 'fei', 'professor-m', 'wedding-carmen'], ks[0:4], ks[9:13], ks[20:24]]


def cases():
    import gen_quick_calib as G
    from battlesim import quick
    q, _ = quick.load(ROOT)
    for stage, sk, extra in STAGES:
        st = q['st']['op'][sk]
        for order in teams(q):
            opt = dict({'build': 'standard', 'rng_streams': True, 'rules_override': {'power_penalty': 'model'}}, **extra)
            yield stage, G.party_spec(q, order, order[1], order, 1.0, st), opt


def run(stage, party, n, opt):
    return json.loads(web.run_auto(stage, party, n, 1, json.dumps(opt)))


def pick(r):
    return {k: r[k] for k in KEYS}


def test_merged_equals_direct():
    """8판 + (run_offset 8 의 24판, merge_raw) 요약 == 32판 한 번. raw(판별 원시값)도 같다."""
    bad, mixed, zero, star, sensitive, n = [], 0, 0, 0, 0, 0
    for stage, party, opt in cases():
        n += 1
        direct = run(stage, party, FULL, opt)
        first = run(stage, party, FIRST, dict(opt, raw_runs=True))
        merged = run(stage, party, FULL - FIRST, dict(opt, run_offset=FIRST, merge_raw=first['raw']))
        raw_direct = run(stage, party, FULL, dict(opt, raw_runs=True))
        if pick(merged) != pick(direct) or merged['raw'] != raw_direct['raw'] or merged['merged'] != [FIRST, FULL - FIRST] or pick(raw_direct) != pick(direct):
            bad.append((stage, [u['key'] for u in party['units']], pick(merged), pick(direct)))
        # 1차 결과 자체는 raw 를 달라고 해도 그대로여야 한다(8판끼리 비교 규칙이 쓰는 값)
        if pick(first) != pick(run(stage, party, FIRST, opt)):
            bad.append((stage, 'first changed by raw_runs'))
        mixed += 0 < direct['clear'] < 1
        zero += direct['clear'] == 0
        star += direct['t60'] is not None and 0 < direct['t60']
        # 대조군: 판 번호를 안 밀면(앞 8판을 또 돌림) 합친 값이 달라져야 한다
        again = json.loads(run(stage, party, FULL - FIRST, dict(opt, raw_runs=True))['raw'])
        wrong = web.merge_summary(json.loads(first['raw']) + again, opt.get('star_turns'))
        sensitive += {k: wrong[k] for k in KEYS} != pick(direct)
    ok = not bad and mixed >= 2 and zero >= 1 and star >= 1 and sensitive >= n // 2
    return ok, '%d건 중 다름 %d / 클리어율이 0~1 사이 %d건·0%% %d건·t60>0 %d건 / 대조군(판 번호 안 밂)이 달라진 건 %d %s' % (n, len(bad), mixed, zero, star, sensitive, bad[:1])


def test_merge_guard():
    """merge_raw 의 판 수와 run_offset 이 다르면 거부(조용히 틀린 합을 내지 않음), 수동 진입점은 merge_raw 를 무시"""
    stage, party, opt = next(iter(cases()))
    first = run(stage, party, 4, dict(opt, raw_runs=True))
    try:
        run(stage, party, 4, dict(opt, run_offset=8, merge_raw=first['raw']))
        refused = False
    except ValueError:
        refused = True
    man = json.loads(web.run_manual(stage, party, 3, 1, json.dumps(dict(opt, merge_raw=first['raw']))))
    return refused and man['n'] == 3, '판 수 불일치 거부 %s / 수동 %d판' % (refused, man['n'])


TESTS = [test_merged_equals_direct, test_merge_guard]


def main():
    fail = 0
    for t in TESTS:
        ok, msg = t()
        print('%s %s - %s' % ('PASS' if ok else 'FAIL', t.__name__, msg))
        fail += not ok
    print('ALL', 'OK' if not fail else 'FAILED')
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
