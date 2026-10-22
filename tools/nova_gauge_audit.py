"""Aggregate nova audit; private myinfo is read in place, never copied."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import ingame_check as check
from received_damage_audit import measure
from battlesim.mc import Battle, RX_SHIELD


def audit_measure(stage, runs, seed, myinfo, override=None):
    """Attribute support to recipients as well as the original source totals."""
    support = defaultdict(Counter)
    original_heal, original_special = Battle.heal, Battle.run_special

    def heal(b, src, target, amount, give):
        actual = original_heal(b, src, target, amount, give)
        if target.side == 0:
            support[target.name]['heal_received'] += actual
        return actual

    def special(b, owner, ln, ctx, rest):
        shield = RX_SHIELD.match(rest)
        before = {u: u.shield_total() for u in b.allies} if shield else {}
        result = original_special(b, owner, ln, ctx, rest)
        for u, amount in before.items():
            support[u.name]['shield_received'] += u.shield_total() - amount
        return result

    with patch.object(Battle, 'heal', heal), patch.object(Battle, 'run_special', special):
        result = measure(stage, runs, seed, myinfo, override)
    for name, target in result['targets'].items():
        target.update({k: support[name][k] / runs for k in ('heal_received', 'shield_received')})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--myinfo', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runs', type=int, default=60)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--ov', type=json.loads, default={})
    args = p.parse_args()
    if args.runs < 1 or not args.output.resolve().is_relative_to(ROOT):
        p.error('Positive runs and a workspace output are required')
    check.low_priority()
    results = {}
    for stage, policy in [('36-36', 'auto'), ('36-36', 'heal')] + [
            (s, 'auto') for s in check.SAMPLES if s != '36-36']:
        r = audit_measure(stage, args.runs, args.seed, args.myinfo,
                          dict(args.ov, nova_policy=policy))
        summary = r['summary']
        summary['bursts_per_run'] = summary['nova_burst']['total'] / args.runs
        results[stage + '/' + policy] = dict(summary=summary, targets=r['targets'], casts=r['casts'])
        print(stage, policy, summary['sim_ratio'], summary['bursts_per_run'], flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
