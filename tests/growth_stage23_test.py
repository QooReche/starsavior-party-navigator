"""Public standard builds: real run arrays -> JS guild metric, plus score boundaries."""
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import guild_defense as gd
from battlesim import simulate


class GrowthStage23Test(unittest.TestCase):
    def check_metric(self, progs, level=0, tiers=None, tiny=False):
        tiers = tiers or [0, 0, 0, 0]
        script = """
const fs=require('fs'),G=require('./growth_guide'),S=require('./guild_search'),V=require('./guild_view'),D=require('./data/guild_defense.json');
const x=JSON.parse(fs.readFileSync(0,'utf8'));
if(x.tiny)Object.assign(D.steps.find(s=>s.ex),{base:0,kill:0,bossKill:1});
const m=G.guildMetric(S,V,D,x.level,x.tiers);
console.log(JSON.stringify(m.prepare({n:x.ps.length,progs:x.ps,prog:x.ps.reduce((a,b)=>a+b)/x.ps.length,clear:0})));
"""
        p = subprocess.run(['node', '-e', script], cwd=ROOT, input=json.dumps(dict(ps=progs, level=level, tiers=tiers, tiny=tiny)),
                           text=True, encoding='utf-8', capture_output=True, check=True)
        result = json.loads(p.stdout)
        data = gd.load()
        if tiny:
            next(s for s in data['steps'] if s.get('ex')).update(base=0, kill=0, bossKill=1)
        pct = gd.extra_pct(data, level, tiers)
        scores = [gd.score_from_prog(data, pct, x) for x in progs]
        self.assertEqual(result['scores'], scores)
        self.assertEqual(result['mean'], math.floor(sum(scores) / len(scores) + .5))
        n = max(1, math.ceil(len(scores) * .2 - 1e-9))
        self.assertEqual(result['top'], math.floor(sum(sorted(scores, reverse=True)[:n]) / n + .5))
        return result

    def test_score_boundaries(self):
        self.check_metric([0, .249999, .25, .499999, .5, .50005, .75, .99995, 1], 4, [1, 2, 0, 0])
        # A deliberately tiny public score table exercises half-up .5 rounding.
        self.assertEqual(self.check_metric([0, 1, 0, 1], tiny=True)['mean'], 1)

    def test_real_guild_runs(self):
        r = simulate({'units': ['gwen', 'fei', 'professor-m', 'amora'], 'leader': 0},
                     {'guild': {'level': 0, 'support': 'gust', 'sets': [0, 0, 0, 0]}},
                     {'build': 'standard', 'n_runs': 4, 'seed': 17011})
        self.assertGreater(r['outcome']['progress'], 0)
        self.assertEqual(len(r['prog_runs']), 4)
        metric = self.check_metric(r['prog_runs'])
        self.assertGreater(metric['top'], 0)


if __name__ == '__main__':
    unittest.main()
