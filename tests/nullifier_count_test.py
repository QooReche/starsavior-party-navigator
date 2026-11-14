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



def _reapply(mode, first, second, dur2='5턴', dur1='1턴'):
    b = battle([unit('a')], [unit('f')], mc={'nullifier_count': mode})
    f = b.foes[0]
    ctx = Ctx(f, f, f.d.skills['기본기'])
    ctx.target, ctx.targets = f, [f]
    b.run_line(f, Line('[스킬 사용 후] 자신에게 〈스킬 피해 무효〉 (%s / 스킬 무효화) 스킬 무효화 %d회' % (dur1, first),
                       '기본기', 'active'), ctx)
    e = f.eff['스킬 피해 무효']
    seq = e.seq
    b.run_line(f, Line('[스킬 사용 후] 자신에게 〈스킬 피해 무효〉 (%s / 스킬 무효화) 스킬 무효화 %d회' % (dur2, second),
                       '기본기', 'active'), ctx)
    return f.eff['스킬 피해 무효'], seq


def test_reapply_smaller_or_equal_refused_client():
    """클라 NKM:4338-4340·5585-5591: 남은 횟수 이하의 재부여는 부여 자체를 거부(지속·목록 순서도 갱신 안 함)."""
    for second in (1, 3):
        e, seq = _reapply('client', 3, second)
        assert e.stacks == 3 and e.dur == 1 and e.seq == seq, (second, e.stacks, e.dur)
    e, _ = _reapply('client', 3, 5)                                 # 더 크면 받음
    assert e.stacks == 5 and e.dur == 5
    e, _ = _reapply('once', 1, 1)                                   # 옛 동작: 같은 1회 재부여로 지속 갱신
    assert e.dur == 5


def test_reapply_larger_new_object_duration_client():
    """더 큰 횟수로 갈아 끼우면 새 객체(NKM:4419·4495-4507, OBF_4403 생성자 5558-5562) — 지속도 새 SE 값(옛 값과 max 아님)."""
    e, seq = _reapply('client', 3, 5, dur2='1턴', dur1='5턴')
    assert e.stacks == 5 and e.dur == 1 and e.seq != seq, (e.stacks, e.dur)
    e, _ = _reapply('client', 2, 4, dur2='지속 무한', dur1='2턴')
    assert e.stacks == 4 and e.dur == float('inf')


def test_reapply_after_consumed_uses_new_count():
    """3회 중 2회 소모(남은 1) 뒤 2회 재부여 = 남은 횟수보다 커서 받음 → 새 객체 횟수 2(최대도 2)."""
    b, f, hp = _run('client', 3, 2)
    assert f.eff['스킬 피해 무효'].stacks == 1
    ctx = Ctx(f, f, f.d.skills['기본기'])
    b.run_line(f, Line('[스킬 사용 후] 자신에게 〈스킬 피해 무효〉 (2턴 / 스킬 무효화) 스킬 무효화 2회', '기본기', 'active'), ctx)
    e = f.eff['스킬 피해 무효']
    assert (e.stacks, e.maxs, e.dur) == (2, 2, 2), (e.stacks, e.maxs, e.dur)


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
