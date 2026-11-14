# -*- coding: utf-8 -*-
"""«약화/강화 효과 N개 해제»의 N이 버프 객체 단위인지 mc.dispel_instance.
클라: 해제 후보 루프(OBF_33563, build 26610546 NKM.decompiled.cs 4229-4253)는 객체마다 1개로 세고,
연소·출혈·중독·빙결(BUFF_TEMPLET 1522-1525 IsUniqueID)은 부여마다 객체가 따로다(4321-4334).
옛 엔진(name)은 이름 하나(인스턴스 묶음 전체)를 1개로 지웠다 — 중독 3개에 «1개 해제»면 3개가 모두 사라짐.
실행: python -X utf8 -I tests/dispel_instance_test.py"""
import os
import random
import sys
from collections import defaultdict
from types import SimpleNamespace as NS

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.mc import Battle, Eff                             # noqa: E402


def _poison(n):
    e = Eff('중독', {}, 5, 2, None, True)
    e.dot = ('atk', 0.1)
    e.inst = [[None, 2 + i] for i in range(n)]
    e.stacks = n
    return e


def _run(mode, x, rest, order='client'):
    b = NS(mc=dict(MC_OPTS, dispel_instance=mode, dispel_order=order), rule_hits=defaultdict(int), dirty=lambda u: None,
           R=lambda side: random.Random(1), _fired=lambda u: None, log=lambda **k: None,
           resolve=lambda owner, expr, ctx, kind=None: [x])
    for f in ('_dispel_ok', '_dispel_shield_ok', '_dispel_n_ordered'):
        setattr(b, f, (lambda g: (lambda *a: g(b, *a)))(getattr(Battle, f)))
    Battle.run_special(b, x, NS(raw=''), None, rest)
    return b


def _unit():
    poison = _poison(3)                      # 중독을 먼저 받음(클라 목록에서도 앞)
    slow = Eff('속도 감소', {'spdp': -0.3}, 1, 2, None, True)
    slow.stacks = 1
    return NS(side=0, name='x', eff={'중독': poison, '속도 감소': slow})


def test_default_client():
    assert MC_OPTS['dispel_instance'] == 'client'


def test_one_removes_one_instance_client():
    for order in ('client', 'insertion'):      # 해제 순서 규칙(mc.dispel_order)과 무관하게 인스턴스 1개
        x = _unit()
        b = _run('client', x, '자신에게 (약화효과 해제) 효과 1개 해제', order)
        assert x.eff['중독'].stacks == 2 and len(x.eff['중독'].inst) == 2
        assert [it[1] for it in x.eff['중독'].inst] == [3, 4]        # 먼저 붙은 인스턴스부터
        assert '속도 감소' in x.eff
        assert b.rule_hits['dispel_instance'] == 1


def test_one_removes_whole_name_legacy():
    for order in ('client', 'insertion'):
        x = _unit()
        b = _run('name', x, '자신에게 (약화효과 해제) 효과 1개 해제', order)
        assert '중독' not in x.eff and '속도 감소' in x.eff
        assert b.rule_hits['dispel_instance'] == 0


def test_count_spills_to_next_effect_client():
    for order in ('client', 'insertion'):
        x = _unit()
        _run('client', x, '자신에게 (약화효과 해제) 효과 4개 해제', order)
        assert '중독' not in x.eff and '속도 감소' not in x.eff          # 중독 3 + 속도 감소 1
        x = _unit()
        _run('client', x, '자신에게 (약화효과 해제) 효과 3개 해제', order)
        assert '중독' not in x.eff and '속도 감소' in x.eff


def test_dispel_all_unchanged():
    for mode in ('client', 'name'):
        x = _unit()
        _run(mode, x, '자신에게 〈디버프 해제〉 (약화효과 해제)')
        assert x.eff == {}



def test_interleaved_single_instance_uses_own_seq_client():
    """중독① → 기절 → 중독② 순으로 받고 «약화 1개 해제» 두 번: 클라 목록(객체별 넣은 순, NKM:4505-4520·4916-4929)은
    중독① → 기절 → 중독② 라 두 번째에 기절이 지워져야 한다. 인스턴스 1개가 남았을 때 묶음 최초 seq 로 세우면 중독②가 지워졌다."""
    from battlesim import mc as M
    poison = Eff('중독', {}, 5, 2, None, True)
    poison.dot = ('atk', 0.1)
    i1 = M._Inst([None, 2]); i1.seq = next(M._EFF_SEQ)
    stun = Eff('기절', {}, 1, 1, None, True)
    stun.stacks = 1
    i2 = M._Inst([None, 2]); i2.seq = next(M._EFF_SEQ)
    poison.seq = i1.seq
    poison.inst = [i1, i2]
    poison.stacks = 2
    x = NS(side=0, name='x', eff={'중독': poison, '기절': stun})
    _run('client', x, '자신에게 (약화효과 해제) 효과 1개 해제')
    assert x.eff['중독'].inst == [i2] and '기절' in x.eff
    _run('client', x, '자신에게 (약화효과 해제) 효과 1개 해제')
    assert '기절' not in x.eff, sorted(x.eff)
    assert x.eff['중독'].inst == [i2] and x.eff['중독'].stacks == 1

if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_') and callable(f):
            f(); n += 1
    print('ok', n)
