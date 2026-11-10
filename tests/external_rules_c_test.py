# -*- coding: utf-8 -*-
"""11/10 과제 C: 합성 전투 + 공개 standard 육성. 계정 자료 없음."""
import math
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from simkit import battle, give, unit
from battlesim.api import simulate
from battlesim.mc import Battle, Ctx, line_rest
from battlesim.rules import MC_OPTS, MC_RULES
from battlesim.starsavior.parser import Line

PARTY = ['sunshine-cat-smile', 'cristelle', 'white-pearl-luna', 'wedding-carmen']
CUBE = {'name': '큐브 과부하', 'level': 5}
DOMAIN = '치트 매트릭스'


def run_stage(mode, runs=4, **overrides):
    seen = []
    original = Battle.run

    def spy(b):
        result = original(b)
        seen.append(b)
        return result

    with patch.object(Battle, 'run', spy):
        result = simulate(PARTY, {'stage': 'clo/태양 회랑/FLOOR 250'},
                          {'build': 'standard', 'n_runs': runs, 'seed': 3,
                           'rules_override': dict(wave_carry=mode, **overrides)})
    return result, seen


def effect(b, owner, target, text, phase='스킬 사용 후'):
    ln = Line('[' + phase + '] ' + text, '기본기', 'active')
    ctx = Ctx(owner, owner, owner.d.skills['기본기'])
    ctx.target, ctx.targets = target, [target]
    b.run_special(owner, ln, ctx, line_rest(ln))


class DefaultsTest(unittest.TestCase):
    def test_switch_contract(self):
        for key, value, legacy in [('wave_carry', 'keep', 'keep'),
                                   ('shield_tick', 'turn_end', 'turn_start'),
                                   ('break_domain_revive', 'client', 'none')]:
            self.assertEqual(MC_OPTS[key], value)
            self.assertEqual(MC_RULES[key]['legacy'], legacy)
            self.assertEqual(MC_RULES[key]['grade'], 'code')
            self.assertTrue(MC_RULES[key]['source'])
        self.assertEqual(MC_OPTS['power_penalty'], 'off')


class WaveTest(unittest.TestCase):
    def setup_wave(self, mode, **mc):
        b = battle([unit('a'), unit('dead')], [unit('first')],
                   mc=dict(wave_carry=mode, **mc), break_skill=CUBE)
        b.waves.append([unit('second')])
        b.kill(b.allies[1], b.foes[0])
        return b, b.allies[0]

    def test_effects_instances_and_exclusions(self):
        for mode in ('keep', 'client'):
            with self.subTest(mode=mode):
                b, a = self.setup_wave(mode)
                old_foe = b.foes[0]
                give(a, 'buff', dur=1).fresh = True
                give(a, 'debuff', dur=2, harmful=True)
                give(a, 'shield', dur=1).shield = 100
                give(a, 'infinite', dur=math.inf)
                give(a, DOMAIN, dur=3).clock = 'global'
                give(a, 'global', dur=2).clock = 'any_turn'
                give(a, 'skip', dur=2).skip_tick = True
                give(a, 'hot', dur=1).hot = .1
                dot = give(a, 'dot', dur=2, harmful=True)
                dot.dot, dot.inst, dot.stacks = ('atk', .1), [[old_foe, 1], [old_foe, 2]], 2
                give(a, '도발', dur=math.inf, src=old_foe, harmful=True)
                give(b.allies[1], 'dead buff', dur=2)
                b.kill(old_foe, a)
                hp, cds = a.hp, dict(a.cd)
                b.spawn_wave()
                self.assertEqual((a.hp, a.cd), (hp, cds))
                self.assertEqual(b.allies[1].eff['dead buff'].dur, 2)
                self.assertEqual(a.eff[DOMAIN].dur, 3)
                self.assertEqual(a.eff['infinite'].dur, math.inf)
                if mode == 'client':
                    for name in ('buff', 'shield', 'hot', '도발'):
                        self.assertNotIn(name, a.eff)
                    self.assertEqual(a.eff['debuff'].dur, 1)
                    self.assertEqual(a.eff['global'].dur, 1)
                    self.assertEqual((dot.inst, dot.stacks), ([[old_foe, 1]], 1))
                    self.assertFalse(a.eff['skip'].skip_tick)
                    self.assertEqual(a.eff['skip'].dur, 2)
                    self.assertGreater(b.rule_hits['wave_carry'], 0)
                else:
                    self.assertEqual(a.eff['buff'].dur, 1)
                    self.assertEqual(a.eff['debuff'].dur, 2)
                    self.assertEqual(len(dot.inst), 2)
                    self.assertIn('도발', a.eff)

    def test_wave_start_order_and_gauge_switch(self):
        for mode, gauge, expected in [('client', 'reset', 2000), ('keep', 'reset', 0),
                                      ('client', 'keep', 7000)]:
            b, a = self.setup_wave(mode, wave_ally_gauge=gauge)
            a.d.lines = [Line('[웨이브 시작 시] 자신에게 행동 게이지 20%p 증가', '고유 패시브', 'passive'),
                         Line('[웨이브 시작 시] 자신에게 〈새 버프〉 (1턴 / 공격력% +10%)', '고유 패시브', 'passive')]
            a.gauge = 5000
            b.spawn_wave()
            self.assertEqual(a.gauge, expected)
            self.assertEqual(a.eff['새 버프'].dur, 1)

    def test_extra_turn_survives(self):
        b, a = self.setup_wave('client')
        a.extra_turn, a.gauge = True, 10000
        b.spawn_wave()
        self.assertEqual((a.extra_turn, a.gauge), (True, 10000))

    def test_both_teams_wave_start_after_carry(self):
        for mode in ('client', 'keep'):
            with self.subTest(mode=mode):
                b, a = self.setup_wave(mode)
                give(a, '기존 효과', dur=2)
                a.d.lines = [Line('[웨이브 시작 시] 자신에게 〈아군 새 효과〉 (2턴 / 공격력% +10%)',
                                  '고유 패시브', 'passive')]
                b.waves[1][0].lines = [
                    Line('[웨이브 시작 시] 적 전체에게 〈적 새 효과〉 (2턴 / 방어력% -10%)',
                         '고유 패시브', 'passive')]
                events = []
                run_line = b.run_line

                def watch(owner, ln, ctx):
                    events.append((owner.side, a.eff['기존 효과'].dur))
                    return run_line(owner, ln, ctx)

                with patch.object(b, 'run_line', watch):
                    b.spawn_wave()
                self.assertEqual(events, [(0, 1), (1, 1)] if mode == 'client' else [(1, 2), (0, 2)])
                self.assertEqual(a.eff['아군 새 효과'].dur, 2)
                self.assertEqual(a.eff['적 새 효과'].dur, 2)

    def test_standard_wave_path(self):
        old, _ = run_stage('keep')
        new, battles = run_stage('client')
        self.assertGreater(new['outcome']['progress'], 0)
        self.assertGreater(old['outcome']['progress'], 0)
        self.assertGreater(sum(b.rule_hits['wave_carry'] for b in battles), 0)
        self.assertNotEqual(old['outcome'], new['outcome'])


