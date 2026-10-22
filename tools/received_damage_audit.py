"""보관 도구: 적·스킬·대상별 피해 분해와 video_comparison 독립 재현용임.
입력: --myinfo로 지정한 계정 자료를 제자리에서 읽음. 원본 복사 없이 집계만 출력함.
근거: docs/received_damage_audit.md, docs/ingame_samples.md.
실행: python -X utf8 -I tools/received_damage_audit.py --myinfo <경로> --output local/received.json
"""
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from battlesim.fileio import atomic_text
import ingame_check as check
from battlesim.mc import Battle


def measure(stage, runs, seed, myinfo, override=None):
    original = {k: getattr(Battle, k) for k in
                ('deal', 'exec_line', 'apply_damage', 'final_dmg', 'run',
                 'skill_targets', 'roll_hit')}
    totals = defaultdict(Counter)
    units = defaultdict(Counter)
    targeting = defaultdict(Counter)
    taunts = defaultdict(Counter)
    casts = defaultdict(Counter)
    stack, first_hits = [], []
    serial = 0
    pending = None

    def targets(b, u, sk, target=None):
        result = original['skill_targets'](b, u, sk, target)
        if u.side == 1 and sk.is_attack:
            taunt = u.eff.get('도발')
            forced = bool(taunt and taunt.stacks > 0 and target is taunt.src
                          and not target.dead and sk.slot == '기본기' and u.acting)
            for v in result:
                targeting[b.wave_i, u.name, u.pos, sk.name, v.name].update(
                    aoe=int(bool(sk.all)), single=int(not sk.all),
                    taunted=int(forced))
        return result

    def roll_hit(b, owner, ctx, x, name):
        result = original['roll_hit'](b, owner, ctx, x, name)
        if name == '도발':
            taunts[b.wave_i, owner.name, x.name, x.pos].update(
                checks=1, passed=int(result), rejected=int(not result),
                immune=int(name in getattr(x.d, 'immune', ())))
        return result

    def deal(b, a, ctx):
        stack.append((a, ctx.skill.name))
        try:
            return original['deal'](b, a, ctx)
        finally:
            stack.pop()

    def line(b, a, ln, ctx):
        # Parsed public databook description, never decompiled source text.
        stack.append((a, ln.raw))
        try:
            return original['exec_line'](b, a, ln, ctx)
        finally:
            stack.pop()

    def final(b, a, v, base, ctx, crit, cdv, pen, r, hctx):
        nonlocal pending
        result = original['final_dmg'](b, a, v, base, ctx, crit, cdv, pen, r, hctx)
        if v.side == 0:
            local = hctx.local[v]['defp'] if hctx is not None and hctx.local is not None else 0
            pending = dict(target=v.name, source=a.name, skill=ctx.skill.name,
                           defense=b.def_stat(v, local), crit=crit, broken=v.broken,
                           base=base, incoming=result, tick=b.t)
        return result

    def apply(b, a, v, dmg, kind, shieldable=True):
        nonlocal pending
        hp, taken, shield = v.hp, v.taken, v.shield_total()
        # Death clears even an unused shield (e.g. lethal DoT). That is not
        # absorption. Count only the shields apply_damage can actually spend.
        usable = sum(e.shield for e in v.eff.values() if e.shield > 0
                     and not (v.buff_blocked() and not e.harmful))
        absorbed = min(max(0, dmg), usable) if shieldable and not v.dead else 0
        info, pending = pending, None
        result = original['apply_damage'](b, a, v, dmg, kind, shieldable)
        if v.side != 0:
            return result
        source = next((label for actor, label in reversed(stack) if actor is a), kind)
        if kind == 'dot':
            # This frame's effect name is diagnostic only, never affects combat.
            source = sys._getframe(1).f_locals.get('name', 'dot')
        key = (b.wave_i, a.name if a else 'environment', a.pos if a else -1, source, kind, v.name)
        c = totals[key]
        actual = v.taken - taken
        c.update(hits=1, incoming=dmg, taken=actual, absorbed=absorbed,
                 hp_loss=actual-absorbed, net_hp_loss=hp-v.hp,
                 discarded_shield=max(0, shield-v.shield_total()-absorbed),
                 excess_or_limited=max(0, dmg-actual))
        if info and kind in ('hit', 'guard'):
            c['critical_hits'] += info['crit']
            if serial == 0:
                first_hits.append(dict(info, kind=kind, taken=actual, absorbed=absorbed))
        return result

    def run(b):
        nonlocal serial
        result = original['run'](b)
        for u in b.allies:
            units[u.name].update(taken=u.taken, heal_given=u.healed,
                                 shield_given=u.shield_given, actions=u.actions,
                                 end_hp=u.hp, max_hp=u.maxhp, deaths=u.dead)
            casts[u.name].update(u.cast_count)
        serial += 1
        return result

    with ExitStack() as scope:
        for name, fn in dict(deal=deal, exec_line=line, final_dmg=final, apply_damage=apply,
                             run=run, skill_targets=targets, roll_hit=roll_hit).items():
            scope.enter_context(patch.object(Battle, name, fn))
        result = check.run(stage, runs, override, seed, True, myinfo)
    rows = [dict(wave=k[0], enemy=k[1], pos=k[2], source=k[3], kind=k[4], target=k[5],
                 **{field: value / runs for field, value in v.items()})
            for k, v in sorted(totals.items())]
    assert abs(sum(r['taken'] for r in rows) - sum(v['taken'] for v in units.values()) / runs) < 1e-6
    assert abs(sum(r['taken'] for r in rows) - result['sim_taken']) <= len(units) * .5
    total = sum(v['taken'] for v in units.values())
    return dict(summary=result, damage=rows, first_seed_hits=first_hits,
                targeting=[dict(wave=k[0], enemy=k[1], pos=k[2], skill=k[3], target=k[4],
                                **{f: x / runs for f, x in v.items()})
                           for k, v in sorted(targeting.items())],
                taunts=[dict(wave=k[0], caster=k[1], target=k[2], pos=k[3],
                             **{f: x / runs for f, x in v.items()})
                        for k, v in sorted(taunts.items())],
                casts={k: {f: x / runs for f, x in v.items()} for k, v in casts.items()},
                targets={k: dict(**{f: x / runs for f, x in v.items()},
                                 taken_share=v['taken'] / total if total else 0)
                         for k, v in units.items()})


