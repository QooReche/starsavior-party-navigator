"""Module reuse, archived boss rotation, and mutation-sensitive runtime parity."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import api, datafile
from battlesim.starsavior import guild
from battlesim.starsavior.boss_registry import expand, module
from tools.boss_modules import pack_guild, pack_cosmo
import guild_defense as gd

TEAM = ['gwen', 'fei', 'professor-m', 'amora']


class BossModulesTest(unittest.TestCase):
    def tearDown(self):
        api.clear_engine_caches()

    def test_reuse_all_archives(self):
        references = []
        for path in sorted((ROOT/'data/guild_seasons').glob('*.json')):
            packed = json.loads(path.read_text(encoding='utf-8'))
            self.assertIn('$module', packed['season']['boss'])
            full = guild.load(int(path.stem))
            self.assertEqual(expand(pack_guild(full)), full)
            self.assertEqual(gd.validate(full), [])
            references.append(packed['season']['boss']['$module'])
            for step in packed['steps']:
                for wave in step.get('waves', []):
                    for u in wave:
                        self.assertIn('$module', u)
                        self.assertNotIn('clientRules', u)
                        self.assertNotIn('definition', u)
        self.assertLess(len(set(references)), len(references))
        for path in (ROOT/'data/cosmo_seasons').glob('*.json'):
            full = expand(json.loads(path.read_text(encoding='utf-8')))
            self.assertEqual(expand(pack_cosmo(full)), full)
        # The former custom model is retained even though it is absent this season.
        old = expand(json.loads((ROOT/'data/cosmo_seasons/1022.json').read_text(encoding='utf-8')))
        self.assertTrue(old['belgras']['skills'])

    def test_other_boss_as_current_and_restore(self):
        original = datafile.load
        chosen = 30109
        old = guild.load(chosen)
        self.assertNotEqual(old['season']['boss']['name'], guild.load()['season']['boss']['name'])
        explicit = api.simulate(TEAM, {'guild': {'seasonId': chosen}},
                                {'build': 'standard', 'seed': 7, 'n_runs': 2})
        api.clear_engine_caches()
        def rotate(name, src=guild.SRC, *args, **kwargs):
            return {'seasonId': chosen} if name == 'guild_current' else original(name, src, *args, **kwargs)
        with patch.object(datafile, 'load', side_effect=rotate):
            current = guild.load()
            result = api.simulate(TEAM, {'guild': {}}, {'build': 'standard', 'seed': 7, 'n_runs': 2})
            self.assertEqual(result['outcome'], explicit['outcome'])
            self.assertEqual(result['prog_runs'], explicit['prog_runs'])
            self.assertGreater(result['outcome']['progress'], 0)
            self.assertEqual(gd.page_payload(current)['season']['id'], chosen)
            self.assertTrue(gd.foe_content(current)['tabs'][0]['stages'])
        api.clear_engine_caches()
        self.assertEqual(guild.load()['season']['id'], 30112)
        # Disabling the module resolution cannot silently fall back to the current boss.
        with patch('battlesim.starsavior.boss_registry.module', side_effect=ValueError('mutation')):
            with self.assertRaisesRegex(ValueError, 'mutation'):
                guild.load(chosen)

    def test_module_tampering_fails(self):
        packed = json.loads((ROOT/'data/guild_seasons/30112.json').read_text(encoding='utf-8'))
        key = packed['season']['boss']['$module']
        changed = copy.deepcopy(module(key))
        changed['engine'] = 'missing'
        api.clear_engine_caches()
        with patch.object(datafile, 'load', return_value=changed):
            with self.assertRaisesRegex(ValueError, '해시'):
                module(key)

    def test_retired_cosmo_model_from_module_season(self):
        from battlesim.starsavior import cosmo_raid
        options = {'build': 'standard', 'seed': 3, 'n_runs': 2}
        encounter = {'cosmo_raid': {'boss': 'belgras', 'step': 1, 'level': 0}}
        try:
            cosmo_raid.use_data(ROOT/'tests/fixtures/cosmo_raid_1022.json')
            before = api.simulate(TEAM, encounter, options)
            cosmo_raid.use_data(ROOT/'data/cosmo_seasons/1022.json')
            after = api.simulate(TEAM, encounter, options)
            self.assertGreater(after['outcome']['progress'], 0)
            self.assertEqual(after['outcome'], before['outcome'])
            self.assertEqual(after['prog_runs'], before['prog_runs'])
        finally:
            cosmo_raid.use_data(None)


if __name__ == '__main__':
    unittest.main()
