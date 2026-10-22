"""Nova rules from skill tables and native skill-end processing; no fitting."""
import copy
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from battlesim.api import _CustomFoe
from battlesim.mc import Battle, Ctx
from battlesim.metrics import unit_def
from battlesim.rules import MC_OPTS
from battlesim.starsavior.parser import Line, Skill
from ingame_check import low_priority
from nova_gauge_audit import audit_measure
from received_damage_audit import measure


def battle(keys=('wedding-carmen',), policy='auto', mc=None, pool='team'):
    foe = _CustomFoe(dict(name='target', hp=10**8, atk=1000, **{'def': 1000}, spd=100), 0)
    b = Battle([copy.deepcopy(unit_def(k)) for k in keys], [[foe]], random.Random(7),
               opts=dict(nova_policy=policy, coop=False, nova_pool=pool), mc=mc, timeline=True)
    b.spawn_wave()
    return b


class NovaGaugeTest(unittest.TestCase):
    def test_reactions_pay_declared_gain(self):
        for key in ('white-pearl-luna', 'wedding-carmen', 'cristelle'):
            with self.subTest(key=key):
                b = battle((key,))
                u = b.allies[0]
                sk = u.d.trigger_skills['특수기']
                self.assertEqual(sk.nv, 1)
                b.cast(u, sk, extra=True, skip_lines=True, via='reaction')
                self.assertEqual(b.team_nova, 1)
                self.assertEqual(sum(b.nova_bursts.values()), 0)

    def test_zero_gain_reaction_stays_zero(self):
        b = battle(('professor-m',))
        u = b.allies[0]
        b.cast(u, u.d.trigger_skills['특수기'], extra=True, skip_lines=True)
        self.assertEqual(b.team_nova, 0)

    def test_every_cast_uses_value_once_not_hit_count(self):
        b = battle()
        u = b.allies[0]
        sk = Skill(dict(sl='특수기', n='gain', ty='액티브', tg='아군 전체', act='비공격', nv=2))
        for extra in (False, True):
            before = b.team_nova
            b.cast(u, sk, extra=extra, skip_lines=True)
            self.assertEqual(b.team_nova - before, 2)

    def test_plain_hit_and_basic_have_no_generic_gain(self):
        b = battle()
        u = b.allies[0]
        b.apply_damage(b.foes[0], u, 10, 'hit')
        b.cast(u, u.d.skills['기본기'], skip_lines=True)
        self.assertEqual(b.team_nova, 0)

    def test_team_and_enemy_pools_are_separate(self):
        b = battle(('wedding-carmen', 'white-pearl-luna'))
        b.nova_add(b.allies[0], 2)
        b.nova_add(b.allies[1], 1)
        b.nova_add(b.foes[0], 5)
        self.assertEqual([b.nova_of(u) for u in b.allies + b.foes], [3, 3, 5])

    def test_cost_before_gain_and_no_extra_burst(self):
        b = battle(policy='manual')
        u = b.allies[0]
        b.team_nova = 3
        self.assertFalse(b.cast(u, u.d.trigger_skills['특수기'], extra=True, skip_lines=True).nb)
        self.assertEqual(b.team_nova, 4)
        self.assertTrue(b.cast(u, u.d.skills['기본기']).nb)
        self.assertEqual(b.team_nova, 0)
        b.team_nova = 4
        self.assertFalse(b.cast(u, u.d.skills['기본기'], extra=True).nb)
        self.assertEqual(b.team_nova, 4)

    def test_manual_slot_shield_matches_heal_policy(self):
        for policy in ('manual', 'heal'):
            b = battle(('white-pearl-luna',), policy=policy)
            u = b.allies[0]
            b.team_nova = 4
            b.cast(u, u.d.skills['기본기'])
            self.assertEqual(u.shield_given, int(u.maxhp * .15))
            self.assertEqual(u.eff['보호막'].dur, 1)

    def test_manual_carmen_heal_is_twelve_percent(self):
        b = battle(policy='manual')
        u = b.allies[0]
        u.hp = 1
        b.team_nova = 4
        plain = copy.deepcopy(b)
        plain.opts['nova'] = False
        plain.cast(plain.allies[0], plain.allies[0].d.skills['기본기'])
        b.cast(u, u.d.skills['기본기'])
        self.assertEqual(u.healed - plain.allies[0].healed, int(u.maxhp * .12))

    def test_explicit_effect_conditions_once_and_cooldown(self):
        b = battle()
        u = b.allies[0]
        ctx = Ctx(u, u, u.d.skills['기본기'])
        once = Line('[스킬 사용 후] (조건: 내 행동 후 [사용 스킬: 궁극기]) 자신에게 노바 포스 +2 {전투당 1회}', '궁극기', 'active')
        b.run_line(u, once, ctx)
        self.assertEqual(b.team_nova, 0)
        ctx.skill = u.d.skills['궁극기']
        b.run_line(u, once, ctx)
        b.run_line(u, once, ctx)
        self.assertEqual(b.team_nova, 2)
        cd = Line('[턴 시작 시] 자신에게 노바 포스 +2 {발동 후 2턴 재발동 불가}', '잠재력', 'potential')
        for action in (0, 1, 2):
            u.actions = action
            b.run_line(u, cd, ctx)
        self.assertEqual(b.team_nova, 6)

    def test_enemy_effect_depletes_target_team_to_zero(self):
        b = battle()
        u, foe = b.allies[0], b.foes[0]
        b.team_nova, b.enemy_nova = 1, 7
        ctx = Ctx(foe, foe, u.d.skills['기본기'])
        ctx.target, ctx.targets = u, [u]
        b.run_line(foe, Line('[스킬 사용 후] 스킬 대상에게 노바 포스 -2', '궁극기', 'active'), ctx)
        self.assertEqual((b.team_nova, b.enemy_nova), (0, 7))

    def test_legacy_switches_restore_omissions(self):
        b = battle(('white-pearl-luna',), policy='manual', mc=dict(
            nova_skill_gain=False, nova_slot_effects=False, nova_force_effects=False))
        u = b.allies[0]
        b.cast(u, u.d.trigger_skills['특수기'], extra=True, skip_lines=True)
        self.assertEqual(b.team_nova, 0)
        b.team_nova = 4
        b.cast(u, u.d.skills['기본기'])
        self.assertEqual(u.shield_given, 0)
        b.run_line(u, Line('[턴 시작 시] 자신에게 노바 포스 +2', '잠재력', 'potential'), Ctx(u, u, None))
        self.assertEqual(b.team_nova, 0)

    def test_support_measurement_does_not_change_battle(self):
        plain = measure('36-36', 2, 7, None)
        measured = audit_measure('36-36', 2, 7, None)
        self.assertEqual(plain['summary'], measured['summary'])
        self.assertEqual(plain['casts'], measured['casts'])
        for name, values in plain['targets'].items():
            self.assertEqual(values, {k: measured['targets'][name][k] for k in values})
        self.assertAlmostEqual(sum(v['shield_received'] for v in measured['targets'].values()),
                               sum(v['shield_given'] for v in measured['targets'].values()))


if __name__ == '__main__':
    low_priority()
    if '--mutations' in sys.argv:
        caught = []
        for flag, test in [('nova_skill_gain', 'test_reactions_pay_declared_gain'),
                           ('nova_slot_effects', 'test_manual_slot_shield_matches_heal_policy'),
                           ('nova_force_effects', 'test_explicit_effect_conditions_once_and_cooldown')]:
            with patch.dict(MC_OPTS, {flag: False}):
                result = unittest.TextTestRunner().run(NovaGaugeTest(test))
            caught.append(bool(result.failures) and not result.errors)
            print(flag, 'mutation detected:', caught[-1])
        sys.exit(0 if all(caught) else 1)
    unittest.main(verbosity=2)
