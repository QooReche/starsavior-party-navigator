# -*- coding: utf-8 -*-
"""공략 사례집 의심 항목 고정 시험(docs/casebook_suspects_1121.md). 합성 유닛만 씀."""
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from simkit import battle, give, hit, unit5 as unit
from battlesim.metrics import unit_def


class DimensionalStrikeToughnessTest(unittest.TestCase):
    """차원 강습 영역(BATTLE_EFFECT 7205002 NST_SUPER_ARMOR_DAMAGE +1)과 상성.
    NKM:17206-17217: 불리면 스킬값·강인도 피해 스탯 모두 0, 동일·중립은 +스탯, 유리는 +1+스탯.
    오비탈 자기 타격은 SuperArmorBreakValue 없음·속성 NUAT_INVALID·스탯 0이라 어떤 속성에도 0."""

    def drop(self, ve):
        b = battle([unit('a', element='태양')], [unit('f', element=ve, hp=10 ** 9, sa=50)],
                   break_skill={'name': '차원 강습'}, mc={})
        a, f = b.allies[0], b.foes[0]
        skills = dict(a.d.skills)
        a.d.skills.clear()
        b.break_points = 3
        sa0 = f.sa
        b.act(a)                                   # 브레이크 스킬만 발동 → 영역
        a.d.skills.update(skills)
        self.assertEqual(f.sa, sa0, '오비탈 피해 자체는 강인도를 깎지 않음')
        self.assertTrue(a.has('CRF 증폭'))
        self.assertEqual(a.mods()['tough'], 1)
        _d, before, after = hit(b, a, f, ab=0)
        return before - after

    def test_domain_bonus_by_element(self):
        self.assertEqual(self.drop('달'), 0)       # 태양→달 불리: 영역 +1 도 0
        self.assertEqual(self.drop('태양'), 1)     # 동일: +1(영역)
        self.assertEqual(self.drop('별'), 2)       # 유리: +1(상성) +1(영역)


class AsherahBreakerIdentityTest(unittest.TestCase):
    """편애의 마녀: 추가 턴(52205 TargetSuperArmorBreak = 대상 강인도 -1, 이번 시전 중 격파)과
    연쇄 피해(2171·2172·52200 IsNotTargetSuperArmor = 현재 강인도 ≤0)는 누가 격파했는지에 따라 갈린다.
    NKM:10251(-1 판정), 15787-15827(SKILL_END 조건 → 시전 끝 -1→0), NKM:9483·9615(MyTurn)."""

    def run_case(self, case):
        b = battle([unit_def('asherah-order-striker'), unit('breaker')],
                   [unit('boss', hp=10 ** 9, sa=1)], opts={'coop': False, 'nova': False})
        a, other, foe = b.allies[0], b.allies[1], b.foes[0]
        foe.boss = True
        give(a, '파쇄', {'강인도 고정 피해': 1})
        if case == 'other_first':
            other.acting = True
            give(other, '고정', {'강인도 고정 피해': 1})
            b.cast(other, other.d.skills['기본기'], target=foe)
            other.acting = False
            self.assertTrue(foe.broken)
        a.acting = case != 'not_own_turn'
        seen = []
        original = b.apply_damage

        def record(src, dst, damage, kind, **kw):
            seen.append((kind, damage))
            return original(src, dst, damage, kind, **kw)
        with patch.object(b, 'apply_damage', record):
            b.cast(a, a.d.skills['기본기'], target=foe)
            b.flush_add_damage()
        return a.extra_turn, any(k == 'chain' and n > 0 for k, n in seen)

    def test_breaker_identity(self):
        self.assertEqual(self.run_case('self'), (True, True))
        self.assertEqual(self.run_case('other_first'), (False, True))   # 남이 깬 뒤: 연쇄만
        self.assertEqual(self.run_case('not_own_turn'), (False, False))  # 자기 턴 아님: 둘 다 없음


if __name__ == '__main__':
    unittest.main()
