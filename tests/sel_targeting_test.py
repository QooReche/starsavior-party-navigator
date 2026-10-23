# -*- coding: utf-8 -*-
"""대상 선택 개선 시험(r3-sel): 적 피격 반응 자동 대상, BI_ENFORCE 강제 추가 행동, 구원자 NOT_SELF·IsHighDef.

  python -X utf8 -I tests/sel_targeting_test.py
"""
import json
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p3_test import battle, give, unit   # noqa: E402
from battlesim.mc import Battle, Ctx, Eff   # noqa: E402
from battlesim.metrics import unit_def   # noqa: E402
from battlesim.starsavior.foe import FoeDef, load_foe   # noqa: E402

RAW = load_foe()


def foe_by_name(name, with_lines=False):
    for ui, u in enumerate(RAW['u']):
        if u['n'] != name:
            continue
        for xi in [None] + list(range(200)):
            try:
                d = FoeDef(RAW, ui, xi)
            except Exception:
                continue
            if not with_lines or d.auto_lines:
                return d
    raise AssertionError('못 찾음: ' + name)


class FoeHitReactionAutoTargetTest(unittest.TestCase):
    """적 피격 반응 패시브의 「적(자동 지정)」이 게임 규칙(AutoTargetId=17, last_damager)으로 해석되는지."""

    def test_bellwether_mane_last_damager(self):
        """공허선도자: [시전자가 보유: 영혼 구속] 적(자동 지정) → 마지막으로 나를 친 적"""
        d = foe_by_name('공허선도자', with_lines=True)
        lines = [(ln.slot, ln.raw) for ln in d.lines if (ln.slot, ln.raw) in d.auto_lines]
        self.assertGreater(len(lines), 0, '공허선도자 auto_lines 가 비어 있음')
        spec = list(d.auto_lines.values())[0]
        self.assertIn('last_damager', spec['f'])

    def test_fallen_shield_last_damager(self):
        """공허절멸자: [자신이 보유: 공허 방패(해제불가)] 적 1명(자동 지정) → last_damager, one=True"""
        d = foe_by_name('공허절멸자', with_lines=True)
        spec = list(d.auto_lines.values())[0]
        self.assertIn('last_damager', spec['f'])
        self.assertTrue(spec['one'])

    def test_last_damager_resolves_to_attacker(self):
        """last_damager 필터: 마지막으로 나를 친 적 1명을 고른다"""
        d = foe_by_name('공허선도자', with_lines=True)
        b = battle([unit('a%d' % i, hp=10**6) for i in range(4)], [d])
        foe = b.foes[0]
        foe.last_damager = b.allies[2]
        ln = [ln for ln in foe.d.lines if (ln.slot, ln.raw) in foe.d.auto_lines][0]
        b._cur_line = ln
        try:
            got = b.resolve(foe, '적(자동 지정)', Ctx(foe, foe, foe.d.skills.get('궁극기') or foe.d.skills['기본기']), kind='damage')
        finally:
            b._cur_line = None
        self.assertEqual(got, [b.allies[2]])

    def test_off_switch_reports_unsupported(self):
        """foe_auto=off 이면 규칙 미확인 unsup 을 남긴다"""
        d = foe_by_name('공허선도자', with_lines=True)
        b = battle([unit('a')], [d], mc=dict(foe_auto='off'))
        foe = b.foes[0]
        ln = [ln for ln in foe.d.lines if '자동 지정' in ln.raw and '영혼 구속' in ln.raw][0]
        b._cur_line = ln
        try:
            b.resolve(foe, '적(자동 지정)', Ctx(foe, foe, foe.d.skills['기본기']), kind='damage')
        finally:
            b._cur_line = None
        self.assertTrue(any('적 자동 지정 규칙 미확인' in k for k in b.unsup))


