# -*- coding: utf-8 -*-
"""코스모 게이트 시즌 1023(프리즘 시즌 8, 11/19 클라 빌드 26752678) 실자료 시험.

- 자료: data/cosmo_raid.json = 시즌 1023(모굴루스·바스커빌의 괴수·괴리의 표상). 지난 시즌(1022) 모델 회귀는 tests/fixtures/cosmo_raid_1022.json.
- 바스커빌의 괴수는 PC 클라 조각으로 세 단계 모두 계산한다.
- EX SET_33 «폭주 : 장벽»(SE 9403301): 피해 처리 직전(NSEAT_DAMAGE_START, NKM:15689) 조건 5509 MyEffectiveDamageStart
  (NKM:10171 — 공격자 강화 효과 수 <= 1, 0개도 참: NKM.Templets:43320 OBF_7056, 공격 스킬만)면 보스 받는 피해 -30%.
"""
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim import simulate                                   # noqa: E402
from battlesim.api import _norm_party                            # noqa: E402
from battlesim.mc import Battle                                  # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior import cosmo_raid as C                 # noqa: E402
from battlesim.starsavior.data import get_db                     # noqa: E402

PARTY = ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria']
DB = get_db()
G = C.load()


def battle(boss, step=3, level=0, seed=1):
    waves, meta = C.build_waves(boss, step, level)
    defs, _ = _norm_party({'units': PARTY}, DB, 'fixed', 'standard')
    b = Battle(defs, waves, random.Random(seed), mc=dict(MC_OPTS, cosmo_raid_boss='on'), leader=0,
               turn_limit=meta['turn_limit'], battle_mode='boss_kill')
    b.spawn_wave()
    return b


def test_season_1023_shape():
    s = G['season']
    assert s['id'] == 1023 and s['bossOrder'] == ['mogulus', 'baskerville', 'disparity']
    assert (s['start'], s['end'], s['settleEnd']) == ('2026-11-19T12:00:00+09:00', '2026-11-26T04:00:00+09:00', '2026-12-03T04:00:00+09:00')
    by = {b['key']: b for b in G['bosses']}
    assert [by[k]['difficultyGroupId'] for k in s['bossOrder']] == [1011, 1002, 1009]
    assert {k: by[k]['sim'] for k in by} == {'mogulus': True, 'baskerville': True, 'disparity': True}
    # 공지 이미지의 시즌 버프·별의 도전 EX 18단계 구성과 같음(HISTORY 11/18 대조)
    assert {k: sorted(x['id'] for x in by[k]['seasonBuffs']) for k in by} == {
        'mogulus': [8060, 8066], 'baskerville': [8058, 8063], 'disparity': [8057, 8062]}
    eff = {e['id']: e for e in G['effects']}
    sets = {k: [eff[i]['num'] for i in by[k]['levels'][17]['effects']] for k in by}
    assert sets == {'mogulus': [2, 24, 3, 4, 25, 28], 'baskerville': [1, 3, 4, 11, 10, 33], 'disparity': [2, 21, 3, 4, 22, 7]}, sets
    assert all(e['kind'] for e in G['effects']), [e for e in G['effects'] if not e['kind']]
    assert eff[940321]['kind'] == 'few_buff_guard' and eff[940321]['params'] == {'pct': 30, 'maxBuffs': 1}
    assert G.get('belgras') is None


def test_baskerville_calculated():
    for step, level in ((1, 0), (3, 0), (3, 18)):
        waves, meta = C.build_waves('baskerville', step, level)
        assert waves[0][0].client_model == 'baskerville'
        r = simulate({'units': PARTY}, {'cosmo_raid': {'boss': '바스커빌의 괴수', 'step': step, 'level': level}},
                     {'seed': 1, 'n_runs': 1, 'build': 'standard'})
        assert r['outcome']['progress'] > 0, (step, level, r['outcome'])
        assert not any('바스커빌' in str(x) for x in (r.get('unsupported') or {}).get('lines', []))


