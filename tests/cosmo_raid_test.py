# -*- coding: utf-8 -*-
"""코스모 게이트 시즌 전투 시험(battlesim/starsavior/cosmo_raid.py, mc.cosmo_raid_boss, data/cosmo_raid.json, cosmo_raid.js).
실행: python -X utf8 -I tests/cosmo_raid_test.py
새 클라 표 폴더(CLIENT_ 접두 추출본)가 환경변수 COSMO_TABLES 에 있으면 data/cosmo_raid.json 이 표와 같은지도 확인한다(공개 저장소에는 표 원문이 없음)."""
import collections
import json
import math
import os
import random
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from cosmo_fixture import use_1022, FIXTURE_1022  # noqa: E402
use_1022()  # 시즌 1022 fixture(벨그라스 등 지난 시즌 모델 회귀)
from nodejs import node_available, node_json                      # noqa: E402
from battlesim import simulate                                   # noqa: E402
from battlesim.api import _norm_party                            # noqa: E402
from battlesim.mc import Battle, Eff                             # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior import cosmo_raid as C                 # noqa: E402
from battlesim.starsavior.data import get_db                     # noqa: E402
from battlesim.starsavior.foe import stage_waves                 # noqa: E402

PARTY = ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria']
DB = get_db()
G = C.load()


def battle(boss='벨그라스', step=3, level=0, mc=None, seed=1, party=None):
    waves, meta = C.build_waves(boss, step, level)
    defs, _ = _norm_party({'units': party or PARTY}, DB, 'fixed', 'standard')
    m = dict(MC_OPTS, cosmo_raid_boss='on')
    m.update(mc or {})
    b = Battle(defs, waves, random.Random(seed), mc=m, leader=0, turn_limit=meta['turn_limit'], battle_mode='boss_kill')
    b.spawn_wave()
    return b


def boss_of(b):
    return b.gb.boss


def ally_skill(b, all_=False):
    return C._skill('궁극기' if all_ else '기본기', 'test', 100, 0, 0, all_=all_, tg='적 전체' if all_ else '적 단일')


def hit(b, boss, all_=False, who=0):
    b.cast(b.allies[who], ally_skill(b, all_), target=boss)


# ---------------------------------------------------------------- 데이터
def test_data_shape():
    assert G['season']['id'] == 1022 and [b['key'] for b in G['bosses']] == ['belgras', 'tyria', 'carnelia']
    for b in G['bosses']:
        assert [s['step'] for s in b['steps']] == [1, 2, 3] and all(s['turnLimit'] == 50 for s in b['steps'])
        assert [s['stats']['hp'] for s in b['steps']] == [56000, 84000, 1000000]
        assert [s['stats']['atk'] for s in b['steps']] == [2060, 2940, 5255] and [s['stats']['spd'] for s in b['steps']] == [140, 160, 180]
        assert [s['stats']['def'] for s in b['steps']] == [700, 1400, 3000]
        assert len(b['levels']) == 18 and b['steps'][0]['difficultyGroup'] is None and b['steps'][2]['difficultyGroup'] == b['difficultyGroupId']
        # 챌린지 효과는 3·6·9·12·15·18 레벨에서 하나씩 늘어난다
        sizes = [len(r['effects']) for r in b['levels']]
        assert sizes == [0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6], sizes
        assert [r['level'] for r in b['levels'] if r['unlock']] == [3, 6, 9, 12, 15, 18]
        assert b['levels'][0]['atk'] == 2000 and b['levels'][17]['atk'] == 19000 and b['levels'][17]['hp'] == 9500 and b['levels'][17]['scoreBonus'] == 39000
    assert [b['difficultyGroupId'] for b in G['bosses']] == [1013, 1008, 1012]
    assert all(e['kind'] for e in G['effects']) and len(G['effects']) == 12
    assert {s['id'] for b in G['bosses'] for s in b['seasonBuffs']} == {8057, 8064, 8062, 8060, 8068, 8058}


def test_stage_stats_match_existing_cosmo():
    """티리아·카넬리아 Step 스탯 = 기존 databook cosmo N단계(같은 FoeDef 경로를 재사용하므로 같아야 함)"""
    for key, nm in (('tyria', '티리아'), ('carnelia', '카넬리아')):
        b = C.boss_data(key)
        for st in b['steps']:
            d = stage_waves('cosmo', nm, '%s %d단계' % (nm, st['step']))[1][0][0]
            for k in ('hp', 'atk', 'def', 'spd'):
                assert d.stats[k] == st['stats'][k], (key, st['step'], k)


def test_build_waves_and_scale():
    w, meta = C.build_waves('벨그라스', 3, 0)
    assert [d.name for d in w[0]] == ['기록자', '벨그라스', '처단자'] and meta['battle_mode'] == 'boss_kill' and meta['turn_limit'] == 50
    bel = w[0][1]
    assert bel.spawn == 'S' and bel.boss and bel.element == '태양' and bel.role == '레인저' and bel.stats['hp'] == 1000000
    assert '기절' in bel.immune
    w18, _ = C.build_waves('belgras', 3, 18)
    s = w18[0][1].stats
    assert s['atk'] == math.floor(5255 * 2.9) and s['hp'] == math.floor(1000000 * 1.95) and s['def'] == math.floor(3000 * 1.95), s
    t18 = C.build_waves('티리아', 3, 18)[0][0][0].stats
    assert t18['atk'] == math.floor(5255 * 2.9) and t18['spd'] == 180 and t18['hp'] == 1950000
    t1 = C.build_waves('카넬리아', 1, 0)[0][0][0].stats
    assert t1['hp'] == 56000 and t1['atk'] == 2060
    for bad in (('벨그라스', 1, 3), ('벨그라스', 4, 0), ('벨그라스', 3, 19), ('벨그라스', 3, -1), ('없는 보스', 3, 0)):
        try:
            C.build_waves(*bad)
        except ValueError:
            continue
        raise AssertionError('잘못된 입력 통과: %r' % (bad,))


