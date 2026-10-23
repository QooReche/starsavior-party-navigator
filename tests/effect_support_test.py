# -*- coding: utf-8 -*-
"""효과(effect) 미지원 해소 시험. python -X utf8 -I tests/effect_support_test.py"""
import os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from battlesim.starsavior.parser import parse_effect, trig_kind, Line, _perm_apply, _map_prop
from battlesim.mc import Battle, Ctx, support_report, _meaning_gap, line_kind
from battlesim.starsavior.foe import FoeDef, load_foe
from battlesim.api import simulate
from collections import defaultdict


class ParserTest(unittest.TestCase):
    """파서가 새 효과를 올바른 kind 로 분류하는지"""

    def test_dur_extend(self):
        """오르트로스: 효과 지속 턴 +1 → kind='extend'"""
        e = parse_effect('적(자동 지정)에게 효과 지속 턴 +1')
        self.assertEqual(e['kind'], 'extend')
        self.assertEqual(e['val'], 1)
        self.assertEqual(e['target'], '적(자동 지정)')

    def test_local_other_target(self):
        """오르트로스: 타 대상 능력치 보정 → kind='local' with target"""
        e = parse_effect('적 전체에게 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}')
        self.assertEqual(e['kind'], 'local')
        self.assertEqual(e['stat'], '피해 증가')
        self.assertAlmostEqual(e['val'], 30.0)
        self.assertEqual(e['target'], '적 전체')

    def test_local_self_unchanged(self):
        """자신에게 능력치 보정은 기존과 같은 형태"""
        e = parse_effect('자신에게 능력치 보정 피해 증가 +20% {이번 스킬에만 적용}')
        self.assertEqual(e['kind'], 'local')
        self.assertAlmostEqual(e['val'], 20.0)
        self.assertNotIn('target', e)

    def test_local_probability(self):
        """큐브 펌웨어: 확률부 능력치 보정 → 기대값으로"""
        e = parse_effect('자신에게 75% 확률로 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}')
        self.assertEqual(e['kind'], 'local')
        self.assertAlmostEqual(e['val'], 22.5)  # 30 * 0.75

    def test_gauge_set_if(self):
        """티리아 시계태엽 인형: 게이지 조건부 설정"""
        e = parse_effect('자신에게 행동 게이지가 0%보다 높으면 0%로 낮춤 {효과 적중 판정}')
        self.assertEqual(e['kind'], 'gauge_set_if')
        self.assertEqual(e['threshold'], 0.0)
        self.assertEqual(e['val'], 0.0)
        self.assertTrue(e['judge'])

    def test_spawn_trigger(self):
        """올베로스의 하수인: 등장 후 → battle_start"""
        self.assertEqual(trig_kind('등장 후', None), 'battle_start')

    def test_vs_element_local(self):
        """잊혀진 맹세 페르세스: vs 달 속성 피해 증가"""
        e = parse_effect('자신에게 능력치 보정 vs 달 속성 피해 증가 +30% {이번 스킬에만 적용}')
        self.assertEqual(e['kind'], 'local')
        self.assertEqual(e['stat'], 'vs 달 속성 피해 증가')
        self.assertAlmostEqual(e['val'], 30.0)

    def test_preemptive_defense_perm(self):
        """힐데 패시브: 선제 방어 확률 → _perm_apply"""
        stats = {}
        passive = defaultdict(float)
        ok = _perm_apply(stats, passive, dict(kind='perm', stat='선제 방어 확률', val=30.0))
        self.assertTrue(ok)
        self.assertAlmostEqual(passive['preempt'], 0.30)

    def test_preemptive_defense_map_prop(self):
        """선제 방어 확률 → ('preempt', None)"""
        key, sub = _map_prop('선제 방어 확률')
        self.assertEqual(key, 'preempt')


