# -*- coding: utf-8 -*-
"""적 패시브 조건 회귀(2026-10-23): python -X utf8 -I tests/enemy_cond_test.py

「강화/약화 효과 개수」 조건이 때린 상대 한 명 기준으로 평가되는지 본다. 예전에는 개수를 세는 대상이 정해지지 않아 0 으로 읽혀
「시전자가 보유: X; 효과 개수: N」·「적 약화효과 보유; 효과 개수 이상: N」은 한 번도 참이 되지 않았고,
「적 강화효과 보유; 효과 개수 미만: N」은 상대 전원 중 하나만 강화 효과가 있어도 참이었다(보스가 아군 아무에게나 맞아도 행동 게이지 +30%p).
실측 근거: 장비 탐색 혹한의 습격 XVII 3판(docs/HANDOFF.md 참고)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tools')]
import gen_quick_calib as G
from battlesim import quick, simulate
import battlesim.mc as M


def party(ck, sk, order, lead, power):
    q, _pen = quick.load(ROOT)
    st = q['st'][ck][sk]
    return G.party_spec(q, order, lead, list(order), power / st['bp'], st)


class EnemyCondTest(unittest.TestCase):
    def watch(self, spec, stage, pairs, over=None, runs=12):
        """pairs 의 조건 키 쌍이 모두 든 줄의 (평가 횟수, 참 횟수)."""
        hits = {p: [0, 0] for p in pairs}
        orig = M.Battle.cond_ok

        def rec(self_, owner, ln, ctx):
            r = orig(self_, owner, ln, ctx)
            keys = {k for k, _v in ln.params}
            for p in pairs:
                if set(p) <= keys:
                    hits[p][0] += 1
                    hits[p][1] += 1 if r else 0
            return r
        M.Battle.cond_ok = rec
        try:
            opt = dict(G.SIMOPT, seed=3, rekindle=0, n_runs=runs, max_turns=30)
            opt['rules_override'] = dict(opt['rules_override'], nova_policy='auto', **(over or {}))
            out = simulate(spec, {'stage': stage}, opt)
        finally:
            M.Battle.cond_ok = orig
        return hits, out

    def test_caster_effect_count_is_read_from_attacker(self):
        spec = party('equip', '혹한의 습격|혹한의 습격 XⅦ', ['emily', 'frey', 'haydee', 'gwen'], 'emily', 372610)
        hits, _ = self.watch(spec, 'clo/달 회랑/FLOOR 410', [('시전자가 보유', '효과 개수')])
        n, t = hits[('시전자가 보유', '효과 개수')]
        self.assertGreater(n, 0)
        self.assertGreater(t, 0, '시전자(제행무상 보유)의 중첩수를 읽어 한 번은 참이어야 함')

    def test_weak_attacker_buff_condition_matches_hit_by_unbuffed_ally_only(self):
        spec = party('equip', '혹한의 습격|혹한의 습격 XⅦ', ['emily', 'frey', 'haydee', 'gwen'], 'emily', 372610)
        pair = ('적 강화효과 보유', '효과 개수 미만')
        new, out_new = self.watch(spec, 'equip/혹한의 습격/혹한의 습격 XⅦ', [pair])
        old, out_old = self.watch(spec, 'equip/혹한의 습격/혹한의 습격 XⅦ', [pair], {'enemy_hit_buff_cmp': 'legacy'})
        self.assertGreater(new[pair][0], 0)
        # 새 판정(기본 le)은 때린 아군 한 명이 강화 효과 1개 이하일 때만 참 → 옛 판정(아군 아무나 버프가 있으면 참)보다 드묾
        self.assertLess(new[pair][1] / new[pair][0], old[pair][1] / max(1, old[pair][0]))
        # 보스가 덜 빨라져 전멸만 하던 결과가 바뀜(근사 확인: 진척도가 늘어남)
        self.assertGreater(out_new['outcome']['progress'], out_old['outcome']['progress'])

    def test_default_is_attacker_based(self):
        import json
        with open(os.path.join(ROOT, 'battlesim', 'rules', 'default.json'), encoding='utf-8') as f:
            rules = json.load(f)
        self.assertEqual(rules['mc']['enemy_hit_buff_cmp']['value'], 'le')


if __name__ == '__main__':
    unittest.main()
