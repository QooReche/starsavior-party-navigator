# -*- coding: utf-8 -*-
"""길드 방어전 BFB 상태 기계 시험(battlesim/starsavior/guild_bfb.py, mc.guild_boss).
실행: python -X utf8 -I tests/guild_bfb_test.py
비공개 표(STARSAVIOR_STATIC 또는 ../static-data)가 있으면 data/guild_bfb.json 이 표와 같은지도 확인한다."""
import json
import math
import os
import random
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim import simulate                                   # noqa: E402
from battlesim.mc import Battle                                  # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.api import _norm_party                            # noqa: E402
from battlesim.starsavior.data import get_db                     # noqa: E402
from battlesim.starsavior import guild_bfb as G                  # noqa: E402

PARTY = ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria']
DB = get_db()


def battle(level=0, sets=None, mc=None, seed=1):
    waves, meta = G.build_waves(level, sets)
    defs, _ = _norm_party({'units': PARTY}, DB, 'fixed', 'standard')
    m = dict(MC_OPTS, guild_boss='on')
    m.update(mc or {})
    b = Battle(defs, waves, random.Random(seed), mc=m, leader=0, turn_limit=meta['turn_limit'], battle_mode='boss_kill')
    return b, waves


def to_boss(b):
    b.spawn_wave()
    for u in b.foes:
        b.kill(u, None)
    b.spawn_wave()
    return b.gb.boss


def test_waves_and_stats():
    bfb, gd = G.load()
    w, meta = G.build_waves(0)
    assert [len(x) for x in w] == [2, 1] and meta['turn_limit'] == 50 and meta['battle_mode'] == 'boss_kill'
    boss = w[1][0]
    # 배치 AddStat: 생명력 +80%, 공격 -17.5%, 속도 -25%. 치명 0(패시브 −100%). 속성 = 배치 ChangeAdjustType(별)
    assert boss.stats['hp'] == 468000 and boss.stats['atk'] == 14025 and boss.stats['spd'] == 172, boss.stats
    assert boss.stats['cr'] == 0 and boss.element == '별' and w[0][0].element == '별'
    w12, _ = G.build_waves(12)
    lv = gd['challenge']['levels'][11]
    assert w12[1][0].stats['hp'] == math.floor(260000 * 1.8 * (1 + lv['hp'] / 100)), w12[1][0].stats
    assert w12[1][0].stats['atk'] == math.floor(17000 * 0.825 * (1 + lv['atk'] / 100))
    for bad in (13, -1):
        try:
            G.build_waves(bad)
        except ValueError:
            continue
        raise AssertionError('잘못된 단계 통과: %r' % bad)


def test_switch_off_no_controller():
    """스위치 off 면 BFB 정의가 있어도 상태 기계가 없다. 다른 전투는 스위치를 켜도 영향 없음."""
    b, _ = battle(mc={'guild_boss': 'off'})
    assert b.gb is None
    assert MC_OPTS['guild_boss'] == 'off'
    a = simulate(PARTY, {'stage': 'rush/매니저 그레고리/매니저 그레고리 Ⅰ'}, {'seed': 1, 'n_runs': 5})['outcome']
    c = simulate(PARTY, {'stage': 'rush/매니저 그레고리/매니저 그레고리 Ⅰ'}, {'seed': 1, 'n_runs': 5, 'rules_override': {'guild_boss': 'on'}})['outcome']
    assert a == c, (a, c)


def test_count_all_casts():
    """질투의 시선(58801)은 시전 종류를 가리지 않는다(클라 DoSkill.cs:3025·3695): guild_count=all(기본)이면 협공·반격·추가 발동도 카운트, main 이면 본 행동만"""
    for mode, extra_counts in (('all', True), ('main', False)):
        b, _ = battle(mc={'guild_count': mode})
        to_boss(b)
        gb, a = b.gb, b.alive(0)[0]
        gb.after_cast(a, a.d.skills['기본기'], _Ctx(), False)
        assert gb.count == 1, mode
        for via in ('coop', 'forced_coop', 'revenge', 'trigger', 'reaction'):
            c = _Ctx(); c.via = via
            gb.after_cast(a, a.d.skills['기본기'], c, True)
        assert gb.count == (6 if extra_counts else 1), (mode, gb.count)
    try:
        battle(mc={'guild_count': 'x'})
    except ValueError:
        pass
    else:
        raise AssertionError('잘못된 guild_count 통과')
    print('OK test_count_all_casts')


