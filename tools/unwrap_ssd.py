# -*- coding: utf-8 -*-
"""데이터북 data/main.js(`window.__SSD.x = {...}` 모음)를 하나의 JSON 으로 푼다.
사용: python -X utf8 -I tools/unwrap_ssd.py <main.js> [출력 json, 기본 rawdata/databook_main.json]"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "rawdata", "databook_main.json")
    s = open(src, encoding="utf-8").read()
    dec, res, pos = json.JSONDecoder(), {}, 0
    for m in re.finditer(r"__SSD\.(\w+)\s*=\s*", s):
        if m.start() < pos:
            continue
        val, end = dec.raw_decode(s[m.end():])
        res[m.group(1)] = val
        pos = m.end() + end
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res.get("main", res), f, ensure_ascii=False)  # data/main.js 는 window.__SSD.main 하나에 전부 들어 있다
    print(out, list(res))


if __name__ == "__main__":
    main()
