"""표시 변경은 버전을 유지하고 계산 입력·알 수 없는 필드는 반드시 반영함."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.guild_version import season_version
from battlesim.starsavior.guild import load


class GuildVersionTest(unittest.TestCase):
    def test_display_only(self):
        for sid in (30111, 30112):
            g = copy.deepcopy(load(sid))
            g.pop('dataVersion', None)
            edited = copy.deepcopy(g)
            edited['challenge']['effectText']['hpDrain'] += ' 표시 수정'
            edited['challenge']['note'] += ' 표시 수정'
            edited['challenge']['statNote'] = '표시 수정'
            edited['asOf'] = '2099-01-01'
            edited['provenance']['source'] = '다른 근거 줄'
            edited['season']['label'] = '표시 시즌'
            edited['season']['start'] = '2099-01-01'
            edited['sets']['items'][0]['name'] = '표시 이름'
            if 'client' in edited:
                edited['client']['challenge']['effectText']['hpDrain'] = '표시 수정'
            self.assertEqual(season_version(g), season_version(edited))

    def test_calculation_inputs(self):
        g = copy.deepcopy(load(30112))
        for change in (
            lambda x: x['steps'][0]['waves'][0][0]['stats'].__setitem__('atk', 987654),
            lambda x: x['supports'][0]['effects'][0].__setitem__('chance', 4321),
            lambda x: x['sets']['items'][0]['tiers'][0].__setitem__('text', '피해 +99%'),
            lambda x: x['search'].__setitem__('excludeText', ['협공']),
            lambda x: x['sets'].__setitem__('enabled', True),
            lambda x: x.__setitem__('futureCalculationInput', 1),
        ):
            edited = copy.deepcopy(g)
            change(edited)
            self.assertNotEqual(season_version(g), season_version(edited))

    def test_bfb_client_and_assets_are_inputs(self):
        g = copy.deepcopy(load(30111))
        for change in (
            lambda x: x['client']['steps'][0]['waves'][0][0]['stats'].__setitem__('atk', 987654),
            lambda x: x['assets']['guild_bfb'].__setitem__('sha256', 'changed'),
            lambda x: x['dependencies'].__setitem__('data/foe.json', 'changed'),
        ):
            edited = copy.deepcopy(g)
            change(edited)
            self.assertNotEqual(season_version(g), season_version(edited))

    def test_stored_versions_and_archive(self):
        import guild_defense as gd
        for sid in range(30101, 30113):
            g = load(sid)
            self.assertEqual(g['dataVersion'], season_version(g))
        self.assertIsNotNone(gd.sim_payload(load(30111)))


if __name__ == '__main__':
    unittest.main()