def test_compete_and_appeal():
    b, _ = battle(mc={'guild_count': 'main'})     # 옛 가정(본 행동만 셈)으로 고정 — all 은 test_count_all_casts
    boss = to_boss(b)
    gb = b.gb
    allies = b.alive(0)
    for i in range(5):
        gb.after_cast(allies[i % 4], allies[i % 4].d.skills['기본기'], _Ctx(), False)
    holder = [v for v in allies if v.has(G.B1)]
    assert len(holder) == 1 and holder[0].stack(G.B1) == 5 and gb.count == 5
    assert b.live_atk(holder[0]) == max(b.live_atk(v) for v in allies)
    # main 모드: 협공·추가 발동(extra)은 세지 않음
    gb.after_cast(allies[0], allies[0].d.skills['기본기'], _Ctx(), True)
    assert gb.count == 5
    gb.after_cast(boss, boss.d.skills['기본기'], _Ctx(), False)       # 보스 공격 후 52093
    assert gb.anim and gb.barrier() and gb.mark is holder[0]
    assert boss.eff[G.B8].shield == math.floor(boss.maxhp * 0.225)
    maids = [v for v in allies if v is not holder[0]]
    assert all(v.has(G.B2) and v.zero_stats for v in maids)
    assert all(b.atk_stat(v) == 0 and b.def_stat(v) == 0 and v.spd() == 1.0 for v in maids)
    before = maids[0].gauge
    b.set_gauge(maids[0], before + 5000)
    assert maids[0].gauge == before, '들러리 게이지 증가 무효'
    assert boss.d.skills['특수기'].name == '독점 선언' and boss.has(G.TOUGH_BAN)
    assert b.pick_attack_target(boss, boss.d.skills['기본기']) is holder[0]
    # 정의 공유 금지: 다른 판의 BFB 정의는 그대로
    assert '특수기' not in G.build_waves(0)[0][1][0].skills
    return b, boss, holder[0], maids


def test_phase_timeout_enforces_hyper2():
    b, boss, holder, maids = test_compete_and_appeal()
    gb = b.gb
    names = []
    real_cast = b.cast

    def spy(u, sk, **kw):
        names.append(sk.name)
        return real_cast(u, sk, **kw)
    b.cast = spy
    for _ in range(5):
        gb.after_cast(boss, boss.d.skills['기본기'], _Ctx(), False)
    assert names == ['축복의 대피로연'], names
    assert not gb.anim and not gb.barrier() and gb.mark is None
    assert not any(v.has(G.B2) or v.zero_stats for v in b.side_units(0))
    assert '특수기' not in boss.d.skills and boss.d.skills['궁극기'].name == '황홀한 허니문'


def test_shield_break_bouquet():
    b, boss, holder, maids = test_compete_and_appeal()
    gb = b.gb
    hp0 = boss.hp
    b.apply_damage(holder, boss, boss.eff[G.B8].shield + 10, 'hit')
    gb.post_hit(holder, boss)
    assert gb.stats['shield_break'] == 1
    assert all(v.has(G.BOUQUET) for v in b.alive(0)) and not any(v.has(G.B1) or v.has(G.B2) for v in b.alive(0))
    assert boss.hp < hp0 - 10, '자해 연쇄 피해'
    assert not boss.has(G.B9) and not boss.has(G.TOUGH_BAN)
    gb.after_cast(holder, holder.d.skills['기본기'], _Ctx(), False)     # 37201
    assert not gb.anim and '특수기' not in boss.d.skills


def test_punish_maids():
    b, boss, holder, maids = test_compete_and_appeal()
    hp = [v.hp for v in maids]
    b.gb.pre_hit(maids[0], boss)
    assert b.gb.stats['punish'] == 1 and all(v.hp < h for v, h in zip(maids, hp))


def test_challenge_effects():
    b, _ = battle(level=12, sets=[3, 3, 3, 3])
    boss = to_boss(b)
    assert boss.on('면역') and boss.eff['면역'].dur == 3
    assert boss.has(G.SPEED) and boss.eff[G.SPEED].props['속도%'] == 30
    assert boss.eff[G.SET_DMG].props['피해 증가'] == 30 and boss.eff[G.SET_RED].props['받는 피해 감소'] == 40
    a = b.alive(0)[0]
    m0 = a.maxhp
    b.gb.post_hit(a, boss)
    assert a.stack(G.DRAIN) == 1 and a.stack(G.DRAIN_SET) == 1 and a.maxhp < m0
    b.gb.after_cast(boss, boss.d.skills['기본기'], _Ctx(), False)
    assert boss.stack(G.STACK) == 1 and boss.eff[G.STACK].props['피해 증가'] == 5