def video_comparison(runs=60):
    """Recreate the documented 382k standard build, not the user's myinfo.

    Guard pieces must be summed per cast: Haydee receives her own hit plus
    three shared pieces. Her floating total is not one ordinary target hit.
    """
    import toughness_check
    from battlesim import rules
    original = Battle.final_dmg
    rows = defaultdict(Counter)
    defenses = defaultdict(set)

    def final(b, a, v, base, ctx, crit, cdv, pen, r, hctx):
        result = original(b, a, v, base, ctx, crit, cdv, pen, r, hctx)
        if a.side == 1 and a.d.boss:
            if not hasattr(b, '_video_first'):
                b._video_first = ctx
            if b._video_first is ctx:
                part = 'direct' if v is ctx.target else 'guard'
                rows[v.name][part] += result
                local = hctx.local[v]['defp'] if hctx and hctx.local is not None else 0
                defenses[v.name].add(b.def_stat(v, local))
        return result

    with patch.object(Battle, 'final_dmg', final), patch.dict(rules.MC_OPTS, guard_normal_hit=False):
        toughness_check.video_run('db', runs)
    return {name: dict(damage=sum(c.values()) / runs,
                       direct=c['direct'] / runs, guard=c['guard'] / runs,
                       defense=sorted(defenses[name])) for name, c in rows.items()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--myinfo', required=True)
    p.add_argument('--runs', type=int, default=60)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--ov', type=json.loads)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.runs < 1:
        p.error('--runs must be positive')
    if not args.output.resolve().is_relative_to(ROOT):
        p.error('Output must stay in the workspace')
    check.low_priority()
    result = {}
    for stage in check.SAMPLES:
        result[stage] = measure(stage, args.runs, args.seed, args.myinfo, args.ov)
        print(json.dumps(result[stage]['summary'], ensure_ascii=False), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_text(args.output, json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
