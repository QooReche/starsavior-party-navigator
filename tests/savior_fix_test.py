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
    # 대상 개수 상한 5는 유지. 게이지는 100% 초과 보존(NKM.cs:3323).
    return out == [3500, 7000, 10500, 17500, 17500], str(out)


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


def test_professor_analysis_coop():
    """기본기 자동 지정 버프가 협공 피해와 냉각·게이지 보상에 적용된다."""
    b, p, f = setup('professor-m', [unit('ally')])
    ally = b.allies[1]
    b.cast(p, p.d.skills['기본기'], target=f)
    out = (ally.has('표본 행동 분석'), round(ally.mods()['inc'], 2),
           ally.cast_count.get('기본기(추가)', 0), p.stack('냉각'), p.gauge)
    return out == (True, 0.1, 1, 3, 800), str(out)


def test_professor_analysis_move():
    """자동 지정 대상이 바뀌면 기존 아군의 분석 버프를 해제한다."""
    b, p, f = setup('professor-m', [unit('first', atk=2000), unit('next', atk=1000)])
    first, nxt = b.allies[1:]
    give(first, '표본 행동 분석', {'피해 증가': 10}, src=p, dur=1)
    give(nxt, '시험 공격력', {'공격력%': 200})
    b.cast(p, p.d.skills['기본기'], target=f)
    out = ([u.has('표본 행동 분석') for u in b.allies],
           [u.cast_count.get('기본기(추가)', 0) for u in (first, nxt)])
    return out == ([False, False, True], [0, 1]), str(out)


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


def pre(b, a, slot='기본기'):
    c = Ctx(a, a, a.d.skills[slot])
    c.targets, c.target = list(b.foes), b.foes[0]
    b.run_own(a, c, 'own_pre')
    return c


def test_fix2_beneficiary():
    out = []
    for slot, mark, name in [('특수기', '청풍(해제불가)', '도약'),
                             ('궁극기', None, '치명타 피해 증가')]:
        b, a, _ = setup('lyn', [unit('star', element='별'), unit('moon', element='달'), unit('star2', element='별')])
        if mark:
            give(a, mark)
        b.cast(a, a.d.skills[slot])
        out.append([x.stack(name) for x in b.allies[1:]])
    for elem in ['달', '별']:
        b, a, _ = setup('wedding-carmen', [unit('ally', element=elem)])
        b.cast(a, a.d.skills['궁극기'], target=b.allies[1])
        out.append(b.allies[1].stack('냉각'))
    return out == [[3, 0, 3], [1, 0, 1], 3, 0], str(out)


def test_fix2_decimal_hp():
    out = []
    for hp in [0.5, 0.49999, 0.4999, 0.49]:
        b, a, _ = setup('roberta')
        a.hp = a.maxhp * hp
        out.append(round(pre(b, a).inc, 3))
    for hp in [0.5, 0.49999]:
        b, a, _ = setup('harley', [unit('ally')])
        a.hp = a.maxhp * hp
        b.cast(a, a.d.skills['궁극기'])
        out.append((a.stack('폭주 모드(해제불가)'), b.allies[1].stack('속도 증가')))
    return out == [0.23, 0.31, 0.31, 0.31, (0, 1), (1, 0)], str(out)


def test_fix2_count_damage():
    out = []
    for n in [0, 1, 3, 5, 7]:
        b, a, f = setup('claire')
        for i in range(n):
            give(f, 'buff%d' % i)
        c = pre(b, a, '궁극기')
        out.append(round(c.inc + c.local_by[f]['inc'], 3))
        assert not a.on('바니 잭팟')
        assert round(pre(b, a).inc, 3) == 0.15
    return out == [0.15, 0.25, 0.45, 0.65, 0.65], str(out)


def test_fix2_shield_count():
    out = []
    for n in [0, 1, 3, 4]:
        b, a, _ = setup('wedding-epindel', foes=[unit(str(i), hp=10**9, sa=1000) for i in range(4)])
        for f in b.foes[:n]:
            give(f, '보호막').shield = 10000
        c = pre(b, a, '궁극기')
        out.append(round(c.inc, 3))
        assert round(pre(b, a).inc, 3) == 0.15
        assert not a.mods()['inc']
    return out == [0.15, 0.3, 0.6, 0.6], str(out)


