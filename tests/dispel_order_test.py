# -*- coding: utf-8 -*-
"""«효과 N개 해제»가 클라 버프 목록 순서로 고르는지 mc.dispel_order.
클라(build 26610546 NKM.decompiled.cs): 버프는 넣을 때 ShowIconPriority 내림차순 → 양성 먼저 → 넣은 순 자리에 들어가고
(OBF_27309·OBF_16553 4495-4520, 비교 OBF_25553 4916-4929), 같은 ID 재부여는 옛 객체를 지우고 다시 넣는다(OBF_5657 4524-4531).
해제 후보 루프(OBF_33563 4229-4253)는 그 순서로 N개를 고른다. 옛 엔진(insertion)은 처음 붙은 이름 순.
실행: python -X utf8 -I tests/dispel_order_test.py"""
import os
import random
import sys
from collections import defaultdict
from types import SimpleNamespace as NS

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim import mc as M                                    # noqa: E402
from battlesim.mc import Battle, Eff                             # noqa: E402


def _eff(name, harmful=False):
    e = Eff(name, {'atkp': 0.1}, 1, 3, None, harmful)
    e.stacks = 1
    return e


def _run(mode, x, rest):
    b = NS(mc=dict(MC_OPTS, dispel_order=mode), rule_hits=defaultdict(int), dirty=lambda u: None,
           R=lambda side: random.Random(1), _fired=lambda u: None, log=lambda **k: None,
           resolve=lambda owner, expr, ctx, kind=None: [x])
    for f in ('_dispel_ok', '_dispel_shield_ok', '_dispel_n_ordered'):
        setattr(b, f, (lambda g: (lambda *a: g(b, *a)))(getattr(Battle, f)))
    Battle.run_special(b, x, NS(raw=''), None, rest)
    return b


def test_default_client():
    assert MC_OPTS['dispel_order'] == 'client'


def test_priority_table_has_omega():
    assert M.buff_priority('오메가 프로토콜') == 1 and M.buff_priority('공격력 증가') == 0


def test_higher_priority_first_client():
    x = NS(side=0, name='x', eff={})
    for e in (_eff('공격력 증가'), _eff('오메가 프로토콜')):     # 일반 강화를 먼저 받음
        x.eff[e.name] = e
    b = _run('client', x, '자신에게 (강화효과 해제) 효과 1개 해제')
    assert sorted(x.eff) == ['공격력 증가']                    # 늦게 받은 오메가(우선순위 1)가 먼저 지워짐
    assert b.rule_hits['dispel_order'] == 1
    x = NS(side=0, name='x', eff={})
    for e in (_eff('공격력 증가'), _eff('오메가 프로토콜')):
        x.eff[e.name] = e
    _run('insertion', x, '자신에게 (강화효과 해제) 효과 1개 해제')
    assert sorted(x.eff) == ['오메가 프로토콜']


def test_reapplied_goes_last_client():
    x = NS(side=0, name='x', eff={})
    a, c = _eff('공격력 증가'), _eff('방어력 증가')
    x.eff = {a.name: a, c.name: c}
    a.seq = next(M._EFF_SEQ)                                  # 공격력 증가를 다시 받음 → 뒤로
    _run('client', x, '자신에게 (강화효과 해제) 효과 1개 해제')
    assert sorted(x.eff) == ['공격력 증가']


def test_reapply_updates_seq_in_add_effect():
    owner = NS(side=0, name='o', d=NS(effect_info={}), acting=False)
    x = NS(side=0, name='x', eff={}, acting=False, ban_refuse=False, buff_banned=lambda: False, on=lambda n: False,
           d=NS(immune=()))
    for mode, moved in (('client', True), ('insertion', False)):
        x.eff = {}
        b = NS(mc=dict(MC_OPTS, dispel_order=mode), rule_hits=defaultdict(int), dirty=lambda u: None,
               _cur_line=None, check_pending=[], refuse_buff=lambda u, n: False, _is_any_turn=lambda o, n: False,
               _buff_fresh=lambda *a: False, alive=lambda side: [], _cc_immune=lambda u, n: False,
               _forced=lambda o, n=None: False)
        eff = dict(name='공격력 증가', props={'공격력%': 10.0}, dur='2턴', max=None, times=1, target='자신')
        Battle.add_effect(b, owner, x, eff, None)
        first = x.eff['공격력 증가'].seq
        Battle.add_effect(b, owner, x, eff, None)
        assert (x.eff['공격력 증가'].seq != first) is moved



def test_put_eff_reapply_updates_seq():
    """기믹 모듈 put_eff(코스모·길방) 재부여도 클라에선 재삽입이라 목록 뒤로 간다(NKM:4505-4537)."""
    for mode, moved in (('client', True), ('insertion', False)):
        b = NS(mc=dict(MC_OPTS, dispel_order=mode), dirty=lambda u: None)
        x = NS(side=0, name='x', eff={}, acting=False, ban_refuse=False)
        Battle.put_eff(b, x, '상급 공격력 증가', {'공격력%': 10.0}, dur=2)
        first = x.eff['상급 공격력 증가'].seq
        Battle.put_eff(b, x, '상급 공격력 증가', {'공격력%': 10.0}, dur=2)
        assert (x.eff['상급 공격력 증가'].seq != first) is moved, mode

if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_') and callable(f):
            f(); n += 1
    print('ok', n)
