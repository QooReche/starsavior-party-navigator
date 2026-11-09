# -*- coding: utf-8 -*-
"""생성물(guild_sim.json·quick.json)이 현재 엔진 규칙 기본값으로 만들어졌는지 + 건너뜀 표식 모으기.
실행: python -X utf8 -I tests/gen_rules_stamp_test.py"""
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from tools import rules_stamp as S                               # noqa: E402
from tools import run_tests as RT                                # noqa: E402
from tools.runtime import skip_note                              # noqa: E402


class TestStamp(unittest.TestCase):
    def test_generated_files_match_current_rules(self):
        bad = S.stale()
        self.assertEqual(bad, [], '규칙 기본값이 바뀐 뒤 %s 를 다시 만들거나 이유를 적어 인정해야 함 '
                         '(tools/rules_stamp.py 머리말 참고)' % bad)

    def test_fingerprint_follows_rule_values(self):
        from battlesim import rules
        before = S.fingerprint()
        with mock.patch.dict(rules.MC_OPTS, {'foe_react_buff_count': 'harmful'}):
            self.assertNotEqual(S.fingerprint(), before)
        self.assertEqual(S.fingerprint(), before)

    def test_stale_detects_old_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'stamp.json')
            with mock.patch.object(S, 'STAMP', path):
                self.assertEqual(S.stale(), list(S.NAMES))          # 도장 없음 = 옛 규칙
                S.stamp('quick', '시험')
                self.assertEqual(S.stale(), ['guild_sim'])
                with mock.patch.object(S, 'fingerprint', return_value='0' * 16):
                    self.assertEqual(S.stale(), list(S.NAMES))      # 규칙이 바뀌면 둘 다 낡음

    def test_stamp_requires_reason(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(S, 'STAMP', os.path.join(d, 's.json')):
            with self.assertRaises(ValueError):
                S.stamp('quick', '  ')
            with self.assertRaises(ValueError):
                S.stamp('nope', '이유')


class TestSkipMarker(unittest.TestCase):
    def test_runner_collects_skip_note_and_unittest_skips(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            skip_note('x_test.test_a: node 없음')
        found = [m.group(0) for m in RT.SKIP_RE.finditer(buf.getvalue())]
        self.assertEqual(len(found), 1)
        self.assertIn('node 없음', found[0])
        self.assertTrue(RT.SKIP_RE.search('Ran 3 tests\n\nOK (skipped=1)\n'))
        self.assertIsNone(RT.SKIP_RE.search('Ran 3 tests\n\nOK\n'))


if __name__ == '__main__':
    unittest.main()
