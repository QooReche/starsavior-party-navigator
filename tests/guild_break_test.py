# -*- coding: utf-8 -*-
"""시즌4 표준 육성: 길방 브레이크 자연 적립·발동과 웹 옵션 전달."""
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from battlesim import simulate
from battlesim import web

PARTY = {'units': ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria']}
GUILD = {'level': 0, 'sets': [0, 0, 0, 0], 'support': 'gust'}
SKILL = {'name': '스타피어서', 'level': 5}


class GuildBreakTest(unittest.TestCase):
    def test_natural_activation(self):
        r = simulate(PARTY, {'guild': GUILD},
                     {'seed': 2, 'n_runs': 3, 'build': 'standard', 'break_skill': SKILL})
        self.assertGreater(r['outcome']['progress'], 0)
        bs = r['break_skill']
        self.assertTrue(bs['supported'])
        self.assertGreater(bs['points_gained'], 0)
        self.assertGreater(bs['uses'], 0)
        self.assertGreater(bs['dmg'], 0)
        print('BFB standard:', r['outcome']['progress'], bs)

    def test_web_options(self):
        # 실제 웹 진입점 → 엔진. 적립·쿨·포인트를 강제로 주지 않는다.
        observed = []
        def run(party, encounter, options):
            self.assertEqual(encounter, {'guild': GUILD})
            observed.append(options.get('break_skill'))
            return simulate(party, encounter, options)
        with patch.object(web, 'simulate', side_effect=run):
            for skill in (None, {'name': '미지원 시험 스킬', 'level': 5}, SKILL):
                r = json.loads(web.run_auto('길방 시즌4', PARTY, 3, 2,
                    {'guild': GUILD, 'build': 'standard', 'break_skill': skill}))
                self.assertGreater(r['prog'], 0)
                self.assertEqual(r['bs']['supported'], skill == SKILL)
                if skill == SKILL:
                    self.assertGreater(r['bs']['uses'], 0)
                else:
                    self.assertEqual(r['bs']['uses'], 0)
        self.assertEqual(observed, [None, {'name': '미지원 시험 스킬', 'level': 5}, SKILL])


if __name__ == '__main__':
    unittest.main()
