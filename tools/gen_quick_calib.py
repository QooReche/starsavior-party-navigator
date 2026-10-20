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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

GROWTHS = [0.6, 0.75, 0.9, 1.0, 1.15, 1.3, 1.6, 2.0]
SIMOPT = {'build': 'standard', 'rules_override': {'power_penalty': 'model'}}    # 화면 SIMOPT 와 같게
TEAMS = os.path.join(ROOT, 'tools', 'calib_teams.json')
OUT = os.path.join(ROOT, 'tools', 'raw', 'quick_calib.json')


def low():
    try:
        if os.name == 'nt':
            import ctypes
            k = ctypes.windll.kernel32
            k.SetPriorityClass(k.GetCurrentProcess(), 0x40)
        else:
            os.nice(19)
    except Exception:
        pass


def sim_order(order):
    """화면 카드 순서 [후열1, 전열1, 전열2, 후열2] -> 시뮬 칸 [전열1, 전열2, 후열1, 후열2](build_sim_results.arrange 와 같은 규칙)"""
    return [order[1], order[2], order[0], order[3]]


def party_spec(q, pen, order, lead, keys, g, st):
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


def job(a):
    ck, sk, team_key, order, lead, g, runs = a
    from battlesim import quick, simulate
    q, pen = quick.load(ROOT)
    st = q['st'][ck][sk]
    spec = party_spec(q, pen, order, lead, team_key.split(','), g, st)
    tab, name = sk.split('|', 1)
    try:
        r = simulate(spec, {'stage': '%s/%s/%s' % (ck, tab, name)}, dict(SIMOPT, n_runs=runs, seed=7))
        return [ck, sk, team_key, g, r['outcome']['clear_p']]
    except Exception as ex:
        return [ck, sk, team_key, g, None, str(ex)[:120]]


def teams():
    """표본 팀 목록 [(콘텐츠, 탭|스테이지, 팀 key, 화면 카드 순서, 리더)] = tools/calib_teams.json
    (옛 사전 계산의 스테이지별 근사 상위 후보에서 뽑아 둔 것 — 실제로 추천될 만한 조합, 2026-10-20)"""
    return [tuple(x) for x in json.load(open(TEAMS, encoding='utf-8'))['teams']]


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
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(dict(growths=GROWTHS, runs=runs, rows=out), f, ensure_ascii=False)
    os.replace(tmp, OUT)
    bad = [r for r in out if r[4] is None]
    print('저장', OUT, len(out), '건, 실패', len(bad), bad[:2])


if __name__ == '__main__':
    main()