def test_fix2_pre_marker():
    b, a, f = setup('epindel')
    a.d.stats['cr'] = 0
    give(a, '냉각', stacks=5).maxs = 5
    c = b.cast(a, a.d.skills['기본기'])
    first = (round(c.inc, 3), a.stack('냉각'), a.stack('귀족의 품격'))
    c = b.cast(a, a.d.skills['기본기'])
    return first == (0.4, 0, 0) and round(c.inc, 3) == 0.2, str((first, c.inc))


def test_fix2_lacy_marker():
    b, a, f = setup('lacy')
    give(a, '격동', stacks=5).maxs = 5
    give(f, '뒤엉킨 꿈결', harmful=True)
    b.cast(f, f.d.skills['기본기'], target=a)
    first = (a.stack('격동'), a.stack('뒤엉킨 꿈결 확인용 버프'))
    f.eff.pop('뒤엉킨 꿈결', None)
    b.dirty(f)
    b.cast(f, f.d.skills['기본기'], target=a)
    return first == (5, 0) and a.stack('격동') == 0, str((first, a.stack('격동')))


def test_fix2_post_dependency():
    b, a, f = setup('tyria')
    give(f, '참극의 가시(해제불가)', harmful=True, stacks=2).maxs = 3
    b.cast(a, a.d.skills['기본기'])
    out = (casts(a), f.stack('참극의 가시(해제불가)'))
    return out == (1, 0), str(out)


def test_fix2_consume_timing():
    out = []
    for key, stack, grant in [('kyra', '점화', '은신'), ('harley', '점화', '효과 적중 증가'),
                               ('wedding-carmen', '냉각', None)]:
        for n in [4, 5]:
            b, a, _ = setup(key)
            give(a, stack, stacks=n).maxs = 5
            b.cast(a, a.d.skills['기본기'])
            out.append((a.stack(stack), a.stack(grant) if grant else 0))
            assert not any('체크용' in name for name in a.eff)
    return out == [(5, 0), (1, 1), (5, 0), (1, 1), (5, 0), (1, 0)], str(out)


def test_fix2_break_transition():
    out = []
    for key in ['petra', 'tanya']:
        for broken in [False, True]:
            b, a, f = setup(key, [unit('actor')], [unit('foe', hp=10**9, sa=1)])
            actor = b.allies[1] if key == 'petra' else a
            actor.d.skills['기본기'].ab = 1
            f.broken = broken
            b.cast(actor, actor.d.skills['기본기'])
            out.append((a.stack('점화') if key == 'petra' else a.stack('도약'),
                        a.gauge if key == 'petra' else b.allies[1].gauge))
    return out == [(1, 2000), (0, 0), (4, 1000), (1, 0)], str(out)


def test_fix2_cooldown_slot():
    b, a, f = setup('lugh', foes=[unit('foe', hp=10**9, skills=[dict(slot='특수기', dm=100, cd=3), dict(slot='궁극기', dm=100, cd=5)])])
    f.cd = {'특수기': 2, '궁극기': 3}
    b.cast(a, a.d.skills['궁극기'])
    return f.cd == {'특수기': 2, '궁극기': 4}, str(f.cd)


def test_fix2_cleanse_heal():
    out = []
    for debuff in [False, True]:
        b, a, _ = setup('wedding-carmen', [unit('ally', hp=10**6)])
        x = b.allies[1]
        x.hp = 1000
        if debuff:
            give(x, '회복 불가', {'받는 회복량': -100}, harmful=True)
        b.cast(a, a.d.skills['궁극기'], target=x)
        out.append(x.hp)
    return out[0] == out[1] and out[0] > 1000, str(out)


