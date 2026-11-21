"""Extract the audited old guild boss rules from PC tables (26752678)."""
import argparse
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.tables import rows, buff_names
from tools.build_foe_react import translate_conds, TIMING, TARGET_TYPE
from tools.build_foe_auto import conds as auto_conds, filters


def build(static):
    tables = Path(static) / 'tables'
    strings = json.loads((tables / 'Strings/STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))
    names = buff_names(tables)
    conditions = {r['Id']: r for r in rows(tables / 'Plain/SKILL_CONDITION_TEMPLET.json')}
    skills = rows(tables / 'SKILL_TEMPLET_2.json')
    skill_by_id = {s['m_SkillStrID']: s for s in skills}
    auto = {r['Id']: r for r in rows(tables / 'Plain/AUTO_SKILL_TEMPLET.json')}
    targets = {r['Id']: r['TargetCondition'] for r in rows(tables / 'Plain/AUTO_SKILL_TARGET_TEMPLET.json')}
    out = {'units': {'심해의 폭군': {'sequential_events': ['enemy_ts']}}, 'buffs': {}}
    se = next(r for r in rows(tables / 'SE_TEMPLET_SKILL_2.json') if r['m_SEID'] == 130056301)
    buff = next(b for b in rows(tables / 'BUFF_TEMPLET.json') if b['m_BuffStrID'] == se['m_BuffStrID'])
    assert not buff['AddDamage']
    out['units']['공허결집자'] = {'local_damage_only': se['Stats'][0]['NKM_STAT_TYPE_RATE'] / 100}
    for name, prefix in [('시엔', 'NKM_UNIT_MON_WHITEDRAGON_METEORWHIP_BOSS_'),
                         ('티엔', 'NKM_UNIT_MON_WHITEDRAGON_WINDFAN_BOSS_'),
                         ('BFB', 'NKM_UNIT_MON_AUTOMATON_MINIGUN_BOSS_EVENT_')]:
        rules, meta, changes = {}, {}, []
        for sk in skills:
            sid = sk['m_SkillStrID']
            if not sid.startswith(prefix):
                continue
            suffix = re.fullmatch(r'(ATTACK|SPECIAL|HYPER)\d*', sid[len(prefix):])
            if not suffix:
                continue
            ko = strings[sk['m_SkillName']]['ko']
            info = {'slot': {'ATTACK': '기본기', 'SPECIAL': '특수기', 'HYPER': '궁극기'}[suffix[1]],
                    'reset_cd': sk.get('ChangeSkillType') == 'CST_RESET_COOL_TURN'}
            if sk.get('AutoSkillId'):
                info['auto'] = [{'c': auto_conds(r['Condition'], names),
                                 'f': filters(targets[r['TargetConditionId']], names)}
                                for r in auto[sk['AutoSkillId']]['SkillConditions']]
            meta[ko] = info
            if sk.get('m_NKM_SKILL_TYPE') != 'NST_REACT':
                continue
            condition = conditions[sk['ReactConditionID']]
            timing, body = next((value, condition[key]) for key, value in TIMING.items() if condition.get(key))
            body = dict(body)
            enemy = body.pop('ExistEnemySpecificBuff', [])
            conds = translate_conds(body, names)
            assert conds is not None, sk['m_SkillStrID']
            if enemy:
                conds.append(['enemy_has', [names[n] for n in enemy]])
            rules[ko] = dict(timing=timing, conds=conds, target=TARGET_TYPE[sk['m_TARGET_TYPE']], client_1121=True)
        for se in rows(tables / 'SE_TEMPLET_SKILL_2.json'):
            before, after = se.get('BeforeChangeSkillStrId'), se.get('AfterChangeSkillStrId')
            if before and before.startswith(prefix):
                assert se['m_BuffStrID'] == 'BI_CHANGE_SKILL'
                changes.append([strings[skill_by_id[s]['m_SkillName']]['ko'] for s in (before, after)])
        out['units'][name] = {'react': rules, 'skills': meta, 'changes': changes}
        if name in ('BFB', '티엔'):
            out['units'][name]['sequential_events'] = ['own_post', 'ally_post', 'foe_post']
    for buff in rows(tables / 'BUFF_TEMPLET.json'):
        if buff['m_BuffStrID'] not in ('BI_NEXT_TURN', 'BI_SHARK_CHAIN_BOSS_5', 'BI_WHITEDRAGON_METEORWHIP_BOSS_1',
                                     'BI_WHITEDRAGON_WINDFAN_BOSS_1', 'BI_WHITEDRAGON_WINDFAN_BOSS_2'):
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
