"""Synthetic shared-hit regression and non-invasive audit checks."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, give, unit
from battlesim.mc import Ctx, MC_OPTS
from tools import ingame_check as check
from tools.received_damage_audit import measure


class GuardNormalHitTest(unittest.TestCase):
    def hit(self, side=1, legacy=False, shield=False, force=False, reduction=False):
        defenders = [unit('target', df=1000), unit('guard', df=2000)]
        attacker = unit('attacker', atk=1000, cr=0 if force else 10000)
        attacker.stats['cd'] = 10000
        b = battle(defenders if side == 1 else [attacker],
                   [attacker] if side == 1 else defenders,
                   mc={'guard_normal_hit': False} if legacy else {})
        a = (b.foes if side == 1 else b.allies)[0]
        v, g = b.allies if side == 1 else b.foes
        give(g, '수호', {'피해 분담(수호)': 40})
        if reduction:
            give(g, '감소', {'피해 감소': 20})
        if shield:
            give(g, '보호막').shield = 100
        c = Ctx(a, v, a.d.skills['기본기'])
        c.targets = [v]
        c.force_crit = force
        b.deal(a, c)
        return b, a, v, g

    def test_ally_guard_is_normal_original_target_still_critical(self):
        _, a, v, g = self.hit()
        # Base 1850: target 60% * .75 * 2; guard 40% * .6.
        self.assertEqual(v.taken, 1665)
        self.assertEqual(g.taken, 444)
        self.assertEqual(a.dmg, 2109)

    def test_enemy_guard_also_normal(self):
        _, _, v, g = self.hit(side=0)
        self.assertEqual((v.taken, g.taken), (1665, 444))

    def test_forced_critical_does_not_crit_shared_piece(self):
        _, _, v, g = self.hit(force=True)
        self.assertEqual((v.taken, g.taken), (1665, 444))

    def test_guard_defense_reduction_and_shield_still_apply(self):
        _, _, v, g = self.hit(shield=True, reduction=True)
        self.assertEqual(v.taken, 1665)
        self.assertEqual(g.taken, 355)
        self.assertEqual(g.maxhp - g.hp, 255)

    def test_legacy_restores_critical_transfer(self):
        _, _, v, g = self.hit(legacy=True)
        self.assertEqual((v.taken, g.taken), (1665, 888))


class AuditTest(unittest.TestCase):
    def test_conservation_and_no_combat_change(self):
        for stage in ('36-36', '37-3'):
            plain = check.run(stage, runs=2, seed=7, bs=True)
            measured = measure(stage, 2, 7, None)
            self.assertEqual(plain, measured['summary'])
            total = sum(r['taken'] for r in measured['damage'])
            self.assertAlmostEqual(total, sum(u['taken'] for u in measured['targets'].values()))
            for row in measured['damage']:
                self.assertGreaterEqual(row['taken'], 0)
            self.assertTrue(all(r['source'] for r in measured['damage']))


if __name__ == '__main__':
    check.low_priority()
    if '--mutations' in sys.argv:
        with patch.dict(MC_OPTS, guard_normal_hit=False):
            result = unittest.TextTestRunner().run(
                unittest.defaultTestLoader.loadTestsFromTestCase(GuardNormalHitTest))
        caught = len(result.failures) == 4 and not result.errors
        print('Legacy critical-sharing mutation detected:', caught)
        sys.exit(0 if caught else 1)
    unittest.main(verbosity=2)
