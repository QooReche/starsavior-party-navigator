# -*- coding: utf-8 -*-
"""Client rule boundaries; --mutations disables each implementation in memory.

Only public standard builds and synthetic units are used.
"""
import collections
import inspect
import io
import math
from pathlib import Path
import sys
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim import simulate
from battlesim.api import assumptions_used
import battlesim.mc as M
from battlesim.mc import Battle, Ctx
from battlesim.metrics import unit_def
from battlesim.rules import MC_OPTS, MC_RULES, DEFAULT_OPTS
from battlesim.starsavior.parser import Line, Skill
from battlesim.starsavior.cosmo_raid import Controller


def dot(u, src, duration=1, name='연소'):
    e = give(u, name, src=src, harmful=True, dur=duration)
    e.dot, e.inst = ('atk', .2), [[src, duration]]
    return e


class RulesTest(unittest.TestCase):
    def test_defaults(self):
        for key, new, legacy in [
            ('dot_hot_order', 'hot_first', 'insertion'),
            ('dot_hot_lifetime', 'tick', 'turn_end'),
            ('ally_cd_tick', 'turn_end', 'turn_start'),
            ('stat_select_int', 'floor', 'float'),
            ('break_domain_category', 'marker', 'buff'),
            ('ally_turn_self', 'condition', 'exclude'),
            ('fixed_true_formula', 'legacy', 'legacy'),
            ('counter_slot_timing', 'end', 'end')]:
            self.assertEqual(MC_OPTS[key], new)
            self.assertEqual(MC_RULES[key]['legacy'], legacy)
            for field in ('alt', 'grade', 'note', 'source'):
                self.assertTrue(MC_RULES[key][field])

    def test_dot_hot_order(self):
        for order in ('hot_first', 'insertion'):
            b = battle([unit()], [unit()], mc={'dot_hot_order': order})
            u, f = b.allies[0], b.foes[0]
            u.hp = 100
            dot(u, f)
            give(u, 'regen').hot = .1
            b._tick_dot_hot(u)
            self.assertEqual(u.dead, order == 'insertion')
            if order == 'hot_first':
                self.assertGreater(u.hp, 100)
                self.assertEqual(b.rule_hits['dot_hot_order'], 1)

    def test_dot_hot_lifetime(self):
        for mode in ('tick', 'turn_end'):
            b = battle([unit()], [unit(hp=10**7)], mc={'dot_hot_lifetime': mode}, opts={'coop': False})
            u, f = b.allies[0], b.foes[0]
            e = dot(u, f)
            e.inst += [[f, 2], [f, math.inf]]
            e.stacks = 3
            e.fresh = e.skip_tick = True  # periodic ticks ignore generic fresh/skip flags
            h = give(u, 'regen', dur=1)
            h.hot, h.fresh = .1, True
            seen = []
            original = b.cast
            def cast(*a, **kw):
                seen.append((u.has('regen'), [it[1] for it in e.inst], u.n_harmful()))
                return original(*a, **kw)
            with patch.object(b, 'cast', cast):
                b.act(u)
            self.assertEqual(len(seen), 1)
            self.assertEqual(seen[0], (False, [1, math.inf], 2) if mode == 'tick'
                             else (True, [1, 2, math.inf], 3))
            self.assertEqual([it[1] for it in e.inst], seen[0][1])  # no second decrement
            self.assertEqual(b.rule_hits['dot_hot_lifetime'], 4 if mode == 'tick' else 0)

    def test_periodic_global_and_zero_damage(self):
        b = battle([unit('owner'), unit('turn')], [unit()])
        u, turn = b.allies
        e = dot(u, turn, 2)  # same-side zero damage still consumes a tick
        h = give(u, 'regen', dur=2)
        h.hot, h.clock = .1, 'any_turn'
        b._tick_dot_hot(u)
        self.assertEqual(e.inst[0][1], 1)
        self.assertEqual(h.dur, 1)
        b._tick_dot_hot(turn)
        self.assertFalse(u.has('regen'))
        self.assertEqual(e.inst[0][1], 1)
        b._tick_any_turn()
        self.assertEqual(e.inst[0][1], 1)

    def test_periodic_not_decremented_again_at_end(self):
        for clock in ('owner_turn', 'any_turn'):
            b = battle([unit()], [unit(hp=10**7)], opts={'coop': False})
            u, f = b.allies[0], b.foes[0]
            e = dot(u, f, 3)
            h = give(u, 'regen', dur=3)
            e.clock = h.clock = clock
            h.hot = .1
            b.act(u)  # includes both owner-turn and any-turn end processing
            self.assertEqual(e.inst[0][1], 2)
            self.assertEqual(h.dur, 2)
            b.act(u)
            self.assertEqual(e.inst[0][1], 1)
            self.assertEqual(h.dur, 1)

    def test_ally_cd_tick(self):
        for mode in ('turn_end', 'turn_start'):
            b = battle([unit(skills=[dict(slot='기본기', dm=100), dict(slot='궁극기', dm=100, cd=5)])],
                       [unit(hp=10**8)], mc={'ally_cd_tick': mode, 'enemy_cd_end_order': 'before_effects'},
                       opts={'coop': False})
            u = b.allies[0]
            u.cd['궁극기'] = 1
            give(u, 'expiry', dur=1)
            seen = []
            orig_fire, orig_tick = b.fire, b._tick_cooldowns
            def fire(owner, kind, ctx):
                if owner is u and kind in ('own_ts', 'own_te'):
                    seen.append((kind, u.cd['궁극기']))
                return orig_fire(owner, kind, ctx)
            def tick(owner):
                seen.append(('tick', owner.has('expiry')))
                return orig_tick(owner)
            with patch.object(b, 'fire', fire), patch.object(b, '_tick_cooldowns', tick):
                b.act(u)
            if mode == 'turn_end':
                self.assertEqual(seen, [('own_ts', 1), ('own_te', 1), ('tick', False)])
                self.assertEqual(u.cd['궁극기'], 0)
                self.assertEqual(b.rule_hits['ally_cd_tick'], 1)
            else:
                self.assertEqual(seen, [('tick', True), ('own_ts', 0), ('own_te', 5)])
                self.assertEqual(u.cd['궁극기'], 5)
        # A just-used skill, CC and a break recovery turn all get exactly one end tick.
        for state in ('normal', 'stun', 'broken', 'dead'):
            b = battle([unit(skills=[dict(slot='궁극기', dm=100, cd=5)])], [unit(hp=10**8)], opts={'coop': False})
            u = b.allies[0]
            if state in ('stun', 'broken'):
                u.cd['궁극기'] = 3
            if state == 'stun':
                give(u, '기절')
            if state == 'broken':
                u.broken = True
            if state == 'dead':
                u.hp = 1
                dot(u, b.foes[0])
            b.act(u)
            self.assertEqual(b.rule_hits['ally_cd_tick'], int(state != 'dead'))
            if state != 'dead':
                self.assertEqual(u.cd['궁극기'], 4 if state == 'normal' else 2)

    def test_stat_select_int(self):
        b = battle([unit('a', df=1000.1), unit('b', df=1000.9)], [unit()])
        a, other = b.allies
        self.assertEqual(b._filter(a, b.allies, 'high_def'), b.allies)
        self.assertEqual(b.rule_hits['stat_select_int'], 1)
        b.mc['stat_select_int'] = 'float'
        self.assertEqual(b._filter(a, b.allies, 'high_def'), [other])

    def test_break_domain_category(self):
        for mode in ('marker', 'buff'):
            b = battle([unit()], [unit(hp=10**8)], break_skill={'name': '큐브 과부하'},
                       mc={'break_domain_category': mode, 'break_domain_revive': 'client'})
            u = b.allies[0]
            b.break_points = 3
            b._use_break_skill(u)
            self.assertEqual(u.eff['치트 매트릭스'].category, mode)
            self.assertEqual(u.eff['오메가 프로토콜'].category, 'buff')
            self.assertEqual(u.n_good(), 1 if mode == 'marker' else 2)
            self.assertGreater(u.spd(), u.d.spd_base)
            del u.eff['치트 매트릭스']
            b._restore_break_domain(u)
            self.assertEqual(u.eff['치트 매트릭스'].category, mode)
            self.assertEqual(b.rule_hits['break_domain_category'], 2 if mode == 'marker' else 0)

    def test_ally_turn_self(self):
        for mode in ('condition', 'exclude'):
            b = battle([unit_def('lydia-moon-caster'), unit('other')], [unit(hp=10**9)],
                       mc={'ally_turn_self': mode}, opts={'coop': False})
            u, other = b.allies
            name = '메이드 리디아 패시브 행게 카운팅 버프'
            give(u, name, dur=math.inf)
            b.act(u)
            self.assertEqual(u.has(name), mode == 'exclude')
            self.assertEqual(b.rule_hits['ally_turn_self'], int(mode == 'condition'))
            give(u, name, dur=math.inf)
            b.act(other)
            self.assertFalse(u.has(name))

    def test_fixed_true_formula(self):
        for mode in ('client', 'legacy'):
            b = battle([unit('target'), unit('guard')], [unit('source')], mc={'fixed_true_formula': mode})
            target, guard = b.allies
            source = b.foes[0]
            give(guard, '수호', {'피해 분담(수호)': 50})
            b.pen = (1, 2)
            # Cap the main target before shields, but independently cap the guard.
            target.d.stats['NST_RATE_DAMAGE_LIMIT_BY_HP'] = 50  # 50 HP
            give(guard, 'cap', {'NST_RATE_DAMAGE_LIMIT_BY_HP': 30})  # 30 HP
            give(target, 'shield').shield = 20
            b.fixed_true_damage(source, target, 101.9)
            self.assertEqual(target.hp, 9970 if mode == 'client' else 9918.1)
            self.assertEqual(guard.hp, 9970 if mode == 'client' else 10000)
            self.assertEqual(b.rule_hits['fixed_true_formula'], 2 if mode == 'client' else 0)

    def test_fixed_boundaries_and_exceptions(self):
        for immune in ('none', '무적', '스킬 피해 무효'):
            b = battle([unit('target'), unit('guard')], [unit()], mc={'fixed_true_formula': 'client'})
            target, guard = b.allies
            give(guard, '수호', {'피해 분담(수호)': 50})
            if immune != 'none':
                give(target, immune)
            b.fixed_true_damage(None, target, 11.9, source_side=target.side)
            self.assertEqual(target.hp, {'none': 9995, '무적': 10000, '스킬 피해 무효': 9989}[immune])
            self.assertEqual(guard.hp, 9995 if immune == 'none' else 10000)
            if immune != 'none':
                self.assertTrue(target.has(immune))
        b = battle([unit(hp=10**12)], [unit()], mc={'fixed_true_formula': 'client'})
        target = b.allies[0]
        b.pen = (10, 1)
        self.assertEqual(b.fixed_true_damage(None, target, 7.9, source_side=0), 7)
        self.assertEqual(b.fixed_true_damage(None, target, 10**15, source_side=0), 2147483647)
        target.d.boss = True
        target.hp = math.ceil(target.maxhp * .5) + 10
        self.assertEqual(b.fixed_true_damage(None, target, 100, remaining_hp_bp=5000), 10)
        self.assertEqual(b.fixed_true_damage(None, target, 100, remaining_hp_bp=5000), 1)
        self.assertEqual(b.fixed_true_damage(None, target, 0), 1)

    def test_fixed_queue(self):
        b = battle([unit()], [unit()], mc={'fixed_true_formula': 'client'})
        c = Controller(b)
        c.pending_damage = [(b.foes[0], 10.9)]
        c.flush_damage()
        c.flush_damage()
        self.assertEqual(b.foes[0].hp, 9990)
        self.assertEqual(c.stats['true_damage_hits'], 1)
        self.assertEqual(b.rule_hits['fixed_true_formula'], 1)

    def test_counter_slot_timing(self):
        for mode in ('event', 'end'):
            b = battle([unit(skills=[dict(slot='궁극기', dm=100)])], [unit(hp=10**7)],
                       mc={'counter_slot_timing': mode}, opts={'coop': False})
            u = b.allies[0]
            u.last_slot = '기본기'
            seen = []
            original = b.run_own
            def own(owner, ctx, kind):
                if kind in ('own_pre', 'own_post'):
                    seen.append((kind, owner.last_slot))
                return original(owner, ctx, kind)
            with patch.object(b, 'run_own', own):
                b.cast(u, u.d.skills['궁극기'])
            self.assertEqual(seen, [('own_pre', '기본기'), ('own_post', '궁극기' if mode == 'event' else '기본기')])
            self.assertEqual(b.rule_hits['counter_slot_timing'], int(mode == 'event'))
            self.assertEqual(u.last_slot, '궁극기')

    def test_counter_nested_and_heal(self):
        b = battle([unit()], [unit(hp=10**7)], mc={'counter_slot_timing': 'event'}, opts={'coop': False})
        u = b.allies[0]
        # A heal-only event records even at full HP. A card without events does not.
        for act, hl, expected in [(None, None, 'old'), (None, '생명력×10%', '특수기'), ('비공격', None, '특수기')]:
            sk = Skill(dict(sl='특수기', n='test', ty='액티브', tg='자신', act=act, hl=hl))
            u.last_slot = 'old'
            b.cast(u, sk)
            self.assertEqual(u.last_slot, expected)
        sk = Skill(dict(sl='궁극기', n='outer', ty='액티브', tg='적 단일', act='공격', cf=[1, 0, 0, 0]))
        orig = b.run_own
        def nested(owner, ctx, kind):
            result = orig(owner, ctx, kind)
            if ctx.skill is sk and kind == 'own_post':
                b.cast(owner, owner.d.skills['기본기'], extra=True)
            return result
        with patch.object(b, 'run_own', nested):
            b.cast(u, sk)
        self.assertEqual(u.last_slot, '기본기')


