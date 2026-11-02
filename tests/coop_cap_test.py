# -*- coding: utf-8 -*-
"""협공 확률 버프가 옛 30% 상한을 넘을 때 새 기본값의 실제 협공 횟수를 검증한다."""
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
from battlesim import simulate  # noqa: E402
from battlesim.mc import Battle  # noqa: E402


class CoopCapTest(unittest.TestCase):
    def test_buff_above_legacy_cap_increases_coops(self):
        # 공개 표의 아세라 / 왈츠 오브 스타라이트. 계정 자료 없이 표준 육성만 쓴다.
        party = ['emily', 'waltz-asherah', 'hilde', 'ceres-sun-supporter']
        stage = {'stage': 'clo/태양 회랑/FLOOR 250'}
        opts = dict(seed=17, n_runs=20, build='standard')
        seen = []
        original = Battle.coop

        def spy(battle, actor, ctx):
            seen.extend(b.mods()['coop'] for b in battle.allies if b is not actor and not b.dead)
            return original(battle, actor, ctx)

        with patch.object(Battle, 'coop', spy):
            current = simulate(party, stage, opts)
        self.assertTrue(any(p > 0.30 for p in seen), '30% 초과 버프 경로를 실제로 타야 함')
        legacy = simulate(party, stage, dict(opts, formula_override={'COOP_CAP': 0.30}))
        for result in (current, legacy):
            self.assertGreater(result['outcome']['progress'], 0)
            self.assertGreater(result['ally_via'].get('coop', 0), 0)
        self.assertGreater(current['ally_via']['coop'], legacy['ally_via']['coop'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
