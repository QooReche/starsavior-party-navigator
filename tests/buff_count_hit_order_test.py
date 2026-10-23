# -*- coding: utf-8 -*-
"""강화 개수·피격 중첩 경계: python -X utf8 -I tests/buff_count_hit_order_test.py"""
import copy
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.mc import Battle, Ctx, Eff, line_kind, positive_buff
from battlesim.metrics import unit_def
from battlesim.rules import MC_RULES
from battlesim.starsavior.foe import stage_waves


def battle(boss='웬디고', **rules):
    stage = ('equip', '혹한의 습격', '혹한의 습격 XⅧ') if boss == '웬디고' else ('clo', '달 회랑', 'FLOOR 355')
    _, waves = stage_waves(*stage)
    d = next(d for wave in waves for d in wave if d.name == boss)
    b = Battle([unit_def('gwen')], [[d]], random.Random(7), mc=rules)
    b.spawn_wave()
    return b, b.allies[0], b.foes[0]


def buff(u, name, stacks=1, harmful=False, fixed=False, check=False):
    e = Eff(name, {}, 99, float('inf'), u, harmful)
    e.stacks, e.fixed, e.check = stacks, fixed, check
    u.eff[name] = e
    return e


class BuffCountTest(unittest.TestCase):
    def test_table_flags_and_fallback(self):
        for name in ('전투의 열기', '탄력 가속', '별빛의 궤적-AX', '별빛의 궤적-CX', '별빛의 궤적-FX'):
            self.assertFalse(positive_buff(name, True), name)
            self.assertFalse(positive_buff(name + '(해제불가)', True), name)
        self.assertFalse(positive_buff('방어력 감소', True))  # IsBuff만으로 양성 판정하면 실패
        self.assertTrue(positive_buff('공격력 증가', False))
        for fallback in (True, False):
            self.assertEqual(positive_buff('파쇄', fallback), fallback)
            self.assertEqual(positive_buff('미등록 시험 효과', fallback), fallback)

    def test_wendigo_zero_one_two_boundary_both_modes(self):
        for mode in ('table', 'legacy'):
            b, a, foe = battle(buff_count_source=mode)
            ln = next(l for l in foe.d.lines if ('적 강화효과 보유', '예') in l.params)
            ctx = Ctx(foe, a, a.d.skills['기본기'])
            for count in range(3):
                with self.subTest(mode=mode, count=count):
                    a.eff.clear()
                    for name in ('공격력 증가', '방어력 증가')[:count]:
                        buff(a, name, stacks=5, fixed=True)
                    self.assertEqual(a.n_good(), count)  # 레벨 중첩·해제 불가와 무관
                    self.assertEqual(b.cond_ok(foe, ln, ctx), count <= 1)
                    buff(a, '전투의 열기', fixed=True)
                    self.assertEqual(a.n_good(), count + (mode == 'legacy'))
                    self.assertEqual(b.cond_ok(foe, ln, ctx), count + (mode == 'legacy') <= 1)

    def test_count_consumers_share_classification(self):
        for mode, count in (('table', 1), ('legacy', 2)):
            b, a, foe = battle(buff_count_source=mode)
            buff(a, '공격력 증가', fixed=True)
            buff(a, '전투의 열기')
            buff(a, '속도 증가', stacks=0)
            buff(a, '치명타 확률 증가', check=True)
            ctx = Ctx(a, a, a.d.skills['기본기'])
            ctx.target, ctx.targets = a, [a]
            self.assertEqual(b._count(a, ctx, ('SB', None)), count)
            self.assertEqual(b._count(foe, ctx, ('TB', None)), count)
            template = next(l for l in foe.d.lines if line_kind(l) == 'hit_self')
            for scope in ('self_good', 'target_good'):
                ln = copy.copy(template)
                ln.eff = dict(kind='count_damage', scope=scope, cap=10, val=10)
                ctx.inc = 0
                ctx.local_by[a].clear()
                b.exec_line(a, ln, ctx)
                got = ctx.inc if scope == 'self_good' else ctx.local_by[a]['inc']
                self.assertAlmostEqual(got, count * .1)
            b.mc['enemy_hit_buff_cmp'] = 'le_disp'
            self.assertEqual(a.n_good(dispellable=True), count - 1)

    def test_rule_metadata(self):
        from tools.build_simpack import files
        self.assertIn('data/buff_count.json', files())
        for key, value in (('buff_count_source', 'table'), ('hit_stack_order', 'apply_first')):
            self.assertEqual(MC_RULES[key]['value'], value)
            self.assertEqual(MC_RULES[key]['legacy'], 'legacy')
            for field in ('grade', 'note', 'source'):
                self.assertTrue(MC_RULES[key][field])


class HitOrderTest(unittest.TestCase):
    def test_wendigo_fifth_or_sixth_hit_and_reset(self):
        for mode, threshold in (('apply_first', 5), ('legacy', 6)):
            with self.subTest(mode=mode):
                b, a, foe = battle(hit_stack_order=mode)
                foe.cd['궁극기'] = 10
                ctx = Ctx(foe, a, a.d.skills['기본기'])
                for hit in range(1, threshold * 2 + 1):
                    b.fire(foe, 'hit_self', ctx)
                    self.assertEqual(foe.cd['궁극기'], 10 - hit // threshold)
                    self.assertEqual(foe.stack('끝 없는 냉기 분노'), min(hit % threshold, 5))

    def test_tuner_eleventh_or_twelfth_hit_consumes_before_extra(self):
        for mode, threshold in (('apply_first', 11), ('legacy', 12)):
            with self.subTest(mode=mode):
                b, a, foe = battle('공허조율자', hit_stack_order=mode)
                ctx = Ctx(foe, a, a.d.skills['기본기'])
                calls = []
                def cast(owner, skill, **kwargs):
                    calls.append((skill.slot, owner.stack('절망의 선율')))
                with patch.object(b, 'cast', side_effect=cast):
                    for hit in range(1, threshold * 2 + 1):
                        b.fire(foe, 'hit_self', ctx)
                        self.assertEqual(len(calls), hit // threshold)
                        self.assertEqual(foe.stack('절망의 선율'), min(hit % threshold, 11))
                self.assertEqual(calls, [('특수기', 0), ('특수기', 0)])


if __name__ == '__main__':
    unittest.main()
