"""Independent gold and CRN/truncated-battle pilot for public-standard search.

Raw per-run arrays are kept only in local/. Gold candidates are the union of all
completed methods' rerank/final teams (not the global combinatorial optimum).
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import statistics as st
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            return json.load(f)
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, obj):
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False)


def battle(task):
    from battlesim import simulate
    from battlesim.web import cosmo_summary
    job, n, seed, streams, limit, *extra = task
    offset = extra[0] if extra else 0
    encounter = {'cosmo_raid': {'boss': job['boss'], 'step': 3, 'level': 6}}
    if limit:
        # Actual action budget. max_turns is a tick horizon and is NOT equivalent.
        encounter['turn_limit'] = limit
    start = time.perf_counter()
    cpu_start = time.process_time()
    r = simulate({'units': job['order'], 'leader': 0}, encounter,
                 {'build': 'standard', 'n_runs': n, 'seed': seed, 'run_offset': offset, 'rng_streams': streams,
                  'rules_override': {'power_penalty': 'model'}})
    cr = r['cosmo_raid']
    if limit is None:
        assert r['outcome']['progress'] > 0, job['key']
    return dict(key=job['key'], boss=job['boss'], keys=job['keys'], order=job['order'],
                summary=cosmo_summary(cr), scores=cr['score_runs'], progress=r['outcome']['progress'],
                seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu_start)


def corr(x, y):
    if len(x) < 2 or st.pvariance(x) == 0 or st.pvariance(y) == 0:
        return None
    return st.correlation(x, y)


def ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    out = [0.] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[i]] == values[order[j]]:
            j += 1
        for k in range(i, j):
            out[order[k]] = (i + j - 1) / 2
        i = j
    return out


def run_jobs(pool, tasks, path):
    signature = hashlib.sha256(json.dumps(tasks, sort_keys=True).encode()).hexdigest()
    if path.exists():
        old = read(path)
        if old['signature'] == signature:
            return old
        raise ValueError('candidate set changed; use a new output: ' + str(path))
    start = time.perf_counter()
    rows = []
    for row in pool.map(battle, tasks, chunksize=5):
        rows.append(row)
        if len(rows) % 100 == 0:
            print(path.name, len(rows), '/', len(tasks), round(time.perf_counter()-start, 2), flush=True)
    data = dict(signature=signature, seconds=time.perf_counter()-start, rows=rows)
    write(path, data)
    return data


def gold(a):
    out = Path(a.output)
    union = {}
    for directory in out.glob('*-top-*'):
        if not (directory / 'result.json').exists():
            continue
        for phase in directory.glob('phase-*.json.gz'):
            d = read(phase)
            if d['seed'] % 100 not in (2, 3):
                continue
            for j in d['jobs']:
                union[j['key']] = j
    if not union:
        raise ValueError('no completed searches')
    # Selection seeds 1..405, independent evaluation seed 900001.
    tasks = [(union[k], a.gold_runs, 900001, False, None) for k in sorted(union)]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        data = run_jobs(pool, tasks, out / a.gold_file)
    print(json.dumps(dict(gold_teams=len(tasks), runs=a.gold_runs, seconds=data['seconds'])), flush=True)


def budget_pilot(a, out, groups, maps, jobs):
    """Time small, actual allocations; not a production search or a valid OCBA-m claim."""
    by_key = {j['key']: j for j in jobs}
    keys = [k for g in groups.values() for k in g['top']]
    def tasks(alloc, offset):
        return [(by_key[k], n, 700001, False, None, offset) for k, n in alloc.items() if n > 0]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(battle, tasks({k: 1 for k in keys[:a.workers]}, 0), chunksize=1))
        initial = run_jobs(pool, tasks(dict.fromkeys(keys, 5), 0), out / 'budget-initial.json.gz')
        init = {r['key']: r['scores'] for r in initial['rows']}
        assert all(init[k] == maps['full'][k]['scores'][:5] for k in keys), 'pilot seed mismatch'
        uniform = run_jobs(pool, tasks(dict.fromkeys(keys, 20), 0), out / 'budget-uniform.json.gz')
        uniform_scores = {r['key']: r['scores'] for r in uniform['rows']}
        assert all(uniform_scores[k] == maps['full'][k]['scores'][:20] for k in keys)
        def top_score(scores):
            n = max(1, math.ceil(len(scores)*.2-1e-9))
            return math.floor(sum(sorted(scores, reverse=True)[:n])/n+.5)
        def recall(scores):
            result = {}
            for boss, g in groups.items():
                ref = sorted(g['top'], key=lambda k: (-maps['independent'][k]['summary']['top'], k))[:10]
                picked = sorted((k for k in g['top'] if k in scores), key=lambda k: (-top_score(scores[k]), k))[:10]
                result[boss] = len(set(ref)&set(picked))/10
            return result
        report = {'uniform20': dict(games=len(keys)*20, seconds=uniform['seconds'],
                                    cpu_seconds=sum(r['cpu_seconds'] for r in uniform['rows']),
                                    top10_recall=recall(uniform_scores))}
        for policy in ('halving', 'race', 'ocba'):
            start = time.perf_counter()
            allocation = {}
            for g in groups.values():
                kk = g['top']; means = {k: st.fmean(init[k]) for k in kk}
                variances = {k: st.variance(init[k]) for k in kk}
                if policy == 'halving':
                    allocation.update(dict.fromkeys(sorted(kk, key=lambda k: (-means[k], k))[:len(kk)//2], 15))
                elif policy == 'race':
                    lower = max(means[k]-2*math.sqrt(variances[k]/5) for k in kk)
                    allocation.update({k: 15 for k in kk if means[k]+2*math.sqrt(variances[k]/5) >= lower})
                else:
                    best = max(kk, key=means.get)
                    weights = {k: variances[k]/max(1, means[best]-means[k])**2 for k in kk if k != best}
                    weights[best] = math.sqrt(variances[best])*math.sqrt(sum(w*w/variances[k] for k,w in weights.items() if variances[k] > 0))
                    total = sum(weights.values()); budget = 15*len(kk)
                    raw = {k: budget*weights[k]/total if total else 15 for k in kk}
                    counts = {k: math.floor(v) for k,v in raw.items()}
                    for k in sorted(kk, key=lambda k: (-(raw[k]-counts[k]), k))[:budget-sum(counts.values())]:
                        counts[k] += 1
                    assert sum(counts.values()) == budget
                    allocation.update(counts)
            selection_seconds = time.perf_counter()-start
            extra = run_jobs(pool, tasks(allocation, 5), out / ('budget-'+policy+'.json.gz'))
            added = {r['key']: r['scores'] for r in extra['rows']}
            # Eliminated candidates are not returned. OCBA keeps its 5-run observations.
            scores = {k: init[k]+added.get(k, []) for k in allocation}
            for k, values in added.items():
                assert values[:min(35,len(values))] == maps['full'][k]['scores'][5:5+min(35,len(values))], 'offset reused old draws'
            report[policy] = dict(games=len(keys)*5+sum(allocation.values()),
                                  seconds=initial['seconds']+extra['seconds']+selection_seconds,
                                  cpu_seconds=sum(r['cpu_seconds'] for r in initial['rows']+extra['rows']),
                                  top10_recall=recall(scores), max_extra_runs=max(allocation.values(), default=0))
        report['note'] = '40 teams/boss, 5-run mean allocation, independent 40-run top10 reference; no diversity guarantee or sequential error correction; not a full-search quality gate'
        return report


def study(a):
    out = Path(a.output)
    catalog = {r['key']: r for r in read(out / 'catalog.json')}
    first = read(out / '30-top-baseline-0/phase-0.json.gz')
    second = read(out / '30-top-baseline-0/phase-2.json.gz')
    rng = random.Random(20261110)
    jobs = []
    groups = {}
    for boss in ('belgras', 'tyria', 'carnelia'):
        all_jobs = [j for j in first['jobs'] if j['boss'] == boss]
        # A random set for global/top-decile correlation; a separate top-candidate set for CRN.
        random_jobs = rng.sample(all_jobs, a.sample)
        top_jobs = sorted([j for j in second['jobs'] if j['boss'] == boss],
                          key=lambda j: -second['res'][j['key']]['cosmo']['top'])[:40]
        groups[boss] = dict(random=[j['key'] for j in random_jobs], top=[j['key'] for j in top_jobs])
        jobs.extend({j['key']: j for j in random_jobs + top_jobs}.values())
    configs = [('full', False, None, 700001), ('streams', True, None, 700001),
               ('independent', False, None, 800001), ('independentStreams', True, None, 800001),
               ('cut15', False, 15, 700001), ('cut25', False, 25, 700001)]
    datasets = {}
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for name, streams, limit, seed in configs:
            data = run_jobs(pool, [(j, a.study_runs, seed, streams, limit) for j in jobs], out / ('study-'+name+'.json.gz'))
            datasets[name] = data
    maps = {name: {r['key']: r for r in data['rows']} for name, data in datasets.items()}
    report = {'sample': a.sample, 'runs': a.study_runs, 'groups': {},
              'games_per_configuration': len(jobs)*a.study_runs,
              'timings': {k: v['seconds'] for k, v in datasets.items()},
              'cpu_seconds': {k: sum(r['cpu_seconds'] for r in v['rows']) for k, v in datasets.items()}}
    for boss, group in groups.items():
        report['groups'][boss] = {}
        for label, keys in group.items():
            pairs = list(zip(keys[::2], keys[1::2]))
            rows = {}
            for name in ('full', 'streams'):
                correlations, paired, independent = [], [], []
                for x, y in pairs:
                    vx, vy = maps[name][x]['scores'], maps[name][y]['scores']
                    rho = corr(vx, vy)
                    if rho is not None:
                        correlations.append(rho)
                    paired.append(st.variance([a-b for a,b in zip(vx, vy)]))
                    # Separate random seeds with the same marginal policy.
                    iy = maps['independent' if name == 'full' else 'independentStreams'][y]['scores']
                    independent.append(st.variance([a-b for a,b in zip(vx, iy)]))
                rows[name] = dict(rho_mean=st.fmean(correlations) if correlations else None,
                                  defined_pairs=len(correlations), pairs=len(pairs),
                                  paired_variance_mean=st.fmean(paired), independent_variance_mean=st.fmean(independent),
                                  difference_variance_ratio=sum(paired)/sum(independent) if sum(independent) else None)
            report['groups'][boss][label] = rows
            rows['streams_vs_base_difference_variance'] = (rows['streams']['paired_variance_mean']/rows['full']['paired_variance_mean']
                                                           if rows['full']['paired_variance_mean'] else None)
        keys = group['random']
        scores = [maps['full'][k]['summary']['top'] for k in keys]
        top = sorted(range(len(keys)), key=lambda i:-scores[i])[:max(2, math.ceil(len(keys)/10))]
        def rank_comparison(values):
            return dict(spearman=corr(ranks(scores), ranks(values)),
                        top_decile_spearman=corr(ranks([scores[i] for i in top]), ranks([values[i] for i in top])))
        proxies = {}
        for kind in ('power', 'attack', 'defense', 'hp'):
            def value(key):
                row = catalog[key]
                if kind == 'power':
                    return row['power']
                if kind == 'attack':
                    return row['stats'].get('atk', 0)*row['stats'].get('spd', 100)
                return row['stats'].get('def' if kind == 'defense' else 'hp', 0)
            proxies[kind] = rank_comparison([sum(value(u) for u in maps['full'][k]['keys']) for k in keys])
        report['groups'][boss]['proxies'] = proxies
        report['groups'][boss]['one_vs_many'] = rank_comparison([first['res'][k]['cosmo']['top'] for k in keys])
        cuts = {}
        for name in ('cut15', 'cut25'):
            values = [maps[name][k]['summary']['top'] for k in keys]
            cuts[name] = dict(spearman=corr(ranks(scores), ranks(values)),
                              top_decile_spearman=corr(ranks([scores[i] for i in top]), ranks([values[i] for i in top])),
                              positive_progress=sum(maps[name][k]['progress'] > 0 for k in keys),
                              cpu_ratio=sum(maps[name][k]['cpu_seconds'] for k in keys)/sum(maps['full'][k]['cpu_seconds'] for k in keys))
        report['groups'][boss]['truncation'] = cuts
        # Fixed-sample pilot of later-stage budget policies; no adaptive path is shipped.
        topkeys = group['top']
        ref = sorted(topkeys, key=lambda k:-maps['independent'][k]['summary']['top'])[:10]
        means = {k: st.fmean(maps['full'][k]['scores'][:5]) for k in topkeys}
        survivors = sorted(topkeys, key=means.get, reverse=True)[:len(topkeys)//2]
        lower = max(means[k]-2*st.stdev(maps['full'][k]['scores'][:5])/math.sqrt(5) for k in topkeys)
        race = [k for k in topkeys if means[k]+2*st.stdev(maps['full'][k]['scores'][:5])/math.sqrt(5) >= lower]
        best_key = max(means, key=means.get)
        best = means[best_key]
        variances = {k: st.variance(maps['full'][k]['scores'][:5]) for k in topkeys}
        weights = {k: variances[k]/max(1, best-means[k])**2 for k in topkeys if k != best_key}
        weights[best_key] = math.sqrt(variances[best_key])*math.sqrt(sum(w*w/variances[k] for k,w in weights.items() if variances[k] > 0))
        total = sum(weights.values())
        report['groups'][boss]['later_budget_pilot'] = dict(
            halving_top10_recall=len(set(ref)&set(survivors))/10, halving_game_ratio=(len(topkeys)*5+len(survivors)*15)/(len(topkeys)*20),
            uncorrected_race_survivors=len(race), uncorrected_race_top10_recall=len(set(ref)&set(race))/10,
            ocba_largest_share=max(weights.values())/total if total else None,
            note='5-run means/normal CI/OCBA diagnostic; top-quantile objective and joint triple selection invalidate direct adoption')
    report['later_budget_measured'] = budget_pilot(a, out, groups, maps, jobs)
    (out / 'study-summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['gold', 'study'])
    ap.add_argument('--output', default='local/cosmo-rd')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--gold-runs', type=int, default=200)
    ap.add_argument('--gold-file', default='gold.json.gz')
    ap.add_argument('--sample', type=int, default=200)
    ap.add_argument('--study-runs', type=int, default=40)
    a = ap.parse_args()
    if a.command == 'study' and a.study_runs < 40:
        ap.error('--study-runs must be at least 40 for the offset/budget comparison')
    (gold if a.command == 'gold' else study)(a)
