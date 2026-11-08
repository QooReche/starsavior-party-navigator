# -*- coding: utf-8 -*-
"""전체 턴 시계(GlobalTurnCounting) 판정 회귀: python -X utf8 -I tests/buff_clock_test.py

2026-11-08: 작전(어려움) 13-10 공허감응자의 «2회 피격 카운팅용/금지용 버프»·«규제» 는 표에서 GlobalTurnCounting=true 인데
엔진이 효과 설명문의 문구만 봐서 보스 자기 턴 기준으로 처리했다 -> 연쇄 피해가 판당 5.5회로 부풀고 규제 50% 감소가 보스 턴까지 이어졌다.
클라는 모든 행동이 끝날 때마다 전원이 차감하고 걸린 행동도 차감한다(NKM:3973-3983, 13546, 4571).
규칙 any_turn_source: table(새 기본) / text(옛 동작)."""
import collections
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests'), os.path.join(ROOT, 'tools')]
from p3_test import battle, unit   # noqa: E402
from battlesim.starsavior import foe as F   # noqa: E402

DATA = os.path.join(ROOT, 'data', 'buff_global_turn.json')
COUNTING = ['2회 피격 카운팅용 버프', '2회 피격 카운팅 금지용 버프', '3회 피격 카운팅용 버프', '규제']


class GlobalTurnClockTest(unittest.TestCase):
    def owner(self, mc=None):
        b = battle([unit('a')], [unit('boss', boss=True)], mc=mc)
        return b, b.all_foes[0]

    def test_table_names_are_any_turn_by_default(self):
        b, boss = self.owner()
        for name in COUNTING + ['규제', '아군 턴 카운팅 버프', '영양 과잉', '몰락한 사념(해제불가)']:
            self.assertTrue(b._is_any_turn(boss, name), name)

    def test_legacy_text_misses_the_nine(self):
        b, boss = self.owner(dict(any_turn_source='text'))
        for name in COUNTING:
            self.assertFalse(b._is_any_turn(boss, name), name)
        self.assertTrue(b._is_any_turn(boss, '불협화음(해제불가)'))      # 설명문 문구가 있는 것은 옛 동작에서도 전체 턴

    def test_own_turn_buffs_stay_own_turn(self):
        b, boss = self.owner()
        for name in ['금제·계(해제불가)', '금제·갑(해제불가)', '없는 이름']:        # 표에서 GlobalTurnCounting=false(혼재 이름도 제외)
            self.assertFalse(b._is_any_turn(boss, name), name)

    def test_data_superset_of_text_rule(self):
        """설명문 기준으로 전체 턴인 효과는 표 기준에도 모두 들어 있다(표가 더 넓은 쪽)."""
        names = set(json.load(open(DATA, encoding='utf-8')))
        text = {n for n, i in F.gloss().items() if i.get('clock') == 'any_turn'}
        self.assertTrue(text <= {n for n in names} | {n + '(해제불가)' for n in names}, sorted(text - names))
        self.assertGreaterEqual(len(names), 15)

    def test_suffixed_names_match_table_path(self):
        """표 이름의 «(해제불가)» 꼬리표가 있어도 표 경로로 맞는다(설명문 사전과 무관하게; 리뷰 지적 2026-11-08)."""
        from battlesim import mc
        for name in ['몰락한 사념(해제불가)', '몰락한 사념', '메이드의 블로킹(해제불가)', '혼의 균열(해제불가)', '불협화음(해제불가)']:
            self.assertTrue(mc.global_turn_buff(name), name)
        self.assertFalse(mc.global_turn_buff('금제·계(해제불가)'))

    def test_counting_buff_expires_with_the_action_that_applied_it(self):
        """실제 부여 경로(add_effect): 아군 행동 중 보스에 걸린 규제·2회 피격 카운팅 버프는 그 행동이 끝나면 사라진다(보스 자기 턴까지 남지 않음).
        text 규칙(옛 동작)에서는 보스 자기 턴까지 남는다."""
        for src, expect_after_ally in (('table', False), ('text', True)):
            b = battle([unit('slow', spd=100), unit('other', spd=100)], [unit('foe', hp=10 ** 8, boss=True, spd=1)],
                       mc=dict(toughness='off', any_turn_source=src), opts={'coop': False, 'nova': False})
            slow, other = b.allies
            foe = b.foes[0]
            for name in ('규제', '2회 피격 카운팅용 버프'):
                b.add_effect(foe, foe, dict(name=name, props={'피해 감소': 50.0}, max=1, dur=1, times=1), None)
                self.assertEqual(foe.eff[name].clock == 'any_turn', src == 'table', (src, name))
            b.act(other)          # 보스는 움직이지 않고 아군만 한 번 행동
            for name in ('규제', '2회 피격 카운팅용 버프'):
                self.assertEqual(name in foe.eff, expect_after_ally, (src, name, '아군 행동 뒤'))

    def test_real_boss_chain_count_drops(self):
        """13-10 보스: 새 기본이 옛 동작보다 보스 연쇄 발동이 적다(진행도>0 인 실제 전투 경로, 같은 난수열)."""
        from battlesim import api, quick
        import gen_quick_calib as G
        q, _ = quick.load(ROOT)
        st = q['st']['oph']['플로라|SECTOR 13-10']
        order = ['emily', 'fei', 'professor-m', 'wedding-carmen']
        p = G.party_spec(q, order, 'fei', order, 1.0, st)       # 표준 육성 100%: 보스에 닿는 진행도(약 0.4), 클리어 5% 안팎
        count = collections.Counter()
        orig, orig_strike = api.Battle.chain, api.Battle.strike

        def chain(self, owner, eff, ctx):
            if getattr(owner.d, 'boss', False):
                count['chain'] += 1
            return orig(self, owner, eff, ctx)

        def strike(self, a, v, *args, **kw):
            if getattr(v.d, 'boss', False) and a.side == 0:
                count['hit'] += 1
            return orig_strike(self, a, v, *args, **kw)
        api.Battle.chain, api.Battle.strike = chain, strike
        try:
            out = {}
            for src in ('table', 'text'):
                count.clear()
                r = api.simulate(p, {'stage': 'oph/플로라/SECTOR 13-10'},
                                 dict(build='standard', n_runs=30, seed=3, rules_override={'any_turn_source': src, 'enemy_leader': 'boss'}))
                out[src] = (count['chain'] / max(1, count['hit']), r['outcome']['progress'], count['hit'] / 30.0)      # (보스 피격 1회당 연쇄, 진행도, 판당 피격)
        finally:
            api.Battle.chain, api.Battle.strike = orig, orig_strike
        self.assertGreater(out['text'][1], 0.1, out)             # 보스까지 닿는 전투
        self.assertGreater(out['text'][0], 0.1, out)            # 옛 동작에서 연쇄가 실제로 발동하는 경로여야 시험이 의미 있음
        self.assertLess(out['table'][0], out['text'][0] * 0.7, out)   # 보스 피격당 연쇄 비율이 크게 줄어듦


if __name__ == '__main__':
    unittest.main()
