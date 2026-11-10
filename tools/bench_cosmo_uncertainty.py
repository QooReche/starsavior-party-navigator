"""Paired gold bootstrap SE, conditional on the selected gold reference triple.

Master-seed SE is reported separately by bench_cosmo_report.js. This does not
claim to remove finite-gold winner selection bias or certify a global optimum.
"""
import argparse
import gzip
import json
import math
from pathlib import Path
import random
import statistics


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', default='local/cosmo-rd')
    ap.add_argument('--bootstrap', type=int, default=500)
    a = ap.parse_args()
    root = Path(a.output)
    report = json.loads((root / 'quality-summary.json').read_text(encoding='utf-8'))
    with gzip.open(root / report['goldFile'], 'rt', encoding='utf-8') as f:
        raw = json.load(f)
    assert raw.get('signature') == report['goldSignature'], 'report/gold input mismatch'
    gold = {r['key']: r['scores'] for r in raw['rows']}
    rng = random.Random(900002)
    n = len(next(iter(gold.values())))
    assert n == report['goldRuns'] and all(len(scores) == n for scores in gold.values())
    m = math.ceil(n*.2-1e-9)
    for pool in report['pools'].values():
        reference = pool['goldBestKeys']
        used = set(reference)
        for method in pool['methods'].values():
            for run in method['runs']:
                used.update(run['selectedKeys'])
        sampled = {k: [] for k in used}
        for _ in range(a.bootstrap):
            # Same indices for all teams preserve covariance from common gold seeds.
            indices = [rng.randrange(n) for _ in range(n)]
            for key in used:
                scores = gold[key]
                sampled[key].append(math.floor(sum(sorted((scores[i] for i in indices), reverse=True)[:m])/m+.5))
        best = [sum(sampled[k][i] for k in reference) for i in range(a.bootstrap)]
        for method in pool['methods'].values():
            deltas = []
            for run in method['runs']:
                delta = [best[i]-sum(sampled[k][i] for k in run['selectedKeys']) for i in range(a.bootstrap)]
                run['goldConditionalSE'] = statistics.stdev(delta)
                deltas.append(delta)
            method['goldConditionalMeanSE'] = statistics.stdev([statistics.fmean(d[i] for d in deltas) for i in range(a.bootstrap)])
    report['bootstrap'] = dict(repeats=a.bootstrap, seed=900002, paired=True,
                               scope='conditional on selected reference; gold winner uncertainty not included')
    (root / 'quality-summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
