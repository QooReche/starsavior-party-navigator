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
from battlesim.starsavior.parser import Line
from battlesim.web import _opts

CUBE = {'name': '큐브 과부하', 'level': 5}
OMEGA, MATRIX = '오메가 프로토콜', '치트 매트릭스'


def setup(bs=CUBE, mc=None, roles=('스트라이커',), **kw):
    allies = [unit('a%d' % i, role=role) for i, role in enumerate(roles)]
    foe = unit('boss', hp=10 ** 9, sa=1, skills=[dict(slot='기본기', dm=0)])
    foe.boss = True
    return battle(allies, [foe], break_skill=bs, mc=mc, timeline=True, **kw)


class BreakSkillTest(unittest.TestCase):
    def test_default_disabled(self):
        b = setup(None)
        a, f = b.allies[0], b.foes[0]
        hit(b, a, f, ab=1)
        b.act(a)
        self.assertEqual((b.break_points, b.break_points_gained, b.break_skill_uses), (0, 0, 0))
        self.assertFalse(any('bskill' in e for e in b.timeline))
        self.assertFalse(a.has(OMEGA) or a.has(MATRIX))

    def test_boss_next_ally_heal_and_durations(self):
        b = setup(roles=('ストライ커', '디펜더', '서포터', '캐스터'))
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
        b = setup()
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
        b = setup(roles=('ストライ커',) * 4)
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
        b = setup(mc={'break_skill_cd_unit': 'round'}, max_turns=8.7)
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
        b = setup(roles=('스트라이커', '서포터'))
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
        b = setup()
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
        for name in ('특이점 관측', '스타피어서', '행성 정화', '차원 강습', '알 수 없는 스킬'):
            with self.subTest(name=name):
                b = setup({'name': name, 'level': 5})
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
        lv1 = simulate(party, enc, dict(opt, break_skill=dict(CUBE, level=1)))
        self.assertEqual(r['per_unit'], lv1['per_unit'])
        self.assertEqual(r['timeline'], lv1['timeline'])
        unsupported = simulate(party, enc, dict(opt, break_skill={'name': '스타피어서'}))
        self.assertEqual(unsupported['unsupported']['runtime']['break_skill:스타피어서'], 3)
        self.assertEqual(unsupported['break_skill']['uses'], 0)
        default = simulate(party, enc, opt)
        self.assertEqual(default['break_skill'], dict(name=None, uses=0, points_gained=0))
        explicit_none = simulate(party, enc, dict(opt, break_skill=None))
        for result in (default, explicit_none):
            result.pop('runtime_ms_per_run')
        self.assertEqual(default, explicit_none)
        for policy in (None, ('boss_first', 'any_attack')):
            self.assertEqual(_opts(json.dumps({'break_skill': CUBE}), policy)['break_skill'], CUBE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
