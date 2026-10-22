# -*- coding: utf-8 -*-
"""데이터북 data/main.js(`window.__SSD.x = {...}` 모음)를 하나의 JSON 으로 푼다.
사용: python -X utf8 -I tools/unwrap_ssd.py <main.js> [출력 json, 기본 rawdata/databook_main.json]"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
from battlesim.fileio import atomic_json


def unwrap(s):
    dec, res, pos = json.JSONDecoder(), {}, 0
    for m in re.finditer(r"__SSD\.(\w+)\s*=\s*", s):
        if m.start() < pos:
            continue
        val, end = dec.raw_decode(s[m.end():])
        res[m.group(1)] = val
        pos = m.end() + end
    if not res or any(not isinstance(v, (dict, list)) or not v for v in res.values()):
        raise ValueError('비어 있거나 올바르지 않은 __SSD 자료')
    return res.get("main", res)


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "rawdata", "databook_main.json")
    with open(src, encoding="utf-8") as f:
        value = unwrap(f.read())
    atomic_json(out, value)
    print(out, list(value))


if __name__ == "__main__":
    main()
