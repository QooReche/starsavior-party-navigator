"""Restored recommendation policy vs frozen implementation; both JS/Python modes."""
import copy
import itertools
import inspect
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import party_reco as pr


class Defaults(unittest.TestCase):
    def test_detects_removed_roles(self):
        original = pr.team_value
        namespace = dict(pr.__dict__)
        source = inspect.getsource(original).replace('if not cfg.get("recommendation", {}).get("neutralRoles", False):', 'if False:')
        exec(source, namespace)
        try:
            pr.team_value = namespace['team_value']
            with self.assertRaises(AssertionError):
                self.test_roles_layout_and_leader()
        finally:
            pr.team_value = original

    def test_roles_layout_and_leader(self):
        roster, growth, mains, cfg, tags = pr.load()
        frozen = dict(pr.__dict__)
        exec((ROOT/'tests/fixtures/reco_role_legacy.py').read_text(encoding='utf8'), frozen)
        by_role = {}
        for s in roster:
            by_role.setdefault(s['className'], []).append(s)
        members = [s for role in [pr.SUPPORT, pr.DEFENDER, '캐스터'] for s in by_role[role][:2]]
        teams = [[dict(s=s, score=10+i/2, stats=dict(hp=100+i*200, spd=i*7, **{'def': 0}))
                  for i, s in enumerate(team)] for team in itertools.combinations(members, 4)]
        data = json.loads(re.search(r'const D=(\{[^\n]+\});', (ROOT/'index.html').read_text(encoding='utf8')).group(1))
        web = {s['key']: s for s in data['roster']}
        expected, cases = [], []
        for neutral in [False, True]:
            policy = copy.deepcopy(cfg)
            policy['recommendation']['neutralRoles'] = neutral
            for team in teams:
                legacy = frozen['team_value'](team, cfg, tags, 3)[0]
                roles = [x['s']['className'] for x in team]
                delta = (cfg['weights']['supportBonus'] if pr.SUPPORT in roles else 0) - 3*max(0, roles.count(pr.DEFENDER)-1) - (4 if roles.count(pr.SUPPORT)>1 else 0)
                score = pr.team_value(team, policy, tags, 3)[0]
                self.assertAlmostEqual(score, legacy-delta if neutral else legacy)
                self.assertEqual(pr.place(team), frozen['place'](team))
                self.assertEqual(pr.leader_pick(team, cfg, tags), frozen['leader_pick'](team, cfg, tags))
                expected.append(score)
                cases.append(dict(neutral=neutral, team=[dict(s=web[x['s']['key']], score=x['score']) for x in team]))
        script = r"""
const fs=require('fs'),vm=require('vm'),x=JSON.parse(fs.readFileSync(0,'utf8')),h=fs.readFileSync('party_template.html','utf8');
const c=vm.createContext({D:x.data,CFG:x.data.cfg,EL:{sun:'태양',moon:'달',star:'별',order:'질서',chaos:'혼돈'}});
vm.runInContext(h.slice(h.indexOf('let SBACT='),h.indexOf('function synSummary(')),c);
const values=x.cases.map(t=>{c.t=t;return vm.runInContext('CFG.recommendation.neutralRoles=t.neutral;teamValue(t.team,3)[0]',c)});
process.stdout.write(JSON.stringify(values));
"""
        output = subprocess.check_output(['node', '-e', script], input=json.dumps(dict(data=data, cases=cases)).encode(), cwd=ROOT)
        for js, py in zip(json.loads(output), expected):
            self.assertAlmostEqual(js, py, places=9)
        # A nontrivial neutral switch: each role adjustment must affect some case.
        self.assertTrue(any(a != b for a, b in zip(expected[:len(teams)], expected[len(teams):])))


if __name__ == '__main__':
    unittest.main()
