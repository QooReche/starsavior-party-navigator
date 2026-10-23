# -*- coding: utf-8 -*-
"""MC 의미 해석 캐시 시험: semantic_cache 가 런 간 normalized_lines 를 공유하면서 결과 바이트가 달라지지 않는지 확인.

  python -X utf8 -I tests/mc_cache_test.py            # 전부
  python -X utf8 -I tests/mc_cache_test.py multiwave  # 이름에 이 글자가 든 시험만

안전 시험(「일부러 깨뜨렸을 때 실패하는지」) 항목:
  test_cache_stale_invalidation: d.lines 교체 후 캐시가 무효화돼 재계산되는지 확인
  test_cache_wrong_key_breaks: 잘못된 키로 오염된 캐시가 결과를 바꾸는지 확인
    ↳ 결과가 달라져야 시험이 의미 있음. 달라지지 않으면 시험 로직 점검 필요."""
import hashlib
import json
import os
import random
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

from battlesim.api import _CustomFoe, simulate  # noqa: E402
from battlesim.mc import Battle  # noqa: E402
from battlesim.rules import MC_OPTS  # noqa: E402
from battlesim.starsavior.mc_semantics import normalized_lines  # noqa: E402

# 두 웨이브 인카운터 — semantic_cache 런 간 공유 효과가 드러나는 기본 시나리오
_ENC = {
    'waves': [
        [dict(name='w1', hp=3000, atk=500, spd=200)],
        [dict(name='w2', hp=3000, atk=500, spd=50)],
    ],
    'max_turns': 30,
}


def _unit(name='u', role='스트라이커', hp=10000, atk=1000, df=500, spd=100, cr=0.2, skills=None, **kw):
    return _CustomFoe(
        dict(name=name, role=role, hp=hp, atk=atk, **{'def': df}, spd=spd, cr=cr, cd=1.5, er=0, der=0,
             skills=skills or [dict(slot='기본기', dm=100)], **kw),
        0,
    )


def _sig(r):
    """simulate 결과에서 결정적 필드만 추출."""
    return {'outcome': r['outcome'], 'per_unit': r['per_unit']}


