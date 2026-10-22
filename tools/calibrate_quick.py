# -*- coding: utf-8 -*-
"""빠른 계산 계수(A 아군 피해·B 적 피해·H 회복)를 확률 엔진 결과에 맞춘다.

정답지 = tools/raw/quick_calib.json — tools/gen_quick_calib.py 가 육성 가정 0.6~2.0배·표준 육성·엔진 역보정으로 돌린 시뮬 표본
(화면 브라우저 시뮬과 같은 조건). 시뮬 오토 클리어 확률 c ≥ 0.5 를 「클리어」로 본다. 보스 콘텐츠(코스모 게이트 cosmo, 플래시 포인트 rush)는 성격이 달라 계수를 따로 맞춘다(pc).
점수 = 균형 정확도(클리어·실패 각각 맞힌 비율의 평균). --write 면 data/quick.json 의 params(기본)·pc(콘텐츠별)·calib 에 쓴다.

사용: python -X utf8 -I tools/calibrate_quick.py [--write]
"""
import itertools
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(ROOT))
from tools.runtime import low_priority
from battlesim.fileio import atomic_open, read_json
from battlesim import quick   # noqa: E402

GROUPS = {'cosmo': 'cosmo', 'rush': 'rush'}          # 나머지는 'base'
GRID_A = [0.25, 0.4, 0.6, 0.8, 1.0, 1.3, 1.7, 2.2, 3.0]
GRID_B = [0.15, 0.25, 0.4, 0.6, 0.8, 1.0, 1.3, 1.7, 2.2, 3.0]
GRID_H = [0.0, 0.03, 0.06, 0.1, 0.15, 0.2, 0.3]
CALIB = os.path.join(ROOT, 'tools', 'raw', 'quick_calib.json')


def group(ck):
    return GROUPS.get(ck, 'base')


def sample_key(row):
    return row[0], row[1], tuple(row[2]), json.dumps(row[5], sort_keys=True), row[4]


def validate_samples(rows):
    if not rows or not any(r[4] >= 0.5 for r in rows) or not any(r[4] < 0.5 for r in rows):
        raise ValueError('보정·검증에는 클리어/실패 표본이 각각 1건 이상 필요함')


def dataset(q):
    """-> [(콘텐츠, 스테이지, keys, stage, c, evaluate 인자)] — tools/gen_quick_calib.py 가 만든 육성 가정별 시뮬 표본"""
    rows = []
    for r in read_json(CALIB)['rows']:
        ck, sk, tk, g, c = r[:5]
        st = q['st'].get(ck, {}).get(sk)
        if c is None or not st:
            continue
        rows.append((ck, sk, tk.split(','), st, c, dict(growth=g)))
    return sorted(rows, key=sample_key)


def score(rows, q, pen, prm):
    validate_samples(rows)
    tp = tn = P = N = 0
    for ck, sk, keys, st, c, kw in rows:
        r = quick.evaluate(keys, st, q['sv'], pen, prm, **kw)
        if c >= 0.5:
            P += 1
            tp += r['clear']
        else:
            N += 1
            tn += not r['clear']
    sens = tp / P
    spec = tn / N
    return (sens + spec) / 2, sens, spec, P, N, (tp + tn) / max(1, P + N)


def fit(rows, q, pen):
    validate_samples(rows)
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


M_GRID = [0.4, 0.55, 0.7, 0.85, 1.0, 1.2, 1.4, 1.7, 2.0, 2.5, 3.0, 4.0]
SM_MIN = 6          # 스테이지 표본이 이보다 적으면 보정하지 않음


