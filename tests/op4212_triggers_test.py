"""PC 26752678: 발동형 효과 세부 동작(작전 42-12 조건부 효과 전수 대조, docs/op4212_triggers_1121.md).

1. SE 재발동 제한(SeCoolTurn, «발동 후 N턴 재발동 불가»)은 주인의 자기 턴 종료마다 1 줄어든다
   (NKM:16496-16538 조건 통과 때 OBF_31057 로 N 저장, 3532-3560 판정, 3604-3617 OBF_15627 차감, 2013-2021·13957-13966 턴 유닛 TURN_END).
2. 강화/약화 해제 후보는 표의 IsBuff 가 참인 것만(NKM:4229-4253 OBF_15506, NKM.Templets:40597-40618).
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit
from battlesim.mc import Battle, Ctx, buff_kind
from battlesim.rules import MC_OPTS
from battlesim.starsavior.parser import Line

# 프로페서M 잠재력 〈날렵한 자세〉(POTEN_PASSIVE_3200301, SeCoolTurn 1)
AGILE = ('[스킬 사용 후] (조건: 내 공격 후 [사용 스킬: 특수기; 단일 대상 공격: 예]) 자신에게 행동 게이지 20%p 증가 '
         '{발동 후 1턴 재발동 불가}')


class SeCoolClockTest(unittest.TestCase):
    def setup(self, mc=None):
        b = battle([unit('m'), unit('x')], [unit('boss')], mc=mc)
        m = b.allies[0]
        ln = Line(AGILE, '잠재력', 'passive')
        ctx = Ctx(m, m, None)
        return b, m, ln, ctx

    def ok(self, b, m, ln, ctx):
        # 조건(특수기·단일 대상)은 이 시험의 대상이 아니므로 통과로 둔다.
        with patch.object(Battle, 'cond_ok', lambda *a, **k: True):
            return b.line_ok(m, ln, ctx)

    def test_default_is_client(self):
        self.assertEqual(MC_OPTS['se_cool_clock'], 'client')

    def test_fired_between_turns_blocks_through_next_own_turn(self):
        b, m, ln, ctx = self.setup()
        self.assertTrue(self.ok(b, m, ln, ctx))      # 남의 턴에 발동
        self.assertFalse(self.ok(b, m, ln, ctx))
        m.actions += 1                               # 주인의 다음 자기 턴 시작: 아직 막힘(쿨 1이 남음)
        self.assertFalse(self.ok(b, m, ln, ctx))
        self.assertGreater(b.rule_hits['se_cool_clock'], 0)
        m.turn_ends += 1                             # 그 턴 종료에 0
        self.assertTrue(self.ok(b, m, ln, ctx))

    def test_fired_in_own_turn_frees_at_turn_end(self):
        b, m, ln, ctx = self.setup()
        m.actions = 1                                # 자기 턴 중 발동
        self.assertTrue(self.ok(b, m, ln, ctx))
        self.assertFalse(self.ok(b, m, ln, ctx))
        m.turn_ends += 1                             # 같은 턴 종료 뒤(다음 자기 턴 전) 다시 걸림
        self.assertTrue(self.ok(b, m, ln, ctx))

    def test_legacy_uses_action_starts(self):
        b, m, ln, ctx = self.setup(mc={'se_cool_clock': 'legacy'})
        self.assertTrue(self.ok(b, m, ln, ctx))
        m.turn_ends += 1
        self.assertFalse(self.ok(b, m, ln, ctx))
        m.actions += 1
        self.assertTrue(self.ok(b, m, ln, ctx))

    def test_turn_end_counter_advances(self):
        b, m, _, _ = self.setup()
        self.assertEqual(m.turn_ends, 0)
        b.act(m)
        self.assertEqual(m.turn_ends, 1)
        self.assertEqual(b.allies[1].turn_ends, 0)


COOP = '[턴 시작 시] 자신에게 〈협공 확률 20% 증가 (C)〉 (지속 무한 / 협공 확률 +20%) {최대 5중첩}'
RESIST = '[스킬 사용 후] 자신에게 〈효과 저항 증가〉 (2턴 / 효과 저항 +30%)'
DISPEL_ALL = '[스킬 사용 후] 적 전체에게 (대상마다 100% 판정) 〈버프 해제〉 (강화효과 해제)'
DISPEL_ONE = '[스킬 사용 후] 적 전체에게 (강화효과 해제) 효과 1개 해제'


class DispelIsBuffTest(unittest.TestCase):
    def setup(self, mc=None, order=(COOP, RESIST)):
        b = battle([unit('w')], [unit('boss')], mc=mc)
        w, boss = b.allies[0], b.foes[0]
        for raw in order:
            b.run_line(w, Line(raw, '고유 패시브', 'passive'), Ctx(w, w, None))
        self.assertTrue(w.has('협공 확률 20% 증가 (C)') and w.has('효과 저항 증가'))
        return b, w, boss

    def test_table(self):
        self.assertEqual(MC_OPTS['dispel_isbuff'], 'client')
        self.assertEqual(buff_kind('협공 확률 20% 증가 (C)'), (False, True))
        self.assertEqual(buff_kind('효과 저항 증가'), (True, True))

    def test_dispel_all_skips_non_isbuff(self):
        b, w, boss = self.setup()
        b.run_line(boss, Line(DISPEL_ALL, '궁극기', 'active'), Ctx(boss, boss, None))
        self.assertFalse(w.has('효과 저항 증가'))
        self.assertTrue(w.has('협공 확률 20% 증가 (C)'))
        self.assertGreater(b.rule_hits['dispel_isbuff'], 0)

    def test_dispel_one_not_spent_on_non_isbuff(self):
        b, w, boss = self.setup()
        b.run_line(boss, Line(DISPEL_ONE, '기본기', 'active'), Ctx(boss, boss, None))
        self.assertFalse(w.has('효과 저항 증가'))
        self.assertTrue(w.has('협공 확률 20% 증가 (C)'))

    def test_legacy_removes_both(self):
        b, w, boss = self.setup(mc={'dispel_isbuff': 'legacy'})
        b.run_line(boss, Line(DISPEL_ALL, '궁극기', 'active'), Ctx(boss, boss, None))
        self.assertFalse(w.has('효과 저항 증가'))
        self.assertFalse(w.has('협공 확률 20% 증가 (C)'))


if __name__ == '__main__':
    unittest.main()
