# -*- coding: utf-8 -*-
"""기대값 엔진(engine.Sim)의 능력치·연쇄/지속 피해 계산이 몬테카를로 엔진(mc.Battle)의 client 규칙과 같은 식인지
(stat_stage·stat_floor·buff_maxhp·chain_round·chain_pen·chain_skill_damage_up·chain_stat_true·dot_formula, 식 = battlesim/statcalc.py,
근거 build 26610546 NKM.decompiled.cs:18874-18897·18272-18358·4730-4740·6212-6236·17314·17545-17561).
실행: python -X utf8 -I tests/ev_stat_test.py"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests'), str(ROOT / 'tools')]
from simkit import battle, give, unit                                 # noqa: E402
from battlesim import engine, mc, metrics, statcalc                    # noqa: E402
from battlesim.engine import Buff, Ctx, DummyDef, Sim                  # noqa: E402
from battlesim.rules import BASE_MULT, DEF_K, DEFAULT_OPTS, INF_HP, MC_OPTS, MC_RULES   # noqa: E402

NEW_KEYS = ('stat_stage', 'stat_floor', 'buff_maxhp', 'chain_round', 'chain_pen', 'chain_skill_damage_up',
            'chain_stat_true', 'dot_formula')
LEGACY = {k: MC_RULES[k]['legacy'] for k in NEW_KEYS}
BUFF = {'공격력%': 23.47, '방어력%': -11.13, '속도%': 7.77, '속도': 3, '생명력%': 12.34}


def _units(n=4):
    """단 자료(stat_stage)가 있고 패시브 공격력%가 있는 실제 구원자 몇 명(2단 경로를 타는지 확인용)."""
    import sim_damage as sd
    db = sd.get_db()
    out = []
    for k in sorted(db.units):
        d = metrics.unit_def(k, db=db)
        st = getattr(d, 'stat_stage', None) or {}
        if 'atk' in st and 'def' in st and d.passive['atkp']:
            out.append(d)
        if len(out) >= n:
            break
    assert out, '단 자료가 있는 구원자를 못 찾음'
    return out


def test_default_reads_mc_rules():
    for k in NEW_KEYS:
        assert MC_OPTS[k] == MC_RULES[k]['value']
    s = Sim([DummyDef()], [dict(name='f', hp=INF_HP)], 1)
    assert (s.stage_client, s.floor_client, s.buff_maxhp, s.chain_round, s.chain_pen_client, s.chain_skill_up,
            s.chain_stat_true, s.dot_client) == (True,) * 8
    assert s.party[0].stage_client and s.party[0].floor_client and s.enemies[0].stage_client and s.enemies[0].floor_client
    s = Sim([DummyDef()], [dict(name='f', hp=INF_HP)], 1, dict(LEGACY))
    assert (s.stage_client, s.floor_client, s.buff_maxhp, s.chain_round, s.chain_pen_client, s.chain_skill_up,
            s.chain_stat_true, s.dot_client) == (False,) * 8
    assert not s.party[0].stage_client and not s.enemies[0].floor_client
    # 골든·순위 시험이 옛 값으로 고정하는 목록 = 엔진이 읽는 목록
    assert set(NEW_KEYS) | {'dmg_cap_scope', 'turn_gauge'} == set(engine.ENGINE_MC_KEYS)
    import rank_check
    assert rank_check.ENGINE_MC_KEYS is engine.ENGINE_MC_KEYS


def test_shared_module_and_values():
    assert mc._stat is statcalc and engine._stat is statcalc
    # 손 계산(NKM:18892-18897): 3단 비율은 만분율 정수 합, 최종 Floor
    assert statcalc.rate3(0.123456) == 1235 * 0.0001
    assert statcalc.stage3(1000.0, 0.123456, True) == 1123.0          # floor(1000 + 1000 x 0.1235)
    assert statcalc.stage3(1000.0, 0.123456, False) == 1000.0 * 1.123456
    assert statcalc.stage2((1000.0, 0.2, 50.0), 1250, 0.1) == 1000 + 50 + 1000 * 0.30000000000000004
    assert statcalc.stage2((1000.0, 0.2, 50.0), 1300, 0.1) == 1300 * 1.1     # 다시 계산한 값이 다르면 근사
    assert statcalc.spd_stage3(103.0, 0.0777, 3.0, True) == 114             # floor(103 + 103 x 0.0777 + 3) = floor(114.0031)
    assert statcalc.maxhp(statcalc.maxhp0(10001, 0.15), 0.1234) == math.floor(math.floor(10001 * 1.15) * 1.1234)
    assert statcalc.chain_value(1234.0, 0.5, 0.2, BASE_MULT) == float(int((617 + 617 * 0.2) * BASE_MULT))
    assert statcalc.chain_true_value(1234.0, 0.37) == 456.0


def _pair(d, mc_rules=None, ev_opts=None):
    b = battle([d], [unit('f', hp=10 ** 9, df=1777, spd=113)], mc=mc_rules or {})
    u = b.side_units(0)[0]
    give(u, '시험 버프', dict(BUFF))
    s = Sim([d], [dict(name='f', hp=INF_HP, **{'def': 1777}, spd=113)], 1, dict(DEFAULT_OPTS, **(ev_opts or {})))
    a = s.party[0]
    bf = Buff('시험 버프', dict(BUFF), 1, 3)
    bf.stacks = 1.0
    a.buffs['시험 버프'] = bf
    return b, u, s, a


def test_ally_stats_match_mc():
    for d in _units():
        b, u, s, a = _pair(d)
        assert not u.leader
        assert s.atk_stat(a) == b.atk_stat(u), d.key
        assert s.atk_stat(a, 0.071) == b.atk_stat(u, type('C', (), {'atkp': 0.071})()), d.key   # 이번 시전 한정 공격력%
        assert s.def_stat(a) == b.def_stat(u), d.key
        assert a.spd() == u.spd(), d.key
        assert s.hp_stat(a) == u.maxhp, d.key
        assert s.live_atk(a) == b.live_atk(u), d.key
        assert float(s.atk_stat(a)).is_integer() and float(a.spd()).is_integer()
        # 단별 곱이 한 합과 실제로 다름(2단·3단 경로를 탔는지)
        legacy_atk = d.stats['atk'] * (1 + d.passive['atkp'] + BUFF['공격력%'] / 100 + d.gear_atkp)
        assert s.atk_stat(a) != legacy_atk


def test_ally_stats_match_mc_stage_without_floor():
    for d in _units(2):
        b, u, s, a = _pair(d, mc_rules={'stat_floor': 'float'}, ev_opts={'stat_floor': 'float'})
        assert s.atk_stat(a) == b.atk_stat(u) and s.def_stat(a) == b.def_stat(u) and a.spd() == u.spd()


def test_enemy_stats_match_mc():
    b = battle([unit('a')], [unit('f', hp=10 ** 9, df=1777, spd=113)])
    f = b.side_units(1)[0]
    give(f, '방깎', {'방어력%': -23.33, '속도%': -17.77}, harmful=True)
    s = Sim([DummyDef()], [dict(name='f', hp=INF_HP, **{'def': 1777}, spd=113)], 1)
    e = s.enemies[0]
    e.deb['방깎'] = dict(stacks=1.0, dur=3, defp=-0.2333, spdp=-0.1777)
    assert e.def_eff() == b.def_stat(f) == math.floor(1777 - 1777 * 0.2333)
    assert e.spd_eff() == f.spd() == math.floor(113 - 113 * 0.1777)
    s2 = Sim([DummyDef()], [dict(name='f', hp=INF_HP, **{'def': 1777}, spd=113)], 1, dict(LEGACY))
    s2.enemies[0].deb['방깎'] = dict(e.deb['방깎'])
    assert s2.enemies[0].def_eff() == 1777 * (1 - 0.2333)      # 옛 실수 그대로


def _chain_sim(opts, inc=0.0, pen=0.0, damage_type='ADT_NORMAL'):
    d = DummyDef(atk=2000)
    s = Sim([d], [dict(name='f', hp=INF_HP, **{'def': 1000})], 1, dict(DEFAULT_OPTS, **opts))
    a = s.party[0]
    bf = Buff('b', {'피해 증가': 10.0, '방어 관통': pen * 100}, 1, 3)
    bf.stacks = 1.0
    a.buffs['b'] = bf
    ctx = Ctx(a, a, d.skills['기본기'], False, 1.0)
    ctx.inc = inc
    s.resolve_targets = lambda owner, text, c: ('e', s.enemies)
    s.chain_damage(a, dict(stat='atk', coef=0.37, target='적', damage_type=damage_type), ctx, 1.0)
    return a.dmg_src['chain'], s


def test_chain_client():
    dr = 1000 / (1000 + DEF_K)
    got, _ = _chain_sim({}, inc=0.05, pen=0.3)
    # chain_round·chain_pen·chain_skill_damage_up=client: (int)((2000x0.37 + 그 x (0.10+0.05)) x 1.85) x (1 - 대상 방어율만)
    assert got == float(int((740 + 740 * 0.15) * BASE_MULT)) * (1 - dr)
    got, _ = _chain_sim(dict(LEGACY), inc=0.05, pen=0.3)
    assert got == 2000 * 0.37 * BASE_MULT * (1 - (dr - dr * 0.3)) * 1.10
    got, _ = _chain_sim({}, inc=0.05, pen=0.3, damage_type='ADT_STAT_TRUE')
    assert got == float(int(2000 * 0.37))          # 방어·증감·1.85 없음


def test_dot_client_pen_and_element():
    d = DummyDef(atk=2000)
    d.element = '태양'
    out = {}
    for mode in ('client', 'legacy'):
        s = Sim([d], [dict(name='f', hp=INF_HP, **{'def': 1000}, element='별')], 1,
                dict(DEFAULT_OPTS, dot_formula=mode, stat_stage='add', stat_floor='float'))
        a = s.party[0]
        bf = Buff('b', {'방어 관통': 40.0}, 1, 3)
        bf.stacks = 1.0
        a.buffs['b'] = bf
        e = s.enemies[0]
        e.deb['연소'] = dict(stacks=1.0, dur=3, dot=True, src=a, coef=('atk', 0.2), base=0.0, inc=0.0)
        s.act_enemy(e)
        out[mode] = a.dmg_src['dot']
    dr = 1000 / (1000 + DEF_K)
    base = 2000 * 0.2 * BASE_MULT
    assert out['legacy'] == base * 1.0 * (1 - dr)
    assert abs(out['client'] - base * 1.05 * (1 - (dr - dr * 0.4))) < 1e-9     # 관통 40% + 상성 유리 +5%


if __name__ == '__main__':
    import inspect
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and inspect.isfunction(fn):
            fn()
            n += 1
            print('ok', name)
    print('통과', n)
