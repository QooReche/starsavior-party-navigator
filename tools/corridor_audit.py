"""Observe one ingame_check battle; private inputs are read only."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import ingame_check as check
from battlesim.mc import Battle


def trace(myinfo, override=None):
    original_init, original_run = Battle.__init__, Battle.run
    original_log, original_damage = Battle.log, Battle.apply_damage
    original_strike = Battle.strike
    captured = []

    def init(b, *args, **kwargs):
        kwargs['timeline'] = True
        original_init(b, *args, **kwargs)

    def run(b):
        result = original_run(b)
        captured.append(dict(timeline=b.timeline, units=[
            dict(name=u.name, side=u.side, damage=u.dmg, taken=u.taken,
                 casts=dict(u.cast_count)) for u in b.allies + b.all_foes]))
        return result

    def log(b, **kwargs):
        kwargs.setdefault('global_turn', b.global_turns)
        kwargs['wave'] = b.wave_i + 1
        original_log(b, **kwargs)

    def damage(b, a, v, amount, kind, **kwargs):
        before = v.taken
        ctx = getattr(b, '_cast_ctx', None)
        result = original_damage(b, a, v, amount, kind, **kwargs)
        b.log(damage_from=a.name if a else None, target=v.name, kind=kind,
              amount=v.taken-before, skill=ctx.skill.name if ctx else None,
              via=ctx.via if ctx else None)
        return result

    def strike(b, a, v, base, ctx, crit, cdv, pen, reactions, evaded=False):
        b.log(hit_from=a.name, target=v.name, skill=ctx.skill.name,
              critical=crit, evaded=evaded, accuracy=a.mods()['acc'], via=ctx.via)
        return original_strike(b, a, v, base, ctx, crit, cdv, pen, reactions, evaded)

    with patch.object(Battle, '__init__', init), patch.object(Battle, 'run', run), \
            patch.object(Battle, 'log', log), patch.object(Battle, 'apply_damage', damage), \
            patch.object(Battle, 'strike', strike):
        result = check.run('corr-a', runs=1, myinfo=myinfo, bs_real=True, ov=override)
    # Account diagnostics and stat inputs are intentionally not exported.
    return dict(summary={k: result[k] for k in ('sim_clear', 'sim_dealt', 'sim_taken', 'per_unit')},
                battles=captured)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--myinfo', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--ov', type=json.loads)
    args = p.parse_args()
    check.low_priority()
    Path(args.output).write_text(json.dumps(trace(args.myinfo, args.ov), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
