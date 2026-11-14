# -*- coding: utf-8 -*-
"""코스모 전용 게이지 감소(폭주: 압박 SE 9401801 · 벨그라스 궁극기 SE 930082355)도 비강제 — 면역 대상은 거부(mc.gauge_cd_immune).
클라 build 26610546 NKM.decompiled.cs:4394-4398(CantGetMoreDebuff 거부), 4540-4566(회피 예외).
실행: python -X utf8 -I tests/cosmo_gauge_immune_test.py"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from cosmo_raid_test import battle, boss_of                     # noqa: E402
from battlesim.mc import Eff                                    # noqa: E402


def _immune_all(b):
    for u in b.allies:
        e = Eff('면역', {}, 1, 3, None, False)
        e.stacks = 1
        u.eff['면역'] = e
        u.gauge = 8000.0


def _run(boss_name, slot, mode, immune):
    b = battle(boss_name, 3, 18, mc={'gauge_cd_immune': mode})
    boss = boss_of(b)
    if immune:
        _immune_all(b)
    else:
        for u in b.allies:
            u.gauge = 8000.0
    b.cast(boss, boss.d.skills[slot])
    return b, min(u.gauge for u in b.allies if not u.dead)


def test_pressure_blocked_by_immune():
    b, g = _run('티리아', '기본기', 'client', True)
    assert b.gb.stats['pressure'] == 0 and g >= 8000, (dict(b.gb.stats), g)
    b, g = _run('티리아', '기본기', 'off', True)                 # 옛 동작: 면역이어도 깎임
    assert b.gb.stats['pressure'] >= 1 and g < 8000


def test_belgras_hyper_gauge_blocked_by_immune():
    _, g = _run('벨그라스', '궁극기', 'client', True)
    assert g >= 8000, g
    _, g = _run('벨그라스', '궁극기', 'off', True)
    assert g < 8000, g
    _, g = _run('벨그라스', '궁극기', 'client', False)           # 면역 없으면 그대로 깎임
    assert g < 8000, g


if __name__ == '__main__':
    test_pressure_blocked_by_immune()
    test_belgras_hyper_gauge_blocked_by_immune()
    print('ok 2')
