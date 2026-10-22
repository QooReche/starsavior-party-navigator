"""Synthetic input and gauge regression; --mutations deliberately restores the cap."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, unit
from battlesim.mc import Battle, Ctx
from battlesim.starsavior.parser import Line
from tools import ingame_check as check


class GaugeTest(unittest.TestCase):
    def make(self, **kw):
        return battle([unit('slow', spd=100), unit('fast', spd=200)],
                      [unit('foe', hp=10**9, spd=50)], **kw)

    def test_buff_overflow_orders_ready_units(self):
        b = self.make()
        slow, fast = b.allies
        slow.gauge, fast.gauge = 9500, 10000
        b.run_line(slow, Line('[스킬 사용 후] 자신에게 행동 게이지 20%p 증가', '기본기', 'active'),
                   Ctx(slow, slow, slow.d.skills['기본기']))
        self.assertEqual(slow.gauge, 11500)
        self.assertEqual(b.pick_next(b.allies), (slow, 0))
        b.act(slow)
        self.assertEqual(slow.gauge, 0)
        self.assertEqual(b.pick_next(b.allies), (fast, 0))

    def test_ready_gauge_survives_run_advance(self):
        b = self.make()
        slow, fast = b.allies
        slow.gauge, fast.gauge = 11500, 11000
        observed = []
        def stop(actor):
            observed.append((actor.name, [u.gauge for u in b.allies]))
            b.kill(b.foes[0], actor)
        with patch.object(b, 'act', side_effect=stop):
            b.run()
        self.assertEqual(observed, [('slow', [11500, 11000])])

    def test_lower_bound_extra_turn_and_legacy(self):
        b = self.make()
        slow, fast = b.allies
        b.set_gauge(slow, -100)
        self.assertEqual(slow.gauge, 0)
        b.set_gauge(slow, 14000)
        fast.gauge, fast.extra_turn = 10000, True
        self.assertEqual(b.pick_next(b.allies), (fast, 0))
        b.mc['gauge_overflow'] = False
        b.set_gauge(slow, 14000)
        self.assertEqual(slow.gauge, 10000)

    def test_break_skill_overflow(self):
        b = self.make(break_skill={'name': '스타피어서'})
        b.break_points = 3
        b.allies[1].gauge = 9500
        b._use_break_skill(b.allies[0])
        self.assertEqual(b.allies[1].gauge, 11500)

    def test_probability_gauge_overflow(self):
        b = self.make()
        a = b.allies[0]
        a.gauge = 9500
        b.run_line(a, Line('[스킬 사용 후] 자신에게 100% 확률로 행동 게이지 20%p 증가', '기본기', 'active'),
                   Ctx(a, a, a.d.skills['기본기']))
        self.assertEqual(a.gauge, 11500)


class MyinfoInputTest(unittest.TestCase):
    def setUp(self):
        # Entirely synthetic account; no private file is opened by these tests.
        self.info = dict(format='ss-myinfo-v1', units=[dict(id=i) for i in range(1, 5)])
        self.growth = dict(units={str(i): {} for i in range(1, 5)})
        self.index = {str(i): dict(key=k) for i, k in enumerate('abcd', 1)}
        self.answer = dict(stats=dict(atk=100, hp=1000, **{'def': 100}, spd=170,
                                      cr=1000, cd=5000, eh=10000, er=100), power=12345,
                           missing=['power_pp'], build_mismatch=True, combat=dict(skills=dict(basic=2), potentials=[[900001, 1]]))

    def read(self, path, **kw):
        data = self.growth if str(path).endswith('growth.json') else (
            self.index if str(path).endswith('saviors_index.json') else self.info)
        return io.StringIO(json.dumps(data))

    def test_final_input_order_leader_power_and_content_rule(self):
        for content, rule in [('op', 'normal'), ('cosmo', 'fixed200')]:
            with patch('builtins.open', side_effect=self.read), patch(
                    'battlesim.starsavior.myinfo_stats.final_stats', return_value=self.answer) as calc:
                spec, diag = check.myinfo_party(content, list('abcd'), 'c', 'synthetic')
            self.assertEqual([u['key'] for u in spec['units']], list('bcad'))
            self.assertEqual(spec['leader'], 1)
            self.assertEqual(diag['rule'], rule)
            self.assertEqual([c.args[-1] for c in calc.call_args_list], [rule] * 4)
            for u in spec['units']:
                self.assertEqual(u['build'], 'none')
                self.assertTrue(u['stats_final'])
                self.assertEqual(u['power'], 12345)
                self.assertEqual(u['myinfo_combat'], self.answer['combat'])
                self.assertEqual(u['stats_override'], self.answer['stats'])
                self.assertEqual(diag['units'][u['key']], dict(missing=['power_pp'], build_mismatch=True))

    def test_missing_member_and_unknown_content_fail_without_fallback(self):
        self.info['units'].pop()
        with patch('builtins.open', side_effect=self.read), patch(
                'battlesim.starsavior.myinfo_stats.final_stats', return_value=self.answer):
            with self.assertRaisesRegex(ValueError, 'Missing myinfo/growth unit: d'):
                check.myinfo_party('op', list('abcd'), None, 'synthetic')
        with self.assertRaisesRegex(ValueError, 'No myinfo rule'):
            check.myinfo_party('unknown', list('abcd'), None, 'synthetic')

    def test_run_uses_calculated_power_without_legacy_rebalance(self):
        spec = dict(units=[dict(key=key, build='none', stats_final=True,
                                stats_override=self.answer['stats'], power=12345)
                           for key in check.TEAM2], leader=2)
        with patch.object(check, 'myinfo_party', return_value=(spec, {'rule': 'normal'})), \
             patch.object(check, 'rebalance', side_effect=AssertionError('legacy rebalance')), \
             patch('gen_quick_calib.party_spec', side_effect=AssertionError('legacy build')):
            result = check.run('37-5', runs=1, myinfo='synthetic')
        self.assertEqual(result['party_power'], 4 * 12345)
        self.assertEqual(result['myinfo'], {'rule': 'normal'})
        self.assertEqual(result['sim_boss_actions'], 0)
        self.assertGreater(result['sim_enemy_actions'], 0)


class EnemyTurnTimingTest(unittest.TestCase):
    def make(self, **mc):
        return battle([unit('ally', hp=10**9, atk=0)],
                      [unit('boss', hp=10**9, atk=0, skills=[
                          dict(slot='기본기', dm=1), dict(slot='특수기', dm=1, cd=3),
                          dict(slot='궁극기', dm=1, cd=4)])], mc=mc)

    def test_displayed_cooldowns_and_other_units_turns(self):
        b = self.make()
        u = b.foes[0]
        self.assertEqual(u.cd['궁극기'], 4)
        b.act(u)
        self.assertEqual((u.cd['특수기'], u.cd['궁극기']), (2, 3))
        before = dict(u.cd)
        b.act(b.allies[0])
        self.assertEqual(u.cd, before)

    def test_one_remaining_cannot_cast_until_next_owner_turn(self):
        b = self.make()
        u = b.foes[0]
        u.cd.update(특수기=2, 궁극기=1)
        b.act(u)
        self.assertEqual(u.last_slot, '기본기')
        self.assertEqual(u.cd['궁극기'], 0)
        b.act(u)
        self.assertEqual(u.last_slot, '궁극기')
        self.assertEqual(u.cd['궁극기'], 3)

    def test_start_effect_reset_ticks_after_use_before_end_effect(self):
        b = self.make()
        u = b.foes[0]
        u.cd.update(특수기=2, 궁극기=1)
        observed = []
        fire = b.fire
        def hook(owner, kind, ctx):
            if owner is u and kind == 'own_ts':
                observed.append(('start', u.cd['궁극기']))
                u.cd['궁극기'] = 0
            if owner is u and kind == 'own_te':
                observed.append(('end', u.cd['궁극기']))
            return fire(owner, kind, ctx)
        with patch.object(b, 'fire', side_effect=hook):
            b.act(u)
        self.assertEqual(observed, [('start', 1), ('end', 3)])
        self.assertEqual(u.last_slot, '궁극기')

    def test_extra_cast_is_not_a_turn_but_extra_turn_ticks(self):
        b = self.make()
        u = b.foes[0]
        u.cd.update(특수기=3, 궁극기=4)
        b.cast(u, u.d.skills['기본기'], extra=True)
        self.assertEqual((u.actions, u.cd['특수기'], u.cd['궁극기']), (0, 3, 4))
        u.extra_turn, u.gauge = True, 10000
        b.act(u)
        self.assertEqual((u.actions, u.cd['특수기'], u.cd['궁극기']), (1, 2, 3))
        self.assertFalse(u.extra_turn)

    def test_legacy_switch_preserves_regular_pilgrim_sequence(self):
        from p3_test import _pilgrim_cd_trace
        native = _pilgrim_cd_trace(dict(enemy_cd_native=True))
        legacy = _pilgrim_cd_trace(dict(enemy_cd_native=False))
        self.assertEqual(native[1]['궁극기'], 4)
        self.assertEqual(legacy[1]['궁극기'], 5)
        self.assertEqual(native[2:], legacy[2:])


class ActionAuditTest(unittest.TestCase):
    def test_measurement_preserves_result_and_separates_gauge_from_turns(self):
        from tools.boss_action_diagnostic import measure
        plain = check.run('37-3', runs=2, seed=7, bs=True)
        audit = measure('37-3', 2, 7, None)
        self.assertEqual(plain, audit['result'])
        boss = audit['per_unit']['1:공허습격자']
        self.assertEqual(boss['extra_turns'], 0)
        self.assertGreater(boss['positive_effect_count'], 0)
        self.assertAlmostEqual(boss['positive_effect_gauge'], 1500 * boss['positive_effect_count'])
        actions = [r for r in audit['first_seed_log'] if r['event'] == 'action' and r['boss']]
        self.assertTrue(any(any('15%p' in key for key in r['gains']) for r in actions))


if __name__ == '__main__':
    if '--turn-mutations' in sys.argv:
        from battlesim.mc import MC_OPTS
        with patch.dict(MC_OPTS, enemy_cd_native=False):
            result = unittest.TextTestRunner().run(
                unittest.defaultTestLoader.loadTestsFromTestCase(EnemyTurnTimingTest))
        caught = len(result.failures) == 3 and not result.errors
        print('Legacy-start mutation detected:', caught)
        sys.exit(0 if caught else 1)
    if '--mutations' in sys.argv:
        def capped(self, u, value):
            u.gauge = min(10000.0, max(0.0, value))
        with patch.object(Battle, 'set_gauge', capped):
            result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(GaugeTest))
        caught = len(result.failures) == 4 and not result.errors
        print('Old-cap mutation detected:', caught)
        sys.exit(0 if caught else 1)
    unittest.main(verbosity=2)
