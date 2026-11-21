"""Read-only combat diagnostics. Private inputs/results must stay outside the repo.

One hit below means one skill/target damage calculation, not an animation tick.
Uses ingame_check's exact input, seed, and real break skill selection.
"""
import argparse
from collections import defaultdict
from contextlib import ExitStack
import json
from pathlib import Path
import statistics
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import ingame_check as check
from battlesim.mc import Battle


def measure(stage, runs, seed, myinfo, override=None):
    original = {k: getattr(Battle, k) for k in ('run', 'final_dmg', 'log', 'cast', 'act')}
    trials, hits, casts = [], [], []

    def turn(b):
        return sum(u.actions for u in b.allies + b.all_foes)

    def act(b, u):
        b._audit_selected_turn = turn(b) + 1
        return original['act'](b, u)

    def final(b, a, v, base, ctx, crit, cdv, pen, r, hctx):
        damage = original['final_dmg'](b, a, v, base, ctx, crit, cdv, pen, r, hctx)
        local = hctx.local[v]['defp'] if hctx is not None and hctx.local is not None else 0
        hits.append(dict(run=len(trials), wave=b.wave_i, turn=getattr(b, '_audit_selected_turn', 0), source=a.name, side=a.side,
                         pos=a.pos, target=v.name, target_pos=v.pos,
                         slot=ctx.skill.slot, skill=ctx.skill.name, via=ctx.via,
                         damage=damage, base=base, attack=b.atk_stat(a, ctx),
                         penalty=b.pen[a.side], defense=b.def_stat(v, local),
                         reduction=dict(v.mods()['red']), buffs=list(v.eff),
                         shield=v.shield_total(), broken=v.broken, critical=bool(crit),
                         evaded=bool(hctx is not None and v in hctx.evaded)))
        return damage

    def cast(b, u, sk, *args, **kwargs):
        row = dict(run=len(trials), wave=b.wave_i, turn=getattr(b, '_audit_selected_turn', 0),
                   source=u.name, side=u.side, pos=u.pos, slot=sk.slot,
                   skill=sk.name, via=kwargs.get('via'), speed=u.spd())
        casts.append(row)
        result = original['cast'](b, u, sk, *args, **kwargs)
        row['accepted'] = result is not None
        if result is not None:
            row.update(slot=result.skill.slot, skill=result.skill.name, via=result.via)
        return result

    def log(b, **kw):
        if 'bskill' in kw or 'brk' in kw:
            b.__dict__.setdefault('_audit_events', []).append(
                dict(turn=getattr(b, '_audit_selected_turn', 0), **kw))
        return original['log'](b, **kw)

    def run(b):
        result = original['run'](b)
        units = {f'{u.name}#{u.pos}': dict(dealt=u.dmg_stat, taken=u.taken_stat,
                 heal=u.healed_raw, heal_effective=u.healed, shield=u.shield_given,
                 actions=u.actions, casts=dict(u.cast_count)) for u in b.allies}
        total = turn(b)
        ally = sum(u.actions for u in b.allies)
        dealt = sum(u.dmg_stat for u in b.allies)
        taken = sum(u.taken_stat for u in b.allies)
        trials.append(dict(result=b.result, actions=total, ally_actions=ally,
                           dealt=dealt, taken=taken, taken_per_turn=taken / total,
                           dealt_per_turn=dealt / total, dealt_per_ally=dealt / ally,
                           units=units, events=b.__dict__.get('_audit_events', [])))
        return result

    with ExitStack() as scope:
        for name, fn in dict(run=run, final_dmg=final, log=log, cast=cast, act=act).items():
            scope.enter_context(patch.object(Battle, name, fn))
        summary = check.run(stage, runs, override, seed, myinfo=myinfo, bs_real=True)
    assert len(trials) == runs
    grouped = defaultdict(list)
    for hit in hits:
        key = tuple(hit[k] for k in ('wave', 'source', 'pos', 'skill', 'target', 'target_pos', 'critical', 'evaded'))
        grouped[key].append(hit['damage'])
    skill_damage = [dict(zip(('wave', 'source', 'pos', 'skill', 'target', 'target_pos', 'critical', 'evaded'), key),
                        calculations=len(values), per_run=len(values) / runs,
                        damage_q05_50_95=check._q(values, (.05, .5, .95)))
                    for key, values in grouped.items()]
    return dict(summary=summary, trials=trials, hits=hits, casts=casts, skill_damage=skill_damage,
                hit_definition='final_dmg calculation; includes shared/recomputed pieces')


def compare(trials, observations):
    """Marginal empirical percentiles, not a joint goodness-of-fit test.

    Unknown/blurred observations are omitted or null. Damage is result-screen
    damage. No ally action count is inferred from a simulation when comparing.
    """
    def flatten(row):
        out = {k: row[k] for k in ('actions', 'dealt', 'taken') if row.get(k) is not None}
        for name, unit in row.get('units', {}).items():
            out.update({name + '/' + k: v for k, v in unit.items()
                        if k in ('dealt', 'taken', 'heal', 'shield', 'actions') and v is not None})
        if row.get('actions'):
            for k in ('dealt', 'taken'):
                if row.get(k) is not None:
                    out[k + '_per_turn'] = row[k] / row['actions']
        return out
    obs = [flatten(r) for r in observations]
    result = {}
    for label, rows in (('all', trials), ('lost', [r for r in trials if r['result'] != 'clear'])):
        sim = [flatten(r) for r in rows]
        metrics = {}
        for key in sorted({k for r in obs for k in r}):
            xs = sorted(r[key] for r in sim if key in r)
            ys = [r[key] for r in obs if key in r]
            if not xs or not ys:
                continue
            real_mean = statistics.mean(ys)
            metrics[key] = dict(n=len(xs), observed_n=len(ys),
                observed_indices=[i + 1 for i, r in enumerate(obs) if key in r],
                sim_q05_50_95=check._q(xs, (.05, .5, .95)),
                sim_over_real_mean=statistics.mean(xs) / real_mean if real_mean else None,
                observed_percentiles=[sum(x <= y for x in xs) / len(xs) for y in ys])
        result[label] = metrics
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only', choices=check.SAMPLES, default='op4212')
    p.add_argument('--myinfo', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runs', type=int, default=200)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--ov', type=json.loads)
    p.add_argument('--observations', type=Path, help='Private JSON array; uncertain values omitted/null')
    a = p.parse_args()
    if a.runs < 1:
        p.error('--runs must be positive')
    if a.output.resolve().is_relative_to(ROOT):
        p.error('Private results must be outside the repository')
    inputs = [Path(a.myinfo)] + ([a.observations] if a.observations else [])
    if any(a.output.resolve() == source.resolve() for source in inputs):
        p.error('Output must not overwrite an input file')
    check.low_priority()
    out = measure(a.only, a.runs, a.seed, a.myinfo, a.ov)
    if a.observations:
        out['comparison'] = compare(out['trials'], json.loads(a.observations.read_text(encoding='utf-8-sig')))
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved private diagnostics:', a.output)


if __name__ == '__main__':
    main()
