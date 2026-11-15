"""Recent attacker is visible for every target before first damage (NKM:15669-15689)."""
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from battlesim.mc import Battle, Ctx, Eff
from battlesim.metrics import unit_def
from battlesim.api import _CustomFoe
from battlesim.starsavior.parser import Line


def battle(mode='client'):
    enemies = [_CustomFoe(dict(name='enemy'+str(i), hp=1e9, atk=100, spd=100), i) for i in range(2)]
    b = Battle([unit_def('amora'), unit_def('gwen')], [enemies], random.Random(7),
               opts=dict(coop=False, nova_policy='auto'), mc={'last_damager_timing': mode})
    b.spawn_wave()
    a, old = b.allies
    for v in b.foes:
        v.last_damager = old
    c = Ctx(a, a, a.d.skills['궁극기'])
    c.targets = list(b.foes)
    return b, a, old, c


class MemoryTests(unittest.TestCase):
    def test_cross_target_reaction_observes_new_attacker(self):
        for mode, want_new in [('client', True), ('per_target', False)]:
            b, a, old, c = battle(mode)
            observed = []
            original = b.fire
            def fire(v, event, ctx):
                if v is b.foes[0] and event == 'prehit_self':
                    observed.append(b.filter_pick(b.foes[1], b.allies, ['last_damager']))
                return original(v, event, ctx)
            b.fire = fire
            b.deal(a, c)
            self.assertEqual(observed, [a if want_new else old])

    def test_damage_zero_still_updates(self):
        b, a, old, c = battle()
        for v in b.foes:
            v.eff['무적'] = Eff('무적', {}, None, 5, v, False)
            v.eff['무적'].stacks = 1
        b.deal(a, c)
        self.assertTrue(all(v.taken == 0 for v in b.foes))
        self.assertTrue(all(v.last_damager is a for v in b.foes))

    def test_chain_does_not_overwrite(self):
        b, a, old, c = battle()
        c.target = b.foes[0]
        for typ in [None, 'ADT_STAT_TRUE']:
            effect = dict(target='스킬 대상', stat='atk', coef=.1)
            if typ:
                effect['damage_type'] = typ
            before = sum(v.taken for v in b.foes)
            b.chain(a, effect, c)
            self.assertGreater(sum(v.taken for v in b.foes), before)
            self.assertTrue(all(v.last_damager is old for v in b.foes))

    def test_dead_attacker_falls_back_to_alive_pool(self):
        b, a, old, c = battle()
        old.dead = True
        self.assertIs(b.filter_pick(b.foes[0], [a], ['last_damager']), a)

    def test_single_target_and_coop_use_attacking_unit(self):
        b, a, old, c = battle()
        c.skill = a.d.skills['기본기']
        c.extra = True
        c.via = 'coop'
        c.targets = [b.foes[0]]
        b.deal(a, c)
        self.assertIs(b.foes[0].last_damager, a)
        self.assertIs(b.foes[1].last_damager, old)

    def test_self_hp_potential_boundary(self):
        b, a, old, c = battle()
        a.maxhp = 100000
        lower = Line('[피해 처리 직전] (자신 HP 49.99% 이하 · 조건: 내가 피해를 받기 직전) 자신에게 능력치 보정 피해 감소 +15% {이번 스킬에만 적용}', '잠재력', 'passive')
        upper = Line('[스킬 사용 시작 시] (자신 HP 50% 이상 · 조건: 내 공격 시) 자신에게 능력치 보정 피해 증가 +15% {이번 스킬에만 적용}', '잠재력', 'passive')
        for hp, want_low, want_high in [(49989, True, False), (49995, True, False), (50000, False, True), (50009, False, True)]:
            a.hp = hp
            self.assertEqual(b.cond_ok(a, lower, c), want_low)
            self.assertEqual(b.cond_ok(a, upper, c), want_high)
        self.assertGreater(b.rule_hits['self_hp_condition'], 0)
        a.hp = 49995
        b.mc['self_hp_condition'] = 'ratio'
        self.assertFalse(b.cond_ok(a, lower, c))

    def test_self_hp_float_multiplication_before_truncation(self):
        b, a, old, c = battle()
        # float32(1/100) is just below .01; float32(*10000) rounds to 100.
        # Reusing the target-condition double multiplication would yield 99.
        a.hp, a.maxhp = 1, 100
        ln = Line('[스킬 사용 시작 시] (자신 HP 1% 이상 · 조건: 내 공격 시) 자신에게 능력치 보정 피해 증가 +15% {이번 스킬에만 적용}', '잠재력', 'passive')
        self.assertTrue(b.cond_ok(a, ln, c))
        self.assertGreater(b.rule_hits['self_hp_condition'], 0)

    def test_dead_victim_not_recorded(self):
        b, a, old, c = battle()
        b.foes[1].dead = True
        b.deal(a, c)
        self.assertIs(b.foes[0].last_damager, a)
        self.assertIs(b.foes[1].last_damager, old)


if __name__ == '__main__':
    unittest.main()
