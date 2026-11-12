"""Sequential, observation-only native measurement; artifacts stay in local/."""
import argparse
import cProfile
import json
import math
from pathlib import Path
import pstats
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'local/measure_1112'
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]


def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def summary(pairs):
    ratios = [p['A'] / p['B'] for p in pairs]
    logs = list(map(math.log, ratios))
    n = len(logs)
    # Two-sided Student t, df=n-1; planned sample counts only.
    t = {5: 2.776445, 10: 2.262157, 20: 2.093024}[n]
    mean = statistics.mean(logs)
    delta = t * statistics.stdev(logs) / math.sqrt(n)
    ci = [math.exp(mean - delta), math.exp(mean + delta)]
    return dict(n=n, ratios=ratios, geometric_ratio=math.exp(mean), ci95=ci,
                stable=ci[0] >= .95 and ci[1] <= 1.05,
                A_min=min(p['A'] for p in pairs), B_min=min(p['B'] for p in pairs),
                A_median=statistics.median(p['A'] for p in pairs),
                B_median=statistics.median(p['B'] for p in pairs),
                ratio_min=min(ratios), ratio_max=max(ratios))


def aa():
    pairs, hashes = [], set()
    for i in range(5):
        pair = {}
        for label in ('AB' if i % 2 == 0 else 'BA'):
            dest = OUT / f'aa-{i+1}-{label}.json'
            with dest.with_suffix('.log').open('w', encoding='utf-8') as log:
                subprocess.run([sys.executable, '-X', 'utf8', '-I', str(ROOT / 'tools/bench_cosmo_speed.py'),
                                '--output', str(dest)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
            row = json.loads(dest.read_text(encoding='utf-8'))
            hashes.add(row['result']['sha256'])
            assert row['result']['positive_progress'] > 0
            pair[label] = row['mean_seconds']
            print(json.dumps(dict(pair=i+1, label=label, seconds=row['seconds'], sha256=row['result']['sha256'])), flush=True)
        pairs.append(pair)
    assert len(hashes) == 1
    result = dict(pairs=pairs, hashes=list(hashes), summary=summary(pairs))
    save('aa-summary.json', result)
    print(json.dumps(result), flush=True)


def blocks():
    from bench_cosmo_speed import search, api
    expected = search('belgras', 6)
    pairs, rows = [], []
    # A fresh confirmation series: 10 predeclared pairs, 8 searches per arm.
    for i in range(10):
        pair = {}
        for label in ('AB' if i % 2 == 0 else 'BA'):
            times = []
            for _ in range(8):
                api.clear_engine_caches()
                start = time.perf_counter()
                result = search('belgras', 6)
                times.append(time.perf_counter() - start)
                assert result == expected and result['positive_progress'] > 0
            pair[label] = sum(times)
            row = dict(pair=i+1, label=label, seconds=times, total=sum(times), result=expected)
            rows.append(row)
            save('aa-block-raw.json', rows)
            print(json.dumps(row), flush=True)
        pairs.append(pair)
    save('aa-block-summary.json', dict(pairs=pairs, summary=summary(pairs), result=expected))


def balanced():
    from bench_cosmo_speed import search, api
    expected = search('belgras', 6)
    pairs, rows = [], []
    # Final fixed confirmation: 10 independent blocks. ABBA/BAAB balances linear drift.
    # Four short cycles per block, eight 340-battle searches per label.
    for i in range(10):
        order = ('ABBA' if i % 2 == 0 else 'BAAB') * 4
        times = {'A': [], 'B': []}
        sequence = []
        for label in order:
            api.clear_engine_caches()
            start = time.perf_counter()
            result = search('belgras', 6)
            elapsed = time.perf_counter() - start
            assert result == expected and result['positive_progress'] > 0
            times[label].append(elapsed)
            sequence.append(dict(label=label, seconds=elapsed))
        pair = {label:sum(v) for label,v in times.items()}
        pairs.append(pair)
        row = dict(pair=i+1, order=order, seconds=times, totals=pair, sequence=sequence, result=expected)
        rows.append(row)
        save('aa-balanced-raw.json', rows)
        print(json.dumps(dict(pair=i+1,totals=pair,ratio=pair['A']/pair['B'],sha256=expected['sha256'])),flush=True)
    save('aa-balanced-summary.json',dict(pairs=pairs,summary=summary(pairs),result=expected))


def profile():
    from bench_cosmo_speed import search, api
    from battlesim import mc
    expected = search('belgras', 6)
    api.clear_engine_caches()
    prof = cProfile.Profile()
    prof.enable()
    result = search('belgras', 6)
    prof.disable()
    assert result == expected
    prof.dump_stats(str(OUT / 'native.prof'))
    st = pstats.Stats(prof)
    def label(k):
        return ':'.join(map(str, k))
    rows = []
    for key, (primitive, calls, own, cumulative, callers) in st.stats.items():
        rows.append(dict(key=label(key), file=key[0], line=key[1], function=key[2], calls=calls,
                         self_s=own, cumulative_s=cumulative, self_pct=own/st.total_tt*100,
                         cumulative_pct=cumulative/st.total_tt*100,
                         callers=[dict(key=label(k), calls=v[1], self_s=v[2], cumulative_s=v[3]) for k,v in callers.items()]))
    rows.sort(key=lambda r:r['cumulative_s'], reverse=True)
    save('profile.json', dict(total_s=st.total_tt, result=result, rows=rows))
    # Separate observation-only cache-miss entry distinguishes hits from rebuilds.
    # These wrapper timings are diagnostic, never used as speed measurements.
    original = mc.Unit.mods
    def rebuild(u):
        return original(u)
    def hit(u):
        return original(u)
    def observed(u):
        return rebuild(u) if u._m is None else hit(u)
    mc.Unit.mods = observed
    try:
        api.clear_engine_caches()
        p = cProfile.Profile()
        p.enable()
        result = search('belgras', 6)
        p.disable()
        assert result == expected
        s = pstats.Stats(p)
        save('mods-split.json', dict(total_s=s.total_tt, rows=[dict(function=k[2], calls=v[1], self_s=v[2], cumulative_s=v[3])
              for k,v in s.stats.items() if k[2] in ('observed','rebuild','hit','mods')]))
    finally:
        mc.Unit.mods = original


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser()
    parser.add_argument('task', choices=['aa','blocks','balanced','profile'])
    args = parser.parse_args()
    globals()[args.task]()
