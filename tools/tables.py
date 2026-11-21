# -*- coding: utf-8 -*-
"""비공개 표(클라 추출 JSON) 읽기 공용 함수. 빌더는 여기서만 읽는다."""
import json
import re
from collections import defaultdict
from functools import lru_cache
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


def table(static, name):
    """<static>/tables/<name>.json 의 Data(주석 없는 JSON 그대로 json.loads — jsonc 의 쉼표 정리를 타지 않음)."""
    return json.loads((Path(static) / 'tables' / (name + '.json')).read_text(encoding='utf-8'))['Data']


def strings(tables):
    """번역 표 {키: {'ko': .., 'en': ..}} (<tables>/Strings/STRING_COMMON_ko_en.json). 경로별 1회 읽기, 돌려준 사전은 고치지 말 것."""
    return _strings(str(Path(tables).resolve()))


@lru_cache(maxsize=4)
def _strings(path):
    return json.loads((Path(path) / 'Strings' / 'STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))


def name_sets(rows, strings, value, rename=None, key='m_BuffName'):
    """행 목록 -> {한국어 이름: 값 집합}. 번역 없는 행은 건너뛴다. rename 이 있으면 이름을 바꿔 묶는다."""
    out = defaultdict(set)
    for row in rows:
        name = strings.get(row.get(key), {}).get('ko')
        if name:
            out[rename(name) if rename else name].add(value(row))
    return out


def unanimous(sets, warn=None, msg=None):
    """{이름: 값 집합} -> {이름: 값}(이름순). 값이 하나뿐인 이름만 담고, 둘 이상이면 warn(msg(이름, 값 집합)) 후 뺀다."""
    out = {}
    for name, vals in sorted(sets.items()):
        if len(vals) == 1:
            out[name] = next(iter(vals))
        elif warn:
            warn(msg(name, vals))
    return out


class UnknownName(Exception):
    """효과 이름을 표에서 못 찾음(적 자동/반응 빌더가 그 줄을 건너뛰는 신호)."""


def buff_names(tables):
    """{m_BuffStrID: 한국어 이름}. 이름 문자열이 없는 버프는 뺀다."""
    tables = Path(tables)
    ko_of = strings(tables)
    out = {}
    for r in json.loads((tables / 'BUFF_TEMPLET.json').read_text(encoding='utf-8'))['Data']:
        ko = (ko_of.get(r.get('m_BuffName') or '') or {}).get('ko')
        if ko:
            out[r['m_BuffStrID']] = ko
    return out


def names_of(ids, bname):
    """버프 id 목록 -> 중복 없는 한국어 이름 목록. 이름 없는 id 가 있으면 UnknownName."""
    out = []
    for i in ids:
        n = bname.get(i)
        if not n:
            raise UnknownName('효과 이름 없음 ' + i)
        if n not in out:
            out.append(n)
    return out
