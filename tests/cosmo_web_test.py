# -*- coding: utf-8 -*-
"""코스모 3보스 편성 찾기의 파이썬 쪽 시험: battlesim/web.py run_auto 의 options.cosmo_raid 분기와 점수 요약(cosmo_summary).
실행: python -X utf8 -I tests/cosmo_web_test.py"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim import simulate                                   # noqa: E402
from battlesim import web                                        # noqa: E402

UNITS = ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria']
PARTY = {'units': [{'key': k} for k in UNITS], 'leader': 0}
BOSSES = ('belgras', 'tyria', 'carnelia')


def auto(boss, level, n=8, seed=3, **extra):
    o = {'build': 'standard', 'cosmo_raid': {'boss': boss, 'step': 3, 'level': level}}
    o.update(extra)
    return json.loads(web.run_auto('ignored/stage/name', PARTY, n, seed, json.dumps(o)))


def test_summary_rounding_and_top():
    """사사오입(JS Math.round 와 같게): 짝수 반올림이면 2.5 -> 2 가 되어 틀림. 상위 = 상위 topQ 비율(올림) 판 평균"""
    cr = lambda sc, cl=None, fr=None: dict(score_runs=sc, clear_runs=cl or [False] * len(sc), damage_frac_runs=fr or [0.5] * len(sc))
    s = web.cosmo_summary(cr([2, 3]))
    assert s['mean'] == 3 and s['top'] == 3 and s['n'] == 2, s            # 평균 2.5 -> 3, 상위 1판(올림) = 3
    s = web.cosmo_summary(cr([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), 0.2)
    assert s['mean'] == 6 and s['top'] == 10, s                            # 평균 5.5 -> 6, 상위 2판 평균 9.5 -> 10
    s = web.cosmo_summary(cr([10, 0, 0, 0, 0]), 0.2)
    assert s['top'] == 10 and s['mean'] == 2, s                            # 5판의 20% = 정확히 1판(부동소수 오차로 2판이 되면 안 됨)
    s = web.cosmo_summary(cr([4], [True], [1.0]))
    assert s['clear'] == 1.0 and s['frac'] == 1.0 and s['mean'] == 4 and s['top'] == 4
    s = web.cosmo_summary(cr([1, 2, 3, 4], [True, False, True, False], [1.0, 0.25, 1.0, 0.5]), 0.5)
    assert s['clear'] == 0.5 and s['frac'] == 0.6875 and s['top'] == 4, s  # 상위 2판 = (4+3)/2 = 3.5 -> 4


def test_run_auto_cosmo_branch():
    """options.cosmo_raid 가 전투를 코스모 시즌 전투로 바꾸고, 작업자 결과에는 요약만 실린다(판별 배열 금지)"""
    for boss in BOSSES:
        r = auto(boss, 0)
        c = r['cosmo']
        assert set(c) == {'mean', 'top', 'clear', 'frac', 'n'} and c['n'] == 8, c
        assert c['mean'] > 0 and 0 <= c['clear'] <= 1 and 0 < c['frac'] <= 1, (boss, c)    # 점수·깎은 비율이 실제로 나옴(진행도 0 이 아님)
        assert c['top'] >= c['mean']
        assert not any(isinstance(v, list) and len(v) >= 8 for v in c.values()), '판별 배열이 요약에 실리면 안 됨'
        assert 'score_runs' not in r and 'damage_frac_runs' not in r
        # simulate 직접 호출과 같은 값(같은 시드·같은 옵션)
        d = simulate(PARTY, {'cosmo_raid': {'boss': boss, 'step': 3, 'level': 0}}, {'build': 'standard', 'n_runs': 8, 'seed': 3})
        assert c == web.cosmo_summary(d['cosmo_raid']), boss
        assert abs(r['clear'] - d['outcome']['clear_p']) < 1e-9


def test_run_auto_level_and_top_q():
    lo, hi = auto('티리아', 0)['cosmo'], auto('티리아', 18)['cosmo']
    assert lo != hi and hi['frac'] < lo['frac'], (lo, hi)                  # 난이도 레벨이 실제로 전투에 반영됨(능력치 배율·챌린지)
    a, b = auto('벨그라스', 0, n=10, cosmo_top_q=0.2)['cosmo'], auto('벨그라스', 0, n=10, cosmo_top_q=1.0)['cosmo']
    assert a['mean'] == b['mean'] and b['top'] == b['mean'] and a['top'] >= b['top'], (a, b)   # top_q=1 이면 상위 = 평균
    assert auto('벨그라스', 0, n=10, cosmo_top_q=0.2)['cosmo'] == a        # 같은 시드 = 같은 결과


def test_other_encounters_unchanged():
    """코스모가 아닌 호출에는 cosmo 키가 없고 기존 스테이지 경로가 그대로"""
    r = json.loads(web.run_auto('clo/달 회랑/FLOOR 100', PARTY, 4, 1, json.dumps({'build': 'standard'})))
    assert 'cosmo' not in r and r['n'] == 4
    o = {'cosmo_raid': {'boss': 'tyria', 'step': 3, 'level': 0}, 'build': 'standard'}
    assert web._enc('s/t/n', dict(o)) == {'cosmo_raid': {'boss': 'tyria', 'step': 3, 'level': 0}}
    assert web._enc('s/t/n', {'build': 'standard'}) == {'stage': 's/t/n'}
    assert web._enc('s/t/n', {'guild': {'level': 1}, 'cosmo_raid': {'boss': 'tyria'}}) == {'guild': {'level': 1}}


TESTS = [test_summary_rounding_and_top, test_run_auto_cosmo_branch, test_run_auto_level_and_top_q, test_other_encounters_unchanged]

if __name__ == '__main__':
    fail = 0
    for t in TESTS:
        try:
            t()
            print('ok  ', t.__name__)
        except Exception as ex:
            import traceback
            fail += 1
            print('FAIL', t.__name__, ex)
            traceback.print_exc()
    if fail:
        print('FAILED', fail)
        sys.exit(1)
    print('PASS cosmo_web_test', len(TESTS))
