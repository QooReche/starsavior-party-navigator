# -*- coding: utf-8 -*-
"""적 소환 시험. python -X utf8 -I tests/run_workspace_test.py tests/summon_test.py"""
import copy
import json
import math
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from battlesim.api import _CustomFoe, simulate
from battlesim.mc import Battle, Unit, Ctx, EventLimitError
from battlesim.metrics import unit_def
from battlesim.starsavior.parser import Line, Skill, parse_effect
from battlesim.starsavior.foe import stage_waves, FoeDef, load_foe, foe_summon


TEAM = ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle']


def _make_summoner(name='boss', summon_name='minion', hp=200000, atk=5000, slots=None,
                   skill_slot='패시브', summon_hp=30000, summon_atk=2000, summon_spd=100,
                   boss=True, spd=100, cd=None, summon_spawn='A'):
    """소환자 FoeDef + 소환 그룹을 만든다. slots = 소환 유닛을 넣을 칸 번호 목록."""
    if slots is None:
        slots = [0, 4]
    d = _CustomFoe(dict(name=name, hp=hp, atk=atk, **{'def': 3000}, spd=spd), 0)
    d.boss = boss
    d.slot = 2
    # 소환 효과 줄 추가
    raw_ef = '[스킬 사용 후] 자신에게 소환: %s ×%d' % (summon_name, len(slots))
    ef_line = Line(raw_ef, skill_slot, 'passive' if skill_slot == '패시브' else 'active')
    d.lines = list(getattr(d, 'lines', [])) + [ef_line]
    # 소환 유닛 정의
    summon_slots = []
    for pos in slots:
        sd = _CustomFoe(dict(name=summon_name, hp=summon_hp, atk=summon_atk, **{'def': 1000}, spd=summon_spd), 0)
        sd.spawn = summon_spawn
        sd.slot = pos
        summon_slots.append({'pos': pos, 'foe_def': sd})
    d.summon_groups = [{'group_id': 'test', 'slots': summon_slots}]
    return d


def _battle(ally_keys=TEAM, foe_defs=None, mc_override=None, **kw):
    mc = dict(summon='data')
    mc.update(mc_override or {})
    foes = foe_defs or [_make_summoner()]
    b = Battle([unit_def(k) for k in ally_keys], [foes], random.Random(42), mc=mc, **kw)
    return b


class SummonParseTest(unittest.TestCase):
    def test_parse_summon_effect(self):
        eff = parse_effect('자신에게 소환: 올베로스의 하수인 ×4')
        self.assertEqual(eff['kind'], 'summon')
        self.assertEqual(eff['name'], '올베로스의 하수인')
        self.assertEqual(eff['count'], 4)

    def test_parse_summon_spaces(self):
        eff = parse_effect('자신에게 소환: 고대 병졸 ×2')
        self.assertEqual(eff['kind'], 'summon')
        self.assertEqual(eff['name'], '고대 병졸')
        self.assertEqual(eff['count'], 2)


