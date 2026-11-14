# -*- coding: utf-8 -*-
"""스킬 타격 피해를 받으면 〈수면〉이 풀리는지 mc.sleep_wake.
클라: 대상별 마지막 타격(IsLastHit)의 동기화 피해가 0보다 크면 OBF_2209 가 피격자의 Sleep 버프를 지운다
(build 26610546 NKM.decompiled.cs 7993-8011, 8314-8336). 옛 엔진(off)은 맞아도 수면이 남아 다음 행동을 막았다.
실행: python -X utf8 -I tests/sleep_wake_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit                            # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402


def _hit(mode, nullify=False):
    b = battle([unit('a')], [unit('f')], mc={'sleep_wake': mode})
    a, f = b.allies[0], b.foes[0]
    give(f, '수면', harmful=True, dur=2)
    if nullify:
        give(f, '스킬 피해 무효')
    hp = f.hp
    b.cast(a, a.d.skills['기본기'], target=f)
    return b, f, hp


def test_default_client():
    assert MC_OPTS['sleep_wake'] == 'client'


def test_hit_wakes_client():
    b, f, hp = _hit('client')
    assert f.hp < hp                                  # 실제로 맞음
    assert '수면' not in f.eff and b.rule_hits['sleep_wake'] == 1


def test_hit_keeps_sleep_legacy():
    b, f, hp = _hit('off')
    assert f.hp < hp and '수면' in f.eff and b.rule_hits['sleep_wake'] == 0


def test_nullified_hit_still_wakes_client():
    b, f, hp = _hit('client', nullify=True)
    assert f.hp == hp and '스킬 피해 무효' not in f.eff   # 피해는 무효로 막힘
    assert '수면' not in f.eff                            # 동기화 피해 기준이라 풀림



def _orbital(mode):
    """공격형 브레이크 스킬(오비탈 〈차원 강습〉)도 공통 타격 경로(NKM:7997-8018, 오비탈 식별 3234)라 피해 > 0 이면 수면 해제."""
    import p5_test as P
    foe = P.unit('boss', hp=10 ** 9, sa=1, skills=[dict(slot='기본기', dm=0)])
    foe.boss = True
    b = P.battle([P.unit('a')], [foe], break_skill={'name': '차원 강습', 'level': 5}, mc={'sleep_wake': mode})
    a, f = b.allies[0], b.foes[0]
    P.give(f, '수면', harmful=True, dur=2)
    b.break_points = 3
    hp = f.hp
    b._use_break_skill(a)
    return b, f, hp


def test_orbital_damage_wakes_client():
    b, f, hp = _orbital('client')
    assert b.break_skill_uses == 1 and f.hp < hp                 # 오비탈이 실제로 피해를 줌
    assert '수면' not in f.eff and b.rule_hits['sleep_wake'] == 1


def test_orbital_keeps_sleep_legacy():
    b, f, hp = _orbital('off')
    assert f.hp < hp and '수면' in f.eff

if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
