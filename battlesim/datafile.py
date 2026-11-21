# -*- coding: utf-8 -*-
"""엔진 자료 파일(<src>/data/*.json) 읽기 공용 함수 — 경로별 1회 파싱, 프로세스 캐시.

  load('auto_skill')['order']            # <SRC>/data/auto_skill.json, 없으면 FileNotFoundError
  load('foe_react', src, default=None)   # 없으면 default(캐시하지 않음)
  @cached                                 # 자료에서 다시 만든 값(집합·사전)의 캐시. clear() 가 같이 비운다
  clear()                                 # 파싱 캐시 + @cached 전부 비우기(api.clear_engine_caches 가 부름)

돌려준 객체는 여러 함수가 같이 쓰므로 고치지 말 것(고칠 곳은 복사해서).
"""
import functools
import inspect
import json
import os
from functools import lru_cache

from .starsavior.data import SRC

MISSING = object()
_CACHE = {}
_DERIVED = []


def path(name, src=SRC):
    return os.path.join(src, 'data', name + '.json')


def load_path(p, default=MISSING):
    """파일 경로 그대로 읽기(파일이 저장소 data/ 밖이거나 이름이 .json 이 아닐 때)."""
    got = _CACHE.get(p, MISSING)
    if got is MISSING:
        if default is not MISSING and not os.path.exists(p):
            return default
        with open(p, encoding='utf-8') as f:
            got = _CACHE[p] = json.load(f)
    return got


def load(name, src=SRC, default=MISSING):
    got = _CACHE.get((name, src), MISSING)   # 판당 여러 번 불리는 조회(buff_flags 등)라 경로 조립 전에 찾는다
    if got is MISSING:
        got = load_path(path(name, src), default)
        if got is not default:
            _CACHE[(name, src)] = got
    return got


def cached(fn):
    """자료에서 만든 값을 인자별로 캐시(lru_cache). clear() 가 같이 비운다.
    인자가 있으면 기본값을 채운 위치 인자로 열쇠를 맞춘다 — f() 와 f(SRC) 가 같은 객체를 돌려준다."""
    c = lru_cache(maxsize=None)(fn)
    _DERIVED.append(c)
    sig = inspect.signature(fn)
    if not sig.parameters:
        return c

    @functools.wraps(fn)
    def call(*a, **k):
        b = sig.bind(*a, **k)
        b.apply_defaults()
        return c(*b.args)
    call.cache_clear = c.cache_clear
    return call


def clear():
    _CACHE.clear()
    for c in _DERIVED:
        c.cache_clear()
