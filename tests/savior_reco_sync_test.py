# -*- coding: utf-8 -*-
"""data/savior_reco.json 은 journeyhelper 의 assets/savior_reco.json 을 손으로 복사한 것(docs/PORTING.md).
옆 폴더에 journeyhelper 가 있으면 두 파일이 같은지 확인한다(없으면 건너뜀 표식).
실행: python -X utf8 -I tests/savior_reco_sync_test.py"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from tools.runtime import skip_note                              # noqa: E402

MINE = os.path.join(ROOT, 'data', 'savior_reco.json')
THEIRS = os.path.abspath(os.path.join(ROOT, '..', '..', 'journeyhelper', 'src', 'assets', 'savior_reco.json'))


def same_bytes(a, b):
    with open(a, 'rb') as f, open(b, 'rb') as g:
        return f.read().replace(b'\r\n', b'\n') == g.read().replace(b'\r\n', b'\n')


class TestSync(unittest.TestCase):
    def test_copy_matches_journeyhelper(self):
        if not os.path.exists(THEIRS):
            skip_note('savior_reco_sync_test: 옆 journeyhelper 저장소 없음')
            return
        self.assertTrue(same_bytes(MINE, THEIRS),
                        'data/savior_reco.json 과 journeyhelper/src/assets/savior_reco.json 이 다름 — '
                        '생성기는 journeyhelper 의 tools/extract_savior_reco.py, 복사 절차는 docs/PORTING.md')

    def test_compare_ignores_only_line_endings(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            a, b, c = (os.path.join(d, n) for n in 'abc')
            open(a, 'wb').write(b'{"x":1}\n')
            open(b, 'wb').write(b'{"x":1}\r\n')
            open(c, 'wb').write(b'{"x":2}\n')
            self.assertTrue(same_bytes(a, b))
            self.assertFalse(same_bytes(a, c))


if __name__ == '__main__':
    unittest.main()
