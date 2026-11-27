"""1197383 result oracle and sequential, warm median benchmark (synthetic parties).

--capture is allowed only on the pinned baseline; never updates an existing oracle.
Every single-run response (except wall time) is compared, including raw scores/via/actions.
"""
import argparse
import hashlib
import json
import pathlib
import statistics
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if '--reference' in sys.argv:
    # Load changed engine modules from a commit without touching the worktree.
    import importlib.abc
    import importlib.util
    ref = sys.argv[sys.argv.index('--reference') + 1]
    class ReferenceLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, fullname, path=None, target=None):
            if fullname in ('battlesim.mc', 'battlesim.api', 'battlesim.datafile'):
                return importlib.util.spec_from_file_location(fullname, ROOT / (fullname.replace('.', '/') + '.py'), loader=self)
        def create_module(self, spec):
            return None
        def exec_module(self, module):
            file = module.__name__.replace('.', '/') + '.py'
            source = subprocess.check_output(['git', 'show', ref + ':' + file], cwd=ROOT)
            exec(compile(source, str(ROOT / file), 'exec'), module.__dict__)
    sys.meta_path.insert(0, ReferenceLoader())
from battlesim import api
from battlesim.mc import Battle

ORACLE = ROOT / 'tests/fixtures/safe_perf_1197383.json'
PARTY = {'units': ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle'], 'leader': 0}
PARTIES = [PARTY, {'units': ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria'], 'leader': 2},
           {'units': ['luna', 'carnelia', 'gwen', 'smile'], 'leader': 1}]


def bits(value):
    if isinstance(value, float):
        return value.hex()
    if isinstance(value, dict):
        return {k: bits(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [bits(v) for v in value]
    return value


def cases():
    for name, stage in [('moon', 'clo/달 회랑/FLOOR 100'),
                        ('sun', 'clo/태양 회랑/FLOOR 200'),
                        ('wave', 'clo/태양 회랑/FLOOR 250')]:
        yield name, {'stage': stage}, {}
    for step in range(1, 8):
        yield 'guild30112-' + str(step), {'guild': {'seasonId': 30112, 'step': step, 'level': 0, 'sets': [0]*4}}, {}
    yield 'cosmo', {'cosmo_raid': {'step': 3, 'level': 0}}, {}
    yield 'unknown-slots', {'waves': [[{'name': 'unknown', 'hp': 300000, 'atk': 2000, 'spd': 105}]]}, {}
    # Public enemy definitions include summon groups; no private account data.
    yield 'summon', {'stage': 'equip/잊혀진 맹세/잊혀진 맹세 XⅤ'}, {}
    yield 'round-boundary', {'stage': 'clo/태양 회랑/FLOOR 250'}, {
        'break_skill': {'name': '큐브 과부하', 'level': 5}, 'rules_override': {'break_skill_cd_unit': 'round'}}


def snapshot():
    out = {}
    original = Battle.run
    observations = []
    def observed(b):
        result = original(b)
        state = bits([b.rng.getstate(), [[getattr(u, k) for k in
                     ('hp', 'gauge', 'dmg', 'taken', 'actions', 'dead', 'cd')]
                     for u in b.allies + b.all_foes]])
        observations.append({'waves': b.wave_i + 1, 'summons': b.rule_hits['summon'],
                             'actions': b.global_turns, 'progress': b.progress(), 'via': b.ally_via,
                             'state': hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()})
        return result
    Battle.run = observed
    try:
        for name, enc, extra in cases():
            rows = []
            for party, seed in zip(PARTIES, (1, 17, 20261127)):
                r = api.simulate(party, enc, {'build': 'standard', 'seed': seed, 'n_runs': 1,
                                             'per_run': True, 'raw_runs': True, **extra})
                r.pop('runtime_ms_per_run', None)
                encoded = json.dumps(bits(r), sort_keys=True, ensure_ascii=False, separators=(',', ':'))
                rows.append({'seed': seed, 'sha256': hashlib.sha256(encoded.encode()).hexdigest(),
                             'raw': r.get('raw_runs'), 'coverage': observations[-1]})
            out[name] = rows
    finally:
        Battle.run = original
    assert all(x['coverage']['actions'] > 0 for rows in out.values() for x in rows)
    assert all(x['coverage']['progress'] > 0 for x in out['moon'])
    assert any(x['coverage']['waves'] > 1 for x in out['wave'])
    assert any(x['coverage']['summons'] > 0 for x in out['summon'])
    return out


def verify():
    expected = json.loads(ORACLE.read_text(encoding='utf-8'))['cases']
    actual = snapshot()
    bad = [name for name in expected if expected[name] != actual.get(name)]
    assert not bad, '1197383 mismatch: ' + ', '.join(bad)
    return len(expected) * 3


def benchmark(repeats):
    picked = list(cases())[:3] + [list(cases())[9]]
    result = {}
    for name, enc, extra in picked:
        samples = []
        for i in range(repeats + 1):
            start = time.perf_counter()
            for seed in range(1, 9):
                api.simulate(PARTY, enc, {'build': 'standard', 'seed': seed, 'n_runs': 1, **extra})
            if i:
                samples.append((time.perf_counter() - start) * 1000 / 8)
        result[name] = {'median_ms_per_run': statistics.median(samples), 'samples': samples}
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--capture', action='store_true')
    p.add_argument('--bench', action='store_true')
    p.add_argument('--repeats', type=int, default=5)
    p.add_argument('--reference')
    p.add_argument('--compare', metavar='COMMIT')
    a = p.parse_args()
    if a.compare:
        rows = {k: {} for k in ('before', 'after')}
        for i in range(a.repeats):
            for label in (('before', 'after') if i % 2 == 0 else ('after', 'before')):
                cmd = [sys.executable, '-X', 'utf8', __file__, '--bench', '--repeats', '1']
                if label == 'before':
                    cmd += ['--reference', a.compare]
                out = subprocess.check_output(cmd, cwd=ROOT, text=True, encoding='utf-8')
                for name, row in json.loads(out[out.index('{'):]).items():
                    rows[label].setdefault(name, []).append(row['median_ms_per_run'])
        print(json.dumps({label: {name: statistics.median(xs) for name, xs in cases.items()}
                          for label, cases in rows.items()}, indent=2))
        return
    if a.capture:
        head = subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(), 'rev-parse', '--short=7', 'HEAD'], cwd=ROOT, text=True).strip()
        assert head == '1197383' and not ORACLE.exists(), 'capture only once at 1197383'
        result = snapshot()
        ORACLE.parent.mkdir(exist_ok=True)
        ORACLE.write_text(json.dumps({'commit': head, 'cases': result}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('captured', len(result) * 3, 'runs')
    else:
        print('identical:', verify(), 'runs')
    if a.bench:
        print(json.dumps(benchmark(a.repeats), indent=2))


if __name__ == '__main__':
    main()
