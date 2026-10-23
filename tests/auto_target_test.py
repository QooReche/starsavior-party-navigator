# -*- coding: utf-8 -*-
"""게임 자동 전투 규칙(AutoSkillController) 회귀: python -X utf8 -I tests/auto_target_test.py

규칙 1(구원자 기본 대상)·1001(적 기본 대상)·스킬별 규칙(data/auto_skill.json)·침묵 기본기. 근거 NKM.decompiled.cs 6360~6620·6786~7130."""
import os
import sys
import unittest
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p3_test import battle, give, unit   # noqa: E402
from battlesim.mc import auto_skill_rules   # noqa: E402

HEAL = [dict(slot='기본기', dm=100), dict(slot='궁극기', cd=3, tg='아군 단일')]


class AllyRule1Test(unittest.TestCase):
    def pick(self, foes, mc=None, element=None):
        b = battle([unit('a', element=element)], foes, mc=mc)
        return b, b.pick_attack_target(b.allies[0])

    def test_boss_then_elite(self):
        b, v = self.pick([unit('m', hp=100), unit('boss', boss=True, hp=10 ** 6)])
        self.assertEqual(v.name, 'boss')
        b = battle([unit('a')], [unit('m', hp=100), unit('elite', hp=10 ** 6)])
        b.foes[1].d.grade = '정예'
        self.assertEqual(b.pick_attack_target(b.allies[0]).name, 'elite')

    def test_advantage_then_not_disadvantage(self):
        _, v = self.pick([unit('sun', element='태양', hp=100), unit('star', element='별', hp=10 ** 6)], element='태양')
        self.assertEqual(v.name, 'star')   # 태양은 별을 이김
        # 이기는 대상이 없으면 나를 이기지 않는 대상(달은 태양을 이김 -> 제외)
        _, v = self.pick([unit('moon', element='달', hp=100), unit('sun', element='태양', hp=10 ** 6)], element='태양')
        self.assertEqual(v.name, 'sun')

    def test_hp_rate_not_absolute_and_ignores_shield(self):
        b = battle([unit('a')], [unit('big', hp=100000), unit('small', hp=1000)])
        big, small = b.foes
        big.hp, small.hp = 40000, 900   # 40% vs 90%
        e = give(big, '보호막')
        e.shield = 10 ** 6
        self.assertIs(b.pick_attack_target(b.allies[0]), big)
        # 옛 규칙(boss_first)은 보호막+생명력 합 최저 -> small
        b.mc['ally_auto_target'] = 'boss_first'
        self.assertIs(b.pick_attack_target(b.allies[0]), small)

    def test_ties_random_both_sides(self):
        b = battle([unit('a')], [unit('f0'), unit('f1')], seed=3)
        got = Counter(b.pick_attack_target(b.allies[0]).name for _ in range(400))
        self.assertGreater(min(got['f0'], got['f1']), 120, got)


class EnemyRule1001Test(unittest.TestCase):
    def test_front_then_defender_distribution(self):
        roles = ['스트라이커', '디펜더', '스트라이커', '스트라이커']
        b = battle([unit('a%d' % i, role=r) for i, r in enumerate(roles)], [unit('foe')], seed=7)
        n = 20000
        cnt = Counter(b.pick_attack_target(b.foes[0]).pos for _ in range(n))
        # 0.8 x (0.8 + 0.2/2) + 0.2 x (0.8 + 0.2/4) = 0.89, 전열 스트라이커 0.09, 후열 각 0.01
        exp = {0: 0.09, 1: 0.89, 2: 0.01, 3: 0.01}
        for pos, p in exp.items():
            self.assertAlmostEqual(cnt[pos] / n, p, delta=0.012, msg=dict(cnt))
        b.mc['enemy_auto_target'] = 'weighted'   # 옛 가중: 디펜더 0.533
        cnt = Counter(b.pick_attack_target(b.foes[0]).pos for _ in range(n))
        self.assertAlmostEqual(cnt[1] / n, 0.8 * 2 / 3, delta=0.015)

    def test_no_defender_keeps_front(self):
        b = battle([unit('a%d' % i) for i in range(4)], [unit('foe')], seed=2)
        cnt = Counter(b.pick_attack_target(b.foes[0]).pos for _ in range(10000))
        self.assertAlmostEqual((cnt[0] + cnt[1]) / 10000, 0.8 + 0.2 * 0.5, delta=0.015)


