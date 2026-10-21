# -*- coding: utf-8 -*-
"""적 공격 우선 타깃 회귀: python -X utf8 -I tests/enemy_target_test.py"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p5_test import battle, give, unit
from battlesim.mc import Ctx
from battlesim.starsavior.foe import load_foe, FoeDef


class EnemyTargetTest(unittest.TestCase):
    def test_max_hp_priority_separate_from_current_hp(self):
        for stat in ('최대 생명력', '최대 HP', '현재 생명력', '현재 HP',
                     '생명력', 'HP', '현재 생명력 비율', 'HP 비율'):
            for order in ('높은', '낮은'):
                with self.subTest(stat=stat, order=order):
                    b, f = self.setup_battle(f'{stat}이 가장 {order} 적을 우선 공격합니다.')
                    for a in b.allies[2:]:
                        b.kill(a, f)
                    b.allies[0].maxhp, b.allies[0].hp = 20000, 1000
                    b.allies[1].maxhp, b.allies[1].hp = 10000, 9000
                    first = stat.startswith('최대') == (order == '높은')
                    self.assertEqual(b.skill_targets(f, f.d.skills['기본기']),
                                     [b.allies[0 if first else 1]])

    def test_real_void_covenant_mark_reapplication_max_hp(self):
        raw = load_foe()
        ui = next(i for i, u in enumerate(raw['u']) if u['n'] == '공허맹약자')
        b = battle([unit('large', hp=20000), unit('small', hp=10000)], [FoeDef(raw, ui)])
        f = b.foes[0]
        self.assertIn('최대 생명력이 가장 높은 적', f.d.desc['패시브'])
        for a, hp in zip(b.allies, (1000, 9000)):
            a.eff.clear()
            a.hp = hp
            b.dirty(a)
        b.fire(f, 'own_ts', Ctx(f, f, None))
        self.assertTrue(b.allies[0].has('피의 맹약(해제불가)'))
        self.assertFalse(b.allies[1].has('피의 맹약(해제불가)'))

    def setup_battle(self, desc='행동 게이지가 가장 높은 적 우선'):
        foe = unit('망각의 예언자')
        foe.desc = {'기본기': desc}
        b = battle([unit('a%d' % i) for i in range(4)], [foe], timeline=True)
        for u, gauge in zip(b.allies, (1000, 2000, 9000, 3000)):
            u.gauge = gauge
        return b, b.foes[0]

    def test_gauge_priority_attack(self):
        b, f = self.setup_battle()
        b.act(f)
        self.assertGreater(b.allies[2].taken, 0)
        self.assertEqual(sum(u.taken for u in b.allies if u.pos != 2), 0)

    def test_real_prophet_basic_description(self):
        raw = load_foe()
        ui = next(i for i, u in enumerate(raw['u']) if u['n'] == '망각의 예언자')
        foe = FoeDef(raw, ui)
        self.assertIn('행동 게이지가 가장 높은 적', foe.desc['기본기'])
        b = battle([unit('a%d' % i) for i in range(4)], [foe], enemy_lines=False)
        b.allies[3].gauge = 9000
        b.cast(b.foes[0], b.foes[0].d.skills['기본기'])
        self.assertGreater(b.allies[3].taken, 0)
        self.assertEqual(sum(u.taken for u in b.allies[:3]), 0)

    def test_explicit_and_taunt_precede_priority(self):
        b, f = self.setup_battle()
        sk = f.d.skills['기본기']
        self.assertEqual(b.skill_targets(f, sk, b.allies[0]), [b.allies[0]])
        give(f, '도발', src=b.allies[1], harmful=True)
        b.act(f)
        self.assertGreater(b.allies[1].taken, 0)
        self.assertEqual(b.allies[2].taken, 0)

    def test_ties_use_existing_random_and_untargetable(self):
        b, f = self.setup_battle()
        sk = f.d.skills['기본기']
        b.allies[3].gauge = 9000
        picks = {b.skill_targets(f, sk)[0].pos for _ in range(100)}
        self.assertEqual(picks, {2, 3})
        give(b.allies[2], '은신')
        self.assertEqual(b.skill_targets(f, sk), [b.allies[3]])

    def test_other_rankings(self):
        for desc in ('생명력이 가장 낮은 적 우선', 'HP가 가장 낮은 적 우선',
                     '방어력이 가장 높은 적 우선', '속도가 가장 높은 적 우선'):
            with self.subTest(desc=desc):
                b, f = self.setup_battle(desc)
                b.allies[3].hp = 100
                give(b.allies[3], '강화', {'방어력%': 50, '속도%': 50})
                self.assertEqual(b.skill_targets(f, f.d.skills['기본기']), [b.allies[3]])

    def test_hp_ratio_priority(self):
        b, f = self.setup_battle('현재 생명력 비율이 가장 낮은 적을 우선 공격합니다.')
        b.allies[0].hp = 100
        b.allies[3].hp, b.allies[3].maxhp = 200, 100000
        self.assertEqual(b.skill_targets(f, f.d.skills['기본기']), [b.allies[3]])

    def test_attack_rank_uses_current_attack(self):
        b, f = self.setup_battle('공격력이 가장 높은 적을 우선 공격합니다.')
        give(b.allies[3], '공격 강화', {'공격력%': 20})
        self.assertEqual(b.skill_targets(f, f.d.skills['기본기']), [b.allies[3]])

    def test_effect_selector_does_not_redirect_attack(self):
        b, f = self.setup_battle('적을 공격하고 방어력이 가장 높은 적의 게이지를 감소시킵니다.')
        picks = {b.skill_targets(f, f.d.skills['기본기'])[0].pos for _ in range(100)}
        self.assertEqual(picks, {0, 1, 2, 3})


if __name__ == '__main__':
    unittest.main(verbosity=2)