def fit_stage_m(srows, q, pen, prm):
    """한 스테이지 표본으로 적 피해 배수 m 하나를 고른다(맞힌 수 최대, 같으면 1 에 가까운 값).
    한쪽 결과만 있는 스테이지도 정상 — 클리어/실패 양쪽 검사는 그룹 단위(main)에서만 한다."""
    if not srows:
        raise ValueError('스테이지 표본 없음')
    best = None
    for m in M_GRID:
        hit = 0
        for ck, sk, keys, st, c, kw in srows:
            r = quick.evaluate(keys, dict(st, m=m), q['sv'], pen, prm, **kw)
            hit += (c >= 0.5) == r['clear']
        key = (hit, -abs(m - 1.0))
        if best is None or key > best[0]:
            best = (key, m)
    return best[1]


def stage_factors(gr, q, pen, prm):
    """보스 콘텐츠: 스테이지마다 m. 검증 = 스테이지 안에서 표본을 번갈아 반으로 나눠 앞 반으로 맞추고 뒤 반에서 잼(같은 스테이지·다른 팀/육성)"""
    by = {}
    for r in sorted(gr, key=sample_key):
        by.setdefault(r[1], []).append(r)
    sm, test_before, test_after = {}, [], []
    for sk, srows in sorted(by.items()):
        if len(srows) < SM_MIN:
            continue
        a, b = srows[0::2], srows[1::2]
        if not b:      # 스테이지 안 표본은 한쪽 결과만 있어도 정상(그룹 단위 검증은 main 에서)
            continue
        m_half = fit_stage_m(a, q, pen, prm)
        for ck, _, keys, st, c, kw in b:
            test_before.append((c >= 0.5) == quick.evaluate(keys, dict(st, m=1.0), q['sv'], pen, prm, **kw)['clear'])
            test_after.append((c >= 0.5) == quick.evaluate(keys, dict(st, m=m_half), q['sv'], pen, prm, **kw)['clear'])
        m = fit_stage_m(srows, q, pen, prm)
        if m != 1.0:
            sm[sk] = m
    n = len(test_before)
    if not n:
        raise ValueError('스테이지 검증 표본 없음')
    return sm, sum(test_before) / n, sum(test_after) / n, len(test_before)


def main():
    low_priority()
    q, pen = quick.load(ROOT)
    for d in q['st'].values():          # 보정을 다시 맞추므로 기존 m 은 지운다
        for st in d.values():
            st.pop('m', None)
    rows = dataset(q)
    print('대조 표본', len(rows))
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
    sm_all = {}
    for gname in GROUPS:
        gr = [r for r in rows if group(r[0]) == gname]
        sm, before, after, nt = stage_factors(gr, q, pen, out[gname])
        sm_all[gname] = sm
        for sk, m in sm.items():
            q['st'][gname][sk]['m'] = m
        acc_m = score(gr, q, pen, out[gname])[5]
        calib[gname].update(acc_stage=round(acc_m, 3), stage_hold_before=round(before, 3), stage_hold_after=round(after, 3), stage_m=len(sm))
        calib[gname]['acc'] = round(acc_m, 3)
        print('[%s] 스테이지 보정 %d곳 -> 전체 일치 %.3f / 같은 스테이지 반반 검증 %.3f -> %.3f (%d건)' % (gname, len(sm), acc_m, before, after, nt))
    tot = sum(c['samples'] for c in calib.values())
    acc_all = sum(c['acc'] * c['samples'] for c in calib.values()) / tot
    print('전체 일치(가중) %.3f' % acc_all)
    if '--write' in sys.argv:
        path = os.path.join(ROOT, 'data', 'quick.json')
        d = read_json(path)
        d['params'] = out['base']
        d['pc'] = {k: out[k] for k in GROUPS}
        d['sm'] = sm_all
        d['calib'] = dict(samples=tot, acc=round(acc_all, 3), groups=calib,
                          against='확률 엔진 오토 클리어 확률 ≥ 0.5 — 표준 육성 + 육성 가정 0.6~2.0배 표본(엔진 역보정)')

        with atomic_open(path) as f:
            json.dump(d, f, ensure_ascii=False, separators=(',', ':'))

        print('저장', path)


if __name__ == '__main__':
    main()