def _h(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


class CacheIdentityTest(unittest.TestCase):
    """semantic_cache 유무와 무관하게 결과가 동일해야 한다."""

    # 고정 해시 — 구현이 바뀌어도 이 값이 달라지면 결과 바이트가 달라진 것이다.
    _H_GWEN_MULTIWAVE = '54bd080d2cb4'       # gwen 1인 10판, seed=7, 2웨이브
    _H_PM_GWEN_MULTIWAVE = 'c4af24f6167e'   # professor-m + gwen 10판, seed=7, 2웨이브 (반응 스킬)
    _H_GWEN_RNG_STREAMS = 'b3893e9e7fa5'    # gwen 1인 rng_streams=True 10판, seed=7

    def test_gwen_multiwave_hash_locked(self):
        """[캐시-1] gwen 2웨이브 결과 해시 고정 — 캐시 때문에 바뀌면 안 된다."""
        r = simulate([{'key': 'gwen'}], _ENC, {'n_runs': 10, 'seed': 7})
        self.assertEqual(_h(_sig(r)), self._H_GWEN_MULTIWAVE)

    def test_pm_gwen_multiwave_hash_locked(self):
        """[캐시-2] professor-m + gwen 2웨이브 해시 고정 — 반응 스킬 포함 시나리오."""
        r = simulate(['professor-m', 'gwen'], _ENC, {'n_runs': 10, 'seed': 7})
        self.assertEqual(_h(_sig(r)), self._H_PM_GWEN_MULTIWAVE)

    def test_gwen_rng_streams_hash_locked(self):
        """[캐시-3] rng_streams=True 해시 고정 — 스트림 분리 모드에서도 캐시 안전."""
        r = simulate([{'key': 'gwen'}], _ENC, {'n_runs': 10, 'seed': 7, 'rng_streams': True})
        self.assertEqual(_h(_sig(r)), self._H_GWEN_RNG_STREAMS)


class CacheMechanicsTest(unittest.TestCase):
    """Battle.lines_of 캐시 메커니즘 단위 시험."""

    def _make_ally(self):
        return [_unit('a%d' % i) for i in range(3)]

    def _make_waves(self):
        return [[_unit('f1')], [_unit('f2')]]

    def _battle(self, ally, waves, seed=1, semantic_cache=None, **kw):
        mc = dict(MC_OPTS, rand_range=[1.0, 1.0], target_mode='first')
        b = Battle(ally, waves, random.Random(seed), mc=mc, semantic_cache=semantic_cache, **kw)
        return b

    def test_no_cache_vs_shared_cache_identical(self):
        """[캐시-4] semantic_cache 없음과 있음의 결과가 동일."""
        ally = self._make_ally()
        waves = self._make_waves()
        sc = {}
        dmg_no = []
        dmg_sc = []
        for seed in range(5, 10):
            b = self._battle(ally, waves, seed=seed)
            b.run()
            dmg_no.append(round(sum(u.dmg for u in b.allies), 6))

            b2 = self._battle(ally, waves, seed=seed, semantic_cache=sc)
            b2.run()
            dmg_sc.append(round(sum(u.dmg for u in b2.allies), 6))

        self.assertEqual(dmg_no, dmg_sc)

    def test_shared_cache_populated_after_run(self):
        """[캐시-5] run 후 semantic_cache 에 def 항목이 채워진다."""
        ally = self._make_ally()
        waves = self._make_waves()
        sc = {}
        b = self._battle(ally, waves, seed=1, semantic_cache=sc)
        b.run()
        # 3 아군 + 2 웨이브 각 1적 = 최대 5, 실제로 lines_of 를 호출한 것만 들어감
        self.assertGreater(len(sc), 0)

    def test_cache_stale_invalidation(self):
        """[캐시-6][안전] d.lines 교체 후 캐시가 무효화돼 재계산된다.

        캐시 항목이 is-check 로 무효화되는지 검증.
        lines 를 새 리스트로 교체하면 캐시가 무효화돼 새로 계산된 값을 돌려준다."""
        ally = [_unit('a')]
        foes = [[_unit('f')]]   # waves 는 list[list[def]]
        sc = {}
        b = self._battle(ally, foes, seed=1, semantic_cache=sc)
        b.spawn_wave()
        u = b.allies[0]

        # 첫 호출: 캐시 미스 → 계산 후 저장
        r1 = b.lines_of(u)
        key = id(u.d)
        self.assertIn(key, sc)
        self.assertIs(sc[key][2], r1)  # 캐시에서 같은 객체가 나와야 함

        # d.lines 를 새 리스트로 교체 → 캐시 is-check 실패
        original_lines = u.d.lines
        u.d.lines = list(original_lines)   # 새 리스트 객체(is 비교 실패)
        r2 = b.lines_of(u)

        # 무효화 후 새로 계산했으므로 sc[key] 가 갱신돼야 함
        self.assertIs(sc[key][0], u.d.lines)  # 새 lines 참조로 업데이트됨

        # 원복
        u.d.lines = original_lines

    def test_rng_streams_identical_with_cache(self):
        """[캐시-7] rng_streams=True 에서도 cache 결과 동일."""
        ally = self._make_ally()
        waves = self._make_waves()
        dmg_no, dmg_sc = [], []
        for seed in range(3, 8):
            b = self._battle(ally, waves, seed=seed, rng_streams=True)
            b.run()
            dmg_no.append(round(sum(u.dmg for u in b.allies), 6))

            b2 = self._battle(ally, waves, seed=seed, rng_streams=True, semantic_cache={})
            b2.run()
            dmg_sc.append(round(sum(u.dmg for u in b2.allies), 6))

        self.assertEqual(dmg_no, dmg_sc)

    def test_cache_tamper_is_detected_by_lines_ref(self):
        """[캐시-8][안전] sc 항목의 lines_ref 를 엉뚱한 객체로 바꾸면 is-check 가 실패해 재계산된다.

        이것이 「일부러 깨뜨린」 케이스다:
          1) 캐시 항목의 lines_ref 를 다른 객체로 교체
          2) lines_of 호출 → is-check 실패 → normalized_lines 재계산
          3) sc 가 올바른 lines_ref 로 갱신된다
        재계산이 일어나지 않으면 this test fails(is-check 로직 손상)."""
        ally = [_unit('a')]
        foes = [[_unit('f')]]
        sc = {}
        b = self._battle(ally, foes, seed=1, semantic_cache=sc)
        b.spawn_wave()
        u = b.allies[0]

        # 캐시 웜업
        r1 = b.lines_of(u)
        key = id(u.d)
        original_entry = sc[key]

        # 캐시 오염: lines_ref 를 빈 리스트로 바꿔서 is-check 를 강제 실패시킴
        sc[key] = ([], original_entry[1], original_entry[2])

        # lines_of 는 is-check 실패 → 재계산 → sc[key] 갱신
        r2 = b.lines_of(u)
        updated_entry = sc[key]

        # lines_ref 가 실제 u.d.lines 로 복구됐는지 확인
        self.assertIs(updated_entry[0], u.d.lines,
                      'is-check 실패 후 sc 항목이 실제 d.lines 참조로 갱신돼야 함')
        # 재계산 결과는 sc 에 새로 저장된 항목과 동일한 객체여야 함
        self.assertIs(r2, updated_entry[2],
                      'lines_of 반환값이 sc 에 갱신된 항목과 동일해야 함')


if __name__ == '__main__':
    filter_kw = sys.argv[1] if len(sys.argv) > 1 else None
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [CacheIdentityTest, CacheMechanicsTest]:
        for name in loader.getTestCaseNames(cls):
            if filter_kw is None or filter_kw in name:
                suite.addTest(cls(name))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
