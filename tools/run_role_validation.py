"""Serial, resumable private policy validation. Native simulations use two workers."""
import argparse
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('account', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        parser.error('private output must be outside the repository')
    output.mkdir(parents=True, exist_ok=True)
    for name in ['rules', 'free', 'B', 'A', 'guild-old', 'guild-new', 'independent', 'small']:
        if (output / (name + '.json')).exists():
            print('existing result:', name, flush=True)
            continue
        if name in ('independent', 'small'):
            cmd = ['node', 'tools/validate_role_search.js', str(args.account), str(output), name]
        else:
            cmd = ['node', 'tools/measure_role_search.js', str(args.account), str(output / (name + '.json')), name]
        start = time.monotonic()
        print('starting:', name, flush=True)
        with (output / (name + '.log')).open('w', encoding='utf8') as log:
            subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        print('completed:', name, 'seconds:', round(time.monotonic()-start), flush=True)


if __name__ == '__main__':
    main()
