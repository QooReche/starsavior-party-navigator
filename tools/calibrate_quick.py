# -*- coding: utf-8 -*-
"""빠른 계산 계수(A 아군 피해·B 적 피해·H 회복)를 확률 엔진 결과(data/sim/*.json, P4 사전 계산 — Lv200·장비 없음·역보정 없음)에 맞춘다.

정답 = 시뮬 오토 클리어 확률 c ≥ 0.5 를 「클리어」로 본다. 점수 = 균형 정확도(클리어·실패 각각 맞힌 비율의 평균).
같은 조건(k=1, 역보정 끔)으로 빠른 계산을 돌려 비교한다. 결과는 data/quick.json 의 params·calib 에 써 넣는다(--write).

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


def dataset(q):
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
                if a.get('c') is None:
                    continue
                keys = tk.split(',')
                if any(k not in q['sv'] for k in keys):
                    continue
                rows.append((ck, sk, keys, st, a['c']))
    return rows


def score(rows, q, pen, prm):
    tp = tn = P = N = 0
    for ck, sk, keys, st, c in rows:
        ref = sum(q['sv'][k][5] for k in keys) * quick.MUL
        r = quick.evaluate(keys, st, q['sv'], pen, prm, power=ref, use_pen=False)
        yes = c >= 0.5
        if yes:
            P += 1
            tp += r['clear']
        else:
            N += 1
            tn += not r['clear']
    sens = tp / P if P else 0
    spec = tn / N if N else 0
    return (sens + spec) / 2, sens, spec, P, N, (tp + tn) / max(1, P + N)


def holdout(rows, q, pen, ga, gb, gh):
    stages = sorted(set((r[0], r[1]) for r in rows))
    a_set = set(stages[0::2])
    fit = [r for r in rows if (r[0], r[1]) in a_set]
    test = [r for r in rows if (r[0], r[1]) not in a_set]
    best = None
    for a, b, h in itertools.product(ga, gb, gh):
        prm = dict(A=a, B=b, H=h)
        sc = score(fit, q, pen, prm)[0]
        if best is None or sc > best[0]:
            best = (sc, prm)
    return score(test, q, pen, best[1])[0]


def rank_key(r):
    return (1 if r['clear'] else 0, r['left'] if r['clear'] else -r['rounds'] * 0, -r['rounds'] if r['clear'] else r['rounds'])


def top_pick(rows, q, pen, prm):
    by = {}
    for ck, sk, keys, st, c in rows:
        ref = sum(q['sv'][k][5] for k in keys) * quick.MUL
        r = quick.evaluate(keys, st, q['sv'], pen, prm, power=ref, use_pen=False)
        by.setdefault((ck, sk), []).append((rank_key(r), c))
    good = n = 0
    for v in by.values():
        if len(v) < 2:
            continue
        n += 1
        best_c = max(c for _, c in v)
        pick_c = max(v, key=lambda x: x[0])[1]
        good += pick_c >= best_c - 0.1
    return (good / n if n else 0), n


def main():
    q, pen = quick.load(ROOT)
    rows = dataset(q)
    print('대조 표본', len(rows), '팀·스테이지')
    best = None
    grid_a = [0.25, 0.4, 0.6, 0.8, 1.0, 1.3, 1.7, 2.2, 3.0]
    grid_b = [0.15, 0.25, 0.4, 0.6, 0.8, 1.0, 1.3, 1.7]
    grid_h = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3]
    for a, b, h in itertools.product(grid_a, grid_b, grid_h):
        prm = dict(A=a, B=b, H=h)
        s = score(rows, q, pen, prm)
        if best is None or s[0] > best[0][0]:
            best = (s, prm)
    (bacc, sens, spec, P, N, acc), prm = best
    hold = holdout(rows, q, pen, grid_a, grid_b, grid_h)
    pick = top_pick(rows, q, pen, prm)
    print('반반 검증(앞 절반 스테이지로 맞추고 뒤 절반에서 잼) 균형 정확도 %.3f' % hold)
    print('1등 팀 고르기: 빠른 계산 1등의 시뮬 클리어 확률이 그 스테이지 최고값 -0.1 이내 %.3f (%d 스테이지)' % pick)
    print('전체 일치율 %.3f' % acc)
    print('최적', prm, '균형 정확도 %.3f (클리어 맞힘 %.3f / 실패 맞힘 %.3f, 클리어 %d·실패 %d)' % (bacc, sens, spec, P, N))
    if '--write' in sys.argv:
        path = os.path.join(ROOT, 'data', 'quick.json')
        d = json.load(open(path, encoding='utf-8'))
        d['params'] = prm
        d['calib'] = dict(samples=len(rows), acc=round(acc, 3), bacc=round(bacc, 3), sens=round(sens, 3), spec=round(spec, 3), pos=P, neg=N,
                          against='data/sim P4 오토 클리어 확률 ≥ 0.5(Lv200·장비 없음)')
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, path)
        print('저장', path)


if __name__ == '__main__':
    main()
