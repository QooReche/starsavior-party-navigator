"""Derive numeric combat adapters; never read account samples or publish source rows."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority
from battlesim.fileio import atomic_text
from battlesim.starsavior.data import get_db
from tools.build_growth import STAT, read


def build(static):
    def load(name):
        return read(Path(static) / 'tables' / (name + '.json'))['Data']

    db = get_db()
    index = read(ROOT / 'data/saviors_index.json')
    keys = {int(k): v['key'] for k, v in index.items()
            if not k.startswith('_') and v.get('key') in db.units}
    skills = {r['m_SkillStrID']: r for n in (1, 2) for r in load(f'SKILL_TEMPLET_{n}')}
    levels = {}
    for n in (1, 2):
        for r in load(f'SKILL_LEVEL_GROUP_TEMPLET_{n}'):
            levels.setdefault(r['SkillLevelGroupID'], []).append(r)
    units = {}
    for u in load('UNIT_TEMPLET_BASE1'):
        if u['m_UnitID'] not in keys:
            continue
        slots = {}
        for slot, sid in zip(('basic', 'special', 'ultimate', 'passive'), u['m_listSkill']):
            sk = skills[sid]
            reduction = 0
            rows = {}
            for r in sorted(levels[sk['SkillLevelGroup']], key=lambda r: r['SkillLevelValue']):
                reduction += r.get('SkillLevelCoolTurnReduce', 0)
                rows[str(r['SkillLevelValue'])] = [max(0, sk.get('m_CoolTurn', 0) - reduction),
                                                 r.get('SkillLevelDamageUp', 0)]
            slots[slot] = rows
        units[keys[u['m_UnitID']]] = slots
    public = {p['id']: p for p in db.main['dict']['pot']}
    pl = {(r['PotenLevelGroupId'], r['PotenLevelValue']): r for r in load('POTENTIAL_LEVEL_GROUP_TEMPLET')}
    se = {r['m_SEStrID']: r for r in load('SE_TEMPLET_POTEN')}
    potentials = {}
    for p in load('SE_POTENTIAL_TEMPLET'):
        rows = {}
        for (group, level), r in pl.items():
            if group != p['PotenLevelGroupId']:
                continue
            pub = next((x for x in public.get(p['PotenId'], {}).get('lv', []) if x[0] == level), None)
            if pub is None:
                continue
            lines = [i for i, s in enumerate(pub[4]) if not s.startswith(('능력치:', '[상시] 능력치:'))]
            source = [se[s] for s in r.get('PotenLevelSe', [])]
            if len(lines) != len(source):
                raise ValueError(f'Combat line mapping changed: {p["PotenId"]}/{level}')
            stats = {s['PotenLevelStatType']: s.get('PotenLevelStatRate', s.get('PotenLevelStatValue', 0))
                     for s in r.get('PotenLevelStat', []) if s['PotenLevelStatType'] not in STAT}
            # Existing public effect text supplies the vocabulary. Only indexes,
            # flags and extracted numeric stats are added to the public artifact.
            random_chain, random_basic = [], {}
            for i, s in zip(lines, source):
                if s.get('AddDamageRate') and s.get('AutoTargetId') == 4:
                    random_chain.append(i)
                if (s.get('m_BuffStrID') == 'BI_ENFORCE' and s.get('AutoTargetId') == 5
                        and s.get('EnforceAutoTargetId') == 4 and s.get('EnforceSkillIndex') == 'NSI_SKILL_1_ATTACK'):
                    random_basic[str(i)] = s['m_Condition'].get('m_fActiveRate', 10000)
            rows[str(level)] = dict(lines=lines, stats=stats, random_chain=random_chain, random_basic=random_basic)
        potentials[str(p['PotenId'])] = rows
    return dict(version=1, units=units, potentials=potentials)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    try:
        args.static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    out = build(args.static)
    atomic_text(ROOT / 'data/myinfo_combat.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('Derived combat adapters:', len(out['units']), 'units,', len(out['potentials']), 'potentials')


if __name__ == '__main__':
    main()
