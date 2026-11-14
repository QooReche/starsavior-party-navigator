# -*- coding: utf-8 -*-
"""브레이크 스킬(오비탈)도 공통 부여·타격 검사를 타는지: 〈스킬 피해 무효〉(mc.bskill_nullify)·행동 게이지 증가 면역(mc.gauge_up_immune).
클라 build 26610546: 오비탈 피해 = OBF_23259(…, 스킬 피해, DAMAGE_SKILL)(NKM:7993) → 무적 0 / SkillNullifier 1회 소모(2693-2710).
오비탈 게이지 = SE_TEMPLET_ORBITAL_ARRAY 102011(비강제) → BI_SPEED_GAUGE_UP 2002 → ImmuneSpeedGaugeUp 이면 거부(4412-4416).
실행: python -X utf8 -I tests/bskill_nullify_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
import p5_test as P                                              # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402


def _battle(name, mc, roles=('스트라이커',)):
    foe = P.unit('boss', hp=10 ** 9, sa=1, skills=[dict(slot='기본기', dm=0)])
    foe.boss = True
    allies = [P.unit('a%d' % i, role=r) for i, r in enumerate(roles)]
    b = P.battle(allies, [foe], break_skill={'name': name, 'level': 5}, mc=mc)
    b.break_points = 3
    return b


def _nullify(mode):
    b = _battle('차원 강습', {'bskill_nullify': mode})
    f = b.foes[0]
    P.give(f, '스킬 피해 무효')
    P.give(f, '수면', harmful=True, dur=2)
    hp = f.hp
    b._use_break_skill(b.allies[0])
    return b, f, hp


def test_default_client():
    assert MC_OPTS['bskill_nullify'] == 'client'


def test_orbital_nullified_client():
    b, f, hp = _nullify('client')
    assert f.hp == hp and '스킬 피해 무효' not in f.eff, (f.hp, hp, sorted(f.eff))
    assert '수면' not in f.eff                                   # 동기화 피해 기준 수면 해제는 그대로
    assert b.rule_hits['bskill_nullify'] == 1


def test_orbital_ignores_nullify_legacy():
    b, f, hp = _nullify('off')
    assert f.hp < hp and '스킬 피해 무효' in f.eff


def test_invincible_first_keeps_nullifier():
    b = _battle('차원 강습', {})
    f = b.foes[0]
    P.give(f, '스킬 피해 무효')
    P.give(f, '무적')
    hp = f.hp
    b._use_break_skill(b.allies[0])
    assert f.hp == hp and '스킬 피해 무효' in f.eff               # 무적이 먼저 막으면 소모 안 함


def _gauge(mode):
    b = _battle('스타피어서', {'gauge_up_immune': mode}, roles=('스트라이커', '스트라이커'))
    a0, a1 = b.allies
    a1.gauge = 1000.0
    P.give(a1, '억류(해제불가)', harmful=True, dur=3)
    b._use_break_skill(a0)
    return a1


def test_orbital_gauge_blocked_by_immune_client():
    assert _gauge('client').gauge == 1000.0
    assert _gauge('off').gauge > 1000.0


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
