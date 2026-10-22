"""Compare combat adapter on/off; export aggregate battle metrics, never account data."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from ingame_check import low_priority, run, SAMPLES

FIELDS = ('stage', 'runs', 'seed', 'real_ratio', 'sim_ratio', 'sim_clear', 'real_turn',
          'sim_ally_actions', 'sim_enemy_actions', 'sim_boss_actions', 'sim_total_actions',
          'sim_total_actions_vs_turn', 'sim_dealt', 'sim_taken', 'heal', 'foe_breaks', 'ally_breaks',
          'sim_dealt_per_ally_action', 'estimated_ally_damage_ratio')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--myinfo', required=True)
    ap.add_argument('--runs', type=int, default=60)
    args = ap.parse_args()
    if args.runs < 1:
        ap.error('runs must be positive')
    low_priority()
    out = dict(seed=7, runs=args.runs, break_skill='큐브 과부하 Lv5', profiles={})
    for label, enabled in [('before', False), ('after', True)]:
        result = []
        for name in SAMPLES:
            r = run(name, args.runs, {'myinfo_combat': enabled}, seed=7, bs=True, myinfo=args.myinfo)
            result.append({k: r[k] for k in FIELDS})
            print(label, name, 'ratio', r['sim_ratio'], 'clear', r['sim_clear'], flush=True)
        out['profiles'][label] = result
    (ROOT / 'docs/myinfo_combat_results.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
