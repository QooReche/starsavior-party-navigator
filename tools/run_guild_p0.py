"""Serial P0 measurement; account and all outputs must remain private.

python -X utf8 -I tools/run_guild_p0.py ACCOUNT PRIVATE_DIR [--with-d]
Requires psutil. Two native workers, no concurrent benchmark processes.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    tmp.replace(path)


def sources():
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    return {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(set(names))
            if n and (n.endswith(('.js', '.py', '.json')) or n == 'index.html')}


def sample():
    rows = {}
    for p in psutil.process_iter(['pid', 'name', 'cpu_times', 'create_time']):
        try:
            if p.pid and p.info['cpu_times']:
                t = p.info['cpu_times']
                rows[p.pid] = (p.info['name'], p.info['create_time'], t.user+t.system)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return time.monotonic(), rows


def background(prev, cur):
    excluded = {os.getpid(), *(p.pid for p in psutil.Process().children(recursive=True))}
    elapsed = cur[0]-prev[0]
    rows = []
    for pid, (name, created, cpu) in cur[1].items():
        if pid in excluded or pid not in prev[1] or prev[1][pid][1] != created:
            continue
        cores = max(0, cpu-prev[1][pid][2])/elapsed
        if cores > .05:
            rows.append(dict(pid=pid, name=name, cores=cores))
    return rows


def quiet(log):
    # Wait for three quiet 5-second windows; never kill unrelated work.
    good = 0
    while good < 3:
        prev = sample()
        time.sleep(5)
        rows = background(prev, sample())
        log.write(json.dumps(dict(type='idle', processes=rows))+'\n'); log.flush()
        good = good+1 if not heavy(rows) else 0
        if not good:
            print('Waiting for unrelated CPU work to finish', flush=True)


def run(cmd, log_path, load_log):
    quiet(load_log)
    contaminated = False
    with log_path.open('a', encoding='utf8') as log:
        child = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        prev = sample()
        while child.poll() is None:
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
            cur = sample()
            rows = background(prev, cur)
            contaminated |= heavy(rows)
            load_log.write(json.dumps(dict(type='running', command=cmd[1], processes=rows))+'\n'); load_log.flush()
            prev = cur
        if child.returncode:
            raise RuntimeError('measurement failed; inspect private log: '+str(log_path))
    return not contaminated


def heavy(rows):
    # Ordinary distributed desktop/OS activity is recorded, not called a heavy job.
    return any(r['cores'] >= .5 for r in rows) or sum(r['cores'] for r in rows) >= 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('account', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--with-d', action='store_true')
    a = ap.parse_args()
    account, out = a.account.resolve(), a.output.resolve()
    if out == ROOT or out.is_relative_to(ROOT):
        ap.error('output must be outside repository')
    out.mkdir(parents=True, exist_ok=True)
    pins = dict(accountHash=hashlib.sha256(account.read_bytes()).hexdigest(), sources=sources(),
                seasons=[30112, 30111], offsets=[0, 100, 200], workers=2, withD=a.with_d,
                runtime=dict(python=platform.python_version(), node=subprocess.check_output(['node','--version']).decode().strip(),
                             machine=platform.node(), platform=platform.platform(), logicalCPUs=psutil.cpu_count()),
                criteria=hashlib.sha256((ROOT/'docs/guild_time.md').read_bytes()).hexdigest())
    pinfile = out/'experiment-pins.json'
    if pinfile.exists() and json.loads(pinfile.read_text(encoding='utf8')) != pins:
        ap.error('experiment changed; use a new output directory')
    save(pinfile, pins)
    import msvcrt
    with (out/'run.lock').open('a+b') as lock, (out/'load.jsonl').open('a', encoding='utf8') as load_log:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0'); lock.flush()
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        plan = [(s, offset, n) for s in pins['seasons'] for offset in pins['offsets']
                for n in (['E','A'] if offset == 100 else ['A','E'])]
        if a.with_d:
            plan.append((30112, 0, 'D'))
        for season, offset, name in plan:
            run_dir = out/str(season)/str(offset)/name
            run_dir.mkdir(parents=True, exist_ok=True)
            setting = {'newSearch':name=='D', 'legacyBaseline':name=='E'}
            if name=='D':
                base=json.loads((ROOT/'data/guild_defaults.json').read_text(encoding='utf8'))
                setting['placement']={**base['search']['placement'], 'baseline':True, 'enabled':True}
            settings_file=run_dir/'settings.json'; save(settings_file, setting)
            status = dict(season=season, offset=offset, condition=name)
            save(out/'status.json', dict(status, step='search', state='running'))
            print(season, offset, name, 'search', flush=True)
            valid = run(['node','tools/measure_guild_time.js',str(account),str(run_dir),
                         'new' if name=='D' else 'old',str(settings_file),str(season),str(offset)],
                        run_dir/'search.log',load_log)
            timing_file=run_dir/'timing.json'
            if not timing_file.exists():
                save(timing_file, dict(backgroundQuiet=valid))
            save(out/'status.json', dict(status, step='holdout', state='running'))
            print(season, offset, name, 'holdout', flush=True)
            run(['node','tools/evaluate_guild_time.js',str(account),str(run_dir/'holdout'),str(run_dir)],
                run_dir/'holdout.log',load_log)
            if sources()!=pins['sources'] or hashlib.sha256(account.read_bytes()).hexdigest()!=pins['accountHash']:
                raise RuntimeError('source/account changed during experiment')
            save(out/'status.json',dict(status,state='complete'))
        subprocess.run(['node','tools/report_guild_p0.js',str(out)],cwd=ROOT,check=True)
        save(out/'status.json',dict(state='complete',inputsUnchanged=True))


if __name__ == '__main__':
    main()
