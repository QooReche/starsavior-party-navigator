"""Compare native debuff-object counting with legacy; derived metrics only.

python -X utf8 tools/web_leads_audit.py --myinfo PATH --runs 60
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from battlesim.fileio import atomic_text
from ingame_check import low_priority, run, SAMPLES
from battlesim.mc import Battle


def measure(stage, runs, seed, myinfo, legacy):
    casts, damage, chains = Counter(), Counter(), Counter()
    original_cast, original_damage = Battle.cast, Battle.apply_damage

    def cast(b, u, sk, *args, **kw):
        ctx = original_cast(b, u, sk, *args, **kw)
        if ctx is not None and u.d.key == 'cristelle':
            casts[sk.slot] += 1
        return ctx

    def apply_damage(b, a, v, dmg, kind, **kw):
        ctx = getattr(b, '_cast_ctx', None)
        track = (a is not None and a.d.key == 'cristelle' and ctx is not None
                 and ctx.src is a and ctx.skill is not None and kind in ('hit', 'chain'))
        before = a.dmg if track else 0
        result = original_damage(b, a, v, dmg, kind, **kw)
        if track:
            damage[ctx.skill.slot] += a.dmg - before
            if kind == 'chain':
                chains[ctx.skill.slot] += 1
        return result

    with patch.object(Battle, 'cast', cast), patch.object(Battle, 'apply_damage', apply_damage):
        summary = run(stage, runs, {'debuff_instance_count': False} if legacy else {}, seed, True, myinfo)
    per_cast = {slot: damage[slot] / n for slot, n in casts.items() if n}
    return dict(summary=summary, cristelle=dict(
        casts_per_run={k: n / runs for k, n in casts.items()},
        hit_and_chain_per_run={k: n / runs for k, n in damage.items()},
        chains_per_run={k: n / runs for k, n in chains.items()},
        damage_per_cast=per_cast,
        basic_ultimate_ratio=(per_cast.get('기본기', 0) / per_cast['궁극기']
                              if per_cast.get('궁극기') else None)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--myinfo', required=True)
    ap.add_argument('--runs', type=int, default=60)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/web_leads_results.json')
    args = ap.parse_args()
    if args.runs < 1 or not args.output.resolve().is_relative_to(ROOT):
        ap.error('Positive runs and a workspace output path required')
    low_priority()
    files = ['battlesim/mc.py', 'battlesim/rules/default.json', 'rawdata/databook_main.json',
             'data/myinfo_combat.json', 'data/growth.json']
    result = dict(runs=args.runs, seed=args.seed,
                  override_before={'debuff_instance_count': False}, override_after={},
                  sha256={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files},
                  profiles={})
    for profile in ('before', 'after'):
        result['profiles'][profile] = {}
        for stage in SAMPLES:
            row = measure(stage, args.runs, args.seed, args.myinfo, profile == 'before')
            result['profiles'][profile][stage] = row
            print(profile, stage, row['summary']['sim_ratio'], flush=True)
    atomic_text(args.output, json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
