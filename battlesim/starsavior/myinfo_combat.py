"""Combat-only adapter for final screen stats; no account-file IO."""
import copy
import json
import math
from functools import lru_cache
from pathlib import Path

from .parser import Line

SLOTS = {'기본기': 'basic', '특수기': 'special', '궁극기': 'ultimate', '고유 패시브': 'passive'}


@lru_cache(maxsize=1)
def combat_data():
    return json.loads((Path(__file__).resolve().parents[2] / 'data/myinfo_combat.json').read_text(encoding='utf8'))


def combat_input(unit):
    """Minimal simulation payload, excluding gear, journey and blessing history."""
    skills = unit.get('skills') or {}
    entries = (unit.get('gauntlet') or {}).get('potentials')
    if not isinstance(entries, list):
        entries = []
    return dict(skills={k: skills[k] for k in SLOTS.values() if k in skills},
                potentials=[[int(p[0]), int(p[1])] for p in entries
                            if isinstance(p, list) and len(p) == 4
                            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                    and math.isfinite(v) and v >= 0 and v == math.floor(v) for v in p)
                            and p[1] > 0])


def select_skills(raw, key, combat):
    """L.e/L.ei contain complete selected-level SE groups, not level deltas.

    NKM:17744-17757 adds SkillLevelDamageUp to a nonzero ATK coefficient.
    Current tables have zero there; SE damage-up effects stay in L.e instead.
    """
    u = copy.deepcopy(raw)
    if key not in combat_data()['units']:
        # 계수 표가 없는 구원자(예: 개화 변형): 파티 전체를 실패시키지 않고 기본 스킬 레벨로 계산한다.
        return u
    rows = combat_data()['units'].get(key, {})
    result = []
    for s in u['sk']:
        slot = SLOTS.get(s['sl'].removeprefix('변형 '))
        if slot is None or slot not in combat.get('skills', {}):
            result.append(s)
            continue
        level = combat['skills'][slot]
        if (not isinstance(level, (int, float)) or isinstance(level, bool)
                or not math.isfinite(level) or level < 0 or level != math.floor(level)):
            raise ValueError('Invalid myinfo skill level: ' + slot)
        level = int(level)
        if level == 0:
            continue
        values = rows.get(slot, {}).get(str(level))
        table = s.get('L')
        if values is None or not table or level > len(table.get('ei', [])):
            raise ValueError('Unsupported myinfo skill level: ' + key + '/' + slot)
        ix = level - 1
        s['ef'] = [table['ln'][i] for i in table['e'][table['ei'][ix]]]
        s['dx'] = s['d1'] = table['d'][table['di'][ix]]
        s['cdm'] = values[0]
        if s.get('cf') and s['cf'][0]:
            s['cf'][0] += values[1]
        s['level'] = level
        result.append(s)
    u['sk'] = result
    return u


def apply_potentials(d, db, combat):
    tables = combat_data()['potentials']
    public = {p['id']: p for p in db.main['dict']['pot']}
    seen = set()
    for pid, level in combat.get('potentials', []):
        if pid in seen:
            raise ValueError('Duplicate myinfo potential')
        seen.add(pid)
        if level == 0:
            continue
        row = tables.get(str(pid), {}).get(str(level))
        pot = public.get(pid)
        if row is None or pot is None:
            d.unmodeled.append('myinfo potential: unknown ID/level %s/%s' % (pid, level))
            continue
        source = next(x[4] for x in pot['lv'] if x[0] == level)
        for stat, value in row['stats'].items():
            if stat == 'NST_SUPER_ARMOR':
                d.stats['sa'] += value
            else:
                d.unmodeled.append('myinfo potential stat: %s/%s' % (pid, stat))
        for i in row['lines']:
            ln = Line(source[i], '잠재력', 'passive')
            if i in row['random_chain']:
                ln.eff['random_enemy'] = True
            if str(i) in row['random_basic']:
                ln.eff = dict(kind='random_ally_basic', chance=row['random_basic'][str(i)] / 10000)
            d.lines.append(ln)
