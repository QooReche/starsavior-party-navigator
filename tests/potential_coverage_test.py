"""Whole-table audit and synthetic executions; no account data."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from battlesim import api, web
from battlesim.mc import Ctx, support_report
from battlesim.starsavior import myinfo_combat as combat
from battlesim.starsavior.data import get_db
from simkit import battle, unit, give
from myinfo_combat_test import definition, SCREEN
from tools.runtime import static_path_or_none
from tools.build_growth import build_growth, STAT
from tools.build_myinfo_combat import build


class CoverageTests(unittest.TestCase):
    def setUp(self):
        api._UNIT_CACHE.clear()

    def test_every_table_id_level_and_effect_accounted(self):
        static = static_path_or_none()
        if static is None:
            self.skipTest('STARSAVIOR_STATIC 없음')
        load = lambda name: json.loads((static / 'tables' / (name + '.json')).read_text(encoding='utf8'))['Data']
        grown, built = build_growth(static), build(static)
        ids = {str(p['PotenId']) for p in load('SE_POTENTIAL_TEMPLET')}
        self.assertEqual(ids, set(grown['potentials']))
        self.assertEqual(ids, set(built['potentials']))
        self.assertEqual(ids, set(built['potential_names']))
        self.assertTrue(all(built['potential_names'].values()))
        self.assertEqual(len(ids), 188)  # 26610546, includes 25004
        levels = load('POTENTIAL_LEVEL_GROUP_TEMPLET')
        checked = 0
        for p in load('SE_POTENTIAL_TEMPLET'):
            pid = str(p['PotenId'])
            for row in (r for r in levels if r['PotenLevelGroupId'] == p['PotenLevelGroupId']):
                lv = str(row['PotenLevelValue'])
                with self.subTest(pid=pid, level=lv):
                    self.assertIn(lv, grown['potentials'][pid])
                    self.assertIn(lv, built['potentials'][pid])
                    b = built['potentials'][pid][lv]
                    self.assertEqual(len(row.get('PotenLevelSe', [])), len(b['lines']))
                    expected = {}
                    for st in row.get('PotenLevelStat', []):
                        key = STAT.get(st['PotenLevelStatType'])
                        value = st.get('PotenLevelStatRate', st.get('PotenLevelStatValue', 0))
                        if key:
                            expected[key] = expected.get(key, 0) + value
                        else:
                            self.assertEqual(b['stats'][st['PotenLevelStatType']], value)
                            self.assertIn(st['PotenLevelStatType'], {'NST_SUPER_ARMOR', *combat.POTENTIAL_STAT_PROPS})
                    self.assertEqual(grown['potentials'][pid][lv], expected)
                    d = definition(potentials=[(int(pid), int(lv))])
                    gaps = [x for x in support_report([d]) if x['slot'] == '잠재력']
                    if gaps:
                        self.assertIn(pid + '/' + lv, built['potential_unsupported'])
                        self.assertTrue(all(built['potential_names'][pid] in x['raw'] for x in gaps))
                    else:
                        self.assertNotIn(pid + '/' + lv, built['potential_unsupported'])
                    checked += 1
        self.assertEqual(checked, 220)
        artifact = combat.combat_data()
        self.assertEqual(built['potentials'], artifact['potentials'])
        self.assertEqual(grown, json.loads((ROOT / 'data/growth.json').read_text(encoding='utf8')))

    def test_new_25004_break_condition_stacks_and_damage(self):
        d = definition(potentials=[(25004, 1)], skills={'basic': 1, 'passive': 0})
        b = battle([d], [unit('dummy', hp=10**8, sa=3)], opts={'coop': False, 'nova': False})
        a, target = b.allies[0], b.foes[0]
        b.cast(a, d.skills['기본기'], target=target)
        self.assertEqual(a.mods()['atkp'], 0)
        target.sa, target.broken = 0, True
        for _ in range(7):
            b.cast(a, d.skills['기본기'], target=target)
        self.assertAlmostEqual(a.mods()['atkp'], .25)
        self.assertGreater(target.taken, 0)
        self.assertGreater(b.progress(), 0)

    def test_missing_public_effects_execute_and_expire(self):
        # Battle-start, own-action, own-turn, chance, remove, critical and hit-count branches.
        d = definition(potentials=[(11044, 1), (30002, 1), (30003, 1), (31001, 1),
                                   (31003, 1), (32001, 1), (34001, 1), (34003, 1), (35001, 1), (35003, 1)])
        b = battle([d], [unit('dummy', hp=10**8)], opts={'coop': False, 'nova': False})
        a, foe = b.allies[0], b.foes[0]
        b.fire(a, 'battle_start', Ctx(a, a, None))
        self.assertTrue(a.has('면역'))
        self.assertAlmostEqual(a.mods()['defp'], .3)
        self.assertAlmostEqual(a.mods()['er'], .3)
        with patch.object(b.rng, 'random', return_value=0):
            b.fire(a, 'own_ts', Ctx(a, a, None))
        self.assertAlmostEqual(a.mods()['cr'], .2)
        self.assertAlmostEqual(a.mods()['inc_slot']['기본기'], .15)
        a.d.stats['cr'] = 10000
        b.cast(a, d.skills['기본기'], target=foe)
        self.assertAlmostEqual(a.mods()['atkp'], .08)
        self.assertEqual(a.mods()['spdf'], 3)
        b.fire(a, 'own_te', Ctx(a, a, None))
        self.assertAlmostEqual(a.mods()['cr'], .05)
        self.assertEqual(a.mods()['inc_slot'].get('기본기', 0), 0)
        b.cast(foe, foe.d.skills['기본기'], target=a)
        self.assertAlmostEqual(a.mods()['defp'], .33)
        self.assertGreater(b.progress(), 0)

    def test_25003_counts_debuffs_and_41004_numeric_override(self):
        d = definition(potentials=[(25003, 1), (41004, 1)])
        b = battle([d], [unit('dummy', hp=10**8)], opts={'coop': False, 'nova': False})
        a, foe = b.allies[0], b.foes[0]
        b.fire(a, 'battle_start', Ctx(a, a, None))
        self.assertAlmostEqual(a.mods()['atkp'], .02)
        self.assertAlmostEqual(a.mods()['cd'], .02)
        self.assertAlmostEqual(a.mods()['er'], .02)
        for n in range(3):
            give(a, 'synthetic debuff %d' % n, harmful=True)
        b.cast(foe, foe.d.skills['기본기'], target=a)
        self.assertAlmostEqual(a.mods()['er'], .17)
        self.assertGreater(a.taken, 0)

    def test_combat_rates_and_cache_rule_boundary(self):
        entries = [(22009, 1), (22010, 1), (30006, 1), (41001, 1), (41002, 1), (23019, 1), (23024, 1)]
        payload = dict(units=[dict(key='wedding-epindel', stats_override=SCREEN, stats_final=True,
                                  myinfo_combat={'potentials': entries})])
        on = api._norm_party(payload, get_db(), 'fixed', 'standard', {'myinfo_potential_coverage': True})[0][0]
        off = api._norm_party(payload, get_db(), 'fixed', 'standard', {'myinfo_potential_coverage': False})[0][0]
        self.assertIsNot(on, off)
        b = battle([on], [unit('dummy')])
        m = b.allies[0].mods()
        expected = {'coop': .015, 'revenge': .215, 'preempt': .2, 'vampirism': .15}
        for k, v in expected.items():
            self.assertAlmostEqual(m[k], v, msg=k)
        self.assertAlmostEqual(m['inc_slot']['기본기'], .05)
        self.assertAlmostEqual(m['red']['궁극기'], .05)
        self.assertFalse(getattr(off, 'potential_props', {}))

    def test_new_arcana_unique_promotes_are_journey_only(self):
        data = combat.combat_data()['arcana_unique']
        self.assertEqual(len(data), 50)
        self.assertTrue(all(row['status'] == 'journey' and row['arcanas'] for row in data.values()))
        for aid in ('7102001', '7106101'):
            self.assertEqual(data[aid]['status'], 'journey')
            self.assertIn(aid, data[aid]['arcanas'])
        # Arcana ownership does not grant the event reward before it is learned.
        u = {'arcana': [7102001, 7106101], 'gauntlet': {'potentials': []}}
        self.assertEqual(combat.combat_input(u)['potentials'], [])
        u['gauntlet']['potentials'] = [[25004, 1, 0, 0]]
        self.assertEqual(combat.combat_input(u)['potentials'], [[25004, 1]])
        static = static_path_or_none()
        if static is not None:
            raw = json.loads((static / 'tables/ARCANA_UNIQUE_PROMOTE_TEMPLET.json').read_text(encoding='utf8'))['Data']
            self.assertEqual(set(data), {str(row['UniquePromoteId']) for row in raw})
            self.assertEqual(build(static)['arcana_unique'], data)

    def test_new_arcana_reward_candidates_enter_distinct_paths(self):
        # Public source candidates, not a claim that the missing event tables were verified.
        from battlesim.starsavior.myinfo_stats import final_stats
        info = json.loads((ROOT / 'tests/fixtures/myinfo_synthetic.json').read_text(encoding='utf8'))
        growth = json.loads((ROOT / 'data/growth.json').read_text(encoding='utf8'))
        u = copy.deepcopy(info['units'][0])
        u['gauntlet']['potentials'] = []
        base = final_stats(u, info, growth)
        u['gauntlet']['potentials'] = [[23038, 1, 0, 0]]
        learned = final_stats(u, info, growth)
        self.assertGreater(learned['stats']['atk'], base['stats']['atk'])
        self.assertEqual(learned['stats']['cd'] - base['stats']['cd'], 600)
        self.assertEqual(learned['combat']['potentials'], [[23038, 1]])
        u['gauntlet']['potentials'] = [[25004, 1, 0, 0]]
        se_only = final_stats(u, info, growth)
        self.assertEqual(se_only['stats'], base['stats'])
        self.assertEqual(se_only['combat']['potentials'], [[25004, 1]])

    def test_retaliation_chain_targets_attacker_and_rolls(self):
        for roll, expected in ((.49, True), (.5, False)):
            d = definition(potentials=[(40701, 1)])
            b = battle([d], [unit('attacker', hp=10**8), unit('bystander', hp=10**8)],
                       opts={'coop': False, 'nova': False})
            a, attacker, other = b.allies[0], b.foes[0], b.foes[1]
            with patch.object(b.rng, 'random', return_value=roll):
                b.cast(attacker, attacker.d.skills['기본기'], target=a)
            self.assertEqual(attacker.taken > 0, expected)
            self.assertEqual(other.taken, 0)
            if expected:
                self.assertGreater(b.progress(), 0)
            # The no-debuff condition excludes the reaction entirely.
            before = attacker.taken
            give(a, 'synthetic debuff', harmful=True)
            with patch.object(b.rng, 'random', return_value=0):
                b.cast(attacker, attacker.d.skills['기본기'], target=a)
            self.assertEqual(attacker.taken, before)

    def test_critical_reduction_requires_positive_toughness(self):
        damage = []
        for potential, toughness in ((False, 3), (True, 3), (True, 0)):
            d = definition(potentials=[(30004, 1)] if potential else [])
            attacker = unit('attacker', hp=10**8, cr=10000)
            attacker.stats['cd'] = 5000
            b = battle([d], [attacker], opts={'coop': False})
            a, foe = b.allies[0], b.foes[0]
            a.sa = toughness
            b.cast(foe, foe.d.skills['기본기'], target=a)
            damage.append(a.taken)
        self.assertGreater(damage[0], 0)
        self.assertLess(damage[1], damage[0])
        self.assertEqual(damage[2], damage[0])

    def test_named_unsupported_reaches_auto_and_manual(self):
        # A real unconfirmed potential, not just a hypothetical unknown ID.
        payload = dict(units=[dict(key='wedding-epindel', stats_override=SCREEN, stats_final=True,
                                  myinfo_combat={'potentials': [[11026, 1]]})])
        for fn in (web.run_auto, web.run_manual):
            result = json.loads(fn('clo/달 회랑/FLOOR 100', payload, 1, 3))
            self.assertIn('unsupported', result)
            self.assertTrue(any('재난 대응 프로토콜' in x['raw'] for x in result['unsupported']))
            self.assertTrue(any('지원하지 않음' in x['raw'] for x in result['unsupported']))
        # Recognized level but a parser gap must retain the name too.
        row = copy.deepcopy(combat.combat_data()['potentials']['25004']['1'])
        row['effects'] = ['[알 수 없는 시점] 자신에게 알 수 없는 효과']
        with patch.dict(combat.combat_data()['potentials']['25004'], {'1': row}):
            api._UNIT_CACHE.clear()
            gaps = support_report([definition(potentials=[(25004, 1)])])
            self.assertTrue(any('끝없는 종착점' in x['raw'] for x in gaps))

    def test_supplemental_bleeding_rolls(self):
        for roll, expected in ((0, True), (.21, False)):
            d = definition(potentials=[(32002, 1)])
            b = battle([d], [unit('dummy', hp=10**8)], opts={'coop': False, 'nova': False})
            a, foe = b.allies[0], b.foes[0]
            with patch.object(b.rng, 'random', return_value=roll):
                b.cast(a, d.skills['기본기'], target=foe)
            self.assertEqual(foe.has('출혈'), expected)
            self.assertGreater(b.progress(), 0)


def mutations():
    # Never modify source/artifacts on disk; each injected defect must fail an assertion.
    original_build = build
    def omit_id(static):
        result = original_build(static)
        del result['potentials']['25004']
        return result
    checks = [
        ('omit table ID', 'test_every_table_id_level_and_effect_accounted',
         patch(__name__ + '.build', omit_id)),
        ('remove new potential SE', 'test_new_25004_break_condition_stacks_and_damage',
         patch.dict(combat.combat_data()['potentials']['25004']['1'], lines=[])),
        ('drop supplemental SE', 'test_missing_public_effects_execute_and_expire',
         patch.dict(combat.combat_data()['potentials']['31001']['1'], lines=[])),
        ('drop combat stat', 'test_combat_rates_and_cache_rule_boundary',
         patch.dict(combat.POTENTIAL_STAT_PROPS, {'NST_RATE_REVENGE_ATTACK': '협공 확률'})),
        ('drop retaliation chance', 'test_retaliation_chain_targets_attacker_and_rolls',
         patch.dict(combat.combat_data()['potentials']['40701']['1']['chains']['1'], chance=1)),
        ('drop critical reduction', 'test_critical_reduction_requires_positive_toughness',
         patch.dict(combat.combat_data()['potentials']['30004']['1'], lines=[])),
        ('drop arcana link', 'test_new_arcana_unique_promotes_are_journey_only',
         patch.dict(combat.combat_data()['arcana_unique']['7106101'], arcanas={})),
        ('drop unsupported payload', 'test_named_unsupported_reaches_auto_and_manual',
         patch.object(web, '_potential_unsupported', lambda r: {})),
    ]
    for name, method, mutation in checks:
        with mutation:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(CoverageTests(method))
        if result.wasSuccessful():
            raise AssertionError('Mutation not caught: ' + name)
        print('Caught mutation:', name)


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main(verbosity=2)
