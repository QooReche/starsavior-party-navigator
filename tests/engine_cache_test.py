# -*- coding: utf-8 -*-
"""엔진 캐시 시험(코스모 전수 탐색 가속): 구원자 정의 캐시·시즌 인카운터 캐시·줄 종류 색인·지원 보고 메모를 켠 결과가 끈 결과와 완전히 같아야 한다.

  python -X utf8 -I tests/engine_cache_test.py

안전 시험(일부러 깨뜨리면 실패해야 하는 것):
  test_wrong_cache_key_is_detected: 캐시 키에서 stats_override 를 빼면(틀린 키) 다른 능력치 팀이 같은 정의를 받아 결과가 달라진다 -> 시험이 그 차이를 잡는지 확인
  test_kind_index_stale_is_detected: 줄 종류 색인이 낡은 값을 돌려주면 결과가 달라지는지 확인"""
import itertools
import json
import os
import random
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

from battlesim import api, mc, simulate, web          # noqa: E402
from battlesim.starsavior.data import get_db          # noqa: E402

KEYS = ['amora', 'bell', 'bunny-charlotte', 'carmen', 'carnelia', 'ceres', 'claire', 'dana', 'elisa', 'gwen', 'harley', 'tyria']
BOSSES = ('belgras', 'tyria', 'carnelia')


def _scaled(key, f_hp, f_atk):
    d = api._norm_party([key], get_db(), 'fixed', 'standard')[0][0]
    return {'key': key, 'stats_override': {'hp': int(d.stats['hp'] * f_hp), 'atk': int(d.stats['atk'] * f_atk), 'def': d.stats['def']}, 'power': 90000}


def _parties(n=14, seed=5):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        ks = rnd.sample(KEYS, 4)
        units = [(_scaled(k, 1 + rnd.random(), 1 + rnd.random()) if rnd.random() < 0.7 else {'key': k}) for k in ks]
        out.append({'units': units, 'leader': 0})
    return out


def _run(party, boss, level, n=2, seed=3):
    r = simulate(party, {'cosmo_raid': {'boss': boss, 'step': 3, 'level': level}}, {'build': 'standard', 'n_runs': n, 'seed': seed, 'rules_override': {'power_penalty': 'model'}})
    r.pop('runtime_ms_per_run', None)
    return json.dumps(r, sort_keys=True, ensure_ascii=False, default=str)


def _all(parties, levels=(0, 6)):
    return [_run(p, b, lv) for p in parties for b in BOSSES for lv in levels]


class Switch:
    def __init__(self, on):
        self.on = on

    def __enter__(self):
        self.old = mc.ENGINE_CACHE
        mc.ENGINE_CACHE = self.on
        api.clear_engine_caches()

    def __exit__(self, *a):
        mc.ENGINE_CACHE = self.old
        api.clear_engine_caches()


