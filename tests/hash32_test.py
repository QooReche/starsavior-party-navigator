# -*- coding: utf-8 -*-
"""행동 우선순위 시드의 튜플 해시가 브라우저(Pyodide wasm32)와 같은지(HANDOFF 34).

내장 hash() 는 Py_hash_t 폭에 따라 값이 달라 64비트 PC 결과가 사이트와 갈렸음 — mc._tuple_hash32 가 32비트 값을 직접 계산.
정답은 실제 32비트 CPython 3.12.1(Pyodide 0.26.4 와 같은 버전)의 hash(tuple) 출력(tests/fixtures/hash32_cpython312_32bit.json).
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from battlesim import mc  # noqa: E402

FIX = os.path.join(ROOT, 'tests', 'fixtures', 'hash32_cpython312_32bit.json')


class Hash32(unittest.TestCase):
    def test_matches_32bit_cpython(self):
        cases = json.load(open(FIX, encoding='utf-8'))['cases']
        self.assertGreater(len(cases), 250)
        bad = [(c, h) for c, h in cases if mc._tuple_hash32(tuple(c)) != h]
        self.assertEqual(bad, [])

    def test_builtin_when_32bit(self):
        if sys.hash_info.width != 32:
            self.skipTest('64비트 파이썬 — 정답 파일로만 대조')
        for c, _ in json.load(open(FIX, encoding='utf-8'))['cases']:
            self.assertEqual(mc._tuple_hash32(tuple(c)), hash(tuple(c)))

    def test_prio_seed_uses_portable_hash(self):
        # 일부러 깨뜨려 보기: 내장 hash 로 되돌리면 64비트에서 시드가 달라져야 이 검사가 의미 있음
        import random
        st = random.Random(1).getstate()[1][:8]
        if sys.hash_info.width == 64:
            self.assertNotEqual(hash(st), mc._tuple_hash32(st))
        src = open(os.path.join(ROOT, 'battlesim', 'mc.py'), encoding='utf-8').read()
        self.assertIn('random.Random(_tuple_hash32(st[:8]) ^ 0x5EED1962)', src)
        self.assertNotIn('hash(st[:8])', src.replace('_tuple_hash32(st[:8])', ''))


if __name__ == '__main__':
    unittest.main()
