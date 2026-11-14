# -*- coding: utf-8 -*-
"""회복·보호막 대체 경로의 «생명력 비율 최저 1명» 동률 처리 mc.heal_tie.
클라 회복 규칙 2(static-data tables/Plain/AUTO_SKILL_TARGET_TEMPLET.json Id 2 = IsLowHpRate → IsLowMaxHp, 그래도 여럿이면 무작위 —
NKM.decompiled.cs 7001-7050). 옛 엔진은 비율이 같으면 앞 칸을 골랐다.
실행: python -X utf8 -I tests/heal_tie_test.py"""
import os
import random
import sys
from collections import Counter, defaultdict
from types import SimpleNamespace as NS

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.mc import Battle                                  # noqa: E402


def _stub(mode, seed=1):
    b = NS(mc={'heal_tie': mode, 'stat_select_int': 'floor'}, rule_hits=defaultdict(int))
    rng = random.Random(seed)
    b.R = lambda side: rng
    b.filter_chain = lambda *a, **k: Battle.filter_chain(b, *a, **k)
    b._filter = lambda *a, **k: Battle._filter(b, *a, **k)
    return b


def _u(name, pos, hp, maxhp):
    return NS(name=name, pos=pos, hp=hp, maxhp=maxhp, side=0, dead=False)


def test_default_client():
    assert MC_OPTS['heal_tie'] == 'client'


def test_lowest_ratio_first():
    a, b, c = _u('a', 0, 50, 100), _u('b', 1, 30, 100), _u('c', 2, 90, 100)
    for mode in ('client', 'slot'):
        assert Battle.heal_order(_stub(mode), a, [a, b, c], 1)[0] is b


def test_tie_lower_maxhp_wins():
    """비율이 같으면 최대 생명력이 낮은 쪽(앞 칸이어도 큰 쪽은 밀림)"""
    big, small = _u('big', 0, 600, 1000), _u('small', 3, 300, 500)
    st = _stub('client')
    assert Battle.heal_order(st, big, [big, small], 1)[0] is small
    assert st.rule_hits['heal_tie'] == 0      # 최대 생명력에서 갈렸으면 무작위 아님
    assert Battle.heal_order(_stub('slot'), big, [big, small], 1)[0] is big   # 옛 동작 = 앞 칸


def test_full_tie_random():
    """비율·최대 생명력이 모두 같으면 무작위(옛 동작은 늘 앞 칸)"""
    a, b = _u('a', 0, 50, 100), _u('b', 2, 50, 100)
    st = _stub('client', seed=7)
    got = Counter(Battle.heal_order(st, a, [a, b], 1)[0].name for _ in range(400))
    assert 120 < got['a'] < 280 and 120 < got['b'] < 280, got
    assert st.rule_hits['heal_tie'] == 400
    assert {Battle.heal_order(_stub('slot'), a, [a, b], 1)[0].name for _ in range(20)} == {'a'}


def test_basis_point_compare():
    """1/10000 정수로 비교: 49.995% 와 49.999% 는 같은 4999 → 최대 생명력으로 갈림"""
    a, b = _u('a', 0, 49995, 100000), _u('b', 1, 4999.9, 10000)
    assert Battle.heal_order(_stub('client'), a, [a, b], 1)[0] is b
    assert Battle.heal_order(_stub('slot'), a, [a, b], 1)[0] is a


def test_k_picks_and_full_list():
    us = [_u('a', 0, 80, 100), _u('b', 1, 20, 100), _u('c', 2, 80, 200), _u('d', 3, 40, 100)]
    got = Battle.heal_order(_stub('client'), us[0], us, 2)
    assert [v.name for v in got[:2]] == ['b', 'd'], [v.name for v in got]
    assert sorted(v.name for v in got) == ['a', 'b', 'c', 'd']


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_') and callable(f):
            f()
            n += 1
    print('heal_tie_test OK', n)
