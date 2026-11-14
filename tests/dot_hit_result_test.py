# -*- coding: utf-8 -*-
"""지속 피해 틱·즉시 피해가 대상의 마지막 피격 결과를 NormalHit 로 덮는지 mc.dot_hit_result.
클라 build 26610546: 지속 피해 틱 OBF_11255(NKM:8037-8090) → OBF_16249(17733) → OBF_7777(18148): DAMAGE_DOT·DAMAGE_INSTANT 이면
OBF_24462(NormalHit)(18163) — 무적·0 피해여도 계산이 먼저. 같은 편 다른 시전자는 17743 에서 먼저 빠짐. 수호자 몫 OBF_21375(17898)도 NormalHit.
엔진은 지속/즉시 피해에서 hit_evaded 를 안 건드려, 스킬 시작 초기화(«회피»)가 남은 유닛이 회피 거부될 수 있었다.
실행: python -X utf8 -I tests/dot_hit_result_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit                            # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS, MC_RULES                    # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402


def _dot(mode='client', guard=False, same_side=False, invincible=False):
    foes = [unit('v', hp=10**7)] + ([unit('g', hp=10**7)] if guard else [])
    b = battle([unit('a'), unit('a2')], foes, mc={'dot_hit_result': mode, 'toughness': 'off'})
    a, v = b.allies[0], b.foes[0]
    src = b.foes[1] if same_side and guard else a
    if guard:
        give(b.foes[1], 'share', {'피해 분담(수호)': 50})
    if invincible:
        give(v, '무적')
    e = give(v, '연소', src=src, harmful=True)
    e.dot, e.inst = ('atk', .4), [[src, 2]]
    for w in b.foes:
        w.hit_evaded = True                                      # 스킬 시작 초기화 뒤 대상이 아니었던 상태
    b._tick_dot_hot(v)
    return b, v


def test_default_client():
    r = MC_RULES['dot_hit_result']
    assert MC_OPTS['dot_hit_result'] == 'client' and r['legacy'] == 'off' and r['grade'] == 'code'
    assert '18163' in r['source']


def test_dot_tick_marks_normal_hit():
    b, v = _dot()
    assert v.hit_evaded is False and b.rule_hits['dot_hit_result'] == 1
    b, v = _dot('off')
    assert v.hit_evaded is True and b.rule_hits['dot_hit_result'] == 0


def test_dot_on_invincible_still_marks():
    b, v = _dot(invincible=True)                                 # 계산(OBF_7777)이 무적 검사보다 먼저
    assert v.hp == v.maxhp and v.hit_evaded is False


def test_dot_guard_share_marks_guard():
    b, v = _dot(guard=True)
    g = b.foes[1]
    assert g.hp < g.maxhp and v.hit_evaded is False and g.hit_evaded is False
    b, v = _dot('off', guard=True)
    assert b.foes[1].hit_evaded is True and v.hit_evaded is True


def test_same_side_caster_dot_does_not_mark():
    b, v = _dot(guard=True, same_side=True)                      # 17743: 같은 편 다른 시전자 → 계산 전에 반환
    assert v.hit_evaded is True and b.rule_hits['dot_hit_result'] == 0


def test_instant_damage_marks_normal_hit():
    for mode, want in (('client', False), ('off', True)):
        b = battle([unit('a')], [unit('v', hp=10**7), unit('v2')], mc={'dot_hit_result': mode})
        a, v, v2 = b.allies[0], b.foes[0], b.foes[1]
        v.hit_evaded = v2.hit_evaded = True
        give(v, '무적')
        b._instant_damage(a, v)
        assert v.hit_evaded is want, mode
        b._instant_damage(v2, v)                                 # 같은 편 다른 시전자 → 덮지 않음
    b = battle([unit('a')], [unit('v', hp=10**7), unit('v2')], mc={'dot_hit_result': 'client'})
    v, v2 = b.foes
    v.hit_evaded = True
    b._instant_damage(v2, v)
    assert v.hit_evaded is True


def test_dot_tick_lifts_evade_reject():
    """관찰 가능한 결과: 지속 피해 틱 뒤 «적 전체» 스킬을 고른 다른 유닛의 피격 시 줄(_evade_rejects)이 더는 거부하지 않음."""
    res = {}
    for mode in ('client', 'off'):
        b = battle([unit('a'), unit('a2')], [unit('f'), unit('f2', skills=[dict(slot='기본기', dm=100),
                                                                       dict(slot='궁극기', dm=100, all=True)])],
                   mc={'dot_hit_result': mode, 'evade_ignore_resist': 'client', 'toughness': 'off'})
        a, f, f2 = b.allies[0], b.foes[0], b.foes[1]
        a.hp = a.maxhp = 10**7
        f2.sel_skill, f2.sel_target = f2.d.skills['궁극기'], a
        a.hit_evaded = True
        e = give(a, '연소', src=f, harmful=True)
        e.dot, e.inst = ('atk', .4), [[f, 2]]
        b._tick_dot_hot(a)
        ctx = Ctx(f2, f, f.d.skills['기본기'])
        ctx.target, ctx.targets = b.allies[1], [b.allies[1]]
        b._cur_line = Line('[스킬 사용 후] (조건: 아군 공격 후) 적 전체에게 〈출혈〉 (2턴)', '기본기', 'active')
        res[mode] = b._evade_rejects(f2, a, ctx)
    assert res == {'client': False, 'off': True}, res


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