def test_switch_off_no_controller():
    b = battle(mc={'cosmo_raid_boss': 'off'})
    assert b.gb is None and MC_OPTS['cosmo_raid_boss'] == 'off'
    try:
        battle(mc={'cosmo_raid_boss': 'wrong'})
    except ValueError:
        pass
    else:
        raise AssertionError('잘못된 cosmo_raid_boss 통과')
    # 다른 전투는 스위치를 켜도 영향 없음
    a = simulate(PARTY, {'stage': 'rush/매니저 그레고리/매니저 그레고리 Ⅰ'}, {'seed': 1, 'n_runs': 5})['outcome']
    c = simulate(PARTY, {'stage': 'rush/매니저 그레고리/매니저 그레고리 Ⅰ'}, {'seed': 1, 'n_runs': 5, 'rules_override': {'cosmo_raid_boss': 'on'}})['outcome']
    assert a == c


# ---------------------------------------------------------------- 시즌 버프·챌린지 효과
def test_season_buffs():
    for boss in ('벨그라스', '티리아', '카넬리아'):
        b = battle(boss, 3, 0)
        bd = C.boss_data(C.boss_by_name(boss)['key'])
        total = 0
        for sb in bd['seasonBuffs']:
            kind, val = next(iter(sb['filter'].items()))
            for u in b.allies:
                has = u.stack('%s %d' % (C.SEASON, sb['id'])) > 0
                assert has == ((u.element if kind == 'element' else u.role) == val), (boss, sb['id'], u.name)
                total += has
        assert total > 0, '파티에 시즌 버프 대상이 하나도 없음: ' + boss
    b = battle('벨그라스', 3, 0)
    sup = [u for u in b.allies if u.role == '서포터'][0]
    assert sup.maxhp == math.floor(sup.maxhp0 * 1.3)         # 8064 서포터 최대 생명력 +30%
    b2 = battle('벨그라스', 3, 0, mc={'cosmo_raid_boss': 'off'})
    assert b2.allies[0].mods()['atkp'] == 0 and sup.maxhp > [u for u in b2.allies if u.role == '서포터'][0].maxhp


def test_challenge_effects_attached():
    b = battle('티리아', 3, 18)
    boss = boss_of(b)
    assert boss.mods()['spdp'] == 0.3 and boss.on('면역') and boss.mods()['tough'] == 0 and 'single' not in boss.mods()['red']
    assert set(b.gb.fx) == {'drain', 'pressure', 'rewind', 'march'}, b.gb.fx
    b = battle('벨그라스', 3, 18)
    boss = boss_of(b)
    assert boss.mods()['red']['single'] == 0.2 and boss.mods()['spdp'] == 0.3 and boss.mods()['tough'] == 1 and not boss.on('면역')
    assert set(b.gb.fx) == {'drain', 'backflow', 'thorn'}
    b = battle('카넬리아', 3, 18)
    boss = boss_of(b)
    assert boss.mods()['spdp'] == 0.3 and boss.mods()['tough'] == 1 and not boss.on('면역')
    assert set(b.gb.fx) == {'drain', 'punish', 'bleed', 'backflow'}
    b = battle('카넬리아', 3, 6)          # 6레벨까지는 쇠락 하나뿐(시공은 9)
    assert set(b.gb.fx) == {'drain'} and boss_of(b).mods()['spdp'] == 0
    b = battle('카넬리아', 3, 2)
    assert b.gb.fx == {} and not boss_of(b).eff, boss_of(b).eff


def test_drain_rewind_backflow_direct():
    b = battle('티리아', 3, 18)
    boss = boss_of(b)
    boss.eff['타임 패러독스'] = Eff('타임 패러독스', {}, 1, 4, boss, True)
    boss.eff['타임 패러독스'].stacks = 1
    boss.d.skills  # 접근 확인
    g0 = boss.gauge
    ally = b.allies[0]
    hit(b, boss, who=0)
    assert b.gb.stats['rewind'] == 1 and b.gb.stats['drain'] == 1
    assert ally.stack(C.CH_DRAIN) == 1 and ally.mods()['hpp'] == -0.05          # 쇠락: 타격자 최대 생명력 -5%
    assert boss.gauge != g0
    b = battle('벨그라스', 3, 18)
    boss = boss_of(b)
    a1 = b.allies[1]
    a1.eff['공격력 감소'] = Eff('공격력 감소', {'공격력%': -30}, 1, 2, boss, True)
    a1.eff['공격력 감소'].stacks = 1
    hit(b, boss, who=1)
    assert b.gb.stats['backflow'] == 1


def test_pressure_march_bleed_thorn_punish_direct():
    b = battle('티리아', 3, 18)
    boss = boss_of(b)
    sk = boss.d.skills['기본기']
    n0 = sum(1 for _ in b.foes)
    b.cast(boss, sk)
    assert b.gb.stats['pressure'] >= 1 and b.gb.stats['march'] >= 1, dict(b.gb.stats)
    b = battle('카넬리아', 3, 18)
    boss = boss_of(b)
    b.cast(boss, boss.d.skills['기본기'])
    assert b.gb.stats['bleed'] >= 1 and any(u.has(C.BLEED) for u in b.allies)
    b = battle('카넬리아', 3, 18)
    boss = boss_of(b)
    for u in b.allies:
        u.eff['공격력 감소'] = Eff('공격력 감소', {'공격력%': -30}, 1, 3, boss, True)
        u.eff['공격력 감소'].stacks = 1
    kinds = []
    orig_apply = b.apply_damage
    b.apply_damage = lambda a, v, dmg, kind, shieldable=True: (kinds.append((kind, v)), orig_apply(a, v, dmg, kind, shieldable))[1]
    b.cast(boss, boss.d.skills['궁극기'])
    b.gb.flush_damage()          # 응징은 반격·반응 뒤 추가 피해 처리 단계
    assert b.gb.stats['punish'] == len(b.allies)
    assert sum(1 for k, _ in kinds if k == 'chain') == len(b.allies), '응징 연쇄 피해가 대상마다 한 번씩 들어가야 함'
    b = battle('벨그라스', 3, 18)
    boss = boss_of(b)
    b.cast(boss, boss.d.skills['궁극기'])
    assert b.gb.stats['thorn'] >= 1 and any(u.has(C.THORN) for u in b.allies)


