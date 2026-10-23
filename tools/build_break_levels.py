# -*- coding: utf-8 -*-
"""브레이크 스킬(오비탈) 레벨 효과 -> data/break_skill_levels.json (공개 저장소에는 가공 수치만).

게임: ORBITAL_ARRAY_TEMPLET(NORMAL_BREAK_SKILL) -> SkillLevelGroup -> ORBITAL_LEVEL_GROUP_TEMPLET 행마다 SkillLevelDamageUp·
SkillLevelHealUp(만분율). 레벨 L 의 효과 = 레벨 L 이하 행의 합(Star.Templets.decompiled.cs 20463~20474·20737~20745).
피해는 0 이 아닌 각 계수에, 회복은 각 회복 계수에 더함(NKM.decompiled.cs 17742~17812·17485~17545).

출력 skills[한국어 이름] = {"dmg": [레벨 1~10 누적 만분율], "heal": [...]}.

사용: python -X utf8 -I tools/build_break_levels.py [--static <비공개 저장소>]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority   # noqa: E402
from battlesim.fileio import atomic_text   # noqa: E402


def build(static):
    tables = Path(static) / 'tables'
    strings = json.loads((tables / 'Strings' / 'STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))
    levels = json.loads((tables / 'ORBITAL_LEVEL_GROUP_TEMPLET.json').read_text(encoding='utf-8'))['Data']
    out = {}
    for a in json.loads((tables / 'ORBITAL_ARRAY_TEMPLET.json').read_text(encoding='utf-8'))['Data']:
        if a.get('BreakSkillType') != 'NORMAL_BREAK_SKILL':
            continue
        name = (strings.get(a.get('m_SkillName') or '') or {}).get('ko')
        rows = sorted((r for r in levels if r['SkillLevelGroupID'] == a['SkillLevelGroup']), key=lambda r: r['SkillLevelValue'])
        if not name or [r['SkillLevelValue'] for r in rows] != list(range(1, len(rows) + 1)):
            raise SystemExit('레벨 표 형식이 다름: %s' % a.get('m_SkillStrID'))
        dmg, heal, d, h = [], [], 0, 0
        for r in rows:
            d += r.get('SkillLevelDamageUp') or 0
            h += r.get('SkillLevelHealUp') or 0
            dmg.append(d)
            heal.append(h)
        out[name] = {'dmg': dmg, 'heal': heal}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    try:
        static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    skills = build(static)
    out = dict(_note='브레이크 스킬 레벨 효과(tools/build_break_levels.py). skills[이름] = {dmg: 레벨 1~10 누적 피해 계수 가산(만분율), '
                     'heal: 누적 회복 계수 가산(만분율)}. 엔진 mc.break_skill_level=data 일 때 씀.',
               skills=skills)
    atomic_text(ROOT / 'data' / 'break_skill_levels.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('break_skill_levels.json:', ', '.join('%s Lv10 피해 +%d 회복 +%d' % (k, v['dmg'][-1], v['heal'][-1]) for k, v in skills.items()))


if __name__ == '__main__':
    main()
