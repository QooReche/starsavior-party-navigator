# -*- coding: utf-8 -*-
"""웨이브 전환 아군 게이지 규칙 wave_ally_gauge: 기본 reset(클라: 전환 시 아군 게이지 0), keep(옛 이월). 실행: python -X utf8 -I tests/wave_gauge_test.py"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim import simulate                                   # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402

PARTY = ['sunshine-cat-smile', 'cristelle', 'white-pearl-luna', 'wedding-carmen']


def test_default_is_reset():
    assert MC_OPTS['wave_ally_gauge'] == 'reset'


def test_both_modes_run():
    out = {}
    for mode in ('keep', 'reset'):
        r = simulate(PARTY, {'stage': 'clo/태양 회랑/FLOOR 250'}, {'seed': 3, 'n_runs': 6, 'build': 'standard',
                                                                   'rules_override': {'wave_ally_gauge': mode, 'wave_extra_turn': 'keep'}})
        out[mode] = (r['outcome']['clear_p'], r['outcome']['progress'])
        assert 0 < out[mode][1] <= 1, out   # 진행도 0 이면 웨이브 전환이 안 일어나 아무것도 검증 못 함(옛 43-36 은 standard 로 0)
    print('  ', out)


def test_reset_zeroes_ally_gauge_on_wave_change():
    """reset 이면 웨이브 전환 직후 생존 아군 게이지가 0, keep 이면 이월 — spawn_wave 를 직접 엿봄(웨이브 전환이 실제로 일어나야 통과)"""
    import battlesim.mc as mc
    seen = {}
    orig = mc.Battle.spawn_wave

    def spy(self, *a, **kw):
        out = orig(self, *a, **kw)
        if self.wave_i > 0:
            seen.setdefault(self.mc['wave_ally_gauge'], []).append(max(u.gauge for u in self.alive(0)) if self.alive(0) else 0)
        return out
    mc.Battle.spawn_wave = spy
    try:
        for mode in ('keep', 'reset'):
            simulate(PARTY, {'stage': 'clo/태양 회랑/FLOOR 250'}, {'seed': 3, 'n_runs': 4, 'build': 'standard',
                                                                  'rules_override': {'wave_ally_gauge': mode, 'wave_extra_turn': 'keep'}})
    finally:
        mc.Battle.spawn_wave = orig
    assert seen.get('reset') and seen.get('keep'), seen
    assert all(g == 0 for g in seen['reset']), seen['reset']
    assert any(g > 0 for g in seen['keep']), seen['keep']


TESTS = [test_default_is_reset, test_both_modes_run, test_reset_zeroes_ally_gauge_on_wave_change]

if __name__ == '__main__':
    for t in TESTS:
        t()
        print('OK', t.__name__)
    print('ALL OK', len(TESTS))
