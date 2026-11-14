# -*- coding: utf-8 -*-
"""이번 시전을 회피한 적 대상에게는 해제가 걸리지 않는지 mc.dispel_evade.
클라: 해제는 버프 부여 함수(OBF_32436) 안에서 실행되고, 그 앞의 회피 거부(OBF_13659, build 26610546
NKM.decompiled.cs 4323-4327·4540-4566)가 HIT/SKILL_END 시점 적 대상 효과를 회피 시 거부한다(강제 적용 예외).
옛 엔진(off)은 회피한 적의 강화까지 지웠다.
실행: python -X utf8 -I tests/dispel_evade_test.py"""
import os
import random
import sys
from collections import defaultdict
from types import SimpleNamespace as NS

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.mc import Battle, Eff                             # noqa: E402


class U(NS):
    __hash__ = object.__hash__


def _case(mode, evaded):
    buff = Eff('공격력 증가', {'atkp': 0.2}, 1, 3, None, False)
    buff.stacks = 1
    owner = NS(side=0, name='o')
    x = U(side=1, name='x', eff={buff.name: buff})
    ctx = NS(evaded={x} if evaded else set())
    b = NS(mc=dict(MC_OPTS, dispel_evade=mode), rule_hits=defaultdict(int), dirty=lambda u: None,
           R=lambda side: random.Random(1), _fired=lambda u: None, log=lambda **k: None,
           resolve=lambda o, expr, c, kind=None: [x], roll_hit=lambda *a: True)
    for f in ('_dispel_ok', '_dispel_shield_ok', '_dispel_n_ordered'):
        setattr(b, f, (lambda g: (lambda *a: g(b, *a)))(getattr(Battle, f)))
    Battle.run_special(b, owner, NS(raw=''), ctx, '스킬 대상에게 〈버프 해제〉 (강화효과 해제) {효과 적중 판정}')
    return x, b


def test_default_client():
    assert MC_OPTS['dispel_evade'] == 'client'


def test_evaded_keeps_buff_client():
    x, b = _case('client', True)
    assert '공격력 증가' in x.eff and b.rule_hits['dispel_evade'] == 1


def test_evaded_loses_buff_legacy():
    x, b = _case('off', True)
    assert '공격력 증가' not in x.eff and b.rule_hits['dispel_evade'] == 0


def test_not_evaded_dispelled_both():
    for mode in ('client', 'off'):
        x, _ = _case(mode, False)
        assert '공격력 증가' not in x.eff


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_') and callable(f):
            f(); n += 1
    print('ok', n)
