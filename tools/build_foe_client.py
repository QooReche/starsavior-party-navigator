"""Extract the audited old guild boss rules from PC tables (26752678)."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.tables import rows, buff_names
from tools.build_foe_react import translate_conds, TIMING, TARGET_TYPE


def build(static):
    tables = Path(static) / 'tables'
    strings = json.loads((tables / 'Strings/STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))
    names = buff_names(tables)
    conditions = {r['Id']: r for r in rows(tables / 'Plain/SKILL_CONDITION_TEMPLET.json')}
    skills = rows(tables / 'SKILL_TEMPLET_2.json')
    out = {'units': {'심해의 폭군': {'sequential_events': ['enemy_ts']}}, 'buffs': {}}
    for name, prefix in [('시엔', 'NKM_UNIT_MON_WHITEDRAGON_METEORWHIP_BOSS_')]:
        rules = {}
        for sk in skills:
            if not sk['m_SkillStrID'].startswith(prefix) or sk.get('m_NKM_SKILL_TYPE') != 'NST_REACT':
                continue
            condition = conditions[sk['ReactConditionID']]
            timing, body = next((value, condition[key]) for key, value in TIMING.items() if condition.get(key))
            conds = translate_conds(body, names)
            assert conds is not None, sk['m_SkillStrID']
            ko = strings[sk['m_SkillName']]['ko']
            rules[ko] = dict(timing=timing, conds=conds, target=TARGET_TYPE[sk['m_TARGET_TYPE']], client_1121=True)
        out['units'][name] = {'react': rules}
    for buff in rows(tables / 'BUFF_TEMPLET.json'):
        if buff['m_BuffStrID'] not in ('BI_NEXT_TURN', 'BI_SHARK_CHAIN_BOSS_5', 'BI_WHITEDRAGON_METEORWHIP_BOSS_1'):
            continue
        info = {'category': 'buff' if buff.get('IsBuff') else 'marker'}
        if buff.get('NextTurnCatch'):
            info['next_turn_catch'] = True
        if buff.get('SuperArmorDamageBan'):
            info['armor_ban'] = True
        if any(s['StatTypeFix'] == 'NST_TURN_SPEED' and s['StatTypeFixValue'] == 0 for s in buff.get('FixStats') or []):
            info['speed_zero'] = True
        out['buffs'][names[buff['m_BuffStrID']]] = info
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--static', required=True)
    args = p.parse_args()
    data = build(args.static)
    (ROOT / 'data/foe_client.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
