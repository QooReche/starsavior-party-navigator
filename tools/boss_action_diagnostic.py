"""Measure action causes without changing combat or copying private inputs.

Each profile runs sequentially at IDLE priority. Full per-action records are
retained for the first seed only; all-run aggregates include non-boss enemies.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import json
import hashlib
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from battlesim.fileio import atomic_text
import ingame_check as check
from battlesim.mc import Battle
from battlesim.starsavior.foe import load_foe, SK_NST


def compare_tables(path):
    """Read private tables in place; emit comparisons, never master rows.

    Unit IDs are matched by name, stat template and skill set. They are not
    verified spawn IDs: the operation BattleScript is unavailable.
    """
    names = ['UNIT_TEMPLET_BASE2', 'UNIT_STAT_TEMPLET2', 'STAT_ADD_PER_LEVEL2',
             'SKILL_TEMPLET_2', 'SKILL_LEVEL_GROUP_TEMPLET_2', 'SE_TEMPLET_SKILL_2',
             'BUFF_TEMPLET', 'DAMAGE_TEMPLET']
    tables, refs, hashes = {}, {}, {}
    for name in names:
        file = Path(path) / (name + '.json')
        content = file.read_text(encoding='utf-8-sig')
        tables[name] = json.loads(content)['Data']
        refs[name] = content.splitlines()
        hashes[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()

    def lookup(table, key, value):
        return next(r for r in tables[table] if r.get(key) == value)

    def ref(table, value):
        needle = json.dumps(value, ensure_ascii=False)
        line = next(i for i, s in enumerate(refs[table], 1) if needle in s)
        return table + '.json:' + str(line)

    raw, result = load_foe(), []
    for ui, uid, level in [(654, 45037, 2896), (658, 44075, 2906)]:
        public = raw['u'][ui]
        u = lookup('UNIT_TEMPLET_BASE2', 'm_UnitID', uid)
        st = lookup('UNIT_STAT_TEMPLET2', 'm_StatStrID', u['m_StatStrID'])
        growth = lookup('STAT_ADD_PER_LEVEL2', 'StatAddPerLevelStrID', st['m_StatAddPerLevelStrID'])
        base = [st['m_StatData'].get(k, 0) for k in SK_NST]
        gw = [growth['StatAddPerLevelData'].get(k, 0) for k in SK_NST[:3]]
        skills = []
        special = []
        passives = []
        extra, summon = 0, 0
        assert len(public['sk']) == len(u['m_listSkill']), 'Skill set changed; review mapping'
        for si, sid in zip(public['sk'], u['m_listSkill']):
            sd = raw['s'][si]
            sk = lookup('SKILL_TEMPLET_2', 'm_SkillStrID', sid)
            dm = lookup('DAMAGE_TEMPLET', 'DTStrID', sk['DTStrID']) if sk.get('DTStrID') else {}
            if sd['ty'] == '액티브':
                pct = float(sd['dm'].split('×')[1].strip('%')) if sd.get('dm') else 0
                skills.append(dict(name=sd['n'], cooldown=[sd.get('cd', 0), sk['m_CoolTurn']],
                                   toughness=[sd.get('ab', 0), sk.get('SuperArmorBreakValue', 0)],
                                   atk_percent=[pct, dm.get('AtkFactor', 0) / 100], source=ref('SKILL_TEMPLET_2', sid)))
            group = lookup('SKILL_LEVEL_GROUP_TEMPLET_2', 'SkillLevelGroupID', sk['SkillLevelGroup'])
            for se_id in group.get('SkillLevelSE', []):
                se = lookup('SE_TEMPLET_SKILL_2', 'm_SEStrID', se_id)
                buff = lookup('BUFF_TEMPLET', 'm_BuffStrID', se['m_BuffStrID'])
                extra += bool(buff.get('ExtraTurn'))
                summon += bool(buff.get('Summon'))
                if sd['ty'] == '패시브':
                    passives.append(dict(name=sd['n'],
                                         stat_percent={v['NKM_STAT_TYPE']: v['NKM_STAT_TYPE_RATE'] / 100
                                                       for v in buff.get('Stats', [])},
                                         chain_atk_percent=se.get('AddDamageRate', 0) / 100,
                                         gauge_percent=se.get('SpeedGaugeRate', 0) / 100,
                                         condition_id=se.get('SkillConditionId'),
                                         source=ref('SE_TEMPLET_SKILL_2', se_id)))
                speed = [x['NKM_STAT_TYPE_RATE'] / 100 for x in buff.get('Stats', [])
                         if x['NKM_STAT_TYPE'] == 'NST_NV_RATE_TURN_SPEED']
                if speed or se.get('SpeedGaugeRate'):
                    special.append(dict(skill=sd['n'], speed_percent=speed,
                                        gauge_percent=se.get('SpeedGaugeRate', 0) / 100,
                                        duration=se.get('m_BuffLifeTurn'),
                                        source=ref('SE_TEMPLET_SKILL_2', se_id),
                                        condition_id=se.get('SkillConditionId')))
        result.append(dict(name=public['n'], raw_unit_index=ui, candidate_unit_id=uid,
                           mapping='stat/skill match; spawn ID unverified',
                           base_stats_match=base == public['b'], growth_match=gw == public['gw'],
                           speed=[public['b'][3], base[3]],
                           final_hp_atk_def=[[public['b'][i] + public['gw'][i] * (level - 1),
                                              base[i] + gw[i] * (level - 1)] for i in range(3)],
                           skills=skills, passive_numeric_summary=passives, speed_and_gauge_effects=special,
                           extra_turn_effects=extra, summon_effects=summon,
                           sources=[ref('UNIT_TEMPLET_BASE2', u['m_UnitStrID']),
                                    ref('UNIT_STAT_TEMPLET2', u['m_StatStrID']),
                                    ref('STAT_ADD_PER_LEVEL2', st['m_StatAddPerLevelStrID'])]))
    return dict(tables_sha256=hashes, units=result,
                limitation='Referenced SkillConditionId bodies (including 6001) and BattleScript are absent; no data replacement.')


def measure(stage, runs, seed, myinfo, override=None):
    originals = {k: getattr(Battle, k) for k in
                 ('run', 'act', 'set_gauge', 'exec_line', 'cast', 'tough_hit')}
    totals = defaultdict(Counter)
    first = []
    serial = 0

    def ident(u):
        return '%s:%s' % (u.side, u.name)

    def record(b, event, **kw):
        row = dict(event=event, tick=round(b.t, 6), **kw)
        if b._audit_serial == 0:
            first.append(row)

    def run(b):
        nonlocal serial
        b._audit_serial = serial
        serial += 1
        b._audit_source = None
        b._audit_gain = defaultdict(Counter)
        b._audit_last = {}
        b._audit_last_action = {}
        b._audit_ordinal = 0
        result = originals['run'](b)
        for u in b.allies + b.all_foes:
            c = totals[ident(u)]
            c['units'] += 1
            c['boss_units'] += bool(getattr(u.d, 'boss', False))
            c['breaks'] += u.breaks
            c['death_tick'] += u.death_t if u.death_t is not None else b.t
            c['deaths'] += u.dead
            c['ending_gauge'] += u.gauge
        return result

    def act(b, u):
        before = u.actions
        b._audit_ordinal += 1
        c = totals[ident(u)]
        gains = dict(b._audit_gain.pop(u, {}))
        row = dict(actor=u.name, side=u.side, pos=u.pos, wave=b.wave_i,
                   boss=bool(getattr(u.d, 'boss', False)), ordinal=b._audit_ordinal,
                   action=u.actions + 1, extra_turn=u.extra_turn,
                   gauge=round(u.gauge, 4), gains={k: round(v, 4) for k, v in gains.items()},
                   base_speed=u.d.spd_base, passive_speed_pct=u.d.passive['spdp'],
                   buff_speed_pct=u.mods()['spdp'], speed=u.spd(),
                   alive_allies=len(b.alive(0)), ally_actions=sum(x.actions for x in b.allies),
                   broken=u.broken, cd_before=dict(u.cd),
                   break_skip=(u.broken and u.side == 0 and b.mc['ally_break_gauge'] == 'skip'),
                   interval=round(b.t - b._audit_last.get(u, 0), 6))
        originals['act'](b, u)
        if u.actions == before:  # support skill ended the wave before actor's turn
            b._audit_gain[u].update(gains)
            b._audit_ordinal -= 1
            return
        b._audit_last[u] = b.t
        c['actions'] += 1
        c['action_gauge_consumed'] += row['gauge']
        c['action_gauge_overflow'] += max(0, row['gauge'] - 10000)
        c['extra_turns'] += row['extra_turn']
        c['break_skips'] += row['break_skip']
        c['actions_all_allies_alive'] += row['alive_allies'] == len(b.allies)
        c['speed_sum'] += row['speed']
        c['interval_sum'] += row['interval']
        c['actions_with_effect_gauge'] += any(k != 'time' and v > 0 for k, v in gains.items())
        c['base_speed'] = row['base_speed'] * runs
        previous = b._audit_last_action.get(u)
        if previous:
            c['intervals'] += 1
            c['ally_gap_sum'] += row['ally_actions'] - previous['ally_actions']
            c['global_gap_sum'] += row['ordinal'] - previous['ordinal']
            if row['alive_allies'] == len(b.allies):
                c['intervals_all_allies_alive'] += 1
                c['ally_gap_all_alive'] += row['ally_actions'] - previous['ally_actions']
                c['global_gap_all_alive'] += row['ordinal'] - previous['ordinal']
        b._audit_last_action[u] = row
        row['cd_after'] = dict(u.cd)
        record(b, 'action', **row)

    def gauge(b, u, value):
        old = u.gauge
        originals['set_gauge'](b, u, value)
        delta = u.gauge - old
        if abs(delta) < 1e-8:
            return
        source = b._audit_source or 'time'
        b._audit_gain[u][source] += delta
        c = totals[ident(u)]
        if source == 'time':
            c['time_gauge'] += delta
            dt = delta / u.spd()
            c['gauge_base_speed'] += u.d.spd_base * dt
            c['gauge_speed_buff'] += u.d.spd_base * u.mods()['spdp'] * dt
            c['gauge_speed_passive'] += u.d.spd_base * u.d.passive['spdp'] * dt
            c['gauge_leader'] += (b.mc['leader_speed'] if u.leader else 0) * dt
        else:
            c['effect_gauge'] += delta
            c['gauge_effect_count'] += 1
            c['positive_effect_gauge' if delta > 0 else 'negative_effect_gauge'] += delta
            c['positive_effect_count' if delta > 0 else 'negative_effect_count'] += 1
            record(b, 'gauge', actor=u.name, side=u.side, pos=u.pos,
                   source=source, delta=delta, before=old, after=u.gauge)

    def line(b, owner, ln, ctx):
        old = b._audit_source
        b._audit_source = owner.name + ': ' + ln.raw
        try:
            return originals['exec_line'](b, owner, ln, ctx)
        finally:
            b._audit_source = old

    def cast(b, u, sk, *args, **kw):
        result = originals['cast'](b, u, sk, *args, **kw)
        if result is not None:
            extra = args[0] if args else kw.get('extra', False)
            totals[ident(u)]['extra_casts' if extra else 'normal_casts'] += 1
            record(b, 'cast', actor=u.name, side=u.side, pos=u.pos,
                   skill=sk.name, slot=sk.slot, extra=extra, via=kw.get('via'))
        return result

    def tough(b, a, v, ctx):
        old, broken = v.gauge, v.broken
        result = originals['tough_hit'](b, a, v, ctx)
        if not broken and v.broken:
            totals[ident(v)]['break_gauge_lost'] += old - v.gauge
            b._audit_gain[v]['break_reset'] += v.gauge - old
            record(b, 'break', actor=v.name, side=v.side, pos=v.pos,
                   by=a.name, lost_gauge=old - v.gauge)
        return result

    with ExitStack() as stack:
        for key, fn in dict(run=run, act=act, set_gauge=gauge, exec_line=line,
                            cast=cast, tough_hit=tough).items():
            stack.enter_context(patch.object(Battle, key, fn))
        result = check.run(stage, runs, override, seed, True, myinfo)
    assert round(sum(c['actions'] for k, c in totals.items()
                     if k.startswith('1:') and c['boss_units']) / runs, 2) == result['sim_boss_actions']
    return dict(result=result, per_unit={k: {n: round(v / runs, 5) for n, v in c.items()}
                                        for k, c in totals.items()}, first_seed_log=first)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--myinfo', required=True)
    p.add_argument('--runs', type=int, default=60)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--only', choices=check.SAMPLES)
    p.add_argument('--ov', type=json.loads, default={})
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--tables', type=Path, help='Optional private table directory; comparisons only')
    args = p.parse_args()
    if args.runs < 1:
        p.error('--runs must be positive')
    out = args.output.resolve()
    if not out.is_relative_to(ROOT):
        p.error('--output must be inside this checkout')
    check.low_priority()
    rows = {}
    for name in check.SAMPLES:
        if args.only and name != args.only:
            continue
        rows[name] = measure(name, args.runs, args.seed, args.myinfo, args.ov)
        print(name, json.dumps(rows[name]['result'], ensure_ascii=False), flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
              [ROOT / 'data/growth.json', ROOT / 'rawdata/foe.js', ROOT / 'rawdata/databook_main.json']}
    atomic_text(out, json.dumps(dict(runs=args.runs, seed=args.seed, override=args.ov,
                                  data_sha256=hashes, stages=rows,
                                  table_comparison=compare_tables(args.tables) if args.tables else None),
                              ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