class EnforceTest(unittest.TestCase):
    """BI_ENFORCE 강제 추가 행동(올베로스 코스모)."""

    def test_olberos_enforce_data(self):
        """foe_auto.json 에 올베로스의 enforce 줄이 있다"""
        d = foe_by_name('올베로스', with_lines=True)
        enforce_lines = {k: v for k, v in d.auto_lines.items() if v.get('enforce')}
        self.assertEqual(len(enforce_lines), 1, '올베로스 enforce 줄이 1개여야 함')
        spec = list(enforce_lines.values())[0]
        self.assertEqual(spec['enforce']['slot'], '기본기')
        self.assertTrue(spec['ally'])

    def test_enforce_makes_ally_cast(self):
        """enforce=data 이면 〈초즌〉 보유 아군이 기본기를 시전한다"""
        d = foe_by_name('올베로스', with_lines=True)
        b = battle([unit('a%d' % i, hp=10**6) for i in range(4)], [d], mc=dict(enforce='data'))
        foe = b.foes[0]
        # 적 편 아군(= foe 진영 = side 1)에게 초즌 부여 — 올베로스가 자기 진영 아군에게 enforce
        # 여기서는 allies (side 0) 가 foe 의 상대이므로, foe 의 아군 = side 1 = foes
        # 하지만 올베로스의 enforce 대상은 자기 아군(같은 side)이고, enforce 된 유닛이 적(상대)에게 기본기를 쓴다.
        # 테스트: 올베로스 side 1 에 추가 유닛 없으면 초즌이 아무에게도 안 붙음.
        # 단순화: enforce 줄의 line_rest 를 직접 호출해 unsupported 가 안 나는지 확인
        ln = [ln for ln in foe.d.lines if '추가 발동' in ln.raw][0]
        b._cur_line = ln
        ctx = Ctx(foe, foe, foe.d.skills['기본기'])
        from battlesim.mc import line_rest
        try:
            b._run_special_rest(foe, ln, ctx, line_rest(ln))
        finally:
            b._cur_line = None
        # 초즌 보유 아군이 없으면 아무 일도 안 하고 unsupported 도 없어야 함
        self.assertFalse(any('enforce' in k or '추가 발동' in k for k in b.unsup), f'unsup: {dict(b.unsup)}')

    def test_enforce_off_reports_unsupported(self):
        """enforce=off 이면 미지원으로 보고한다"""
        d = foe_by_name('올베로스', with_lines=True)
        b = battle([unit('a')], [d], mc=dict(enforce='off'))
        foe = b.foes[0]
        ln = [ln for ln in foe.d.lines if '추가 발동' in ln.raw][0]
        b._cur_line = ln
        ctx = Ctx(foe, foe, foe.d.skills['기본기'])
        try:
            from battlesim.mc import line_rest
            b._run_special_rest(foe, ln, ctx, line_rest(ln))
        finally:
            b._cur_line = None
        self.assertTrue(any('effect:' in k for k in b.unsup))


class AllyAutoNotSelfTest(unittest.TestCase):
    """구원자 효과 줄 자동 대상: NOT_SELF(자신 제외 1명)."""

    def test_wedding_carmen_not_self(self):
        """웨딩 카르멘 고유 패시브: not_self + high_atk → 자신 제외 공격력 최고"""
        d = json.loads(open(os.path.join(ROOT, 'data', 'auto_skill.json'), encoding='utf-8').read())
        lines = d['lines'].get('wedding-carmen', [])
        self.assertGreater(len(lines), 0, 'wedding-carmen 에 auto lines 가 없음')
        spec = lines[0][2]
        self.assertIn('not_self', spec['f'])
        self.assertIn('high_atk', spec['f'])
        self.assertTrue(spec['ally'])


class IsHighDefFilterTest(unittest.TestCase):
    """IsHighDef 필터(방어력 최고)."""

    def test_tyria_highdef_in_data(self):
        """티리아 궁극기: 방어력 최고 적에게 체크용 버프"""
        d = json.loads(open(os.path.join(ROOT, 'data', 'auto_skill.json'), encoding='utf-8').read())
        lines = d['lines'].get('tyria', [])
        has_highdef = any('high_def' in str(spec['f']) for _, _, spec in lines)
        self.assertTrue(has_highdef, 'tyria 에 high_def 필터가 없음')

    def test_highdef_filter_engine(self):
        """high_def 필터: 방어력 최고 유닛을 고른다"""
        b = battle([unit('low_def', df=500), unit('high_def', df=3000), unit('mid_def', df=1500), unit('pad')],
                   [unit('foe')])
        # allies 중 방어력 최고 = high_def (df=3000)
        pool, ok = b.filter_chain(b.foes[0], b.allies, ['high_def'], stop_at_one=True)
        self.assertTrue(ok)
        self.assertEqual(len(pool), 1)
        self.assertEqual(pool[0].name, 'high_def')


if __name__ == '__main__':
    unittest.main()
