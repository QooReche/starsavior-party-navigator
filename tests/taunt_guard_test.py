"""Taunt lifetime and real defensive skill contracts; no private fixtures."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, give, unit
from battlesim.mc import Ctx, MC_OPTS
from battlesim.metrics import unit_def
from battlesim.starsavior.parser import Line
from tools.ingame_check import low_priority


class TauntDurationTest(unittest.TestCase):
    def setup_reaction(self, legacy=False, immune=False, aoe=False):
        d = unit_def('white-pearl-luna')
        b = battle([d, unit('protected', hp=10**7)],
                   [unit('attacker', hp=10**8, cr=10000,
                         immune=['도발'] if immune else [],
                         skills=[dict(slot='기본기', dm=100, all=aoe),
                                 dict(slot='특수기', dm=100, cd=2)])],
                   mc=dict(toughness='off', **({'taunt_skill_end_duration': False} if legacy else {})),
                   opts={'coop': False, 'nova': False}, timeline=True)
        luna, ally = b.allies
        foe = b.foes[0]
        b.fire(luna, 'battle_start', Ctx(luna, luna, None))
        luna.cd['특수기'] = 0
        foe.cd['특수기'] = 0
        # Eliminate targeting and effect-hit randomness, retain real skills,
        # critical-hit reactions, buff application and owner turn ticking.
        b.pick_attack_target = lambda u, sk=None: ally if u is foe else foe
        b.roll_hit = lambda owner, ctx, x, name: name not in x.d.immune
        return b, luna, ally, foe

    def test_reaction_taunt_survives_then_forces_exactly_one_basic(self):
        b, luna, _, foe = self.setup_reaction()
        b.act(foe)
        self.assertEqual(luna.cast_count['특수기(추가)'], 1)
        self.assertTrue(foe.has('도발'))
        self.assertEqual(foe.eff['도발'].dur, 1)
        self.assertGreater(luna.shield_total(), 0)
        b.act(foe)
        actions = [r for r in b.timeline if r.get('actor') == foe.name]
        self.assertEqual(actions[-1]['skill'], '기본기')
        self.assertEqual(actions[-1]['targets'], [luna.name])
        self.assertFalse(foe.has('도발'))

    def test_reapplication_updates_source_and_preserves_one_turn(self):
        b, luna, ally, foe = self.setup_reaction()
        give(foe, '도발', src=ally, harmful=True, dur=1)
        b.act(foe)
        self.assertTrue(foe.has('도발'))
        self.assertIs(foe.eff['도발'].src, luna)
        self.assertEqual(foe.eff['도발'].dur, 1)

    def test_legacy_reproduces_immediate_reaction_expiry(self):
        b, luna, _, foe = self.setup_reaction(legacy=True)
        b.act(foe)
        self.assertEqual(luna.cast_count['특수기(추가)'], 1)
        self.assertFalse(foe.has('도발'))

    def test_immune_still_gets_shield_reaction_but_no_taunt(self):
        b, luna, _, foe = self.setup_reaction(immune=True)
        b.act(foe)
        self.assertGreater(luna.shield_total(), 0)
        self.assertFalse(foe.has('도발'))

    def test_ultimate_outside_target_turn_expires_after_next_action(self):
        b, luna, _, foe = self.setup_reaction()
        b.cast(luna, luna.d.skills['궁극기'], target=foe)
        self.assertTrue(foe.has('도발'))
        self.assertFalse(foe.eff['도발'].fresh)
        b.act(foe)
        self.assertFalse(foe.has('도발'))
        self.assertEqual(foe.cast_count['기본기'], 1)

    def test_dead_taunter_does_not_force_basic(self):
        b, luna, _, foe = self.setup_reaction()
        give(foe, '도발', src=luna, harmful=True, dur=1)
        luna.dead = True
        b.act(foe)
        self.assertEqual(foe.cast_count['특수기'], 1)

    def test_taunted_aoe_basic_still_hits_all(self):
        b, luna, ally, foe = self.setup_reaction(aoe=True)
        give(foe, '도발', src=luna, harmful=True, dur=1)
        b.act(foe)
        action = next(r for r in b.timeline if r.get('actor') == foe.name)
        self.assertEqual(action['skill'], '기본기')
        self.assertEqual(action['targets'], [luna.name, ally.name])

    def test_skill_start_application_does_not_get_new_grace(self):
        b, luna, _, foe = self.setup_reaction()
        ln = Line('[스킬 사용 시작 시] 스킬 대상에게 〈도발〉 (1턴)', '궁극기', 'active')
        ctx = Ctx(luna, luna, luna.d.skills['궁극기'])
        ctx.target, ctx.targets = foe, [foe]
        foe.acting = True
        b.run_line(luna, ln, ctx)
        self.assertFalse(foe.eff['도발'].fresh)


class DefensiveSkillsTest(unittest.TestCase):
    def setup_carmen(self):
        b = battle([unit_def('wedding-carmen'),
                    unit('tank', role='디펜더', hp=100000, atk=100),
                    unit('damage', hp=100000, atk=100000)],
                   [unit('enemy', hp=10**8)], mc={'toughness': 'off'},
                   opts={'coop': False, 'nova': False})
        carmen, tank, damage = b.allies
        b.fire(carmen, 'battle_start', Ctx(carmen, carmen, None))
        carmen.cd['특수기'] = 99
        return b, carmen, tank, damage, b.foes[0]

    def test_oath_highest_attack_and_only_single_oath_hit_shares(self):
        for target, aoe, shared in [('damage', False, True), ('tank', False, False),
                                    ('damage', True, False)]:
            with self.subTest(target=target, aoe=aoe):
                b, carmen, tank, damage, enemy = self.setup_carmen()
                self.assertTrue(damage.has('사랑의 서약(해제불가)'))
                self.assertFalse(tank.has('사랑의 서약(해제불가)'))
                sk = enemy.d.skills['기본기']
                sk.all = aoe
                pieces = []
                orig = b.apply_damage
                def record(a, v, dmg, kind, **kw):
                    pieces.append((v, kind, dmg))
                    return orig(a, v, dmg, kind, **kw)
                with patch.object(b, 'apply_damage', record):
                    b.cast(enemy, sk, target=damage if target == 'damage' else tank)
                guard = [r for r in pieces if r[1] == 'guard']
                self.assertEqual(bool(guard), shared)
                if shared:
                    self.assertIs(guard[0][0], carmen)
                    # 1850 base * 40%, then the guardian's own defense.
                    self.assertEqual(guard[0][2], int(740 * 3000 / (3000 + b.def_stat(carmen))))

    def test_carmen_heal_and_shield_use_caster_hp(self):
        b, carmen, _, damage, _ = self.setup_carmen()
        damage.hp = 1
        b.cast(carmen, carmen.d.trigger_skills['특수기'], extra=True, target=damage)
        self.assertEqual(damage.hp - 1, int(carmen.maxhp * .15 * 1.2))
        self.assertEqual(damage.shield_total(), int(carmen.maxhp * .20))
        damage.hp = 1
        b.cast(carmen, carmen.d.skills['궁극기'], target=damage)
        self.assertEqual(damage.hp - 1, int(carmen.maxhp * .23 * 1.2))


if __name__ == '__main__':
    low_priority()
    if '--mutations' in sys.argv:
        with patch.dict(MC_OPTS, taunt_skill_end_duration=False):
            result = unittest.TextTestRunner().run(
                unittest.defaultTestLoader.loadTestsFromTestCase(TauntDurationTest))
        caught = len(result.failures) == 2 and not result.errors
        print('Premature taunt expiry mutation detected:', caught)
        sys.exit(0 if caught else 1)
    unittest.main(verbosity=2)