class OlberosTest(unittest.TestCase):
    """올베로스 하수인: 패시브, 하수인 4기가 처음부터 배치에 있고, 사망 후 스킬 사용 시 빈 칸만 리필."""

    def test_initial_slots_full_no_extra_summon(self):
        """초기 배치에 4기가 모두 있으면 소환해도 추가 유닛이 안 생김."""
        summoner = _make_summoner(slots=[0, 1, 3, 4])
        minion0 = _CustomFoe(dict(name='minion', hp=10000, atk=1000, **{'def': 500}, spd=80), 0)
        minion0.slot = 0; minion0.spawn = 'N'
        minion1 = _CustomFoe(dict(name='minion', hp=10000, atk=1000, **{'def': 500}, spd=80), 0)
        minion1.slot = 1; minion1.spawn = 'N'
        minion3 = _CustomFoe(dict(name='minion', hp=10000, atk=1000, **{'def': 500}, spd=80), 0)
        minion3.slot = 3; minion3.spawn = 'N'
        minion4 = _CustomFoe(dict(name='minion', hp=10000, atk=1000, **{'def': 500}, spd=80), 0)
        minion4.slot = 4; minion4.spawn = 'N'
        wave = [minion0, minion1, summoner, minion3, minion4]
        b = _battle(foe_defs=wave)
        b.spawn_wave()
        initial_count = len(b.foes)
        self.assertEqual(initial_count, 5)
        # 소환자가 스킬을 사용해도 빈 칸이 없으므로 foes 수 불변
        sk = summoner.skills.get('기본기') or list(summoner.skills.values())[0]
        ctx = b.cast(b.foes[2], sk)  # 올베로스(pos 2)가 기본기
        self.assertEqual(len(b.foes), 5, '빈 칸 없으면 소환 안 됨')

    def test_kill_then_refill_one_slot(self):
        """하수인 1기 처치 후 소환자 스킬 사용 → 그 칸만 다시 채움."""
        summoner = _make_summoner(slots=[0, 4])
        m0 = _CustomFoe(dict(name='minion', hp=100, atk=100, **{'def': 100}, spd=80), 0)
        m0.slot = 0; m0.spawn = 'A'
        m4 = _CustomFoe(dict(name='minion', hp=100, atk=100, **{'def': 100}, spd=80), 0)
        m4.slot = 4; m4.spawn = 'A'
        wave = [m0, summoner, m4]
        b = _battle(foe_defs=wave)
        b.spawn_wave()
        self.assertEqual(len(b.foes), 3)
        # 칸 0 하수인 처치
        victim = b._foe_slots[0]
        self.assertIsNotNone(victim)
        b.kill(victim, b.allies[0])
        self.assertIsNone(b._foe_slots[0], '사망 시 칸 비움')
        self.assertIsNotNone(b._foe_slots[4], '다른 칸은 유지')
        # 소환자 스킬 사용 → 칸 0만 채움
        summoner_u = b._foe_slots[2]
        sk = list(summoner_u.d.skills.values())[0]
        b.cast(summoner_u, sk)
        self.assertIsNotNone(b._foe_slots[0], '빈 칸 0에 소환됨')
        self.assertTrue(b._foe_slots[0].summoned)
        self.assertEqual(len(b.foes), 4, '한 기만 추가됨')

    def test_no_exceed_4(self):
        """4기 초과 소환 불가(칸이 5개뿐이고 소환자가 1칸 차지)."""
        summoner = _make_summoner(slots=[0, 1, 3, 4])
        wave = [summoner]
        b = _battle(foe_defs=wave)
        b.spawn_wave()
        self.assertEqual(len(b.foes), 1)
        # 소환 → 4기 추가(칸 0,1,3,4)
        sk = list(b.foes[0].d.skills.values())[0]
        b.cast(b.foes[0], sk)
        self.assertEqual(len(b.foes), 5)
        # 다시 소환 → 추가 없음
        b.cast(b.foes[0], sk)
        self.assertEqual(len(b.foes), 5, '빈 칸 없으면 추가 안 됨')


class TyriaTest(unittest.TestCase):
    """티리아 인형: 패시브, 2기 생성, 3기 이상 안 됨."""

    def test_summon_2_dolls(self):
        """티리아(칸 2)가 스킬 사용 후 인형 2기(칸 1, 3)를 소환."""
        summoner = _make_summoner(name='tyria', summon_name='doll', slots=[1, 3],
                                  summon_hp=15000, summon_spd=90)
        wave = [summoner]
        b = _battle(foe_defs=wave)
        b.spawn_wave()
        self.assertEqual(len(b.foes), 1)
        sk = list(b.foes[0].d.skills.values())[0]
        b.cast(b.foes[0], sk)
        self.assertEqual(len(b.foes), 3)
        self.assertIsNotNone(b._foe_slots[1])
        self.assertIsNotNone(b._foe_slots[3])

    def test_no_third_doll(self):
        """인형 2기가 차 있으면 추가 소환 안 됨."""
        summoner = _make_summoner(name='tyria', summon_name='doll', slots=[1, 3])
        wave = [summoner]
        b = _battle(foe_defs=wave)
        b.spawn_wave()
        sk = list(b.foes[0].d.skills.values())[0]
        b.cast(b.foes[0], sk)  # 2기 소환
        b.cast(b.foes[0], sk)  # 다시 소환 시도
        self.assertEqual(len(b.foes), 3, '3기 이상 안 됨')


