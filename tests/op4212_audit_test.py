"""Diagnostics must use client result statistics without altering combat."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from tools import ingame_check as check
from tools.op4212_audit import measure, compare


class DiagnosticsTest(unittest.TestCase):
    def test_uncertain_turn_is_not_used_as_exact_measurement(self):
        trials = [dict(result='wipe', actions=10, dealt=100, taken=200),
                  dict(result='wipe', actions=20, dealt=300, taken=600),
                  dict(result='clear', actions=30, dealt=900, taken=1200)]
        r = compare(trials, [dict(actions=10, dealt=200, taken=300),
                             dict(actions=None, dealt=300, taken=600)])
        lost = r['lost']
        self.assertEqual(lost['taken_per_turn']['observed_n'], 1)
        self.assertEqual(lost['taken_per_turn']['observed_indices'], [1])
        self.assertEqual(lost['taken_per_turn']['observed_percentiles'], [1])
        self.assertAlmostEqual(lost['taken_per_turn']['sim_over_real_mean'], 25 / 30)
        self.assertEqual(lost['dealt']['observed_percentiles'], [.5, 1])
        self.assertEqual(r['all']['dealt']['observed_percentiles'], [1 / 3, 2 / 3])

    def test_turn_rates_use_result_screen_damage(self):
        # Real simulation with deaths/overkill, not a fixture mirroring the helper.
        r = check.run('eq3219', runs=3, seed=7, bs_real=True)
        actions = r['sim_ally_actions']  # rounded; exact total comes from enemy+ally counter
        self.assertGreater(actions, 0)
        self.assertGreater(r['sim_stat_taken'], r['sim_taken'])
        self.assertGreater(r['sim_stat_dealt'], 0)
        total = r['sim_total_actions']
        self.assertAlmostEqual(r['sim_taken_per_global_turn'], r['sim_stat_taken'] / total, delta=1)
        self.assertAlmostEqual(r['sim_dealt_per_global_turn'], r['sim_stat_dealt'] / total, delta=1)
        self.assertEqual(r['turn_damage_basis'], 'battle_stat')
        self.assertEqual(r['ally_action_basis'], 'estimated_from_simulation_share')

    def test_observer_preserves_rng_and_collects_real_paths(self):
        expected = check.run('eq3219', runs=2, seed=7, bs_real=True)
        r = measure('eq3219', 2, 7, None)
        self.assertEqual(r['summary'], expected)
        self.assertEqual(len(r['trials']), 2)
        self.assertTrue(r['hits'])
        self.assertTrue(r['casts'])
        self.assertEqual(sum(g['calculations'] for g in r['skill_damage']), len(r['hits']))
        self.assertEqual({h['side'] for h in r['hits']}, {0, 1})
        self.assertTrue(all(t['actions'] > t['ally_actions'] > 0 for t in r['trials']))
        for i, trial in enumerate(r['trials']):
            self.assertEqual(trial['taken'], sum(u['taken'] for u in trial['units'].values()))
            actual_casts = sum(sum(u['casts'].values()) for u in trial['units'].values())
            self.assertEqual(sum(c['accepted'] for c in r['casts'] if c['run'] == i and c['side'] == 0), actual_casts)
        self.assertAlmostEqual(sum(t['taken'] for t in r['trials']) / 2,
                               expected['sim_stat_taken'], delta=2)
        for name, unit in expected['healing'].items():
            self.assertAlmostEqual(sum(t['units'][name]['heal'] for t in r['trials']) / 2,
                                   unit['heal_raw'], delta=.5)


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        # Restore precisely the old call site's d/t inputs in memory.
        src = Path(check.__file__).read_text(encoding='utf-8')
        good = 'turn_comparison(dealt, taken, turn, stat_d, stat_t, acts,'
        assert good in src
        ns = dict(check.__dict__)
        exec(compile(src.replace(good, 'turn_comparison(dealt, taken, turn, d, t, acts,'),
                     check.__file__, 'exec'), ns)
        with patch.object(check, 'run', ns['run']):
            result = unittest.TextTestRunner().run(unittest.TestSuite([
                DiagnosticsTest('test_turn_rates_use_result_screen_damage')]))
        detected = len(result.failures) == 1 and not result.errors
        print('Old HP-clamped comparison detected:', detected)
        import tools.op4212_audit as audit
        audit_src = Path(audit.__file__).read_text(encoding='utf-8')
        for old, new, function, test in (
            ('casts.append(row)', 'pass  # observation disabled', 'measure',
             'test_observer_preserves_rng_and_collects_real_paths'),
            ('heal=u.healed_raw', 'heal=u.healed', 'measure',
             'test_observer_preserves_rng_and_collects_real_paths'),
            ('def flatten(row):', "def flatten(row):\n        row = dict(row, actions=row.get('actions') or 1)",
             'compare', 'test_uncertain_turn_is_not_used_as_exact_measurement'),
        ):
            assert old in audit_src
            ns = dict(audit.__dict__)
            exec(compile(audit_src.replace(old, new), audit.__file__, 'exec'), ns)
            with patch.dict(globals(), {function: ns[function]}):
                result = unittest.TextTestRunner().run(unittest.TestSuite([DiagnosticsTest(test)]))
            caught = len(result.failures) == 1 and not result.errors
            detected = detected and caught
            print(function, 'mutation detected:', caught)
        sys.exit(0 if detected else 1)
    unittest.main(verbosity=2)
