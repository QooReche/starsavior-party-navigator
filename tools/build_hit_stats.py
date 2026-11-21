"""Connect public enemy base stats to PC HIT/EVADE, without guessing by name.

The name and all ten published base stats must match, and every matching client
row must agree on the two missing stats. Ambiguity/missing rows fail the build.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.tables import jsonc
from battlesim.starsavior.foe import load_foe, SK_NST
from battlesim.starsavior.hit_stats import signature   # 엔진과 같은 열쇠(한 벌)


def build(tables, raw):
    tables = Path(tables)
    rows = lambda name: jsonc(tables / ('CLIENT_' + name + '.json'))['Data']
    strings = {key: r['Value'] for r in jsonc(tables / 'hard/STRING_COMMON.json')['Data']
               for key in ([r['Key']] if r.get('Key') else r.get('Keys', []))}
    stats = {r['m_StatStrID']: r['m_StatData'] for n in (1, 2)
             for r in rows(f'UNIT_STAT_TEMPLET{n}')}
    candidates = defaultdict(set)
    for n in (1, 2, 3, 4):
        for unit in rows(f'UNIT_TEMPLET_BASE{n}'):
            stat = stats.get(unit.get('m_StatStrID'))
            name = strings.get(unit.get('m_UnitNameString'))
            if stat is not None and name:
                key = signature(name, [stat.get(k, 0) for k in SK_NST])
                candidates[key].add((stat.get('NST_RATE_HIT', 0), stat.get('NST_RATE_EVADE', 0)))
    out = {}
    for unit in raw['u']:
        key = signature(unit['n'], unit['b'])
        rates = candidates.get(key, set())
        if len(rates) != 1:
            raise ValueError(f"{unit['n']}: HIT/EVADE mapping missing or ambiguous: {rates}")
        out[key] = list(next(iter(rates)))
    return dict(sorted(out.items()))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tables', type=Path, required=True)
    args = ap.parse_args()
    out = build(args.tables, load_foe())
    (ROOT / 'data/hit_stats.json').write_text(json.dumps(
        {'_note': 'PC 26752678. 이름+기본 스탯 지문별 [명중, 회피], 만분율. tools/build_hit_stats.py',
         'units': out}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('HIT/EVADE:', len(out))
