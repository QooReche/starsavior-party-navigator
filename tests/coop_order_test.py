# -*- coding: utf-8 -*-
"""협공 후보 순서: 상한 전 능력치·동점 슬롯순·첫 성공·실제 전투 경로."""
import math
import itertools
import os
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from battlesim import simulate
from battlesim import engine, rules
from battlesim.mc import Battle, Ctx
from battlesim.metrics import ref_enemies
from p3_test import battle, give, unit
import rank_check


class CoopOrderTest(unittest.TestCase):
    def make_battle(self, rates, mode='stat'):
        b = battle([unit('a%d' % i) for i in range(len(rates) + 1)], [unit('foe')],
                   opts={'coop_order': mode})
        a = b.allies[0]
        give(a, '본 행동자', props={'협공 확률': 999})
        for u, rate in zip(b.allies[1:], rates):
            give(u, '협공 시험', props={'협공 확률': rate * 100})
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target = b.foes[0]
        return b, a, ctx

    def pick(self, b, a, ctx, rolls=(0.0,)):
        rng = Mock()
        rng.random.side_effect = rolls
        with patch.object(b, 'R', return_value=rng), patch.object(b, 'cast') as cast:
            b.coop(a, ctx)
        return [c.args[0].pos for c in cast.call_args_list], rng.random.call_count

    def test_defaults_and_rank_check_legacy(self):
        self.assertEqual(rules.DEFAULT_OPTS['coop_order'], 'random_success')
        self.assertIn('stat', rules.RULES['opts']['coop_order']['alt'])
        self.assertEqual(rules.RULES['opts']['coop_order']['legacy'], 'capped')
        self.assertNotIn('coop_order', rules.MC_OPTS)  # 공통 opts와 MC 전용 키는 중복시키지 않음
        try:
            rank_check.apply_rules('legacy')
            self.assertEqual(rules.DEFAULT_OPTS['coop_order'], 'capped')
            rank_check.apply_rules('default')
            self.assertEqual(rules.DEFAULT_OPTS['coop_order'], 'random_success')
            rank_check.apply_rules('default', {'coop_order': 'capped'})
            self.assertEqual(rules.DEFAULT_OPTS['coop_order'], 'capped')
        finally:
            rank_check.apply_rules('default')

    def test_mc_above_cap_and_legacy(self):
        for cap in (1.0, 0.30):
            for mode, winner in (('stat', 2), ('capped', 1)):
                with self.subTest(cap=cap, mode=mode), patch.object(rules, 'COOP_CAP', cap):
                    b, a, ctx = self.make_battle([1.2, 1.8, 1.4], mode)
                    self.assertEqual(self.pick(b, a, ctx), ([winner], 1))

    def test_mc_ties_use_slots(self):
        b, a, ctx = self.make_battle([1.8, 1.8, 1.2])
        # 열거 순서와 슬롯순이 우연히 같아서 통과하지 않도록 뒤집음.
        b.allies.reverse()
        self.assertEqual(self.pick(b, a, ctx), ([1], 1))

    def test_mc_roll_order_and_first_success(self):
        b, a, ctx = self.make_battle([0.5, 0.8, 0.2])
        # 80% 후보 실패, 50% 후보 성공 -> 세 번째 난수를 요구하면 실패.
        self.assertEqual(self.pick(b, a, ctx, (0.9, 0.4)), ([1], 2))
        self.assertEqual(self.pick(b, a, ctx, (0.9, 0.6, 0.3)), ([], 3))
        self.assertEqual(self.pick(b, a, ctx, (0.8, 0.5, 0.19)), ([3], 3))

    def test_mc_ineligible_candidates_do_not_roll(self):
        for reason in ('dead', 'broken', 'stun', 'sleep', 'missing', 'cooldown', 'passive'):
            with self.subTest(reason=reason):
                b, a, ctx = self.make_battle([2.0, 1.2, 0.0])
                u = b.allies[1]
                if reason == 'dead':
                    u.dead = True
                elif reason == 'broken':
                    u.broken = True
                elif reason in ('stun', 'sleep'):
                    give(u, '기절' if reason == 'stun' else '수면', harmful=True)
                elif reason == 'missing':
                    del u.d.skills['기본기']
                elif reason == 'cooldown':
                    u.cd['기본기'] = 1
                else:
                    u.d.skills['기본기'].ty = '패시브'
                self.assertEqual(self.pick(b, a, ctx), ([2], 1))
        b, a, ctx = self.make_battle([0.0, -0.1])
        self.assertEqual(self.pick(b, a, ctx, ()), ([], 0))

    def test_mc_silence_allowed_and_used_slot_skipped(self):
        b, a, ctx = self.make_battle([1.8, 1.2])
        give(b.allies[1], '침묵', harmful=True)
        self.assertEqual(self.pick(b, a, ctx), ([1], 1))
        ctx.coop_used = True
        self.assertEqual(self.pick(b, a, ctx, ()), ([], 0))

    def expected_casts(self, rates, mode='stat', cap=1.0, unavailable=None, used=0.0):
        defs = [engine.DummyDef(name='a%d' % i) for i in range(len(rates) + 1)]
        for d in defs:
            d.dummy = False  # 독립 합성 유닛: 실 구원자 캐시/계정 자료를 바꾸지 않음
        s = engine.Sim(defs, ref_enemies(1), 10, {'coop_order': mode})
        for u, rate in zip(s.party[1:], rates):
            buff = engine.Buff('협공 시험', {'협공 확률': rate * 100}, 1, math.inf)
            buff.stacks = 1
            u.buffs[buff.name] = buff
        if unavailable == 'cooldown':
            s.party[2].cd['기본기'] = 1
        elif unavailable == 'passive':
            s.party[2].d.skills['기본기'].ty = '패시브'
        elif unavailable == 'missing':
            del s.party[2].d.skills['기본기']
        elif unavailable == 'disabled':
            buff = engine.Buff('협공 불가', {}, 1, math.inf)
            buff.stacks = 1
            s.party[2].buffs[buff.name] = buff
        a = s.party[0]
        with patch.object(engine, 'COOP_CAP', cap), patch.object(s, 'cast') as cast:
            ctx = engine.Ctx(a, a, a.d.skills['기본기'], False, 1.0)
            ctx.coop_used = used
            s.coop_followups(a, ctx)
        return [(c.args[0].idx, c.kwargs['w']) for c in cast.call_args_list if c.kwargs['w'] > 0]

    def test_expected_above_cap_and_legacy(self):
        self.assertEqual(self.expected_casts([1.2, 1.8, 1.4]), [(2, 1.0)])
        self.assertEqual(self.expected_casts([1.2, 1.8, 1.4], 'capped'), [(1, 1.0)])
        for mode, order in (('stat', [2, 3, 1]), ('capped', [1, 2, 3])):
            got = self.expected_casts([1.2, 1.8, 1.4], mode, cap=0.30)
            self.assertEqual([i for i, _ in got], order)
            for (_, weight), expected in zip(got, [0.30, 0.21, 0.147]):
                self.assertAlmostEqual(weight, expected)

    def test_expected_ties_and_failure_weights(self):
        self.assertEqual(self.expected_casts([1.8, 1.8, 1.2]), [(1, 1.0)])
        got = self.expected_casts([0.5, 0.8, 0.2])
        self.assertEqual([i for i, _ in got], [2, 1, 3])
        for (_, weight), expected in zip(got, [0.8, 0.1, 0.02]):
            self.assertAlmostEqual(weight, expected)

    def test_expected_unavailable_basic(self):
        for reason in ('cooldown', 'passive', 'missing'):
            with self.subTest(reason=reason):
                self.assertEqual(self.expected_casts([1.2, 1.8, 1.4], unavailable=reason), [(3, 1.0)])

    def test_random_success_rolls_every_candidate_in_slot_order(self):
        b, a, ctx = self.make_battle([0.5, 0.8, 0.2], 'random_success')
        b.allies.reverse()
        rng = Mock()
        rng.random.side_effect = [0.49, 0.8, 0.19]  # slots 1/3 성공, 2는 경계 실패
        rng.choice.side_effect = lambda seq: seq[-1]
        with patch.object(b, 'R', return_value=rng), patch.object(b, 'cast') as cast:
            b.coop(a, ctx)
        self.assertEqual(rng.random.call_count, 3)
        rng.choice.assert_called_once()
        self.assertEqual([u.pos for u in rng.choice.call_args.args[0]], [1, 3])
        self.assertEqual(cast.call_count, 1)
        self.assertEqual(cast.call_args.args[0].pos, 3)
        self.assertEqual(cast.call_args.kwargs['via'], 'coop')
        self.assertIs(cast.call_args.kwargs['target'], ctx.target)

    def test_random_success_empty_and_single_pool(self):
        for rolls, expected in [([0.6, 0.9], []), ([0.6, 0.1], [2])]:
            b, a, ctx = self.make_battle([0.5, 0.8], 'random_success')
            rng = Mock()
            rng.random.side_effect = rolls
            rng.choice.side_effect = lambda seq: seq[0]
            with patch.object(b, 'R', return_value=rng), patch.object(b, 'cast') as cast:
                b.coop(a, ctx)
            self.assertEqual(rng.random.call_count, 2)
            self.assertEqual(rng.choice.call_count, bool(expected))
            self.assertEqual([c.args[0].pos for c in cast.call_args_list], expected)
        b, a, ctx = self.make_battle([0, -0.1], 'random_success')
        self.assertEqual(self.pick(b, a, ctx, ()), ([], 0))
        b, a, ctx = self.make_battle([1.2, 1.8], 'random_success')
        ctx.coop_used = True
        self.assertEqual(self.pick(b, a, ctx, ()), ([], 0))

    def test_random_success_filters_before_rolling(self):
        for reason in ('dead', 'broken', 'stun', 'sleep', 'missing', 'cooldown', 'passive', 'disabled'):
            b, a, ctx = self.make_battle([1.8, 1.2], 'random_success')
            u = b.allies[1]
            if reason == 'dead':
                u.dead = True
            elif reason == 'broken':
                u.broken = True
            elif reason in ('stun', 'sleep', 'disabled'):
                give(u, {'stun': '기절', 'sleep': '수면', 'disabled': '협공 불가'}[reason], harmful=True)
            elif reason == 'missing':
                del u.d.skills['기본기']
            elif reason == 'cooldown':
                u.cd['기본기'] = 1
            else:
                u.d.skills['기본기'].ty = '패시브'
            rng = Mock()
            rng.random.return_value = 0.0
            rng.choice.side_effect = lambda seq: seq[0]
            with self.subTest(reason=reason), patch.object(b, 'R', return_value=rng), patch.object(b, 'cast') as cast:
                b.coop(a, ctx)
                self.assertEqual(rng.random.call_count, 1)
                self.assertEqual([u.pos for u in rng.choice.call_args.args[0]], [2])
                self.assertEqual(cast.call_args.args[0].pos, 2)

    def test_random_success_weights_match_all_success_sets(self):
        # 엔진의 성공자 수 분포와 독립적으로 모든 성공/실패 집합을 열거.
        for rates, cap in [([0.5, 0.8, 0.2], 1.0), ([1.2, 1.8, 1.4], 1.0),
                           ([1.2, 1.8, 1.4], 0.3), ([0, 1, 0.5], 1.0), ([0, -0.1], 1.0)]:
            probs = [min(cap, max(0, p)) for p in rates]
            expected = [0.0] * len(probs)
            for flags in itertools.product([False, True], repeat=len(probs)):
                if not any(flags):
                    continue
                mass = math.prod(p if yes else 1-p for p, yes in zip(probs, flags))
                for i, yes in enumerate(flags):
                    if yes:
                        expected[i] += mass / sum(flags)
            for used in (0, 0.25, 1):
                got = dict(self.expected_casts(rates, 'random_success', cap, used=used))
                for i, weight in enumerate(expected):
                    self.assertAlmostEqual(got.get(i+1, 0), weight * (1-used))
                self.assertAlmostEqual(sum(got.values()), (1-math.prod(1-p for p in probs)) * (1-used))

    def test_random_success_expected_unavailable_basic(self):
        for reason in ('cooldown', 'passive', 'missing', 'disabled'):
            self.assertEqual(self.expected_casts([1.2, 1.8, 1.4], 'random_success', unavailable=reason),
                             [(1, 0.5), (3, 0.5)])

    def test_random_success_standard_battle_uses_new_default(self):
        original_coop, original_cast = Battle.coop, Battle.cast
        checked = []

        def spy(b, actor, ctx):
            eligible = sorted([u for u in b.alive(0) if u is not actor and not b.no_react(u)
                               and u.d.skills.get('기본기') and u.d.skills['기본기'].ty == '액티브'
                               and u.cd.get('기본기', 0) <= 0 and not u.has('협공 불가')], key=lambda u: u.pos)
            if (ctx.coop_used or ctx.skill.slot != '기본기' or len(eligible) < 2
                    or (not ctx.skill.all and ctx.target is not None and ctx.target.dead)):
                return original_coop(b, actor, ctx)
            for u in eligible:
                give(u, '새 협공 시험', props={'협공 확률': 180 - u.pos * 10})
            selected = []

            def cast(u, skill, *args, **kwargs):
                if kwargs.get('via') == 'coop':
                    selected.append(u)
                return original_cast(b, u, skill, *args, **kwargs)

            with patch.object(b, 'cast', cast), patch.object(b.R(actor.side), 'choice', side_effect=lambda seq: seq[-1]):
                result = original_coop(b, actor, ctx)
            self.assertEqual(selected, [eligible[-1]])  # stat/capped면 앞 후보여서 실패
            checked.append(1)
            return result

        with patch.object(Battle, 'coop', spy):
            result = simulate(['emily', 'waltz-asherah', 'hilde', 'ceres-sun-supporter'],
                              {'stage': 'clo/달 회랑/FLOOR 100'},
                              {'seed': 17, 'n_runs': 2, 'build': 'standard'})
        self.assertGreater(len(checked), 0)
        self.assertGreater(result['outcome']['progress'], 0)
        self.assertGreater(result['ally_via'].get('coop', 0), 0)
        self.assertEqual(next(r['value'] for r in result['assumptions_used']
                              if r['rule'] == 'opts.coop_order'), 'random_success')
        print('random_success: 새 후보 분기 %d회, progress=%.4f' % (len(checked), result['outcome']['progress']))

    def test_standard_battle_reaches_above_cap_branch(self):
        original_coop, original_cast = Battle.coop, Battle.cast
        for mode in ('stat', 'capped'):
            checked = []

            def spy(b, actor, ctx):
                # 표준 육성의 실제 전투에 합성 버프만 주입해 100% 초과 경계를 강제함.
                eligible = [u for u in b.alive(0) if u is not actor and not b.no_react(u)
                            and u.d.skills.get('기본기') and u.d.skills['기본기'].ty == '액티브'
                            and u.cd.get('기본기', 0) <= 0]
                if (ctx.coop_used or ctx.skill.slot != '기본기' or len(eligible) < 2
                        or (not ctx.skill.all and ctx.target is not None and ctx.target.dead)):
                    return original_coop(b, actor, ctx)
                for u in eligible:
                    give(u, '순서 경계 시험', props={'협공 확률': (120, 180, 140, 160)[u.pos]})
                ordered = sorted(eligible, key=lambda u: u.pos)
                expected = max(ordered, key=lambda u: u.mods()['coop']) if mode == 'stat' else ordered[0]
                self.assertGreater(min(u.mods()['coop'] for u in eligible), 1.0)
                selected = []

                def cast(u, skill, *args, **kwargs):
                    if kwargs.get('via') == 'coop':
                        selected.append(u)
                    return original_cast(b, u, skill, *args, **kwargs)

                with patch.object(b, 'cast', cast):
                    result = original_coop(b, actor, ctx)
                self.assertEqual(selected, [expected])
                checked.append(expected.pos)
                return result

            with patch.object(Battle, 'coop', spy):
                result = simulate(['emily', 'waltz-asherah', 'hilde', 'ceres-sun-supporter'],
                                  {'stage': 'clo/달 회랑/FLOOR 100'},
                                  {'seed': 17, 'n_runs': 2, 'build': 'standard',
                                   'rules_override': {'coop_order': mode}})
            self.assertGreater(len(checked), 0)
            self.assertGreater(result['outcome']['progress'], 0)
            self.assertGreater(result['ally_via'].get('coop', 0), 0)
            self.assertEqual(next(r['value'] for r in result['assumptions_used']
                                  if r['rule'] == 'opts.coop_order'), mode)
            print('coop_order=%s: 초과 후보 검증 %d회, progress=%.4f' %
                  (mode, len(checked), result['outcome']['progress']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
