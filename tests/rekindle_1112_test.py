"""재점화: API 전달·피해 합산·연쇄 예외·legacy·실제 어려움 경로."""
import os
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from simkit import unit, give
from battlesim import api
from battlesim.mc import Battle, Ctx
from battlesim.rules import MC_RULES


def api_battle(content='oph', level=5, mode='sum', power='off', stage_fx='off'):
    seen = []
    class Capture(Battle):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            seen.append(self)
    # API에서 전투까지 실제로 실행. 큰 HP로 전투 후에도 양쪽 피해식을 검사한다.
    enc = ([[unit('foe', hp=100000, df=0)]], None, {}, [],
           {'content': content, 'recommended_power': 10**6})
    ally = unit(hp=100000, df=0)
    ally.build = {}
    with patch.object(api, '_norm_party', return_value=([ally], None)), \
         patch.object(api, '_norm_encounter', return_value=enc), patch.object(api, 'Battle', Capture):
        result = api.simulate(['gwen'], {'stage': 'stub', 'max_turns': 3},
                              {'rekindle': level, 'n_runs': 1, 'seed': 3,
                               'rules_override': {'rekindle_apply': mode, 'power_penalty': power,
                                                  'stage_fx_target': stage_fx, 'toughness': 'off',
                                                  'rand_range': [1, 1]}})
    b = seen[0]
    assert result['outcome']['progress'] > 0
    return b, result


