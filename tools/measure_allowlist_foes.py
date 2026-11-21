"""Public standard-build foe regression samples; no account input."""
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    label = sys.argv[1]
    base = ROOT
    if '--revision' in sys.argv:
        rev = sys.argv[sys.argv.index('--revision') + 1]
        base = ROOT / 'local' / 'allow-e2' / rev
        base.mkdir(parents=True, exist_ok=True)
        archive = base.parent / (rev + '.zip')
        subprocess.run(['git', 'archive', '--format=zip', '-o', str(archive), rev,
                        'battlesim', 'data', 'rawdata', 'party_contents.json'], cwd=ROOT, check=True)
        with zipfile.ZipFile(archive) as z:
            z.extractall(base)
    sys.path.insert(0, str(base))
    from battlesim import simulate
    from battlesim.mc import Battle
    counts = []
    original = Battle.run

    def run(b):
        result = original(b)
        counts.append({u.d.name: sum(v.actions for v in b.all_foes if v.d.name == u.d.name)
                       for u in b.all_foes})
        return result

    Battle.run = run
    team = ['asherah-order-striker', 'gille', 'amora', 'wedding-carmen']
    rows = []
    for tab in ('심해의 폭군', '티엔'):
        for stage in [f'길드 방어전 {i}단계' for i in range(1, 7)] + ['길드 방어전 EX스테이지']:
            counts.clear()
            encounter = f'guild/{tab}/{stage}'
            r = simulate(team, {'stage': encounter}, {'build': 'standard', 'n_runs': 8, 'seed': 20261121})
            assert r['outcome']['progress'] > 0, encounter
            row = dict(stage=encounter, party=team, outcome=r['outcome'], actions=list(counts), foes=r['foes'])
            rows.append(row)
            print(encounter, r['outcome']['clear_p'], r['outcome']['progress'], counts, flush=True)
    dest = ROOT / 'local' / 'allow-e2'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / (label + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
