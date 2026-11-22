"""Public standard-build samples. No account input; output is ignored local data.

python -X utf8 -I tools/measure_casebook.py LABEL    # local/casebook/LABEL.json
옛 --legacy(지운 스위치 fixstats_speed_zero·speed_min)는 11/22 코드째 삭제 — 태그 engine-legacy-final 에만 있음.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import simulate
from battlesim.starsavior import cosmo_raid as C

TEAM = ['asherah-order-striker', 'gille', 'haydee', 'ceres']
HEAL = ['asherah-order-striker', 'gille', 'amora', 'wedding-carmen']


def main():
    rows = []
    scenarios = [(f'mogulus-{step}-{level}', TEAM,
                  {'cosmo_raid': {'boss': 'mogulus', 'step': step, 'level': level}})
                 for step, level in ((1, 0), (3, 0), (3, 18))]
    scenarios += [(f'sun-{floor}', HEAL, {'stage': f'clo/태양 회랑/FLOOR {floor}'})
                  for floor in (200, 250)]
    scenarios += [('baskerville', HEAL, {'cosmo_raid': {'boss': 'baskerville', 'step': 3, 'level': 0}})]
    scenarios += [('tyria', ['gwen', 'fei', 'smile', 'luna'],
                   {'cosmo_raid': {'boss': 'tyria', 'step': 3, 'level': 18}})]
    for name, party, encounter in scenarios:
        old = C._DATA_FILE
        opts = {'build': 'standard', 'n_runs': 8, 'seed': 20261121}
        try:
            if name == 'tyria':
                C.use_data(str(ROOT / 'tests/fixtures/cosmo_raid_1022.json'))
            r = simulate(party, encounter, opts)
        finally:
            C.use_data(old)
        assert r['outcome']['progress'] > 0, name
        scores = r.get('cosmo_raid', {}).get('score_runs')
        row = dict(name=name, party=party, encounter=encounter, outcome=r['outcome'],
                   score=sum(scores) / len(scores) if scores else None,
                   per_unit=r['per_unit'], unsupported=r['unsupported'])
        rows.append(row)
        print(name, row['outcome']['progress'], row['outcome']['clear_p'], row['score'], flush=True)
    dest = ROOT / 'local' / 'casebook'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / (sys.argv[1] + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
