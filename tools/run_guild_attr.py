"""Serial four-setting attribution with private, resumable search and holdout files.

python -X utf8 -I tools/run_guild_attr.py ACCOUNT PRIVATE_DIR
The existing native measurement/evaluation tools own the two-worker limit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = [('A', False, False), ('B', False, True),
              ('C', True, False), ('D', True, True)]


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    temporary.replace(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('account', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    output, account = a.output.resolve(), a.account.resolve()
    if output == ROOT or output.is_relative_to(ROOT):
        ap.error('output must be outside repository')
    output.mkdir(parents=True, exist_ok=True)
    base = json.loads((ROOT/'data/guild_defense.json').read_text(encoding='utf8'))['search']
    # Hash the full tracked input tree, not HEAD (documentation commits may advance).
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    sources = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
               for name in names if name and (name.endswith(('.js', '.py', '.json')) or name == 'index.html')}
    pins = dict(accountHash=hashlib.sha256(account.read_bytes()).hexdigest(), sources=sources,
                conditions=CONDITIONS, workers=2, holdout='50 seeds x 20 battles, seedStart=20270101')
    pinfile = output/'experiment-pins.json'
    if pinfile.exists() and json.loads(pinfile.read_text(encoding='utf8')) != json.loads(json.dumps(pins)):
        ap.error('experiment inputs changed; use a new output directory')
    save(pinfile, pins)
    # A process lock prevents two orchestrators from sharing this experiment.
    # On Windows an open exclusive file handle is released even after a crash.
    import msvcrt
    with (output/'run.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        for name, new, placement in CONDITIONS:
            settings = dict(newSearch=new, placement={**base['placement'], 'baseline': placement, 'enabled': placement})
            settings_file = output/(name+'-settings.json')
            save(settings_file, settings)
            steps = [('search', ['node', 'tools/measure_guild_time.js', str(account), str(output/name),
                                 'new' if new else 'old', str(settings_file)]),
                     ('holdout', ['node', 'tools/evaluate_guild_time.js', str(account),
                                  str(output/(name+'-holdout')), str(output/name)])]
            for step, cmd in steps:
                save(output/'status.json', dict(condition=name, step=step, state='running'))
                print(name, step, flush=True)
                with (output/(name+'-'+step+'.log')).open('a', encoding='utf8') as log:
                    subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                save(output/'status.json', dict(condition=name, step=step, state='complete'))
        subprocess.run(['node', 'tools/report_guild_attr.js', str(output)], cwd=ROOT, check=True)
        save(output/'status.json', dict(state='complete'))


if __name__ == '__main__':
    main()
