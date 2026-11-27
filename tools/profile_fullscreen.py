# -*- coding: utf-8 -*-
"""훑기(1판×N팀) 고정 비용 분해 — 네이티브 run_auto 1판 호출 vs 8판 호출의 팀당 시간, cProfile 상위 항목.
팀 명세는 bench_fullscreen browser 결과(비공개 browser.json 의 rows)를 쓴다. 출력은 시간·비율만(계정 수치 없음).
  python -X utf8 -I tools/profile_fullscreen.py [--src browser.json] [--batch]"""
import argparse
import cProfile
import io
import json
import pstats
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SRC = Path('E:/AI_mk2/_private/role-private/casebook_myinfo/site_reco/fullscreen/browser.json')


def specs(src):
    data = json.loads(Path(src).read_text(encoding='utf-8'))
    out = {}
    for r in data:
        if r['mode'] != 'on' or not r['full']:
            continue
        opt = dict(r['options'], rng_streams=True)
        teams = [(t['party'], dict(opt, break_skill={'name': t['bname'], 'level': t['blv']} if t['bname'] else None)) for t in r['rows']]
        out[r['name']] = (r['stageStr'], teams)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=str(SRC))
    ap.add_argument('--reps', type=int, default=6)
    ap.add_argument('--batch', action='store_true', help='run_auto_batch 도 잰다')
    a = ap.parse_args()
    from battlesim import web
    for name, (stage, teams) in specs(a.src).items():
        teams = (teams * a.reps)[:max(len(teams), 24)]
        web.run_auto(stage, teams[0][0], 1, 1, json.dumps(teams[0][1]))   # 데우기(데이터 적재)
        row = {}
        for n in (1, 8):
            t0 = time.perf_counter()
            for p, o in teams:
                web.run_auto(stage, p, n, 1, json.dumps(o))
            row[n] = (time.perf_counter() - t0) / len(teams)
        if a.batch and hasattr(web, 'run_auto_batch'):
            t0 = time.perf_counter()
            list(web.run_auto_batch(stage, [{'key': i, 'party': p, 'options': o} for i, (p, o) in enumerate(teams)], 1, 1, '{}'))
            row['b1'] = (time.perf_counter() - t0) / len(teams)
        fixed = (8 * row[1] - row[8]) / 7     # 1판 호출 = 고정 + 판, 8판 = 고정 + 8판
        print('%s: 팀당 1판 %.1fms · 8판 %.1fms(판당 %.1fms) → 호출당 고정 약 %.1fms(1판 호출의 %.0f%%)%s' % (
            name, 1000 * row[1], 1000 * row[8], 1000 * row[8] / 8, 1000 * fixed, 100 * fixed / row[1],
            (' · 묶음 1판 %.1fms' % (1000 * row['b1'])) if 'b1' in row else ''), flush=True)
        pr = cProfile.Profile()
        pr.enable()
        for p, o in teams:
            web.run_auto(stage, p, 1, 1, json.dumps(o))
        pr.disable()
        s = io.StringIO()
        st = pstats.Stats(pr, stream=s)
        st.sort_stats('cumulative').print_stats(r'(api|web|mc|foe|support|mc_semantics)\.py:\d+\((_simulate|run_auto|_norm_encounter_raw|_norm_party|support_report|_ally_stage_fx|run|__init__|assumptions_used|stage_waves|parse_fx|party_power|dumps)\)')
        print('\n'.join(l for l in s.getvalue().splitlines() if '(' in l and ('ncalls' in l or '.py:' in l))[:3000])


if __name__ == '__main__':
    main()
