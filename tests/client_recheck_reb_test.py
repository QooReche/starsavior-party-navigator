"""Build 26314877: cooldown order, hit-time revenge rate, NovaForce cap.

Synthetic combat only. --mutations temporarily restores each legacy rule.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, give, unit
from battlesim.mc import Ctx, MC_OPTS
from battlesim.starsavior.parser import Line


class CooldownOrderTest(unittest.TestCase):
    def trace(self, mc=None, side=1):
        actor = unit('actor', hp=10**7, skills=[
            dict(slot='기본기', dm=100), dict(slot='궁극기', dm=100, cd=4)])
        actor.spawn = 'A'
        other = unit('other', hp=10**7)
        b = battle([other] if side else [actor], [actor] if side else [other], mc=mc)
        u = (b.foes if side else b.allies)[0]
        give(u, '종료 관측', dur=1)
        seen = []
        fire, tick = b.fire, b._tick_cooldowns

        def on_fire(owner, kind, ctx):
            if owner is u and kind == 'own_te':
                seen.append(('effect', u.cd['궁극기']))
                # A cooldown setter distinguishes ordering, unlike subtraction.
                u.cd['궁극기'] = 2
            return fire(owner, kind, ctx)

        def on_tick(owner):
            if owner is u:
                seen.append(('tick', '종료 관측' in u.eff))
            return tick(owner)

        with patch.object(b, 'fire', side_effect=on_fire), patch.object(b, '_tick_cooldowns', side_effect=on_tick):
            b.act(u)
        self.assertEqual(u.actions, 1)
        self.assertGreater(u.dmg, 0)
        return u, seen

    def test_effect_and_duration_before_enemy_cooldown(self):
        u, seen = self.trace()
        self.assertEqual(seen, [('effect', 4), ('tick', False)])
        self.assertEqual(u.cd['궁극기'], 1)

    def test_legacy_order(self):
        u, seen = self.trace({'enemy_cd_end_order': 'before_effects'})
        self.assertEqual(seen, [('tick', True), ('effect', 3)])
        self.assertEqual(u.cd['궁극기'], 2)

    def test_ally_still_ticks_at_start(self):
        for order in ('before_effects', 'after_effects'):
            u, seen = self.trace({'enemy_cd_end_order': order}, side=0)
            self.assertEqual(seen, [('tick', True), ('effect', 4)])
            self.assertEqual(u.cd['궁극기'], 2)


class RevengeSnapshotTest(unittest.TestCase):
    def counter(self, before, after, mc=None, side=1):
        b = battle([unit('ally', hp=10**7)], [unit('enemy', hp=10**7)], mc=mc)
        defender = (b.foes if side else b.allies)[0]
        attacker = (b.allies if side else b.foes)[0]
        give(defender, '반격 시험', {'반격 확률': before}, dur=50)
        seen = []
        fire = b.fire

        def on_fire(owner, kind, ctx):
            if owner is defender and kind == 'hit_self':
                seen.append(owner.taken)
                give(defender, '반격 시험', {'반격 확률': after}, dur=50)
            return fire(owner, kind, ctx)

        with patch.object(b, 'fire', side_effect=on_fire), patch.object(b.R(defender.side), 'random', return_value=0.5):
            b.act(attacker)
        self.assertEqual(len(seen), 1)
        self.assertGreater(seen[0], 0)
        return b.revenges[defender.side]

    def test_hit_rate_survives_positive_rate_decrease(self):
        for side in (0, 1):
            self.assertEqual(self.counter(100, 25, side=side), 1)

    def test_later_increase_does_not_raise_hit_rate(self):
        self.assertEqual(self.counter(25, 100), 0)

    def test_later_gain_does_not_create_counter(self):
        self.assertEqual(self.counter(0, 100), 0)

    def test_removing_current_rate_cancels_saved_counter(self):
        self.assertEqual(self.counter(100, 0), 0)

    def test_legacy_uses_current_rate(self):
        self.assertEqual(self.counter(100, 25, {'revenge_rate': 'current'}), 0)
        self.assertEqual(self.counter(0, 100, {'revenge_rate': 'current'}), 1)

    def test_off_still_disables_revenge(self):
        self.assertEqual(self.counter(100, 100, {'revenge': 'off'}), 0)


class NovaCapTest(unittest.TestCase):
    def test_skill_and_explicit_effect_share_cap(self):
        b = battle([unit('ally', hp=10**7)], [unit('enemy', hp=10**7)])
        a, v = b.allies[0], b.foes[0]
        b.team_nova = 11
        sk = a.d.skills['기본기']
        sk.nv = 3
        b.cast(a, sk, extra=True)
        self.assertGreater(v.taken, 0)
        self.assertGreater(b.progress(), 0)
        self.assertEqual(b.team_nova, 12)
        b.run_line(v, Line('[스킬 사용 후] 자신에게 노바 포스 +20', '기본기', 'active'), Ctx(v, v, sk))
        self.assertEqual(b.enemy_nova, 12)
        b.nova_add(a, -4)
        self.assertEqual(b.team_nova, 8)
        b.nova_add(a, -99)
        self.assertEqual(b.team_nova, 0)

    def test_legacy_no_cap(self):
        b = battle([unit('a')], [unit('v')], mc={'nova_force_cap': 0})
        b.nova_add(b.allies[0], 20)
        self.assertEqual(b.team_nova, 20)

    def test_break_skill_uses_cap_for_team_and_unit_pools(self):
        for pool in ('team', 'unit'):
            for cap, expected in ((12, 12), (0, 15)):
                with self.subTest(pool=pool, cap=cap):
                    b = battle([unit('a'), unit('b')], [unit('v', hp=10**9)],
                               opts={'nova_pool': pool}, mc={'nova_force_cap': cap},
                               break_skill={'name': '차원 강습'})
                    b.team_nova = 11
                    for u in b.allies:
                        u.nova = 11
                    b.break_points = b.mc['break_skill_cost']
                    b._use_break_skill()
                    self.assertEqual(b.break_skill_uses, 1)
                    self.assertGreater(b.break_skill_dmg, 0)
                    self.assertGreater(b.progress(), 0)
                    self.assertEqual([b.nova_of(u) for u in b.allies], [expected, expected])

    def test_unit_pool_also_capped_without_affecting_other_units(self):
        b = battle([unit('a'), unit('b')], [unit('v')], opts={'nova_pool': 'unit'})
        b.nova_add(b.allies[0], 20)
        self.assertEqual([u.nova for u in b.allies], [12, 0])


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        cases = [
            ('enemy_cd_end_order', 'before_effects', CooldownOrderTest, 1),
            ('revenge_rate', 'current', RevengeSnapshotTest, 3),
            ('nova_force_cap', 0, NovaCapTest, 2),
        ]
        caught = True
        for key, value, cls, minimum in cases:
            with patch.dict(MC_OPTS, {key: value}):
                result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
            ok = len(result.failures) >= minimum and not result.errors
            print(f'{key} legacy mutation detected: {ok} ({len(result.failures)} failures)')
            caught &= ok
        sys.exit(0 if caught else 1)
    unittest.main(verbosity=2)
