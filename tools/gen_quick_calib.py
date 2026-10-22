# -*- coding: utf-8 -*-
"""빠른 계산 계수용 정답지 만들기: 표본 (스테이지, 팀)(tools/calib_teams.json)을 «여러 육성 가정»으로 확률 엔진에 돌린다.

화면 브라우저 시뮬과 같은 조건: Lv200·표준 육성(build=standard) 위에 공·생·방 × k(가정 전투력 = 권장 × g), 역보정은 엔진이
스탯으로 전투력을 계산해 적용(power_penalty=model), 시뮬 칸 = 화면 카드 순서를 [전열1, 전열2, 후열1, 후열2]로 바꾼 것.
결과 = tools/raw/quick_calib.json(저장소 제외). 작업자 2개·낮은 우선순위. 다음 = tools/calibrate_quick.py --write

사용: python -X utf8 -I tools/gen_quick_calib.py [--runs 40] [--per-content 400]
"""
import json
import math
import os
import random
import sys
from multiprocessing import Pool
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(ROOT))
from battlesim.fileio import atomic_open, read_json
from tools.runtime import low_priority as low
sys.path.insert(0, os.path.join(ROOT, 'tools'))

GROWTHS = [0.6, 0.75, 0.9, 1.0, 1.15, 1.3, 1.6, 2.0]
SIMOPT = {'build': 'standard', 'rules_override': {'power_penalty': 'model'}}    # 화면 SIMOPT 와 같게
TEAMS = os.path.join(ROOT, 'tools', 'calib_teams.json')
OUT = os.path.join(ROOT, 'tools', 'raw', 'quick_calib.json')


def sim_order(order):
    """화면 카드 순서 [후열1, 전열1, 전열2, 후열2] -> 시뮬 칸 [전열1, 전열2, 후열1, 후열2](화면 simParty와 같은 규칙)"""
    return [order[1], order[2], order[0], order[3]]


def party_spec(q, order, lead, keys, g, st):
    """화면 simParty 와 같은 변환(sim_worker 로 보내는 값). order = 화면 카드 순서"""
    from battlesim import quick
    sv = q['sv']
    rs = 0.0
    for k in keys:
        rs += sv[k][5]
    P = st['bp'] * g if st.get('bp') else rs * quick.MUL
    units = []
    so = sim_order(order)
    for k in so:
        u = sv[k]
        kk = (P * u[5] / rs) / (u[5] * quick.MUL)
        R = lambda x: math.floor(x + 0.5)      # 화면 simParty 와 같은 반올림(파이썬 round 는 .5 를 짝수로 보냄)
        units.append(dict(key=k, stats_override=dict(atk=R(u[1] * kk), hp=R(u[2] * kk), **{'def': R(u[3] * kk)})))
    return dict(units=units, leader=so.index(lead) if lead in so else None)


@lru_cache(maxsize=1)
def quick_data(root):
    from battlesim import quick
    return quick.load(root)


def job(a):
    ck, sk, team_key, order, lead, g, runs = a
    from battlesim import simulate
    q, _ = quick_data(ROOT)
    st = q['st'][ck][sk]
    spec = party_spec(q, order, lead, team_key.split(','), g, st)
    tab, name = sk.split('|', 1)
    try:
        r = simulate(spec, {'stage': '%s/%s/%s' % (ck, tab, name)}, dict(SIMOPT, n_runs=runs, seed=7))
        return [ck, sk, team_key, g, r['outcome']['clear_p']]
    except Exception as ex:
        return [ck, sk, team_key, g, None, str(ex)[:120]]


def teams():
    """표본 팀 목록 [(콘텐츠, 탭|스테이지, 팀 key, 화면 카드 순서, 리더)] = tools/calib_teams.json
    (옛 사전 계산의 스테이지별 근사 상위 후보에서 뽑아 둔 것 — 실제로 추천될 만한 조합, 2026-10-20)"""
    return [tuple(x) for x in read_json(TEAMS)['teams']]


def save_samples(out, runs):
    if not out or any(r[4] is None for r in out):
        raise ValueError('보정 표본 없음 또는 시뮬 실패: 기존 표본을 보존했음')
    rows = sorted(out, key=lambda r: (r[0], r[1], r[2], r[3]))
    with atomic_open(OUT) as f:
        json.dump(dict(growths=GROWTHS, runs=runs, rows=rows), f, ensure_ascii=False)


def main():
    runs = int(sys.argv[sys.argv.index('--runs') + 1]) if '--runs' in sys.argv else 40
    per = int(sys.argv[sys.argv.index('--per-content') + 1]) if '--per-content' in sys.argv else 260
    low()
    from battlesim import quick
    q, _ = quick.load(ROOT)
    rnd = random.Random(20261020)
    jobs = []
    by = {}
    for ck, sk, tk, o, L in teams():
        if sk in q['st'].get(ck, {}) and all(k in q['sv'] for k in tk.split(',')):
            by.setdefault(ck, []).append((sk, tk, o, L))
    for ck in sorted(by):
        items = by[ck]
        rnd.shuffle(items)
        for sk, tk, o, L in items[:per]:
            jobs.append((ck, sk, tk, o, L, rnd.choice(GROWTHS), runs))
    print('작업', len(jobs), '건, 판 수', runs, flush=True)
    out = []
    with Pool(2, initializer=low) as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs, chunksize=4)):
            out.append(r)
            if (i + 1) % 200 == 0:
                print(i + 1, flush=True)
    save_samples(out, runs)
    print('저장', OUT, len(out), '건')


if __name__ == '__main__':
    main()
