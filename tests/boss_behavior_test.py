"""A different display name/model uses the same registered behavior, with mutants."""
import copy
from contextlib import contextmanager
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
from battlesim import api, datafile
from battlesim.starsavior import cosmo_raid as C
from battlesim.starsavior.boss_registry import monster_behaviors
from battlesim.starsavior.foe import FoeDef, load_foe
import guild_khan_rotation_test as khan


@contextmanager
def catalog_with(value):
    original = datafile.load
    api.clear_engine_caches()
    with patch.object(datafile, 'load', side_effect=lambda name, *a, **kw:
                      value if name == 'boss_catalog' else original(name, *a, **kw)):
        yield
    api.clear_engine_caches()


class BossBehaviorTest(unittest.TestCase):
    def tearDown(self):
        C.use_data(None)
        api.clear_engine_caches()

    def test_registered_switch_audit_detects_removed_registration(self):
        from rules_test import test_alt_legacy_keys_in_code
        catalog = copy.deepcopy(datafile.load('boss_catalog'))
        with catalog_with(catalog):
            self.assertTrue(test_alt_legacy_keys_in_code()[0])
            spec = catalog['behaviorProfiles']['overclock_heat']['stun_flags']
            spec['value'] = 'invalid-value'
            self.assertFalse(test_alt_legacy_keys_in_code()[0])
            spec['value'] = 'client'
            catalog['monsters']['카본펑크 칸']['profiles'] = []
            self.assertFalse(test_alt_legacy_keys_in_code()[0])

    def test_registered_other_name_runs_overclock_heat_and_se(self):
        catalog = copy.deepcopy(datafile.load('boss_catalog'))
        alias = '등록 시험 보스'
        catalog['monsters'][alias] = copy.deepcopy(catalog['monsters']['카본펑크 칸'])
        original = khan.build_waves
        def renamed(*a, **kw):
            waves, meta = original(*a, **kw)
            for wave in waves:
                for d in wave:
                    if d.boss:
                        d.name = alias
                        d.boss_behaviors = monster_behaviors(alias)
            return waves, meta
        checks = ('test_overclock_threshold', 'test_overheat_threshold',
                  'test_overheat_stun_and_debuff_stats', 'test_se_rng_and_immunity_order')
        with catalog_with(catalog), patch.object(khan, 'build_waves', side_effect=renamed):
            for check in checks:
                with self.subTest(check=check):
                    getattr(khan.KhanTest(check), check)()
            # Registration removal must make every behavior check fail.
            catalog['monsters'][alias]['profiles'] = []
            for check in checks:
                with self.subTest(mutant=check), self.assertRaises(AssertionError):
                    getattr(khan.KhanTest(check), check)()

        # The extractor chooses the same guaranteed-SE validation for the new name.
        from tools.build_foe_auto import unit_rules
        raw = {'s': [{'ef': ['[스킬 사용 후] 자신에게 〈속도 증가〉 (2턴)']}]}
        se = {'skill': [{'m_BuffTargetType': 'NSETT_SELF', 'm_SEStrID': 'test',
                        'm_Condition': {'m_fActiveRate': 10000}, 'm_fBuffActiveRate': 5000}]}
        with catalog_with(catalog), self.assertRaisesRegex(ValueError, alias + ' 효과 확률 변경'):
            unit_rules({'n': alias, 'sk': [0]}, raw, {'m_listSkill': ['skill']}, {}, {}, {}, se, {})

    def test_other_client_model_and_stage_name_attach_profiles(self):
        catalog = copy.deepcopy(datafile.load('boss_catalog'))
        catalog['clientModels']['registered_model'] = catalog['clientModels']['baskerville']
        catalog['monsters']['등록 침식 보스'] = catalog['monsters']['벨그라스']
        raw = copy.deepcopy(load_foe())
        seen = set()
        with catalog_with(catalog):
            for i, row in enumerate(raw['u']):
                if row.get('client_model') == 'baskerville':
                    before = FoeDef(raw, i).boss_behaviors
                    row['client_model'] = 'registered_model'
                    self.assertEqual(FoeDef(raw, i).boss_behaviors, before)
                    seen.add('model')
                if row['n'] == '벨그라스':
                    from battlesim.starsavior.belgras_se import normalize
                    row['n'] = '등록 침식 보스'
                    d = FoeDef(raw, i)
                    self.assertEqual(sum(x.eff['kind'] == 'belgras_fixed' for x in normalize(d, d.lines)), 50)
                    seen.add('stage')
        self.assertEqual(seen, {'model', 'stage'})

    def test_registered_other_cosmo_boss_reuses_model_and_hooks(self):
        C.use_data(ROOT/'data/cosmo_seasons/1022.json')
        team = ['gwen', 'fei', 'professor-m', 'amora']
        options = {'build': 'standard', 'seed': 7, 'n_runs': 2}
        before = api.simulate(team, {'cosmo_raid': {'boss': 'belgras', 'step': 3}}, options)
        catalog = copy.deepcopy(datafile.load('boss_catalog'))
        catalog['cosmo']['registered_boss'] = copy.deepcopy(catalog['cosmo']['belgras'])
        value = copy.deepcopy(C.load())
        boss = next(b for b in value['bosses'] if b['key'] == 'belgras')
        boss.update(key='registered_boss', name='등록 코스모 보스')
        value['season']['bossOrder'][0] = boss['key']
        encounter = {'cosmo_raid': {'boss': boss['key'], 'step': 3}}
        with catalog_with(catalog), patch.object(C, 'load', return_value=value):
            waves, _ = C.build_waves(boss['key'], 3)
            self.assertEqual(waves[0][1].name, boss['name'])
            self.assertEqual(waves[0][1].key, 'cosmo:registered_boss')
            after = api.simulate(team, encounter, options)
            self.assertGreater(after['outcome']['progress'], 0)
            self.assertEqual(after['outcome'], before['outcome'])
            self.assertEqual(after['prog_runs'], before['prog_runs'])
            self.assertEqual(after['cosmo_raid']['ctl'], before['cosmo_raid']['ctl'])
            self.assertGreater(sum(after['cosmo_raid']['ctl'].values()), 0)
            catalog['cosmo']['registered_boss']['mechanics'] = []
            api.clear_engine_caches()
            mutant = api.simulate(team, encounter, options)
            self.assertNotEqual(mutant['cosmo_raid']['ctl'], before['cosmo_raid']['ctl'])


if __name__ == '__main__':
    unittest.main()
