# -*- coding: utf-8 -*-
"""브레이크 스킬: python -X utf8 tests/break_skill_test.py (운영 데이터·골든 변경 없음)."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from p5_test import battle, give, hit, unit
from battlesim.api import simulate
from battlesim.mc import Ctx
from battlesim.rules import MC_OPTS
from battlesim.starsavior.parser import Line
from battlesim.web import _opts
from battlesim import web
from unittest.mock import patch

CUBE = {'name': '큐브 과부하', 'level': 5}
OMEGA, MATRIX = '오메가 프로토콜', '치트 매트릭스'


# 공식 단위 시험은 옛 계수(레벨 가산 없음·DamageScale 제외)로 고정하고, 레벨·배율은 BreakLevelScaleTest 가 따로 본다
LEGACY_SCALE = dict(break_skill_level='off', break_skill_scale='off')


def setup(bs=CUBE, mc=None, roles=('스트라이커',), **kw):
    allies = [unit('a%d' % i, role=role) for i, role in enumerate(roles)]
    foe = unit('boss', hp=10 ** 9, sa=1, skills=[dict(slot='기본기', dm=0)])
    foe.boss = True
    return battle(allies, [foe], break_skill=bs, mc=dict(LEGACY_SCALE, **(mc or {})), timeline=True, **kw)


def legacy_setup(bs=CUBE, mc=None, **kw):
    return setup(bs, mc=dict(break_skill_domain_clock='legacy', **(mc or {})), **kw)


class BreakLevelScaleTest(unittest.TestCase):
    """레벨 가산(mc.break_skill_level)·DamageScale(mc.break_skill_scale) — NKM 17742~17817, ORBITAL_LEVEL_GROUP"""
    def dmg(self, name, level, **mc):
        b = setup({'name': name, 'level': level}, mc=mc)
        b.break_points = 3
        b.act(b.allies[0])
        return b.break_skill_dmg

    def test_level_adds_to_ratio(self):
        base = self.dmg('특이점 관측', 1, break_skill_level='data')
        lv10 = self.dmg('특이점 관측', 10, break_skill_level='data')
        self.assertAlmostEqual(lv10 / base, 0.8 / 0.7, delta=0.01)         # 70% -> 80%(곱이 아니라 가산)
        self.assertEqual(self.dmg('특이점 관측', 10), base)                  # off: 레벨 무관

    def test_damage_scale(self):
        off = self.dmg('스타피어서', 1)
        game = self.dmg('스타피어서', 1, break_skill_scale='game')
        self.assertAlmostEqual(game / off, 1.85, delta=0.02)          # 정수 내림 오차

    def test_bad_level_is_one(self):
        b = setup({'name': '차원 강습', 'level': 99}, mc=dict(break_skill_level='data'))
        self.assertEqual(b._break_level_up(), (0.0, 0.0))
        self.assertEqual(sum(v for k, v in b.unsup.items() if k.startswith('break_skill: 레벨 범위 밖')), 1)

    def test_cube_heal_level(self):
        b = setup(dict(CUBE, level=10), mc=dict(break_skill_level='data'))
        self.assertEqual(b._break_level_up(), (0.0, 0.02))                  # 회복 계수 2% -> 4%


class BreakSkillLegacyTest(unittest.TestCase):
    def test_last_enemy_break_kill_before_dot(self):
        for name in ('특이점 관측', '스타피어서', '차원 강습', '행성 정화'):
            with self.subTest(name=name):
                b = legacy_setup({'name': name})
                a, f = b.allies[0], b.foes[0]
                a.hp, a.gauge, f.hp = 1, 10000, 1
                bleed = give(a, '출혈', src=f, harmful=True)
                bleed.dot, bleed.inst = ('atk', .3), [[f, 3]]
                b.break_points = 3
                b.run()
                self.assertEqual(b.result, 'clear')
                self.assertEqual((a.hp, a.actions, a.gauge), (1, 0, 10000))
                self.assertFalse(a.cast_count)
                self.assertEqual(bleed.inst, [[f, 3]])

    def test_break_kill_wave_transition_preserves_ultimate(self):
        b = battle([unit('ally', skills=[dict(slot='궁극기', dm=100, cd=5)])],
                   [unit('first', hp=1)], break_skill={'name': '차원 강습'},
                   opts={'nova_policy': 'manual'}, timeline=True, max_turns=.1)
        b.waves.append([unit('second', hp=10 ** 9)])
        a = b.allies[0]
        a.gauge, a.extra_turn, b.break_points = 10000, True, 3
        with patch.object(b, 'spawn_wave', wraps=b.spawn_wave) as spawn:
            b.act(a)
            # 일반 공격 종료 때처럼 웨이브 생성은 run 루프가 담당한다.
            spawn.assert_not_called()
        self.assertEqual((a.gauge, a.extra_turn, a.actions), (10000, True, 0))
        self.assertEqual((a.cd['궁극기'], b.team_nova), (0, 4))
        self.assertFalse(a.cast_count)
        b.run()
        casts = [e for e in b.timeline if e.get('actor') == a.name]
        self.assertEqual(len(casts), 1)
        self.assertEqual((casts[0]['skill'], casts[0]['targets'], casts[0]['nb']),
                         ('궁극기', ['second'], True))
        self.assertEqual((a.actions, a.gauge, a.cd['궁극기']), (1, 0, 5))
        self.assertGreater(b.foes[0].taken, 0)

    def test_damage_skills_and_domains(self):
        for name, ratio, domain, props in (
            ('특이점 관측', .7, '별빛 지평선', {'atkp': .2, 'defp': .2}),
            ('스타피어서', .5, '전략 사령부', {'cr': .2, 'cd': .2}),
            ('차원 강습', .5, 'CRF 증폭', {'atkp': .15, 'tough': 1}),
        ):
            with self.subTest(name=name):
                b = legacy_setup({'name': name}, roles=('스트라이커', '레인저', '서포터'))
                a, f = b.allies[0], b.foes[0]
                for u in b.allies:
                    u.d.skills.clear()
                b.break_points = 3
                b.act(a)
                expected = int(3000 * ratio / 4 * .75)
                self.assertEqual(f.taken, expected)
                self.assertEqual(b.break_skill_dmg, expected)
                self.assertEqual(sum(u.dmg for u in b.allies), 0)
                self.assertEqual(f.sa, f.sa_max)
                self.assertEqual(b.team_nova, 0 if name == '스타피어서' else 4)
                for key, val in props.items():
                    self.assertAlmostEqual(a.mods()[key], val)
                if name == '스타피어서':
                    self.assertAlmostEqual(b.allies[2].mods()['cr'], .1)
                self.assertEqual(a.eff[domain].dur, 4)
                for _ in range(4):
                    b.act(a)
                self.assertTrue(all(not u.has(domain) for u in b.allies))
                for key in props:
                    self.assertEqual(a.mods()[key], 0)

    def test_break_gauge_overflow_actor_and_dead(self):
        b = legacy_setup({'name': '스타피어서'}, roles=('스트라이커',) * 4)
        for u, gauge in zip(b.allies, (10000, 9500, 2500, 0)):
            u.gauge = gauge
            u.d.skills.clear()
        b.kill(b.allies[3], b.foes[0])
        b.break_points = 3
        b.act(b.allies[0])
        self.assertEqual([u.gauge for u in b.allies], [0, 11500, 4500, 0])
        self.assertFalse(b.allies[3].eff)

    def test_nova_pool_and_live_atk_only(self):
        for name in ('특이점 관측', '차원 강습'):
            for pool in ('unit', 'team'):
                with self.subTest(name=name, pool=pool):
                    b = legacy_setup({'name': name}, roles=('스트라이커',) * 3, opts={'nova_pool': pool})
                    for u in b.allies:
                        u.d.skills.clear()
                    b.kill(b.allies[2], b.foes[0])
                    give(b.allies[1], '공격 강화', {'공격력%': 100})
                    b.break_points = 3
                    b.act(b.allies[0])
                    self.assertEqual([u.nova for u in b.allies], [4, 4, 0] if pool == 'unit' else [0, 0, 0])
                    self.assertEqual(b.team_nova, 4 if pool == 'team' else 0)
                    self.assertEqual(b.foes[0].taken, int(3000 * (.7 if name == '특이점 관측' else .5) / 4 * .75))

    def test_break_formula_and_no_hit_reactions(self):
        b = legacy_setup({'name': '특이점 관측'}, pen=(.8, 1))
        a, f = b.allies[0], b.foes[0]
        f.broken = True
        give(f, '피해 감소', {'받는 피해 감소': 40, '전체 대상 피해 감소': 30})
        give(a, '개인 공격 보정', {'피해 증가': 100, '치명타 확률': 100, '치명타 피해': 200, '방어 관통': 100})
        a.d.skills.clear()
        b.break_points = 3
        # 반응·협공·일반 피해/강인도 경로를 호출하면 즉시 실패.
        with patch.object(b, 'deal', side_effect=AssertionError('deal')), \
             patch.object(b, 'strike', side_effect=AssertionError('strike')), \
             patch.object(b, 'reaction_skills', side_effect=AssertionError('reaction')):
            b.act(a)
        self.assertEqual(f.taken, int(1000 * .7 / 4 * .75 * .5 * .8))
        self.assertEqual(b.break_skill_dmg, f.taken)
        self.assertEqual(b._break_dmg(f, 1000), 300)
        give(f, '피해 감소', {'받는 피해 감소': 20})
        self.assertEqual(b._break_dmg(f, 1000), 570)  # (20%-15%) 감소

    def test_break_damage_shield_kill_and_no_attribution(self):
        b = legacy_setup({'name': '차원 강습'}, roles=('스트라이커',) * 4)
        a, f = b.allies[0], b.foes[0]
        f.hp = 10
        e = give(f, '보호막')
        e.shield = 30
        a.d.skills.clear()
        b.break_points = 3
        b.act(a)
        self.assertTrue(f.dead)
        self.assertEqual(b.break_skill_dmg, 40)
        self.assertEqual(sum(u.dmg for u in b.allies), 0)

    def test_break_aoe_damage_limit_and_nova_policy(self):
        b = battle([unit()], [unit('f0'), unit('f1')], break_skill={'name': '특이점 관측'}, mc=LEGACY_SCALE)
        b.foes[1].hp = 10
        give(b.foes[1], '불사')
        b.allies[0].d.skills.clear()
        b.break_points = 3
        b.act(b.allies[0])
        self.assertEqual([v.taken for v in b.foes], [131, 9])
        self.assertEqual(b.break_skill_dmg, 140)
        self.assertEqual(b.foes[1].hp, 1)
        for policy in ('auto', 'manual'):
            b = legacy_setup({'name': '차원 강습'}, opts={'nova_policy': policy})
            b.break_points = 3
            b.act(b.allies[0])
            bursts = [e for e in b.timeline if e.get('nb')]
            self.assertEqual(len(bursts), int(policy == 'manual'))
            self.assertEqual(b.team_nova, 4 if policy == 'auto' else 0)

    def test_damage_api_averages_and_web_summaries(self):
        party = {'units': ['fei', 'professor-m', 'wedding-carmen', 'white-pearl-luna']}
        enc = {'waves': [[{'hp': 1000000, 'atk': 100, 'boss': True, 'sa': 1}]], 'max_turns': 5}
        opt = {'n_runs': 3, 'seed': 8, 'rules_override': {'basic_tough': 1}}
        for name in ('특이점 관측', '스타피어서', '차원 강습', '행성 정화'):
            with self.subTest(name=name):
                opts = dict(opt, break_skill={'name': name, 'level': 5})
                r = simulate(party, enc, opts)
                self.assertTrue(r['break_skill']['supported'])
                self.assertGreater(r['break_skill']['dmg'], 0)
                singles = [simulate(party, enc, dict(opts, n_runs=1, run_offset=i)) for i in range(3)]
                for key in ('uses', 'dmg', 'points_gained'):
                    self.assertEqual(r['break_skill'][key], round(sum(s['break_skill'][key] for s in singles) / 3, 3))
                lv1 = simulate(party, enc, dict(opts, break_skill={'name': name, 'level': 1}))
                self.assertGreater(r['break_skill']['dmg'], lv1['break_skill']['dmg'])   # Lv5 = 계수 +4%p(mc.break_skill_level)
                off = {'rules_override': dict(opt['rules_override'], break_skill_level='off')}
                o5 = simulate(party, enc, dict(opts, **off))
                o1 = simulate(party, enc, dict(opts, break_skill={'name': name, 'level': 1}, **off))
                self.assertEqual(o5['per_unit'], o1['per_unit'])       # 옛 동작: 모든 레벨 같은 계수
                self.assertEqual(o5['break_skill'], o1['break_skill'])
        # 웹 진입점의 auto/manual이 실제 엔진 결과의 네 필드를 그대로 돌려준다.
        stage = 'op/NOA 상업지구/SECTOR 1-3'
        for name in ('특이점 관측', '스타피어서', '차원 강습', '큐브 과부하', '행성 정화', None):
            extra = {'break_skill': {'name': name} if name else None, 'rules_override': {'basic_tough': 1}}
            for runner in (web.run_auto, web.run_manual):
                got = json.loads(runner(stage, party, 2, 8, extra))
                pol = got.get('pol')
                expected = simulate(party, {'stage': stage}, _opts(extra, pol, n_runs=2, seed=8))['break_skill']
                self.assertEqual(got['bs'], {k: expected[k] for k in ('name', 'uses', 'dmg', 'supported')})
                self.assertEqual(got['bs']['supported'], name is not None)

    def test_default_disabled(self):
        b = legacy_setup(None)
        a, f = b.allies[0], b.foes[0]
        hit(b, a, f, ab=1)
        b.act(a)
        self.assertEqual((b.break_points, b.break_points_gained, b.break_skill_uses), (0, 0, 0))
        self.assertFalse(any('bskill' in e for e in b.timeline))
        self.assertFalse(a.has(OMEGA) or a.has(MATRIX))

    def test_boss_next_ally_heal_and_durations(self):
        b = legacy_setup(roles=('ストライ커', '디펜더', '서포터', '캐스터'))
        a, f = b.allies[0], b.foes[0]
        for u in b.allies:
            u.hp -= 2000
        b.allies[-1].hp = b.allies[-1].maxhp - 10
        hit(b, a, f, ab=1)
        self.assertEqual((b.break_points, b.break_skill_uses), (3, 0))
        hit(b, a, f, ab=1)  # 이미 격파: 중복 적립 없음
        self.assertEqual(b.break_points_gained, 3)
        b.act(f)  # 적 턴에는 발동하지 않음
        self.assertEqual(b.break_skill_uses, 0)
        a.d.skills.clear()  # 직후 일반 공격의 재격파와 발동 자체를 분리
        b.act(a)
        self.assertEqual((b.break_points, b.break_skill_cd, b.break_skill_uses), (0, 8, 1))
        self.assertEqual([u.hp for u in b.allies], [8800, 8800, 8800, 10000])
        self.assertEqual([u.eff[OMEGA].dur for u in b.allies], [1, 2, 2, 2])
        self.assertEqual([u.eff[MATRIX].dur for u in b.allies], [4] * 4)
        for u, speed in zip(b.allies, (0.1, 0.2, 0.2, 0.1)):
            self.assertAlmostEqual(u.mods()['atkp'], 0.15)
            self.assertAlmostEqual(u.mods()['eh'], 0.15)
            self.assertAlmostEqual(u.mods()['spdp'], speed)
            self.assertTrue(u.eff[OMEGA].fixed and u.eff[MATRIX].fixed)
        b.act(a)
        self.assertFalse(a.has(OMEGA))
        self.assertTrue(b.allies[1].has(OMEGA))  # 개인 지속은 남의 턴에 줄지 않음
        self.assertEqual(a.eff[MATRIX].dur, 3)
        for _ in range(3):
            b.act(b.allies[1])
        self.assertTrue(all(not u.has(MATRIX) for u in b.allies))
        self.assertEqual(a.mods()['spdp'], 0)
        event = next(e for e in b.timeline if 'bskill' in e)
        self.assertEqual(event, {'bskill': '큐브 과부하', 'turn': 0.0})

    def test_cooldown_and_point_cap(self):
        b = legacy_setup()
        a, f = b.allies[0], b.foes[0]
        hit(b, a, f, ab=1)
        b.act(a)
        for _ in range(2):
            b.act(f)
            hit(b, a, f, ab=1)
        self.assertEqual((b.break_points, b.break_points_gained), (3, 6))
        self.assertEqual(b.break_skill_cd, 8)  # 적 턴·타격은 공용 쿨을 차감하지 않음
        for left in range(7, 0, -1):
            b.act(a)
            self.assertEqual(b.break_skill_cd, left)
            self.assertEqual(b.break_skill_uses, 1)
        b.act(a)
        self.assertEqual((b.break_skill_uses, b.break_skill_cd, b.break_points), (2, 8, 0))

    def test_three_normal_breaks_and_ally_excluded(self):
        b = battle([unit(sa=1)], [unit('f%d' % i, hp=10 ** 9, sa=1) for i in range(3)], break_skill=CUBE)
        a = b.allies[0]
        hit(b, b.foes[0], a, ab=1)
        self.assertEqual(b.break_points, 0)
        for i, f in enumerate(b.foes):
            hit(b, a, f, ab=1)
            self.assertEqual(b.break_points, i + 1)
            if i < 2:
                b.act(a)
                self.assertEqual(b.break_skill_uses, 0)
        b.act(a)
        self.assertEqual((b.break_points_gained, b.break_skill_uses), (3, 1))

    def test_heal_reduction_dead_and_dispel(self):
        b = legacy_setup(roles=('ストライ커',) * 4)
        a, f = b.allies[0], b.foes[0]
        for u in b.allies:
            u.hp = 1000
        give(a, '회복 불가', {'받는 회복량': -100}, harmful=True)
        give(b.allies[1], '회복 감소', {'받는 회복량': -50}, harmful=True)
        b.kill(b.allies[3], f)
        hit(b, a, f, ab=1)
        b.act(a)
        self.assertEqual([u.hp for u in b.allies], [1000, 1400, 1800, 0])
        self.assertFalse(b.allies[3].eff)
        self.assertEqual(sum(u.healed for u in b.allies), 0)  # 파티 스킬 힐을 개인 힐로 오귀속하지 않음
        give(a, '일반 강화', {'공격력%': 10})
        ctx = Ctx(f, f, f.d.skills['기본기'])
        ctx.targets, ctx.target = [a], a
        b.run_line(f, Line('[스킬 사용 후] 스킬 대상에게 〈해제〉 (강화효과 해제)', '기본기', 'active'), ctx)
        self.assertFalse(a.has('일반 강화'))
        self.assertTrue(a.has(OMEGA) and a.has(MATRIX))

    def test_round_boundaries_and_speed_expiry(self):
        b = legacy_setup(mc={'break_skill_cd_unit': 'round'}, max_turns=8.7)
        a, f = b.allies[0], b.foes[0]
        hit(b, a, f, ab=1)
        b.act(a)  # 시각 0 에 발동
        b.act(f)
        hit(b, a, f, ab=1)  # 쿨 중 충전
        a.d.skills['기본기'].is_attack = False
        b.run()
        uses = [e['turn'] for e in b.timeline if 'bskill' in e]
        self.assertEqual(uses, [0.0, 8.6])  # 8라운드 경과 후 다음 아군 턴
        turns = [e['turn'] for e in b.timeline if e.get('actor') == a.name]
        self.assertIn(4.6, turns)  # 4.0 에 영역 만료: 남은 게이지는 속도 100 으로 진행
        self.assertEqual((b.break_skill_cd, a.eff[MATRIX].dur), (8, 4))

    def test_no_extra_cast_nova_or_coop(self):
        b = legacy_setup(roles=('스트라이커', '서포터'))
        a, f = b.allies[0], b.foes[0]
        hit(b, a, f, ab=1)
        a.d.skills.clear()
        b.team_nova = 3
        give(b.allies[1], '협공', {'협공 확률': 100})
        b.act(a)
        self.assertEqual(b.break_skill_uses, 1)
        self.assertEqual(sum(u.actions for u in b.allies), 1)
        self.assertEqual(sum(sum(u.cast_count.values()) for u in b.allies + b.foes), 0)
        self.assertEqual(b.team_nova, 3)

    def test_wave_carry(self):
        b = legacy_setup()
        a, f = b.allies[0], b.foes[0]
        hit(b, a, f, ab=1)
        b.waves.append(b.waves[0])
        b.spawn_wave()
        self.assertEqual(b.break_points, 3)
        b.act(a)
        hit(b, a, b.foes[0], ab=1)
        b.waves.append(b.waves[0])
        b.spawn_wave()
        self.assertEqual((b.break_points, b.break_skill_cd, a.eff[MATRIX].dur), (3, 8, 4))

    def test_unsupported_names(self):
        for name in ('알 수 없는 스킬',):
            with self.subTest(name=name):
                b = legacy_setup({'name': name, 'level': 5})
                hit(b, b.allies[0], b.foes[0], ab=1)
                b.act(b.allies[0])
                self.assertEqual((b.break_points, b.break_skill_uses), (0, 0))
                self.assertEqual(b.unsup['break_skill:' + name], 1)

    def test_api_averages_levels_and_web_options(self):
        party = ['fei', 'professor-m', 'wedding-carmen', 'white-pearl-luna']
        enc = {'waves': [[{'hp': 1000000, 'atk': 100, 'boss': True, 'sa': 1}]], 'max_turns': 5}
        opt = {'n_runs': 3, 'seed': 8, 'timeline': True, 'rules_override': {'basic_tough': 1}}
        r = simulate(party, enc, dict(opt, break_skill=CUBE))
        singles = [simulate(party, enc, dict(opt, break_skill=CUBE, n_runs=1, run_offset=i)) for i in range(3)]
        for key in ('uses', 'points_gained'):
            self.assertGreater(r['break_skill'][key], 0)
            self.assertEqual(r['break_skill'][key], round(sum(s['break_skill'][key] for s in singles) / 3, 3))
        self.assertEqual(r['timeline'], singles[0]['timeline'])
        off = dict(opt, rules_override=dict(opt['rules_override'], break_skill_level='off'))
        lv1 = simulate(party, enc, dict(off, break_skill=dict(CUBE, level=1)))
        self.assertEqual(simulate(party, enc, dict(off, break_skill=CUBE))['per_unit'], lv1['per_unit'])   # 옛 동작: 레벨 무관
        unsupported = simulate(party, enc, dict(opt, break_skill={'name': '알 수 없는 스킬'}))
        self.assertEqual(unsupported['unsupported']['runtime']['break_skill:알 수 없는 스킬'], 3)
        self.assertEqual(unsupported['break_skill']['uses'], 0)
        default = simulate(party, enc, opt)
        self.assertEqual(default['break_skill'], dict(name=None, uses=0, points_gained=0, dmg=0, supported=False))
        explicit_none = simulate(party, enc, dict(opt, break_skill=None))
        for result in (default, explicit_none):
            result.pop('runtime_ms_per_run')
        self.assertEqual(default, explicit_none)
        for policy in (None, ('boss_first', 'any_attack')):
            self.assertEqual(_opts(json.dumps({'break_skill': CUBE}), policy)['break_skill'], CUBE)


class BreakSkillGlobalTest(unittest.TestCase):
    """실제 run/act 경계로 전역 시계·조기 반환·시전 지급을 검증한다."""

    def prepared(self, name='큐브 과부하', turns=6, mc=None, **kw):
        b = setup({'name': name}, turn_limit=turns,
                  mc=dict(enemy_leader='none', **(mc or {})), **kw)
        b.break_points = 3
        b.allies[0].gauge = b.foes[0].gauge = 10000
        for u in b.allies + b.foes:
            u.d.skills.clear()
        return b

    def observe(self, b, hook=None):
        rows = []
        act = b.act
        domain = b.break_skill_rule['domain']

        def record(u):
            act(u)
            a = b.allies[0]
            rows.append(dict(actor=u, turn=b.global_turns, time=b.t,
                             left=a.eff[domain].dur if a.has(domain) else 0,
                             cd=b.break_skill_cd, nova=b.nova_of(a), speed=a.spd()))
            if hook:
                hook(u)

        with patch.object(b, 'act', side_effect=record):
            b.run()
        return rows

    def test_five_actions_all_domains_and_cooldown_clocks(self):
        for name in ('큐브 과부하', '특이점 관측', '스타피어서', '차원 강습', '행성 정화'):
            for cd_unit in ('ally_turn', 'round'):
                with self.subTest(name=name, cd_unit=cd_unit):
                    b = self.prepared(name, mc={'break_skill_cd_unit': cd_unit})
                    unrelated = give(b.allies[0], '별도 효과', dur=20)
                    unrelated.clock = 'global'
                    rows = self.observe(b)
                    self.assertEqual([r['left'] for r in rows], [5, 4, 3, 2, 1, 0])
                    self.assertEqual([r['actor'].side for r in rows], [0, 1, 0, 1, 0, 1])
                    self.assertEqual([r['cd'] for r in rows],
                                     [8, 8, 7, 7, 6, 6] if cd_unit == 'ally_turn' else
                                     ([8, 8, 8, 7, 7, 6] if name == '큐브 과부하' else [8, 8, 7, 7, 6, 6]))
                    self.assertEqual(unrelated.dur, 20)  # 영역 외 효과는 차감하지 않음
                    self.assertFalse(b.allies[0].has(b.break_skill_rule['domain']))

    def test_early_return_break_kill(self):
        b = self.prepared('행성 정화', roles=('스트라이커', '서포터'))
        b.foes[0].hp = 1
        rows = self.observe(b)
        self.assertEqual((b.result, b.global_turns, len(rows)), ('clear', 1, 1))
        self.assertEqual([u.eff['마녀의 은총'].dur for u in b.allies], [4, 4])
        self.assertEqual((b.allies[0].actions, b.team_nova, b.break_skill_cd), (0, 0, 8))

    def test_early_return_dot_death_and_disabled_action(self):
        for death in (True, False):
            with self.subTest(death=death):
                b = self.prepared('행성 정화', turns=1, roles=('스트라이커', '서포터'))
                a, other = b.allies
                if death:
                    a.hp = 1
                    bleed = give(a, '출혈', src=b.foes[0], harmful=True)
                    bleed.dot, bleed.inst = ('atk', .3), [[b.foes[0], 3]]
                else:
                    give(a, '기절', harmful=True)
                self.observe(b)
                self.assertEqual(other.eff['마녀의 은총'].dur, 4)
                self.assertEqual(a.dead, death)
                self.assertEqual((b.global_turns, b.team_nova), (1, 0))
                self.assertFalse(a.cast_count)

    def test_wave_transition_keeps_domain_and_cooldown(self):
        b = self.prepared('행성 정화', turns=2)
        b.foes[0].hp = 1
        b.waves.append([unit('second', hp=10 ** 9)])
        a = b.allies[0]
        spawn, carried = b.spawn_wave, []

        def next_wave():
            before = (a.eff['마녀의 은총'].dur, b.break_skill_cd, b.break_points)
            spawn()
            carried.append((before, (a.eff['마녀의 은총'].dur, b.break_skill_cd, b.break_points)))

        with patch.object(b, 'spawn_wave', side_effect=next_wave):
            rows = self.observe(b)
        self.assertEqual(carried, [((4, 8, 0), (4, 8, 0))])
        self.assertEqual([r['left'] for r in rows], [5, 4])
        self.assertEqual((b.wave_i, a.eff['마녀의 은총'].dur), (1, 3))

    def test_extra_turn_and_speed_expiry_on_enemy_action(self):
        b = self.prepared()
        a = b.allies[0]

        def extra(u):
            if b.global_turns == 1:
                u.extra_turn, u.gauge = True, 10000

        rows = self.observe(b, extra)
        self.assertEqual([r['actor'].side for r in rows], [0, 0, 1, 0, 1, 0])
        self.assertEqual([r['left'] for r in rows], [5, 4, 3, 2, 1, 0])
        self.assertAlmostEqual(rows[4]['speed'], 110)
        self.assertEqual(rows[5]['speed'], 100)
        self.assertAlmostEqual(rows[5]['time'], 100 + (10000 - (100 - 10000 / 110) * 110) / 100)
        self.assertFalse(a.has(MATRIX))

    def test_planet_damage_and_toughness(self):
        b = setup({'name': '행성 정화'}, turn_limit=1,
                  mc={'toughness_elem': 'db'}, opts={'coop': False})
        a, f = b.allies[0], b.foes[0]
        a.gauge, b.break_points = 10000, 3
        f.sa = f.sa_max = 100
        a.d.skills['기본기'].ab = 1
        b.run()
        self.assertEqual(b.break_skill_dmg, int(1000 * 1.0 / 4 * .75))
        self.assertEqual(f.sa, 98)  # 기본 강인도 1 + 영역 1; 브레이크 피해 자체는 0
        self.assertEqual((b.team_nova, a.eff['마녀의 은총'].dur), (1, 4))

    def test_planet_nova_basic_special_ultimate_and_last_action(self):
        for pool in ('team', 'unit'):
            for slot in ('기본기', '특수기', '궁극기'):
                with self.subTest(pool=pool, slot=slot):
                    b = setup({'name': '행성 정화'}, turn_limit=6,
                              opts={'nova_pool': pool, 'coop': False}, mc={'toughness': 'off'})
                    a = b.allies[0]
                    sk = a.d.skills.pop('기본기')
                    sk.slot, sk.nv = slot, 2
                    a.d.skills[slot] = sk
                    a.cd[slot] = 0
                    b.break_points = 3
                    # 같은 유닛 6행동: 마지막 영역 행동까지 +1, 만료 후에는 원래 스킬 노바만.
                    with patch.object(b, 'pick_next', return_value=(a, 0)):
                        rows = self.observe(b)
                    self.assertEqual([r['nova'] for r in rows], [3, 6, 9, 12, 15, 17])
                    self.assertEqual(b.team_nova, 17 if pool == 'team' else 0)
                    self.assertEqual(a.nova, 17 if pool == 'unit' else 0)

    def test_planet_nova_excludes_extra_casts_and_missing_domain(self):
        for case in ('reaction', 'coop', 'extra', 'missing', 'dead', 'stun'):
            with self.subTest(case=case):
                b = setup({'name': '행성 정화'}, turn_limit=1, opts={'coop': False})
                a = b.allies[0]
                b.break_points, a.gauge = 3, 10000
                original = b.cast

                def cast(u, sk, **kw):
                    if case == 'missing':
                        u.eff.pop('마녀의 은총', None)
                        b.dirty(u)
                    elif case == 'dead':
                        # 실제 시전은 시작했지만 시전 종료 이벤트에서 사망하는 경우.
                        with patch.object(b, 'fire_side', side_effect=lambda *_: b.kill(u, b.foes[0])):
                            return original(u, sk, **kw)
                    elif case == 'stun':
                        give(u, '기절', harmful=True)
                    else:
                        kw.update(extra=True, via=case)
                    return original(u, sk, **kw)

                with patch.object(b, 'cast', side_effect=cast):
                    b.run()
                self.assertEqual(b.team_nova, 0)

    def test_duration_override_and_api_legacy(self):
        for name in ('큐브 과부하', '행성 정화'):
            for clock in ('global', 'legacy'):
                for turns in (None, 2, 5):
                    with self.subTest(name=name, clock=clock, turns=turns):
                        mc = {'break_skill_domain_clock': clock}
                        if turns is not None:
                            if name == '큐브 과부하':
                                mc['break_skill_domain_turns'] = turns
                            else:
                                mc['break_skills'] = {name: dict(MC_OPTS['break_skills'][name], domain_turns=turns)}
                        b = self.prepared(name, turns=1, mc=mc)
                        self.observe(b)
                        expected = turns if turns is not None else (5 if clock == 'global' else 4)
                        self.assertEqual(b.allies[0].eff[b.break_skill_rule['domain']].dur,
                                         expected - (clock == 'global'))
                        # API의 기본값 병합이 명시 override 여부를 잃지 않는지 확인.
                        from battlesim import api
                        constructor = api.Battle
                        made = []

                        def capture(*args, **kw):
                            result = constructor(*args, **kw)
                            made.append(result)
                            return result

                        with patch.object(api, 'Battle', side_effect=capture):
                            simulate(['fei'], {'waves': [[{'hp': 10 ** 9}]], 'max_turns': .01},
                                     {'n_runs': 1, 'break_skill': {'name': name}, 'rules_override': mc})
                        self.assertEqual(made[0].break_domain_turns, expected)

    def test_invalid_clock(self):
        with self.assertRaisesRegex(ValueError, 'break_skill_domain_clock'):
            setup(mc={'break_skill_domain_clock': 'unknown'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
