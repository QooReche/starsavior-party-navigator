"""전체 리뷰 결함 회귀. 공개 자료·합성 입력만 사용함."""
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from battlesim import simulate
from battlesim import fileio, metrics
from battlesim.mc import Battle
from battlesim.starsavior.data import get_db, _find_key
from battlesim.starsavior.foe import gloss
from battlesim.starsavior.parser import UnitDef
from p3_test import unit
from tools import build_simpack, calibrate_quick as calib, gen_quick_calib as gen, fetch_sources, unwrap_ssd
from tools.runtime import static_path


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = ROOT / 'local' / 'test-tmp' / uuid.uuid4().hex
        self.tmp.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def test_wave_start(self):
        d = UnitDef(get_db(), 'sunshine-cat-smile')
        f = unit('immune', hp=10**9)
        f.stats['er'] = 10000
        f.immune = {'물폭탄'}
        b = Battle([d], [[f], [f]], random.Random(7), max_turns=0.001)
        b.run()
        self.assertEqual(b.foes[0].stack('물폭탄'), 1)
        b.spawn_wave()
        self.assertEqual(b.foes[0].stack('물폭탄'), 1)

    def test_cache_sources(self):
        a = get_db()
        b = copy.copy(a)
        b.units = copy.deepcopy(a.units)
        key = next(iter(a.units))
        b.units[key]['n'] = '다른 DB'
        self.assertNotEqual(metrics.unit_def(key, db=a).name, metrics.unit_def(key, db=b).name)
        self.assertIs(metrics.unit_def(key, db=a), metrics.unit_def(key, db=a))
        raw = lambda n: {'s': [{'gl': [{'n': '시험', 'x': '공격력%% +%d%%' % n}]}]}
        x, y = raw(10), raw(99)
        self.assertEqual(gloss(x)['시험']['props']['공격력%'], 10)
        self.assertEqual(gloss(y)['시험']['props']['공격력%'], 99)
        self.assertIs(gloss(x), gloss(x))

    def test_api_validation(self):
        for n in [0, -1, 1.5, '2', True, None]:
            with self.subTest(n=n), self.assertRaisesRegex(ValueError, 'n_runs'):
                simulate([], {}, {'n_runs': n})
        with self.assertRaises(ValueError):
            _find_key(get_db(), 'no-such-unit')
        r = subprocess.run([sys.executable, '-X', 'utf8', '-I', str(ROOT / 'tools/sim_damage.py'), 'stats', 'no-such-unit'], capture_output=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn(b'Traceback', r.stderr)

    def test_manifest(self):
        manifest = json.loads((ROOT / 'sim/manifest.json').read_text(encoding='utf-8'))
        paths = build_simpack.files()
        h, size = hashlib.sha256(), 0
        for p in paths:
            content = (ROOT / p).read_bytes()
            h.update(p.encode() + b'\0' + content)
            size += len(content)
        self.assertEqual(manifest['files'], paths)
        self.assertEqual(manifest['ver'], h.hexdigest()[:12], 'tools/build_simpack.py 재실행 필요')
        self.assertEqual(manifest['bytes'], size)

    def test_atomic_failure(self):
        out = self.tmp / 'out.json'
        out.write_bytes(b'old')
        with patch.object(fileio.os, 'replace', side_effect=OSError('locked')):
            with self.assertRaises(OSError):
                fileio.atomic_text(out, '새 값\r\n')
        self.assertEqual(out.read_bytes(), b'old')
        self.assertEqual(list(self.tmp.iterdir()), [out])
        fileio.atomic_text(out, '새 값\r\n')
        self.assertEqual(out.read_bytes(), '새 값\n'.encode())
        with self.assertRaises(ValueError):
            fileio.atomic_json(out, {'bad': float('nan')}, allow_nan=False)
        self.assertEqual(out.read_bytes(), '새 값\n'.encode())

    def test_source_failure(self):
        for name in ['databook_main.json', 'foe.js', 'guide_app-core.js']:
            (self.tmp / name).write_text('old', encoding='utf-8')
        main = 'window.__SSD.main={"units":[1],"dict":{},"topics":{}};window.__SSV={"foe":"a"};'
        for last in [OSError('network'), 'bad structure']:
            with patch.object(fetch_sources, 'RAW', str(self.tmp)), patch.object(fetch_sources, 'DRY', False), patch.object(fetch_sources, 'get', side_effect=['<script src="data/main.js">', main, last]):
                with self.assertRaises((OSError, ValueError)):
                    fetch_sources.main()
            for p in self.tmp.iterdir():
                self.assertEqual(p.read_text(encoding='utf-8'), 'old')
        source = self.tmp / 'bad.js'
        source.write_text('no SSD data', encoding='utf-8')
        out = self.tmp / 'foe.js'
        with patch.object(sys, 'argv', ['unwrap', str(source), str(out)]), self.assertRaises(ValueError):
            unwrap_ssd.main()
        self.assertEqual(out.read_text(), 'old')

    def test_calibration(self):
        for rows in [[], [('op', 's', ['a'], {}, 1, {})], [('op', 's', ['a'], {}, 0, {})]]:
            with self.assertRaises(ValueError):
                calib.fit(rows, {}, [])
        rows = [('cosmo', 's', ['a'+str(i)], {}, i % 2, {'growth': i}) for i in range(8)]
        # 양성/음성이 각 분할에 존재하도록 배치함.
        rows = [(*r[:4], (i // 2) % 2, r[5]) for i, r in enumerate(rows)]
        partitions = []
        def fit_rows(rs, *_):
            partitions.append(tuple(calib.sample_key(r) for r in rs))
            return 1.0
        with patch.object(calib.quick, 'evaluate', return_value={'clear': True}), patch.object(calib, 'fit_stage_m', side_effect=fit_rows):
            a = calib.stage_factors(rows, {'sv': {}}, [], {})
            b = calib.stage_factors(list(reversed(rows)), {'sv': {}}, [], {})
        self.assertEqual(a, b)
        self.assertEqual(partitions[:2], partitions[2:])
        gen.quick_data.cache_clear()
        q, pen = gen.quick_data(str(ROOT))
        self.assertIs(gen.quick_data(str(ROOT))[0], q)
        fresh, _ = calib.quick.load(str(ROOT))
        keys = list(q['sv'])[:4]
        st = next(iter(q['st']['op'].values()))
        self.assertEqual(calib.quick.evaluate(keys, st, q['sv'], pen), calib.quick.evaluate(keys, st, fresh['sv'], pen))

    def test_generated_samples(self):
        out = self.tmp / 'samples.json'
        out.write_bytes(b'old')
        with patch.object(gen, 'OUT', str(out)):
            for rows in [[], [['op', 's', 'a', 1, None]]]:
                with self.assertRaises(ValueError):
                    gen.save_samples(rows, 2)
                self.assertEqual(out.read_bytes(), b'old')
            rows = [['op', 's', 'b', 1, 0], ['op', 's', 'a', 1, 1]]
            gen.save_samples(rows, 2)
            a = out.read_bytes()
            gen.save_samples(list(reversed(rows)), 2)
            self.assertEqual(out.read_bytes(), a)

    def test_extractor_and_empty_filter(self):
        source = self.tmp / 'bad.js'
        source.write_text('const GROWTH_PRIORITY = {\na:1\n', encoding='utf-8')
        r = subprocess.run(['node', str(ROOT / 'tools/extract_guide_tier.js'), str(source)], capture_output=True, timeout=10)
        self.assertNotEqual(r.returncode, 0)
        r = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tests/e2e/test_page.py'), 'NO_MATCH_FOR_CLEANUP_TEST'], capture_output=True, timeout=10)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('필터'.encode(), r.stdout)

    def test_static_path(self):
        with patch.dict(os.environ, {'STARSAVIOR_STATIC': str(self.tmp)}):
            self.assertEqual(static_path(), self.tmp)
            self.assertEqual(static_path(ROOT), ROOT)
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, 'STARSAVIOR_STATIC'):
            static_path()

    def test_output_isolated(self):
        view = ROOT / 'data/myinfo_view.json'
        before = view.stat().st_mtime_ns, view.read_bytes()
        r = subprocess.run([sys.executable, '-X', 'utf8', '-I', str(ROOT / 'build_party_html.py'), str(self.tmp / 'index.html')], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr.decode('utf-8'))
        self.assertEqual((view.stat().st_mtime_ns, view.read_bytes()), before)
        self.assertNotIn(b'\r\n', (self.tmp / 'index.html').read_bytes())
        from tools.build_myinfo_view import build
        self.assertEqual(build(fileio.read_json(ROOT / 'rawdata/databook_main.json')), json.loads(before[1]))

    @unittest.skipUnless(os.name == 'nt', 'Windows 우선순위 API 시험')
    def test_priority_failure(self):
        import ctypes
        from unittest.mock import MagicMock
        from tools.runtime import low_priority
        kernel = MagicMock()
        kernel.SetPriorityClass.return_value = 0
        with patch.object(ctypes, 'WinDLL', return_value=kernel), self.assertRaises(RuntimeError):
            low_priority()

    def test_html_cleanup_checks(self):
        """생성 HTML에 cytoscape 정적 태그 없음, D.syn에 e 없음, syn_detail 대조, URL 해시."""
        out = self.tmp / 'index.html'
        r = subprocess.run([sys.executable, '-X', 'utf8', '-I', str(ROOT / 'build_party_html.py'), str(out)], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr.decode('utf-8'))
        html = out.read_text(encoding='utf-8')
        # 1. 정적 cytoscape script 태그 없음
        self.assertNotIn('<script src="lib/cytoscape', html)
        # 2. D.syn에 e 없음
        import re
        m = re.search(r'const D=(\{.*?\});\s*\n', html)
        self.assertIsNotNone(m, 'D not found in HTML')
        d = json.loads(m.group(1))
        for entry in d['syn']:
            self.assertNotIn('e', entry, f'D.syn entry must not have e: {entry}')
        # 3. syn_detail.json 길이·순서 D.syn과 같고 원본과 대조
        syn_detail_path = ROOT / 'data' / 'syn_detail.json'
        self.assertTrue(syn_detail_path.exists())
        detail = json.loads(syn_detail_path.read_text(encoding='utf-8'))
        self.assertEqual(len(detail), len(d['syn']), 'syn_detail.json length must match D.syn')
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        import party_reco as pr_mod
        pairs = pr_mod.load_synergy()
        self.assertEqual(len(detail), len(pairs))
        for i, (ev, p) in enumerate(zip(detail, pairs)):
            expected = [e[:110] for e in p.get('evidence', [])[:2]]
            self.assertEqual(ev, expected, f'syn_detail[{i}] mismatch')
        # 4. URL 해시 = 파일 내용 해시
        detail_bytes = syn_detail_path.read_bytes()
        expected_hash = hashlib.sha256(detail_bytes).hexdigest()[:12]
        self.assertIn(f'syn_detail.json?v={expected_hash}', html)
        cyto_bytes = (ROOT / 'lib' / 'cytoscape.min.js').read_bytes()
        cyto_hash = hashlib.sha256(cyto_bytes).hexdigest()[:12]
        self.assertIn(f'cytoscape.min.js?v={cyto_hash}', html)

    def test_update_public_steps(self):
        from tools import update
        calls = []
        with patch.object(update, 'run', side_effect=lambda *a: calls.append(a)), patch.object(update, 'atomic_open', fileio.atomic_open):
            # 원본은 읽되 산출물 경로는 합성 임시 디렉터리로 대체함.
            main = {'units': [], 'rel': {'u': {}}, 'topics': {'pen': [], 'tribe': []}}
            (self.tmp / 'rawdata').mkdir()
            fileio.atomic_json(self.tmp / 'rawdata/databook_main.json', main)
            with patch.object(update, 'ROOT', str(self.tmp)), patch.object(sys, 'argv', ['update', '--no-html']):
                update.main()
        names = [Path(c[0]).name for c in calls]
        self.assertIn('build_skills.py', names)
        self.assertIn('build_myinfo_view.py', names)
        self.assertLess(names.index('build_skills.py'), names.index('build_simpack.py'))


if __name__ == '__main__':
    from tools.runtime import low_priority
    low_priority()
    unittest.main()
