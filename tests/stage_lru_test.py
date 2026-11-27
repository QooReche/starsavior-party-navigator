"""Cross-batch ordinary encounter reuse, bounded keys and mutable enemy isolation."""
import pathlib
import random
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from battlesim import api, datafile
from battlesim.mc import Battle

STAGE = {'stage': 'clo/태양 회랑/FLOOR 250'}


class StageLRU(unittest.TestCase):
    def setUp(self):
        api.clear_engine_caches()

    def test_reuse_options_and_generation(self):
        raw = api._norm_encounter_raw
        with patch.object(api, '_norm_encounter_raw', wraps=raw) as build:
            a = api._norm_encounter(STAGE)
            b = api._norm_encounter(dict(STAGE))
            self.assertEqual(build.call_count, 1)
            self.assertIs(a[0][0][0], b[0][0][0])
            for option in ({'turn_limit': 10}, {'stage_fx': []}, {'max_turns': 17},
                           {'rules_override': {'coop': False}}, {'dataVersion': 'different'}):
                api._norm_encounter(dict(STAGE, **option))
            self.assertEqual(build.call_count, 6, 'every encounter option participates')
            datafile.clear()
            api._norm_encounter(STAGE)
            self.assertEqual(build.call_count, 7, 'data reload invalidates prepared definitions')

    def test_bounded_and_isolated(self):
        old = api._ENC_CACHE.maxsize
        api._ENC_CACHE.maxsize = 3
        try:
            for limit in range(8):
                api._norm_encounter(dict(STAGE, turn_limit=limit))
            self.assertEqual(len(api._ENC_CACHE), 3)
        finally:
            api._ENC_CACHE.maxsize = old
        a = api._norm_encounter(STAGE)
        a[0][0].pop(); a[4]['junk'] = True
        b = api._norm_encounter(STAGE)
        self.assertNotIn('junk', b[4])
        self.assertGreater(len(b[0][0]), len(a[0][0]))
        party, _ = api._norm_party(['amora'], api.get_db(), 'fixed', 'standard')
        first = Battle(party, b[0], random.Random(1)); first.spawn_wave()
        original = dict(b[0][0][0].stats)
        first.foes[0].hp = 0
        first.foes[0].d.stats['spd'] = 9999
        first.foes[0].d.passive['spdp'] = 99
        second = Battle(party, api._norm_encounter(STAGE)[0], random.Random(1)); second.spawn_wave()
        self.assertEqual(b[0][0][0].stats, original)
        self.assertGreater(second.foes[0].hp, 0)
        self.assertNotEqual(second.foes[0].d.stats['spd'], 9999)


if __name__ == '__main__':
    unittest.main()