def test_punish_client_timing():
    """SET 31 응징(SE 9403101): 궁극기 «스킬 시작»(대상 확정 직후·타격 전) 때 조건 1161(스킬 대상 중 하나라도 약화) → 약화 상태인 적
    «전원»(AutoTargetId 10, 스킬 대상만이 아님)에게 공격력 30% 추가 피해. 공격자 쪽 값은 생성 때, 대상 방어는 넣을 때(NKM:4734·6226·8168),
    넣는 시점은 반격·반응 뒤 추가 피해 처리 단계(NKM:15382·13961 → flush_damage). 옛 엔진은 궁극기 «뒤» 맞은 대상 기준(codex 2차 리뷰 3건 반영)"""
    from types import SimpleNamespace

    def setup(debuffed):
        b = battle('카넬리아', 3, 18)
        boss = boss_of(b)
        for i in debuffed:
            u = b.allies[i]
            u.eff['공격력 감소'] = Eff('공격력 감소', {'공격력%': -30}, 1, 3, boss, True)
            u.eff['공격력 감소'].stacks = 1
        return b, boss
    hyper = lambda boss: boss.d.skills['궁극기']    # noqa: E731
    lb = lambda: collections.defaultdict(lambda: {'inc': 0.0})    # noqa: E731
    # 대상 판정: 스킬 대상이 아군 0 하나(약화 없음)이면, 약화된 아군 2 가 있어도 미발동
    b, boss = setup([2])
    b.gb.skill_start(boss, hyper(boss), SimpleNamespace(src=boss, skill=hyper(boss), targets=[b.allies[0]], inc=0.0, local_by=lb()))
    assert b.gb._punish_q == []
    # 스킬 대상(아군 1)이 약화면 참 → 대상이 아닌 약화 아군 2 도 포함, 약화 없는 아군 0 은 제외
    b, boss = setup([1, 2])
    b.gb.skill_start(boss, hyper(boss), SimpleNamespace(src=boss, skill=hyper(boss), targets=[b.allies[0], b.allies[1]], inc=0.0, local_by=lb()))
    assert sorted(x.pos for x, _ in b.gb._punish_q) == sorted([b.allies[1].pos, b.allies[2].pos])
    # 대상 방어는 넣을 때 값: 생성 뒤 방어가 오르면 피해가 줄어듦(공격자 쪽 값만 생성 때 확정)
    x, pre = b.gb._punish_q[0]
    lo = b.gb._chain_hit(boss, x, dict(pre))
    b.put_eff(x, '시험 방어 증가', {'방어력%': 200}, dur=5, maxs=1, add=1, src=x, cat='buff', fixed=False)
    assert b.gb._chain_hit(boss, x, dict(pre)) < lo
    # 실제 시전: 약화 아군 1명이면 연쇄 1회(전원 광역 궁극기라도), 큐는 행동 뒤(flush_damage)에 비워짐
    b, boss = setup([3])
    b.cast(boss, hyper(boss))
    assert b.gb._punish_q, '시전 직후(반격·반응 전)에는 아직 넣지 않음'
    b.gb.flush_damage()
    assert b.gb.stats['punish'] == 1 and b.gb._punish_q == []
    # 약화 아군 전원이 「스킬 피해 무효」여도(타격 경로가 pre_hit 전에 끝나도) 스킬 시작 판정이라 응징은 들어감
    b, boss = setup([1, 2])
    for i in (1, 2):
        b.put_eff(b.allies[i], '스킬 피해 무효', {}, dur=5, maxs=1, add=1, src=b.allies[i], cat='buff', fixed=False)
    b.cast(boss, hyper(boss))
    b.gb.flush_damage()
    assert b.gb.stats['punish'] == 2, dict(b.gb.stats)
    # 같은 행동 안에서 궁극기가 두 번 시작되면(반응 재시전) 예약이 누적됨 — 덮어쓰지 않음(NKM:6239-6241, codex 재검토)
    b, boss = setup([1, 2])
    for _ in range(2):
        b.gb.skill_start(boss, hyper(boss), SimpleNamespace(src=boss, skill=hyper(boss), targets=list(b.allies), inc=0.0, local_by=lb()))
    assert len(b.gb._punish_q) == 4
    b.gb.flush_damage()
    assert b.gb.stats['punish'] == 4 and b.gb._punish_q == []
    # 시작 때 약화가 아무도 없으면 미발동(궁극기가 거는 약화는 시작 뒤라 세지 않음)
    b, boss = setup([])
    b.cast(boss, hyper(boss))
    b.gb.flush_damage()
    assert b.gb.stats.get('punish', 0) == 0


# ---------------------------------------------------------------- 벨그라스 상태 기계
def test_belgras_erosion_and_rot():
    b = battle('벨그라스', 3, 0)
    boss = boss_of(b)
    gp = b.gb
    assert boss.stack(C.ERO) == 0 and boss.d.stats['def'] == 3000
    b.cast(boss, boss.d.skills['특수기'])                      # 생기 약탈: 침식된 의지 35회
    assert boss.stack(C.ERO) == 35 and boss.has(C.TOUGH_BAN)
    assert abs(b.def_stat(boss) - 3000 * (1 + 0.05 * 35)) < 1e-6 and abs(boss.mods()['spdp'] - 0.35) < 1e-9
    hit(b, boss)                                              # 단일 -1
    assert boss.stack(C.ERO) == 34 and boss.stack(C.ROT) == 0
    hit(b, boss, all_=True)                                   # 전체 -17
    assert boss.stack(C.ERO) == 17
    gp._put(boss, C.ERO, {}, maxs=35, add=0)
    boss.eff[C.ERO].stacks = 1
    hit(b, boss)                                              # 마지막 한 겹: 0 이 되지만 같은 타격에서는 썩은 의지가 안 생김(체크 버프 근사)
    assert boss.stack(C.ERO) == 0 and boss.stack(C.ROT) == 0 and not boss.has(C.TOUGH_BAN)
    hit(b, boss)                                              # 침식·잠행 없음 -> 단일 +1
    assert boss.stack(C.ROT) == 1
    hit(b, boss, all_=True)                                   # 전체 +5
    assert boss.stack(C.ROT) == 6 and abs(b.def_stat(boss) - 3000 * 0.94) < 1e-6
    nonatk = C._skill('특수기', 'buff', 0, 0, 0, attack=False, tg='자신')
    b.cast(b.allies[0], nonatk)                               # 적의 비공격 스킬: 썩은 의지 +5
    assert boss.stack(C.ROT) == 11
    b.cast(boss, boss.d.skills['궁극기'])                      # 공허 붕괴: 추가 고정 피해 5000 x 11
    assert gp.stats['true_damage_hits'] == 0 and len(gp.pending_damage) == 1
    hp = boss.hp
    shield = boss.shield_total()
    gp.flush_damage()
    assert gp.stats['true_damage_hits'] == 1
    assert hp - boss.hp == max(0, 55000 - shield)
    assert boss.stack(C.ERO) == 0 and boss.stack(C.ROT) == 0 and boss.has(C.ROOT) and boss.has(C.TOUGH_BAN)
    assert abs(boss.mods()['spdp'] - 0.5) < 1e-9


