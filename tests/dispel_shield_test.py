# -*- coding: utf-8 -*-
"""강화효과 해제가 보호막 효과도 지우는지 mc.dispel_shield.
클라: 해제 후보 선정(OBF_33563, build 26610546 NKM.decompiled.cs 4229-4253)은 IsBuff·IsPositive·CanNotDispel 만 보고
Barrier 를 빼지 않는다. 일반 〈보호막〉 BI_BARRIER(1038)는 CanNotDispel=false, «(해제불가)» 보호막(1039·1060)만 남는다.
옛 엔진(skip)은 보호막이 남은 효과를 해제 후보에서 뺐다.
실행: python -X utf8 -I tests/dispel_shield_test.py"""
import os
import random
import sys
from collections import defaultdict
from types import SimpleNamespace as NS

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.mc import Battle, Eff                             # noqa: E402


def _eff(name, shield=0.0, fixed=False, props=None):
    e = Eff(name, props or {}, 1, 3, None, False)
    e.stacks, e.shield, e.fixed = 1, shield, fixed
    return e


def _battle(mode, target):
    b = NS(mc=dict(MC_OPTS, dispel_shield=mode), rule_hits=defaultdict(int), dirty=lambda u: None,
           R=lambda side: random.Random(1), _fired=lambda u: None, log=lambda **k: None)
    b.resolve = lambda owner, expr, ctx, kind=None: [target]
    b._dispel_ok = lambda *a: Battle._dispel_ok(b, *a)
    b._dispel_shield_ok = lambda e: Battle._dispel_shield_ok(b, e)
    return b


def _target():
    x = NS(side=0, name='x', eff={})
    for e in (_eff('보호막', 500.0), _eff('공허 방패(해제불가)', 300.0, fixed=True), _eff('공격력 증가', props={'atkp': 0.2})):
        x.eff[e.name] = e
    return x


def test_default_client():
    assert MC_OPTS['dispel_shield'] == 'client'


def test_dispel_all_removes_shield_client():
    x = _target()
    b = _battle('client', x)
    Battle.run_special(b, x, NS(raw=''), None, '자신에게 〈버프 해제〉 (강화효과 해제)')
    assert sorted(x.eff) == ['공허 방패(해제불가)']          # 일반 보호막·강화 해제, 해제불가 보호막만 남음
    assert b.rule_hits['dispel_shield'] == 1


def test_dispel_all_keeps_shield_legacy():
    x = _target()
    b = _battle('skip', x)
    Battle.run_special(b, x, NS(raw=''), None, '자신에게 〈버프 해제〉 (강화효과 해제)')
    assert sorted(x.eff) == ['공허 방패(해제불가)', '보호막']
    assert b.rule_hits['dispel_shield'] == 0


def test_dispel_n_counts_shield_client():
    x = _target()
    b = _battle('client', x)
    Battle.run_special(b, x, NS(raw=''), None, '자신에게 (강화효과 해제) 효과 1개 해제')
    assert '보호막' not in x.eff and '공격력 증가' in x.eff    # 먼저 붙은 보호막이 1개 몫으로 지워짐
    b2 = _battle('skip', _target())
    x2 = _target()
    b2.resolve = lambda owner, expr, ctx, kind=None: [x2]
    Battle.run_special(b2, x2, NS(raw=''), None, '자신에게 (강화효과 해제) 효과 1개 해제')
    assert '보호막' in x2.eff and '공격력 증가' not in x2.eff


def test_shield_grant_marks_undispellable():
    for name, raw, want in (('보호막(해제불가)', '{해제 불가}', True), ('보호막', '', False)):
        owner = NS(side=0, name='o', maxhp=1000.0, shield_given=0.0, mods=lambda: {'barrier_give': 0.0})
        x = NS(side=0, name='x', eff={}, acting=False)
        b = _battle('client', x)
        b.refuse_buff = lambda u, n: False
        b._is_any_turn = lambda o, n: False
        b._buff_fresh = lambda *a, **k: False
        b.atk_stat = b.def_stat = lambda u: 100.0
        Battle.run_special(b, owner, NS(raw='[스킬 사용 후] 자신에게 〈%s〉 (2턴) 보호막 = 자신 생명력×10%% %s' % (name, raw)),
                           None, '자신에게 〈%s〉 (2턴) 보호막 = 자신 생명력×10%%' % name)
        assert x.eff[name].shield == 100.0 and x.eff[name].fixed is want


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_') and callable(f):
            f(); n += 1
    print('ok', n)