class ShieldTest(unittest.TestCase):
    def setup_shield(self, mode='turn_end'):
        b = battle([unit('a'), unit('b')], [unit('foe', hp=10**9)],
                   mc={'shield_tick': mode}, opts={'coop': False})
        return b, *b.allies

    def shield(self, b, owner, target, phase='스킬 사용 후'):
        effect(b, owner, target, '아군 전체에게 〈보호막〉 (1턴) 보호막 = 자신 생명력×10%', phase)

    def test_outside_turn_absorbs_until_owner_end(self):
        for mode in ('turn_start', 'turn_end'):
            b, a, other = self.setup_shield(mode)
            self.shield(b, other, a)
            hp = a.hp

            def counter(*args, **kw):
                b.apply_damage(b.foes[0], a, 100, 'hit')

            with patch.object(b, 'cast', counter):
                b._act_turn(a)
            self.assertEqual(a.hp, hp if mode == 'turn_end' else hp - 100)
            self.assertNotIn('보호막', a.eff)

    def test_own_turn_self_other_and_refresh(self):
        for other_cast in (False, True):
            for refresh in (False, True):
                b, a, other = self.setup_shield()
                if refresh:
                    self.shield(b, other, a)
                with patch.object(b, 'cast', lambda *args, **kw: self.shield(b, other if other_cast else a, a)):
                    b._act_turn(a)
                self.assertIn('보호막', a.eff)
                self.assertEqual(a.eff['보호막'].dur, 1)
                self.assertEqual(a.eff['보호막'].shield, 2000 if refresh else 1000)
                with patch.object(b, 'cast', return_value=None):
                    b._act_turn(a)
                self.assertNotIn('보호막', a.eff)

    def test_start_events_count_same_turn(self):
        for phase in ('스킬 사용 시작 시', '턴 시작 시', '등장 후', '웨이브 시작 시', '전투 시작 시'):
            b, a, other = self.setup_shield()
            self.shield(b, other, a)
            with patch.object(b, 'cast', lambda *args, **kw: self.shield(b, other, a, phase)):
                b._act_turn(a)
            self.assertNotIn('보호막', a.eff, phase)

    def test_infinite_shield(self):
        b, a, other = self.setup_shield()
        effect(b, other, a, '아군 전체에게 〈보호막〉 (지속 무한) 보호막 = 자신 생명력×10%')
        b._act_turn(a)
        self.assertEqual(a.eff['보호막'].dur, math.inf)

    def test_standard_owner_absorption_path(self):
        # FLOOR 200은 이 편성에서 보유자 턴 흡수 0회. 250/40판은 실제 흡수 경로를 탐.
        # 결과 집계가 같아도 실제 보호막의 턴 시작 유지·턴 끝 차감을 직접 검사한다.
        boundaries = {'start': 0, 'end': 0}
        act, fire = Battle._act_turn, Battle.fire

        def watch_act(b, u, **kw):
            initial = {name: (e, e.dur) for name, e in u.eff.items()
                       if e.shield > 0 and e.clock == 'owner_turn' and math.isfinite(e.dur)}
            ending = []

            def watch_fire(owner, kind, ctx):
                if owner is u and kind == 'own_ts':
                    for name, (e, dur) in initial.items():
                        self.assertIs(u.eff.get(name), e)
                        self.assertEqual(e.dur, dur)  # 시전 시작 전에 미리 차감하면 실패
                        boundaries['start'] += 1
                result = fire(b, owner, kind, ctx)
                if owner is u and kind == 'own_te':
                    ending.extend((e, e.dur) for e in u.eff.values()
                                  if e.shield > 0 and e.clock == 'owner_turn' and math.isfinite(e.dur)
                                  and not e.fresh and not e.skip_tick and e.inst is None)
                return result

            with patch.object(b, 'fire', watch_fire):
                result = act(b, u, **kw)
            for e, dur in ending:
                self.assertEqual(e.dur, dur - 1)  # 종료 차감을 지우면 실패
                boundaries['end'] += 1
            return result

        with patch.object(Battle, '_act_turn', watch_act):
            result, battles = run_stage('keep', 40, shield_tick='turn_end')
        self.assertGreater(result['outcome']['progress'], 0)
        self.assertGreater(sum(b.rule_hits['shield_owner_absorb'] for b in battles), 0)
        self.assertGreater(boundaries['start'], 0)
        self.assertGreater(boundaries['end'], 0)


