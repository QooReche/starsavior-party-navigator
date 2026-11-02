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
        r = simulate(PARTY, {'stage': 'op/전초 기지/SECTOR 43-36'}, {'seed': 3, 'n_runs': 6, 'build': 'standard',
                                                                    'rules_override': {'wave_ally_gauge': mode}})
        out[mode] = (r['outcome']['clear_p'], r['outcome']['progress'])
        assert 0 <= out[mode][1] <= 1
    print('  ', out)


TESTS = [test_default_is_reset, test_both_modes_run]

if __name__ == '__main__':
    for t in TESTS:
        t()
        print('OK', t.__name__)
    print('ALL OK', len(TESTS))