def test_mogulus_disparity_simulate():
    for boss in ('mogulus', '괴리의 표상'):
        for step, level in ((1, 0), (3, 18)):
            r = simulate({'units': PARTY}, {'cosmo_raid': {'boss': boss, 'step': step, 'level': level}},
                         {'seed': 3, 'n_runs': 2, 'build': 'standard'})
            assert r['encounter']['cosmo_raid']['season'] == 1023 and r['encounter']['turn_limit'] == 50
            assert r['outcome']['progress'] > 0, (boss, step, r['outcome'])
            un = r.get('unsupported') or {}
            assert not any('미지원 챌린지 효과' in k for k in (un.get('runtime') or {})), un


def test_api_default_boss_is_season_first():
    r = simulate({'units': PARTY}, {'cosmo_raid': {'step': 1}}, {'seed': 1, 'n_runs': 1, 'build': 'standard'})
    assert r['encounter']['cosmo_raid']['boss'] == G['season']['bossOrder'][0] == 'mogulus'


def _guard_case(n_buffs, attack=True, with_fx=True):
    b = battle('mogulus', 3, 0, seed=7)
    boss = b.gb.boss
    if with_fx:
        b.gb.fx['few_buff_guard'] = {'pct': 30, 'maxBuffs': 1}
    a = b.allies[0]
    for x in list(a.eff):
        if a.eff[x].category == 'buff':
            del a.eff[x]
    for i in range(n_buffs):
        b.put_eff(a, '시험 강화 %d' % i, {}, dur=5, maxs=1, add=1, src=a, cat='buff', fixed=False)
    assert a.n_good() == n_buffs
    hp0 = boss.hp
    sk = C._skill('기본기', 'test', 100, 0, 0, attack=attack, tg='적 단일')
    b.cast(a, sk, target=boss)
    assert boss.eff.get(C.CH_GUARD) is None, '지속 0턴: 시전이 끝나면 지움'
    return b.gb.stats.get('few_buff_guard', 0), hp0 - boss.hp


def test_ex_few_buff_guard():
    n0, d_off = _guard_case(0, with_fx=False)
    assert n0 == 0 and d_off > 0
    n, d0 = _guard_case(0)
    assert n == 1 and d0 < d_off                     # 강화 0개도 참(BuffCountLess 판정)
    n, d1 = _guard_case(1)
    assert n == 1 and d1 == d0                       # 1개 = 경계, 같은 감소
    n, d2 = _guard_case(2)
    assert n == 0 and d2 == d_off                    # 2개 이상이면 미발동
    # 공격 스킬(SAT_ATTACK)만: 비공격 행동 중 보스 피해(효과 줄 피해 등)는 판정하지 않음 — 행동 맥락을 직접 만들어 pre_hit 호출
    from types import SimpleNamespace
    for attack, want in ((False, 0), (True, 1)):
        b = battle('mogulus', 3, 0, seed=7)
        b.gb.fx['few_buff_guard'] = {'pct': 30, 'maxBuffs': 1}
        a = b.allies[0]
        sk = C._skill('특수기', 'test', 0, 0, 0, attack=attack, tg='적 단일')
        b._cast_ctx = SimpleNamespace(src=a, skill=sk, targets=[b.gb.boss])
        b.gb.pre_hit(a, b.gb.boss)
        assert b.gb.stats.get('few_buff_guard', 0) == want and (b.gb.boss.eff.get(C.CH_GUARD) is not None) == bool(want), attack
    assert abs(d0 / d_off - 0.7) < 0.02, (d0, d_off)  # 받는 피해 -30%


TESTS = [test_season_1023_shape, test_baskerville_calculated, test_mogulus_disparity_simulate, test_api_default_boss_is_season_first,
         test_ex_few_buff_guard]

if __name__ == '__main__':
    bad = 0
    for t in TESTS:
        try:
            t()
            print('ok', t.__name__)
        except Exception as e:      # noqa: BLE001
            bad += 1
            print('FAIL', t.__name__, type(e).__name__, e)
    sys.exit(1 if bad else 0)
