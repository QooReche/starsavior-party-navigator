# -*- coding: utf-8 -*-
"""반격 회귀: python -X utf8 -I tests/revenge_test.py

게임 코드 NKM.decompiled.cs 11990~12075·15227~15360: 유효 타격을 받은 유닛마다 행동당 한 번, 반격 확률로 공격자에게 기본기."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p3_test import battle, give, unit   # noqa: E402

AOE = [dict(slot='기본기', dm=100, all=True)]


def counters(foe):
    return foe.cast_count.get('기본기(추가)', 0)


class RevengeTest(unittest.TestCase):
    def setup(self, n_foes=1, rate=100, mc=None, skills=None):
        b = battle([unit('a', hp=10 ** 7, skills=skills)], [unit('f%d' % i, hp=10 ** 7) for i in range(n_foes)], mc=mc)
        for f in b.foes:
            give(f, '강화 반격', props={'반격 확률': rate}, dur=50)
        return b, b.allies[0]

    def test_counter_once_per_action(self):
        b, a = self.setup()
        b.act(a)
        self.assertEqual(counters(b.foes[0]), 1)
        self.assertGreater(a.taken, 0)
        self.assertEqual(b.revenges, [0, 1])

    def test_each_hit_unit_counters(self):
        b, a = self.setup(n_foes=3, skills=AOE)
        b.act(a)
        self.assertEqual([counters(f) for f in b.foes], [1, 1, 1])

    def test_no_counter_to_counter_or_without_rate(self):
        b, a = self.setup(rate=0)
        give(a, '강화 반격', props={'반격 확률': 100}, dur=50)   # 반격을 받은 쪽이 다시 반격하지 않음
        b.act(a)
        self.assertEqual(counters(b.foes[0]), 0)
        self.assertEqual(a.cast_count.get('기본기(추가)', 0), 0)

    def test_broken_or_stunned_no_counter(self):
        b, a = self.setup(n_foes=2, skills=AOE)
        b.foes[0].broken = True
        give(b.foes[1], '기절', harmful=True)
        b.act(a)
        self.assertEqual([counters(f) for f in b.foes], [0, 0])

    def test_rate_probability(self):
        b, a = self.setup(rate=25)
        for _ in range(2000):
            a.cd = {}
            b.act(a)
        self.assertAlmostEqual(counters(b.foes[0]) / 2000, 0.25, delta=0.03)

    def test_damage_not_evade_decides(self):
        # 게임은 피해가 0보다 큰 타격을 기록(NKM 7203~7215): 회피해도 피해가 남으면 반격, 피해 무효면 반격 없음
        b, a = self.setup(n_foes=2, skills=AOE)
        give(b.foes[0], '회피율 증가', props={'회피율': 100}, dur=50)
        give(b.foes[1], '스킬 피해 무효', dur=50)
        b.act(a)
        self.assertGreater(b.foes[0].taken, 0)
        self.assertEqual(b.foes[1].taken, 0)
        self.assertEqual([counters(f) for f in b.foes], [1, 0])

    def test_attacker_death_ends_only_that_attack(self):
        # A(생명력 1)의 기본기 -> B 광역 협공. F0 의 반격에 A 가 쓰러져도 협공(B)에 대한 F1 의 반격은 따로 처리
        b = battle([unit('A', hp=1), unit('B', hp=10 ** 7, skills=AOE)], [unit('f%d' % i, hp=10 ** 7, atk=10 ** 5) for i in range(2)])
        A, B = b.allies
        give(B, '협공 증가', props={'협공 확률': 100}, dur=50)
        for f in b.foes:
            give(f, '강화 반격', props={'반격 확률': 100}, dur=50)
        b.pick_attack_target = lambda att, sk=None: b.foes[0] if att.side == 0 else A
        b.act(A)
        self.assertGreater(B.cast_count.get('기본기(추가)', 0), 0)   # 협공이 일어났음
        self.assertTrue(A.dead)
        self.assertEqual([counters(f) for f in b.foes], [1, 1])

    def test_basic_on_cooldown_no_counter(self):
        b, a = self.setup()
        b.foes[0].cd['기본기'] = 3
        b.act(a)
        self.assertEqual(counters(b.foes[0]), 0)

    def test_off(self):
        b, a = self.setup(mc=dict(revenge='off'))
        b.act(a)
        self.assertEqual(counters(b.foes[0]), 0)


if __name__ == '__main__':
    unittest.main()
