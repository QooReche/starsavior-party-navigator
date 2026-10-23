# -*- coding: utf-8 -*-
"""적 자동 대상 규칙 회귀(data/foe_auto.json, mc.foe_auto): python -X utf8 -I tests/foe_auto_test.py

게임 코드 NKM.decompiled.cs 6390~6450(효과 줄 자동 대상: 단일이면 1명, 아니면 맞는 필터가 있을 때만 그 목록)·6454~6620(스킬 규칙 행)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p3_test import battle, give, unit   # noqa: E402
from battlesim.mc import Ctx   # noqa: E402
from battlesim.starsavior.foe import FoeDef, load_foe   # noqa: E402

RAW = load_foe()


def foe_named(name, with_lines=False, with_skills=False):
    for ui, u in enumerate(RAW['u']):
        if u['n'] != name:
            continue
        for xi in [None] + list(range(len(RAW['x']))):
            try:
                d = FoeDef(RAW, ui, xi)
            except Exception:
                continue
            if (not with_lines or d.auto_lines) and (not with_skills or d.auto):
                return d
    raise AssertionError('규칙 있는 ' + name + ' 없음')


class FoeAutoTest(unittest.TestCase):
    def wendigo_battle(self, mc=None):
        d = foe_named('웬디고', with_lines=True)
        b = battle([unit('a%d' % i, hp=10 ** 6) for i in range(4)], [d], mc=mc)
        foe = b.foes[0]
        lines = [ln for ln in foe.d.lines if (ln.slot, ln.raw) in foe.d.auto_lines]
        self.assertEqual(len(lines), 2)
        lines.sort(key=lambda ln: '25%' in ln.raw)   # 15%(강화 2개 이상) -> 25%(1개 이하)
        return b, foe, lines

    def targets(self, b, foe, ln):
        b._cur_line = ln
        try:
            return b.resolve(foe, '적(자동 지정)', Ctx(foe, foe, foe.d.skills['궁극기']), kind='damage')
        finally:
            b._cur_line = None

    def test_wendigo_chain_by_buff_count(self):
        b, foe, (l15, l25) = self.wendigo_battle()
        a = b.allies
        for x in a[:2]:
            give(x, '공격력 증가', props={'공격력%': 10})
            give(x, '방어력 증가', props={'방어력%': 10})
        give(a[2], '공격력 증가', props={'공격력%': 10})
        self.assertEqual(set(self.targets(b, foe, l15)), {a[0], a[1]})
        self.assertEqual(set(self.targets(b, foe, l25)), {a[2], a[3]})
        for x in a:                      # 강화 2개 이상인 적이 없으면 15% 줄은 대상 없음(전체형 + 맞는 필터 없음)
            x.eff.clear()
            x._m = None
        self.assertEqual(self.targets(b, foe, l15), [])
        self.assertEqual(len(self.targets(b, foe, l25)), 4)

    def test_wendigo_off_keeps_old_choice(self):
        b, foe, (l15, _) = self.wendigo_battle(mc=dict(foe_auto='off'))
        self.assertEqual(len(self.targets(b, foe, l15)), 1)   # 옛 동작: 첫 대상/공격자/기본 규칙 1명

    def test_witness_coffin_targets_brand(self):
        d = foe_named('공허목도자', with_skills=True)
        b = battle([unit('a%d' % i, hp=10 ** 6) for i in range(4)], [d])
        foe = b.foes[0]
        foe.cd = {}
        give(b.allies[3], '낙인', harmful=True, dur=5)
        for _ in range(30):
            sk, tgt = b.choose_skill(foe)
            self.assertIn(sk.slot, foe.d.auto)
            self.assertIs(tgt, b.allies[3])

    def test_single_line_random_one(self):
        b = battle([unit('a%d' % i) for i in range(4)], [unit('foe')])
        foe = b.foes[0]
        spec = {'one': True, 'f': [['has', ['없는 효과']]]}
        got = {self.single(b, foe, spec) for _ in range(200)}
        self.assertEqual(len(got), 4)      # 맞는 필터가 없어도 단일형은 무작위 1명
        give(b.allies[1], '낙인', harmful=True)
        spec = {'one': True, 'f': [['has', ['낙인']], 'high_atk']}
        self.assertEqual({self.single(b, foe, spec) for _ in range(50)}, {b.allies[1]})

    def test_last_damager_recorded_even_if_nullified(self):
        b = battle([unit('A'), unit('B')], [unit('foe', hp=10 ** 7)])
        foe = b.foes[0]
        A, B = b.allies
        b.cast(A, A.d.skills['기본기'], target=foe)
        self.assertIs(foe.last_damager, A)
        t0 = foe.taken
        give(foe, '스킬 피해 무효', dur=50)   # 다음 스킬 1회 피해 0
        b.cast(B, B.d.skills['기본기'], target=foe)
        self.assertEqual(foe.taken, t0)
        self.assertIs(foe.last_damager, B)

    def test_pairing_rejects_any_target_kind_mismatch(self):
        from tools.build_foe_auto import pair_lines
        auto = {'m_BuffTargetType': 'NSETT_AUTO_ENEMY', 'AutoTargetId': 17}
        ok = pair_lines(['[스킬 사용 후] 자신에게 〈X〉', '[스킬 사용 후] 적(자동 지정)에게 〈Y〉'], [{'m_BuffTargetType': 'NSETT_SELF'}, auto])
        self.assertIsNotNone(ok)
        bad = pair_lines(['[스킬 사용 후] 자신에게 〈X〉', '[스킬 사용 후] 적(자동 지정)에게 〈Y〉'], [{'m_BuffTargetType': 'NSETT_ENEMY_ALL'}, auto])
        self.assertIsNone(bad)
        self.assertIsNone(pair_lines(['[스킬 사용 후] 자신에게 〈X〉'], [{'m_BuffTargetType': 'NSETT_SELF'}, auto]))   # 줄 수 다름
        self.assertIsNone(pair_lines(['[스킬 사용 후] 스킬 대상에게 〈X〉', '[스킬 사용 후] 적(자동 지정)에게 〈Y〉'],
                                     [{'m_BuffTargetType': 'NSETT_SELF'}, auto]))
        self.assertIsNone(pair_lines(['[스킬 사용 후] 행동 게이지 증가', '[스킬 사용 후] 적(자동 지정)에게 〈Y〉'],
                                     [{'m_BuffTargetType': 'NSETT_SELF'}, auto]))   # 대상 머리말을 못 읽는 줄

    def single(self, b, foe, spec):
        out = b.line_auto_targets(foe, spec, None)
        self.assertEqual(len(out), 1)
        return out[0]


if __name__ == '__main__':
    unittest.main()