def test_belgras_thorn_gauge_growth():
    b = battle('벨그라스', 3, 0)
    boss = boss_of(b)
    b.cast(boss, boss.d.skills['기본기'])                      # 연쇄 파열: 적 전체 잔멸의 가시 + 끝없는 성장
    assert all(u.has(C.THORN) for u in b.allies if not u.dead) and boss.stack(C.GROW) == 1
    boss.gauge = 0.0
    hit(b, boss)                                              # 가시 상태 아군의 단일 공격에 피격 -> 게이지 +20%
    assert boss.gauge >= 2000
    b2 = battle('벨그라스', 3, 0)
    assert boss_of(b2).gauge >= 5000                         # 패시브1: 전투 시작 게이지 +50%


def test_minions():
    b = battle('벨그라스', 3, 0)
    boss = boss_of(b)
    rec, exe = b.gb.minions['recorder'], b.gb.minions['executioner']
    assert rec.invincible() and exe.invincible() and rec.spd() == 0 and rec.stack(C.STACKS) == 5
    hp0 = rec.hp
    hit(b, boss, all_=True)                                   # 전체 공격은 부속 유닛도 맞힘: -3 (무적이라 피해 없음)
    assert rec.stack(C.STACKS) == 2 and rec.hp == hp0
    hit(b, boss, all_=True)                                   # 0 이 되면 보상: 기록자 = 타격자 공격력 +50% 3턴, 처단자 = 아군 전체 보호막
    assert rec.stack(C.STACKS) == 0 and b.gb.stats['minion_break'] == 2
    assert b.allies[0].mods()['atkp'] >= 0.5 and all(u.shield_total() > 0 for u in b.allies)
    assert b.gb.over[rec] > b.gb._gt()                        # 영양 과잉 10턴
    # 응집된 생기가 있는 동안 벨그라스가 공격하면 공격력 증가/보호막이 붙는다
    b = battle('벨그라스', 3, 0)
    boss = boss_of(b)
    b.cast(boss, boss.d.skills['기본기'])
    assert boss.mods()['atkp'] >= 0.5 and 0.01 * boss.maxhp - 1 <= boss.shield_total() < 0.02 * boss.maxhp   # cosmo_boss_barrier=client: 1%
    b = battle('벨그라스', 3, 0, mc=dict(cosmo_boss_barrier='legacy'))
    boss = boss_of(b)
    b.cast(boss, boss.d.skills['기본기'])
    assert boss.shield_total() >= 0.25 * boss.maxhp - 1                                     # legacy: 25%


# ---------------------------------------------------------------- 시뮬 경로
def run(boss, step, level, n=12, seed=2, **o):
    return simulate({'units': PARTY}, {'cosmo_raid': {'boss': boss, 'step': step, 'level': level}},
                    dict({'seed': seed, 'n_runs': n, 'build': 'standard'}, **o))


def test_simulate_clear_step1_step2():
    """Step 1·2 는 standard 육성으로 클리어 가능: 진행도·점수가 실제로 나오고 경로가 탔는지 확인"""
    for boss in ('벨그라스', '티리아', '카넬리아'):
        for step in (1, 2):
            r = run(boss, step, 0)
            c = r['cosmo_raid']
            assert r['outcome']['clear_p'] > 0 and r['outcome']['progress'] > 0, (boss, step, r['outcome'])
            clears = [i for i, x in enumerate(c['clear_runs']) if x]
            assert clears and all(c['damage_frac_runs'][i] == 1.0 and c['remain_turns_runs'][i] > 0 and c['survivors_runs'][i] > 0 for i in clears)
            i = clears[0]
            st = C.boss_data(C.boss_by_name(boss)['key'])['steps'][step - 1]
            assert c['score_runs'][i] == st['base'] + st['maxDamage'] + st['remainTurn'] * c['remain_turns_runs'][i] + st['survivor'] * c['survivors_runs'][i]
            assert r['encounter']['turn_limit'] == 50 and r['encounter']['cosmo_raid']['step'] == step


def test_simulate_belgras_path_taken():
    """Step 3 에서 상태 기계 경로(특수기·공허 붕괴·부속 유닛·썩은 의지·추가 고정 피해)가 실제로 여러 번 탄다"""
    r = run('벨그라스', 3, 0, n=10)
    ctl = r['cosmo_raid']['ctl']
    assert r['outcome']['progress'] > 0
    for k in ('special', 'hyper', 'minion_break', 'rot_gain', 'true_damage_hits'):
        assert ctl.get(k, 0) > 0, (k, ctl)
    # 스위치를 끄면(= 난이도·챌린지·상태 기계 없음) 결과가 달라진다: 시험이 기능을 실제로 지키는지 확인
    r2 = run('벨그라스', 3, 0, n=10, rules_override={'cosmo_raid_boss': 'off'})
    assert r2['cosmo_raid']['ctl'] == {} and r2['cosmo_raid']['damage_frac_runs'] != r['cosmo_raid']['damage_frac_runs']


