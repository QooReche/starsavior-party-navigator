# -*- coding: utf-8 -*-
"""Battle.put_eff 와 길방 BFB·코스모 Controller 의 _put/_sup_put 래퍼가 옛 동작을 지키는지.
(두 모듈의 _put 이 따로 있던 시절의 차이: 코스모는 다시 걸 때 수치 갱신, 길방은 갱신 안 함)
실행: python -X utf8 -I tests/put_eff_test.py"""
import math
import os
import random
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from battlesim.mc import Battle                                  # noqa: E402
from battlesim.metrics import unit_def                           # noqa: E402
from battlesim.starsavior import cosmo_raid, guild_bfb           # noqa: E402
from foe_react_test import _foe                                  # noqa: E402


def _battle():
    foe = _foe({'특수기': {'timing': 'hit', 'conds': [['skill_basic']], 'target': 'react_target', 'is_attack': True}})
    b = Battle([unit_def('emily')], [[foe]], random.Random(1), opts=dict(nova_policy='auto', coop=False),
               mc={}, timeline=False)
    b.spawn_wave()
    return b


class TestPutEff(unittest.TestCase):
    def test_new_effect_fields(self):
        b = _battle()
        a, foe = b.allies[0], b.foes[0]
        e = b.put_eff(a, 'X', {'공격력%': 5}, dur=3, maxs=2, add=1, src=foe, cat='debuff', fixed=False)
        self.assertEqual((e.stacks, e.dur, e.harmful, e.category, e.fixed, e.src), (1, 3, True, 'debuff', False, foe))
        self.assertIs(a.eff['X'], e)

    def test_stack_cap_floor_and_duration(self):
        b = _battle()
        a = b.allies[0]
        b.put_eff(a, 'X', {}, dur=2, maxs=2, add=5)
        self.assertEqual(a.eff['X'].stacks, 2)                   # maxs 로 자름
        b.put_eff(a, 'X', {}, dur=7, maxs=2, add=-9)
        self.assertEqual(a.eff['X'].stacks, 0)                   # 0 아래로 안 내려감
        self.assertEqual(a.eff['X'].dur, 7)                      # 지속은 긴 쪽
        b.put_eff(a, 'X', {}, dur=1, maxs=2, add=0)
        self.assertEqual(a.eff['X'].dur, 7)

    def test_refresh_props_switch(self):
        b = _battle()
        a = b.allies[0]
        b.put_eff(a, 'X', {'v': 1})
        b.put_eff(a, 'X', {'v': 2})
        self.assertEqual(a.eff['X'].props, {'v': 1})
        b.put_eff(a, 'X', {'v': 3}, refresh_props=True)
        self.assertEqual(a.eff['X'].props, {'v': 3})

    def test_cosmo_put_refreshes_props_and_defaults_to_marker(self):
        b = _battle()
        c = cosmo_raid.Controller(b)
        c.boss = b.foes[0]
        a = b.allies[0]
        e = c._put(a, 'X', {'v': 1})
        self.assertEqual((e.category, e.harmful, e.src, e.dur), ('marker', False, c.boss, math.inf))
        c._put(a, 'X', {'v': 2})
        self.assertEqual(a.eff['X'].props, {'v': 2})
        self.assertEqual(a.eff['X'].stacks, 1)                   # maxs=1

    def test_guild_put_keeps_props_and_defaults_to_buff(self):
        b = _battle()
        c = guild_bfb.Controller(b)
        c.boss = b.foes[0]
        a = b.allies[0]
        e = c._put(a, 'X', {'v': 1})
        self.assertEqual((e.category, e.src), ('buff', c.boss))
        c._put(a, 'X', {'v': 2})
        self.assertEqual(a.eff['X'].props, {'v': 1})

    def test_guild_sup_put_is_marker_owned_by_target(self):
        b = _battle()
        c = guild_bfb.Controller(b)
        c.boss = b.foes[0]
        a = b.allies[0]
        c._sup_put(a, 'S', {'v': 1}, maxs=3)
        c._sup_put(a, 'S', {'v': 9}, maxs=3)
        e = a.eff['S']
        self.assertEqual((e.category, e.harmful, e.fixed, e.src, e.stacks, e.props), ('marker', False, True, a, 2, {'v': 1}))


if __name__ == '__main__':
    unittest.main()
