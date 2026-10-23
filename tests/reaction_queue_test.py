# -*- coding: utf-8 -*-
"""반응 스킬 대기열(mc.reaction_timing)·버프 생명력%의 최대 생명력 반영(mc.buff_maxhp) 회귀:
python -X utf8 -I tests/reaction_queue_test.py

게임 순서(NKM.decompiled.cs 15180~15372): 본 행동 → 협공 → 그 타격의 반격 → 예약된 반응 스킬(각각 직후 반격), 최대 11개.
최대 생명력 = floor(전투 전 최종값 x (1 + 버프 생명력%)), 줄면 자르고 전투 중엔 안 채움(2828~2839)."""
import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import FIXED, battle, give, unit   # noqa: E402
from battlesim.mc import Battle, Ctx   # noqa: E402
from battlesim.metrics import unit_def   # noqa: E402


class ReactionQueueTest(unittest.TestCase):
    def setup(self, timing='queue', guard_atk=1):
        # 루나 「썸머 템테이션♡」: 자신 제외 아군이 치명타 피격 후 타격자에게 발동. 피격 아군은 반격 100%
        d = unit_def('white-pearl-luna')
        b = battle([d, unit('guard', hp=10 ** 7, atk=guard_atk)],
                   [unit('attacker', hp=10 ** 6, cr=10000, skills=[dict(slot='기본기', dm=100)])],
                   mc=dict(toughness='off', reaction_timing=timing), opts={'coop': False, 'nova': False})
        luna, guard = b.allies
        foe = b.foes[0]
        b.fire(luna, 'battle_start', Ctx(luna, luna, None))
        luna.cd['특수기'] = 0
        give(guard, '반격 증가', {'반격 확률': 100}, dur=9)
        b.pick_attack_target = lambda u, sk=None: guard if u is foe else foe
        b.roll_hit = lambda owner, ctx, x, name: True
        order = []
        cast = b.cast

        def rec(u, sk, *a, **kw):
            order.append((u.name, kw.get('via'), b.depth))
            return cast(u, sk, *a, **kw)
        b.cast = rec
        return b, luna, guard, foe, order

    def test_order_main_revenge_reaction(self):
        b, luna, guard, foe, order = self.setup()
        b.act(foe)
        vias = [(n, v) for n, v, _ in order]
        self.assertEqual(vias, [(foe.name, None), (guard.name, 'revenge'), (luna.name, 'reaction')])
        self.assertEqual(order[-1][2], 0)        # 반응은 본 시전 밖(중첩 아님)

    def test_nested_legacy(self):
        b, luna, guard, foe, order = self.setup(timing='nested')
        b.act(foe)
        vias = [(n, v) for n, v, _ in order]
        self.assertEqual(vias, [(foe.name, None), (luna.name, 'reaction'), (guard.name, 'revenge')])
        self.assertEqual(order[1][2], 1)          # 옛 동작: 본 시전 안에서 바로

    def test_dead_target_misfires_and_clears_reservation(self):
        b, luna, guard, foe, order = self.setup(guard_atk=10 ** 7)   # 반격이 공격자를 쓰러뜨림
        b.act(foe)
        self.assertTrue(foe.dead)
        self.assertNotIn((luna.name, 'reaction'), [(n, v) for n, v, _ in order])
        self.assertEqual(luna.cd['특수기'], 0)    # 불발이라 쿨도 안 돌았음

    def test_misfire_clears_reservation_for_rereserve(self):
        b, luna, guard, foe, order = self.setup()
        ts = luna.d.trigger_skills['특수기']
        b._react_q, b._react_seen, b._revenged, b._hit_log = [], set(), set(), None
        b._react(luna, ts, foe)
        foe_backup = foe.dead
        foe.dead = True                      # 대상이 쓰러져 불발 — 다른 적은 살아 있어 루프는 계속
        b.foes.append(b.foes[0].__class__(unit('other', hp=10 ** 6), 1, 1, b))
        b._run_reactions()
        self.assertNotIn((id(luna), ts.slot), b._react_seen)   # 이력이 지워져 다시 예약 가능
        b._react(luna, ts, b.foes[-1])
        self.assertEqual(len(b._react_q), 1)
        foe.dead = foe_backup
        b._react_q = b._react_seen = b._revenged = None

    def test_queue_closed_after_action(self):
        b, luna, guard, foe, order = self.setup()
        b.act(foe)
        self.assertIsNone(b._react_q)        # 행동 밖(다음 웨이브·추가 턴 사이)으로 대기열이 새지 않음
        self.assertIsNone(b._revenged)

    def test_reaction_cap_11(self):
        b, luna, guard, foe, order = self.setup()
        ts = luna.d.trigger_skills['특수기']
        calls = []
        b.trigger_cast = lambda owner, sk, target=None, **kw: calls.append(1) or Ctx(owner, owner, sk)
        b._react_q, b._react_seen, b._revenged, b._hit_log = [(luna, ts, foe, None)] * 15, set(), set(), None
        b._run_reactions()
        self.assertEqual(len(calls), 11)
        self.assertEqual(b.unsup['reaction: 한 행동 반응 스킬 11개 초과로 나머지 생략'], 1)

    def test_one_reservation_per_unit_slot(self):
        b, luna, guard, foe, order = self.setup()
        ts = luna.d.trigger_skills['특수기']
        b._react_q, b._react_seen = [], set()
        b._react(luna, ts, foe)
        b._react(luna, ts, foe)
        self.assertEqual(len(b._react_q), 1)
        b._react_q = b._react_seen = None


