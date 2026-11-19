"""Sequential current-season quality comparison; synthetic public standard roster only.

python -X utf8 -I tools/bench_cosmo_learned.py --workers 4
Raw output stays in local/. No legacy 59-unit search is run.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bench_cosmo_search import catalog


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workers', type=int, default=4, choices=range(1, 5))
    ap.add_argument('--output', default='local/cosmo-learned')
    ap.add_argument('--sizes', default='20,26,32,59')
    ap.add_argument('--seeds', default='0,1')
    a = ap.parse_args()
    out = ROOT / a.output
    out.mkdir(parents=True, exist_ok=True)
    (out / 'catalog.json').write_text(json.dumps(catalog(), ensure_ascii=False), encoding='utf8')
    subprocess.run(['node', str(ROOT / 'tools/bench_cosmo_learned.js'), str(out), str(a.workers), sys.executable,
                    a.sizes, a.seeds], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