def test_fix2_extend_scope():
    out = []
    for key, slot in [('cristelle', '궁극기'), ('muriel', '특수기')]:
        b, a, f = setup(key)
        b.roll_hit = lambda *args: True
        e = give(f, '연소', harmful=True, dur=2, stacks=2)
        e.inst = [[a, 1], [a, 2]]
        give(f, '공격력 감소', harmful=True, dur=2)
        give(f, '공격력 증가', dur=2)
        b.cast(a, a.d.skills[slot])
        out.append(([i[1] for i in e.inst], f.eff['공격력 감소'].dur, f.eff['공격력 증가'].dur))
    return out == [([2, 3], 2, 2), ([2, 3], 3, 2)], str(out)


def test_fix2_critical_targets():
    out = []
    for n in [0, 1, 2, 3, 5]:
        b, a, _ = setup('rosaria', foes=[unit(str(i), hp=1 if i == 0 else 10**9, sa=1000) for i in range(5)])
        a.d.stats['cr'] = 10000
        for f in b.foes[n:]:
            give(f, '회피', {'회피율': 100})
        b.cast(a, a.d.skills['궁극기'])
        out.append(a.stack('업화(해제불가)'))
    return out == [0, 1, 2, 3, 3], str(out)


def test_fix2_compound_passive():
    import math
    d = UnitDef(get_db(), 'hilde')
    before = dict(d.passive)
    b = battle([d], [unit('foe')])
    a = b.allies[0]
    out = (a.maxhp, math.floor(d.stats['hp'] * 1.15), dict(d.passive) == before)
    return out[0] == out[1] and out[2], str(out)


def test_fix2_bloom_hp():
    import math
    out = []
    for hp, coef in [(0.5, 0.2), (0.49999, 0.3), (0.49, 0.3)]:
        b, a, _ = setup('besta@개화(SSR)')
        a.hp = a.maxhp * hp
        b.cast(a, a.d.skills['궁극기'])
        out.append((a.shield_total(), math.floor(a.maxhp * coef)))
    return all(a == e for a, e in out), str(out)


def test_fix2_bloom_counts():
    out = []
    for key, slot, coef, cap, kind in [('naru', '기본기', .03, 5, 'harmful'),
                                      ('bunny-claire', '특수기', .03, 5, 'self'),
                                      ('bunny-scarlet', '특수기', .15, 3, 'dot')]:
        for n in [0, 1, 3, 5, 7]:
            b, a, f = setup(key + '@개화(SSR)')
            if kind == 'dot' and n:
                give(f, '연소', harmful=True, stacks=n).inst = [[a, 2] for _ in range(n)]
            elif kind != 'dot':
                for i in range(n):
                    give(a if kind == 'self' else f, 'test%d' % i, harmful=kind != 'self')
            c = pre(b, a, slot)
            got = round(c.inc + c.local_by[f]['inc'], 4)
            exp = round(.15 + coef * min(n, cap), 4)
            out.append((key, n, got, exp))
            assert a.mods()['inc'] == 0
            other = pre(b, a, '궁극기')
            assert round(other.inc + other.local_by[f]['inc'], 4) == .15
    return all(g == e for _, _, g, e in out), str(out)


def test_fix2_bloom_consume():
    out = []
    for own in [False, True]:
        for n in [4, 5]:
            b, a, _ = setup('annah@개화(SSR)', [unit('ally')])
            a.acting = own
            give(a, '점화', stacks=n).maxs = 5
            b.cast(a, a.d.skills['궁극기'])
            out.append((a.stack('점화'), a.stack('강화 반격')))
    return out == [(5, 0), (5, 0), (5, 0), (3, 1)], str(out)


def test_fix2_bloom_break():
    out = []
    for own in [False, True]:
        for broken in [False, True]:
            b, a, f = setup('marcille@개화(SSR)', [unit('actor')], [unit('foe', hp=10**9, sa=1)])
            actor = a if own else b.allies[1]
            actor.d.skills['기본기'].ab = 1
            f.broken = broken
            b.cast(actor, actor.d.skills['기본기'])
            out.append(a.stack('부서진 너트'))
    return out == [2, 0, 2, 0], str(out)