class PersesTest(unittest.TestCase):
    """페르세스 고대 병졸: 특수기 cd 4, 2기 소환."""

    def test_special_skill_cooldown_zero(self):
        """소환된 병졸의 시작 쿨이 flag S 로 특수기 0."""
        summoner = _make_summoner(name='perses', summon_name='soldier', slots=[0, 4],
                                  summon_spawn='S', summon_hp=20000)
        wave = [summoner]
        b = _battle(foe_defs=wave)
        b.spawn_wave()
        sk = list(b.foes[0].d.skills.values())[0]
        b.cast(b.foes[0], sk)
        for u in b.foes:
            if u.summoned:
                # flag S = 특수기 쿨 0(나머지 가득)
                sp_cd = u.cd.get('특수기', None)
                if sp_cd is not None:
                    self.assertEqual(sp_cd, 0, '특수기 쿨 0')


class SummonBehaviorTest(unittest.TestCase):
    """소환 유닛 행동·웨이브·off 스위치."""

    def test_summoned_unit_acts(self):
        """소환 유닛이 전역 턴에 포함(alive(1)에 들어가 pick_next 로 선택됨)."""
        summoner = _make_summoner(slots=[0, 4], summon_hp=50000, summon_spd=200)
        wave = [summoner]
        b = _battle(foe_defs=wave, max_turns=5)
        b.spawn_wave()
        sk = list(b.foes[0].d.skills.values())[0]
        b.cast(b.foes[0], sk)
        # 소환 유닛이 alive(1)에 포함
        living = b.alive(1)
        self.assertEqual(len(living), 3)
        summoned = [u for u in living if u.summoned]
        self.assertEqual(len(summoned), 2)

    def test_wave_clear_requires_summons_dead(self):
        """소환 유닛이 살아 있으면 웨이브 클리어 안 됨."""
        summoner = _make_summoner(slots=[0], summon_hp=50000)
        wave = [summoner]
        b = _battle(foe_defs=wave)
        b.spawn_wave()
        sk = list(b.foes[0].d.skills.values())[0]
        b.cast(b.foes[0], sk)
        # 소환자 처치
        b.kill(b._foe_slots[2], b.allies[0])
        self.assertTrue(len(b.alive(1)) > 0, '소환 유닛 생존')

    def test_off_switch(self):
        """mc.summon=off 일 때 소환 안 되고 unsupported 에 기록됨."""
        summoner = _make_summoner(slots=[0, 4])
        wave = [summoner]
        b = _battle(foe_defs=wave, mc_override={'summon': 'off'})
        b.spawn_wave()
        sk = list(b.foes[0].d.skills.values())[0]
        b.cast(b.foes[0], sk)
        self.assertEqual(len(b.foes), 1, 'off 면 소환 안 됨')
        self.assertTrue(any('summon' in k for k in b.unsup), 'unsupported 에 기록')

    def test_progress_excludes_summons(self):
        """progress() 는 소환 유닛을 분모에 넣지 않음."""
        summoner = _make_summoner(slots=[0, 4], hp=100000)
        wave = [summoner]
        b = _battle(foe_defs=wave)
        b.spawn_wave()
        sk = list(b.foes[0].d.skills.values())[0]
        p0 = b.progress()
        b.cast(b.foes[0], sk)  # 2기 소환
        p1 = b.progress()
        # 소환 전후 진척도 변화 없음(소환자 체력 안 변함)
        self.assertAlmostEqual(p0, p1, places=3, msg='소환 추가가 진척도를 바꾸지 않음')


class SummonStaticReportTest(unittest.TestCase):
    """support_report 에서 소환 줄이 unsupported 로 안 잡힘."""

    def test_summon_line_not_unsupported(self):
        from battlesim.mc import support_report
        summoner = _make_summoner(slots=[0, 4])
        report = support_report([summoner])
        summon_reasons = [r for r in report if 'summon' in r.get('raw', '').lower() or '소환' in r.get('raw', '')]
        self.assertEqual(len(summon_reasons), 0, 'support_report 에 소환이 unsupported 로 나오지 않음')


if __name__ == '__main__':
    unittest.main()
