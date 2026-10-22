"""Optional breakdown parity and arithmetic; synthetic accounts only."""
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from myinfo_stats_test import fixture, node_cases
from battlesim.starsavior.myinfo_stats import final_stats, KEYS


class BreakdownTests(unittest.TestCase):
    def test_parity_sum_and_unchanged_result(self):
        rng = random.Random(42)
        cases = []
        info = json.loads((ROOT / 'tests/fixtures/myinfo_synthetic.json').read_text(encoding='utf8'))
        growth = json.loads((ROOT / 'data/growth.json').read_text(encoding='utf8'))
        for rule in ('normal', 'fixed200'):
            cases.extend([u, info, growth, rule, True] for u in info['units'])
        for n in range(80):
            u, i, g = fixture()
            i['star_link_level'] = rng.choice([1, 199, 200, 201, 343, 999])
            u['sigil'] = rng.randrange(3)
            u['resonance'] = rng.choice([0, 2, 10])
            u['skills']['passive'] = rng.randrange(4)
            u['gauntlet']['journey'] = [rng.randrange(2001) for _ in range(5)]
            u['gauntlet']['potentials'] = [[900101, 2, 0, 0], [900102, 1, 0, 0]]
            u['equip'] += [dict(item_id=900012, main=dict(stat='NST_ATK', value=11.5), subs=[])] * (n % 6)
            if n % 5 == 0:
                g['units'][str(u['id'])]['resonance_unlock'] = {'2': 150, '10': 220}
            cases.append([u, i, g, 'fixed200' if n % 2 else 'normal', True])
        js = node_cases(cases)
        for args, other in zip(cases, js):
            got = final_stats(*args)
            self.assertEqual(got, other)
            detail = got.pop('breakdown')
            self.assertEqual(got, final_stats(*args[:4]))
            for k in KEYS:
                s = detail['stats'][k]
                total = 0
                for v in s['components'].values():
                    total += v
                self.assertEqual(total, got['stats'][k])
                self.assertEqual(s['final'], got['stats'][k])
                self.assertEqual(s['components']['bundle'], s['x1'] * s['r1'] + s['x'] * s['r2'])

    def test_source_values_and_order(self):
        u, i, g = fixture()
        u['skills']['passive'] = 2
        r = final_stats(u, i, g, breakdown=True)
        rows = r['breakdown']['sources']
        self.assertEqual(next(s['values'] for s in rows if s['id'] == 'passive'), dict(atkP=400, hpP=600, defP=800))
        self.assertEqual(len([s for s in rows if s['id'] == 'tactics']), 13)
        atk = r['breakdown']['stats']['atk']
        self.assertEqual(atk['r1'], .03)
        self.assertEqual(atk['r2'], .19)
        self.assertEqual(atk['x1'], 115)
        self.assertEqual(atk['x'], 135.45)
        # Removing the R1/R2 interaction must change the claimed final sum.
        wrong = sum(v for k, v in atk['components'].items() if k != 'bundle')
        self.assertNotEqual(round(wrong), atk['final'])
        self.assertNotIn('breakdown', final_stats(u, i, g))


if __name__ == '__main__':
    unittest.main()
