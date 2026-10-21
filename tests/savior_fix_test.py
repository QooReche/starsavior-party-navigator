# -*- coding: utf-8 -*-
"""설명문 기준 트리거·스택·이벤트 회귀. python -X utf8 -I tests/savior_fix_test.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p5_test import battle, give, unit, Ctx, Line, UnitDef, get_db


def setup(key, allies=(), foes=None):
    b = battle([UnitDef(get_db(), key), *allies], foes or [unit('foe', hp=10**9, sa=1000)],
               opts={'coop': False, 'nova': False}, timeline=True)
    return b, b.allies[0], b.foes[0]


def casts(u):
    return u.cast_count.get('특수기(추가)', 0)


def test_omega_promotion():
    return promotion('omega', '도약', '파워업 스타', 3)


def test_bunny_promotion():
    return promotion('bunny-frey', '냉각', '하이 롤러(해제불가)', 5)


def promotion(key, source, dest, cap):
    out = []
    for stacks, promoted in [(4, 0), (5, 0), (5, cap - 1), (5, cap)]:
        b, a, _ = setup(key)
        give(a, source, stacks=stacks).maxs = 5
        if promoted:
            give(a, dest, stacks=promoted).maxs = cap
        b.fire(a, 'own_ts', Ctx(a, a, None))
        out.append((a.stack(source), a.stack(dest)))
    exp = [(4, 0), (0, 1), (0, cap), (5, cap)]
    return out == exp, '%s / 기대 %s' % (out, exp)


def test_ceres_targets():
    out = []
    for n in [1, 2, 3, 5, 6]:
        b, a, _ = setup('ceres', foes=[unit(str(i), hp=1 if i == 0 else 10**9, sa=1000) for i in range(n)])
        b.cast(a, a.d.skills['특수기'])
        out.append(a.gauge)
    # 게이지 자체 상한은 100%: 3명 이상이면 10000.
    return out == [3500, 7000, 10000, 10000, 10000], str(out)


def test_lydia_targets():
    out = []
    for n, own_turn in [(1, True), (2, True), (5, True), (6, True), (2, False)]:
        b, a, _ = setup('lydia-moon-caster', [unit('ally', skills=[dict(slot='기본기', dm=100, all=True)])],
                        [unit(str(i), hp=1 if i == 0 else 10**9, sa=1000) for i in range(n)])
        actor = b.allies[1]
        give(actor, '책임 전가(해제불가)')
        actor.acting = own_turn
        b.cast(actor, actor.d.skills['기본기'])
        out.append(a.stack('퇴근 재촉(해제불가)'))
    return out == [1, 2, 5, 5, 0], str(out)


def test_smile_trigger():
    out = []
    for hp in [0.51, 0.50, 0.49]:
        b, a, f = setup('smile')
        f.hp = f.maxhp * hp
        give(f, '보호막').shield = 10**9  # 피해 후에도 정확히 50%인 경계값 포함.
        b.cast(a, a.d.skills['기본기'], target=f)
        out.append(casts(a))
    b, a, f = setup('smile', foes=[unit('weak', hp=1), unit('alive', hp=10**9)])
    b.cast(a, a.d.skills['기본기'], target=f)
    out.append(casts(a))
    return out == [0, 1, 1, 0], str(out)


def test_roberta_trigger():
    out = []
    for aoe in [False, True]:
        b, a, f = setup('roberta', foes=[unit('foe', atk=1, hp=10**9, sa=1000,
                                             skills=[dict(slot='기본기', dm=100, all=aoe)])])
        a.d.stats['cr'] = 10000
        b.cast(f, f.d.skills['기본기'], target=a)
        out.append((casts(a), a.cd.get('특수기', 0)))
    return out == [(0, 0), (1, max(0, a.d.trigger_skills['특수기'].cd - 1))], str(out)


def test_fei_trigger():
    out = []
    for evade in [0, 100]:
        b, a, f = setup('fei', foes=[unit('foe', atk=1, hp=10**9, sa=1000)])
        give(a, '시험 회피', {'회피율': evade})
        b.cast(f, f.d.skills['기본기'], target=a)
        out.append((casts(a), a.stack('냉각')))
    return out == [(0, 0), (1, 2)], str(out)


def test_sunshine_trigger():
    out = []
    for stack, marked, dead in [(1, True, False), (2, True, False), (5, True, False),
                                (2, False, False), (2, True, True)]:
        b, a, f = setup('sunshine-cat-smile', [unit('ally')],
                        [unit('foe', hp=1 if dead else 10**9, sa=1000), unit('other', hp=10**9)])
        give(a, '도약', stacks=stack).maxs = 5
        if marked:
            give(f, '물폭탄', harmful=True)
        actor = b.allies[1]
        b.cast(actor, actor.d.skills['기본기'], target=f)
        out.append((casts(a), a.stack('도약'), a.stack('스파클라(해제불가)'), a.gauge))
    exp = [(0, 1, 0, 0), (1, 0, 1, 1500), (1, 3, 1, 1500), (0, 2, 0, 0), (0, 2, 0, 0)]
    return out == exp, str(out)


def test_sunshine_extra():
    b, a, f = setup('sunshine-cat-smile', foes=[unit('plain', hp=10**9), unit('marked', hp=10**9)])
    marked = b.foes[1]
    give(marked, '물폭탄', harmful=True)
    give(a, '도약', stacks=2).maxs = 5
    give(a, '스파클라(해제불가)', stacks=2).maxs = 3
    b.cast(a, a.d.skills['궁극기'], target=f)
    targets = [e['targets'] for e in b.timeline if e.get('skill') == '특수기(추가)']
    out = (casts(a), a.stack('도약'), a.stack('스파클라(해제불가)'), a.gauge, targets)
    return out == (2, 5, 0, 0, [[marked.name], [marked.name]]), str(out)


def test_claire_source():
    b, a, f = setup('claire')
    a.d.stats['cr'] = 0
    give(a, '냉각', stacks=4).maxs = 5
    b.cast(a, a.d.skills['기본기'], target=f)
    normal = (casts(a), a.stack('냉각'))
    # 다른 스킬에서 추가 발동한 특수기는 기본기 연쇄 조건을 충족하지 않는다.
    give(a, '냉각', stacks=5).maxs = 5
    c = Ctx(a, a, a.d.skills['궁극기'])
    c.target, c.targets = f, [f]
    b.run_line(a, Line('[스킬 사용 후] 자신에게 특수기 추가 발동', '궁극기', 'active'), c)
    return normal == (1, 0) and a.stack('냉각') == 5, str((normal, a.stack('냉각')))


def test_professor_events_target():
    b, p, first = setup('professor-m', [unit('actor'), unit('observer')],
                         [unit('first', hp=10**9, sa=1000), unit('recent', hp=10**9, sa=1000)])
    actor, observer = b.allies[1:]
    observer.d.lines = [Line('[스킬 사용 후] (조건: 아군 공격 후) 자신에게 행동 게이지 1%p 증가', '고유 패시브', 'passive')]
    p.last_target = b.foes[1]
    give(p, '냉각', stacks=4).maxs = 5
    b.cast(actor, actor.d.skills['기본기'], target=first)
    targets = [e['targets'] for e in b.timeline if e.get('actor') == p.name and e.get('via') == 'trigger']
    out = (casts(p), p.stack('냉각'), observer.gauge, targets)
    return out == (1, 0, 200, [[b.foes[1].name]]), str(out)


def test_bell_death():
    b, a, f = setup('bell', [unit('ally')], [unit('f1'), unit('f2'), unit('f3')])
    b.kill(f, a)
    first = (a.gauge, a.stack('다가오는 안식'))
    b.kill(b.allies[1], b.foes[1])
    b.kill(b.foes[1], a)
    b.kill(b.foes[2], a)
    return first == (5000, 1) and a.stack('다가오는 안식') == 3, str((first, a.stack('다가오는 안식')))


def test_trigger_blocking():
    out = []
    for key in ['roberta', 'fei', 'smile', 'sunshine-cat-smile', 'professor-m']:
        for block in ['기절', '수면', 'break', 'cd']:
            b, a, f = setup(key, [unit('actor')], [unit('foe', atk=1, hp=10**9, sa=1000,
                                                       skills=[dict(slot='기본기', dm=100, all=True)])])
            if block == 'break':
                a.broken = True
            elif block == 'cd':
                a.cd['특수기'] = 3
            else:
                give(a, block)
            give(a, '냉각', stacks=5).maxs = 5
            if key == 'sunshine-cat-smile':
                give(a, '도약', stacks=5).maxs = 5
            give(a, '회피', {'회피율': 100})
            give(f, '물폭탄', harmful=True)
            f.hp = f.maxhp * 0.49
            b.cast(f, f.d.skills['기본기'], target=a)
            b.cast(b.allies[1], b.allies[1].d.skills['기본기'], target=f)
            b.cast(a, a.d.skills['기본기'], target=f)
            if casts(a):
                out.append((key, block, casts(a)))
    return not out, str(out)


def test_trigger_reentry():
    out = []
    for key in ['roberta', 'fei']:
        b, a, f = setup(key, foes=[unit('foe', atk=1, hp=10**9, sa=1000,
                                       skills=[dict(slot='기본기', dm=100, all=True)])])
        give(a, '확정 회피', {'회피율': 100})
        calls = []
        original = b.cast
        def traced(owner, sk, **kw):
            if owner is a and kw.get('via') == 'reaction':
                calls.append(owner.cd.get(sk.slot, 0))
                # 시전 진입 시 동일한 피격 이벤트가 중첩돼도 다시 발동하지 않는다.
                b.reaction_skills(a, f, f.d.skills['기본기'], False, True)
            return original(owner, sk, **kw)
        b.cast = traced
        b.cast(f, f.d.skills['기본기'])
        out.append((casts(a), calls, sum(v for k, v in b.unsup.items() if k.startswith('depth:'))))
    exp = [(1, [UnitDef(get_db(), key).trigger_skills['특수기'].cd or 0], 0) for key in ['roberta', 'fei']]
    return out == exp, str(out)


def test_lydia_threshold():
    b, a, _ = setup('lydia-moon-caster', [unit('actor', skills=[dict(slot='기본기', dm=100, all=True)])],
                    [unit(str(i), hp=10**9, sa=1000) for i in range(2)])
    actor = b.allies[1]
    give(actor, '책임 전가(해제불가)')
    give(a, '퇴근 재촉(해제불가)', stacks=3).maxs = 10
    actor.acting = True
    b.cast(actor, actor.d.skills['기본기'])
    first = (a.stack('퇴근 재촉(해제불가)'), a.gauge)
    b.cast(actor, actor.d.skills['기본기'], extra=True)
    second = (a.stack('퇴근 재촉(해제불가)'), a.gauge)
    return (first, second) == ((5, 3000), (7, 3000)), str((first, second))


def test_sunshine_target_selection():
    out = []
    for mode in ['unmarked_hit', 'self', 'aoe', 'extra']:
        b, a, f = setup('sunshine-cat-smile', [unit('actor', skills=[dict(slot='기본기', dm=100, all=mode == 'aoe')])],
                        [unit('plain', hp=10**9, sa=1000), unit('marked', hp=10**9, sa=1000)])
        give(b.foes[1], '물폭탄', harmful=True)
        give(a, '도약', stacks=2).maxs = 5
        actor = a if mode == 'self' else b.allies[1]
        target = f if mode in ['unmarked_hit', 'aoe'] else b.foes[1]
        b.cast(actor, actor.d.skills['기본기'], target=target, extra=mode == 'extra')
        targets = [e['targets'] for e in b.timeline if e.get('actor') == a.name and e.get('via') == 'trigger']
        out.append((casts(a), targets))
    return out == [(0, []), (0, []), (1, [['marked']]), (1, [['marked']])], str(out)


TESTS = [v for k, v in list(globals().items()) if k.startswith('test_')]


def main():
    failed = 0
    selected = [t for t in TESTS if not sys.argv[1:] or any(s in t.__name__ for s in sys.argv[1:])]
    for test in selected:
        try:
            ok, msg = test()
        except Exception as ex:
            ok, msg = False, repr(ex)
        print('%s %s - %s' % ('PASS' if ok else 'FAIL', test.__name__, msg))
        failed += not ok
    print('%d/%d PASS' % (len(selected) - failed, len(selected)))
    return int(bool(failed))


if __name__ == '__main__':
    sys.exit(main())
