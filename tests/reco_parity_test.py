"""실제 웹 추천 함수와 Python 상위 10의 조합·동점 순서·수치 대조."""
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import reco_check as reco
import party_reco as pr


class RecoParityTest(unittest.TestCase):
    def test_top_ten(self):
        data = json.loads(re.search(r'const D=(\{.*?\});\s*\n', (ROOT / 'index.html').read_text(encoding='utf-8')).group(1))
        roster = [s['key'] for s in pr.load()[0]]
        rng = random.Random(7)
        filters = [roster, sorted(rng.sample(roster, 40)), sorted(rng.sample(roster, 24))]
        cases, expected = [], []
        for ck, needle in [('cosmo', '길레 2단계'), ('rush', '매니저 그레고리 Ⅰ'), ('op', 'SECTOR 1-1')]:
            c = next(c for c in data['contents'] if c['key'] == ck)
            st = next(st for st in c['stages'] if needle in st['name'])
            source = reco.stage_obj(ck, st['tab'], st['name'])
            for own in filters:
                candidates, dp = reco.candidates(ck, st['tab'], source)
                candidates = [x for x in candidates if x['s']['key'] in own]
                expected.append([(reco.ckey(combo), value) for combo, value, _ in pr.top_parties(candidates, reco.base()['cfg'], reco.base()['tags'], dp, 10)])
                cases.append(dict(c=c['key'], stage=st['name'], own=own))
        script = r"""
const fs=require('fs'),vm=require('vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const html=fs.readFileSync('party_template.html','utf8'),ctx=vm.createContext({D:input.data,CFG:input.data.cfg,EL:{sun:'태양',moon:'달',star:'별',order:'질서',chaos:'혼돈'}});
vm.runInContext(html.slice(html.indexOf('let SBACT='),html.indexOf('function synSummary(')),ctx);
const result=input.cases.map(x=>{ctx.test=x;return vm.runInContext(`(()=>{
 const c=D.contents.find(c=>c.key===test.c),st=c.stages.find(s=>s.name===test.stage);
 GIMACT=gimTop(c,st);SBACT=st.sb||[];DMW=[Math.min(1,(st.n-1)/2),c.boss?CFG.damage.weightBoss:CFG.damage.weightMob];
 const candidates=D.roster.filter(s=>test.own.includes(s.key)).map(s=>{const [v,parts]=score(s,st.w,c.main,c.boss);return {s,score:v,parts}});
 return topParties(candidates,CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty,10).map(t=>[t.combo.map(x=>x.s.key).sort().join(','),t.v]);
})()`,ctx)});process.stdout.write(JSON.stringify(result));
"""
        r = subprocess.run(['node', '-e', script], input=json.dumps(dict(data=data, cases=cases)), text=True, encoding='utf-8', capture_output=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        for i, (js, py) in enumerate(zip(json.loads(r.stdout), expected)):
            with self.subTest(case=i):
                self.assertEqual([x[0] for x in js], [x[0] for x in py])
                for x, y in zip(js, py):
                    self.assertAlmostEqual(x[1], y[1], delta=1e-9)


    def test_full_order_and_ties(self):
        """상위 200 전체 순서 + 동점 구간 내 i-순서 보존 검증."""
        data = json.loads(re.search(r'const D=(\{.*?\});\s*\n', (ROOT / 'index.html').read_text(encoding='utf-8')).group(1))
        rng = random.Random(42)
        roster = [s['key'] for s in pr.load()[0]]
        K = 200
        cases, expected = [], []
        for ck, needle in [('cosmo', '길레 2단계'), ('op', 'SECTOR 1-1')]:
            c = next(c for c in data['contents'] if c['key'] == ck)
            st = next(st for st in c['stages'] if needle in st['name'])
            source = reco.stage_obj(ck, st['tab'], st['name'])
            own = sorted(rng.sample(roster, 24))
            candidates, dp = reco.candidates(ck, st['tab'], source)
            candidates = [x for x in candidates if x['s']['key'] in own]
            expected.append([(reco.ckey(combo), value) for combo, value, _ in pr.top_parties(candidates, reco.base()['cfg'], reco.base()['tags'], dp, K)])
            cases.append(dict(c=c['key'], stage=st['name'], own=own, k=K))
        script = r"""
const fs=require('fs'),vm=require('vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const html=fs.readFileSync('party_template.html','utf8'),ctx=vm.createContext({D:input.data,CFG:input.data.cfg,EL:{sun:'태양',moon:'달',star:'별',order:'질서',chaos:'혼돈'}});
vm.runInContext(html.slice(html.indexOf('let SBACT='),html.indexOf('function synSummary(')),ctx);
const result=input.cases.map(x=>{ctx.test=x;return vm.runInContext(`(()=>{
 const c=D.contents.find(c=>c.key===test.c),st=c.stages.find(s=>s.name===test.stage);
 GIMACT=gimTop(c,st);SBACT=st.sb||[];DMW=[Math.min(1,(st.n-1)/2),c.boss?CFG.damage.weightBoss:CFG.damage.weightMob];
 const candidates=D.roster.filter(s=>test.own.includes(s.key)).map(s=>{const [v,parts]=score(s,st.w,c.main,c.boss);return {s,score:v,parts}});
 return topParties(candidates,CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty,test.k).map(t=>[t.combo.map(x=>x.s.key).sort().join(','),t.v]);
})()`,ctx)});process.stdout.write(JSON.stringify(result));
"""
        r = subprocess.run(['node', '-e', script], input=json.dumps(dict(data=data, cases=cases)), text=True, encoding='utf-8', capture_output=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        for i, (js, py) in enumerate(zip(json.loads(r.stdout), expected)):
            with self.subTest(case=i):
                self.assertEqual(len(js), len(py), f'count mismatch: js={len(js)} py={len(py)}')
                self.assertEqual([x[0] for x in js], [x[0] for x in py], 'combo key order mismatch')
                for j, (x, y) in enumerate(zip(js, py)):
                    self.assertAlmostEqual(x[1], y[1], delta=1e-9, msg=f'value mismatch at {j}')
                # Verify tie spans: within equal-v groups, order must be consistent
                ties = {}
                for item in js:
                    ties.setdefault(round(item[1], 9), []).append(item[0])
                tie_pairs = sum(len(v) * (len(v)-1) // 2 for v in ties.values() if len(v) > 1)
                # tie_pairs may be 0 for small rosters — just record for diagnostics
                _ = tie_pairs  # ordering comparison above is the real correctness check


if __name__ == '__main__':
    from tools.runtime import low_priority
    low_priority()
    unittest.main()
