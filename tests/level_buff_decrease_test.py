# -*- coding: utf-8 -*-
"""level_buff_decrease: 세레스(샤프 앤 스위트) 〈손님 맞이 청소〉의 먼지 포착(해제불가) «5회 부여»는 표(LevelBuffDecrease=true)상 5 감소.
11/12 데이터북은 명시적 5중첩 감소로 바뀌었으므로 on/off 모두 감소함.
옛 «5회 부여»의 on/off 차이는 patch_1112_test가 별도 검사함.
실행: python -X utf8 -I tests/level_buff_decrease_test.py
근거: static-data SE_TEMPLET_SKILL_1.json:38328-38343, 영상 11/02 성간 회랑 450(추가 발동 전후 중첩 5건 중 4건 -5).
일부러 깨뜨리기: 명시적 중첩 감소 파싱을 끄면 patch_1112_test의 소비 검사가 실패함."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim import simulate                                   # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402

PARTY = ['emily', 'waltz-asherah', 'hilde', 'ceres-sun-supporter']
STAGE = {'stage': 'clo/태양 회랑/FLOOR 250'}
NAME = '먼지 포착(해제불가)'


def _run(mode):
    """5회 부여 호출마다 (전, 후) 먼지 포착 중첩을 모은다"""
    import battlesim.mc as mc
    seen = []
    orig = mc.Battle.apply_buff

    def spy(self, owner, eff, ctx, *a, **kw):
        hit = eff.get('name') == NAME and eff.get('times') == 5
        before = (owner.eff[NAME].stacks if NAME in owner.eff else 0) if hit else None
        out = orig(self, owner, eff, ctx, *a, **kw)
        if hit:
            seen.append((before, owner.eff[NAME].stacks if NAME in owner.eff else 0))
        return out
    mc.Battle.apply_buff = spy
    try:
        r = simulate(PARTY, STAGE, {'seed': 3, 'n_runs': 6, 'build': 'standard', 'rules_override': {'level_buff_decrease': mode}})
    finally:
        mc.Battle.apply_buff = orig
    return seen, r


def test_default_is_on():
    assert MC_OPTS['level_buff_decrease'] == 'on'


def test_on_decreases():
    seen, r = _run('on')
    assert len(seen) >= 3, seen                       # 5회 부여 줄이 실제로 여러 번 탔는지(안 타면 아무것도 검증 못 함)
    assert all(after == max(0, before - 5) for before, after in seen), seen[:8]
    assert any(before >= 5 for before, _ in seen), seen[:8]
    assert 0 < r['outcome']['progress'] <= 1, r['outcome']


def test_explicit_decrease_ignores_legacy_inference_switch():
    seen, _ = _run('off')
    assert len(seen) >= 3, seen
    assert all(after == max(0, before - 5) for before, after in seen), seen[:8]
    assert any(before >= 5 for before, _ in seen), seen[:8]


TESTS = [test_default_is_on, test_on_decreases, test_explicit_decrease_ignores_legacy_inference_switch]

if __name__ == '__main__':
    for t in TESTS:
        t()
        print('OK', t.__name__)
    print('ALL OK', len(TESTS))
