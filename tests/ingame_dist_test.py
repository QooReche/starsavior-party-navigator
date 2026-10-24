"""tools/ingame_check.distribution 시험: 결과 비율·행동 수 분위수·실측 TURN 위치·보스 남은 생명력·먼저 쓰러진 구원자.
실행: python -X utf8 -I tests/ingame_dist_test.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.argv = [sys.argv[0]]
import ingame_check as ic  # noqa: E402

B = [dict(result='clear', actions=30, boss_left=0.0, progress=1.0, first_down=None),
     dict(result='clear', actions=40, boss_left=0.0, progress=1.0, first_down='A'),
     dict(result='wipe', actions=50, boss_left=0.2, progress=0.8, first_down='A'),
     dict(result='timeout', actions=60, boss_left=0.4, progress=0.6, first_down='B')]
d = ic.distribution(B, 'clear', 35)
assert d['n'] == 4 and d['result'] == {'clear': 0.5, 'wipe': 0.25, 'timeout': 0.25}, d
assert d['same_result_runs'] == 2 and d['real_turn_pct'] == 0.5, d       # 클리어 판 30·40 중 35 이하 1개
assert d['boss_left_q10_50_90_when_lost'] == [0.2, 0.4, 0.4], d
assert d['first_down'] == {'A': 0.5, 'B': 0.25} and d['no_death_rate'] == 0.25, d
f = ic.distribution(B, 'fail', 55)
assert f['same_result_runs'] == 2 and f['real_turn_pct'] == 0.5, f       # 실패 판 50·60 중 55 이하 1개
assert ic.distribution([], 'clear', 10)['real_turn_pct'] is None
print('PASS ingame_check.distribution')
