"""공개 자료 전체 진단 래칫 + 양방향/동일 개수 교체/실제 수집 경로 변이."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import unsupported_allowlist as gate


class UnsupportedGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        gate.low_priority()
        cls.document = gate.read_json(gate.ALLOWLIST)
        cls.found, cls.stats = gate.collect()
        print('관문 측정: %s; 영역별 항목: %s' %
              (cls.stats, {a: len(v) for a, v in cls.found.items()}), flush=True)

    def test_current_inventory(self):
        gate.assert_gate(self.found, self.document)
        self.assertEqual(self.stats['static_builds'], self.stats['saviors'] * 2)
        self.assertEqual(self.stats['scenarios'], self.stats['saviors'] * 5 + 4)
        self.assertEqual(self.stats['runs'], self.stats['scenarios'] * 3)

    def test_added_line_mutations_all_areas(self):
        for area in gate.AREAS:
            with self.subTest(area=area):
                changed = deepcopy(self.found)
                changed[area].add('결함 주입: 새 미지원 1줄')
                with self.assertRaisesRegex(AssertionError, '클라로 확정하거나 사유와 함께 등록'):
                    gate.assert_gate(changed, self.document)
        # 변이 사본만 바꾸었고 원본으로 다시 통과해야 함.
        gate.assert_gate(self.found, self.document)

    def test_removed_and_same_count_replacement(self):
        for area in ('D', 'E'):
            changed = deepcopy(self.found)
            self.assertTrue(changed[area], area)
            changed[area].pop()
            with self.assertRaisesRegex(AssertionError, '해소됨, 목록에서 지우기'):
                gate.assert_gate(changed, self.document)
            changed[area].add('개수는 같지만 새로운 키')
            self.assertEqual(len(changed[area]), len(self.found[area]))
            with self.assertRaisesRegex(AssertionError, '새 항목'):
                gate.assert_gate(changed, self.document)

    def test_metadata_and_write_require_human_reason(self):
        for field in ('reason', 'client_clue', 'owner'):
            document = deepcopy(self.document)
            document['areas']['D'][0][field] = '  '
            with self.assertRaisesRegex(AssertionError, field + ' 빈칸'):
                gate.assert_gate(self.found, document)
        changed = deepcopy(self.found)
        changed['B'].add('새 실행 진단')
        written = gate.refreshed(changed, self.document)
        self.assertEqual(written['areas']['D'], self.document['areas']['D'])
        row = next(r for r in written['areas']['B'] if r['key'] == '새 실행 진단')
        self.assertEqual([row[k] for k in ('reason', 'client_clue', 'owner')], ['', '', ''])
        with self.assertRaisesRegex(AssertionError, 'reason 빈칸'):
            gate.assert_gate(changed, written)

    def test_empty_roster_and_failed_scenario(self):
        with self.assertRaisesRegex(AssertionError, '구원자 0명'):
            gate.collect(db=SimpleNamespace(units={}))
        with patch.object(gate.api, 'simulate', side_effect=RuntimeError('실행 결함 주입')):
            with self.assertRaisesRegex(AssertionError, '시나리오 실행 실패.*실행 결함 주입'):
                gate.collect()

    def test_collectors_mutations(self):
        # 실제 simulate 3판의 결과를 사용해 수집 경로에 한 줄을 주입함.
        # 재수집은 이 결과를 재사용하여 시뮬 워커/판 수를 불필요하게 늘리지 않음.
        result = gate.api.simulate(['carmen', 'frey', 'claire', 'gwen'],
                                   {'stage': 'cosmo/길레/길레 1단계'},
                                   {'n_runs': 3, 'seed': 1, 'build': 'standard'})
        self.assertTrue(any(p > 0 for p in result['prog_runs']))
        result['unsupported']['runtime']['결함 주입: 실행 중 미지원'] = 1
        result['assumptions_used'].append({'rule': '결함 주입: 새 규칙 가정'})
        # 코스모 전용 필드는 실제 코스모 결과에서 가져옴.
        raid = gate.api.simulate(['carmen', 'frey', 'claire', 'gwen'],
                                 {'cosmo_raid': {'boss': 'mogulus', 'step': 3, 'level': 0}},
                                 {'n_runs': 3, 'seed': 1, 'build': 'standard'})
        result['cosmo_raid'] = raid['cosmo_raid']
        original_report = gate.support_report
        def injected_report(defs):
            return original_report(defs) + [dict(unit='결함 주입', slot='시험',
                                                 reason='새 미지원', raw='새 정적 줄', critical=False)]
        with patch.object(gate.api, 'simulate', return_value=result), \
                patch.object(gate, 'support_report', side_effect=injected_report):
            changed, _ = gate.collect()
        for area in gate.AREAS:
            self.assertTrue(any('결함 주입' in k for k in changed[area]), area)
        with self.assertRaisesRegex(AssertionError, '클라로 확정하거나 사유와 함께 등록'):
            gate.assert_gate(changed, self.document)
        gate.assert_gate(self.found, self.document)

    def test_zero_progress_and_incomplete_runs(self):
        for progress in ([0, 0, 0], [1]):
            with patch.object(gate.api, 'simulate', return_value={'prog_runs': progress}):
                with self.assertRaisesRegex(AssertionError, '시나리오 실행 실패'):
                    gate.collect()

    def test_season_change_requires_samples(self):
        cfg = gate.read_json(gate.SCENARIOS)
        cfg['bosses'][0] = '새 시즌 보스'
        with self.assertRaisesRegex(AssertionError, '현 시즌 3보스'):
            gate.collect(scenarios=cfg)


if __name__ == '__main__':
    unittest.main()
