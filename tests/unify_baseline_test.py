# -*- coding: utf-8 -*-
"""엔진 공통 함수 통일 보강 기준선 시험(tools/unify_baseline.py, 설계 fable_unify 0단계).

diet_baseline 이 안 덮는 경로 — 코스모(시즌 1023 + 1022 fixture 벨그라스·티리아·카넬리아), 길드 레이드 지원 6종,
캐릭터 분기 표 대상 구원자(savior_rules.table_keys()), 연쇄 피해 4경로 — 의 결과 해시가 tests/golden/unify_baseline.json 과 바이트 일치.
덮는지도 확인: 진행도 > 0, 표의 구원자가 모두 파티에 있음, 연쇄 4경로가 각각 실제로 탔음.

  python -X utf8 -I tests/unify_baseline_test.py
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import unify_baseline as U  # noqa: E402
from battlesim.starsavior import savior_rules as R  # noqa: E402


class UnifyBaseline(unittest.TestCase):
    def test_baseline_same_and_covers(self):
        with open(U.GOLDEN, encoding='utf-8') as f:
            want = json.load(f)['cases']
        got, cnt, per = U.compute(count=True)
        self.assertEqual(sorted(got), sorted(want))
        bad = [k for k in got if got[k] != want[k]]
        self.assertEqual(bad, [], '보강 기준선과 다른 케이스')
        self.assertTrue(all(v['prog'] > 0 for v in got.values()), [k for k, v in got.items() if v['prog'] <= 0])
        # 연쇄 4경로 각각 실제로 탄 판이 있다(5단계 피해식 조각 치환을 잡으려면 필요)
        for tag in ('battle_chain', 'queue_punish', 'cosmo_chain_hit', 'guild_chain'):
            self.assertGreater(cnt[tag], 0, tag)
        # 지원 5종이 모두 있다 + 벨그라스 fixture 케이스가 있다
        for sup in ('gust', 'focus', 'strike', 'mountain', 'fire'):
            self.assertTrue(any(k.startswith('guild_%s_' % sup) for k in got), sup)
        self.assertTrue(any(k.startswith('raid1022_belgras') for k in got))
        units = {u for c in U.CASES for _, us in c[4] for u in us}
        # 분기 표 구원자는 표에서 읽음(savior_rules_test.test_baseline_covers_table 과 같은 출처 — 구원자가 늘면 여기서 걸림)
        self.assertEqual(sorted(R.table_keys() - units), [])


if __name__ == '__main__':
    unittest.main()
