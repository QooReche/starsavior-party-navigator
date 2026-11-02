# -*- coding: utf-8 -*-
"""현재 빌드의 강제 협공: 효과 대상 → 플래그 → 유효 후보 균등 선정."""
import os
import sys
import unittest
from collections import Counter
from unittest.mock import Mock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from battlesim import simulate, rules
from battlesim.mc import Battle, Ctx
from battlesim.metrics import unit_def
from p3_test import battle, give, unit


class ForcedCoopTest(unittest.TestCase):
    def setup_battle(self, mode='random'):
        b = battle([unit('a%d' % i, atk=1000 * (i + 1)) for i in range(4)],
                   [unit('foe', hp=10 ** 8)], opts={'forced_coop_target': mode})
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target = b.foes[0]
        return b, a, ctx

    def test_default_and_legacy(self):
        self.assertEqual(rules.DEFAULT_OPTS['forced_coop_target'], 'random')
        self.assertEqual(rules.RULES['opts']['forced_coop_target']['legacy'], 'live_atk')
        self.assertEqual(rules.DEFAULT_OPTS['coop_dead_target'], 'cancel')
        self.assertNotIn('coop_dead_target', rules.MC_OPTS)  # 공통 opts이며 MC 전용 키가 아님
        for mode in ('live_atk', 'stat_atk'):
            b, a, ctx = self.setup_battle(mode)
            give(b.allies[1], '공격력', {'공격력%': 200})
            with patch.object(b, 'cast') as cast:
                b.forced_coop(a, ctx, 1)
            self.assertIs(cast.call_args.args[0], b.allies[1 if mode == 'live_atk' else 3])

    def test_effect_only_marks_resolved_targets(self):
        b, a, ctx = self.setup_battle()
        eff = {'name': '강제 협공', 'target': '아군 전체', 'chance': 1.0}
        with patch.object(b, 'resolve', return_value=[b.allies[1], b.allies[2]]), patch.object(b, 'cast') as cast:
            b.apply_buff(a, eff, ctx)
        self.assertEqual(b._forced_coop_candidates, set(b.allies[1:3]))
        cast.assert_not_called()
        self.assertFalse(ctx.coop_used)

    def test_uniform_forced_priority_and_single_slot(self):
        b, a, ctx = self.setup_battle()
        b._forced_coop_candidates.update(b.allies[:3])  # 자신은 후보에서 빠짐
        give(b.allies[3], '일반 협공', {'협공 확률': 100})
        rng = Mock()
        rng.choice.side_effect = lambda seq: seq[-1]
        with patch.object(b, 'R', return_value=rng), patch.object(b, 'cast') as cast:
            b.coop(a, ctx)
            b.coop(a, ctx)
        rng.choice.assert_called_once()
        self.assertEqual(rng.choice.call_args.args[0], b.allies[1:3])
        rng.random.assert_not_called()
        self.assertEqual(cast.call_count, 1)
        self.assertIs(cast.call_args.args[0], b.allies[2])
        self.assertEqual(cast.call_args.kwargs['via'], 'forced_coop')
        self.assertIs(cast.call_args.kwargs['target'], ctx.target)

    def test_seeded_uniform_distribution(self):
        b, a, ctx = self.setup_battle()
        b._forced_coop_candidates.update(b.allies[1:])
        counts = Counter()
        with patch.object(b, 'cast', side_effect=lambda u, *args, **kw: counts.update([u.pos])):
            for _ in range(6000):
                ctx.coop_used = False
                b.coop(a, ctx)
        self.assertEqual(sum(counts.values()), 6000)
        for pos in (1, 2, 3):
            self.assertLess(abs(counts[pos] - 2000), 150)

    def test_ineligible_forced_falls_back_to_all_normal_rolls(self):
        for reason in ('dead', 'broken', 'stun', 'sleep', 'disabled', 'cooldown', 'missing', 'passive'):
            with self.subTest(reason=reason):
                b, a, ctx = self.setup_battle()
                u = b.allies[1]
                b._forced_coop_candidates.add(u)
                if reason in ('dead', 'broken'):
                    setattr(u, reason, True)
                elif reason in ('stun', 'sleep', 'disabled'):
                    give(u, {'stun': '기절', 'sleep': '수면', 'disabled': '협공 불가'}[reason])
                elif reason == 'cooldown':
                    u.cd['기본기'] = 1
                elif reason == 'missing':
                    del u.d.skills['기본기']
                else:
                    u.d.skills['기본기'].ty = '패시브'
                for v in b.allies[2:]:
                    give(v, '협공', {'협공 확률': 50})
                rng = Mock()
                rng.random.side_effect = [0.2, 0.3]
                rng.choice.side_effect = lambda seq: seq[-1]
                with patch.object(b, 'R', return_value=rng), patch.object(b, 'cast') as cast:
                    b.coop(a, ctx)
                self.assertEqual(rng.random.call_count, 2)
                self.assertEqual(rng.choice.call_args.args[0], b.allies[2:])
                self.assertEqual(cast.call_args.kwargs['via'], 'coop')

    def test_finish_action_clears_flags(self):
        b, a, ctx = self.setup_battle()
        b._forced_coop_candidates.update(b.allies)
        b._finish_action(a)
        self.assertFalse(b._forced_coop_candidates)
        with patch.object(b, 'cast') as cast:
            b.coop(a, ctx)
        cast.assert_not_called()

    def test_forced_and_normal_switches_remain_independent(self):
        b, a, ctx = self.setup_battle()
        b.opts['coop'] = False
        b._forced_coop_candidates.add(b.allies[1])
        give(b.allies[2], '협공', {'협공 확률': 100})
        b.cast(a, a.d.skills['기본기'], target=ctx.target)
        self.assertEqual(b.allies[1].cast_count.get('기본기(추가)', 0), 1)
        self.assertEqual(b.allies[2].cast_count.get('기본기(추가)', 0), 0)

    def test_dead_single_target_cancels_forced_and_normal_before_retarget(self):
        for forced in (False, True):
            for mode in ('cancel', 'retarget'):
                with self.subTest(forced=forced, mode=mode):
                    b = battle([unit('actor', atk=100000), unit('follower')],
                               [unit('first', hp=1), unit('second', hp=10**8)],
                               opts={'coop_dead_target': mode})
                    a, u = b.allies
                    if forced:
                        b._forced_coop_candidates.add(u)
                    else:
                        give(u, '협공', {'협공 확률': 100})
                    b.cast(a, a.d.skills['기본기'], target=b.foes[0])
                    self.assertTrue(b.foes[0].dead)
                    self.assertGreater(b.progress(), 0)
                    self.assertEqual(u.cast_count.get('기본기(추가)', 0), int(mode == 'retarget'))
                    self.assertEqual(b.foes[1].taken > 0, mode == 'retarget')

    def test_expected_dead_target_cancels_forced_and_normal(self):
        from battlesim import engine
        for forced in (False, True):
            for mode in ('cancel', 'retarget'):
                with self.subTest(forced=forced, mode=mode):
                    defs = [engine.DummyDef(atk=100000), engine.DummyDef(atk=1000)]
                    for d in defs:
                        d.dummy = False
                    s = engine.Sim(defs, [{'hp': 1}, {'hp': 10**8}], opts={'coop_dead_target': mode})
                    a, u = s.party
                    if forced:
                        u.forced_coop = 1
                    else:
                        eff = engine.Buff('협공', {'협공 확률': 100}, 1, 3)
                        eff.stacks = 1
                        u.buffs[eff.name] = eff
                    s.cast(a, a.d.skills['기본기'])
                    self.assertTrue(s.enemies[0].dead)
                    self.assertGreater(a.dmg, 0)
                    self.assertEqual(u.cast_count.get('기본기(추가)', 0), int(mode == 'retarget'))

    def test_professor_effect_target_uses_marker_not_global_attack_rank(self):
        b = battle([unit_def('professor-m')] + [unit('u%d' % i, atk=1000 + i * 1000) for i in range(3)],
                   [unit('foe', hp=10 ** 8)])
        a = b.allies[0]
        # 가장 낮은 공격력의 후보만 표식을 받았다고 가정. 효과 타겟은 그 표식임.
        give(b.allies[1], '표본 행동 분석 대상 체크용 버프')
        ln = next(x for x in a.d.lines if x.eff.get('name') == '강제 협공')
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target = b.foes[0]
        b._cur_line = ln
        with patch.object(b, 'cast') as cast:
            b.apply_buff(a, ln.eff, ctx)
        cast.assert_not_called()
        self.assertEqual(b._forced_coop_candidates, {b.allies[1]})

    def test_real_battle_exercises_forced_path(self):
        seen = []
        original = Battle.coop

        def spy(b, a, ctx):
            if b._forced_coop_candidates and ctx.skill.slot == '기본기':
                seen.append(len(b._forced_coop_candidates))
            return original(b, a, ctx)

        with patch.object(Battle, 'coop', spy):
            result = simulate(['professor-m', 'hilde', 'amora', 'ceres-sun-supporter'],
                              {'stage': 'clo/달 회랑/FLOOR 100'},
                              {'seed': 17, 'n_runs': 2, 'build': 'standard'})
        self.assertGreater(result['outcome']['progress'], 0)
        self.assertGreater(result['ally_via'].get('forced_coop', 0), 0)
        self.assertGreater(len(seen), 0)
        print('강제 협공 실제 경로 %d회, progress=%.4f' % (len(seen), result['outcome']['progress']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
