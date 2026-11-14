# -*- coding: utf-8 -*-
"""효과 적중 판정의 절대값 항(시전자 절대 적중·역상성 절대 저항) mc.abs_hit_terms.
클라 OBF_23872(build 26610546 NKM.decompiled.cs 20255-20302): 절대값 = 시전자 NST_RATE_DEFINITE_EFFECT_HIT
- (대상 절대 저항 + 불리 상성일 때 대상 NST_RATE_ADJUST_DEFINITE_EFFECT_EVADE). 옛 엔진(zero)은 두 항을 0으로 고정.
표의 두 값은 현재 전 유닛 0 이라 실전 결과는 같다(우선순위 낮음).
실행: python -X utf8 -I tests/abs_hit_terms_test.py"""
import os
import sys
from collections import defaultdict
from types import SimpleNamespace as NS

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.mc import Battle                                  # noqa: E402

MODS = dict(eh=0.0, er=0.0, der=0.0)


def _roll(mode, owner_stats, target_stats, oel='별', xel='별', r=0.7):
    owner = NS(d=NS(stats=dict(eh=5000, **owner_stats), passive=defaultdict(float)), mods=lambda: MODS, element=oel, side=0)
    x = NS(d=NS(stats=dict(er=0, **target_stats), immune=()), mods=lambda: MODS, element=xel, side=1)
    rng = NS(random=lambda: r)
    b = NS(mc=dict(MC_OPTS, abs_hit_terms=mode), rule_hits=defaultdict(int), R=lambda side: rng)
    return Battle.roll_hit(b, owner, None, x, None), b


def test_default_client():
    assert MC_OPTS['abs_hit_terms'] == 'client'


def test_attacker_abs_hit_client():
    ok, b = _roll('client', dict(dhit=9000), {})          # 적중 50% < 절대 적중 90% → 90%
    assert ok and b.rule_hits['abs_hit_terms'] == 1
    assert not _roll('zero', dict(dhit=9000), {})[0]


def test_reverse_element_abs_resist_client():
    # 별 → 태양 은 불리(ELEM_LOSES): 적중 50%-30%=20%, 절대값 -(0+역상성 9000) → min(20%, 10%) = 10%
    assert not _roll('client', {}, dict(adher=9000), oel='별', xel='태양', r=0.15)[0]
    assert _roll('zero', {}, dict(adher=9000), oel='별', xel='태양', r=0.15)[0]
    assert _roll('client', {}, dict(adher=9000), oel='별', xel='별', r=0.15)[0]      # 같은 속성이면 무관


def test_zero_values_unchanged():
    for r in (0.1, 0.49, 0.51):
        assert _roll('client', {}, {}, r=r)[0] == _roll('zero', {}, {}, r=r)[0]


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
