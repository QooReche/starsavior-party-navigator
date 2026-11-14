# -*- coding: utf-8 -*-
"""유닛 면역 목록이 저항 무시 효과도 막는지 mc.immune_group_resist.
클라: 부여 검사 첫머리(build 26610546 NKM.decompiled.cs 4318-4322)에서 대상 유닛의 면역 SE 목록(ImmuneGroupId)으로
거부하고, 효과 저항 무시(4362-4377 의 OBF_10347)와 무관하다. 옛 엔진(resist_only)은 면역 이름을 저항 판정 안에서만 봐서
저항 무시 약화가 보스 고유 면역을 뚫었다. 현재 데이터에서 실전 발생 0(우선순위 낮음).
실행: python -X utf8 -I tests/immune_group_resist_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit                                  # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402


def _run(mode, ignore_resist):
    b = battle([unit('a')], [unit('f')], mc={'immune_group_resist': mode})
    a, f = b.allies[0], b.foes[0]
    f.d.immune = {'기절'}
    eff = dict(name='기절', props={}, dur='1턴', max=None, times=1, target='스킬 대상', judge=False,
               ignore_resist=ignore_resist)
    b.add_effect(a, f, eff, None)
    return b, f


def test_default_client():
    assert MC_OPTS['immune_group_resist'] == 'client'


def test_ignore_resist_blocked_client():
    b, f = _run('client', True)
    assert '기절' not in f.eff and b.rule_hits['immune_group_resist'] == 1


def test_ignore_resist_pierces_legacy():
    assert '기절' in _run('resist_only', True)[1].eff


def test_normal_debuff_blocked_both():
    for mode in ('client', 'resist_only'):
        assert '기절' not in _run(mode, False)[1].eff


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