def test_fix2_final_hp():
    from battlesim.api import _norm_party
    out = []
    for final in [False, True]:
        defs, _ = _norm_party({'units': [dict(key='hilde', stats_override={'hp': 10000}, stats_final=final)]}, get_db(), 'fixed')
        b = battle(defs, [unit('foe')])
        out.append(b.allies[0].maxhp)
    return out == [11500, 10000], str(out)


def test_fix2_nested_marker():
    b, a, _ = setup('epindel')
    a.d.stats['cr'] = 0
    give(a, '냉각', stacks=5).maxs = 5
    out = []
    original = b.event_triggers
    def nested(actor, ctx, event):
        if actor is a and not ctx.extra and event == 'own_post':
            out.append(round(b.cast(a, a.d.skills['기본기'], extra=True, parent=ctx).inc, 3))
        return original(actor, ctx, event)
    b.event_triggers = nested
    outer = b.cast(a, a.d.skills['기본기'])
    out.append(round(outer.inc, 3))
    return out == [0.2, 0.4] and not a.has('귀족의 품격'), str(out)


def test_fix2_shield_context():
    b, a, f = setup('wedding-epindel', foes=[unit('plain', hp=10**9, sa=1000), unit('shield', hp=10**9, sa=1000)])
    shielded = b.foes[1]
    give(shielded, '보호막').shield = 1
    for x in b.foes:
        x.gauge = 5000
    b.roll_hit = lambda *args: True
    c = b.cast(a, a.d.skills['궁극기'])
    out = (round(c.inc, 3), [x.gauge for x in b.foes], [x.n_harmful() for x in b.foes])
    c2 = pre(b, a, '궁극기')
    return out == (0.3, [5000, 3000], [0, 0]) and round(c2.inc, 3) == .15, str((out, c2.inc))


def test_fix3_variants():
    out = []
    cases = [('lyn', '궁극기', '명월(해제불가)', 1, 11500, 1, .15),
             ('bunny-frey', '기본기', '하이 롤러(해제불가)', 5, 6500, 1, 1.2),
             ('lydia-moon-caster', '특수기', '퇴근 재촉(해제불가)', 5, 20000, 2, 1.45),
             ('lydia-moon-caster', '궁극기', '퇴근 재촉(해제불가)', 5, 26500, 2, 1.5)]
    for key, slot, mark, n, coef, targets, inc in cases:
        for active in [False, True]:
            b, a, f = setup(key, foes=[unit('one', hp=10**9, sa=1000), unit('two', hp=10**9, sa=1000)])
            a.acting = True
            if active:
                give(a, mark, stacks=n).maxs = n if key != 'lydia-moon-caster' else 10
            c = b.cast(a, a.d.skills[slot])
            if active:
                assert (c.skill.cf[0], len(c.targets), round(c.inc, 2)) == (coef, targets, inc)
                if key == 'lyn':
                    assert c.cd == .5 and c.tough == 1 and not a.has('청풍(해제불가)')
                elif key == 'bunny-frey':
                    assert a.gauge == 3000 and not a.has(mark) and a.stack('냉각') == 1
                else:
                    assert a.stack(mark) == 0 and a.stack('쌓여가는 수치심(해제불가)') == (4 if slot == '특수기' else 6)
                assert a.cd.get(slot, 0) == (c.skill.cd or 0) - (1 if key == 'lyn' else 0)
                if key == 'lyn':
                    a.eff.pop(mark)
                next_cast = b.cast(a, a.d.skills[slot])
                assert next_cast.skill is a.d.skills[slot] and not hasattr(a.d.skills[slot], 'semantic_lines')
            else:
                assert c.skill.name == a.d.skills[slot].name
            out.append((key, active, c.skill.name, len(c.targets), round(c.inc, 2)))
    return True, str(out)


