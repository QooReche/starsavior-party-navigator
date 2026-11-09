# -*- coding: utf-8 -*-
"""단계 그룹 버프(BUFF_STEP_TEMPLET): 같은 그룹은 높은 단계가 이긴다(buff_step_group=client).
클라 NKM:4283-4305,4450-4458. 실행: python -X utf8 -I tests/buff_step_test.py"""
import json
import math
import os
import random
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from battlesim.mc import Battle, buff_step                       # noqa: E402
from battlesim.metrics import unit_def                           # noqa: E402
from foe_react_test import _foe                                  # noqa: E402

LOW, HIGH = '공격력 증가', '상급 공격력 증가'


def _battle(**mc):
    foe = _foe({'특수기': {'timing': 'hit', 'conds': [['skill_basic']], 'target': 'react_target', 'is_attack': True}})
    b = Battle([unit_def('emily')], [[foe]], random.Random(3), opts=dict(nova_policy='auto', coop=False),
               mc=mc, timeline=False)
    b.spawn_wave()
    return b


def _give(b, name, dur):
    a = b.allies[0]
    b.add_effect(a, a, dict(name=name, props={'공격력%': 10}, max=1, dur=dur, times=1), None)
    return a


class TestStepTable(unittest.TestCase):
    def test_table_levels(self):
        self.assertEqual(buff_step(LOW), (3, 1))
        self.assertEqual(buff_step(HIGH), (3, 2))
        self.assertEqual(buff_step(HIGH + '(해제불가)'), (3, 2))       # 꼬리표는 떼고 비교
        self.assertIsNone(buff_step('도발'))
        self.assertIsNone(buff_step('잔재된 괴리(해제불가)'))          # 이름만으로 단계를 못 가르는 그룹은 제외

    def test_data_names_unique_per_group(self):
        with open(os.path.join(ROOT, 'data', 'buff_step.json'), encoding='utf-8') as f:
            names = json.load(f)['names']
        for n, (g, s) in names.items():
            self.assertGreaterEqual(s, 1)


class TestStepGroup(unittest.TestCase):
    def test_higher_replaces_lower(self):
        b = _battle()
        a = _give(b, LOW, 3)
        _give(b, HIGH, 2)
        self.assertNotIn(LOW, a.eff)
        self.assertEqual(a.eff[HIGH].dur, 2)

    def test_lower_rejected_when_shorter(self):
        b = _battle()
        a = _give(b, HIGH, 3)
        _give(b, LOW, 1)
        self.assertNotIn(LOW, a.eff)
        self.assertEqual(a.eff[HIGH].dur, 3)
        self.assertFalse(a.eff[HIGH].skip_tick)

    def test_lower_extends_higher_and_skips_one_tick(self):
        b = _battle()
        a = _give(b, HIGH, 2)
        _give(b, LOW, 5)
        self.assertNotIn(LOW, a.eff)
        self.assertEqual(a.eff[HIGH].dur, 5)
        self.assertTrue(a.eff[HIGH].skip_tick)

    def test_off_keeps_both(self):
        b = _battle(buff_step_group='off')
        a = _give(b, LOW, 3)
        _give(b, HIGH, 2)
        self.assertIn(LOW, a.eff)
        self.assertIn(HIGH, a.eff)

    def test_other_group_untouched(self):
        b = _battle()
        a = _give(b, '방어력 증가', 3)        # 그룹 4
        _give(b, HIGH, 2)                     # 그룹 3
        self.assertIn('방어력 증가', a.eff)
        self.assertIn(HIGH, a.eff)

    def test_same_name_reapply_not_a_step_conflict(self):
        b = _battle()
        a = _give(b, LOW, 2)
        _give(b, LOW, 4)
        self.assertEqual(a.eff[LOW].dur, 4)
        self.assertFalse(a.eff[LOW].skip_tick)

    def test_skip_tick_is_consumed_by_owner_turn_end(self):
        def dur_after_own_turn(skip):
            b = _battle()
            a = _give(b, HIGH, 5)
            a.eff[HIGH].fresh = False
            a.eff[HIGH].skip_tick = skip
            b._act_turn(a)
            return a.eff[HIGH].dur, a.eff[HIGH].skip_tick
        self.assertEqual(dur_after_own_turn(False), (4, False))   # 평소: 자기 턴 종료에 1 차감
        self.assertEqual(dur_after_own_turn(True), (5, False))    # 단계 그룹 갱신 직후: 이번 차감만 건너뜀


if __name__ == '__main__':
    unittest.main()