class StandardTest(unittest.TestCase):
    def test_stage_progress_and_paths(self):
        # A controlled periodic boundary is added to a public standard battle.
        # The rest (Lydia condition, selection, cooldowns, orbital and events) is native.
        seen = []
        original = Battle.spawn_wave
        def spawn(b):
            result = original(b)
            seen.append(b)
            u = b.allies[0]
            dot(u, b.foes[0], 2)
            give(u, 'test regen', dur=2).hot = .05
            b.break_points = 3
            return result
        with patch.object(Battle, 'spawn_wave', spawn):
            r = simulate(['lydia-moon-caster', 'tyria', 'gwen', 'amora'],
                         {'stage': 'clo/달 회랑/FLOOR 100'},
                         {'build': 'standard', 'seed': 3, 'n_runs': 2,
                          'break_skill': {'name': '큐브 과부하'},
                          'rules_override': {'counter_slot_timing': 'event'}})
        self.assertGreater(r['outcome']['progress'], 0)
        hits = collections.Counter()
        for b in seen:
            hits.update(b.rule_hits)
        for key in ('dot_hot_order', 'dot_hot_lifetime', 'ally_cd_tick', 'stat_select_int',
                    'break_domain_category', 'ally_turn_self', 'counter_slot_timing'):
            self.assertGreater(hits[key], 0, (key, hits))

    def test_cosmo_fixed_path(self):
        seen = []
        orig = Battle.__init__
        def init(b, *a, **kw):
            orig(b, *a, **kw)
            seen.append(b)
        with patch.object(Battle, '__init__', init):
            r = simulate(['amora', 'bell', 'carmen', 'ceres'],
                         {'cosmo_raid': {'boss': 'belgras', 'step': 3, 'level': 0}},
                         {'build': 'standard', 'seed': 3, 'n_runs': 2,
                          'rules_override': {'fixed_true_formula': 'client'}})
        self.assertGreater(r['outcome']['progress'], 0)
        self.assertGreater(sum(b.rule_hits['fixed_true_formula'] for b in seen), 0)


