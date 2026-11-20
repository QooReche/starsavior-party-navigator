"""Standard-build before/after samples; private output stays in local/unsup."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.api import simulate

KEYS = ('sunshine-cat-smile', 'gille', 'bunny-claire@개화(SSR)',
        'scarlet', 'vera', 'vera@개화(SSR)')


def main():
    mode = sys.argv[1]
    out = ROOT / 'local' / 'unsup'
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for key in KEYS:
        for stage in ('mogulus', 'disparity', 'baskerville', 'sun'):
            enc = ({'stage': 'clo/태양 회랑/FLOOR 250'} if stage == 'sun' else
                   {'cosmo_raid': {'boss': stage, 'step': 1, 'level': 0}})
            r = simulate([key, 'gwen', 'amora', 'frey'], enc,
                         {'build': 'standard', 'n_runs': 8, 'seed': 20261120})
            assert r['outcome']['progress'] > 0, (key, stage)
            scores = r.get('cosmo_raid', {}).get('score_runs')
            rows.append(dict(key=key, stage=stage, outcome=r['outcome'],
                             score=sum(scores)/len(scores) if scores else None,
                             unsupported=r['unsupported'], per_unit=r['per_unit']))
            print(key, stage, r['outcome']['clear_p'], rows[-1]['score'], flush=True)
    (out / (mode + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
