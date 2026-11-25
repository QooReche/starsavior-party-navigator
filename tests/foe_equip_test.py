"""합성 클라 21·22단계: 생성 → 병합 → 엔진/HTML 목록/추천. 비공개 표 불필요."""
import copy
import json
import random
import re
import shutil
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import datafile
from battlesim.starsavior import foe
from tools import build_foe_equip as B
from tools.runtime import static_path_or_none


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')


class EquipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / 'local').mkdir(exist_ok=True)
        cls.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'local', prefix='equip-test-')
        cls.root = Path(cls.tmp.name)
        cls.static = cls.root / 'static'
        cls.fixture = json.loads((ROOT / 'tests/fixtures/equip_client_stages.json').read_text(encoding='utf-8'))
        for name, rows in cls.fixture['tables'].items():
            write_json(cls.static / 'tables' / (name + '.json'), {'Data': rows})
        write_json(cls.static / 'tables/Strings/STRING_COMMON_ko_en.json', cls.fixture['strings'])
        for name, rows in cls.fixture['scripts'].items():
            write_json(cls.static / 'tables/BattleScript' / name.replace('.txt', '.json'), {'Data': rows})
        cls.raw = B.databook()
        cls.frag = B.build(cls.static, cls.raw)
        write_json(cls.root / 'data/foe_equip.json', cls.frag)
        for name in ('foe_clash', 'foe_cosmo_extra'):
            shutil.copyfile(ROOT / 'data' / (name + '.json'), cls.root / 'data' / (name + '.json'))
        (cls.root / 'rawdata').mkdir()
        (cls.root / 'rawdata/foe.js').write_text('__SSD.foe=' + json.dumps(cls.raw, ensure_ascii=False), encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        foe._FOE = None
        foe._EXTRA_ON.pop(str(cls.root), None)
        datafile.clear()
        cls.tmp.cleanup()

    def setUp(self):
        foe._FOE = None
        datafile.clear()

    def assert_six(self, fragment):
        rows = [s for g in fragment['g'] for t in g['tabs'] for s in t['s']]
        self.assertEqual(len(rows), 6)
        self.assertEqual(sum(s['n'].endswith('XXI') for s in rows), 3)
        self.assertEqual(sum(s['n'].endswith('XXII') for s in rows), 3)

    def test_generated_values_and_engine(self):
        self.assert_six(self.frag)
        for i, tab in enumerate(self.frag['g'][0]['tabs'], 1):
            for n, st in zip((21, 22), tab['s']):
                got, waves = foe.stage_waves('equip', tab['t'], st['n'], str(self.root))
                self.assertEqual((got['lv'], got['bp'], got['lt']), (n, 1000+i*100+n, 77))
                self.assertEqual(list(map(len, waves)), [1, 1])
                d, last = waves[0][0], waves[1][0]
                self.assertEqual((d.name, d.role, d.element, d.boss), ('합성 시험 적', '디펜더', ('태양','달','별')[i-1], True))
                self.assertEqual((d.stats['hp'], d.stats['atk'], d.stats['hit'], d.stats['evade']),
                                 (int((100+10*(n-1))*1.5), 20+2*(n-1), 9800, 700))
                self.assertEqual((d.game_slot, last.game_slot, last.level), (2, 4, 30))
                self.assertEqual((d.spawn, last.spawn), ('A', 'S'))
                self.assertEqual(d.skills['기본기'].cf, [12500, 0, 0, 0])
                self.assertEqual(d.skills['기본기'].ab, 2)
                self.assertEqual(d.auto['기본기'], {'rows':[{'c':[], 'f':['high_atk']}]})
                self.assertEqual(d.lines[0].eff['kind'], 'buff')
                self.assertEqual(len(d.force_lines), 1)
                self.assertEqual('equip|%s|%s' % (tab['t'], st['n']) in foe.battle_end(str(self.root)), n == 21)

    def test_existing_stages_unchanged_and_idempotent(self):
        merged = copy.deepcopy(self.raw)
        old = copy.deepcopy(next(g for g in merged['g'] if g['k'] == 'equip'))
        self.assertTrue(foe.merge_extra(merged, self.frag))
        new = next(g for g in merged['g'] if g['k'] == 'equip')
        for a, b in zip(old['tabs'], new['tabs']):
            self.assertEqual(a['s'], b['s'][:20])
        self.assertFalse(foe.merge_extra(merged, self.frag))
        # 같은 단계가 데이터북에 추가되면 오래된 조각의 aux도 버림.
        fresh = copy.deepcopy(self.raw)
        for tab in next(g for g in fresh['g'] if g['k'] == 'equip')['tabs']:
            tab['s'] += copy.deepcopy(next(t['s'] for t in self.frag['g'][0]['tabs'] if t['t']==tab['t']))
        self.assertFalse(foe.merge_extra(fresh, self.frag))
        self.assertNotIn('_extra_aux', fresh)

    def test_new_stage_runs_both_waves(self):
        from battlesim.mc import Battle
        from battlesim.metrics import unit_def
        st, waves = foe.stage_waves('equip', '뒤틀린 감정', '뒤틀린 감정 XXII', str(self.root))
        b = Battle([unit_def(k) for k in ('luna', 'carnelia', 'bell', 'emily')], waves,
                   random.Random(3), turn_limit=st['lt'])
        b.run()
        self.assertGreater(b.progress(), 0)
        self.assertEqual(b.result, 'clear')
        self.assertEqual(b.wave_i, 1)

    def test_web_list_and_recommendation(self):
        # 같은 build_foe.py를 local/ 안에서 실행해 배포 자료를 덮어쓰지 않음.
        (self.root / 'tools').mkdir(exist_ok=True)
        (self.root / 'docs').mkdir(exist_ok=True)
        code = (ROOT / 'tools/build_foe.py').read_text(encoding='utf-8')
        scope = {'__file__': str(self.root / 'tools/build_foe.py'), '__name__': '__equip_build__'}
        exec(compile(code, scope['__file__'], 'exec'), scope)
        import party_reco as pr
        import build_party_html as page
        with patch.object(pr, 'FOE', str(self.root / 'data/foe_stages.json')):
            path = self.root / 'index.html'
            page.main(str(path))
            html = path.read_text(encoding='utf-8')
            for tab in self.frag['g'][0]['tabs']:
                for st in tab['s']:
                    self.assertIn(st['n'], html)
                    self.assertIn(page.numerize(st['n']), html)
                    hits = [h for h in pr.find_stages('장비', st['n']) if h[1]['name'] == st['n']]
                    self.assertEqual(len(hits), 1)
                    self.assertEqual(hits[0][1]['recommended_power'], st['bp'])
            data = json.loads(re.search(r'const D=(\{.*?\});\s*\n', html).group(1))
            names = [st['n'] for tab in self.frag['g'][0]['tabs'] for st in tab['s']]
            # 장비는 웹 콘텐츠이며 CLI recommend의 설정에는 없음. 실제 웹 추천 함수를 실행함.
            script = r"""
const fs=require('fs'),vm=require('vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const html=fs.readFileSync('party_template.html','utf8');
const ctx=vm.createContext({D:input.data,CFG:input.data.cfg});
vm.runInContext(html.slice(html.indexOf('let SBACT='),html.indexOf('function synSummary(')),ctx);
ctx.names=input.names;
const result=vm.runInContext(`names.map(name=>{
 const c=D.contents.find(c=>c.key==='equip'),st=c.stages.find(s=>s.name===name);
 GIMACT=gimTop(c,st);SBACT=st.sb||[];DMW=[Math.min(1,(st.n-1)/2),CFG.damage.weightMob];
 const candidates=D.roster.filter(s=>['luna','carnelia','bell','emily'].includes(s.key)).map(s=>{
  const [v,parts]=score(s,st.w,c.main,c.boss);return {s,score:v,parts};});
 return {name:st.name,rp:st.rp,teams:topParties(candidates,CFG.weights.defenderPenalty,1).map(t=>t.combo.map(x=>x.s.key))};
})`,ctx);
process.stdout.write(JSON.stringify(result));
"""
            result = subprocess.run(['node', '-e', script], input=json.dumps(dict(data=data, names=names)),
                                    text=True, encoding='utf-8', capture_output=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual([r['name'] for r in rows], names)
            self.assertEqual(len(rows), 6)
            for r in rows:
                self.assertEqual(len(r['teams']), 1)
                self.assertEqual(len(r['teams'][0]), 4)

    def test_unknown_input_rejected(self):
        tb = B.Tables(self.static)
        battles = copy.deepcopy(self.fixture['tables']['BATTLE_TEMPLET_NORMAL'])
        row = next(r for r in battles if r['OrderList'] == 21)
        row['BattleMode'] = 'UNKNOWN'
        args = (tb, battles, self.fixture['tables']['BATTLE_TAB_TEMPLET'], self.fixture['scripts'].__getitem__, {}, self.raw)
        with self.assertRaisesRegex(ValueError, '승리 조건'):
            B.generate(*args)

    def test_comparison_reports_additions_separately(self):
        from tools.compare_foe_equip import compare
        old = dict(self.raw, g=[g for g in self.raw['g'] if g['k'] != 'equip'])
        result = compare(old, self.frag)
        self.assertEqual(len(result['added']), 6)
        self.assertNotIn('stage.missing', result['differences'])
        missing = compare(dict(self.frag, ak=self.raw['ak']), dict(self.frag, g=[]))
        self.assertEqual(missing['differences']['stage.missing'], 1)

    def test_ambiguous_skill_level_rejected(self):
        tb = B.Tables(self.static)
        tb.level[1].append(dict(tb.level[1][0], SkillLevelValue=2))
        with self.assertRaisesRegex(ValueError, '복수 스킬 레벨'):
            B.generate(tb, self.fixture['tables']['BATTLE_TEMPLET_NORMAL'],
                       self.fixture['tables']['BATTLE_TAB_TEMPLET'], self.fixture['scripts'].__getitem__,
                       {r['Id']: r for r in self.fixture['tables']['Plain/AUTO_SKILL_TEMPLET']}, self.raw)

    def test_client_hit_rates_override_old_fingerprint(self):
        from battlesim.starsavior import hit_stats
        unit = self.frag['u'][0]
        key = hit_stats.signature(unit['n'], unit['b'])
        with patch.object(hit_stats, 'data', return_value={key: [10000, 0]}):
            self.assertEqual(hit_stats.rates(self.raw, unit, None), (9800, 700))
            legacy = {k: v for k, v in unit.items() if k not in ('hit', 'evade')}
            self.assertEqual(hit_stats.rates(self.raw, legacy, None), (10000, 0))

    def test_disabled_generation_and_merge_are_detected(self):
        # 생성/병합을 실제로 꺼서 위 검증이 실패하는지 확인(작업 파일은 바꾸지 않음).
        with patch.object(B, 'generate', return_value={'g': []}):
            with self.assertRaises(AssertionError):
                self.assert_six(B.build(self.static, self.raw))
        with patch.object(foe, 'merge_extra', return_value=False):
            with self.assertRaises(KeyError):
                foe.stage_waves('equip', '뒤틀린 감정', '뒤틀린 감정 XXI', str(self.root))


@unittest.skipIf(static_path_or_none(ROOT) is None, '비공개 클라 표 없음')
class EquipClientTest(unittest.TestCase):
    def test_existing_twenty_stages_match_client(self):
        from tools.compare_foe_equip import compare
        raw = B.databook()
        frag = B.build(static_path_or_none(ROOT), raw, all_stages=True)
        result = compare(raw, frag)
        self.assertEqual(result['stages'], 60)
        self.assertEqual(result['units'], 100)
        self.assertEqual(result['summons'], 40)
        self.assertGreater(result['lines'], 900)
        self.assertEqual(result['differences'], {}, result['examples'])


if __name__ == '__main__':
    unittest.main()