class RekindleTest(unittest.TestCase):
    def test_private_table_chain(self):
        static = os.environ.get('STARSAVIOR_STATIC')
        if not static:
            self.skipTest('STARSAVIOR_STATIC 없음')
        def table(name, key):
            rows = json.loads((Path(static)/'tables'/(name+'.json')).read_text(encoding='utf8'))['Data']
            return {r[key]: r for r in rows}
        operation = table('OPERATION_BUFF_TEMPLET', 'OperationBuffId')
        effects = table('BATTLE_EFFECT_TEMPLET', 'BattleEffectStrId')
        ses = table('SE_TEMPLET_BATTLE_EFFECT', 'm_SEStrID')
        buffs = table('BUFF_TEMPLET', 'm_BuffStrID')
        for level in range(1, 6):
            effect = effects[operation[100+level]['BattleEffectStrId']]
            self.assertEqual(effect['AteamEffectTarget'], 'ALL')
            se, = [ses[k] for k in effect['BattleEffectSeStrId']]
            self.assertEqual(se['m_Condition'], {'m_ActiveType': 'NSEAT_BATTLE_START', 'm_fActiveRate': 10000})
            self.assertEqual(se['m_BuffTargetType'], 'NSETT_SELF')
            buff = buffs[se['m_BuffStrID']]
            stats = {s['NKM_STAT_TYPE']: s['NKM_STAT_TYPE_RATE'] for s in buff['Stats']}
            self.assertEqual(stats, {k: round(api.REKINDLE[level]*10000) for k in ('NST_RATE_DAMAGE_UP', 'NST_RATE_DAMAGE_REDUCE')})
            self.assertFalse(buff['IsBuff'])
            self.assertTrue(all(buff[k] for k in ('TurnInfinite', 'DeadNotDispel', 'ForceApplyEffect')))

    def test_rule(self):
        r = MC_RULES['rekindle_apply']
        self.assertEqual((r['value'], r['legacy'], r['grade']), ('sum', 'multiply', 'code'))
        self.assertIn('multiply', r['alt'])
        self.assertIn('18864-18897', r['source'])

    def test_api_all_levels_content_and_power_independence(self):
        for content in ('op', 'oph', 'clo'):
            for level, x in enumerate(api.REKINDLE):
                for power in ('off', 'model'):
                    for mode in ('sum', 'multiply'):
                        with self.subTest(content=content, level=level, power=power, mode=mode):
                            base, r0 = api_battle(content, 0, mode, power)
                            if power == 'model':
                                self.assertNotEqual(base.pen, (1, 1))
                            b, r = api_battle(content, level, mode, power)
                            active = x if content in ('op', 'oph') else 0
                            a, v = b.allies[0], b.foes[0]
                            stat = active if mode == 'sum' else 0
                            self.assertAlmostEqual(a.mods()['inc'], stat)
                            self.assertAlmostEqual(a.mods()['red'].get('all', 0), stat)
                            self.assertEqual(v.mods()['inc'], 0)
                            self.assertEqual(v.mods()['red'].get('all', 0), 0)
                            self.assertEqual(r['party']['rekindle'], level if content in ('op', 'oph') else 0)
                            expected = base.pen if mode == 'sum' else (base.pen[0]*(1+active), base.pen[1]*(1-active))
                            self.assertEqual(b.pen, expected)

    def test_general_critical_and_net_cap(self):
        for mode, outgoing, incoming in [('sum', 2250, 500), ('multiply', 2500, 375)]:
            b, _ = api_battle(mode=mode)
            a, v = b.allies[0], b.foes[0]
            a.last_slot = v.last_slot = None
            give(a, 'inc', {'피해 증가': 25, '피해 감소': 50})
            def hit(src, dst, critical):
                return b.final_dmg(src, dst, 1000, Ctx(src, src, src.d.skills['기본기']), bool(critical), critical, 0, 1, None)
            self.assertEqual(hit(a, v, .75), outgoing)
            self.assertEqual(hit(v, a, 0), incoming)
            self.assertEqual(b.rule_hits['dmg_cap_scope'], int(mode == 'sum'))

    def test_dot_and_chain_both_directions(self):
        for mode in ('sum', 'multiply'):
            for side in (0, 1):
                for kind in ('dot', 'chain'):
                    with self.subTest(mode=mode, side=side, kind=kind):
                        b, _ = api_battle(mode=mode)
                        a, v = (b.allies[0], b.foes[0]) if side == 0 else (b.foes[0], b.allies[0])
                        give(a, 'inc', {'피해 증가': 25})
                        give(v, 'red', {'피해 감소': 50})
                        a.last_slot = v.last_slot = None
                        before = v.taken
                        if kind == 'dot':
                            e = give(v, '연소', src=a, harmful=True)
                            e.dot, e.inst = ('atk', 1), [[a, 2]]
                            b._tick_dot_hot(v)
                            # 1000×1.85: 아군은 1+.25+.25-.5, 적은 1+.25-.5-.25.
                            expected = (1850 if side == 0 else 925) if mode == 'sum' else (1734 if side == 0 else 1040)
                        else:
                            b.chain(a, {'target': '적 전체', 'stat': 'atk', 'coef': 1}, None)
                            # 일반 감소는 연쇄에 미적용. 재점화 증가만 기존 증가와 합산.
                            expected = (2775 if side == 0 else 2312) if mode == 'sum' else (2890 if side == 0 else 1734)
                        self.assertEqual(v.taken - before, expected)

    def test_permanent_non_buff_and_fixed_true(self):
        b, _ = api_battle()
        a, v = b.allies[0], b.foes[0]
        give(a, '강화 불가', harmful=True)
        a.ban_refuse = False  # 옛 suppress에서도 IsBuff=false는 유지
        a._m = None
        self.assertEqual(a.mods()['inc'], .25)
        self.assertNotIn('재점화', a.eff)
        a.eff.clear(); b.dirty(a)
        self.assertEqual(a.mods()['red'].get('all', 0), .25)
        before = a.taken
        b.fixed_true_damage(v, a, 1000)
        self.assertEqual(a.taken - before, 1000)

    def test_stage_effect_composes_and_wave_keeps_stats(self):
        with patch.object(api, '_ally_stage_fx', return_value=[({'피해 증가': 10}, None, None)]):
            b, _ = api_battle(stage_fx='allies')
        a = b.allies[0]
        self.assertAlmostEqual(a.mods()['inc'], .35)
        b.waves.append([unit('next', hp=100000)])
        b.spawn_wave()
        self.assertEqual(b.wave_i, 1)
        self.assertAlmostEqual(a.mods()['inc'], .35)
        self.assertEqual(a.mods()['red'].get('all', 0), .25)
        self.assertEqual(b.foes[0].mods()['inc'], 0)

    def test_invalid_mode(self):
        with self.assertRaisesRegex(ValueError, 'rekindle_apply'):
            api_battle(mode='invalid')

    def test_real_hard_stage_progress_and_affected_hits(self):
        seen = {'calls': 0, 'changed': 0}
        original = Battle.final_dmg
        def hit(b, a, v, *args, **kw):
            out = original(b, a, v, *args, **kw)
            if a.side == 0:
                seen['calls'] += 1
                self.assertEqual(a.fx.get('피해 증가'), 25)
                old = dict(a.fx)
                try:
                    a.fx.pop('피해 증가'); a._m = None
                    seen['changed'] += out != original(b, a, v, *args, **kw)
                finally:
                    a.fx = old; a._m = None
            return out
        with patch.object(Battle, 'final_dmg', hit):
            r = api.simulate(['bunny-charlotte', 'carnelia', 'gwen', 'tyria'],
                             {'stage': 'oph/플로라/SECTOR 13-10'},
                             {'build': 'standard', 'rekindle': 5, 'n_runs': 3, 'seed': 3})
        self.assertGreater(r['outcome']['progress'], 0)
        self.assertGreater(seen['calls'], 0)
        self.assertGreater(seen['changed'], 0)
        print('hard stage progress / hits:', r['outcome']['progress'], seen)


if __name__ == '__main__':
    unittest.main()

