# -*- coding: utf-8 -*-
"""길방 시뮬 표 프리셋 입력·판별 평균·실제 엔진 선택 효과 회귀 시험."""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import build_guild_sim as B


class GuildSimTest(unittest.TestCase):
    def test_default_build_shape(self):
        # main의 인자 기본값 → 엔진 인자 → 파일의 모든 배수/프리셋 → 화면 payload까지 확인.
        import guild_defense as gd
        calls = []
        def fake(party, stage, opts):
            tiers = stage['guild']['sets']
            calls.append(tiers)
            p = 0.5 if tiers == [0]*4 else 0
            return dict(outcome=dict(clear_p=p, progress=0.6), prog_runs=[0.2, 1])
        db = SimpleNamespace(units={k: {'n': k} for k in B.COMMUNITY})
        with tempfile.TemporaryDirectory() as d:
            out = str(Path(d) / 'sim.json')
            with patch.object(sys, 'argv', ['build_guild_sim.py', '--out', out, '--workers', '1']), \
                    patch.object(B, 'get_db', return_value=db), \
                    patch.object(B, 'reco_teams', return_value=[]), \
                    patch.object(B, 'scaled_units', return_value=[]), \
                    patch.object(B, 'simulate', side_effect=fake), patch('builtins.print'):
                B.main()
            raw = json.loads(Path(out).read_text(encoding='utf-8'))
            self.assertEqual(raw['growth'], ['1', '1.5', '2', '2.5', '3'])
            self.assertEqual(raw['sets'], B.SETS)
            self.assertEqual(raw['runs'], 60)
            self.assertEqual(len(calls), 5*2*6*13)
            t = raw['teams'][0]
            self.assertEqual(t['rates'], t['bySupport']['none'])
            self.assertEqual(set(t['bySets']), {'max'})
            for g in raw['growth']:
                self.assertEqual(raw['summary'][g]['level'], 12)
                self.assertIsNone(raw['summaryBySets']['max'][g])
                for tab in (t, t['bySets']['max']):
                    for sup in raw['supports']:
                        self.assertEqual(tab['fracBySupport'][sup][g], [0.5]*13)
            payload = gd.sim_payload(gd.load(), out)
            self.assertEqual(payload['sets'], raw['sets'])
            self.assertEqual(payload['summaryBySets'], raw['summaryBySets'])
            self.assertEqual(payload['teams'][0]['bySets'], t['bySets'])

    def test_presets(self):
        self.assertEqual(B.parse_sets('off,max,no_void=3330'),
                         dict(off=[0]*4, max=[3]*4, no_void=[3, 3, 3, 0]))
        for bad in ('max', 'off,off', 'off,max=0000', 'off,x=4444', 'off,x=333', 'off,'):
            with self.assertRaises(argparse.ArgumentTypeError):
                B.parse_sets(bad)

    def test_tables_and_summary(self):
        def fake(party, stage, opts):
            self.assertEqual(opts['n_runs'], 2)
            self.assertEqual(opts['seed'], 7)
            self.assertEqual(stage['guild']['sets'], [3]*4)
            p = 0.5 if stage['guild']['level'] <= 6 else 0
            return dict(outcome=dict(clear_p=p, progress=0.6), prog_runs=[0.2, 1])
        with patch.object(B, 'simulate', side_effect=fake):
            tab = B.sim_tables([], 0, '2.5', ['none', 'fire'], [3]*4, 2, 7)
        self.assertEqual(tab['fracBySupport']['fire']['2.5'], [0.5]*13)
        self.assertEqual(tab['progBySupport']['none']['2.5'], [0.6]*13)
        off = {'bySupport': {s: {'2.5': [0]*13} for s in ['none', 'fire']}, 'bySets': {'max': tab}}
        self.assertEqual(B.summarize([off], ['2.5'], ['none', 'fire']), {'2.5': None})
        self.assertEqual(B.summarize([off], ['2.5'], ['none', 'fire'], 'max'),
                         {'2.5': dict(level=6, team=0, p=0.5, support='none')})

    def test_engine_sets_change_progress(self):
        db = B.get_db()
        rec = json.loads((ROOT / 'data/guild_bfb.json').read_text(encoding='utf-8'))['power']
        units = B.scaled_units(db, B.COMMUNITY, 0, rec * 2)
        outcomes = []
        for tiers in ([0]*4, [3]*4):
            r = B.simulate({'units': units, 'leader': 0},
                           {'guild': {'level': 6, 'support': 'fire', 'sets': tiers}},
                           {'seed': 7, 'n_runs': 12, 'build': 'standard', 'rules_override': {'power_penalty': 'model'}})
            self.assertGreater(r['outcome']['progress'], 0)
            outcomes.append(r['outcome'])
        print('engine off/max:', [(r['progress'], r['clear_p']) for r in outcomes])
        self.assertGreater(abs(outcomes[0]['progress'] - outcomes[1]['progress']), 0.01)

    def test_parallel_matches_sequential(self):
        rec = json.loads((ROOT / 'data/guild_bfb.json').read_text(encoding='utf-8'))['power']
        units = B.scaled_units(B.get_db(), B.COMMUNITY, 0, rec * 2)
        jobs = [(units, 0, '2', ['fire'], tiers, 2, 7) for tiers in ([0]*4, [3]*4)]
        sequential = list(B.run_jobs(jobs, 1))
        self.assertEqual(list(B.run_jobs(jobs, 2)), sequential)
        self.assertTrue(all(max(t['progBySupport']['fire']['2']) > 0 for t in sequential))
        self.assertNotEqual(sequential[0], sequential[1])


if __name__ == '__main__':
    unittest.main()
