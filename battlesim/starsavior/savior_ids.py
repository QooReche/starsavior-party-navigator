# -*- coding: utf-8 -*-
"""구원자 키(가이드 색인 key) <-> 게임 id(uid) 매핑을 한 곳에서 정한다.

규칙: 색인 key 우선 -> (필요하면) 시뮬 DB 의 id -> 이름이 유일할 때만 이름.
동명이인(리디아·아세라·세레스 등)은 이름 연결을 하지 않는다."""
from collections import defaultdict


def _entries(index):
    return {int(k): v for k, v in index.items() if not str(k).startswith('_') and isinstance(v, dict)}


def keys_by_id(index, db=None, only_db=False):
    """게임 id -> 구원자 키. db 를 주면 색인에 없는 시뮬 DB 구원자(개화 변형 '@' 제외)를 id 로 채운다.
    only_db 면 색인 키 중 시뮬 DB 에 있는 것만 남긴다."""
    out = {uid: v['key'] for uid, v in _entries(index).items() if v.get('key')}
    if db is not None:
        if only_db:
            out = {uid: k for uid, k in out.items() if k in db.units}
        for key, row in db.units.items():
            if '@' not in key and row.get('id') not in out:
                out[row['id']] = key
    return out


def ids_by_key(index, db=None):
    """구원자 키 -> 게임 id. db 를 주면 색인 키와 다른 시뮬 DB 키(변형 포함)를 setdefault 로 채운다."""
    out = {v['key']: uid for uid, v in _entries(index).items() if v.get('key')}
    if db is not None:
        for key, row in db.units.items():
            out.setdefault(key, int(row['id']))
    return out


def uid_resolver(index):
    """(key, name) -> uid 또는 None. 키가 색인에 있으면 그 id, 없으면 이름이 유일할 때만."""
    by_key = ids_by_key(index)
    by_name = defaultdict(list)
    for uid, v in _entries(index).items():
        by_name[v.get('profile', {}).get('name')].append(uid)

    def resolve(key, name):
        if key in by_key:
            return by_key[key]
        c = by_name.get(name, [])
        return c[0] if len(c) == 1 else None
    return resolve