def apply(b, u, *a, **kw):
    """엔진처럼 효과를 건 뒤 dirty(현재 생명력 자르기 포함)"""
    e = give(u, *a, **kw)
    b.dirty(u)
    return e


class BuffMaxHpTest(unittest.TestCase):
    def test_debuff_clamps_buff_does_not_fill(self):
        b = battle([unit('a', hp=10000)], [unit('boss', hp=10 ** 9)])
        a = b.allies[0]
        apply(b, a, '영혼 구속', {'생명력%': -15}, harmful=True)
        self.assertEqual((a.hp, a.maxhp), (8500.0, 8500.0))
        del a.eff['영혼 구속']
        b.dirty(a)
        apply(b, a, '생명 강화', {'생명력%': 20})
        self.assertEqual((a.hp, a.maxhp), (8500.0, 12000.0))   # 전투 중엔 늘어도 안 채움

    def test_maxhp_read_has_no_side_effect(self):
        # codex 리뷰: 조회가 생명력을 바꾸면 hp/maxhp 읽는 순서에 따라 비율이 달라진다
        b = battle([unit('a', hp=10000), unit('b', hp=10000)], [unit('boss', hp=10 ** 9)])
        a, c = b.allies
        c.hp = 9000.0
        apply(b, a, '영혼 구속', {'생명력%': -15}, harmful=True)
        before = a.hp
        _ = a.maxhp
        self.assertEqual(a.hp, before)
        got = b._filter(c, [a, c], 'high_hp_rate')
        self.assertEqual([x.name for x in got], ['a'])           # a = 100%, c = 90%

    def test_start_reduction_clamps(self):
        f = unit('boss', hp=10 ** 9, atk=1)
        b = Battle([unit('a', hp=10000)], [[f]], random.Random(1), mc=dict(FIXED), max_turns=0.001)
        apply(b, b.allies[0], '영혼 구속', {'생명력%': -15}, harmful=True)
        b.run()
        self.assertEqual((b.allies[0].hp, b.allies[0].maxhp), (8500.0, 8500.0))

    def test_battle_start_fills(self):
        f = unit('boss', hp=10 ** 9, atk=1)
        b = Battle([unit('a', hp=10000)], [[f]], random.Random(1), mc=dict(FIXED), max_turns=0.001)
        apply(b, b.allies[0], '생명 강화', {'생명력%': 20})
        b.run()
        self.assertEqual(b.allies[0].hp, 12000.0)          # 전투 시작 단계는 채움

    def test_hp_scaling_uses_max(self):
        b = battle([unit('a', hp=10000)], [unit('boss', hp=10 ** 9)])
        a = b.allies[0]
        apply(b, a, '영혼 구속', {'생명력%': -15}, harmful=True)
        sk = a.d.skills['기본기']
        sk.cf = [0, 10000, 0, 0]
        v = b.foes[0]
        v.d.stats['def'] = 0
        ctx = Ctx(a, a, sk)
        ctx.targets = [v]
        b.deal(a, ctx)
        on = v.taken
        b2 = battle([unit('a', hp=8500)], [unit('boss', hp=10 ** 9)])
        a2 = b2.allies[0]
        sk2 = a2.d.skills['기본기']
        sk2.cf = [0, 10000, 0, 0]
        b2.foes[0].d.stats['def'] = 0
        ctx2 = Ctx(a2, a2, sk2)
        ctx2.targets = [b2.foes[0]]
        b2.deal(a2, ctx2)
        self.assertEqual(on, b2.foes[0].taken)              # 최대 생명력 8,500 과 같은 생명력 항

    def test_off_switch(self):
        b = battle([unit('a', hp=10000)], [unit('boss', hp=10 ** 9)], mc=dict(buff_maxhp='off'))
        a = b.allies[0]
        apply(b, a, '영혼 구속', {'생명력%': -15}, harmful=True)
        self.assertEqual((a.hp, a.maxhp), (10000.0, 10000.0))

    def test_floor_minus_99(self):
        b = battle([unit('a', hp=10000)], [unit('boss', hp=10 ** 9)])
        a = b.allies[0]
        apply(b, a, 'x', {'생명력%': -150}, harmful=True)
        self.assertEqual(a.maxhp, float(math.floor(10000 * 0.01)))


if __name__ == '__main__':
    unittest.main()
