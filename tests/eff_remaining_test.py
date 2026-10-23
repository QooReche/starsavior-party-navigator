# -*- coding: utf-8 -*-
"""효과 미지원 항목 구현 시험. python -X utf8 -I tests/eff_remaining_test.py"""
import os, sys, unittest, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('STARSAVIOR_STATIC', os.path.join(ROOT, '..', 'starsavior-static-data'))

from battlesim.starsavior.parser import parse_effect, trig_kind, _map_prop, _perm_apply
from battlesim.mc import support_report, Battle, _m_vs
from battlesim.api import simulate, _CustomFoe
from battlesim.starsavior.foe import stage_waves
from battlesim.metrics import unit_def
from collections import defaultdict


class ParserTest(unittest.TestCase):
    """파서 변경 항목 단위 시험."""

    def test_extend_dur(self):
        """효과 지속 턴 +1 → kind='extend'."""
        e = parse_effect('적(자동 지정)에게 효과 지속 턴 +1')
        self.assertEqual(e['kind'], 'extend')
        self.assertEqual(e['val'], 1)
        self.assertEqual(e['target'], '적(자동 지정)')

    def test_gauge_set_if(self):
        """행동 게이지 조건부 설정 → kind='gauge_set_if'."""
        e = parse_effect('자신에게 행동 게이지가 0%보다 높으면 0%로 낮춤 {효과 적중 판정}')
        self.assertEqual(e['kind'], 'gauge_set_if')
        self.assertEqual(e['threshold'], 0.0)
        self.assertEqual(e['val'], 0.0)
        self.assertTrue(e['judge'])

    def test_local_chance(self):
        """N% 확률로 능력치 보정 → kind='local', val에 확률 곱."""
        e = parse_effect('자신에게 75% 확률로 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}')
        self.assertEqual(e['kind'], 'local')
        self.assertEqual(e['stat'], '피해 증가')
        self.assertAlmostEqual(e['val'], 30.0 * 0.75)

    def test_local_other_target(self):
        """타 대상 이번 스킬 능력치 보정 → kind='local' with target."""
        e = parse_effect('적 전체에게 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}')
        self.assertEqual(e['kind'], 'local')
        self.assertEqual(e['target'], '적 전체')
        self.assertAlmostEqual(e['val'], 30.0)

    def test_local_other_no_skill_flag(self):
        """이번 스킬 플래그가 없는 타 대상 → ignored(종전 동작)."""
        e = parse_effect('적 전체에게 능력치 보정 방어력% -30%')
        self.assertEqual(e['kind'], 'ignored')

    def test_extra_cast_other_target(self):
        """아군 대상 추가 발동 → kind='extra_cast' with target."""
        e = parse_effect('아군 1명(자동 지정)에게 기본기 추가 발동')
        self.assertEqual(e['kind'], 'extra_cast')
        self.assertEqual(e['slot'], '기본기')
        self.assertEqual(e['target'], '아군 1명(자동 지정)')

    def test_extra_cast_self(self):
        """자신 추가 발동(기존 호환)."""
        e = parse_effect('자신에게 궁극기 추가 발동')
        self.assertEqual(e['kind'], 'extra_cast')
        self.assertEqual(e['slot'], '궁극기')
        self.assertEqual(e['target'], '자신')

    def test_trig_spawn(self):
        """등장 후 → battle_start."""
        self.assertEqual(trig_kind('등장 후', None), 'battle_start')

    def test_preemptive_prop(self):
        """선제 방어 확률 → _map_prop."""
        self.assertEqual(_map_prop('선제 방어 확률'), ('preempt', None))

    def test_preemptive_perm(self):
        """선제 방어 확률 상시 → _perm_apply."""
        p = defaultdict(float)
        ok = _perm_apply({}, p, {'stat': '선제 방어 확률', 'val': 30})
        self.assertTrue(ok)
        self.assertAlmostEqual(p['preempt'], 0.30)

    def test_vs_element_local_regex(self):
        """vs X 속성 피해 증가 regex."""
        self.assertTrue(_m_vs.match('vs 달 속성 피해 증가'))
        self.assertTrue(_m_vs.match('vs 태양 속성 피해 증가'))
        self.assertFalse(_m_vs.match('피해 증가'))

    def test_perm_undispellable_as_buff(self):
        """해제 불가 능력치 보정 → kind='buff' (영구 버프)."""
        e = parse_effect('자신에게 능력치 보정 속도% -1000% {해제 불가}')
        self.assertEqual(e['kind'], 'buff')
        self.assertEqual(e['props']['속도%'], -1000.0)


class SupportReportTest(unittest.TestCase):
    """support_report 마커 교차 수집 시험."""

    def test_cross_def_marker(self):
        """다른 def 의 조건이 참조하는 버프는 미해석으로 보고하지 않음(올베로스 영웅의 혼)."""
        from battlesim.starsavior.parser import UnitDef, Line
        # 하수인: 영웅의 혼 부여
        from battlesim.starsavior.data import DB
        db = DB()
        # 시뮬레이션 대신 간이 검증: 올베로스 1단계
        src = ROOT
        st, waves = stage_waves('cosmo', '올베로스', '올베로스 1단계', src)
        defs = [d for w in waves for d in w]
        rpt = support_report(defs)
        # 영웅의 혼(해제불가) 가 의미 미해석으로 나오지 않아야 함
        hero_soul = [r for r in rpt if '영웅의 혼' in r['raw'] and '의미 미해석' in r['reason']]
        self.assertEqual(hero_soul, [], '영웅의 혼이 여전히 미해석으로 보고됨: %s' % hero_soul)

    def test_foe_react_marker(self):
        """foe_react 조건이 참조하는 버프는 미해석으로 보고하지 않음(맹약결속)."""
        src = ROOT
        st, waves = stage_waves('oph', '고립된 저택', 'SECTOR 35-10', src)
        defs = [d for w in waves for d in w]
        rpt = support_report(defs)
        covenant = [r for r in rpt if '맹약결속' in r['raw'] and '의미 미해석' in r['reason']]
        self.assertEqual(covenant, [], '맹약결속이 여전히 미해석으로 보고됨: %s' % covenant)


class EngineTest(unittest.TestCase):
    """엔진 동작 시험."""

    def test_vs_element_local(self):
        """vs 달 속성 피해 증가가 달 속성 적에게만 적용됨."""
        src = ROOT
        # 잊혀진 맹세 Ⅰ 시뮬
        r = simulate(['professor-m', 'gwen', 'fei', 'amora'],
                     {'stage': 'equip/잊혀진 맹세/잊혀진 맹세 Ⅰ'},
                     {'n_runs': 2, 'seed': 1, 'rules_override': {'local_vs_element': 'on'}})
        rt = r.get('unsupported', {}).get('runtime', {})
        vs_unsup = [k for k in rt if 'vs 달' in k]
        self.assertEqual(vs_unsup, [], 'vs 달 속성 피해 증가가 여전히 미지원: %s' % vs_unsup)

    def test_vs_element_off(self):
        """off 로 하면 unsupported 에 기록."""
        r = simulate(['professor-m', 'gwen', 'fei', 'amora'],
                     {'stage': 'equip/잊혀진 맹세/잊혀진 맹세 Ⅰ'},
                     {'n_runs': 2, 'seed': 1, 'rules_override': {'local_vs_element': 'off'}})
        rt = r.get('unsupported', {}).get('runtime', {})
        vs_unsup = [k for k in rt if 'local_vs_element off' in k]
        self.assertGreater(len(vs_unsup), 0, 'off 일 때 unsupported 기록이 없음')


if __name__ == '__main__':
    unittest.main()
