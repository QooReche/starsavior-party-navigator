# -*- coding: utf-8 -*-
"""브레이크 스킬 클라 대조 고정(2026-11-21, docs/break_skill_1121.md). python -X utf8 -I tests/break_skill_1121_test.py

1. 표 고정: 엔진이 모델링하지 않는 오비탈 표 필드(NoReuseOrbital·ForceApplyOrbital·OrbitalSkillActiveUnitId·
   SkillLevelCoolTurnReduce·DomainInfinityTurn)가 구원자 브레이크 스킬에서 모두 꺼져 있고, 엔진 규칙 값(쿨 8·포인트 3·
   영역 5·스타피어서 피해 50%·게이지 2000·치확/치피 10%p·역할 추가)이 표와 같음. 표가 바뀌면 실패해 다시 대조하게 함.
   STARSAVIOR_STATIC 이 없으면 건너뜀.
2. 영역은 발동 팀(아군)에만 걸림 — 적에게 붙지 않음(NKM:8486-8497 팀 검사).
3. tools/measure_break_skill.aggregate: 이긴 판/진 판을 나눠 발동 횟수를 셈.
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests'), os.path.join(ROOT, 'tools')]
from break_skill_test import legacy_setup
from battlesim.mc import break_skill_levels
from battlesim.rules import MC_OPTS

PLAYER_SKILLS = {101: '특이점 관측', 102: '스타피어서', 103: '큐브 과부하', 104: '행성 정화', 105: '차원 강습'}
DOMAIN_OF = {101: 'DOMAIN_LISA', 102: 'DOMAIN_VOYAGER_GUNBLADE', 103: 'DOMAIN_OMEGA',
             104: 'DOMAIN_ALICIA', 105: 'DOMAIN_GLEIPNIRE'}


def _static():
    root = os.environ.get('STARSAVIOR_STATIC')
    return root if root and os.path.isdir(os.path.join(root, 'tables')) else None


def _table(name):
    with open(os.path.join(_static(), 'tables', name + '.json'), encoding='utf-8') as f:
        return json.loads(re.sub(r'^\s*//.*$', '', f.read(), flags=re.M))['Data']


@unittest.skipUnless(_static(), 'STARSAVIOR_STATIC 미설정')
class OrbitalTablePinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arr = {r['m_SkillID']: r for r in _table('ORBITAL_ARRAY_TEMPLET')}
        cls.dom = {r['DomainStrId']: r for r in _table('ORBITAL_DOMAIN_TEMPLET')}
        cls.lv = _table('ORBITAL_LEVEL_GROUP_TEMPLET')
        cls.se = {r['m_SEStrID']: r for r in _table('SE_TEMPLET_ORBITAL_ARRAY')}
        cls.be = {r['BattleEffectId']: r for r in _table('BATTLE_EFFECT_TEMPLET')}
        cls.dt = {r['DTStrID']: r for r in _table('DAMAGE_TEMPLET')}

    def test_unmodeled_flags_off(self):
        # ST:24198-24224(OBF_14671 로더), NKM:1442-1493(사용 가능 검사): 아래 필드가 켜지면 엔진에 없는 제한이 생김
        for sid in PLAYER_SKILLS:
            r = self.arr[sid]
            with self.subTest(skill=sid):
                self.assertFalse(r.get('NoReuseOrbital', False))
                self.assertFalse(r.get('ForceApplyOrbital', False))
                self.assertFalse(r.get('OrbitalSkillActiveUnitId'))
                self.assertEqual(r['m_TARGET_TYPE'], 'NSTT_ALLY_ALL' if sid == 103 else 'NSTT_ENEMY_ALL')
        self.assertFalse(any('SkillLevelCoolTurnReduce' in r for r in self.lv))   # ST:24310-24318 쿨 감소 합 = 0

    def test_cost_cooldown_domain_life(self):
        mc = MC_OPTS
        for sid, name in PLAYER_SKILLS.items():
            r, d = self.arr[sid], self.dom[DOMAIN_OF[sid]]
            with self.subTest(skill=name):
                self.assertEqual(r['m_CoolTurn'], mc['break_skill_cooldown'])
                self.assertEqual(r['OrbitalTriggerPoint'], mc['break_skill_cost'])
                self.assertEqual(r['OrbitalTriggerPoint'], mc['break_skill_point_cap'])
                self.assertEqual(r['DomainStrId'], DOMAIN_OF[sid])
                self.assertFalse(d['DomainInfinityTurn'])
                turns = mc['break_skill_domain_turns'] if name == '큐브 과부하' else mc['break_skills'][name]['domain_turns']
                self.assertEqual(d['DomainGlobalLifeTurn'], turns)
                # 영역이 남아 있으면 다시 쓸 수 없는 클라 검사(NKM:1458-1461)는 영역 수명 < 쿨일 때 도달 불가
                self.assertLess(d['DomainGlobalLifeTurn'], r['m_CoolTurn'])

    def test_starpiercer_values(self):
        rule = MC_OPTS['break_skills']['스타피어서']
        r = self.arr[102]
        self.assertNotIn('GetNovaForceValue', r)
        self.assertNotIn('nova', rule)
        self.assertEqual(self.dt[r['DTStrID']]['AllyAllAtkFactor'] / 10000, rule['damage_ratio'])
        gauge = self.se['COND_ORBITAL_ARRAY_VOYAGER_GUNBLADE_01_01']
        self.assertEqual((gauge['m_BuffTargetType'], gauge['m_BuffStrID'], gauge['SpeedGaugeRate']),
                         ('NSETT_MYTEAM_ALL', 'BI_SPEED_GAUGE_UP', rule['gauge']))
        stat = {'NST_RATE_CRITICAL': '치명타 확률', 'NST_RATE_CRITICAL_DAMAGE': '치명타 피해'}
        role = {'NURT_STRIKER': '스트라이커', 'NURT_RANGER': '레인저'}
        base, extra = {}, {}
        for cid in self.dom['DOMAIN_VOYAGER_GUNBLADE']['CharmList']:
            e = self.be[cid]
            self.assertEqual(e['AteamEffectTarget'], 'ALL')
            key = stat[e['BattleEffectStatType']]
            if 'TargetRoleType' in e:
                extra.setdefault(role[e['TargetRoleType']], {})[key] = e['BattleEffectStatValue'] / 100
            else:
                base[key] = e['BattleEffectStatValue'] / 100
        self.assertEqual(base, rule['props'])
        self.assertEqual(sorted(extra), sorted(rule['bonus_roles']))
        for props in extra.values():
            self.assertEqual(props, rule['role_props'])

    def test_level_damage_rows(self):
        levels = break_skill_levels()
        for sid, name in PLAYER_SKILLS.items():
            rows = sorted((r for r in self.lv if r['SkillLevelGroupID'] == self.arr[sid]['SkillLevelGroup']),
                          key=lambda r: r['SkillLevelValue'])
            dmg = [sum(x.get('SkillLevelDamageUp', 0) for x in rows[:i + 1]) for i in range(len(rows))]
            heal = [sum(x.get('SkillLevelHealUp', 0) for x in rows[:i + 1]) for i in range(len(rows))]
            with self.subTest(skill=name):
                self.assertEqual(levels[name]['dmg'], dmg)
                self.assertEqual(levels[name]['heal'], heal)
        self.assertEqual(levels['스타피어서']['dmg'][3], 300)   # Lv4 = 50% + 3%p


class DomainTeamTest(unittest.TestCase):
    def test_domain_only_on_casting_team(self):
        b = legacy_setup({'name': '스타피어서'}, roles=('스트라이커', '서포터'))
        for u in b.allies:
            u.d.skills.clear()
        f = b.foes[0]
        cr0 = f.mods()['cr']
        b.break_points = 3
        b.act(b.allies[0])
        self.assertEqual(b.break_skill_uses, 1)
        self.assertTrue(all(u.has('전략 사령부') for u in b.allies))
        self.assertFalse(f.has('전략 사령부'))
        self.assertEqual(f.mods()['cr'], cr0)


class AggregateTest(unittest.TestCase):
    def test_split_by_result(self):
        import measure_break_skill as M
        lost = dict(result='timeout', turns=40, uses=[22], domain=[(22, 26)], domain_open_at_end=None,
                    points=[dict(turn=21, boss=True, gained=3, cd=0, new_break=True)], boss_breaks=[21],
                    points_gained=3, points_left=0)
        won = dict(result='clear', turns=45, uses=[19, 41], domain=[(19, 23), (41, 45)], domain_open_at_end=None,
                   points=[dict(turn=18, boss=True, gained=3, cd=0, new_break=True),
                           dict(turn=40, boss=True, gained=3, cd=0, new_break=True)], boss_breaks=[18, 40],
                   points_gained=6, points_left=0)
        agg = M.aggregate([lost, lost, won])
        self.assertEqual(agg['lost']['uses_dist'], {1: 2})
        self.assertEqual(agg['clear']['uses_dist'], {2: 1})
        self.assertEqual(agg['all']['uses_mean'], round(4 / 3, 3))
        self.assertEqual(agg['all']['domain_life_turns'], {5: 4})
        self.assertEqual(agg['lost']['points_after_first_use_mean'], 0)
        self.assertEqual(agg['clear']['points_after_first_use_mean'], 3)


if __name__ == '__main__':
    unittest.main()