class AutoSkillTest(unittest.TestCase):
    def setUp(self):
        self.assertIn('wedding-carmen', auto_skill_rules())

    def healer(self, mc=None, n=3):
        b = battle([unit('heal', skills=HEAL)] + [unit('a%d' % i) for i in range(n)], [unit('foe')], mc=mc)
        h = b.allies[0]
        h.key = 'wedding-carmen'   # 웨딩 카르멘 궁극기: 생명력 75% 이하 아군이 있을 때만, 대상 = 생명력 비율 최저
        h.cd = {}
        return b, h

    def test_heal_ultimate_held_until_75pct(self):
        b, h = self.healer()
        sk, tgt = b.choose_skill(h)
        self.assertEqual((sk.slot, tgt), ('기본기', None))
        b.allies[2].hp = b.allies[2].maxhp * 0.76
        self.assertEqual(b.choose_skill(h)[0].slot, '기본기')
        b.allies[2].hp = b.allies[2].maxhp * 0.75
        b.allies[3].hp = b.allies[3].maxhp * 0.6
        sk, tgt = b.choose_skill(h)
        self.assertEqual(sk.slot, '궁극기')
        self.assertIs(tgt, b.allies[3])
        # 실제 시전 대상도 그 아군
        b.cast(h, sk, target=tgt)
        self.assertGreater(h.cast_count['궁극기'], 0)

    def test_off_restores_old_choice(self):
        b, h = self.healer(mc=dict(auto_skill='off'))
        sk, tgt = b.choose_skill(h)
        self.assertEqual((sk.slot, tgt), ('궁극기', None))

    def test_self_stack_exact(self):
        b = battle([unit('bunny', skills=[dict(slot='기본기', dm=100), dict(slot='궁극기', dm=300, cd=4)])], [unit('foe')])
        u = b.allies[0]
        u.key, u.cd = 'bunny-charlotte', {}
        for n, slot in ((0, '기본기'), (4, '기본기'), (5, '궁극기')):
            if n:
                give(u, '점화', stacks=n)
            self.assertEqual(b.choose_skill(u)[0].slot, slot, n)

    def test_silence_basic(self):
        b, h = self.healer()
        b.allies[3].hp = 1
        give(h, '침묵', harmful=True)
        self.assertEqual(b.choose_skill(h)[0].slot, '기본기')

    def test_dead_ally_last_died(self):
        b = battle([unit('elisa', skills=HEAL)] + [unit('a%d' % i) for i in range(3)], [unit('foe')])
        u = b.allies[0]
        u.key, u.cd = 'elisa', {}   # 엘리사 궁극기: 쓰러진 아군이 있으면 마지막으로 쓰러진 아군, 아니면 75% 이하 회복
        b.kill(b.allies[1], b.foes[0])   # 같은 틱(광역)에 1번 -> 3번 순으로 쓰러짐 -> 3번
        b.kill(b.allies[3], b.foes[0])
        sk, tgt = b.choose_skill(u)
        self.assertEqual(sk.slot, '궁극기')
        self.assertIs(tgt, b.allies[3])
        b.allies[3].dead, b.allies[3].hp = False, 1.0   # 되살아난 뒤 다시 쓰러지면 새 순서
        b.kill(b.allies[3], b.foes[0])
        b.allies[1].dead, b.allies[1].hp = False, 1.0
        b.kill(b.allies[1], b.foes[0])
        self.assertIs(b.choose_skill(u)[1], b.allies[1])

    def test_variant_uses_base_key(self):
        b, h = self.healer()
        h.key = 'vera@개화(SSR)'   # 개화 베라 특수기·궁극기도 AutoSkillId 2(75% 이하 아군이 있을 때만)
        h.d.skills['특수기'] = h.d.skills['궁극기']
        self.assertEqual(b.choose_skill(h)[0].slot, '기본기')

    def test_data_vocabulary_known(self):
        b, h = self.healer()
        for key, slots in auto_skill_rules().items():
            for slot, spec in slots.items():
                for row in spec.get('rows', []):
                    for c in row['c']:
                        b.auto_cond_ok(h, c)
                    b.filter_pick(h, b.alive(0), row['f'])


if __name__ == '__main__':
    unittest.main()
