#!/usr/bin/env python3
"""Public standard roster / actual JS search policy with native Python battles.

python -X utf8 -I tools/bench_cosmo_search.py --output local/cosmo-rd --workers 8
Raw results stay under ignored local/. Interrupted runs resume completed phases.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def catalog():
    from battlesim import api
    db = api.get_db()
    rows = []
    for key in sorted(db.units):
        if '@' in key:
            continue
        defs, _ = api._norm_party([key], db, 'fixed', 'standard')
        d = defs[0]
        rows.append(dict(key=key, cls=d.role, power=api.party_power(defs), stats=d.stats))
    return rows


def worker():
    from battlesim.web import run_auto
    for line in sys.stdin:
        m = json.loads(line)
        try:
            for t in m['teams']:
                opts = dict(m.get('options') or {})
                opts.update(t.get('options') or {})
                opts['rules_override'] = dict(m.get('options', {}).get('rules_override') or {},
                                              **(t.get('options', {}).get('rules_override') or {}))
                r = json.loads(run_auto(m['stage'], t['party'], m['n_runs'], m['seed'], opts))
                r = {k: r.get(k) for k in ('prog', 'clear', 'n', 'via', 'progs', 'cosmo')}
                print(json.dumps(dict(type='team', key=t['key'], result=r)), flush=True)
            print(json.dumps(dict(type='done', id=m['id'])), flush=True)
        except Exception as exc:
            print(json.dumps(dict(type='error', msg=repr(exc))), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--worker', action='store_true')
    ap.add_argument('--output', default='local/cosmo-rd')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--repeats', type=int, default=5)
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--sizes', default='30,54')
    ap.add_argument('--variant', default='baseline')
    ap.add_argument('--mode', choices=['top', 'mean'], default='top')
    a = ap.parse_args()
    if a.worker:
        worker()
        return
    out = Path(a.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = catalog()
    (out / 'catalog.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    for size in map(int, a.sizes.split(',')):
        for repeat in range(a.start, a.repeats):
            cmd = ['node', '--max-old-space-size=8192', str(ROOT / 'tools/bench_cosmo_search.js'),
                   str(out), str(size), str(repeat), str(a.workers), sys.executable, a.variant, a.mode]
            subprocess.run(cmd, check=True, cwd=ROOT)


if __name__ == '__main__':
    main()
