"""Adoption gate: screening recall, total time, and independent master seeds."""
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def test_report():
    (ROOT / 'local').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cosmo-report-test-', dir=ROOT / 'local') as temp:
        out = Path(temp)
        bosses = ['belgras', 'tyria', 'carnelia']
        catalog = [{'key': 'u%02d' % i} for i in range(24)]
        (out / 'catalog.json').write_text(json.dumps(catalog), encoding='utf-8')
        gold = []
        for bi, boss in enumerate(bosses):
            for low in range(2):
                keys = [r['key'] for r in catalog[bi*8+low*4:bi*8+low*4+4]]
                gold.append(dict(key=boss+'|'+'+'.join(keys)+'|6', boss=boss, keys=keys, order=keys,
                                 summary={'top': 100-low*50}, scores=[100-low*50]*200))
        with gzip.open(out / 'gold-custom.json.gz', 'wt', encoding='utf-8') as f:
            json.dump(dict(rows=gold, seconds=10), f)
        high, low = gold[::2], gold[1::2]
        result = {'rows': [{'teams': high, 'sum': 300}]}
        # Deliberately different pass/rerank rankings to distinguish the gate inputs.
        for variant, repeat, replay in [('baseline', 0, False), ('baseline', 1, False), ('fast', 0, False), ('fast', 0, True)]:
            folder = out / ('24-top-%s%s-%d' % (variant, '-replay' if replay else '', repeat))
            folder.mkdir()
            baseline = variant == 'baseline'
            report = dict(size=24, repeat=repeat, variant=variant, mode='top', replay=replay,
                          result=result, seconds=100 if baseline else 90,
                          wallSeconds=None if replay else (110 if baseline else 120), phases=[])
            for index, seed, jobs in [(0, 1, gold), (1, 4, gold if baseline else high), (2, 3, low if baseline else gold)]:
                phase = dict(seed=repeat*100+seed, jobs=jobs)
                with gzip.open(folder / ('phase-%d.json.gz' % index), 'wt', encoding='utf-8') as f:
                    json.dump(phase, f)
            (folder / 'result.json').write_text(json.dumps(report), encoding='utf-8')
        subprocess.run(['node', str(ROOT / 'tools/bench_cosmo_report.js'), str(out), 'gold-custom.json.gz'],
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        summary = json.loads((out / 'quality-summary.json').read_text(encoding='utf-8'))
        fast = summary['pools']['24']['methods']['fast']
        assert len(fast['runs']) == 1, 'replay cannot inflate independent R'
        assert fast['timedRuns'] == 1 and fast['meanSeconds'] == 120
        assert fast['gate']['top50'] is False, 'screening recall takes priority over rerank recall'
        assert fast['gate']['faster'] is False, 'total time includes selection overhead'
        subprocess.run([sys.executable, '-X', 'utf8', '-I', str(ROOT / 'tools/bench_cosmo_uncertainty.py'),
                        '--output', str(out), '--bootstrap', '20'], cwd=ROOT, check=True)
        updated = json.loads((out / 'quality-summary.json').read_text(encoding='utf-8'))
        assert updated['pools']['24']['methods']['fast']['goldConditionalMeanSE'] == 0


if __name__ == '__main__':
    test_report()
    print('PASS cosmo_bench_report_test')
