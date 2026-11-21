# -*- coding: utf-8 -*-
"""battlesim.datafile(엔진 자료 읽기 공용, 설계 fable_unify 2단계 A3) 계약.

  - 같은 파일은 한 번만 파싱해 같은 객체를 돌려준다. 없는 파일은 default(캐시 안 함), default 없으면 FileNotFoundError.
  - api.clear_engine_caches() 가 datafile.clear() 로 파싱 캐시와 @cached 파생 캐시를 비운다(코스모 use_data 도 이 길).
  - @cached 는 f() 와 f(SRC) 를 같은 열쇠로 본다.

  python -X utf8 -I tests/datafile_test.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from battlesim import api, datafile, mc   # noqa: E402
from battlesim.starsavior import cosmo_raid, foe   # noqa: E402
from battlesim.starsavior.data import SRC   # noqa: E402


class DataFile(unittest.TestCase):
    def test_parse_once_and_clear(self):
        a = datafile.load('buff_flags')
        self.assertIs(datafile.load('buff_flags', SRC), a)
        self.assertIs(mc.buff_flags(), a)
        api.clear_engine_caches()
        b = datafile.load('buff_flags')
        self.assertIsNot(b, a, 'clear_engine_caches 가 자료 캐시를 비우지 않음')
        self.assertEqual(b, a)

    def test_derived_cache_cleared(self):
        g = mc._global_turn()
        self.assertIs(mc._global_turn(), g)
        api.clear_engine_caches()
        self.assertIsNot(mc._global_turn(), g, '@cached 파생 캐시가 clear 로 안 비워짐')
        s = foe.spawn_flags()
        self.assertIs(foe.spawn_flags(SRC), s, 'f() 와 f(SRC) 가 다른 열쇠')

    def test_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(datafile.load('auto_skill', d, {}), {})
            self.assertEqual(mc.auto_skill_order(d), {})
            self.assertEqual(mc.ally_auto_lines(d), {})
            self.assertEqual(foe.sudden_death(d), {'groups': {}, 'stages': {}})
            with self.assertRaises(FileNotFoundError):
                datafile.load('auto_skill', d)

    def test_use_data_keyed_by_path(self):
        fx = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'cosmo_raid_1022.json')
        try:
            cur = cosmo_raid.load()
            cosmo_raid.use_data(fx)
            old = cosmo_raid.load()
            self.assertNotEqual([b['key'] for b in old['bosses']], [b['key'] for b in cur['bosses']])
            self.assertIs(cosmo_raid._DATA[cosmo_raid.data_path()], old)
        finally:
            cosmo_raid.use_data(None)
        self.assertEqual(cosmo_raid.load(), cur)

    def test_dedup_rows(self):
        self.assertEqual(mc._dedup_rows([('a', 'x', 1), ('a', 'x', 1), ('b', 'y', 1), ('b', 'y', 2)]), {('a', 'x'): 1})

    def test_base_name(self):
        self.assertEqual(mc.base_name('보호막 (해제 불가) '), '보호막 (해제 불가)')
        self.assertEqual(mc.base_name('보호막 (해제 불가)'), '보호막')
        self.assertEqual(mc.base_name('보호막(해제불가)'), '보호막')


if __name__ == '__main__':
    unittest.main()
