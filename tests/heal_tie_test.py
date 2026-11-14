# -*- coding: utf-8 -*-
"""회복·보호막 대체 경로의 «생명력 비율 최저 1명» 동률 처리 mc.heal_tie.
클라 회복 규칙 2(static-data tables/Plain/AUTO_SKILL_TARGET_TEMPLET.json Id 2 = IsLowHpRate → IsLowMaxHp, 그래도 여럿이면 무작위 —
NKM.decompiled.cs build 26610546 7132-7181). 옛 엔진은 비율이 같으면 앞 칸을 골랐다.
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


# ---- 세 호출 경로 연결(pick_ally · «아군 N명» 문구 경로 · select_auto lowest_hp)과 난수·자료 경로 우선 ----
from unittest.mock import patch                                  # noqa: E402
import battlesim.mc as MCM                                       # noqa: E402


def _path_stub(mode, units, seed=1):
    b = _stub(mode, seed)
    b.mc.update(heal_target='lowest_hp_ratio', foe_auto='client')
    b.opts = {'forced_coop_target': 'random'}
    b._cur_line = None
    b.alive = lambda side: [u for u in units if u.side == side and not u.dead]
    b.heal_order = lambda *a, **k: Battle.heal_order(b, *a, **k)
    b.live_atk = lambda v: 0
    b.unsup = defaultdict(int)
    return b


def _tied():
    """a(앞 칸)·b 가 비율·최대 생명력 모두 같음, c 는 체력 가득."""
    return [_u('a', 0, 50, 100), _u('b', 1, 50, 100), _u('c', 2, 100, 100)]


def _draws(call, mode, n=300):
    c = Counter()
    for seed in range(n):
        us = _tied()
        c[call(_path_stub(mode, us, seed), us)] += 1
    return c


def test_path_pick_ally():
    call = lambda b, us: Battle.pick_ally(b, us[2], 'heal').name
    c = _draws(call, 'client')
    assert set(c) == {'a', 'b'} and min(c.values()) > 60, c        # 동률은 무작위
    assert _draws(call, 'slot', 20) == Counter(a=20)                # 옛 동작 = 앞 칸


def test_path_text_resolve():
    call = lambda b, us: Battle.resolve(b, us[2], '아군 1명', NS(), 'heal')[0].name
    c = _draws(call, 'client')
    assert set(c) == {'a', 'b'} and min(c.values()) > 60, c
    assert _draws(call, 'slot', 20) == Counter(a=20)


def test_path_select_auto_lowest_hp():
    def call(b, us):
        with patch.object(MCM, 'auto_rule', lambda d, ln, kind: {'mode': 'lowest_hp'}):
            return Battle.select_auto(b, us[2], '아군 1명(자동 지정)', NS(targets=[]), 'heal')[0].name
    c = Counter()
    for seed in range(300):
        us = _tied()
        b = _path_stub('client', us, seed)
        b._cur_line = NS(eff={}, raw='', slot=None)
        for u in us:
            u.d = None
        c[call(b, us)] += 1
    assert set(c) == {'a', 'b'} and min(c.values()) > 60, c


def test_no_tie_keeps_rng_state():
    """동률이 없으면 난수를 쓰지 않음(난수 흐름 불변)."""
    us = [_u('a', 0, 80, 100), _u('b', 1, 20, 100), _u('c', 2, 90, 100)]
    b = _path_stub('client', us)
    rng = b.R(0)
    before = rng.getstate()
    assert Battle.pick_ally(b, us[0], 'heal') is us[1]
    assert Battle.resolve(b, us[0], '아군 2명', NS(), 'heal')[0] is us[1]
    assert rng.getstate() == before and b.rule_hits['heal_tie'] == 0


def test_data_path_wins_over_heal_order():
    """줄에 자동 대상 자료가 있으면(line_spec ally) 자료 경로가 먼저 — heal_order 를 부르지 않음."""
    us = _tied()
    b = _path_stub('client', us)
    b._cur_line = NS(eff={'name': '회복'})
    sentinel = [us[2]]
    b.line_spec = lambda owner, ln: {'ally': True}
    b.line_auto_targets = lambda owner, spec, ctx: sentinel
    b.heal_order = lambda *a, **k: (_ for _ in ()).throw(AssertionError('heal_order 호출됨'))
    assert Battle.resolve(b, us[0], '아군 1명(자동 지정)', NS(), 'heal') is sentinel


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_') and callable(f):
            f()
            n += 1
    print('heal_tie_test OK', n)
