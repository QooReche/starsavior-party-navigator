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


MISMATCH = []   # build() 가 건너뛴 잠재력 레벨(설명·클라 효과 수 불일치) '잠재력/레벨: …'
PUBLIC_LINES = {}   # (잠재력, 레벨) -> 지금 공개 설명 줄 수(보존 가능 여부 검사용)


def build(static):
    MISMATCH.clear()
    PUBLIC_LINES.clear()
    def load(name):
        return read(Path(static) / 'tables' / (name + '.json'))['Data']

    db = get_db()
    index = read(ROOT / 'data/saviors_index.json')
    keys = {int(k): v['key'] for k, v in index.items()
            if not k.startswith('_') and v.get('key') in db.units}
    # saviors_index 에 아직 없는 구원자(예: 아모라)는 시뮬 DB 의 id 로 찾는다. 개화 변형('@')은 기본 키와 id 가 같아 제외.
    for key, row in db.units.items():
        if '@' not in key and row.get('id') not in keys:
            keys[row['id']] = key
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
                # 공개 설명 줄 수와 클라 효과 수가 다르면(데이터북이 클라 표보다 새 빌드일 때 등) 이 레벨은 만들지 않고 기록 —
                # main() 이 이전 계수를 보존한다. 둘 다 없으면 시험(myinfo_combat_test)이 잡는다
                MISMATCH.append(f'{p["PotenId"]}/{level}: 설명 {len(lines)}줄·클라 효과 {len(source)}개')
                PUBLIC_LINES[(str(p['PotenId']), str(level))] = len(pub[4])
                continue
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
    # 클라 표에서 사라진 구원자(예: 10/22 에 1060 이 삭제됨)도 공개 DB 에 남아 있으면 이전 계수를 보존한다.
    old_path = ROOT / 'data/myinfo_combat.json'
    if old_path.exists():
        old = json.loads(old_path.read_text(encoding='utf8'))
        for k, v in old.get('units', {}).items():
            out['units'].setdefault(k, v)
        # 불일치로 건너뛴 잠재력 레벨만 이전 계수 보존 — 지금 공개 설명에 그 레벨이 있고 이전 줄 번호가 범위 안일 때만
        # (지워진 레벨·줄어든 설명은 되살리지 않는다 → 엔진은 그 효과를 「전투 효과 미해석」으로 둔다)
        for (pid, k), n in PUBLIC_LINES.items():
            v = old.get('potentials', {}).get(pid, {}).get(k)
            if v and all(0 <= i < n for i in v.get('lines', [])):
                out['potentials'].setdefault(pid, {})[k] = v
            else:
                print('이전 계수 보존 불가(설명 구조 다름):', pid, k)
    if MISMATCH:
        print('설명·클라 효과 수 불일치(이전 계수 보존):', '; '.join(MISMATCH))
    atomic_text(ROOT / 'data/myinfo_combat.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('Derived combat adapters:', len(out['units']), 'units,', len(out['potentials']), 'potentials')


if __name__ == '__main__':
    main()