def test_fix3_variant_own_turn_only():
    from battlesim.mc import support_report
    for key, slot, mark in [('bunny-frey', '기본기', '하이 롤러(해제불가)'),
                            ('lydia-moon-caster', '궁극기', '퇴근 재촉(해제불가)')]:
        for own, extra, n in [(False, False, 5), (True, True, 5), (True, False, 4)]:
            b, a, _ = setup(key)
            a.acting = own
            give(a, mark, stacks=n).maxs = 10
            c = b.cast(a, a.d.skills[slot], extra=extra)
            assert c.skill.name == a.d.skills[slot].name
    defs = [UnitDef(get_db(), k) for k in ['lyn', 'bunny-frey', 'lydia-moon-caster', 'hilde']]
    report = support_report(defs)
    assert not any('변형' in x['raw'] or '스킬 교체' in x['raw'] for x in report)
    assert any('선제 방어' in x['raw'] for x in report)
    assert sum('변형' in x for d in defs for x in d.unmodeled) == 4  # 공유 기대값 정의 보존
    return True, '자기 정규 턴 + 임계 스택만 교체'


def test_fix3_pinball():
    b, a, _ = setup('scarlet')
    draws = []
    def choose(names):
        draws.append(tuple(names))
        return names[-1]
    b.rng.choice = choose
    base = a.spd()
    for turn, expected in enumerate([3, 6, 9, 10]):
        b.fire(a, 'own_ts', Ctx(a, a, None))
        assert len(draws) == (turn + 1) * 3
        assert a.stack('세븐볼(해제불가)') == 3
        assert a.spd() == base + expected
        assert round(a.mods()['inc'], 2) == .21
        b.cast(a, a.d.skills['기본기'])
        assert not a.has('세븐볼(해제불가)')
    b.rng.choice = lambda names: names[0]
    b.fire(a, 'own_ts', Ctx(a, a, None))
    assert a.stack('노멀볼(해제불가)') == 3 and round(a.mods()['inc'], 2) == .03
    return not b.unsup, str(dict(b.unsup))


def test_fix3_tyria_stack_role():
    out = []
    for role in ['스트라이커', '디펜더']:
        for n in range(4):
            b, a, f = setup('tyria', foes=[unit('foe', role=role, hp=10**9, sa=1000)])
            if n:
                give(f, '참극의 가시(해제불가)', harmful=True, stacks=n).maxs = 3
            c = b.cast(a, a.d.skills['특수기'])
            val = round(c.inc + c.local_by[f]['inc'], 2)
            expected = round(.2 + n * (.6 if role == '디펜더' else .1), 2)
            assert val == expected, (role, n, val, expected)
            assert not f.has('참극의 가시(해제불가)')
            out.append(val)
    return True, str(out)


def test_fix3_enemy_rank_selectors():
    out = []
    for key, mark, field in [('tyria', '참극의 가시(해제불가)', 'def'), ('hilde', '도발', 'gauge')]:
        b, a, f = setup(key, foes=[unit('one', hp=10**9, sa=1000), unit('two', hp=10**9, sa=1000)])
        high = b.foes[1]
        if field == 'def':
            high.d.stats['def'] *= 3
        else:
            high.gauge = 9000
        b.roll_hit = lambda *args: True
        b.cast(a, a.d.skills['궁극기'], target=f)
        got = [v.stack(mark) for v in b.foes]
        assert got == ([1, 3] if key == 'tyria' else [0, 1]), got
        out.append(got)
    return True, str(out)


def test_fix3_enemy_state_filter():
    b, a, _ = setup('lydia', foes=[unit('plain', hp=10**9, sa=1000), unit('marked', hp=10**9, sa=1000)])
    for f in b.foes:
        f.gauge = 5000
    give(b.foes[1], '미지의 주문', harmful=True)
    b.roll_hit = lambda *args: True
    b.cast(a, a.d.skills['특수기'])
    got = [f.gauge for f in b.foes]
    return got == [5000, 3500], str(got)


