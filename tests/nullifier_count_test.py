# -*- coding: utf-8 -*-
"""〈스킬 피해 무효〉 «스킬 무효화 N회»를 횟수로 세는지 mc.nullifier_count.
클라 SkillNullifier(build 26610546 NKM.decompiled.cs 5553-5592): 생성 때 SkillNullifierValue 를 카운트로 갖고
막을 때마다 1 줄인다. 옛 엔진(once)은 첫 무효 뒤 통째로 지웠다. 현재 줄은 모두 1회라 실전 발생 0(우선순위 낮음).
실행: python -X utf8 -I tests/nullifier_count_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit                                  # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402


def _run(mode, n, hits):
    b = battle([unit('a')], [unit('f')], mc={'nullifier_count': mode})
    a, f = b.allies[0], b.foes[0]
    ctx = Ctx(f, f, f.d.skills['기본기'])
    ctx.target, ctx.targets = f, [f]
    b.run_line(f, Line('[스킬 사용 후] 자신에게 〈스킬 피해 무효〉 (지속 무한 / 스킬 무효화) 스킬 무효화 %d회' % n,
                       '기본기', 'active'), ctx)
    hp = f.hp
    for _ in range(hits):
        b.cast(a, a.d.skills['기본기'], target=f)
    return b, f, hp


def test_default_client():
    assert MC_OPTS['nullifier_count'] == 'client'


def test_three_charges_client():
    b, f, hp = _run('client', 3, 2)
    assert f.hp == hp and f.eff['스킬 피해 무효'].stacks == 1      # 두 번 막고 1회 남음
    b, f, hp = _run('client', 3, 4)
    assert f.hp < hp and '스킬 피해 무효' not in f.eff


def test_three_charges_once_legacy():
    b, f, hp = _run('once', 3, 2)
    assert f.hp < hp and '스킬 피해 무효' not in f.eff               # 첫 공격 뒤 사라져 두 번째에 맞음


def test_single_charge_same_both():
    for mode in ('client', 'once'):
        b, f, hp = _run(mode, 1, 1)
        assert f.hp == hp and '스킬 피해 무효' not in f.eff


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
