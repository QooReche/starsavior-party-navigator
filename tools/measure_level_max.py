"""표준 육성 모굴루스·괴리 Step3 중첩 수정 영향(계정 입력 없음, 순차 실행)."""
import argparse
import json
import statistics
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.api import simulate
from battlesim.mc import Battle

PARTY = ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runs', type=int, default=20)
    ap.add_argument('--out', default='local/level_max_impact.json')
    args = ap.parse_args()
    rows = []
    original = Battle.add_effect
    for boss, name in [('mogulus', '보주의 축성'), ('disparity', '기억의 증폭')]:
        for level in (8, 18):
            for mode in ('legacy', 'client'):
                stacks = [0]
                def observed(b, owner, target, eff, ctx, *a, **kw):
                    result = original(b, owner, target, eff, ctx, *a, **kw)
                    if eff.get('name') == name and name in target.eff:
                        stacks[0] = max(stacks[0], target.eff[name].stacks)
                    return result
                with patch.object(Battle, 'add_effect', observed):
                    r = simulate(PARTY, {'cosmo_raid': {'boss': boss, 'step': 3, 'level': level}},
                                 {'build': 'standard', 'n_runs': args.runs, 'seed': 7,
                                  'break_skill': {'name': '행성 정화', 'level': 1},
                                  'rules_override': {'level_max_source': mode}})
                assert r['outcome']['progress'] > 0, (boss, level, mode)
                assert stacks[0] > 0, (boss, level, mode)
                row = dict(boss=boss, level=level, mode=mode, runs=args.runs,
                           clear=r['outcome']['clear_p'], progress=r['outcome']['progress'],
                           mean_score=round(statistics.fmean(r['cosmo_raid']['score_runs']), 2),
                           max_stacks=stacks[0], runtime=r['unsupported']['runtime'])
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(party=PARTY, build='standard', seed=7,
                                   break_skill='행성 정화 Lv1', rows=rows), ensure_ascii=False, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
