# -*- coding: utf-8 -*-
"""구원자 키<->게임 id 매핑 공용 규칙(battlesim/starsavior/savior_ids.py)."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.starsavior.savior_ids import ids_by_key, keys_by_id, uid_resolver

INDEX = {
    '_meta': {'x': 1},
    '100': {'key': 'aaa', 'profile': {'name': '유일'}},
    '200': {'key': 'ser-1', 'profile': {'name': '세레스'}},
    '201': {'key': 'ser-2', 'profile': {'name': '세레스'}},
    '300': {'profile': {'name': '키없음'}},
}
DB = SimpleNamespace(units={
    'aaa': {'id': 100}, 'source-1058@개화': {'id': 1058}, 'source-1058': {'id': 1058}, 'ser-1': {'id': 200}})  # 변형이 먼저


class SaviorIdsTest(unittest.TestCase):
    def test_keys_by_id(self):
        self.assertEqual(keys_by_id(INDEX), {100: 'aaa', 200: 'ser-1', 201: 'ser-2'})

    def test_db_fill_skips_variants(self):
        k = keys_by_id(INDEX, DB)
        self.assertEqual(k[1058], 'source-1058')  # 색인에 없는 DB 구원자
        self.assertEqual(sum(1 for v in k.values() if v.startswith('source-1058')), 1)  # '@' 변형 제외

    def test_only_db(self):
        self.assertEqual(sorted(keys_by_id(INDEX, DB, only_db=True)), [100, 200, 1058])  # ser-2 는 DB 에 없음

    def test_ids_by_key_setdefault(self):
        ids = ids_by_key(INDEX, DB)
        self.assertEqual(ids['source-1058'], 1058)
        self.assertEqual(ids['source-1058@개화'], 1058)
        self.assertEqual(ids['aaa'], 100)

    def test_resolver_name_only_when_unique(self):
        r = uid_resolver(INDEX)
        self.assertEqual(r('aaa', 'x'), 100)           # 키 우선
        self.assertEqual(r('없는키', '유일'), 100)      # 이름이 유일
        self.assertIsNone(r('없는키', '세레스'))        # 동명이인은 연결 안 함
        self.assertEqual(r('없는키', '키없음'), 300)     # 키 없는 항목도 이름으로
        self.assertIsNone(r('없는키', '없는이름'))


if __name__ == '__main__':
    unittest.main()
