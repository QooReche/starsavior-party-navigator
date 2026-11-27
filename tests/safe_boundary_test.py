"""Public boundary runs against the immutable 1197383 / CPython 3.12.1 x86 oracle.

--mutations reverses E1's living order in memory, proves every selected case
fails the same oracle assertion, and restores the method even on failure.
"""
from collections import Counter
import pathlib
import struct
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
from bench_safe_boundary import (Battle, CASES, api, check_row, digest,
                                 observe, read_oracle, snapshot)

MUTATIONS = '--mutations' in sys.argv
if MUTATIONS:
    sys.argv.remove('--mutations')


class SafeBoundary(unittest.TestCase):
    def test_1197383_and_events(self):
        expected = read_oracle()
        required = Counter(event for case in CASES for event in case['requires'])
        for event in ('revive', 'speed_zero', 'speed_fixed_zero', 'action_blocked',
                      'speed_expired', 'sudden_transition'):
            self.assertGreaterEqual(required[event], 2, event)
        for case in CASES:
            with self.subTest(case=case['name']):
                check_row(case, observe(case), expected[case['name']])

    def test_observation_preserves_response(self):
        # Extra spd() calls populate caches; prove instrumentation itself does
        # not perturb RNG, ordering, the response, or any raw floating bits.
        for case in CASES:
            with self.subTest(case=case['name']):
                observed = observe(case)
                response = api.simulate(case['party'], case['encounter'],
                                        {'build': 'standard', 'seed': case['seed'],
                                         'n_runs': 1, 'per_run': True, 'raw_runs': True})
                response.pop('runtime_ms_per_run', None)
                self.assertEqual(digest(response), observed['sha256'])

    @unittest.skipUnless(MUTATIONS, 'opt-in mutation check')
    def test_e1_reversed_living_order_is_rejected(self):
        expected = read_oracle()
        original = Battle.alive
        with patch.object(Battle, 'alive', lambda b, side: original(b, side)[::-1]):
            for case in CASES:
                with self.subTest(case=case['name']):
                    row = observe(case)
                    good = expected[case['name']]
                    # Failure must affect combat, not just event accounting.
                    self.assertNotEqual(row['sha256'], good['sha256'])
                    self.assertNotEqual(row['coverage']['state'], good['coverage']['state'])
                    with self.assertRaises(AssertionError):
                        check_row(case, row, good)
        self.assertIs(Battle.alive, original)
        self.assertEqual(snapshot(), expected, 'mutation leaked into normal engine')


if __name__ == '__main__':
    start = time.perf_counter()
    result = unittest.main(exit=False).result
    print('safe boundary: %d runs, %d-bit Python, %.3fs' %
          (len(CASES), struct.calcsize('P') * 8, time.perf_counter() - start))
    sys.exit(not result.wasSuccessful())
