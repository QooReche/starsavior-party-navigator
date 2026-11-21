# -*- coding: utf-8 -*-
"""추가 발동 시점: 클라 예약 큐 순서(옛 스위치 enforce_timing·enforce_target 은 엔진 다이어트 4단계에서 지움 — 항상 queue·exec).
실행: python -X utf8 -I tests/enforce_timing_test.py"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim import simulate                                   # noqa: E402

PARTY = ['sunshine-cat-smile', 'cristelle', 'white-pearl-luna', 'wedding-carmen']


def test_default_runs():
    r = simulate(PARTY, {'stage': 'clo/달 회랑/FLOOR 100'}, {'seed': 3, 'n_runs': 6, 'build': 'standard'})
    assert r['unsupported'].get('gate_ok', True)
    assert 0 < r['outcome']['progress'] <= 1, r['outcome']   # 진행도 0 이면 아무것도 검증 못 함(옛 스테이지 43-36 은 standard 로 0)
    print('  ', (r['outcome']['clear_p'], r['outcome']['progress']))


ST_EXTRA = {'stage': 'clo/달 회랑/FLOOR 100'}     # 추가 발동이 실제로 나가는 스테이지(진행도 0 인 곳은 아무것도 못 봄)
PARTY_EXTRA = ['gwen', 'sunshine-cat-smile', 'cristelle', 'hilde']


def test_exec_pick_retargets_dead():
    """예약 실행 때 대상을 다시 고른다: 추가 발동이 실제로 나가고, 대상 없이(None) 시전하지 않음."""
    import battlesim.mc as mc
    seen = []
    orig = mc.Battle.cast

    def spy(self, actor, sk, *a, **kw):
        if kw.get('extra') and kw.get('via') in ('enforce', 'potential', None):
            seen.append(kw.get('target'))
        return orig(self, actor, sk, *a, **kw)
    mc.Battle.cast = spy
    try:
        simulate(PARTY_EXTRA, ST_EXTRA, {'seed': 2, 'n_runs': 4, 'build': 'standard'})
    finally:
        mc.Battle.cast = orig
    assert seen, '추가 발동이 한 번도 안 나감 — 시험이 아무것도 검증 못 함'
    assert all(t is not None for t in seen), seen


def test_exec_defers_unbound_picker():
    """예약되는 추가 발동 함수가 대상을 묶지 않고 실행 때 고른다(함수 안에서 pool 계산).
    _exec_pick 을 꺼 버리면 단언이 실패한다(기능 제거 검출)."""
    import battlesim.mc as mc
    got = []
    orig = mc.Battle._defer_extra

    def spy(self, fn, key=None):
        names = getattr(getattr(fn, '__code__', None), 'co_varnames', ())
        got.append('pool' in names)
        return orig(self, fn, key)
    mc.Battle._defer_extra = spy
    try:
        simulate(PARTY_EXTRA, ST_EXTRA, {'seed': 2, 'n_runs': 4, 'build': 'standard'})
    finally:
        mc.Battle._defer_extra = orig
    assert got and any(got), got


TESTS = [test_exec_defers_unbound_picker, test_default_runs, test_exec_pick_retargets_dead]

if __name__ == '__main__':
    for t in TESTS:
        t()
        print('OK', t.__name__)
    print('ALL OK', len(TESTS))