def test_appeal_deferred_to_reaction_queue():
    """정실 어필은 반응 스킬: 반응 큐가 열려 있으면 보스 시전 직후 바로 실행하지 않고 예약(반격이 먼저 나감). 큐 밖이면 바로 실행."""
    for queued in (True, False):
        b, _ = battle(mc={'guild_count': 'main'})
        boss = to_boss(b)
        gb, allies = b.gb, b.alive(0)
        for i in range(5):
            gb.after_cast(allies[i % 4], allies[i % 4].d.skills['기본기'], _Ctx(), False)
        assert gb.count == 5
        b._react_q = [] if queued else None
        gb.after_cast(boss, boss.d.skills['기본기'], _Ctx(), False)
        if queued:
            assert not gb.anim and not gb.barrier() and len(b._react_q) == 1 and b._react_q[0][0] is None
            assert not any(v.has(G.B2) for v in allies), '예약 전에는 들러리 없음'
            b._run_reactions()
            assert gb.anim and gb.barrier() and any(v.has(G.B2) for v in allies)
        else:
            assert gb.anim and gb.barrier()
    print('OK test_appeal_deferred_to_reaction_queue')


def test_revive_clears_maid():
    """부활한 들러리는 정상 능력치로 돌아온다(클라 들러리 300872 는 사망 시 사라짐)"""
    b, _ = battle(mc={'guild_count': 'main'})
    to_boss(b)
    gb, allies = b.gb, b.alive(0)
    for i in range(5):
        gb.after_cast(allies[i % 4], allies[i % 4].d.skills['기본기'], _Ctx(), False)
    gb.after_cast(gb.boss, gb.boss.d.skills['기본기'], _Ctx(), False)
    maid = next(v for v in allies if v.has(G.B2))
    assert maid.zero_stats
    maid.dead = True
    ctx = _Ctx()
    b.resolve = lambda owner, tgt, c, kind=None: [maid]       # 대상 해석만 고정
    b.run_special(allies[0], None, ctx, '자신에게 부활(생명력 50%)')
    assert not maid.dead and not maid.zero_stats and not maid.has(G.B2)
    print('OK test_revive_clears_maid')


def test_simulate_runs():
    r = simulate(PARTY, {'guild': {'level': 0}}, {'seed': 1, 'n_runs': 3, 'build': 'standard', 'timeline': True})
    assert r['encounter']['content'] == 'guild' and r['encounter']['turn_limit'] == 50
    assert any(e.get('skill_name') == '정실 어필' for e in r['timeline']), '정실 어필 발동 안 함'
    assert r['unsupported']['gate_ok']


def test_ally_via_reported():
    """결과 outcome.ally_via 에 아군 시전 경로별 판당 평균이 실린다(길방 편성 찾기가 협공 발생 팀을 거르는 데 씀)"""
    r = simulate(PARTY + [], {'guild': {'level': 0}}, {'seed': 1, 'n_runs': 4, 'build': 'standard'})
    v = r['ally_via']
    assert isinstance(v, dict) and all(isinstance(x, float) or isinstance(x, int) for x in v.values()), v
    print('OK test_ally_via_reported', v)


def test_data_matches_tables():
    static = os.environ.get('STARSAVIOR_STATIC') or os.path.join(ROOT, '..', 'static-data')
    if not os.path.isdir(os.path.join(static, 'tables')):
        print('  (비공개 표 없음 — 건너뜀)')
        return
    out = os.path.join(tempfile.mkdtemp(), 'g.json')
    subprocess.run([sys.executable, '-X', 'utf8', '-I', os.path.join(ROOT, 'tools', 'build_guild_bfb.py'), '--static', static, '--out', out],
                   check=True, capture_output=True)
    with open(out, encoding='utf-8') as f, open(os.path.join(ROOT, 'data', 'guild_bfb.json'), encoding='utf-8') as g:
        assert json.load(f) == json.load(g), 'data/guild_bfb.json 이 게임 표와 다름 — tools/build_guild_bfb.py 다시 실행'


class _Ctx:
    via = None
    kill = False


TESTS = [test_waves_and_stats, test_switch_off_no_controller, test_count_all_casts, test_compete_and_appeal, test_phase_timeout_enforces_hyper2,
         test_shield_break_bouquet, test_punish_maids, test_challenge_effects, test_simulate_runs, test_revive_clears_maid, test_appeal_deferred_to_reaction_queue, test_ally_via_reported, test_data_matches_tables]

if __name__ == '__main__':
    bad = 0
    for t in TESTS:
        try:
            t()
            print('OK  ', t.__name__)
        except Exception as ex:   # noqa: BLE001
            bad += 1
            print('FAIL', t.__name__, type(ex).__name__, ex)
    print('ALL OK %d' % len(TESTS) if not bad else '%d FAIL' % bad)
    sys.exit(1 if bad else 0)
