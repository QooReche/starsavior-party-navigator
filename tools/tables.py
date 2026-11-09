# -*- coding: utf-8 -*-
"""비공개 표(클라 추출 JSON) 읽기 공용 함수. 빌더는 여기서만 읽는다."""
import json
import re
from pathlib import Path


def jsonc(path):
    """주석(//) 달린 표. 문자열 안의 // 는 건드리지 않는다."""
    s = Path(path).read_text(encoding='utf-8-sig')
    out, i, n, ins = [], 0, len(s), False
    while i < n:
        c = s[i]
        if ins:
            out.append(c)
            if c == '\\':
                out.append(s[i + 1])
                i += 2
                continue
            ins = c != '"'
            i += 1
            continue
        if c == '"':
            ins = True
        elif s.startswith('//', i):
            j = s.find('\n', i)
            i = n if j < 0 else j
            continue
        out.append(c)
        i += 1
    return json.loads(re.sub(r',(\s*[\]}])', r'\1', ''.join(out)))


def rows(path):
    """표 파일 -> 행 목록. {"Data": [...]} 형태면 Data 를 벗기고, 목록이면 그대로."""
    d = jsonc(path)
    return d['Data'] if isinstance(d, dict) and 'Data' in d else d
