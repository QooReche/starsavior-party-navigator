# -*- coding: utf-8 -*-
"""공개 standard 육성 코스모 후보 탐색의 재현 가능한 단일 프로세스 측정.

python -X utf8 -I tools/bench_cosmo_speed.py --output local/cosmo-before.json
전체 UI 탐색이 아니라 대표 보스의 고정 후보 70팀 예선 + 상위 10팀 재평가임.
"""
import argparse
import cProfile
import hashlib
import itertools
import json
from pathlib import Path
import pstats
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import api, simulate

KEYS = ('amora', 'bell', 'bunny-charlotte', 'carmen', 'carnelia', 'ceres', 'gwen', 'tyria')


def search(boss, level):
    """입력·순서·시드·판 수 고정. 동점은 원래 조합 순서대로 유지함."""
    encounter = {'cosmo_raid': {'boss': boss, 'step': 3, 'level': level}}
    ranked = []
    results = []
    for keys in itertools.combinations(KEYS, 4):
        party = {'units': list(keys), 'leader': 0}
        result = simulate(party, encounter, {'build': 'standard', 'seed': 1, 'n_runs': 2})
        result.pop('runtime_ms_per_run')
        ranked.append((sum(result['cosmo_raid']['score_runs']), party))
        results.append(result)
    ranked.sort(key=lambda row: row[0], reverse=True)
    for _, party in ranked[:10]:
        result = simulate(party, encounter, {'build': 'standard', 'seed': 7, 'n_runs': 20})
        result.pop('runtime_ms_per_run')
        results.append(result)
    packed = json.dumps(results, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return {'sha256': hashlib.sha256(packed).hexdigest(), 'battles': 340,
            'positive_progress': sum(r['outcome']['progress'] > 0 for r in results)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--boss', default='belgras')
    ap.add_argument('--level', type=int, default=6)
    ap.add_argument('--output', required=True)
    ap.add_argument('--mode', choices=('baseline', 'dirty', 'line', 'all'), default='all')
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT / 'tests'))
    from cosmo_speed_reference import mode
    with mode(args.mode):
        measure(args)


def measure(args):
    # 모듈·DB 최초 읽기는 측정에서 제외. 각 탐색의 정의/인카운터 LRU는 비우고 시작.
    search(args.boss, args.level)
    elapsed, signatures = [], []
    for _ in range(3):
        api.clear_engine_caches()
        start = time.perf_counter()
        signatures.append(search(args.boss, args.level))
        elapsed.append(time.perf_counter() - start)
    assert signatures[0] == signatures[1] == signatures[2]
    api.clear_engine_caches()
    profile = cProfile.Profile()
    profile.enable()
    signature = search(args.boss, args.level)
    profile.disable()
    assert signature == signatures[0]
    stats = pstats.Stats(profile)
    rows = [{'file': str(Path(file).as_posix()).replace(ROOT.as_posix() + '/', ''),
             'line': line, 'function': name, 'calls': calls, 'self_s': own, 'cumulative_s': cumulative}
            for (file, line, name), (_, calls, own, cumulative, _) in stats.stats.items()]
    rows.sort(key=lambda row: row['self_s'], reverse=True)
    report = {'python': sys.version, 'mode': args.mode, 'boss': args.boss, 'level': args.level,
              'seconds': elapsed, 'mean_seconds': statistics.fmean(elapsed),
              'result': signature, 'profile_total_s': stats.total_tt, 'profile': rows}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'profile'}, ensure_ascii=False, indent=2))
    stats.sort_stats('tottime').print_stats(18)


if __name__ == '__main__':
    main()
