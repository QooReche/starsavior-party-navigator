# -*- coding: utf-8 -*-
"""공격 시 해제(DC_ATTACK) 회귀: python -X utf8 -I tests/dispel_on_attack_test.py

게임 코드 NKM.decompiled.cs 15580: 공격 스킬의 타격×대상 루프가 끝난 뒤 공격자에게서 DC_ATTACK 효과를 해제, 반격·협공도 같은 공격 함수(15227·15485).
대상 = 여유로운 응수(9012, 반격 확률 +100%)·헥사 너트(16062). 규칙 mc.dispel_on_attack(off = 옛 동작)."""
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p3_test import battle, give, unit   # noqa: E402

AOE = [dict(slot='기본기', dm=100, all=True)]


class DispelOnAttackTest(unittest.TestCase):
    def setup(self, mc=None, n_foes=1, skills=None):
        b = battle([unit('a', hp=10 ** 7, skills=skills)], [unit('f%d' % i, hp=10 ** 7) for i in range(n_foes)], mc=mc)
        return b, b.allies[0]

    def test_removed_after_attack(self):
        b, a = self.setup()
        give(a, '헥사 너트', props={'치명타 피해': 30}, dur=999)
        give(a, '다른 강화', props={'공격력%': 10}, dur=999)
        b.act(a)
        self.assertNotIn('헥사 너트', a.eff)
        self.assertIn('다른 강화', a.eff)        # 이름에 없는 효과는 그대로

    def test_off_keeps_old_behavior(self):
        b, a = self.setup(mc={'dispel_on_attack': 'off'})
        give(a, '헥사 너트', props={'치명타 피해': 30}, dur=999)
        b.act(a)
        self.assertIn('헥사 너트', a.eff)

    def test_aoe_applies_to_every_target_then_removed(self):
        # 광역 공격: 버프는 모든 대상 타격에 적용되고(대상마다 지우지 않음) 공격이 끝난 뒤 한 번 지워진다
        b, a = self.setup(n_foes=3, skills=AOE)
        seen = []
        orig = b.strike

        def spy(att, v, *args, **kw):
            seen.append('헥사 너트' in att.eff)
            return orig(att, v, *args, **kw)
        b.strike = spy
        give(a, '헥사 너트', props={'치명타 피해': 30}, dur=999)
        b.act(a)
        self.assertEqual(seen, [True, True, True])
        self.assertNotIn('헥사 너트', a.eff)

    def test_counter_attack_removes_retort(self):
        # 응수(반격 확률 +100%)로 반격하면 그 반격이 공격이라 해제된다 — 다음 피격엔 반격 확률이 남지 않음
        b, a = self.setup()
        f = b.foes[0]
        give(f, '여유로운 응수', props={'반격 확률': 100}, dur=999)
        b.act(a)
        self.assertEqual(f.cast_count.get('기본기(추가)', 0), 1)
        self.assertNotIn('여유로운 응수', f.eff)

    def test_counter_keeps_retort_when_off(self):
        b, a = self.setup(mc={'dispel_on_attack': 'off'})
        f = b.foes[0]
        give(f, '여유로운 응수', props={'반격 확률': 100}, dur=999)
        b.act(a)
        a.cd = {}
        b.act(a)
        self.assertEqual(f.cast_count.get('기본기(추가)', 0), 2)
        self.assertIn('여유로운 응수', f.eff)

    def test_empty_attack_processes_dispel_before_own_post(self):
        # 실제 대상 선택 함수가 빈 목록을 돌려주는 단일·광역 공격을 직접 시전함.
        for aoe in (False, True):
            for mode, dispel, removed in (('process', 'on', True), ('skip', 'on', False), ('process', 'off', False)):
                for via in (None, 'revenge', 'coop', 'enforce'):
                    with self.subTest(aoe=aoe, mode=mode, dispel=dispel, via=via):
                        b, a = self.setup(mc={'empty_attack': mode, 'dispel_on_attack': dispel},
                                          skills=[dict(slot='기본기', dm=100, all=aoe)])
                        b.foes[0].dead, b.foes[0].hp = True, 0
                        for name in ('헥사 너트', '여유로운 응수', '다른 강화'):
                            give(a, name, dur=999)
                        seen = []
                        orig = b.run_own
                        def spy(owner, ctx, kind):
                            if kind == 'own_post':
                                seen.append('헥사 너트' in owner.eff)
                            return orig(owner, ctx, kind)
                        with patch.object(b, 'run_own', side_effect=spy), patch.object(b, 'deal', wraps=b.deal) as deal:
                            ctx = b.cast(a, a.d.skills['기본기'], extra=via is not None, via=via)
                        self.assertEqual(ctx.targets, [])
                        self.assertEqual(ctx.hit_targets, [])
                        self.assertEqual(deal.call_count, int(mode == 'process'))
                        self.assertEqual(a.cast_count['기본기(추가)' if via else '기본기'], 1)
                        self.assertEqual(a.dmg, 0)
                        self.assertEqual(seen, [not removed])
                        for name in ('헥사 너트', '여유로운 응수'):
                            self.assertEqual(name in a.eff, not removed)
                        self.assertIn('다른 강화', a.eff)

    def test_default_empty_attack_and_cancelled_cast(self):
        b, a = self.setup()
        b.foes[0].dead, b.foes[0].hp = True, 0
        give(a, '헥사 너트', dur=999)
        give(a, '기절', harmful=True)
        self.assertIsNone(b.cast(a, a.d.skills['기본기']))
        self.assertIn('헥사 너트', a.eff)
        self.assertEqual(sum(a.cast_count.values()), 0)
        del a.eff['기절']
        b.cast(a, a.d.skills['기본기'])
        self.assertNotIn('헥사 너트', a.eff)

    def test_nonattack_without_targets_preserves_effect(self):
        b, a = self.setup(skills=[dict(slot='특수기', dm=0, tg='적 전체')])
        b.foes[0].dead, b.foes[0].hp = True, 0
        give(a, '헥사 너트', dur=999)
        sk = a.d.skills['특수기']
        self.assertFalse(sk.is_attack)
        ctx = b.cast(a, sk)
        self.assertEqual(ctx.targets, [])
        self.assertEqual(a.cast_count['특수기'], 1)
        self.assertIn('헥사 너트', a.eff)


if __name__ == '__main__':
    unittest.main(verbosity=1)
