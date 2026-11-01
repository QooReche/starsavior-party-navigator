# -*- coding: utf-8 -*-
"""적 전용 효과 회귀: python -X utf8 -I tests/enemy_effects_test.py

〈특수기 쿨타임 초기화〉(어둠의 맹세, NKM 2874~2886)·〈즉시 피해〉 자폭(mc.instant_damage, NKM 4794~4822)·
〈별도 사망 애니메이션 트리거 버프〉(연출용 무시)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, unit   # noqa: E402
from battlesim.mc import Ctx, support_report   # noqa: E402
from battlesim.starsavior.parser import Line   # noqa: E402

RESET = '[사망 시] (조건: 아군 사망 시) 자신에게 〈특수기 쿨타임 초기화〉'
BOMB = '[스킬 사용 후] 자신에게 〈즉시 피해〉'
ANIM = '[스킬 사용 후] 자신에게 〈별도 사망 애니메이션 트리거 버프〉 (1턴) {해제 불가}'


class EnemyEffectsTest(unittest.TestCase):
    def setup(self, mc=None):
        sk = [dict(slot='기본기', dm=100), dict(slot='특수기', dm=100, cd=4)]
        b = battle([unit('a', hp=10 ** 7)], [unit('watch', hp=10 ** 6, skills=sk), unit('mob', hp=10 ** 6)], mc=mc)
        return b, b.foes[0], b.foes[1]

    def fire_line(self, b, owner, raw, slot='특수기'):
        ln = Line(raw, slot, 'active')
        b._cur_line = ln
        b.run_line(owner, ln, Ctx(owner, owner, None))

    def test_special_cd_reset_on_ally_death(self):
        b, watch, mob = self.setup()
        watch.cd['특수기'] = 4
        watch.d.lines.append(Line(RESET, '고유 패시브', 'passive'))
        b._semantic_lines.clear()
        b.kill(mob, b.allies[0])
        self.assertEqual(watch.cd['특수기'], 0)
        self.assertEqual(watch.n_good(), 0)          # 이름뿐인 강화 효과로 남지 않음

    def test_instant_damage_self_kill(self):
        b, watch, mob = self.setup()
        self.fire_line(b, watch, BOMB)
        self.assertTrue(watch.dead)
        self.assertFalse(mob.dead)

    def test_instant_damage_blocked(self):
        """damage(기본) = 클라 DAMAGE_INSTANT: 무적·스킬 피해 무효·보호막·불사를 거침 / self_kill 은 무시하고 사망"""
        from p3_test import give
        for name, props, alive in (('무적', {}, True), ('스킬 피해 무효', {}, True), ('불사', {}, True)):
            b, watch, mob = self.setup()
            give(watch, name, props)
            self.fire_line(b, watch, BOMB)
            self.assertEqual(not watch.dead, alive, name)
            if name == '스킬 피해 무효':
                self.assertNotIn(name, watch.eff)       # 1회 소모
            if name == '불사':
                self.assertEqual(watch.hp, 1.0)
            b, watch, mob = self.setup(mc=dict(instant_damage='self_kill'))
            give(watch, name, props)
            self.fire_line(b, watch, BOMB)
            self.assertTrue(watch.dead, name + ' (self_kill)')
        # 보호막: 생명력 10배 + 공격력 넘게 막으면 생존, 모자라면 사망
        b, watch, mob = self.setup()
        give(watch, '보호막').shield = 10 ** 8
        self.fire_line(b, watch, BOMB)
        self.assertFalse(watch.dead)
        self.assertEqual(watch.hp, 10 ** 6)
        b, watch, mob = self.setup()
        give(watch, '보호막').shield = 10 ** 6
        self.fire_line(b, watch, BOMB)
        self.assertTrue(watch.dead)
        self.assertEqual(watch.dmg, 0.0)                # 자기 피해는 적 피해 집계에서 뺌

    def test_invincible_blocks_all(self):
        """〈무적〉: 일반 타격·지속 피해·연쇄 피해 모두 0, 무효화보다 먼저(무효화 소모 안 됨)"""
        from p3_test import give
        b, watch, mob = self.setup()
        give(watch, '무적')
        for kind, sh in (('hit', True), ('dot', False), ('chain', True), ('bskill', True)):
            self.assertFalse(b.apply_damage(b.allies[0], watch, 10 ** 9, kind, shieldable=sh))
        self.assertEqual(watch.hp, 10 ** 6)
        give(watch, '스킬 피해 무효')
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.targets = [watch]
        b.deal(a, ctx)
        self.assertEqual(watch.hp, 10 ** 6)
        self.assertIn('스킬 피해 무효', watch.eff)
        del watch.eff['무적']
        watch._m = None
        b.deal(a, ctx)
        self.assertNotIn('스킬 피해 무효', watch.eff)

    def test_instant_damage_off_legacy(self):
        b, watch, mob = self.setup(mc=dict(instant_damage='off'))
        self.fire_line(b, watch, BOMB)
        self.assertFalse(watch.dead)

    def test_anim_buff_ignored(self):
        b, watch, mob = self.setup()
        self.fire_line(b, watch, ANIM)
        self.assertEqual(watch.eff, {})

    def test_static_report_clean(self):
        d = unit('x', skills=[dict(slot='기본기', dm=100)])
        for raw in (RESET, BOMB, ANIM):
            d.lines.append(Line(raw, '기본기', 'active'))
        rep = support_report([d])
        flat = repr(rep)
        for name in ('특수기 쿨타임 초기화', '즉시 피해', '별도 사망 애니메이션'):
            self.assertNotIn('의미 미해석 효과 〈' + name, flat)


if __name__ == '__main__':
    unittest.main()
