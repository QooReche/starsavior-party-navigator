# -*- coding: utf-8 -*-
"""시험 공용 전투 도우미(p3_test·p5_test 가 쓰던 것을 한 곳으로). 시험 파일끼리 import 하지 않도록 새 시험은 여기서 가져온다.

unit 은 p3 판(넘긴 키워드만 dict 에 넣음). p5 판처럼 element·sa 를 항상 넣고 싶으면 tests/p5_test.unit 을 쓴다."""
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.api import _CustomFoe  # noqa: E402
from battlesim.mc import Battle, Eff  # noqa: E402

FIXED = dict(rand_range=[1.0, 1.0])   # 난수 고정(정확한 값 비교용)


def unit(name='u', role='스트라이커', hp=10000, atk=1000, df=1000, spd=100, cr=0, skills=None, **kw):
    return _CustomFoe(dict(name=name, role=role, hp=hp, atk=atk, **{'def': df}, spd=spd, cr=cr, cd=0, er=0, der=0,
                           skills=skills or [dict(slot='기본기', dm=100)], **kw), 0)


def battle(allies, foes, mc=None, seed=1, **kw):
    b = Battle(allies, [foes], random.Random(seed), mc=dict(FIXED, **(mc or {})), **kw)
    b.spawn_wave()
    return b


def give(u, name, props=None, src=None, harmful=False, dur=3, stacks=1):
    e = Eff(name, props or {}, 1, dur, src or u, harmful)
    e.stacks = stacks
    u.eff[name] = e
    u._m = None
    return e
