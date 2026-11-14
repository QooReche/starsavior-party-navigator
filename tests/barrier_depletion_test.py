# -*- coding: utf-8 -*-
"""보호막이 다 깎였을 때 그 효과의 능력치도 사라지는지 mc.barrier_depletion.
클라: Barrier 플래그 버프는 보호막 HP 가 0 이 되면 버프째 제거(build 26610546 NKM.decompiled.cs 2746-2765, 5858-5861).
옛 엔진(keep_props)은 능력치가 붙은 보호막 효과(힐데 〈파프닐의 강림〉 방어력% +20% 등)를 지속 끝까지 남겼다.
실행: python -X utf8 -I tests/barrier_depletion_test.py"""
import os
import sys
from collections import defaultdict
from types import SimpleNamespace as NS

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.mc import Battle, Eff                             # noqa: E402


def _eff(name, shield, props):
    e = Eff(name, props, 1, 3, None, False)
    e.shield = shield
    return e


def _setup(mode, effs):
    dirty = []
    b = NS(mc={'barrier_depletion': mode}, rule_hits=defaultdict(int), dirty=dirty.append,
           log=lambda **k: None, kill=lambda v, a: setattr(v, 'dead', True))
    v = NS(name='v', dead=False, hp=1000.0, taken=0.0, acting=False, eff={e.name: e for e in effs},
           invincible=lambda: False, buff_blocked=lambda: False)
    return b, v, dirty


def test_default_client():
    assert MC_OPTS['barrier_depletion'] == 'client'


def test_depleted_with_props_removed_client():
    b, v, dirty = _setup('client', [_eff('파프닐', 300.0, {'defp': 0.2})])
    Battle.apply_damage(b, None, v, 500.0, 'hit')
    assert '파프닐' not in v.eff          # 능력치째 사라짐
    assert v.hp == 800.0                  # 넘친 200 만 체력으로
    assert b.rule_hits['barrier_depletion'] == 1
    assert dirty                          # 능력치 다시 계산


def test_depleted_with_props_kept_legacy():
    b, v, _ = _setup('keep_props', [_eff('파프닐', 300.0, {'defp': 0.2})])
    Battle.apply_damage(b, None, v, 500.0, 'hit')
    assert '파프닐' in v.eff and v.eff['파프닐'].shield <= 0
    assert v.hp == 800.0
    assert b.rule_hits['barrier_depletion'] == 0


def test_partial_absorb_keeps_effect():
    b, v, _ = _setup('client', [_eff('파프닐', 300.0, {'defp': 0.2})])
    Battle.apply_damage(b, None, v, 100.0, 'hit')
    assert v.eff['파프닐'].shield == 200.0 and v.hp == 1000.0


def test_plain_shield_removed_both_modes():
    for mode in ('client', 'keep_props'):
        b, v, _ = _setup(mode, [_eff('보호막', 100.0, {})])
        Battle.apply_damage(b, None, v, 150.0, 'hit')
        assert '보호막' not in v.eff and v.hp == 950.0
        assert b.rule_hits['barrier_depletion'] == 0     # 능력치 없는 보호막은 옛 동작과 같음


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_') and callable(f):
            f(); n += 1
    print('ok', n)
