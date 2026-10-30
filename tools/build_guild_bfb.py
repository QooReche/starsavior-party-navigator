# -*- coding: utf-8 -*-
"""길드 방어전 시즌4 EX 보스 BFB·졸개 수치 -> data/guild_bfb.json (공개 저장소에는 가공 값만).

엔진 모듈 battlesim/starsavior/guild_bfb.py 가 이 파일을 읽어 상태 기계(신부 경쟁·정실 어필·보호막·캣파이트·신부의 응징)를 돌린다.
범용 SE 해석기가 아니다: 아는 SE 배열(순서·버프 이름·조건 id)과 다르면 빌드를 멈춘다(패치로 구조가 바뀌면 사람이 다시 확인).
명세·근거: AI/temp/partynavigator/work/guild_defense/bfb_skill_spec.md

사용: python -X utf8 -I tools/build_guild_bfb.py [--static <비공개 저장소>]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority   # noqa: E402
from tools.build_foe_spawn import jsonc                # noqa: E402
from battlesim.fileio import atomic_json               # noqa: E402

NUAT = {'NUAT_ORDER': '질서', 'NUAT_SUN': '태양', 'NUAT_MOON': '달', 'NUAT_STAR': '별', 'NUAT_CHAOS': '혼돈'}
ROLE = {'NURT_STRIKER': '스트라이커', 'NURT_CASTER': '캐스터', 'NURT_ASSASSIN': '어쌔신', 'NURT_RANGER': '레인저',
        'NURT_DEFENDER': '디펜더', 'NURT_SUPPORTER': '서포터'}
SCRIPT = 'JSON_GUILD_DUNGEON_BFB_07'
BATTLE_ID = 3011107
BOSS_SK = 'NKM_UNIT_MON_AUTOMATON_MINIGUN_BOSS_EVENT_'
# 아는 SE 배열(스킬 -> [(버프, 조건 id 또는 None)]). 다르면 중단.
EXPECT = {
    'ATTACK': [('BI_STAT_NST_RATE_PENETRATE_DEF', None)],
    'SPECIAL': [('BI_CHANGE_SKILL', None), ('BI_AUTOMATON_MINIGUN_BOSS_ANIMSET2', None), ('BI_DELETEBUFF', None),
                ('BI_SPEED_GAUGE_CHANGE_FIX', None), ('BI_AUTOMATON_MINIGUN_BOSS_2', None), ('BI_DELETEDEBUFF', None),
                ('BI_SPEED_GAUGE_CHANGE_FIX', None), ('BI_AUTOMATON_MINIGUN_BOSS_8', None), ('BI_AUTOMATON_MINIGUN_BOSS_6', None),
                ('BI_AUTOMATON_MINIGUN_BOSS_9', None)],
    'HYPER': [('BI_STAT_NST_RATE_PENETRATE_DEF', None), ('BI_SPEED_GAUGE_UP', None)],
    'PASSIVE1': [('BI_AUTOMATON_MINIGUN_BOSS_1', 58801), ('BI_AUTOMATON_MINIGUN_BOSS_7', 58801), ('BI_DELETE_SPECIFIC_BUFF', 4001)],
    'PASSIVE3': [('BI_ADD_DAMAGE_1', 55521)],
    'SPECIAL2': [('BI_STAT_NST_RATE_PENETRATE_DEF', None), ('BI_ATTACK_DECREASE', None), ('BI_ATTACK_INCREASE', None)],
    'HYPER2': [('BI_STAT_NST_RATE_PENETRATE_DEF', None), ('BI_ATTACK_DECREASE', None), ('BI_SPEED_DECREASE', None), ('BI_SPEED_GAUGE_UP', None)],
}
PASSIVE2_CONDS = [32002] + [52094] * 8 + [52095] * 8 + [2144] * 3 + [55148] * 9 + [37201] * 2


class Changed(Exception):
    pass


def rows(p):
    d = jsonc(p)
    d = d.get('Data', d) if isinstance(d, dict) else d
    return d


def need(cond, msg):
    if not cond:
        raise Changed(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--static', default=None)
    ap.add_argument('--out', default=str(ROOT / 'data' / 'guild_bfb.json'))
    args = ap.parse_args()
    low_priority()
    T = static_path(args.static) / 'tables'
    bs = rows(T / 'BattleScript' / (SCRIPT + '.json'))
    waves = bs['Waves']
    need(len(waves) == 2 and len(waves[0]['TeamBSpawnList']) == 2 and len(waves[1]['TeamBSpawnList']) == 1, '배치 웨이브 구성 변경')
    units = {u['m_UnitStrID']: u for u in rows(T / 'UNIT_TEMPLET_BASE2.json')}
    stats = {}
    for fn in sorted(T.glob('UNIT_STAT_TEMPLET*.json')):
        for r in rows(fn):
            stats[r['m_StatStrID']] = r
    sapl = {}
    for fn in sorted(T.glob('STAT_ADD_PER_LEVEL*.json')):
        for r in rows(fn):
            sapl[r['StatAddPerLevelStrID']] = r['StatAddPerLevelData']
    skills = {}
    for fn in ('SKILL_TEMPLET_1.json', 'SKILL_TEMPLET_2.json'):
        for r in rows(T / fn):
            skills[r['m_SkillStrID']] = r
    lvg = {}
    for fn in ('SKILL_LEVEL_GROUP_TEMPLET_1.json', 'SKILL_LEVEL_GROUP_TEMPLET_2.json'):
        for r in rows(T / fn):
            lvg[r['SkillLevelGroupID']] = r
    se = {}
    for fn in ('SE_TEMPLET_SKILL_1.json', 'SE_TEMPLET_SKILL_2.json'):
        for r in rows(T / fn):
            se[r['m_SEStrID']] = r
    dmg = {r['DTStrID']: r for r in rows(T / 'DAMAGE_TEMPLET.json')}
    buffs = {r['m_BuffStrID']: r for r in rows(T / 'BUFF_TEMPLET.json')}
    bt = next(r for r in rows(T / 'BATTLE_TEMPLET_GUILD_DUNGEON.json') if r['BattleID'] == BATTLE_ID)
    need(bt['BattleTempletFileName'].startswith(SCRIPT), '전투 표의 배치 파일 변경')

    def unit_block(sp, kind):
        u = units[sp['UnitStrId']]
        s = stats[u['m_StatStrID']]['m_StatData']
        g = sapl.get(stats[u['m_StatStrID']].get('m_StatAddPerLevelStrID'), {})
        need(not any(g.get(k) for k in ('NST_HP', 'NST_ATK', 'NST_DEF')), '레벨 성장값이 생김(%s)' % u['m_UnitStrID'])
        el = sp.get('ChangeAdjustType')
        el = el if el and el != 'NUAT_INVALID' else u['NKM_UNIT_ADJUST_TYPE']
        flag = 'A' if sp.get('AllSkillAvailable') else {(True, True): 'B', (True, False): 'S', (False, True): 'H'}.get(
            (bool(sp.get('SpecialSkillAvailable')), bool(sp.get('HyperSkillAvailable'))), 'N')
        add = sp.get('AddStatData') or {}
        return dict(id=u['m_UnitStrID'], kind=kind, element=NUAT[el], unitElement=NUAT[u['NKM_UNIT_ADJUST_TYPE']],
                    role=ROLE[u['m_NKM_UNIT_ROLE_TYPE']], boss=bool(sp.get('IsBoss')), pos=sp['SpawnPosIndex'], spawn=flag,
                    stats=dict(hp=s['NST_HP'], atk=s['NST_ATK'], **{'def': s['NST_DEF']}, spd=s['NST_TURN_SPEED'],
                               cr=s['NST_RATE_CRITICAL'], cd=s['NST_RATE_CRITICAL_DAMAGE'], eh=s['NST_RATE_EFFECT_HIT'],
                               er=s['NST_RATE_EFFECT_EVADE'], der=s.get('NST_RATE_DEFINITE_EFFECT_EVADE', 0), sa=s['NST_SUPER_ARMOR']),
                    addStat=dict(hpp=add.get('NST_NV_RATE_HP', 0), atkp=add.get('NST_NV_RATE_ATK', 0),
                                 defp=add.get('NST_NV_RATE_DEF', 0), spdp=add.get('NST_NV_RATE_TURN_SPEED', 0)),
                    skills=u['m_listSkill'])

    def ses(name):
        sk = skills[name]
        return [se[x] for x in lvg[sk['SkillLevelGroup']]['SkillLevelSE']]

    def coef(name):
        sk = skills[name]
        return dmg[sk['DTStrID']]['AtkFactor'] if sk.get('DTStrID') else 0

    minion = unit_block(waves[0]['TeamBSpawnList'][0], 'minion')
    need(minion['id'] == unit_block(waves[0]['TeamBSpawnList'][1], 'minion')['id'], '졸개 2기가 다른 유닛')
    boss = unit_block(waves[1]['TeamBSpawnList'][0], 'boss')
    need(boss['boss'] and boss['skills'] == [BOSS_SK + x for x in ('ATTACK', 'SPECIAL', 'HYPER', 'PASSIVE1', 'PASSIVE2', 'PASSIVE3')],
         '보스 스킬 목록 변경')
    for k, exp in EXPECT.items():
        got = [(r['m_BuffStrID'], r.get('SkillConditionId')) for r in ses(BOSS_SK + k)]
        need(got == exp, 'SE 배열 변경: %s %s' % (k, got))
    p2 = ses(BOSS_SK + 'PASSIVE2')
    need([r.get('SkillConditionId') for r in p2] == PASSIVE2_CONDS, 'PASSIVE2 조건 배열 변경')
    crit = lvg[skills[BOSS_SK + 'PASSIVE1']['SkillLevelGroup']].get('SkillLevelStat') or []
    sp = ses(BOSS_SK + 'SPECIAL')
    st = {k: skills[BOSS_SK + k] for k in ('ATTACK', 'SPECIAL', 'HYPER', 'SPECIAL2', 'HYPER2')}
    need(st['SPECIAL']['m_NKM_SKILL_TYPE'] == 'NST_REACT' and st['SPECIAL']['ReactConditionID'] == 52093, '정실 어필 반응 조건 변경')

    def bstat(name, typ):
        for s in buffs[name].get('Stats') or []:
            if s['NKM_STAT_TYPE'] == typ:
                return s.get('NKM_STAT_TYPE_RATE', s.get('NKM_STAT_TYPE_VALUE'))
        raise Changed('버프 능력치 없음: %s %s' % (name, typ))

    b2 = buffs['BI_AUTOMATON_MINIGUN_BOSS_2']
    need(sorted(f['StatTypeFix'] for f in b2['FixStats']) == ['NST_ATK', 'NST_DEF', 'NST_TURN_SPEED'] and b2['ImmuneSpeedGaugeUp'],
         '들러리 고정 능력치 변경')
    hy, hy2 = ses(BOSS_SK + 'HYPER'), ses(BOSS_SK + 'HYPER2')
    s2 = ses(BOSS_SK + 'SPECIAL2')
    m_at, m_sp = ses(minion['skills'][0]), ses(minion['skills'][1])
    need([r['m_BuffStrID'] for r in m_at] == ['BI_SPEED_GAUGE_DOWN'] and [r['m_BuffStrID'] for r in m_sp] == ['BI_SPEED_INCREASE'],
         '졸개 SE 변경')
    out = dict(
        _note='길드 방어전 시즌4 EX(BFB) 엔진 수치. tools/build_guild_bfb.py 가 비공개 게임 표에서 생성(손으로 고치지 말 것). '
              '비율 단위 1/10000. 명세: AI/temp/partynavigator/work/guild_defense/bfb_skill_spec.md',
        season=30111, battleId=BATTLE_ID, script=SCRIPT, limitTurn=bt['LimitTurn'], battleLevel=bt['BattleLevel'],
        power=bt['BattlePower'], mode=bt['BattleMode'],
        minion=dict(minion, names='난폭한 신부 지원자',
                    attack=dict(coef=coef(minion['skills'][0]), cd=skills[minion['skills'][0]]['m_CoolTurn'],
                                gaugeDown=m_at[0]['SpeedGaugeRate'], chance=m_at[0]['m_Condition'].get('m_fActiveRate', 10000)),
                    special=dict(coef=coef(minion['skills'][1]), cd=skills[minion['skills'][1]]['m_CoolTurn'],
                                 speedUp=bstat('BI_SPEED_INCREASE', 'NST_NV_RATE_TURN_SPEED'), dur=m_sp[0]['m_BuffLifeTurn'])),
        boss=dict(boss, name='BFB',
                  critRate=sum(s['SkillLevelStatRate'] for s in crit if s['SkillLevelStatType'] == 'NST_RATE_CRITICAL'),
                  pen=ses(BOSS_SK + 'ATTACK')[0]['Stats'][0]['NKM_STAT_TYPE_RATE'],
                  attack=dict(coef=coef(BOSS_SK + 'ATTACK'), cd=st['ATTACK']['m_CoolTurn'], tough=st['ATTACK'].get('SuperArmorBreakValue', 0)),
                  hyper=dict(coef=coef(BOSS_SK + 'HYPER'), cd=st['HYPER']['m_CoolTurn'], tough=st['HYPER'].get('SuperArmorBreakValue', 0),
                             gaugeUp=hy[1]['SpeedGaugeRate']),
                  special2=dict(coef=coef(BOSS_SK + 'SPECIAL2'), cd=st['SPECIAL2']['m_CoolTurn'], tough=st['SPECIAL2'].get('SuperArmorBreakValue', 0),
                                atkDown=bstat('BI_ATTACK_DECREASE', 'NST_NV_RATE_ATK'), atkDownDur=s2[1]['m_BuffLifeTurn'],
                                atkUp=bstat('BI_ATTACK_INCREASE', 'NST_NV_RATE_ATK'), atkUpDur=s2[2]['m_BuffLifeTurn']),
                  hyper2=dict(coef=coef(BOSS_SK + 'HYPER2'), cd=st['HYPER2']['m_CoolTurn'], tough=st['HYPER2'].get('SuperArmorBreakValue', 0),
                              atkDown=bstat('BI_ATTACK_DECREASE', 'NST_NV_RATE_ATK'), spdDown=bstat('BI_SPEED_DECREASE', 'NST_NV_RATE_TURN_SPEED'),
                              dur=hy2[1]['m_BuffLifeTurn'], gaugeUp=hy2[3]['SpeedGaugeRate']),
                  bridal=dict(atkPerStack=bstat('BI_AUTOMATON_MINIGUN_BOSS_1', 'NST_NV_RATE_ATK'),
                              max=buffs['BI_AUTOMATON_MINIGUN_BOSS_1']['BuffLevelMax'],
                              countMax=buffs['BI_AUTOMATON_MINIGUN_BOSS_7']['BuffLevelMax'], trigger=5),
                  appeal=dict(barrierRate=sp[7]['BarrierRate'],
                              slowSpd=bstat('BI_AUTOMATON_MINIGUN_BOSS_9', 'NST_NV_RATE_TURN_SPEED'),
                              slowAtk=bstat('BI_AUTOMATON_MINIGUN_BOSS_9', 'NST_NV_RATE_ATK'),
                              maidDmgTaken=-bstat('BI_AUTOMATON_MINIGUN_BOSS_2', 'NST_RATE_DAMAGE_REDUCE')),
                  shieldHits=buffs['BI_AUTOMATON_MINIGUN_BOSS_3']['BuffLevelMax'],
                  bouquet=dict(atk=bstat('BI_AUTOMATON_MINIGUN_BOSS_4', 'NST_NV_RATE_ATK'), dur=p2[22]['m_BuffLifeTurn'],
                               allyGauge=p2[23]['SpeedGaugeRate'], selfGaugeDown=p2[24]['SpeedGaugeRate'], selfChainHp=p2[27]['AddDamageRate']),
                  punishChainHp=ses(BOSS_SK + 'PASSIVE3')[0]['AddDamageRate']),
    )
    atomic_json(args.out, out)
    print('저장', args.out)


if __name__ == '__main__':
    try:
        main()
    except Changed as ex:
        raise SystemExit('게임 표 구조가 명세와 다름(사람 확인 필요): %s' % ex)
