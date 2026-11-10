# -*- coding: utf-8 -*-
"""mc.stage_fx_target: 스테이지 효과(fx)를 적(enemies, 옛 동작)에게 걸지 아군(allies, 표대로)에게 걸지.
플래시 포인트 «공허말살자 Ⅰ» = 태양 속성 방어력 +30%(60007) + 디펜더 치명타 확률 +30%(60009), 대상은 A팀(아군)만.
근거: static-data tables/BATTLE_EFFECT_TEMPLET.json·SE_TEMPLET_BATTLE_EFFECT.json, NKM.Templets.decompiled.cs:36765-36799.
실행: python -X utf8 -I tests/stage_fx_target_test.py"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
import battlesim.api as api                                      # noqa: E402
from battlesim.rules import MC_RULES                             # noqa: E402

STAGE = 'rush/공허말살자/공허말살자 Ⅰ'
PARTY = ['emily', 'gwen', 'fei']        # 달 디펜더 / 별 스트라이커 / 달 어쌔신
SEEN = []


class _Spy(api.Battle):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        SEEN.append(self)


def _run(mode, stage=STAGE, extra=None):
    SEEN.clear()
    orig = api.Battle
    api.Battle = _Spy
    try:
        r = api.simulate(PARTY, dict(stage=stage), dict(n_runs=20, seed=3, rules_override=dict(stage_fx_target=mode), **(extra or {})))
    finally:
        api.Battle = orig
    return r, list(SEEN)


class StageFxTargetTest(unittest.TestCase):
    def test_default_is_allies_with_enemies_legacy(self):
        self.assertEqual(MC_RULES['stage_fx_target']['value'], 'allies')
        self.assertEqual(MC_RULES['stage_fx_target']['legacy'], 'enemies')
        self.assertIn('off', MC_RULES['stage_fx_target']['alt'])

    def test_allies_mode_buffs_only_matching_allies(self):
        _, bs = _run('allies')
        self.assertTrue(bs)
        em, gw, fei = bs[0].allies
        self.assertAlmostEqual(em.mods()['cr'], gw.mods()['cr'] + 0.30, places=6)     # 디펜더만 치명 +30%
        self.assertAlmostEqual(fei.mods()['cr'], gw.mods()['cr'], places=6)
        self.assertEqual(em.fx, {'치명타 확률': 30.0})
        self.assertEqual(gw.fx, {})                                                   # 별 스트라이커: 태양도 디펜더도 아님
        # 적에게는 안 걸림
        foes = [f for f in bs[0].all_foes]
        self.assertTrue(foes)
        self.assertTrue(all(not f.fx for f in foes))

    def test_enemies_mode_is_legacy(self):
        _, bs = _run('enemies')
        for a in bs[0].allies:
            self.assertEqual(a.fx, {})
        foes = bs[0].all_foes
        self.assertTrue(foes and all(f.fx == {'방어력%': 30.0, '치명타 확률': 30.0} for f in foes), [f.fx for f in foes])

    def test_modes_give_different_results(self):
        ra, _ = _run('allies')
        re_, _ = _run('enemies')
        ro, _ = _run('off')
        key = lambda r: json.dumps([r['outcome'], r['per_unit']], sort_keys=True, ensure_ascii=False)
        self.assertNotEqual(key(ra), key(re_))
        self.assertNotEqual(key(ra), key(ro))
        self.assertNotEqual(key(re_), key(ro))
        for r in (ra, re_, ro):
            self.assertGreater(r['outcome']['progress'], 0.3)       # 진행도 0 인 스테이지로 «아무것도 안 지키는» 시험이 되지 않게
        self.assertGreater(ra['outcome']['progress'], re_['outcome']['progress'])    # 적이 아니라 아군이 강해지면 진행도가 높다

    def test_stage_without_fx_unchanged(self):
        a, _ = _run('allies', stage='clo/달 회랑/FLOOR 100')
        e, _ = _run('enemies', stage='clo/달 회랑/FLOOR 100')
        key = lambda r: json.dumps([r['outcome'], r['per_unit']], sort_keys=True, ensure_ascii=False)
        self.assertEqual(key(a), key(e))

    def test_bad_value_rejected(self):
        with self.assertRaises(ValueError):
            _run('both')

    def test_condition_table_covers_every_rush_stage(self):
        from battlesim.starsavior.foe import stage_fx_cond, load_foe
        cond = stage_fx_cond()
        n = 0
        for g in load_foe()['g']:
            for t in g['tabs']:
                for s in t['s']:
                    if s.get('fx'):
                        n += 1
                        self.assertEqual(len(cond['%s|%s|%s' % (g['k'], t['t'], s['n'])]), len(s['fx']))
        self.assertEqual(n, 44)
        self.assertEqual(len(cond), 44)


if __name__ == '__main__':
    unittest.main()
