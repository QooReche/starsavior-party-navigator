"""Synthetic combat regressions. No private account fixtures or output."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from battlesim.api import _norm_party
from battlesim.mc import Ctx, support_report
from battlesim.starsavior.data import get_db
from battlesim.starsavior import myinfo_combat as combat
from p5_test import battle, unit
from tools.ingame_check import low_priority


SCREEN = dict(atk=1000, hp=10000, spd=100, cr=0, cd=5000, eh=10000, er=0, **{'def': 100})


def definition(key='wedding-epindel', potentials=(), skills=None, enabled=True):
    payload = dict(skills=skills or dict(basic=1, special=1, ultimate=1, passive=1), potentials=list(potentials))
    return _norm_party([dict(key=key, build='none', stats_override=dict(SCREEN), stats_final=True,
                             myinfo_combat=payload)], get_db(), 'fixed', 'standard', {'myinfo_combat': enabled})[0][0]


class CombatTests(unittest.TestCase):
    def test_final_stats_not_doubled_and_toughness_added(self):
        d = definition('wedding-carmen', [(40005, 1), (11055, 1), (23007, 1)])
        for k, value in SCREEN.items():
            self.assertEqual(d.stats[k], value)
        self.assertEqual(d.passive['atkp'], 0)
        self.assertEqual(d.stats['sa'], 6)
        self.assertIsNone(d.build)

    def test_skill_damage_uses_selected_absolute_group(self):
        for level, expected in ((1, 0), (7, 8), (10, 15)):
            d = definition(skills=dict(basic=level))
            total = sum(x.eff['val'] for x in d.lines if x.slot == '기본기' and x.eff['kind'] == 'local')
            self.assertEqual(total, expected)

    def test_cooldown_and_unlearned_passive(self):
        low = definition(skills=dict(special=1, passive=0))
        high = definition(skills=dict(special=6))
        self.assertEqual((low.skills['특수기'].cd, high.skills['특수기'].cd), (4, 3))
        self.assertFalse(any(x.slot == '고유 패시브' for x in low.lines))

    def test_legacy_and_shared_database_untouched(self):
        before = copy.deepcopy(get_db().units['wedding-epindel'])
        d = definition(potentials=[(33001, 1)], skills=dict(basic=1), enabled=False)
        self.assertFalse(any(x.slot == '잠재력' for x in d.lines))
        self.assertEqual(sum(x.eff['val'] for x in d.lines if x.slot == '기본기' and x.eff['kind'] == 'local'), 15)
        definition(potentials=[(33001, 1)], skills=dict(basic=1))
        self.assertEqual(before, get_db().units['wedding-epindel'])

    def test_zero_unknown_and_duplicate_potentials(self):
        d = definition(potentials=[(40005, 0), (999999, 1)])
        self.assertFalse(any(x.slot == '잠재력' for x in d.lines))
        self.assertTrue(any(x['reason'] == 'data' for x in support_report([d])))
        with self.assertRaises(ValueError):
            definition(potentials=[(40005, 1), (40005, 1)])
        with self.assertRaises(ValueError):
            definition(skills=dict(basic=99))

    def test_attack_stacks_and_ultimate_reset(self):
        b = battle([definition(potentials=[(40005, 1)])], [unit('enemy', hp=10**8)], opts={'coop': False})
        a = b.allies[0]
        for _ in range(7):
            b.fire(a, 'own_ts', Ctx(a, a, None))
        self.assertAlmostEqual(a.mods()['atkp'], .4)
        b.cast(a, a.d.skills['궁극기'], target=b.foes[0])
        self.assertEqual(a.mods()['atkp'], 0)

    def test_luna_chain_stacks_consumption_and_coefficient(self):
        d = definition('white-pearl-luna', [(11003, 1)])
        b = battle([d, unit('partner')], [unit('enemy', hp=10**8, df=0)], opts={'coop': False, 'nova': False})
        a, partner = b.allies
        b.fire(a, 'own_ts', Ctx(a, a, None))
        for _ in range(2):
            b.fire(a, 'ally_ts', Ctx(a, partner, None))
        damage = []
        original = b.apply_damage
        def record(src, target, amount, kind, **kw):
            if kind == 'chain':
                damage.append(amount)
            return original(src, target, amount, kind, **kw)
        with patch.object(b, 'apply_damage', record):
            b.cast(a, a.d.skills['기본기'], target=b.foes[0])
        self.assertEqual(damage, [592, 592, 592])
        self.assertEqual(a.stack('지금이니!(해제불가)'), 0)

    def test_random_chain_uses_random_enemy(self):
        d = definition('white-pearl-luna', [(11003, 1)])
        b = battle([d], [unit('one', hp=10**8), unit('two', hp=10**8)])
        a = b.allies[0]
        ln = next(x for x in d.lines if x.slot == '잠재력' and x.eff['kind'] == 'chain')
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = b.foes[0], [b.foes[0]]
        with patch.object(b.rng, 'choice', lambda xs: xs[-1]):
            b.chain(a, ln.eff, ctx)
        self.assertEqual(b.foes[0].taken, 0)
        self.assertGreater(b.foes[1].taken, 0)

    def test_random_ally_basic_conditions_and_once_per_turn(self):
        d = definition(potentials=[(40405, 1)])
        b = battle([d, unit('partner')], [unit('one'), unit('two')])
        a = b.allies[0]
        a.acting = True
        ln = next(x for x in d.lines if x.slot == '잠재력')
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.crit = True
        with patch.object(b.rng, 'random', return_value=0), patch.object(b.rng, 'choice', lambda xs: xs[-1]), patch.object(b, 'cast') as cast:
            b.run_line(a, ln, ctx)
            b.run_line(a, ln, ctx)
            self.assertEqual(cast.call_count, 1)
            self.assertIs(cast.call_args.args[0], b.allies[1])
            self.assertIs(cast.call_args.kwargs['target'], b.foes[1])
            a.actions += 1
            ctx.extra = True
            b.run_line(a, ln, ctx)
            self.assertEqual(cast.call_count, 1)
        self.assertFalse(any(x['slot'] == '잠재력' for x in support_report([d])))

    def test_nova_cooldown_and_skill_nova(self):
        d = definition('wedding-carmen', [(30005, 1), (11055, 1)])
        b = battle([d], [unit('enemy', hp=10**8)], opts={'coop': False, 'nova': False})
        a = b.allies[0]
        b.fire(a, 'own_ts', Ctx(a, a, None))
        n = b.nova_of(a)
        self.assertEqual(n, 2)
        a.actions += 1
        b.fire(a, 'own_ts', Ctx(a, a, None))
        self.assertEqual(b.nova_of(a), n)
        a.actions += 1
        b.fire(a, 'own_ts', Ctx(a, a, None))
        self.assertEqual(b.nova_of(a), n + 2)
        b.cast(a, a.d.skills['궁극기'], target=b.foes[0])
        self.assertEqual(b.nova_of(a), n + 5)  # normal skill 1 + potential 2

    def test_builder_reproduces_numeric_artifact(self):
        from tools.build_myinfo_combat import build
        from tools.runtime import static_path
        try:
            static = static_path()
        except ValueError:
            self.skipTest('STARSAVIOR_STATIC 미설정 또는 경로 없음')
        built, artifact = build(static), combat.combat_data()
        # main() 은 클라 표에서 사라진 구원자(10/22 패치에서 1060 삭제)의 이전 계수를 보존한다 — 같은 규칙으로 비교
        kept = set(artifact['units']) - set(built['units'])
        self.assertLessEqual(kept, {'lydia-moon-caster'})
        for k in kept:
            built['units'][k] = artifact['units'][k]
        self.assertEqual(built, artifact)

    def test_web_entry_and_manifest_keep_combat_payload(self):
        from battlesim import api, web
        from battlesim.mc import Battle
        captured = []
        class InspectBattle(Battle):
            def __init__(self, defs, *args, **kw):
                captured.extend(defs)
                super().__init__(defs, *args, **kw)
        payload = dict(skills=dict(basic=7.0, special=7, ultimate=7, passive=4), potentials=[[23007, 1]])
        party = dict(units=[dict(key='wedding-carmen', stats_final=True, stats_override=SCREEN,
                                 power=12345, myinfo_combat=payload)], leader=None)
        encounter = api._norm_encounter(dict(waves=[[dict(name='dummy', hp=100000, atk=1)]], max_turns=1))
        with patch.object(api, '_norm_encounter', return_value=encounter), patch.object(api, 'Battle', InspectBattle):
            result = json.loads(web.run_auto('synthetic/stage', party, 1, 7, '{"build":"standard"}'))
        self.assertEqual(result['power'], 12345)
        self.assertEqual(captured[0].skills['기본기'].raw['level'], 7)
        self.assertEqual(captured[0].stats['sa'], 5)
        manifest = json.loads((ROOT / 'sim/manifest.json').read_text(encoding='utf8'))
        self.assertIn('data/myinfo_combat.json', manifest['files'])
        self.assertIn('battlesim/starsavior/myinfo_combat.py', manifest['files'])

    def test_all_roster_max_level_effects_match_existing_data(self):
        for key, slots in combat.combat_data()['units'].items():
            levels = {slot: max(map(int, rows)) for slot, rows in slots.items()}
            raw = get_db().units[key]
            selected = combat.select_skills(raw, key, dict(skills=levels))
            for old, new in zip(raw['sk'], selected['sk']):
                self.assertEqual(old['ef'], new['ef'], (key, old['sl']))
                self.assertEqual(old.get('cdm', old.get('cd')) or 0, new.get('cdm', new.get('cd')) or 0, key)


if __name__ == '__main__':
    low_priority()
    if '--mutations' in sys.argv:
        checks = [
            ('omit potential', 'test_final_stats_not_doubled_and_toughness_added', patch.object(combat, 'apply_potentials', lambda *a: None)),
            ('max skill', 'test_skill_damage_uses_selected_absolute_group', patch.object(combat, 'select_skills', lambda raw, *a: raw)),
            ('disable random basic', 'test_random_ally_basic_conditions_and_once_per_turn', patch.dict(combat.combat_data()['potentials']['40405']['1'], random_basic={})),
            ('wrong random enemy', 'test_random_chain_uses_random_enemy', patch.dict(combat.combat_data()['potentials']['11003']['1'], random_chain=[])),
        ]
        for name, method, mutation in checks:
            with mutation:
                r = unittest.TextTestRunner(stream=io.StringIO()).run(CombatTests(method))
            if not r.failures or r.errors:
                raise AssertionError('Mutation not caught by assertion: ' + name)
            print('Caught mutation:', name)
    else:
        unittest.main(verbosity=2)