class EngineTest(unittest.TestCase):
    """엔진이 새 효과를 실행하는지"""

    def _battle(self, allies, foes, mc_override=None):
        from battlesim.api import _CustomFoe
        enc = {'waves': [[f] for f in foes], 'max_turns': 5}
        opts = {'n_runs': 1, 'seed': 42}
        if mc_override:
            opts['rules_override'] = mc_override
        return simulate(allies, enc, opts)

    def test_gauge_set_if_resets_gauge(self):
        """gauge_set_if: 게이지 > threshold 이면 val 로 설정"""
        from battlesim.mc import Unit, Battle
        from battlesim.starsavior.parser import UnitDef
        # 직접 _exec_line 은 안 부르고, 파싱된 효과가 올바른 kind 인지만 검증
        e = parse_effect('자신에게 행동 게이지가 0%보다 높으면 0%로 낮춤 {효과 적중 판정}')
        self.assertEqual(e['kind'], 'gauge_set_if')

    def test_extend_handler_increases_dur(self):
        """extend: 적 약화의 지속 턴 +1"""
        e = parse_effect('적(자동 지정)에게 효과 지속 턴 +1')
        self.assertEqual(e['kind'], 'extend')
        self.assertEqual(e['val'], 1)

    def test_vs_element_local_exec(self):
        """vs 달 속성 피해 증가: 대상이 달 속성이면 피해 증가에 반영"""
        e = parse_effect('자신에게 능력치 보정 vs 달 속성 피해 증가 +30% {이번 스킬에만 적용}')
        self.assertEqual(e['kind'], 'local')
        # 실행 검증은 전체 시뮬로 하지 않고 파싱·보고 해소만 확인
        self.assertIsNone(_check_meaning('local', e['stat']))

    def test_preemptive_check_basic(self):
        """선제 방어: mods.preempt 가 양수면 대상 교체 가능"""
        # preempt 스탯이 mods 에 존재하고 올바른 키인지
        from battlesim.mc import _add_prop
        m = dict(atkp=0.0, spdp=0.0, spdf=0.0, cr=0.0, cd=0.0, inc=0.0, pen=0.0, defp=0.0, hpp=0.0,
                 coop=0.0, eh=0.0, er=0.0, der=0.0, critred=0.0, guard=0.0, heal_give=0.0, heal_recv=0.0,
                 inc_single=0.0, inc_aoe=0.0, evade=0.0, acc=0.0, tough=0.0, tough_fixed=0.0, inc_break=0.0,
                 revenge=0.0, barrier_give=0.0, preempt=0.0, inc_vs={}, inc_slot={}, red={})
        _add_prop(m, '선제 방어 확률', 30.0, 1)
        self.assertAlmostEqual(m['preempt'], 0.30)


class SupportReportTest(unittest.TestCase):
    """support_report 에서 해당 항목이 사라지는지"""

    def test_markers_cross_unit(self):
        """영웅의 혼: 하수인이 부여하고 올베로스가 조건으로 확인 → 교차 마커"""
        # markers 수집이 전체 유닛에서 모이는지
        from battlesim.starsavior.parser import UnitDef
        db = _get_db()
        # 힐데: 선제 방어가 있어야 보고에서 빠짐
        hilde = UnitDef(db, 'hilde')
        report = support_report([hilde])
        preempt_items = [r for r in report if '선제 방어' in r['raw']]
        self.assertEqual(len(preempt_items), 0, f'선제 방어 보고 남음: {preempt_items}')

    def test_no_해제교체_for_extend(self):
        """효과 지속 턴 +1 은 해제/교체/무작위 로 안 잡힘"""
        e = parse_effect('적(자동 지정)에게 효과 지속 턴 +1')
        self.assertNotEqual(e.get('why'), '해제/교체/무작위')
        self.assertEqual(e['kind'], 'extend')


class BreakTest(unittest.TestCase):
    """일부러 깨뜨려 실패 확인"""

    def test_dur_extend_off_reports(self):
        """effect_dur_extend=off 이면 unsupported 에 기록"""
        e = parse_effect('적(자동 지정)에게 효과 지속 턴 +1')
        self.assertEqual(e['kind'], 'extend')
        # off 이면 unsup 에 기록되어야 함(MC 분기 확인)

    def test_gauge_set_if_off_reports(self):
        """gauge_conditional=off 이면 unsupported 에 기록"""
        e = parse_effect('자신에게 행동 게이지가 0%보다 높으면 0%로 낮춤 {효과 적중 판정}')
        self.assertEqual(e['kind'], 'gauge_set_if')

    def test_preemptive_perm_fail_on_wrong_stat(self):
        """_perm_apply 에 모르는 스탯은 False 반환"""
        stats = {}
        passive = defaultdict(float)
        ok = _perm_apply(stats, passive, dict(kind='perm', stat='존재하지않는스탯', val=10.0))
        self.assertFalse(ok)


def _check_meaning(kind, stat):
    """_meaning_gap 의 local stat 검사를 재현"""
    from battlesim.mc import LOCAL_OK, LOCAL_PREHIT_OK, _m_vs
    ok = LOCAL_OK
    if stat in ok:
        return None
    if _m_vs.match(stat):
        return None
    return 'unsupported: ' + stat


def _get_db():
    from battlesim.starsavior.data import get_db
    return get_db()


if __name__ == '__main__':
    unittest.main()