def test_simulate_challenge_paths_and_level_scale():
    # 티리아 SE10253015의 반복별 선택·부여로 난수 소비 횟수가 달라짐.
    # 이전 seed=2는 legacy에서 응징 1회, client에서는 0회였음.
    # 두 모드에서 실제 응징·출혈 경로가 실행되는 시드를 각각 보존함.
    for mode, seed in (('client', 1), ('legacy', 2)):
        r = run('카넬리아', 3, 18, n=10, seed=seed, rules_override={'auto_se_reselect': mode})
        ctl = r['cosmo_raid']['ctl']
        assert r['outcome']['progress'] > 0
        assert ctl.get('punish', 0) > 0 and ctl.get('bleed', 0) > 0, (mode, ctl)
    ctl = run('티리아', 3, 18, n=10)['cosmo_raid']['ctl']
    assert ctl.get('pressure', 0) > 0 and ctl.get('march', 0) > 0 and ctl.get('drain', 0) > 0, ctl
    ctl = run('벨그라스', 3, 18, n=10)['cosmo_raid']['ctl']
    assert ctl.get('thorn', 0) > 0 and ctl.get('backflow', 0) > 0, ctl
    # 레벨이 높을수록 보스를 덜 깎는다(Step 3, 같은 시드)
    lo = run('티리아', 3, 0, n=10)['cosmo_raid']['damage_frac_runs']
    hi = run('티리아', 3, 18, n=10)['cosmo_raid']['damage_frac_runs']
    assert sum(lo) > sum(hi) > 0


def test_existing_results_unchanged_fields():
    r = run('티리아', 1, 0, n=4)
    for k in ('prog_runs', 'ally_via', 'outcome', 'per_unit'):
        assert k in r
    assert len(r['prog_runs']) == 4 and r['unsupported']['gate_ok'] in (True, False)
    plain = simulate({'units': PARTY}, {'stage': 'cosmo/티리아/티리아 1단계'}, {'seed': 2, 'n_runs': 4, 'build': 'standard'})
    assert 'cosmo_raid' not in plain       # 기존 경로 결과에는 새 최상위 키가 없다


