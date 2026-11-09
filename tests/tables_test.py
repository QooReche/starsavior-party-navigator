# -*- coding: utf-8 -*-
"""tools/tables.py: 주석 달린 표 읽기."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.tables import jsonc, rows


class TablesTest(unittest.TestCase):
    def write(self, text, bom=False):
        d = Path(tempfile.mkdtemp())
        p = d / 't.json'
        p.write_bytes((b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8'))
        return p

    def test_comments_and_trailing_commas(self):
        p = self.write('{\n  // 주석\n  "Data": [\n    {"a": 1, "b": "x",}, // 끝\n  ],\n}\n')
        self.assertEqual(jsonc(p), {'Data': [{'a': 1, 'b': 'x'}]})

    def test_double_slash_inside_string_kept(self):
        p = self.write('{"Data": [{"u": "http://a/b", "q": "a\\"//b"}]}')  # 따옴표 이스케이프 뒤 // 도 문자열 안
        self.assertEqual(rows(p), [{'u': 'http://a/b', 'q': 'a"//b'}])

    def test_rows_unwrap_and_bom(self):
        self.assertEqual(rows(self.write('{"Data": [1, 2]}', bom=True)), [1, 2])
        self.assertEqual(rows(self.write('[3, 4]')), [3, 4])


if __name__ == '__main__':
    unittest.main()
