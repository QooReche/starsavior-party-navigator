"""Synthetic effective-level parity and stats integration, including legacy inputs."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from myinfo_stats_test import fixture, node_cases, ms


class EffectiveLevelTests(unittest.TestCase):
    def test_levels_and_stats(self):
        cases, descriptions, expected_levels = [], [], []
        for link_level in (1, 120, 199, 200, 201, 250):
            for role in ('unit', 'slot', 'source', 'both'):
                for own_level in (1, 23, 200):
                    u, info, growth = fixture()
                    u['level'] = own_level
                    info['star_link_level'] = link_level
                    info['star_link'] = dict(level=link_level,
                        source=[u['id']] if role in ('source', 'both') else [],
                        slots=[dict(index=0, id=0), dict(index=99, id=u['id'] if role in ('slot', 'both') else 900099)])
                    expected = link_level if role in ('slot', 'both') or role == 'source' and link_level >= 201 else own_level
                    origin = 'slot' if role in ('slot', 'both') else 'source' if role == 'source' and link_level >= 201 else 'unit'
                    self.assertEqual(ms.effective_level(u, info), expected)
                    self.assertEqual(ms.level_info(u, info), dict(level=expected, source=origin, missing=[]))
                    for rule in ('normal', 'fixed200'):
                        result = ms.final_stats(u, info, growth, rule, True)
                        level = next(s['level'] for s in result['breakdown']['sources'] if s['id'] == 'level')
                        self.assertEqual(level, 200 if rule == 'fixed200' else expected)
                        self.assertEqual(result['missing'], [])
                        # Independent legacy input at the expected level must yield the same stats.
                        old_info = {k: v for k, v in info.items() if k != 'star_link'}
                        old_info['star_link_level'] = expected
                        self.assertEqual(result['stats'], ms.final_stats(u, old_info, growth, rule)['stats'])
                        cases.append([u, info, growth, rule, True])
                    descriptions.append([u, info])
                    expected_levels.append(expected)
        self.assertEqual(node_cases(descriptions, 'effective_level'), expected_levels)
        self.assertEqual(node_cases(descriptions, 'level_info'), [ms.level_info(*x) for x in descriptions])
        self.assertEqual(node_cases(cases), [ms.final_stats(*x) for x in cases])

    def test_legacy_and_partial(self):
        u, info, growth = fixture()
        u['level'] = 23
        info.update(star_link_level=201, star_link=dict(level=201, source=[], slots=[]))
        cases = []
        for field in ('unit.level', 'star_link', 'star_link.level', 'star_link.source', 'star_link.slots'):
            unit, account = deepcopy(u), deepcopy(info)
            if field == 'unit.level':
                unit.pop('level')
            elif field == 'star_link':
                account.pop('star_link')
            else:
                account['star_link'].pop(field.split('.')[1])
            self.assertEqual(ms.effective_level(unit, account), 201)
            normal = ms.final_stats(unit, account, growth)
            self.assertIn('star_link.slots' if field == 'star_link' else field, normal['missing'])
            fixed = ms.final_stats(unit, account, growth, 'fixed200')
            self.assertFalse(any(s.startswith(('unit.level', 'star_link')) for s in fixed['missing']))
            cases.append([unit, account, growth])
        self.assertEqual(node_cases(cases), [ms.final_stats(*x) for x in cases])
        old = json.loads((ROOT / 'tests/fixtures/myinfo_legacy.json').read_text(encoding='utf-8'))
        for unit in old['units']:
            self.assertEqual(ms.effective_level(unit, old), old['star_link_level'])
            self.assertIn('unit.level', ms.level_info(unit, old)['missing'])

    def test_outside_slot_changes_real_stats(self):
        u, info, growth = fixture()
        u['level'] = 23
        info.update(star_link_level=201, star_link=dict(level=201, source=[], slots=[]))
        outside = ms.final_stats(u, info, growth)
        info['star_link']['slots'] = [dict(index=0, id=u['id'])]
        inside = ms.final_stats(u, info, growth)
        self.assertGreater(inside['stats']['atk'], outside['stats']['atk'])
        self.assertGreater(inside['stats']['hp'], outside['stats']['hp'])
        self.assertGreater(inside['power'], outside['power'])


if __name__ == '__main__':
    unittest.main()