# ---------------------------------------------------------------- 점수
def test_score_values_and_bounds():
    s = lambda *a, **k: C.cosmo_score(G, *a, **k)
    # Step 1: 기본 0 + 100000 x 비율 + 1000 x 남은 턴 + 2000 x 생존
    assert s(0, 0.0, 0, 0, False, boss='belgras', step=1) == 0
    assert s(0, 0.5, 30, 4, False, boss='belgras', step=1) == 50000
    assert s(0, 1.0, 40, 4, True, boss='belgras', step=1) == 100000 + 40000 + 8000
    assert s(5, 1.0, 40, 4, True, boss='tyria', step=1) == 148000, '난이도는 Step 3 에서만'
    # Step 3 Lv0: 배율·달성 점수 없음
    assert s(0, 0.0, 0, 0, False) == 553000
    assert s(0, 0.5, 0, 0, False) == 553000 + 1250000
    assert s(0, 1.0, 10, 4, True) == 553000 + 2500000 + 25000 + 200000
    # Lv18: 배율 +390%, 달성 점수 배율 미적용
    raw = 553000 + 1250000
    assert s(18, 0.5, 0, 0, False) == raw * 4.9 // 1 + 300000
    assert s(18, 0.4999, 0, 0, False) == (553000 + 2500000 * 4999 // 10000) * 49 // 10, '0.5 미만은 HalfHPScore 없음'
    full = 553000 + 2500000 + 2500 * 20 + 50000 * 4
    assert s(18, 1.0, 20, 4, True) == full * 49 // 10 + 300000 + 600000
    # 비율은 1/10000 내림(0.00005 -> 0), 부동소수 오차(0.29)에도 2900
    assert s(0, 0.00005, 0, 0, False, boss='belgras', step=2) == 158000
    assert s(0, 0.29, 0, 0, False, boss='belgras', step=2) == 158000 + 250000 * 2900 // 10000
    assert s(0, -3, 0, 0, False) == 553000 and s(0, 9, 0, 0, False) == 553000 + 2500000
    for bad in (19, -1):
        try:
            s(bad, 0.5, 0, 0, False)
        except ValueError:
            continue
        raise AssertionError('잘못된 레벨 통과')


def test_data_driven_defaults():
    """보스 이름을 코드에 고정하지 않음: 기본 보스는 시즌 데이터의 첫 보스, 면역 목록 빌릴 보스는 데이터(같은 immuneGroup)에서 고른다"""
    import copy
    from battlesim.starsavior import foe
    d = copy.deepcopy(G)
    d['season']['bossOrder'] = ['tyria', 'belgras', 'carnelia']
    next(b for b in d['bosses'] if b['key'] == 'tyria')['steps'][2]['base'] += 1234        # 보스마다 점수표가 같아서 구분되게 바꿈
    a = C.cosmo_score(d, 0, 0.5, 0, 0, False)
    assert a == C.cosmo_score(d, 0, 0.5, 0, 0, False, boss='tyria') and a != C.cosmo_score(d, 0, 0.5, 0, 0, False, boss='belgras'), '기본 보스가 데이터 순서를 따름'
    assert C.cosmo_score(G, 0, 0.5, 0, 0, False) == C.cosmo_score(G, 0, 0.5, 0, 0, False, boss='belgras')
    calls = []
    real = foe.stage_waves

    def spy(content, tab, name, src=C.SRC):
        calls.append((content, tab, name))
        return real(content, tab, name, src)
    foe.stage_waves = spy
    try:
        C._donor_immune(C.boss_data('belgras'), C.SRC)
        assert calls[-1] == ('cosmo', '티리아', '티리아 3단계'), calls
        # 데이터를 바꾸면(티리아 면역 그룹 변경 -> 카넬리아가 빌려 줌) 다른 보스를 고른다
        other = copy.deepcopy(G)
        for b in other['bosses']:
            if b['key'] == 'tyria':
                b['immuneGroup'] = 9999
        key, keep = C.data_path(), C._DATA[C.data_path()]
        C._DATA[key] = other         # 자료 캐시 키 = 자료 파일 경로(cosmo_raid.data_path)
        try:
            C._donor_immune(next(b for b in other['bosses'] if b['key'] == 'belgras'), C.SRC)
        except Exception:
            pass       # 가짜 src 로는 databook 줄을 못 읽음: 호출 인자만 본다
        assert calls[-1][1:] == ('카넬리아', '카넬리아 3단계'), calls
        for b in other['bosses']:
            b['immuneGroup'] = b['raidGroupId']          # 같은 면역 그룹이 없으면 분명한 오류
        try:
            C._donor_immune(next(b for b in other['bosses'] if b['key'] == 'belgras'), C.SRC)
        except ValueError as e:
            assert '면역' in str(e)
        else:
            raise AssertionError('빌려 줄 보스가 없는데 통과')
    finally:
        foe.stage_waves = real
        if 'key' in locals():
            C._DATA[key] = keep


def test_js_parity():
    if not node_available():
        from tools.runtime import skip_note
        skip_note('cosmo_raid_test.test_js_parity: node 없음')
        return
    cases = []
    for boss in ('belgras', 'tyria', 'carnelia'):
        for step in (1, 2, 3):
            for level in ((0, 1, 3, 17, 18) if step == 3 else (0, 7)):
                for f in (-1, 0, 0.00005, 0.0001, 0.29, 0.4999, 0.5, 0.9999, 1, 2):
                    for clear in (False, True):
                        for rt, sv in ((0, 0), (17, 3), (49, 4)):
                            cases.append([level, f, rt, sv, clear, boss, step])
    cf = os.path.join(tempfile.mkdtemp(), 'cases.json')
    with open(cf, 'w', encoding='utf-8') as f:
        json.dump(cases, f)
    js = node_json("const V=require('./cosmo_raid.js'),fs=require('fs'),G=JSON.parse(fs.readFileSync(" + json.dumps(FIXTURE_1022) + ",'utf8'));"
                   "console.log(JSON.stringify(JSON.parse(fs.readFileSync(" + json.dumps(cf) + ",'utf8')).map(c=>V.cosmoScore(G,...c))))")
    assert js == [C.cosmo_score(G, *c) for c in cases]
    assert len(set(js)) > 50
    eff = node_json("const V=require('./cosmo_raid.js'),G=JSON.parse(require('fs').readFileSync(" + json.dumps(FIXTURE_1022) + ",'utf8'));"
                    "console.log(JSON.stringify([0,2,3,6,18].map(l=>V.levelEffects(G,'carnelia',l).map(e=>e.id))))")
    assert eff == [[], [], [940011], [940011, 940101], [940011, 940101, 940021, 940301, 940091, 940191]]


# ---------------------------------------------------------------- EX 챌린지 효과 8종
def test_ex_grow():
    """SET 01 grow: 스킬 사용 후 주는 피해 +5% 중첩 최대 10 (SE 9400101, BI_STAR_CHALLENGE_EX_1 IsLevel BuffLevelMax 10)"""
    # 대조군: grow 없을 때 1회 시전 후 inc
    b0 = battle('티리아', 3, 0, seed=99)
    boss0 = boss_of(b0)
    b0.cast(boss0, boss0.d.skills['기본기'])
    ctrl_inc = boss0.mods()['inc']
    assert boss0.stack(C.CH_GROW_EX) == 0 and b0.gb.stats.get('grow', 0) == 0
    # grow 적용
    b = battle('티리아', 3, 0, seed=99)
    boss = boss_of(b)
    b.gb.fx['grow'] = {'pct': 5, 'max': 10}
    sk = boss.d.skills['기본기']
    b.cast(boss, sk)
    assert boss.stack(C.CH_GROW_EX) == 1 and b.gb.stats['grow'] == 1
    assert abs(boss.mods()['inc'] - (ctrl_inc + 0.05)) < 1e-9, 'ctrl=%r actual=%r' % (ctrl_inc, boss.mods()['inc'])
    for _ in range(11):
        b.cast(boss, sk)
    assert boss.stack(C.CH_GROW_EX) == 10, boss.stack(C.CH_GROW_EX)   # 상한 10


def test_ex_armor():
    """SET 04 armor: 강인도 최대치 +5 (SE 9400401, NSEAT_AFTER_SPAWN, BI_STAT_NST_SUPER_ARMOR_INFINITE)"""
    import copy
    sa_base = boss_of(battle('티리아', 3, 1)).sa_max   # level 1 기준선(armor 없음)
    # 데이터 캐시를 임시 교체: armor 효과를 넣어 on_wave 가 실제로 처리하게 한다
    orig = C._DATA[C.data_path()]
    G_copy = copy.deepcopy(orig)
    fake_eid = 99999
    G_copy['effects'].append(dict(id=fake_eid, kind='armor', params=dict(add=5), name='armor_test', key='T', num=4, desc='', target=None))
    tyr = next(b for b in G_copy['bosses'] if b['key'] == 'tyria')
    tyr['levels'][0]['effects'].append(fake_eid)
    C._DATA[C.data_path()] = G_copy
    try:
        b = battle('티리아', 3, 1)
        boss = boss_of(b)
        assert boss.sa_max == sa_base + 5, 'sa_max=%d expected=%d' % (boss.sa_max, sa_base + 5)
        assert boss.sa == boss.sa_max
    finally:
        C._DATA[C.data_path()] = orig


def test_ex_hit_gauge():
    """SET 07 hit_gauge: 보스를 대상으로 한 아군 공격 스킬 1번당 행동 게이지 +5% (SE 9400701 NSEAT_DAMAGE_END — NKM:15742 -> 21183:
    공격 처리 끝에 시전자의 대상 목록 각자에게 1회. 타격·대상 수만큼이 아님)"""
    b = battle('벨그라스', 3, 0)          # 보스 + 부속 2 = 광역 한 번에 3명 타격
    boss = boss_of(b)
    b.gb.fx['hit_gauge'] = {'pct': 5}
    boss.gauge = 0.0
    hit(b, boss, all_=True)
    assert b.gb.stats['hit_gauge'] == 1, b.gb.stats['hit_gauge']
    assert 499 <= boss.gauge <= 501, boss.gauge
    hit(b, boss)                           # 단일 공격 1번 더 -> 누적 2회
    assert b.gb.stats['hit_gauge'] == 2
    b2 = battle('벨그라스', 3, 0)          # 대조군: 효과 없음
    boss2 = boss_of(b2)
    boss2.gauge = 0.0
    hit(b2, boss2, all_=True)
    assert b2.gb.stats.get('hit_gauge', 0) == 0 and boss2.gauge < 100


def test_ex_debuff_amp():
    """SET 21 debuff_amp: 자신 약화 개수당 주는 피해 +10% 최대 10 (SE 9402101, NegativeBuffCount CountMax 10)"""
    b = battle('티리아', 3, 0)
    boss = boss_of(b)
    b.gb.fx['debuff_amp'] = {'pct': 10, 'max': 10}
    # 보스에 약화 3개 부여
    for i in range(3):
        boss.eff['약화%d' % i] = Eff('약화%d' % i, {'공격력%': -1}, 1, 3, boss, True)
        boss.eff['약화%d' % i].stacks = 1
        boss.eff['약화%d' % i].category = 'debuff'
    assert boss.n_harmful() == 3
    sk = boss.d.skills['기본기']
    ctx_before = [None]
    orig = b.gb.before_cast

    def spy(u, sk2, ctx):
        orig(u, sk2, ctx)
        ctx_before[0] = ctx.inc
    b.gb.before_cast = spy
    b.cast(boss, sk)
    assert abs(ctx_before[0] - 0.30) < 1e-9, ctx_before[0]   # 3 x 10% = 30%
    assert b.gb.stats['debuff_amp'] == 3
    # 상한 10
    for i in range(3, 15):
        boss.eff['약화%d' % i] = Eff('약화%d' % i, {'공격력%': -1}, 1, 3, boss, True)
        boss.eff['약화%d' % i].stacks = 1
        boss.eff['약화%d' % i].category = 'debuff'
    b.cast(boss, sk)
    assert b.gb.stats['debuff_amp'] == 3 + 10   # 두 번째 시전에서 max 10


def test_ex_ult_cd():
    """SET 22 ult_cd: 타격 후 대상의 궁극기 쿨 +1 (SE 9402201, SkillCoolturnUpValue 1, AutoTargetId 21)"""
    b = battle('티리아', 3, 0)
    boss = boss_of(b)
    b.gb.fx['ult_cd'] = {'turns': 1}
    ally = b.allies[0]
    cd0 = ally.cd.get('궁극기', 0)
    sk = boss.d.skills['기본기']
    b.cast(boss, sk)
    # 적어도 맞은 아군의 궁극기 쿨이 1 증가해야 함
    assert b.gb.stats['ult_cd'] >= 1
    hit_allies = [u for u in b.allies if not u.dead and u.cd.get('궁극기', 0) > cd0]
    assert len(hit_allies) >= 1, [u.cd.get('궁극기') for u in b.allies]
    # 대조군
    b2 = battle('티리아', 3, 0)
    boss2 = boss_of(b2)
    ally2 = b2.allies[0]
    cd_before = ally2.cd.get('궁극기', 0)
    b2.cast(boss2, boss2.d.skills['기본기'])
    assert b2.gb.stats.get('ult_cd', 0) == 0


    # 면역 대상은 거부(비강제 효과 — NKM:4394, codex 2차 리뷰). 저항 판정은 없음(EffectHitCheck=false)
    b3 = battle('티리아', 3, 0)
    boss3 = boss_of(b3)
    b3.gb.fx['ult_cd'] = {'turns': 1}
    before = {id(u): u.cd.get('궁극기', 0) for u in b3.allies}
    for u in b3.allies:
        b3.put_eff(u, '면역', {}, dur=5, maxs=1, add=1, src=u, cat='buff', fixed=False)
    b3.cast(boss3, boss3.d.skills['기본기'])
    assert b3.gb.stats.get('ult_cd', 0) == 0
    assert all(u.cd.get('궁극기', 0) <= before[id(u)] for u in b3.allies)

def test_ex_no_shield_amp():
    """SET 24 no_shield_amp: 보스 공격 시 대상 중 하나라도 보호막 계열(조건 31010 NotTargetBuffStrId)이 없으면 이번 스킬 피해 +20
    (OnMyAttack NKM:9590-9606 -> NKM.Templets 42715: 광역도 대상 전원으로 판정). 보호막 판정은 수치가 아니라 버프 이름"""
    names = ['보호막', '보호막(해제불가)', '공허 방패(해제불가)', '저항 장막(해제불가)', '파프닐의 강림(해제불가)']
    def run(shield_all, name='보호막', slot='기본기'):
        b = battle('티리아', 3, 0)
        boss = boss_of(b)
        b.gb.fx['no_shield_amp'] = {'pct': 20, 'names': names}
        if shield_all:
            for u in b.allies:
                e = b.put_eff(u, name, {}, dur=5, maxs=1, add=1, src=u, cat='buff', fixed=False)
                e.shield = 999999
        b.cast(boss, boss.d.skills[slot])
        return b.gb.stats.get('no_shield_amp', 0)
    assert run(False) == 1
    assert run(True) == 0                                   # 전원 보호막 -> 미발동
    assert run(True, '공허 방패(해제불가)') == 0              # 목록의 다른 이름도 보호막 계열
    assert run(True, '보호막 아님') == 1                     # 이름이 목록에 없으면 수치가 있어도 보호막 아님
    assert run(False, slot='궁극기') == 1                   # 광역(티리아 궁극기)도 판정함


def test_ex_no_shield_chain():
    """SET 25 no_shield_chain: 기본기 후 피해 기록 중 하나라도 처치 안 됨 + 보호막 계열 없음이면 적 전체에 공격력 30 연쇄 1회씩
    (AfterMyAttack NKM:8037 -> 15963, 조건 32167 기본기·NotTargetBuffStrId·NotEliminateEnemy)"""
    names = ['보호막', '보호막(해제불가)', '공허 방패(해제불가)', '저항 장막(해제불가)', '파프닐의 강림(해제불가)']
    def run(shield_all, name='보호막', slot='기본기'):
        b = battle('티리아', 3, 0)
        boss = boss_of(b)
        b.gb.fx['no_shield_chain'] = {'atkRate': 30.0, 'names': names}
        kinds = []
        orig = b.apply_damage
        b.apply_damage = lambda a, v, dmg, kind, shieldable=True, **kw: (kinds.append(kind), orig(a, v, dmg, kind, shieldable, **kw))[1]
        if shield_all:
            for u in b.allies:
                e = b.put_eff(u, name, {}, dur=5, maxs=1, add=1, src=u, cat='buff', fixed=False)
                e.shield = 999999
        b.cast(boss, boss.d.skills[slot])
        return b, b.gb.stats.get('no_shield_chain', 0), kinds.count('chain')
    b, n, chains = run(False)
    assert n == 1 and chains == len(b.alive(0)), (n, chains)
    assert run(True)[1] == 0
    assert run(True, '보호막 아님')[1] == 1
    assert run(False, slot='궁극기')[1] == 0                # 기본기 조건


    # 24(이번 스킬 피해 +20)가 함께 걸리면 25의 연쇄도 그 증가를 읽음(NKM:4734·6226, codex 2차 리뷰)
    def chain_total(with_amp):
        b = battle('티리아', 3, 0, seed=7)
        boss = boss_of(b)
        b.gb.fx['no_shield_chain'] = {'atkRate': 30.0, 'names': names}
        if with_amp:
            b.gb.fx['no_shield_amp'] = {'pct': 20, 'names': names}
        got = []
        orig = b.apply_damage
        b.apply_damage = lambda a, v, dmg, kind, shieldable=True, **kw: (got.append(dmg) if kind == 'chain' else None, orig(a, v, dmg, kind, shieldable, **kw))[1]
        b.cast(boss, boss.d.skills['기본기'])
        return sum(got)
    assert chain_total(True) > chain_total(False) * 1.15

def test_ex_strip():
    """SET 28 strip: 타격 후 적 강화 1개 해제 저항 무시 (SE 9402801, cond 2107, BI_DELETEBUFF_NONEFFECTHIT)"""
    b = battle('티리아', 3, 0)
    boss = boss_of(b)
    b.gb.fx['strip'] = {'count': 1}
    # 모든 아군에게 강화 2개씩 부여 (보스가 누구를 때릴지 모름)
    for u in b.allies:
        b.put_eff(u, '공격력 증가', {'공격력%': 50}, dur=5, maxs=1, add=1, src=u, cat='buff', fixed=False)
        b.put_eff(u, '방어력 증가', {'방어력%': 50}, dur=5, maxs=1, add=1, src=u, cat='buff', fixed=False)
    sk = boss.d.skills['기본기']
    b.cast(boss, sk)
    # 적어도 맞은 아군 하나의 강화가 1개 해제되어야 함
    assert b.gb.stats['strip'] >= 1
    stripped = [u for u in b.allies if not (u.on('공격력 증가') and u.on('방어력 증가'))]
    assert len(stripped) >= 1, '맞은 아군의 강화가 해제되지 않음'
    for u in stripped:
        assert sum(1 for n in ('공격력 증가', '방어력 증가') if u.on(n)) == 1, '1개만 해제해야 함'
    # 대조군: strip 없으면 해제 없음
    b2 = battle('티리아', 3, 0)
    boss2 = boss_of(b2)
    for u in b2.allies:
        b2.put_eff(u, '공격력 증가', {'공격력%': 50}, dur=5, maxs=1, add=1, src=u, cat='buff', fixed=False)
    b2.cast(boss2, boss2.d.skills['기본기'])
    assert all(u.on('공격력 증가') for u in b2.allies) and b2.gb.stats.get('strip', 0) == 0


def test_data_matches_tables():
    tables = os.environ.get('COSMO_TABLES')
    if not tables or not os.path.isdir(tables):
        from tools.runtime import skip_note
        skip_note('cosmo_raid_test.test_data_matches_tables: COSMO_TABLES 없음')
        return
    out = os.path.join(tempfile.mkdtemp(), 'c.json')
    p = subprocess.run([sys.executable, '-X', 'utf8', '-I', os.path.join(ROOT, 'tools', 'build_cosmo_raid.py'), '--tables', tables, '--season', '1022',
                        '--build', str(G['gameBuild']), '--out', out], capture_output=True, text=True, encoding='utf-8')
    assert p.returncode == 0, p.stdout + p.stderr
    new = json.load(open(out, encoding='utf-8'))
    cur = json.loads(json.dumps(G))
    for d in (new, cur):  # 표에 없는 값: 공지 날짜·출처, 빌더 계산 가능 표시, 탐색 설정
        for k in ('start', 'end', 'settleEnd', 'src'):
            d['season'].pop(k, None)
        for b in d['bosses']:
            b.pop('sim', None)
            b.pop('simNote', None)
        d.pop('search', None)
    assert new == cur, '표에서 다시 뽑은 값이 data/cosmo_raid.json 과 다름'


TESTS = [test_data_shape, test_stage_stats_match_existing_cosmo, test_build_waves_and_scale, test_switch_off_no_controller, test_season_buffs,
         test_challenge_effects_attached, test_drain_rewind_backflow_direct, test_pressure_march_bleed_thorn_punish_direct, test_punish_client_timing,
         test_belgras_erosion_and_rot, test_belgras_thorn_gauge_growth, test_minions, test_simulate_clear_step1_step2,
         test_simulate_belgras_path_taken, test_simulate_challenge_paths_and_level_scale, test_existing_results_unchanged_fields,
         test_score_values_and_bounds, test_data_driven_defaults, test_js_parity,
         test_ex_grow, test_ex_armor, test_ex_hit_gauge, test_ex_debuff_amp, test_ex_ult_cd,
         test_ex_no_shield_amp, test_ex_no_shield_chain, test_ex_strip,
         test_data_matches_tables]

if __name__ == '__main__':
    bad = 0
    for t in TESTS:
        try:
            t()
            print('OK  ', t.__name__)
        except Exception as ex:   # noqa: BLE001
            import traceback
            bad += 1
            print('FAIL', t.__name__, type(ex).__name__, ex)
            traceback.print_exc(limit=3)
    print('ALL OK %d' % len(TESTS) if not bad else '%d FAIL' % bad)
    sys.exit(1 if bad else 0)
