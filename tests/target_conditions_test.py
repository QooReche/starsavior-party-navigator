"""PC build 26610546 target conditions; public/synthetic inputs only. --mutate verifies guards."""
import copy
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim import simulate
from battlesim.mc import Battle, Ctx
from battlesim.metrics import unit_def
from battlesim.starsavior.parser import Line
from battlesim.starsavior.foe import FoeDef, load_foe


class TargetConditionsTest(unittest.TestCase):
    def asherah(self, mode='event', sa=(99, 1)):
        b = battle([unit_def('asherah-order-striker')],
                   [unit('foe%d' % i, hp=10**9, sa=s) for i, s in enumerate(sa)],
                   mc={'target_break_condition': mode}, opts={'coop': False, 'nova': False})
        b.allies[0].acting = True
        return b

    def test_asherah_second_target_break_and_old_break(self):
        for mode, expected in [('event', [True, False]), ('state', [False, True])]:
            outcomes = []
            for old in (False, True):
                b = self.asherah(mode)
                a = b.allies[0]
                if old:
                    for v in b.foes:
                        v.sa, v.broken = 0, True
                c = b.cast(a, a.d.skills['특수기'])
                self.assertGreater(b.progress(), 0)
                self.assertEqual(bool(c.break_targets), not old)
                outcomes.append(a.has('추가 턴 대기 확인용 버프'))
            self.assertEqual(outcomes, expected)

    def test_break_window_does_not_leak_to_next_cast(self):
        b = self.asherah(sa=(1,))
        a = b.allies[0]
        first = b.cast(a, a.d.skills['특수기'])
        self.assertTrue(a.has('추가 턴 대기 확인용 버프'))
        a.eff.pop('추가 턴 대기 확인용 버프')
        b.dirty(a)
        second = b.cast(a, a.d.skills['기본기'], extra=True, parent=first)
        self.assertGreater(b.progress(), 0)
        self.assertFalse(second.break_targets)
        self.assertFalse(a.has('추가 턴 대기 확인용 버프'))

    def test_enemy_hit_break_is_victim_and_only_new_event(self):
        raw = load_foe()
        # Real Olberos minion passive, alongside a higher-HP ally receiving the soul.
        foe = FoeDef(raw, 34, stats_override={'hp': 10**8, 'sa': 1})
        for mode, expected in [('event', [1, 1]), ('state', [1, 2])]:
            b = battle([unit_def('asherah-order-striker')], [foe, unit('boss', hp=10**9, sa=99)],
                       mc={'target_break_condition': mode}, opts={'coop': False, 'nova': False})
            a, v, boss = b.allies[0], *b.foes
            stacks = []
            for _ in range(2):
                b.cast(a, a.d.skills['기본기'], target=v)
                stacks.append(boss.stack('영웅의 혼(해제불가)'))
            self.assertGreater(b.progress(), 0)
            self.assertEqual(v.breaks, 1)
            self.assertEqual(stacks, expected)
            self.assertFalse(v.has('영웅의 혼(해제불가)'))

    def test_dana_self_buff_on_second_low_hp_target(self):
        for mode, expected in [('any', True), ('first', False)]:
            b = battle([unit_def('dana')], [unit('healthy', hp=10**9), unit('low', hp=10**9)],
                       mc={'target_condition_set': mode}, opts={'coop': False, 'nova': False})
            b.foes[1].hp *= .4
            a = b.allies[0]
            b.cast(a, a.d.skills['궁극기'])
            self.assertGreater(b.progress(), 0)
            self.assertEqual(a.has('로로카!(해제불가)'), expected)
            self.assertTrue(all(not v.has('로로카!(해제불가)') for v in b.foes))

    def test_lydia_self_buff_on_second_debuffed_target(self):
        for mode, expected in [('any', 1), ('first', 0)]:
            b = battle([unit_def('lydia')], [unit('clean', hp=10**9), unit('debuffed', hp=10**9)],
                       mc={'target_condition_set': mode}, opts={'coop': False, 'nova': False})
            give(b.foes[0], '면역')
            give(b.foes[1], '속도 감소', {'속도%': -20}, harmful=True)
            a = b.allies[0]
            b.cast(a, a.d.skills['특수기'])
            self.assertGreater(b.progress(), 0)
            self.assertEqual(b.foes[0].n_harmful(), 0)
            self.assertEqual(a.stack('공허의 추구자'), expected)
            self.assertTrue(all(not v.has('공허의 추구자') for v in b.foes))

    def test_frey_checks_before_heal_and_gauges_all_allies(self):
        for mode, expected in [('any', 1500), ('first', 0)]:
            b = battle([unit_def('frey'), unit('low'), unit('healthy')], [unit('foe', hp=10**9)],
                       mc={'target_condition_set': mode}, opts={'coop': False, 'nova': False})
            a = b.allies[0]
            b.allies[1].hp *= .7
            b.cast(a, a.d.skills['궁극기'])
            self.assertGreater(b.allies[1].hp / b.allies[1].maxhp, .75)
            self.assertEqual([round(v.gauge, 8) for v in b.allies], [expected] * 3)

    def test_post_conditions_must_match_same_target(self):
        b = self.asherah()
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['특수기'])
        ctx.target, ctx.targets = b.foes[0], b.foes
        b.foes[0].hp *= .4
        ctx.break_targets.add(b.foes[1])
        ln = Line('[스킬 사용 후] (조건: 내 공격 후 [대상 HP% 이하: 5000; 대상 브레이크: 예]) 자신에게 행동 게이지 10%p 증가', '특수기', 'active')
        self.assertFalse(b.cond_ok(a, ln, ctx))
        b.foes[1].hp *= .4
        self.assertTrue(b.cond_ok(a, ln, ctx))
        ctx.targets, ctx.target = [], None
        self.assertFalse(b.cond_ok(a, ln, ctx))

    def test_pre_conditions_independent_but_debuff_count_stays_on_one_target(self):
        b = self.asherah()
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['특수기'])
        ctx.target, ctx.targets = b.foes[0], b.foes
        b.foes[0].hp *= .4
        give(b.foes[1], '속도 감소', {'속도%': -20}, harmful=True)
        give(b.foes[1], '방어력 감소', {'방어력%': -30}, harmful=True)
        ln = Line('[스킬 사용 시작 시] (조건: 내 공격 시 [대상 HP% 이하: 5000; 대상 약화효과 보유: 예; 효과 개수 이상: 2]) 자신에게 행동 게이지 10%p 증가', '특수기', 'active')
        self.assertTrue(b.cond_ok(a, ln, ctx))
        b.foes[1].eff.pop('방어력 감소')
        give(b.foes[0], '방어력 감소', {'방어력%': -30}, harmful=True)
        self.assertFalse(b.cond_ok(a, ln, ctx))

    def test_single_target_does_not_borrow_break_or_debuff(self):
        b = self.asherah()
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = b.foes[0], [b.foes[0]]
        ctx.break_targets.add(b.foes[1])
        give(b.foes[1], '속도 감소', {'속도%': -20}, harmful=True)
        for condition in ['대상 브레이크: 예', '대상 약화효과 보유: 예']:
            ln = Line(f'[스킬 사용 후] (조건: 내 공격 후 [{condition}]) 자신에게 행동 게이지 10%p 증가', '기본기', 'active')
            self.assertFalse(b.cond_ok(a, ln, ctx))
    def test_real_reproductions_execute_effects(self):
        for floor, seed, key, effect in [(250, 13, 'dana', '로로카!(해제불가)'),
                                         (200, 8, 'lydia', '공허의 추구자'),
                                         (200, 7, 'frey', '전력지원 생명력 체크용 버프')]:
            hits = []
            original = Battle._exec_line
            def record(b, owner, ln, ctx):
                if owner.key == key and ln.eff.get('name') == effect and len(ctx.targets) > 1:
                    probe = copy.copy(ctx)
                    probe.targets = [ctx.target]
                    if not b._cond_values(owner, ln, probe):
                        hits.append(ln.raw)
                return original(b, owner, ln, ctx)
            with patch.object(Battle, '_exec_line', record):
                r = simulate(dict(units=['dana', 'lydia', 'frey', 'hilde'], leader=0),
                             dict(stage=f'clo/태양 회랑/FLOOR {floor}'),
                             dict(build='standard', n_runs=1, seed=seed))
            self.assertGreater(r['prog_runs'][0], 0)
            self.assertTrue(hits, (key, effect))


