# -*- coding: utf-8 -*-
"""강제 협공 효과 대상/후보 추첨 분리와 기대값 합성. 공개 합성 유닛만 사용."""
import itertools
import math
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from battlesim import engine
from battlesim.starsavior.parser import Line


class ForcedCoopExpectedTest(unittest.TestCase):
    def make(self, mode='random', slot='shared'):
        defs = [engine.DummyDef(atk=1000 + i * 1000, name='a%d' % i) for i in range(4)]
        for d in defs:
            d.dummy = False
        s = engine.Sim(defs, [dict(hp=10000000, **{'def': 100})],
                       opts={'forced_coop_target': mode, 'forced_coop_slot': slot,
                             'coop_order': 'random_success', 'coop_trigger': 'basic_only'})
        a = s.party[0]
        return s, a, engine.Ctx(a, a, a.d.skills['기본기'], False, 1.0)

    def buff(self, a, name, props=None):
        b = engine.Buff(name, props or {}, 1, math.inf)
        b.stacks = 1
        a.buffs[name] = b

    def effect(self, target='아군 전체', chance=1.0):
        eff = Line('[스킬 사용 후] ' + target + '에게 〈강제 협공〉', '기본기', 'active').eff
        eff['chance'] = chance
        return eff

    def calls(self, s, a, ctx):
        with patch.object(s, 'cast') as cast:
            s.coop_followups(a, ctx)
        out = {}
        for c in cast.call_args_list:
            out[c.args[0].idx] = out.get(c.args[0].idx, 0) + c.kwargs['w']
        return {k: v for k, v in out.items() if v > 1e-12}

    def test_multiple_forced_candidates_uniform_without_rate_or_atk_priority(self):
        s, a, ctx = self.make()
        s.apply_buff(a, self.effect(), ctx, 1)
        self.assertEqual(self.calls(s, a, ctx), {1: 1/3, 2: 1/3, 3: 1/3})

    def test_effect_is_deferred_and_self_excluded(self):
        s, a, ctx = self.make()
        with patch.object(s, 'cast') as cast:
            s.apply_buff(a, self.effect('자신'), ctx, 1)
            cast.assert_not_called()
        self.assertEqual(a.forced_coop, 1)
        self.assertEqual(self.calls(s, a, ctx), {})

    def test_ineligible_forced_candidates_fall_back_to_normal(self):
        for reason in ('dead', 'broken', '기절', '수면', '협공 불가', 'missing', 'passive', 'cooldown'):
            with self.subTest(reason=reason):
                s, a, ctx = self.make()
                b = s.party[1]
                b.forced_coop = 1
                if reason in ('dead', 'broken'):
                    setattr(b, reason, True)
                elif reason in ('기절', '수면', '협공 불가'):
                    self.buff(b, reason)
                elif reason == 'missing':
                    del b.d.skills['기본기']
                elif reason == 'passive':
                    b.d.skills['기본기'].ty = '패시브'
                else:
                    b.cd['기본기'] = 1
                self.buff(s.party[2], '확률', {'협공 확률': 100})
                self.assertEqual(self.calls(s, a, ctx), {2: 1})

    def test_fractional_candidates_match_exhaustive_success_subsets(self):
        s, a, ctx = self.make()
        rates = [.2, .5, .8]
        for b, p in zip(s.party[1:], rates):
            b.forced_coop = p
        expected = [0., 0., 0.]
        for bits in itertools.product((0, 1), repeat=3):
            mass = math.prod(p if yes else 1-p for p, yes in zip(rates, bits))
            for i, yes in enumerate(bits):
                if yes:
                    expected[i] += mass / sum(bits)
        got = self.calls(s, a, ctx)
        for i, w in enumerate(expected, 1):
            self.assertAlmostEqual(got[i], w)

    def test_fractional_forced_slot_leaves_normal_fallback(self):
        s, a, ctx = self.make()
        s.apply_buff(a, self.effect('자신 제외 아군 1명', .5), ctx, 1)
        self.buff(s.party[1], '확률', {'협공 확률': 100})
        self.assertEqual(self.calls(s, a, ctx), {1: .5, 3: .5})

    def test_effect_target_is_not_random_final_candidate(self):
        s, a, ctx = self.make()
        a.d.key = 'professor-m'
        rows = [(slot, raw) for key, slot, raw in engine._forced_coop_lines() if key == a.d.key]
        self.assertEqual(len(rows), 4)
        # 최고 공격력 유닛은 기절. 표의 행위불가 필터 뒤 공격력 1위는 2번.
        self.buff(s.party[3], '기절')
        with patch.object(s, 'cast') as cast:
            for slot, raw in rows:
                s.apply_line(a, Line(raw, slot, 'passive'), ctx, 1)
            cast.assert_not_called()
        self.assertEqual([b.forced_coop for b in s.party], [0, 0, 1, 0])
        self.assertEqual(s.party[2].stack('표본 행동 분석'), 1)
        self.assertEqual(self.calls(s, a, ctx), {2: 1})

    def test_live_atk_and_stat_atk_legacy_stay_immediate(self):
        for mode, winner in [('live_atk', 1), ('stat_atk', 3)]:
            s, a, ctx = self.make(mode)
            self.buff(s.party[1], '공격', {'공격력%': 400})
            with patch.object(s, 'cast') as cast:
                s.apply_buff(a, self.effect('자신 제외 아군 1명'), ctx, 1)
                self.assertEqual(cast.call_count, 1)
                self.assertEqual(cast.call_args.args[0].idx, winner)
            self.assertEqual(ctx.coop_used, 1)
            self.assertFalse(any(b.forced_coop for b in s.party))

    def professor_marker(self, a):
        a.d.key = 'professor-m'
        slot, raw = next((slot, raw) for key, slot, raw in engine._forced_coop_lines()
                         if key == a.d.key and '〈표본 행동 분석 대상 체크용 버프〉' in raw)
        return Line(raw, slot, 'passive')

    def test_effect_target_allows_broken_but_final_candidate_does_not(self):
        s, a, ctx = self.make()
        ln = self.professor_marker(a)
        s.party[3].broken = True
        self.assertEqual(s._forced_effect_targets(a, ln), ('a', [s.party[3]]))
        s.apply_buff(a, self.effect(), ctx, 1, targets=('a', [s.party[3]]))
        self.buff(s.party[1], '확률', {'협공 확률': 100})
        self.assertEqual(self.calls(s, a, ctx), {1: 1})

    def test_effect_filter_stops_at_one_before_disable_filter(self):
        s, a, ctx = self.make()
        ln = self.professor_marker(a)
        self.buff(s.party[1], '협공 불가')
        self.buff(s.party[2], '기절')
        self.buff(s.party[3], '수면')
        with patch.object(s, 'live_atk', wraps=s.live_atk) as attack:
            self.assertEqual(s._forced_effect_targets(a, ln), ('a', [s.party[1]]))
            attack.assert_not_called()

    def test_empty_effect_filter_keeps_previous_pool(self):
        s, a, ctx = self.make()
        ln = self.professor_marker(a)
        for b in s.party[1:]:
            self.buff(b, '기절')
        self.assertEqual(s._forced_effect_targets(a, ln), ('a', [s.party[3]]))

    def test_enemy_turn_also_clears_force_flag(self):
        s, a, ctx = self.make()
        s.party[1].forced_coop = 1
        s.act_enemy(s.enemies[0])
        self.assertFalse(any(b.forced_coop for b in s.party))

    def test_actual_damage_then_coop_and_turn_clear(self):
        s, a, ctx = self.make()
        a.d.lines = [Line('[스킬 사용 후] 자신 제외 아군 1명에게 〈강제 협공〉', '기본기', 'active')]
        events = []
        original = s.deal_damage
        def record(unit, context):
            events.append(unit.idx)
            original(unit, context)
        with patch.object(s, 'choose_skill', return_value=a.d.skills['기본기']), patch.object(s, 'deal_damage', side_effect=record):
            s.act_ally(a)
        self.assertEqual(events, [0, 3])
        self.assertGreater(a.dmg, 0)
        self.assertGreater(s.party[3].dmg, 0)
        self.assertEqual(s.party[3].cast_count['기본기(추가)'], 1)
        self.assertFalse(any(b.forced_coop for b in s.party))


if __name__ == '__main__':
    unittest.main()
