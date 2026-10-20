# -*- coding: utf-8 -*-
"""빠른 계산 계수(A 아군 피해·B 적 피해·H 회복)를 확률 엔진 결과에 맞춘다.

정답지 두 가지(둘 다 시뮬 오토 클리어 확률 c ≥ 0.5 를 「클리어」로 봄):
 ① data/sim/*.json — P4 사전 계산(Lv200·장비 없음, 육성 배수 k=1, 역보정 없음)
 ② tools/raw/quick_calib.json — tools/gen_quick_calib.py 가 육성 가정 0.7~1.5배로 다시 돌린 표본(화면 시뮬과 같은 스탯 변환)
②가 없으면 ①만 쓴다. 보스 콘텐츠(코스모 게이트 cosmo, 플래시 포인트 rush)는 성격이 달라 계수를 따로 맞춘다(pc).
점수 = 균형 정확도(클리어·실패 각각 맞힌 비율의 평균). --write 면 data/quick.json 의 params(기본)·pc(콘텐츠별)·calib 에 쓴다.

사용: python -X utf8 -I tools/calibrate_quick.py [--write]
"""
import glob
import itertools
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from battlesim import quick   # noqa: E402

GROUPS = {'cosmo': 'cosmo', 'rush': 'rush'}          # 나머지는 'base'
GRID_A = [0.25, 0.4, 0.6, 0.8, 1.0, 1.3, 1.7, 2.2, 3.0]
GRID_B = [0.15, 0.25, 0.4, 0.6, 0.8, 1.0, 1.3, 1.7, 2.2, 3.0]
GRID_H = [0.0, 0.03, 0.06, 0.1, 0.15, 0.2, 0.3]
CALIB = os.path.join(ROOT, 'tools', 'raw', 'quick_calib.json')


def group(ck):
    return GROUPS.get(ck, 'base')


def dataset(q):
    """-> [(콘텐츠, 스테이지, keys, stage, c, evaluate 인자)]"""
    rows = []
    for fp in sorted(glob.glob(os.path.join(ROOT, 'data', 'sim', '*.json'))):
        if fp.endswith('index.json'):
            continue
        d = json.load(open(fp, encoding='utf-8'))
        ck = d['content']
        for sk, sd in d['stages'].items():
            st = q['st'].get(ck, {}).get(sk)
            if not st:
                continue
            for tk, t in sd['teams'].items():
                a = t.get('auto') or {}
                keys = tk.split(',')
                if a.get('c') is None or any(k not in q['sv'] for k in keys):
                    continue
                ref = quick._add(q['sv'][k][5] for k in keys) * quick.MUL
                rows.append((ck, sk, keys, st, a['c'], dict(power=ref, use_pen=False)))
    if os.path.exists(CALIB):
        for r in json.load(open(CALIB, encoding='utf-8'))['rows']:
            ck, sk, tk, g, c = r[:5]
            st = q['st'].get(ck, {}).get(sk)
            if c is None or not st:
                continue
            rows.append((ck, sk, tk.split(','), st, c, dict(growth=g)))
    return rows


def score(rows, q, pen, prm):
    tp = tn = P = N = 0
    for ck, sk, keys, st, c, kw in rows:
        r = quick.evaluate(keys, st, q['sv'], pen, prm, **kw)
        if c >= 0.5:
            P += 1
            tp += r['clear']
        else:
            N += 1
            tn += not r['clear']
    sens = tp / P if P else 1.0
    spec = tn / N if N else 1.0
    return (sens + spec) / 2, sens, spec, P, N, (tp + tn) / max(1, P + N)


def fit(rows, q, pen):
    best = None
    for a, b, h in itertools.product(GRID_A, GRID_B, GRID_H):
        prm = dict(A=a, B=b, H=h)
        s = score(rows, q, pen, prm)
        if best is None or s[0] > best[0][0]:
            best = (s, prm)
    return best


def holdout(rows, q, pen):
    stages = sorted(set((r[0], r[1]) for r in rows))
    a_set = set(stages[0::2])
    fit_rows = [r for r in rows if (r[0], r[1]) in a_set]
    test = [r for r in rows if (r[0], r[1]) not in a_set]
    return score(test, q, pen, fit(fit_rows, q, pen)[1])[0]


def main():
    q, pen = quick.load(ROOT)
    rows = dataset(q)
    n2 = sum(1 for r in rows if 'growth' in r[5])
    print('대조 표본', len(rows), '(Lv200 표본', len(rows) - n2, '+ 육성 가정 표본', n2, ')')
    out, calib = {}, {}
    for gname in ('base', 'cosmo', 'rush'):
        gr = [r for r in rows if group(r[0]) == gname]
        (bacc, sens, spec, P, N, acc), prm = fit(gr, q, pen)
        hold = holdout(gr, q, pen)
        grw = [r for r in gr if 'growth' in r[5]]
        acc_g = score(grw, q, pen, prm)[5] if grw else None
        out[gname] = prm
        calib[gname] = dict(samples=len(gr), acc=round(acc, 3), bacc=round(bacc, 3), sens=round(sens, 3), spec=round(spec, 3),
                            hold_bacc=round(hold, 3), acc_growth=acc_g and round(acc_g, 3), pos=P, neg=N)
        print('[%s] %s 표본 %d 전체 일치 %.3f 균형 %.3f(반반 검증 %.3f) 클리어 맞힘 %.3f 실패 맞힘 %.3f 육성 가정 표본 일치 %s'
              % (gname, prm, len(gr), acc, bacc, hold, sens, spec, acc_g and '%.3f' % acc_g))
    tot = sum(c['samples'] for c in calib.values())
    acc_all = sum(c['acc'] * c['samples'] for c in calib.values()) / tot
    print('전체 일치(가중) %.3f' % acc_all)
    if '--write' in sys.argv:
        path = os.path.join(ROOT, 'data', 'quick.json')
        d = json.load(open(path, encoding='utf-8'))
        d['params'] = out['base']
        d['pc'] = {k: out[k] for k in GROUPS}
        d['calib'] = dict(samples=tot, acc=round(acc_all, 3), groups=calib,
                          against='확률 엔진 오토 클리어 확률 ≥ 0.5 — P4(Lv200·장비 없음) + 육성 가정 0.7~1.5배 표본')
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, path)
        print('저장', path)


if __name__ == '__main__':
    main()
