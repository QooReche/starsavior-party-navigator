# -*- coding: utf-8 -*-
"""build_party_html: 여정 스탯 우선순위에 빠진 구원자가 있으면 페이지를 쓰기 전에 중단(잘못된 페이지가 저장된 채 남지 않게).
실행: python -X utf8 -I tests/party_html_priority_test.py"""
import os
import sys
import tempfile
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import build_party_html as B                                     # noqa: E402
import party_reco as pr                                          # noqa: E402


def test_missing_priority_stops_before_write():
    first = pr.load()[0][0]['key']
    real = pr._json

    def fake(path, *a, **k):
        d = real(path, *a, **k)
        if str(path).endswith('journey_priority.json'):
            d = dict(d, units={u: v for u, v in d['units'].items() if u != first})
        return d

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'index.html')
        with patch.object(pr, '_json', fake):
            try:
                B.main(out)
            except SystemExit as e:
                assert first in str(e)
            else:
                raise AssertionError('중단되지 않음')
        assert not os.path.exists(out), '중단했는데 페이지가 저장됨'


if __name__ == '__main__':
    test_missing_priority_stops_before_write()
    print('ok 1')
