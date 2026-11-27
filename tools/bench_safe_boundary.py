"""Public, standard-build boundary oracle; capture only on 1197383 / CPython 3.12.1 x86.

Copy this tool into a detached 1197383 worktree and run --capture with that
interpreter. Copy only the resulting fixture back. Existing fixtures are never
replaced. --probe accepts a public stage, comma-separated party, and seed.

Reproduce (from a clean repository; <python32> is CPython 3.12.1 x86):
    git worktree add --detach <baseline-worktree> 1197383
    # Copy tools/bench_safe_boundary.py into that worktree's tools/ directory.
    <python32> -X utf8 -I <baseline-worktree>/tools/bench_safe_boundary.py --capture
    # Copy tests/fixtures/safe_boundary_1197383.json back, then remove worktree.
Check: python -X utf8 -I tests/safe_boundary_test.py [--mutations]
"""
import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
import pathlib
import platform
import struct
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import api
from battlesim.mc import Battle
from battlesim.starsavior.data import SRC

ORACLE = ROOT / 'tests/fixtures/safe_boundary_1197383.json'
PARTY = ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle']
REVIVE_PARTY = ['elisa', 'wedding-epindel', 'bunny-charlotte', 'cristelle']
ENDURANCE_PARTY = ['carmen', 'elisa', 'frey', 'serpang']
# Public stage names and standard builds only. No stats overrides or account input.
CASES = [
    {'name': 'revive-sun', 'party': {'units': REVIVE_PARTY, 'leader': 0},
     'encounter': {'stage': 'clo/태양 회랑/FLOOR 250'}, 'seed': 3,
     'requires': ['revive', 'speed_expired']},
    {'name': 'revive-moon', 'party': {'units': REVIVE_PARTY, 'leader': 0},
     'encounter': {'stage': 'clo/달 회랑/FLOOR 250'}, 'seed': 3,
     'requires': ['revive', 'speed_expired']},
    {'name': 'zero-mogulus-2', 'party': {'units': ENDURANCE_PARTY, 'leader': 0},
     'encounter': {'stage': 'cosmo/불사왕 모굴루스/불사왕 모굴루스 2단계'}, 'seed': 3,
     'requires': ['speed_zero', 'speed_fixed_zero', 'speed_expired']},
    {'name': 'zero-mogulus-3', 'party': {'units': PARTY, 'leader': 0},
     'encounter': {'stage': 'cosmo/불사왕 모굴루스/불사왕 모굴루스 3단계'}, 'seed': 3,
     'requires': ['speed_zero', 'speed_fixed_zero', 'speed_expired']},
    {'name': 'sudden-sun', 'party': {'units': ENDURANCE_PARTY, 'leader': 0},
     'encounter': {'stage': 'clo/태양 회랑/FLOOR 230'}, 'seed': 3,
     'requires': ['sudden_transition', 'action_blocked', 'speed_expired']},
    {'name': 'sudden-moon', 'party': {'units': ENDURANCE_PARTY, 'leader': 0},
     'encounter': {'stage': 'clo/달 회랑/FLOOR 230'}, 'seed': 3,
     'requires': ['sudden_transition', 'action_blocked', 'speed_expired']},
]


