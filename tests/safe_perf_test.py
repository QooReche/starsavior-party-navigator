"""Immutable single-run oracle captured at deployment 1197383."""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
from bench_safe_perf import verify

if __name__ == '__main__':
    print('PASS:', verify(), 'runs byte-identical to 1197383 (excluding timing)')
