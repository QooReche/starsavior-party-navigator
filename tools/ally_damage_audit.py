"""Read-only private inputs; export derived comparisons only, at IDLE priority.

python -X utf8 -I tools/ally_damage_audit.py --myinfo PATH --tables PATH 
    --output docs/ally_damage_results.json --runs 60
"""
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from battlesim.fileio import atomic_text
import ingame_check as check
from battlesim import rules
from battlesim.mc import Battle
from battlesim.starsavior.data import get_db
from battlesim.starsavior.parser import UnitDef

KEYS = ['cristelle', 'wedding-epindel', 'white-pearl-luna', 'wedding-carmen']


def compare_tables(path):
    """No original rows, account fields, or input path are serialized."""
    names = ['UNIT_TEMPLET_BASE1', 'UNIT_STAT_TEMPLET1', 'SKILL_TEMPLET_1',
             'DAMAGE_TEMPLET', 'SE_TEMPLET_SKILL_1', 'BUFF_TEMPLET']
    tables, contents, hashes = {}, {}, {}
    for name in names:
        file = Path(path) / (name + '.json')
        content = file.read_text(encoding='utf-8-sig')
        tables[name] = json.loads(content)['Data']
        contents[name] = content.splitlines()
        hashes[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()

    def row(name, key, value):
        return next(r for r in tables[name] if r.get(key) == value)

    def ref(name, value):
        needle = json.dumps(value, ensure_ascii=False)
        line = next(i for i, s in enumerate(contents[name], 1) if needle in s)
        return name + '.json:' + str(line)

    db, units = get_db(), []
    for key in KEYS:
        d = UnitDef(db, key)
        u = row('UNIT_TEMPLET_BASE1', 'm_UnitID', d.id)
        stat = row('UNIT_STAT_TEMPLET1', 'm_StatStrID', u['m_StatStrID'])
        skills = []
        for sid in u['m_listSkill']:
            sk = row('SKILL_TEMPLET_1', 'm_SkillStrID', sid)
            suffix = sid.rsplit('_', 1)[-1]
            slot = {'ATTACK': '기본기', 'SPECIAL': '특수기', 'HYPER': '궁극기'}.get(suffix)
            if slot is None:
                continue
            public = d.skills.get(slot) or d.trigger_skills.get(slot)
            dm = row('DAMAGE_TEMPLET', 'DTStrID', sk['DTStrID']) if sk.get('DTStrID') else {}
            cf = [dm.get(k, 0) for k in ('AtkFactor', 'HpFactor', 'DefFactor', 'TurnSpeedFactor')]
            effects = [e for e in tables['SE_TEMPLET_SKILL_1']
                       if e.get('m_SEStrID') == 'COND_' + sid.removeprefix('NKM_UNIT_S_') + '_10_01']
            skills.append(dict(slot=slot, coefficient_match=public.cf == cf,
                               coefficient_percent=[v / 100 for v in cf],
                               toughness=[public.raw.get('ab', 0), sk.get('SuperArmorBreakValue', 0)],
                               source=ref('SKILL_TEMPLET_1', sid),
                               damage_source=ref('DAMAGE_TEMPLET', sk['DTStrID']) if dm else None,
                               level_effect_sources=[ref('SE_TEMPLET_SKILL_1', e['m_SEStrID']) for e in effects]))
        units.append(dict(key=key, skills=skills, base_cross_attack=stat['m_StatData'].get('NST_RATE_CROSS_ATTACK', 0),
                          base_revenge_attack=stat['m_StatData'].get('NST_RATE_REVENGE_ATTACK', 0),
                          sources=[ref('UNIT_TEMPLET_BASE1', u['m_UnitStrID']),
                                   ref('UNIT_STAT_TEMPLET1', u['m_StatStrID'])]))
    return dict(tables_sha256=hashes, units=units)


def measure(stage, runs, seed, myinfo, override=None, experiment=None):
    """Counters observe successful casts/damage without consuming RNG."""
    originals = {k: getattr(Battle, k) for k in ('act', 'cast', 'apply_damage', 'exec_line', 'final_dmg')}
    casts, damage, states, targets = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    turns = defaultdict(Counter)

    def act(b, u):
        before = u.actions
        extra, broken = u.extra_turn, u.broken
        result = originals['act'](b, u)
        if u.side == 0 and u.actions != before:
            turns[u.d.key]['selected'] += 1
            turns[u.d.key]['extra_turn'] += bool(extra)
            turns[u.d.key]['break_recovery'] += bool(broken)
        return result

    def cast(b, u, sk, *args, **kw):
        ctx = originals['cast'](b, u, sk, *args, **kw)
        if ctx is not None and u.side == 0:
            casts[u.d.key][sk.slot + ':' + (ctx.via or 'turn')] += 1
        return ctx

    def apply_damage(b, a, v, dmg, kind, **kw):
        before = a.dmg if a is not None else 0
        result = originals['apply_damage'](b, a, v, dmg, kind, **kw)
        if a is not None and a.side == 0:
            damage[a.d.key][kind] += a.dmg - before
            targets[a.d.key]['boss' if v.d.boss else 'other'] += a.dmg - before
        return result

    def exec_line(b, owner, ln, ctx):
        if experiment == 'no_epindel_shield_bonus' and owner.d.key == 'wedding-epindel' and '피해 증가 +150%' in ln.raw:
            return
        if experiment == 'no_luna_damage_bonus' and owner.d.key == 'white-pearl-luna' and '피해 증가 +100%' in ln.raw:
            return
        if experiment == 'no_forbidden' and owner.side == 1 and ln.eff.get('name') in ('금제·계', '금제·갑'):
            return
        if experiment == 'no_silhouette' and owner.side == 1 and ln.eff.get('name') == '선명해지는 실루엣':
            return
        if experiment in ('no_epindel_stack', 'no_luna_stack') and owner.d.key == {
                'no_epindel_stack': 'wedding-epindel', 'no_luna_stack': 'white-pearl-luna'}.get(experiment) and ln.eff.get('name') == '점화':
            return
        return originals['exec_line'](b, owner, ln, ctx)

    def final_dmg(b, a, v, base, ctx, crit, cdv, pen, r, hctx):
        if a.side == 0:
            states[a.d.key]['hits'] += 1
            states[a.d.key]['broken_target_hits'] += bool(v.broken)
            states[a.d.key]['max_ignition_hits'] += a.stack('점화') >= 5
            states[a.d.key]['defense_sum'] += b.def_stat(v)
        if experiment == 'no_forbidden_reduction' and v.side == 1:
            vm = v.mods()
            old = vm['red']
            vm['red'] = dict(old)
            for name, slot in [('금제·계', '특수기'), ('금제·갑', '궁극기')]:
                if v.on(name):
                    vm['red'][slot] = vm['red'].get(slot, 0) - 0.2
            try:
                return originals['final_dmg'](b, a, v, base, ctx, crit, cdv, pen, r, hctx)
            finally:
                vm['red'] = old
        return originals['final_dmg'](b, a, v, base, ctx, crit, cdv, pen, r, hctx)

    original_def = Battle.def_stat
    with ExitStack() as stack:
        for name, fn in [('act', act), ('cast', cast), ('apply_damage', apply_damage), ('exec_line', exec_line), ('final_dmg', final_dmg)]:
            stack.enter_context(patch.object(Battle, name, fn))
        if experiment == 'no_break_bonus':
            stack.enter_context(patch.object(rules, 'BREAK_DEC', 0.0))
        if experiment == 'enemy_def_half':
            stack.enter_context(patch.object(Battle, 'def_stat',
                lambda b, u, local=0: original_def(b, u, local) * (0.5 if u.side == 1 else 1)))
        if experiment == 'no_rekindle':
            sample = list(check.SAMPLES[stage])
            sample[5] = 0
            stack.enter_context(patch.dict(check.SAMPLES, {stage: tuple(sample)}))
        if experiment in ('no_luna_reaction', 'no_cristelle_trigger', 'no_carmen_reaction'):
            key = {'no_luna_reaction': 'white-pearl-luna', 'no_cristelle_trigger': 'cristelle',
                   'no_carmen_reaction': 'wedding-carmen'}[experiment]
            original_trigger = Battle.trigger_cast
            def trigger(b, u, *args, **kw):
                return None if u.d.key == key else original_trigger(b, u, *args, **kw)
            stack.enter_context(patch.object(Battle, 'trigger_cast', trigger))
        result = check.run(stage, runs, override, seed, True, myinfo)
    def avg(rows):
        return {k: {f: round(v / runs, 4) for f, v in vs.items()} for k, vs in rows.items()}
    return dict(summary=result, turns=avg(turns), casts=avg(casts), damage_by_kind=avg(damage), damage_by_target=avg(targets), hit_states=avg(states))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--myinfo', required=True)
    p.add_argument('--tables', required=True)
    p.add_argument('--runs', type=int, default=60)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.runs < 1 or not args.output.resolve().is_relative_to(ROOT):
        p.error('Positive runs and a workspace output path are required')
    check.low_priority()
    tracked = ['rawdata/databook_main.json', 'rawdata/foe.js', 'data/growth.json', 'battlesim/mc.py', 'battlesim/rules/default.json']
    result = dict(runs=args.runs, seed=args.seed, tables=compare_tables(args.tables),
                  workspace_sha256={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in tracked},
                  profiles={})
    profiles = [('before', {'chain_skill_damage_up': False}, None), ('after', {}, None),
                ('no_break_bonus', {}, 'no_break_bonus'), ('no_toughness', {'toughness': 'off'}, None),
                ('no_forbidden', {}, 'no_forbidden'), ('no_forbidden_reduction', {}, 'no_forbidden_reduction'),
                ('no_silhouette', {}, 'no_silhouette'),
                ('enemy_def_half', {}, 'enemy_def_half'), ('no_penalty', {'power_penalty': 'off'}, None),
                ('no_rekindle', {}, 'no_rekindle'), ('no_coop', {'coop': False, 'forced_coop': False}, None),
                ('no_luna_reaction', {}, 'no_luna_reaction'), ('no_cristelle_trigger', {}, 'no_cristelle_trigger'),
                ('no_carmen_reaction', {}, 'no_carmen_reaction'), ('no_epindel_stack', {}, 'no_epindel_stack'),
                ('no_luna_stack', {}, 'no_luna_stack'),
                ('no_epindel_shield_bonus', {}, 'no_epindel_shield_bonus'), ('no_luna_damage_bonus', {}, 'no_luna_damage_bonus')]
    for name, override, experiment in profiles:
        stages = check.SAMPLES if name in ('before', 'after') else ('36-36', '37-3')
        result['profiles'][name] = {stage: measure(stage, args.runs, args.seed, args.myinfo, override, experiment) for stage in stages}
        print(name, {s: r['summary']['sim_ratio'] for s, r in result['profiles'][name].items()}, flush=True)
        atomic_text(args.output, json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