def bits(value):
    if isinstance(value, float):
        return value.hex()
    if isinstance(value, dict):
        return {k: bits(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [bits(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(bits(value), sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def speed_effect(e):
    return e.speed_zero or any(e.props.get(k) for k in ('속도%', '속도'))


def observe(case):
    """Count actual events, never change combat state or consume RNG.

    speed_zero counts zero-speed living units at pick_next (once per segment,
    independent of E2's number of spd calls). speed_expired counts removed speed
    effects whose duration reached zero while the holder is alive; death,
    dispel and replacement of a still-live effect do not qualify. dirty is the
    common post-removal boundary, including owner/global/any-turn clocks.
    sudden_transition excludes initial installation of level zero.
    action_blocked counts actual skipped actions, separately from zero speed:
    stun/sleep do not themselves force spd() to zero in this engine.
    """
    assert pathlib.Path(SRC).resolve() == ROOT, 'PN_SRC must not redirect public input data'
    events = Counter()
    expired = Counter()
    tracked = {}
    observations = []
    originals = {name: getattr(Battle, name) for name in
                 ('run', 'dirty', 'pick_next', '_sudden_step', 'log')}

    def log(b, **kw):
        if kw.get('skip') == '행동 불가':
            events['action_blocked'] += 1
        if 'revive' in kw:
            events['revive'] += 1
        return originals['log'](b, **kw)

    def dirty(b, u):
        result = originals['dirty'](b, u)
        for name, e in tracked.get(u, {}).items():
            if u.eff.get(name) is not e and e.dur <= 0 and not u.dead:
                events['speed_expired'] += 1
                expired[name] += 1
        tracked[u] = {n: e for n, e in u.eff.items() if speed_effect(e) and e.stacks > 0}
        return result

    def pick(b, living, *args, **kwargs):
        for u in living:
            if u.spd() == 0:
                events['speed_zero'] += 1
                if u.zero_stats or any(e.speed_zero and e.stacks > 0 for e in u.eff.values()):
                    events['speed_fixed_zero'] += 1
        return originals['pick_next'](b, living, *args, **kwargs)

    def sudden(b):
        before = b.sd_level
        result = originals['_sudden_step'](b)
        if before >= 0 and b.sd_level > before:
            events['sudden_transition'] += 1
        return result

    def run(b):
        result = originals['run'](b)
        assert events['revive'] == b.rule_hits['revive_toughness']
        state = [b.rng.getstate(), [[getattr(u, k) for k in
                 ('hp', 'gauge', 'dmg', 'taken', 'actions', 'dead', 'cd')]
                 for u in b.allies + b.all_foes]]
        observations.append({'waves': b.wave_i + 1, 'summons': b.rule_hits['summon'],
                             'actions': b.global_turns, 'progress': b.progress(),
                             'via': b.ally_via, 'state': digest(state),
                             'events': {k: events[k] for k in ('revive', 'speed_zero',
                                 'speed_fixed_zero', 'action_blocked', 'speed_expired', 'sudden_transition')},
                             'expired_effects': dict(expired)})
        return result

    with ExitStack() as stack:
        for name, method in [('run', run), ('dirty', dirty), ('pick_next', pick),
                             ('_sudden_step', sudden), ('log', log)]:
            stack.enter_context(patch.object(Battle, name, method))
        response = api.simulate(case['party'], case['encounter'],
                                {'build': 'standard', 'seed': case['seed'], 'n_runs': 1,
                                 'per_run': True, 'raw_runs': True, **case.get('options', {})})
    assert len(observations) == 1, response
    response.pop('runtime_ms_per_run', None)
    return {'sha256': digest(response), 'raw': response.get('raw_runs'), 'coverage': observations[0]}


def snapshot():
    return {case['name']: observe(case) for case in CASES}


def check_events(case, row):
    assert row['coverage']['actions'] > 0, case['name']
    assert row['coverage']['progress'] > 0, case['name']
    for event in case['requires']:
        assert row['coverage']['events'][event] > 0, (case['name'], event)


def check_row(case, row, expected):
    check_events(case, row)
    assert row == expected, '1197383 mismatch: ' + case['name']


def read_oracle():
    expected = json.loads(ORACLE.read_text(encoding='utf-8'))
    assert expected['commit'] == '1197383'
    assert expected['generator'] == 'CPython 3.12.1 32-bit (hash width 32)'
    assert expected['inputs'] == CASES, 'oracle inputs changed'
    assert set(expected['cases']) == {case['name'] for case in CASES}
    return expected['cases']


def verify():
    expected = read_oracle()
    actual = snapshot()
    for case in CASES:
        check_row(case, actual[case['name']], expected[case['name']])
    return len(actual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--probe', metavar='PUBLIC_STAGE')
    parser.add_argument('--party', default=','.join(PARTY))
    parser.add_argument('--seed', type=int, default=1)
    args = parser.parse_args()
    if args.probe:
        case = dict(party={'units': args.party.split(','), 'leader': 0},
                    encounter={'stage': args.probe}, seed=args.seed)
        print(json.dumps(observe(case), ensure_ascii=False, indent=2))
    elif args.capture:
        head = subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(),
                                        'rev-parse', '--short=7', 'HEAD'], cwd=ROOT, text=True).strip()
        assert head == '1197383', 'capture requires detached 1197383'
        assert platform.python_implementation() == 'CPython' and platform.python_version() == '3.12.1'
        assert struct.calcsize('P') == 4 and sys.hash_info.width == 32, 'capture requires 32-bit CPython'
        assert not ORACLE.exists(), 'existing oracle is immutable'
        subprocess.run(['git', '-c', 'safe.directory=' + ROOT.as_posix(), 'diff',
                        '--exit-code', 'HEAD', '--', 'battlesim', 'data', 'rawdata'],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        assert CASES, 'no boundary cases'
        data = {'commit': head, 'generator': 'CPython 3.12.1 32-bit (hash width 32)',
                'inputs': CASES, 'cases': snapshot()}
        for case in CASES:
            check_events(case, data['cases'][case['name']])
        with ORACLE.open('x', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        print('captured', len(CASES), 'runs')
    else:
        start = time.perf_counter()
        print('PASS:', verify(), 'runs; %.3fs' % (time.perf_counter() - start))


if __name__ == '__main__':
    main()
