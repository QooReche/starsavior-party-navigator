# -*- coding: utf-8 -*-
"""빠른 계산 계수용 정답지 만들기: P4 사전 계산의 (스테이지, 팀) 표본을 «여러 육성 수준»으로 확률 엔진에 다시 돌린다.

P4 결과는 Lv200·장비 없음(육성 배수 k=1)뿐이라, 권장 전투력만큼 키웠다고 가정하면(k>1) 빠른 계산이 보스전에서 크게 낙관했다
(코스모 길레 3단계: 빠른 계산 「깰만함」 / 시뮬 0%). 그래서 육성 가정 g ∈ GROWTHS 마다 화면 시뮬(sim_worker)과 같은 방식으로
스탯을 바꿔(공·생·방 × k, 역보정은 공격력 × 아군 배율·생명력 ÷ 적 배율) 돌린다.
결과 = tools/raw/quick_calib.json(저장소 제외). 작업자 2개·낮은 우선순위.

사용: python -X utf8 -I tools/gen_quick_calib.py [--runs 40] [--per-content 260]
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

GROWTHS = [0.7, 0.85, 1.0, 1.2, 1.5]
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


def party_spec(q, pen, order, lead, keys, g, st):
    """화면 simParty 와 같은 변환(sim_worker 로 보내는 값)"""
    from battlesim import quick
    sv = q['sv']
    rs = 0.0
    for k in keys:
        rs += sv[k][5]
    P = st['bp'] * g if st.get('bp') else rs * quick.MUL
    pa, pe = quick.pen_mult(pen, P / st['bp']) if st.get('bp') else (1.0, 1.0)
    units = []
    for k in order:
        u = sv[k]
        kk = (P * u[5] / rs) / (u[5] * quick.MUL)
        R = lambda x: math.floor(x + 0.5)      # 화면 simParty 와 같은 반올림(파이썬 round 는 .5 를 짝수로 보냄)
        units.append(dict(key=k, stats_override=dict(atk=R(u[1] * kk * pa), hp=R(u[2] * kk / pe), **{'def': R(u[3] * kk)})))
    return dict(units=units, leader=order.index(lead) if lead in order else None)


def job(a):
    ck, sk, team_key, order, lead, g, runs = a
    from battlesim import quick, simulate
    q, pen = quick.load(ROOT)
    st = q['st'][ck][sk]
    spec = party_spec(q, pen, order, lead, team_key.split(','), g, st)
    tab, name = sk.split('|', 1)
    try:
        r = simulate(spec, {'stage': '%s/%s/%s' % (ck, tab, name)}, {'n_runs': runs, 'seed': 7})
        return [ck, sk, team_key, g, r['outcome']['clear_p']]
    except Exception as ex:
        return [ck, sk, team_key, g, None, str(ex)[:120]]


def main():
    runs = int(sys.argv[sys.argv.index('--runs') + 1]) if '--runs' in sys.argv else 40
    per = int(sys.argv[sys.argv.index('--per-content') + 1]) if '--per-content' in sys.argv else 260
    low()
    from battlesim import quick
    import glob
    q, _ = quick.load(ROOT)
    rnd = random.Random(20261020)
    jobs = []
    for fp in sorted(glob.glob(os.path.join(ROOT, 'data', 'sim', '*.json'))):
        if fp.endswith('index.json'):
            continue
        d = json.load(open(fp, encoding='utf-8'))
        ck = d['content']
        items = []
        for sk, sd in d['stages'].items():
            if sk not in q['st'].get(ck, {}):
                continue
            for tk, t in sd['teams'].items():
                if all(k in q['sv'] for k in tk.split(',')):
                    items.append((sk, tk, t['o'], t['L']))
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
