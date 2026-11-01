"""알리시아의 지원(길드 방어전) 5종이 전투에서 실제로 걸리는지 센다. 명세: AI/temp/partynavigator/work/guild_defense/support_spec.md
실행: python -X utf8 -I tests/guild_support_test.py
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from battlesim.api import simulate
from battlesim.starsavior import guild_bfb as gb

TEAM = ['wedding-carmen', 'ceres-sun-supporter', 'amora', 'tyria']


def run(support, runs=6, level=1):
    """simulate 를 돌리며 지원 효과 호출을 센다"""
    seen = Counter()
    orig_put, orig_tmp = gb.Controller._sup_put, gb.Controller._sup_put_tmp
    orig_gauge = None

    def put(self, x, name, props, maxs=1):
        seen[(name, x.role)] += 1
        return orig_put(self, x, name, props, maxs)

    gb.Controller._sup_put = put
    try:
        r = simulate({'units': TEAM, 'leader': 0}, {'guild': {'level': level, 'support': support}},
                     {'n_runs': runs, 'build': 'standard', 'seed': 3})
    finally:
        gb.Controller._sup_put = orig_put
    return seen, r


def test_none_changes_nothing():
    seen, _ = run('none')
    assert not seen, seen
    print('OK test_none_changes_nothing')


def test_role_filter():
    # 직업 전용 지원은 해당 직업에만 시작 효과가 걸린다
    seen, _ = run('gust')
    roles = {role for (name, role) in seen if name == gb.SUP_STAT}
    assert roles == {'서포터'}, roles
    seen, _ = run('focus')
    assert {role for (n, role) in seen if n == gb.SUP_STAT} <= {'캐스터'}
    seen, _ = run('strike')
    assert {role for (n, role) in seen if n == gb.SUP_STAT} <= {'스트라이커'}
    print('OK test_role_filter')


def test_party_wide_start():
    seen, _ = run('fire', runs=3)
    n = sum(c for (name, _r), c in seen.items() if name == gb.SUP_STAT)
    assert n >= 4 * 3 / 2, n          # 파티 4명 x 판 수(웨이브 2에서 중복 적용 안 됨: sup_done)
    assert any(name == gb.SUP_HIT for (name, _r) in seen), '불의 고동 적중 중첩이 쌓이지 않음'
    print('OK test_party_wide_start')


def test_gust_gauge():
    calls = []
    from battlesim import mc
    orig = mc.Battle.set_gauge

    def spy(self, u, value):
        if self.gb is not None and self.gb.support == 'gust':
            calls.append((u.name, value - u.gauge))
        return orig(self, u, value)

    mc.Battle.set_gauge = spy
    try:
        run('gust', runs=3)
    finally:
        mc.Battle.set_gauge = orig
    assert any(abs(d - 3000) < 1e-6 for _n, d in calls), '격돌의 돌풍 +30% 가 한 번도 안 걸림'
    print('OK test_gust_gauge')


def test_temp_damage_effects():
    seen, _ = run('mountain', runs=3)
    assert any(n == gb.SUP_TMP_INC for (n, _r) in seen), '태산의 의지 피해 +10% 가 안 걸림'
    seen, _ = run('strike', runs=3)
    print('   strike 임시 피해 증가 횟수:', sum(c for (n, _r), c in seen.items() if n == gb.SUP_TMP_INC))
    print('OK test_temp_damage_effects')


def test_invalid_support():
    try:
        gb.build_waves(1, None, support='wrong')
    except ValueError:
        print('OK test_invalid_support')
        return
    raise AssertionError('잘못된 지원 이름이 통과함')


def test_web_run_auto_guild():
    """화면(sim_worker → web.run_auto)이 options.guild 를 넘기면 길방 BFB 전투로 돈다(스테이지 문자열은 무시). guild 가 없으면 기존 스테이지."""
    import json
    from battlesim import web
    party = {'units': TEAM, 'leader': 0}
    extra = json.dumps({'build': 'standard', 'guild': {'level': 1, 'sets': [0, 0, 0, 0], 'support': 'fire'}})
    r1 = json.loads(web.run_auto('길드방어전/x/7', party, 4, 3, extra))
    r2 = json.loads(web.run_auto('길드방어전/x/7', party, 4, 3, extra))
    assert r1['n'] == 4 and r1 == r2, '같은 시드 → 같은 결과'
    r0 = json.loads(web.run_auto('op/NOA 상업지구/SECTOR 1-3', party, 4, 3, json.dumps({'build': 'standard'})))
    assert r0['n'] == 4 and r0 != r1
    print('OK test_web_run_auto_guild')


if __name__ == '__main__':
    for t in (test_none_changes_nothing, test_role_filter, test_party_wide_start, test_gust_gauge, test_temp_damage_effects, test_invalid_support, test_web_run_auto_guild):
        t()
    print('ALL OK 7')