def mutations():
    cases = [
        ('dot_hot_order', '_tick_dot_hot', 'test_dot_hot_order'),
        ('dot_hot_lifetime', '_tick_dot_hot', 'test_dot_hot_lifetime'),
        ('ally_cd_tick', '_act_turn', 'test_ally_cd_tick'),
        ('stat_select_int', '_filter', 'test_stat_select_int'),
        ('break_domain_category', '_use_break_skill', 'test_break_domain_category'),
        ('ally_turn_self', '_act_turn', 'test_ally_turn_self'),
        ('fixed_true_formula', 'fixed_true_damage', 'test_fixed_true_formula'),
        ('counter_slot_timing', 'cast', 'test_counter_slot_timing')]
    for key, method, test in cases:
        suite = lambda: unittest.TestSuite([RulesTest(test)])
        runner = unittest.TextTestRunner(stream=io.StringIO())
        assert runner.run(suite()).wasSuccessful(), (key, 'baseline failed')
        source = textwrap.dedent(inspect.getsource(getattr(Battle, method)))
        needle = "self.mc['%s']" % key
        assert needle in source, (key, method)
        altered = source.replace(needle, repr(MC_RULES[key]['legacy']))
        namespace = {}
        exec(compile(altered, '<mutation>', 'exec'), M.__dict__, namespace)
        with patch.object(Battle, method, namespace[method]):
            result = runner.run(suite())
        assert result.failures and not result.errors, (key, result.failures, result.errors)
        print('DETECTED', key, test)


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