def mutations():
    original = Battle.cond_ok
    def legacy(rule, value):
        def broken(b, owner, ln, ctx):
            with patch.dict(b.mc, {rule: value}):
                return original(b, owner, ln, ctx)
        return broken
    cases = [('break state', 'target_break_condition', 'state', 'test_asherah_second_target_break_and_old_break'),
             ('victim event', 'target_break_condition', 'state', 'test_enemy_hit_break_is_victim_and_only_new_event'),
             ('HP first', 'target_condition_set', 'first', 'test_dana_self_buff_on_second_low_hp_target'),
             ('debuff first', 'target_condition_set', 'first', 'test_lydia_self_buff_on_second_debuffed_target'),
             ('preheal first', 'target_condition_set', 'first', 'test_frey_checks_before_heal_and_gauges_all_allies')]
    for name, rule, value, test in cases:
        with patch.object(Battle, 'cond_ok', legacy(rule, value)):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(TargetConditionsTest(test))
        if result.errors or not result.failures:
            raise AssertionError((name, result.errors, result.failures))
        print('detected:', name)
    original_strike, original_exec = Battle.strike, Battle._exec_line
    def lose_victim_event(b, a, v, base, ctx, crit, cdv, pen, reactions, evaded=False):
        result = original_strike(b, a, v, base, ctx, crit, cdv, pen, reactions, evaded)
        for _, hctx in reactions:
            hctx.break_targets = set()
        return result
    def wrong_recipient(b, owner, ln, ctx):
        if ln.eff.get('name') == '로로카!(해제불가)':
            ln = copy.copy(ln)
            ln.eff = dict(ln.eff, target='스킬 대상')
        return original_exec(b, owner, ln, ctx)
    def drop_reproduced_effect(b, owner, ln, ctx):
        if ln.eff.get('name') not in ('로로카!(해제불가)', '공허의 추구자', '전력지원 생명력 체크용 버프'):
            return original_exec(b, owner, ln, ctx)
    # An execution guard must observe state, not merely that a line was attempted.
    extra = [('lost victim event', '_strike', lose_victim_event, 'test_enemy_hit_break_is_victim_and_only_new_event'),
             ('wrong recipient', '_exec_line', wrong_recipient, 'test_dana_self_buff_on_second_low_hp_target'),
             ('lost effect', '_exec_line', drop_reproduced_effect, 'test_frey_checks_before_heal_and_gauges_all_allies')]
    for name, attr, fn, test in extra:
        with patch.object(Battle, 'strike' if attr == '_strike' else attr, fn):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(TargetConditionsTest(test))
        if result.errors or not result.failures:
            raise AssertionError((name, result.errors, result.failures))
        print('detected:', name)


if __name__ == '__main__':
    mutations() if '--mutate' in sys.argv else unittest.main()
