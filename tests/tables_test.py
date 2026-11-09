# -*- coding: utf-8 -*-
"""tools/tables.py: 주석 달린 표 읽기."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json

from tools.tables import UnknownName, buff_names, jsonc, names_of, rows


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

    def test_names_of_dedupes_and_rejects_unknown(self):
        bname = {'A': '공격력 증가', 'B': '공격력 증가', 'C': '방어력 증가'}
        self.assertEqual(names_of(['A', 'B', 'C'], bname), ['공격력 증가', '방어력 증가'])
        with self.assertRaises(UnknownName):
            names_of(['A', 'Z'], bname)

    def test_buff_names_skips_buffs_without_korean_name(self):
        d = Path(tempfile.mkdtemp())
        (d / 'Strings').mkdir()
        (d / 'Strings' / 'STRING_COMMON_ko_en.json').write_text(
            json.dumps({'S1': {'ko': '공격력 증가'}, 'S2': {'en': 'x'}}), encoding='utf-8')
        (d / 'BUFF_TEMPLET.json').write_text(json.dumps({'Data': [
            {'m_BuffStrID': 'B1', 'm_BuffName': 'S1'}, {'m_BuffStrID': 'B2', 'm_BuffName': 'S2'},
            {'m_BuffStrID': 'B3'}, {'m_BuffStrID': 'B4', 'm_BuffName': None}]}), encoding='utf-8')
        self.assertEqual(buff_names(d), {'B1': '공격력 증가'})


if __name__ == '__main__':
    unittest.main()