class ReviveTest(unittest.TestCase):
    def setup_domain(self, mode='client', clock='global'):
        b = battle([unit('a'), unit('b', role='서포터')], [unit('foe', hp=10**9)],
                   mc={'break_domain_revive': mode, 'break_skill_domain_clock': clock}, break_skill=CUBE)
        b.break_points = 3
        b._use_break_skill(b.allies[0])
        return b, *b.allies

    def revive(self, b, owner, target):
        effect(b, owner, target, '스킬 대상에게 부활(생명력 50%)')

    def test_remaining_lifetime_role_props_and_expiry(self):
        for mode in ('none', 'client'):
            for clock in ('global', 'legacy'):
                b, a, other = self.setup_domain(mode, clock)
                b.kill(other, b.foes[0])
                b._tick_break_domain(b.break_domain_clock)
                self.revive(b, a, other)
                self.assertFalse(other.dead)
                self.assertNotIn('오메가 프로토콜', other.eff)
                if mode == 'none':
                    self.assertNotIn(DOMAIN, other.eff)
                else:
                    self.assertIn(DOMAIN, other.eff)
                    restored = other.eff[DOMAIN]
                    self.assertEqual((restored.dur, restored.clock), (a.eff[DOMAIN].dur, a.eff[DOMAIN].clock))
                    self.assertEqual(restored.props['속도%'], b.mc['break_skill_speed_pct'] + b.mc['break_skill_role_speed_pct'])
                    self.assertEqual(restored.fixed, b.mc['break_skill_fixed'])
                    self.assertEqual(b.rule_hits['break_domain_revive'], 1)
                b.kill(other, b.foes[0])
                for _ in range(b.break_domain_turns):
                    b._tick_break_domain(b.break_domain_clock)
                self.revive(b, a, other)
                self.assertNotIn(DOMAIN, other.eff)

    def test_team_lifetime_without_surviving_effect(self):
        b, a, other = self.setup_domain()
        b.kill(other, b.foes[0])
        a.eff.pop(DOMAIN)
        b._tick_break_domain(b.break_domain_clock)
        self.revive(b, a, other)
        self.assertIn(DOMAIN, other.eff)
        self.assertEqual(other.eff[DOMAIN].dur, b.break_domain_turns - 1)

    def test_revive_before_first_domain(self):
        b = battle([unit('a'), unit('b')], [unit('foe')], break_skill=CUBE)
        a, other = b.allies
        b.kill(other, b.foes[0])
        self.revive(b, a, other)
        self.assertFalse(other.dead)
        self.assertNotIn(DOMAIN, other.eff)

    def test_enemy_revive_does_not_receive_ally_domain(self):
        b, a, other = self.setup_domain()
        foe = b.foes[0]
        b.kill(foe, a)
        self.revive(b, foe, foe)
        self.assertFalse(foe.dead)
        self.assertNotIn(DOMAIN, foe.eff)


if __name__ == '__main__':
    unittest.main()
