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


def test_default_is_nested():
    assert MC_OPTS['enforce_timing'] == 'nested'


def test_both_modes_run():
    out = {}
    for mode in ('nested', 'queue'):
        r = simulate(PARTY, {'stage': 'op/전초 기지/SECTOR 43-36'}, {'seed': 3, 'n_runs': 6, 'build': 'standard',
                                                                    'rules_override': {'enforce_timing': mode}})
        out[mode] = (r['outcome']['clear_p'], r['outcome']['progress'])
        assert r['unsupported'].get('gate_ok', True)
    assert all(0 <= v[1] <= 1 for v in out.values()), out
    print('  ', out)


TESTS = [test_default_is_nested, test_both_modes_run]

if __name__ == '__main__':
    for t in TESTS:
        t()
        print('OK', t.__name__)
    print('ALL OK', len(TESTS))
