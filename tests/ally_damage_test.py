"""Skill-local chain damage, TURN diagnostics, and non-invasive counters."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p5_test import battle, unit, give
from battlesim.mc import Ctx, MC_OPTS
from battlesim.starsavior.data import get_db
from battlesim.starsavior.parser import UnitDef
from tools.ingame_check import turn_comparison, run
from tools.ally_damage_audit import measure


class ChainDamageTest(unittest.TestCase):
    def damage(self, *, legacy=False, source=True, targeted=0.0):
        b = battle([unit('a', atk=1000)], [unit('v', hp=100000, df=0)],
                   mc={'chain_skill_damage_up': False} if legacy else {})
        a, v = b.allies[0], b.foes[0]
        ctx = Ctx(a, a if source else v, a.d.skills['기본기'])
        ctx.target, ctx.targets = v, [v]
        ctx.inc = 0.15
        ctx.local_by[v]['inc'] = targeted
        give(a, 'buff', {'피해 증가': 20})
        b.chain(a, dict(target='스킬 대상', stat='atk', coef=0.4), ctx)
        return v.taken

    def test_skill_local_stat_is_added_to_live_damage_up(self):
        self.assertEqual(self.damage(), 999)  # 1000*.4*1.85*(1+.2+.15)

    def test_target_local_stat_is_included(self):
        self.assertEqual(self.damage(targeted=0.5), 1369)

    def test_legacy_is_exact(self):
        self.assertEqual(self.damage(legacy=True), 888)

    def test_reacting_defender_does_not_inherit_incoming_skill_stat(self):
        self.assertEqual(self.damage(source=False, targeted=0.5), 888)

    def test_cristelle_ultimate_chain_uses_level_bonus(self):
        totals = []
        for legacy in (True, False):
            d = UnitDef(get_db(), 'cristelle')
            b = battle([d], [unit('v', hp=10**8, df=0)],
                       mc={'chain_skill_damage_up': False} if legacy else {}, opts={'coop': False, 'nova': False})
            a, v = b.allies[0], b.foes[0]
            give(v, 'test debuff', harmful=True)
            received = []
            original = b.apply_damage
            def record(src, target, dmg, kind, **kw):
                if kind == 'chain':
                    received.append(dmg)
                return original(src, target, dmg, kind, **kw)
            with patch.object(b, 'apply_damage', record):
                b.cast(a, a.d.skills['궁극기'], target=v)
            self.assertEqual(len(received), 1)
            totals.append(received[0])
        self.assertAlmostEqual(totals[1] / totals[0], 1.15, delta=0.001)


class TurnTest(unittest.TestCase):
    def test_global_turn_and_estimated_ally_share(self):
        r = turn_comparison(1000, 400, 40, 500, 300, 10, 20)
        self.assertEqual(r['sim_total_actions'], 30)
        self.assertEqual(r['sim_total_actions_vs_turn'], 0.75)
        self.assertEqual(r['real_taken_per_global_turn'], 10)
        self.assertEqual(r['sim_taken_per_global_turn'], 10)
        self.assertAlmostEqual(r['real_estimated_ally_actions'], 40 / 3)
        self.assertAlmostEqual(r['estimated_ally_damage_ratio'], 1.5)

    def test_zero_actions_have_no_fabricated_rate(self):
        r = turn_comparison(0, 0, 0, 0, 0, 0, 0)
        self.assertIsNone(r['estimated_ally_damage_ratio'])
        self.assertIsNone(r['sim_taken_per_global_turn'])

    def test_audit_preserves_battle_result(self):
        self.assertEqual(run('36-36', runs=2, seed=7, bs=True),
                         measure('36-36', 2, 7, None)['summary'])


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        with patch.dict(MC_OPTS, chain_skill_damage_up=False):
            result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(ChainDamageTest))
        caught = len(result.failures) == 3 and not result.errors
        print('Legacy omission detected:', caught)
        sys.exit(0 if caught else 1)
    unittest.main(verbosity=2)