def test_fix3_waterbomb_move():
    b, a, f = setup('sunshine-cat-smile', foes=[unit('slow', hp=10**9, sa=1000), unit('fast', spd=300, hp=10**9, sa=1000)])
    fast = b.foes[1]
    give(fast, '면역')
    fast.d.immune = {'물폭탄'}
    b.fire(a, 'wave_start', Ctx(a, a, None))
    assert [v.has('물폭탄') for v in b.foes] == [False, True]
    b.roll_hit = lambda *args: False
    b.cast(a, a.d.skills['기본기'], target=f)
    assert [v.has('물폭탄') for v in b.foes] == [False, True]
    b.roll_hit = lambda *args: True
    b.cast(a, a.d.skills['궁극기'], target=f)
    got = [v.has('물폭탄') for v in b.foes]
    return got == [True, False] and not a.has('물폭탄'), str(got)


def test_fix3_elisa_life_branch():
    out = []
    for dead in [False, True]:
        b, a, _ = setup('elisa', [unit('target'), unit('bystander')])
        v, other = b.allies[1:]
        v.hp = 0 if dead else 100
        v.dead = dead
        c = b.cast(a, a.d.skills['궁극기'], target=v)
        assert not v.dead and v.hp > 100
        assert v.has('성스러운 가호') == (not dead)
        assert other.gauge == 0 and a.gauge == 0
        out.append(v.gauge)
        if dead:
            assert v.hp == v.maxhp * .5
    return out == [4000, 8000], str(out)


def test_fix3_delivery_duration_hot():
    out = []
    for key, dur in [('vera', 1), ('vera@개화(SSR)', 2)]:
        for selected in ['공격력 증가', '방어력 증가', '속도 증가', '지속 회복']:
            b, a, _ = setup(key, [unit('buffed'), unit('plain')])
            v = b.allies[1]
            give(v, '시험 강화', {'공격력%': 1})
            b.rng.choice = lambda names: selected
            b.cast(a, a.d.skills['궁극기'])
            assert v.eff[selected].dur == dur
            assert b.allies[2].has(selected) == (dur == 2)
            if selected == '지속 회복':
                v.hp = 100
                b._tick_dot_hot(v)
                assert v.hp == 1600, v.hp
                give(v, '강화 불가', harmful=True)
                b._tick_dot_hot(v)
                assert v.hp == 1600
            out.append((key, selected, v.eff[selected].dur))
    return True, str(out)


def test_fix3_random_extra_target():
    out = []
    for key in ['carnelia', 'besta@개화(SSR)']:
        b, a, f = setup(key, foes=[unit('first', atk=1, hp=10**9, sa=1000, skills=[dict(slot='기본기', dm=100, all=True)]),
                                  unit('last', hp=10**9, sa=1000)])
        b.rng.choice = lambda pool: pool[-1]
        b.rng.random = lambda: 0
        a.acting = True
        if key == 'carnelia':
            give(a, '칠흑의 잔향(해제불가)')
            b.cast(a, a.d.skills['특수기'], target=f)
        else:
            b.cast(f, f.d.skills['기본기'], target=a)
        targets = [e['targets'] for e in b.timeline if e.get('actor') == a.name and e.get('skill') == '특수기(추가)']
        assert targets == [['last']], targets
        out.append(targets)
    return True, str(out)


def test_fix3_neutral_boost():
    b, a, f = setup('luna')
    b.fire(a, 'battle_start', Ctx(a, a, None))
    assert a.stack('통찰') == 2 and a.n_good() == 0 and a.n_harmful() == 0
    give(a, '강화 불가', harmful=True)
    b.cast(a, a.d.skills['기본기'])
    assert a.stack('통찰') >= 3 and a.on('통찰')
    assert a.mods()['inc_vs']['혼돈'] >= .03
    c = pre(b, a, '궁극기')
    assert c.cd == 0
    give(a, '시험 강화', {'공격력%': 10})
    assert a.n_good() == 1 and a.mods()['atkp'] == 0
    ctx = Ctx(a, a, a.d.skills['궁극기'])
    ctx.targets, ctx.target = [f], f
    b.run_line(a, Line('[스킬 사용 후] 스킬 대상에게 〈시험 카운팅 표지〉', '궁극기', 'active'), ctx)
    assert f.has('시험 카운팅 표지') and f.n_harmful() == 0 and f.n_good() == 0
    return True, '중립 스택은 강화 개수·강화 불가와 독립'


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