class EngineCacheTest(unittest.TestCase):
    def test_cache_on_equals_off(self):
        """[E-1] 파티 14개 x 보스 3 x 레벨 2 = 84 전투: 캐시 끔 / 켬(차가운 시작) / 켬(데운 뒤) 결과(통계 전부, 지원 보고 포함)가 같다"""
        parties = _parties()
        with Switch(False):
            ref = _all(parties)
        with Switch(True):
            cold = _all(parties)
            warm = _all(parties)                  # 두 번째는 캐시가 채워진 상태
            self.assertGreater(len(api._UNIT_CACHE), 0)
            self.assertGreater(len(api._ENC_CACHE), 0)
        self.assertEqual(ref, cold)
        self.assertEqual(ref, warm)
        sc = [x for s in ref for x in json.loads(s)['cosmo_raid']['score_runs']]
        self.assertGreater(len(set(sc)), 20)                            # 점수가 판마다 다르게 나옴 = 전투가 실제로 진행됨

    def test_support_report_memo_identical(self):
        """[E-1b] 지원 보고 메모: 전체 구원자(+보스)를 4명씩 묶어 메모 없이/있이 보고한 목록이 같고, 보고가 비어 있지 않은 묶음이 있다"""
        db = get_db()
        keys = sorted(db.units)
        encs = [api._norm_encounter_raw({'cosmo_raid': {'boss': b, 'step': 3, 'level': 0}}) for b in BOSSES]
        defs = [api._norm_party_raw([k], db, 'fixed', 'standard')[0][0] for k in keys]
        rnd = random.Random(11)
        groups = [rnd.sample(defs, rnd.randint(1, 6)) for _ in range(150)]
        groups += [[d] for d in defs] + [defs] + [[d] for d in defs]      # 혼자일 때 / 전원이 모였을 때(다른 구원자의 표지 이름 때문에 보고가 달라지는 정의가 있음) / 다시 혼자일 때
        nonempty = 0
        with Switch(True):
            memo_runs = []
            for g in groups:
                waves = rnd.choice(encs)[0] if rnd.random() < 0.5 else []
                allw = g + [d for w in waves for d in w]
                memo_runs.append((allw, mc.support_report(allw)))
        for allw, got in memo_runs:
            with Switch(False):
                ref = mc.support_report(allw)
            self.assertEqual(ref, got)
            nonempty += bool(ref)
        self.assertGreater(nonempty, 0, '보고가 전부 비어 있으면 이 시험은 아무것도 지키지 않음')

    def test_def_memo_separates_stamps_and_invalidates(self):
        """[E-1c] 정의 메모: 입력 표식(stamp)이 다르면 따로 계산하고, d.lines 가 바뀌거나 복사본이면 다시 계산하며, 항목은 8개를 넘지 않는다.
        (실제 데이터에서는 표지 이름 합집합이 보고를 거의 바꾸지 않아 결과 비교만으로는 stamp 오류를 못 잡으므로 메커니즘을 직접 확인한다)"""
        import copy
        d = api._norm_party_raw(['amora'], get_db(), 'fixed', 'standard')[0][0]
        with Switch(True):
            self.assertEqual(mc._def_memo(d, '_t', 'A', lambda: 'a1'), 'a1')
            self.assertEqual(mc._def_memo(d, '_t', 'A', lambda: 'XX'), 'a1')       # 같은 표식 = 메모 사용
            self.assertEqual(mc._def_memo(d, '_t', 'B', lambda: 'b1'), 'b1')       # 다른 표식 = 새로 계산
            c = copy.copy(d)
            self.assertEqual(mc._def_memo(c, '_t', 'A', lambda: 'c1'), 'c1')       # 복사본에 딸려 온 메모는 쓰지 않음
            old = d.lines
            d.lines = list(old) + list(old[:1])
            self.assertEqual(mc._def_memo(d, '_t', 'A', lambda: 'a2'), 'a2')       # lines 가 바뀌면 무효
            d.lines = old
            for i in range(30):
                mc._def_memo(d, '_t', 'k%d' % i, lambda: i)
            self.assertLessEqual(len(d._t[3]), 8)

    def test_run_auto_cosmo_summary_identical(self):
        """[E-2] 작업자 진입점(run_auto) 출력 문자열도 같다"""
        parties = _parties(6, seed=9)
        o = json.dumps({'build': 'standard', 'rules_override': {'power_penalty': 'model'}, 'cosmo_raid': {'boss': 'belgras', 'step': 3, 'level': 0}, 'cosmo_top_q': 0.2})
        with Switch(False):
            ref = [web.run_auto('x', p, 2, 1, o) for p in parties]
        with Switch(True):
            cold = [web.run_auto('x', p, 2, 1, o) for p in parties]
            warm = [web.run_auto('x', p, 2, 1, o) for p in parties]
        self.assertEqual(ref, cold)
        self.assertEqual(ref, warm)

    def test_lru_bounded(self):
        """[E-3] 서로 다른 구원자 설정이 계속 들어와도 캐시 크기가 상한을 넘지 않는다(시전마다 쌓이는 키 없음: 전투 중 캐시는 정의 객체에 붙어 정의와 함께 사라진다)"""
        old = (api._UNIT_CACHE.maxsize, api._ENC_CACHE.maxsize)
        api._UNIT_CACHE.maxsize, api._ENC_CACHE.maxsize = 5, 3
        try:
            with Switch(True):
                db = get_db()
                for i in range(40):
                    api._norm_party([{'key': 'amora', 'stats_override': {'atk': 1000 + i}}], db, 'fixed', 'standard')
                    api._norm_encounter({'cosmo_raid': {'boss': 'belgras', 'step': 3, 'level': i % 18}})
                self.assertEqual(len(api._UNIT_CACHE), 5)
                self.assertEqual(len(api._ENC_CACHE), 3)
        finally:
            api._UNIT_CACHE.maxsize, api._ENC_CACHE.maxsize = old

    def test_same_unit_twice_gets_separate_objects(self):
        """[E-4] 같은 파티에 같은 구원자가 두 번 있어도 정의 객체는 따로(전투 중 서로의 상태를 공유하지 않음)"""
        with Switch(True):
            db = get_db()
            defs, _ = api._norm_party([{'key': 'amora'}, {'key': 'amora'}], db, 'fixed', 'standard')
            self.assertIsNot(defs[0], defs[1])
            again, _ = api._norm_party([{'key': 'amora'}], db, 'fixed', 'standard')
            self.assertIs(again[0], defs[0])         # 캐시가 실제로 재사용됨

    def test_encounter_cache_returns_independent_containers(self):
        """[E-5] 인카운터 캐시가 돌려준 웨이브 목록·메타를 호출자가 고쳐도 다음 호출에 영향이 없다"""
        with Switch(True):
            enc = {'cosmo_raid': {'boss': 'tyria', 'step': 3, 'level': 3}}
            w1, _, fx1, _, m1 = api._norm_encounter(enc)
            n = len(w1)
            w1.append(['x'])
            m1['junk'] = 1
            w2, _, _, _, m2 = api._norm_encounter(enc)
            self.assertEqual(len(w2), n)
            self.assertNotIn('junk', m2)

    def test_wrong_cache_key_is_detected(self):
        """[E-6][안전] 키에서 stats_override 를 빼면 다른 능력치 팀이 같은 정의를 받는다 -> 이 시험의 비교가 그 차이를 잡아야 한다"""
        a = {'units': [_scaled(k, 3.0, 3.0) for k in KEYS[:4]], 'leader': 0}
        b = {'units': [{'key': k} for k in KEYS[:4]], 'leader': 0}
        with Switch(False):
            ref_b = _run(b, 'belgras', 0)
        real = api._unit_key
        api._unit_key = lambda u, db, mode, build, use_combat: (id(db), u['key'], mode, build, bool(use_combat))      # 일부러 틀린 키
        try:
            with Switch(True):
                _run(a, 'belgras', 0)
                broken_b = _run(b, 'belgras', 0)
        finally:
            api._unit_key = real
        self.assertNotEqual(ref_b, broken_b, '틀린 키인데도 결과가 같다 -> 동일성 시험이 키 오류를 못 잡음')

    def test_kind_index_stale_is_detected(self):
        """[E-7][안전] 줄 종류 색인이 항상 빈 값이면 결과가 달라진다(색인을 쓰는 경로가 실제로 탄다)"""
        p = {'units': [{'key': k} for k in KEYS[:4]], 'leader': 0}
        with Switch(False):
            ref = _run(p, 'carnelia', 0, n=3)
        real = mc.Battle.kind_lines
        mc.Battle.kind_lines = lambda self, u, kind: ()
        try:
            with Switch(True):
                broken = _run(p, 'carnelia', 0, n=3)
        finally:
            mc.Battle.kind_lines = real
        self.assertNotEqual(ref, broken)


if __name__ == '__main__':
    unittest.main(verbosity=2)
