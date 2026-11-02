# -*- coding: utf-8 -*-
"""추가 발동 시점 규칙 enforce_timing: 기본 nested(옛 동작)와 queue(클라 예약 큐 순서) 모두 돌아가고, 기본값은 nested.
영상 검증 전이라 기본값은 바꾸지 않는다(work/common_rules/notes_enforce_queue.md). 실행: python -X utf8 -I tests/enforce_timing_test.py"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim import simulate                                   # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402

PARTY = ['sunshine-cat-smile', 'cristelle', 'white-pearl-luna', 'wedding-carmen']


def test_default_is_queue():
    assert MC_OPTS['enforce_timing'] == 'queue'


def test_both_modes_run():
    out = {}
    for mode in ('nested', 'queue'):
        r = simulate(PARTY, {'stage': 'clo/달 회랑/FLOOR 100'}, {'seed': 3, 'n_runs': 6, 'build': 'standard',
                                                                    'rules_override': {'enforce_timing': mode}})
        out[mode] = (r['outcome']['clear_p'], r['outcome']['progress'])
        assert r['unsupported'].get('gate_ok', True)
    assert all(0 < v[1] <= 1 for v in out.values()), out   # 진행도 0 이면 아무것도 검증 못 함(옛 스테이지 43-36 은 standard 로 0)
    print('  ', out)


def test_enforce_target_default_exec():
    assert MC_OPTS['enforce_target'] == 'exec'


ST_EXTRA = {'stage': 'clo/달 회랑/FLOOR 100'}     # 추가 발동이 실제로 나가는 스테이지(진행도 0 인 곳은 아무것도 못 봄)
PARTY_EXTRA = ['gwen', 'sunshine-cat-smile', 'cristelle', 'hilde']


def test_enforce_target_modes_run():
    """exec/book 둘 다 돌고, nested 에선 두 값이 같은 결과(차이는 queue 에서만)."""
    res = {}
    for timing in ('queue', 'nested'):
        for tgt in ('exec', 'book'):
            r = simulate(PARTY_EXTRA, ST_EXTRA, {'seed': 5, 'n_runs': 6, 'build': 'standard',
                                                 'rules_override': {'enforce_timing': timing, 'enforce_target': tgt}})
            assert r['unsupported'].get('gate_ok', True)
            res[(timing, tgt)] = (r['outcome']['clear_p'], r['outcome']['progress'])
    assert res[('nested', 'exec')] == res[('nested', 'book')], res
    assert res[('queue', 'exec')][1] > 0, res
    print('  ', res)


def test_exec_pick_retargets_dead():
    """exec 이면 예약 실행 때 대상을 다시 고른다: 추가 발동이 실제로 나가고, 대상 없이(None) 시전하지 않음."""
    import battlesim.mc as mc
    seen = []
    orig = mc.Battle.cast

    def spy(self, actor, sk, *a, **kw):
        if kw.get('extra') and kw.get('via') in ('enforce', 'potential', None):
            seen.append(kw.get('target'))
        return orig(self, actor, sk, *a, **kw)
    mc.Battle.cast = spy
    try:
        simulate(PARTY_EXTRA, ST_EXTRA, {'seed': 2, 'n_runs': 4, 'build': 'standard',
                                         'rules_override': {'enforce_target': 'exec'}})
    finally:
        mc.Battle.cast = orig
    assert seen, '추가 발동이 한 번도 안 나감 — 시험이 아무것도 검증 못 함'
    assert all(t is not None for t in seen), seen


def test_exec_defers_unbound_picker():
    """exec 이면 예약되는 추가 발동 함수가 대상을 묶지 않고 실행 때 고른다(함수 안에서 pool 계산), book 이면 그런 함수가 없다.
    _exec_pick 을 꺼 버리면 exec 쪽 단언이 실패한다(기능 제거 검출)."""
    import battlesim.mc as mc
    got = {}
    orig = mc.Battle._defer_extra

    def spy(self, fn, key=None):
        names = getattr(getattr(fn, '__code__', None), 'co_varnames', ())
        got.setdefault(self.mc['enforce_target'], []).append('pool' in names)
        return orig(self, fn, key)
    mc.Battle._defer_extra = spy
    try:
        for t in ('exec', 'book'):
            simulate(PARTY_EXTRA, ST_EXTRA, {'seed': 2, 'n_runs': 4, 'build': 'standard', 'rules_override': {'enforce_target': t}})
    finally:
        mc.Battle._defer_extra = orig
    assert got.get('exec') and any(got['exec']), got
    assert not any(got.get('book', [])), got


TESTS = [test_exec_defers_unbound_picker, test_default_is_queue, test_both_modes_run, test_enforce_target_default_exec, test_enforce_target_modes_run,
         test_exec_pick_retargets_dead]

if __name__ == '__main__':
    for t in TESTS:
        t()
        print('OK', t.__name__)
    print('ALL OK', len(TESTS))
