# -*- coding: utf-8 -*-
"""턴 제한 단위 회귀: python -X utf8 -I tests/turn_limit_test.py

게임 전역 턴 = 아군·적 유닛이 행동할 때마다 +1(NKM.decompiled.cs 13796~13798), 전역 턴 > 제한이면 전투 종료(599~623·755~762).
코스모 게이트(RANKING_RAID) LimitTurn 50·CountEnemyTurnOnly false."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p3_test import battle, unit   # noqa: E402
from battlesim import quick   # noqa: E402


def total_actions(b):
    return sum(u.actions for u in b.allies) + sum(u.actions for u in b.all_foes)


class EngineTurnLimitTest(unittest.TestCase):
    def fight(self, mc=None, limit=12):
        b = battle([unit('a%d' % i, spd=100 + 10 * i) for i in range(4)], [unit('boss', hp=10 ** 9, boss=True, spd=150)],
                   mc=mc, turn_limit=limit)
        return b.run()

    def test_counts_all_actions(self):
        b = self.fight()
        self.assertEqual(b.result, 'timeout')
        self.assertEqual(total_actions(b), 12)
        self.assertEqual(b.global_turns, 12)

    def test_model_unit_legacy(self):
        b = self.fight(mc=dict(turn_limit_unit='model'))
        self.assertEqual(b.result, 'timeout')
        self.assertGreater(total_actions(b), 12 * 4)   # 모델 턴 12 = 100틱 x 12 -> 전체 행동은 그 몇 배

    def test_clear_before_limit(self):
        b = battle([unit('a%d' % i, atk=10 ** 6) for i in range(4)], [unit('foe', hp=1000)], turn_limit=3)
        b.run()
        self.assertEqual(b.result, 'clear')
        self.assertLessEqual(total_actions(b), 3)

    def test_no_limit_keeps_max_turns(self):
        b = battle([unit('a')], [unit('boss', hp=10 ** 9)], max_turns=4)
        b.run()
        self.assertEqual(b.result, 'timeout')
        self.assertGreater(total_actions(b), 4)   # 제한 없는 스테이지는 옛 시간 상한(모델 턴) 그대로


class QuickTurnLimitTest(unittest.TestCase):
    SV = {'x': ['s', 1000, 100000, 1000, 120, 1000.0, 10.0, 10.0, '']}

    def stage(self, lt):
        # 생명력 1e9 보스 1, 속도 160 -> 라운드마다 (120 + 160)/100 = 2.8 행동
        return dict(bp=1000.0, lt=lt, w=[[[1e9, 0, 160, 0, 0, 1]]])

    def test_rounds_from_actions(self):
        r = quick.evaluate(['x'], self.stage(28), self.SV, [[0, 99999, 10000, 10000]])
        self.assertEqual((r['clear'], r['why']), (False, 'time'))
        self.assertEqual(r['rounds'], 10)   # 2.8 x 10 = 28 에 닿으면 끝
        r = quick.evaluate(['x'], self.stage(None), self.SV, [[0, 99999, 10000, 10000]])
        self.assertEqual(r['rounds'], quick.MAX_ROUNDS)


if __name__ == '__main__':
    unittest.main()
