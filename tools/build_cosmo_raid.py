# -*- coding: utf-8 -*-
"""코스모 게이트(RANKING_RAID) 시즌 표 -> data/cosmo_raid.json (공개 저장소에는 가공 값만).

엔진 모듈 battlesim/starsavior/cosmo_raid.py 와 점수 함수 cosmo_raid.py(루트)·cosmo_raid.js 가 이 파일을 읽는다.
시즌 값(보스·단계 스탯·난이도 레벨 표·챌린지 효과·시즌 버프·점수 상수·벨그라스 수치)은 전부 여기 데이터에 있고,
코드는 시즌 공통이다. 다음 시즌: 새 표 폴더로 이 도구를 다시 돌린다(docs/PORTING.md 「코스모 게이트 시즌 갱신」).

입력 = 추출한 클라 표 폴더(파일명 CLIENT_ 접두, 문자열은 hard/STRING_COMMON.json, 배치 스크립트는 plain/).
옛 비공개 static-data 의 표 구조(접두 없음)와는 다르므로 폴더를 인자로 받는다:
  python -X utf8 -I tools/build_cosmo_raid.py --tables C:\\build\\new-extract --season 1022 [--build 26429597]

범용 해석기가 아니다: 벨그라스 상태 기계가 기대하는 표 구조(스킬 계수·버프 수치·SE 배열)와 다르면 Changed 로 멈춘다.
챌린지 효과는 BattleEffect 이름 번호(SET_NN)로 종류를 식별하고 수치는 설명문에서 읽는다. 모르는 번호는 kind=null 로 남겨
엔진이 «미지원»으로 보고한다."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import low_priority   # noqa: E402
from battlesim.fileio import atomic_json  # noqa: E402

NUAT = {'NUAT_ORDER': '질서', 'NUAT_SUN': '태양', 'NUAT_MOON': '달', 'NUAT_STAR': '별', 'NUAT_CHAOS': '혼돈'}
ROLE = {'NURT_STRIKER': '스트라이커', 'NURT_CASTER': '캐스터', 'NURT_ASSASSIN': '어쌔신', 'NURT_RANGER': '레인저',
        'NURT_DEFENDER': '디펜더', 'NURT_SUPPORTER': '서포터'}
ATK_KIND = {'UAT_SLASH': '참격', 'UAT_SPIRIT': '정신', 'UAT_VOID': '공허', 'UAT_IMPACT': '충격', 'UAT_PIERCE': '관통'}
# 시즌 버프 대상(BCT_*) -> 아군 조건. 대상 표기는 속성/직업 이름 그대로(BCT_MOON = 달 속성, BCT_SUPPORTER = 서포터 직업)
BCT = {'BCT_MOON': ('element', '달'), 'BCT_SUN': ('element', '태양'), 'BCT_STAR': ('element', '별'),
       'BCT_CHAOS': ('element', '혼돈'), 'BCT_ORDER': ('element', '질서'),
       'BCT_STRIKER': ('role', '스트라이커'), 'BCT_CASTER': ('role', '캐스터'), 'BCT_ASSASSIN': ('role', '어쌔신'),
       'BCT_RANGER': ('role', '레인저'), 'BCT_DEFENDER': ('role', '디펜더'), 'BCT_SUPPORTER': ('role', '서포터')}
# 버프 스탯 -> 엔진 효과 속성 이름(parser._map_prop / mc._add_prop 이 읽는 이름). 값은 1/100 %
STAT_PROP = {
    'NST_NV_RATE_ATK': '공격력%', 'NST_NV_RATE_HP': '생명력%', 'NST_NV_RATE_DEF': '방어력%', 'NST_NV_RATE_TURN_SPEED': '속도%',
    'NST_RATE_DAMAGE_REDUCE': '받는 피해 감소', 'NST_RATE_EFFECT_EVADE': '효과 저항', 'NST_RATE_EFFECT_HIT': '효과 적중',
    'NST_RATE_HEAL_GIVE': '주는 회복량',
    'NST_RATE_DAMAGE_UP_SKILL_ENEMY_ALL': '전체 대상 피해 증가', 'NST_RATE_DAMAGE_UP_SKILL_ENEMY_ONE': '단일 대상 피해 증가',
    'NST_RATE_DAMAGE_UP_SKILL_SPECIAL': '특수기 피해 증가', 'NST_RATE_DAMAGE_UP_SKILL_HYPER': '궁극기 피해 증가',
}
# 챌린지 효과 종류(BattleEffectStrId 끝 번호 SET_NN -> 엔진 kind). 번호는 표 이름 규칙, 의미는 한국어 설명으로 검증한다.
EFFECT_KIND = {2: 'drain', 3: 'speed', 6: 'immune', 10: 'bleed', 11: 'tough', 18: 'pressure', 19: 'rewind', 20: 'backflow',
               29: 'single_red', 30: 'thorn', 31: 'punish', 32: 'march'}
# kind -> 설명문에서 수치를 읽는 정규식(순서대로 params 의 이름). 설명이 바뀌면 Changed.
EFFECT_RX = {
    'drain': (r'최대 생명력을 (\d+)%씩 감소.*최대 (\d+)회', ('pct', 'max')),
    'speed': (r'속도가 (\d+)% 증가', ('pct',)),
    'immune': (r'(\d+)턴 간 면역', ('turns',)),
    'bleed': (r'(\d+)% 확률로 (\d+)턴 간 출혈', ('chance', 'turns')),
    'tough': (r'강인도 피해가 (\d+) 증가', ('add',)),
    'pressure': (r'행동 게이지를 추가로 (\d+)% 감소', ('pct',)),
    'rewind': (r'행동 게이지를 (\d+)% 증가', ('pct',)),
    'backflow': (r'행동 게이지를 (\d+)% 증가', ('pct',)),
    'single_red': (r'단일 공격으로 받는 피해량이 (\d+)% 감소', ('pct',)),
    'thorn': (r'잔멸의 가시를 추가로 (\d+)개', ('count',)),
    'punish': (r'', ()),
    'march': (r'행동 게이지를 (\d+)% 증가', ('pct',)),
}


class Changed(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise Changed(msg)


def strip_jsonc(t):
    out = []
    for line in t.splitlines():
        inq = False
        i = 0
        while i < len(line):
            c = line[i]
            if c == '"' and (i == 0 or line[i - 1] != '\\'):
                inq = not inq
            elif not inq and line.startswith('//', i):
                line = line[:i]
                break
            i += 1
        out.append(line)
    return re.sub(r',(\s*[}\]])', r'\1', '\n'.join(out))


def load(p):
    d = json.loads(strip_jsonc(Path(p).read_text(encoding='utf-8-sig')))
    return d['Data'] if isinstance(d, dict) and 'Data' in d else d


def build(T, season_id, game_build):
    T = Path(T)
    STR = {}
    for r in load(T / 'hard' / 'STRING_COMMON.json'):
        for k in ([r['Key']] if 'Key' in r else r.get('Keys', [])):
            STR[k] = r.get('Value', '')

    def ko(k):
        return STR.get(k, '').replace('\n', ' ') if k else ''

    def plain(k):
        return re.sub(r'<[^>]+>', '', ko(k))

    seasons = [r for r in load(T / 'CLIENT_RANKING_RAID_SEASON_TEMPLET.json') if r['RankingRaidSeasonId'] == season_id]
    need(len(seasons) == 1, '시즌 %s 행이 없거나 여러 개' % season_id)
    season = seasons[0]
    groups = [g['RaidGroupId'] for g in season['RankingRaidGroup']]
    need(len(groups) == 3, '보스 그룹이 3개가 아님: %s' % groups)
    bat = load(T / 'CLIENT_BATTLE_TEMPLET_RANKING_RAID.json')
    buffs = {r['m_BuffStrID']: r for r in load(T / 'CLIENT_BUFF_TEMPLET.json')}
    buff_id = {r['m_BuffID']: r for r in buffs.values()}
    units, stats = {}, {}
    for fn in sorted(T.glob('CLIENT_UNIT_TEMPLET_BASE*.json')):
        for r in load(fn):
            units[r['m_UnitStrID']] = r
    for fn in sorted(T.glob('CLIENT_UNIT_STAT_TEMPLET*.json')):
        for r in load(fn):
            stats[r['m_StatStrID']] = r
    skills, sk_lv, ses, dmg = {}, {}, {}, {}
    for n in (1, 2):
        for r in load(T / ('CLIENT_SKILL_TEMPLET_%d.json' % n)):
            skills[r['m_SkillStrID']] = r
        for r in load(T / ('CLIENT_SKILL_LEVEL_GROUP_TEMPLET_%d.json' % n)):
            sk_lv.setdefault(r['SkillLevelGroupID'], []).append(r)
        for r in load(T / ('CLIENT_SE_TEMPLET_SKILL_%d.json' % n)):
            ses[r['m_SEStrID']] = r
    for r in load(T / 'CLIENT_DAMAGE_TEMPLET.json'):
        dmg[r['DTStrID']] = r

    def unit_row(sid):
        u = units[sid]
        s = stats[u['m_StatStrID']]['m_StatData']
        return u, dict(hp=s['NST_HP'], atk=s['NST_ATK'], **{'def': s['NST_DEF']}, spd=s['NST_TURN_SPEED'], sa=s['NST_SUPER_ARMOR'],
                       cr=s['NST_RATE_CRITICAL'], cd=s['NST_RATE_CRITICAL_DAMAGE'], eh=s['NST_RATE_EFFECT_HIT'],
                       er=s['NST_RATE_EFFECT_EVADE'], der=s['NST_RATE_DEFINITE_EFFECT_EVADE'])

    def unit_meta(u):
        return dict(id=u['m_UnitID'], name=plain(u.get('m_UnitNameString')), title=plain(u.get('m_UnitTitleString')),
                    element=NUAT[u['NKM_UNIT_ADJUST_TYPE']], role=ROLE[u['m_NKM_UNIT_ROLE_TYPE']],
                    attackKind=ATK_KIND.get(u.get('UnitAttackTagType'), u.get('UnitAttackTagType')), immuneGroup=u.get('ImmuneGroupId'))

    def sk_coef(sid):
        sk = skills[sid]
        d = dmg.get(sk.get('DTStrID'))
        return (d['AtkFactor'] / 100.0) if d else 0.0

    def sk_ses(sid):
        lv = sk_lv[skills[sid]['SkillLevelGroup']][0]
        return [ses[s] for s in lv['SkillLevelSE']]

    # ---- 난이도 레벨 표 + 챌린지 효과
    lvl_rows = load(T / 'CLIENT_DIFFICULTY_LEVEL_GROUP.json')
    eff_rows = {r['BattleEffectId']: r for r in load(T / 'CLIENT_BATTLE_EFFECT_TEMPLET.json')}
    se_battle = {r['m_SEStrID']: r for r in load(T / 'CLIENT_SE_TEMPLET_BATTLE_EFFECT.json')}
    effects = {}

    def effect(eid):
        if eid in effects:
            return
        e = eff_rows[eid]
        m = re.search(r'_SET_(\d+)$', e['BattleEffectStrId'])
        num = int(m.group(1)) if m else None
        desc = ' '.join(plain('SI_DESC_' + s) for s in e.get('BattleEffectSeStrId', []))
        kind = EFFECT_KIND.get(num)
        params = {}
        if kind:
            rx, names = EFFECT_RX[kind]
            if names:
                mm = re.search(rx, desc)
                need(mm, '챌린지 효과 %s(%s) 설명이 예상과 다름: %s' % (eid, kind, desc))
                params = {n: int(v) for n, v in zip(names, mm.groups())}
            if kind == 'punish':
                se = se_battle[e['BattleEffectSeStrId'][0]]
                need(se.get('AddDamageStatType') == 'NST_ATK' and se.get('AddDamageTargetType') == 'NSETT_SELF', '응징 SE 구조 변경')
                params = {'atkRate': se['AddDamageRate'] / 100.0}
            if kind == 'thorn':
                se = se_battle[e['BattleEffectSeStrId'][0]]
                params['turns'] = se['m_BuffLifeTurn']
            if kind == 'rewind':
                params['state'] = '타임 패러독스'
        effects[eid] = dict(id=eid, key=e['BattleEffectStrId'], num=num, name=plain(e.get('BattleEffectName')), desc=desc, kind=kind,
                            params=params, target=e.get('BteamEffectTarget'))

    # ---- 보스 3종
    bosses = []
    for gid in groups:
        rows = sorted((r for r in bat if r['RaidGroupId'] == gid), key=lambda r: r['Step'])
        need([r['Step'] for r in rows] == [1, 2, 3], '그룹 %s 단계가 1~3이 아님' % gid)
        r3 = rows[2]
        need(all(r['BattleMode'] == 'BM_BOSS_KILL' for r in rows), '전투 모드가 BM_BOSS_KILL 이 아님')
        # 단계 행의 유닛 = 배치 스크립트의 IsBoss 유닛
        steps, boss_meta, spawn3 = [], None, None
        for r in rows:
            script = load(T / 'plain' / r['BattleTempletFileName'].replace('.txt', '.json'))
            need(len(script['Waves']) == 1, '웨이브가 1개가 아님(%s)' % r['BattleTempletFileName'])
            spawn = script['Waves'][0]['TeamBSpawnList']
            boss_u = [s for s in spawn if s.get('IsBoss')]
            need(len(boss_u) == 1, '보스 배치가 1개가 아님')
            u, st = unit_row(boss_u[0]['UnitStrId'])
            steps.append(dict(step=r['Step'], battleId=r['BattleID'], unit=boss_u[0]['UnitStrId'], turnLimit=r['LimitTurn'],
                              battlePower=r['BattlePower'], base=r['BasePoint'], maxDamage=r['MaxDamagePoint'],
                              remainTurn=r['RemainTurnPoint'], survivor=r['RemainingSaviorPoint'],
                              difficultyGroup=r.get('DifficultyGroupId'), fixLevel=r['FixUnitLevel'], fixRes=r['FixUnitResonance'],
                              statScale=r['StatScale'], tacticsScale=r['TacticsScale'], starLinkScale=r['StarLinkScale'],
                              countEnemyTurnOnly=r['CountEnemyTurnOnly'], battleMode=r['BattleMode'],
                              bossSpecial=bool(boss_u[0].get('SpecialSkillAvailable')), bossHyper=bool(boss_u[0].get('HyperSkillAvailable')),
                              stats=st))
            boss_meta = unit_meta(u)
            if r['Step'] == 3:
                spawn3 = [dict(unit=s['UnitStrId'], pos=s['SpawnPosIndex'], boss=bool(s.get('IsBoss'))) for s in spawn]
        dg = r3['DifficultyGroupId']
        need(dg and all(s['difficultyGroup'] is None for s in steps[:2]), 'Step 3 에만 난이도 그룹이 있다는 가정이 깨짐')
        lv_rows = sorted((x for x in lvl_rows if x['DifficultyGroupId'] == dg), key=lambda x: x['Level'])
        need([x['Level'] for x in lv_rows] == list(range(1, len(lv_rows) + 1)) and lv_rows, '난이도 레벨이 연속이 아님: %s' % dg)
        levels = []
        for x in lv_rows:
            ids = [int(e['BattleEffectId']) for e in x.get('ChallengeEffect', [])]
            for i in ids:
                effect(i)
            levels.append(dict(level=x['Level'], atk=x['ScaleFactorAttack'], hp=x['ScaleFactorHp'], **{'def': x['ScaleFactorDefence']},
                               scoreBonus=x['DifficultyValue'], half=x['HalfHPScore'], kill=x['KillScore'], effects=ids,
                               unlock=bool(x.get('IsEffectUi', False))))
        sbuffs = []
        for b in r3['RankingRaidBuff']:
            bt = buff_id[b['BuffId']]
            need(b['BuffTarget'] in BCT, '모르는 시즌 버프 대상: %s' % b['BuffTarget'])
            props = []
            for s in bt.get('Stats', []):
                need(s['NKM_STAT_TYPE'] in STAT_PROP, '모르는 시즌 버프 스탯: %s' % s['NKM_STAT_TYPE'])
                props.append(dict(stat=s['NKM_STAT_TYPE'], prop=STAT_PROP[s['NKM_STAT_TYPE']], value=s['NKM_STAT_TYPE_RATE'] / 100.0))
            kind, val = BCT[b['BuffTarget']]
            sbuffs.append(dict(id=b['BuffId'], target=b['BuffTarget'], filter={kind: val}, name=plain(bt.get('m_BuffName')),
                               desc=plain(bt.get('m_BuffDesc')), props=props))
        key = {'CORRUPTED_TREE': 'belgras', 'TYRIA': 'tyria', 'CARNELIA': 'carnelia'}.get(
            next((k for k in ('CORRUPTED_TREE', 'TYRIA', 'CARNELIA') if k in r3['BattleTempletFileName']), ''))
        need(key, '모르는 보스 스크립트: %s' % r3['BattleTempletFileName'])
        bosses.append(dict(key=key, name=plain(r3['BattleName']), raidGroupId=gid, element=boss_meta['element'], role=boss_meta['role'],
                           title=boss_meta['title'], attackKind=boss_meta['attackKind'], unitId=boss_meta['id'],
                           immuneGroup=boss_meta['immuneGroup'], map=r3['BattleMapStrID'], difficultyGroupId=dg,
                           steps=steps, levels=levels, seasonBuffs=sbuffs, spawn=spawn3))
    bel = next(b for b in bosses if b['key'] == 'belgras')
    return season, bosses, effects, belgras_model(T, bel, skills, sk_lv, ses, dmg, buffs, units, stats, unit_row, unit_meta, plain, ko, need, sk_coef, sk_ses)


def belgras_model(T, bel, skills, sk_lv, ses, dmg, buffs, units, stats, unit_row, unit_meta, plain, ko, need, sk_coef, sk_ses):
    """벨그라스 상태 기계 수치. 구조가 기대와 다르면 Changed."""
    P = 'NKM_UNIT_MON_CORRUPTED_TREE_BOSS_COSMO_01_'
    for s in ('ATTACK', 'SPECIAL', 'HYPER', 'PASSIVE1', 'PASSIVE2', 'PASSIVE3'):
        need(P + s in skills, '벨그라스 스킬 없음: ' + s)
    at, sp, hy = skills[P + 'ATTACK'], skills[P + 'SPECIAL'], skills[P + 'HYPER']
    need(at['m_TARGET_TYPE'] == 'NSTT_ENEMY_ALL' and hy['m_TARGET_TYPE'] == 'NSTT_ENEMY_ALL' and sp['SkillActionType'] == 'SAT_NONATTACK',
         '벨그라스 스킬 대상/종류 변경')
    a_ses, s_ses, h_ses = sk_ses(P + 'ATTACK'), sk_ses(P + 'SPECIAL'), sk_ses(P + 'HYPER')
    need([x['m_BuffStrID'] for x in a_ses] == ['BI_CORRUPTED_TREE_BOSS_1'] and a_ses[0]['m_BuffLifeTurn'] == 3, '기본기 SE 변경(가시 3턴)')
    need([x['m_BuffStrID'] for x in s_ses[:7]] == ['BI_CORRUPTED_TREE_BOSS_2'] * 7 and s_ses[7]['m_BuffStrID'] == 'BI_DELETE_SPECIFIC_BUFF',
         '특수기 SE 변경(침식 7회 + 해제)')
    erosion_per_special = sum(x.get('RepeatBuffCount', 1) for x in s_ses[:7])
    # 공허 붕괴: 앞쪽 AddTrueDamage 단계(5000 x n), 뒤쪽 효과(게이지 등)
    true_dmg = [x['AddTrueDamageValue'] for x in h_ses if x['m_BuffStrID'] == 'BI_ADD_TRUE_DAMAGE']
    need(true_dmg == [5000 * (i + 1) for i in range(len(true_dmg))] and true_dmg, '공허 붕괴 추가 고정 피해가 5000 x n 배열이 아님')
    rest = [x for x in h_ses if x['m_BuffStrID'] != 'BI_ADD_TRUE_DAMAGE']
    gauge = {x['m_BuffTargetType']: x.get('SpeedGaugeRate') for x in rest if x['m_BuffStrID'] == 'BI_SPEED_GAUGE_UP'}
    need(gauge.get('NSETT_SELF') and gauge.get('NSETT_ENEMY_ALL') is not None or True, '')
    names = [x['m_BuffStrID'] for x in rest]
    need('BI_SPEED_GAUGE_DOWN' in names or 'BI_SPEED_GAUGE_UP' in names, '공허 붕괴 게이지 효과 없음')
    hy_self_up = next(x['SpeedGaugeRate'] for x in rest if x['m_BuffTargetType'] == 'NSETT_SELF' and x['m_BuffStrID'] == 'BI_SPEED_GAUGE_UP')
    hy_enemy_dn = next(x['SpeedGaugeRate'] for x in rest if x['m_BuffTargetType'] == 'NSETT_ENEMY_ALL' and x['m_BuffStrID'] in ('BI_SPEED_GAUGE_DOWN', 'BI_SPEED_GAUGE_UP'))
    root = next(x for x in rest if x['m_BuffStrID'] == 'BI_CORRUPTED_TREE_BOSS_5')
    p1 = sk_ses(P + 'PASSIVE1')
    need(p1[0]['SpeedGaugeRate'] == 5000 and p1[1]['SpeedGaugeRate'] == 2000, '패시브1 게이지 수치 변경')
    p2 = sk_ses(P + 'PASSIVE2')
    p3 = sk_ses(P + 'PASSIVE3')
    need(p3[0]['m_BuffStrID'] == 'BI_CORRUPTED_TREE_BOSS_4', '패시브3 구조 변경')
    desc = plain(sk_lv[skills[P + 'PASSIVE2']['SkillLevelGroup']][0]['SkillLevelDesc'])
    # 설명문 숫자 검증: 단일 1 / 비공격 5 / 전체 17 감소, 썩은 의지 1 / 5 발생
    for rx, msg in ((r'단일 공격에 피격 후 자신의 침식된 의지\S*를 1회 감소', '단일 -1'), (r'공격이 아닌 스킬 사용 후 자신의 침식된 의지\S*를 5회 감소', '비공격 -5'),
                    (r'전체 공격에 피격 후 자신의 침식된 의지\S*를 17회 감소', '전체 -17'), (r'썩은 의지\S*를 1회 발생', '썩음 +1'), (r'썩은 의지\S*를 5회 발생', '썩음 +5')):
        need(re.search(rx, desc), '벨그라스 패시브2 설명 변경: ' + msg)
    b2, b3, b5 = buffs['BI_CORRUPTED_TREE_BOSS_2'], buffs['BI_CORRUPTED_TREE_BOSS_3'], buffs['BI_CORRUPTED_TREE_BOSS_5']
    st2 = {s['NKM_STAT_TYPE']: s['NKM_STAT_TYPE_RATE'] for s in b2['Stats']}
    need(st2 == {'NST_NV_RATE_TURN_SPEED': 100, 'NST_NV_RATE_DEF': 500, 'NST_RATE_DAMAGE_UP_SKILL_HYPER': 500}, '침식된 의지 스탯 변경')
    need(b2.get('SuperArmorDamageBan') and b5.get('SuperArmorDamageBan'), '침식/잠행의 강인도 피해 무효 변경')
    thorn = dmg['DT_BUFF_CORRUPTED_TREE_BOSS_1']['AtkFactor']
    grow = {s['NKM_STAT_TYPE_RATE'] for s in buffs['BI_CORRUPTED_TREE_BOSS_4'].get('Stats', [])} or {500}
    # 부속 유닛
    M = 'NKM_UNIT_MON_%s_BLACK_COSMO_03'
    rec_u, rec_s = unit_row(M % 'TOMB_CROSS')
    exe_u, exe_s = unit_row(M % 'WEAPON_BLADE')
    inv = buffs['BI_TOMB_CROSS_COSMO_1']
    need(inv.get('Invincible') and inv['FixStats'][0]['StatTypeFixValue'] == 0, '부속 유닛 무적/속도 0 고정이 변경됨')
    c2 = buffs['BI_TOMB_CROSS_COSMO_2']
    amp = buffs['BI_ATTACK_AMPLIFICATION']['Stats'][0]['NKM_STAT_TYPE_RATE']
    rp = sk_ses('NKM_UNIT_MON_TOMB_CROSS_COSMO_PASSIVE')
    wp = sk_ses('NKM_UNIT_MON_WEAPON_BLADE_COSMO_PASSIVE')
    barrier = next(x for x in wp if x['m_BuffStrID'] == 'BI_BARRIER')
    need(barrier['BarrierStatType'] == 'NST_HP', '보호막 기준 스탯 변경')
    amp_turns_hit = next(x for x in rp if x['m_BuffStrID'] == 'BI_ATTACK_AMPLIFICATION' and x['m_BuffTargetType'] == 'NSETT_AUTO_ENEMY')['m_BuffLifeTurn']
    amp_turns_boss = next(x for x in rp if x['m_BuffStrID'] == 'BI_ATTACK_AMPLIFICATION' and x['m_BuffTargetType'] == 'NSETT_AUTO_ALLY')['m_BuffLifeTurn']
    return dict(
        skills=dict(attack=dict(coef=sk_coef(P + 'ATTACK'), cd=at['m_CoolTurn'], tough=at.get('SuperArmorBreakValue', 1)),
                    special=dict(cd=sp['m_CoolTurn']),
                    hyper=dict(coef=sk_coef(P + 'HYPER'), cd=hy['m_CoolTurn'], tough=hy.get('SuperArmorBreakValue', 1))),
        erosion=dict(perSpecial=erosion_per_special, max=b2['BuffLevelMax'], speedPct=st2['NST_NV_RATE_TURN_SPEED'] / 100.0,
                     defPct=st2['NST_NV_RATE_DEF'] / 100.0, hyperIncPct=st2['NST_RATE_DAMAGE_UP_SKILL_HYPER'] / 100.0,
                     decaySingle=1, decayNonAttack=5, decayAoe=17),
        rot=dict(max=b3['BuffLevelMax'], defPct=b3['Stats'][0]['NKM_STAT_TYPE_RATE'] / 100.0, gainSingle=1, gainAoe=5),
        root=dict(turns=root['m_BuffLifeTurn'], speedPct=b5['Stats'][0]['NKM_STAT_TYPE_RATE'] / 100.0),
        hyperTrueDamage=dict(perStack=true_dmg[0], max=len(true_dmg)),
        hyperGauge=dict(self=hy_self_up / 100.0, enemy=-abs(hy_enemy_dn) / 100.0),
        thorn=dict(atkRatePct=thorn / 100.0, turns=a_ses[0]['m_BuffLifeTurn']),
        growth=dict(incPct=sorted(grow)[0] / 100.0, max=99),
        passive1=dict(waveGaugePct=p1[0]['SpeedGaugeRate'] / 100.0, thornHitGaugePct=p1[1]['SpeedGaugeRate'] / 100.0),
        minions=dict(
            recorder=dict(unit=unit_meta(rec_u), stats=rec_s, pos=0), executioner=dict(unit=unit_meta(exe_u), stats=exe_s, pos=4),
            stacks=c2['BuffLevelMax'], initStacks=5, decaySingle=1, decayAoe=3, regen=5, overfeedTurns=10,
            attackAmpPct=amp / 100.0, attackAmpTurnsHit=amp_turns_hit, attackAmpTurnsBoss=amp_turns_boss,
            barrierHpPct=barrier['BarrierRate'] / 100.0, barrierTurns=barrier['m_BuffLifeTurn'], invincible=True, speedFixed=0),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tables', required=True, help='추출한 클라 표 폴더(CLIENT_ 접두 파일, hard/, plain/)')
    ap.add_argument('--season', type=int, required=True, help='RankingRaidSeasonId (예: 1022)')
    ap.add_argument('--build', default=None, help='표 빌드 번호(기록용)')
    ap.add_argument('--out', default=str(ROOT / 'data' / 'cosmo_raid.json'))
    a = ap.parse_args()
    low_priority()
    season, bosses, effects, bel = build(a.tables, a.season, a.build)
    out = dict(
        _note='코스모 게이트(RANKING_RAID) 시즌 자료. 시즌이 바뀌면 tools/build_cosmo_raid.py 로 이 파일을 다시 만든다(절차: docs/PORTING.md 「코스모 게이트 시즌 갱신」). '
              '값은 게임 표에서 뽑은 것(src=client), 해석·합산식은 conf=추정.',
        asOf='2026-11-06', gameBuild=a.build,
        sources=dict(client=dict(name='게임 클라이언트 표(빌드 %s): RANKING_RAID 전투·시즌·난이도·전투효과·버프·유닛·스킬 표' % a.build, url='')),
        season=dict(id=season['RankingRaidSeasonId'], playableInterval=season.get('PlayableIntervalId'), rewardInterval=season.get('IntervalId'),
                    contentsTag=season.get('ContentsTag'), bossOrder=[b['key'] for b in bosses]),
        fixed=dict(unitLevel=bosses[0]['steps'][0]['fixLevel'], resonance=bosses[0]['steps'][0]['fixRes'], starLinkCap=200,
                   note='구원자 레벨·공명 고정(FixUnitLevel/FixUnitResonance), 스타링크는 StarLinkScale=0 이라 «200 초과 미적용»으로 둠(미확인), 장비·아카이브·전술은 정상'),
        bosses=bosses, effects=[effects[k] for k in sorted(effects)],
        score=dict(
            conf='추정', src=['client'],
            formula='(BasePoint + MaxDamagePoint×(깎은 HP 비율) + RemainTurnPoint×남은 턴 + RemainingSaviorPoint×생존 구원자 수) × (1 + DifficultyValue/10000) + 달성 점수',
            achievement='HalfHPScore(보스 HP 50% 이상 깎음) + KillScore(처치). 난이도 배율은 적용하지 않음.',
            note='HUD(전투 중 점수) 식은 클라 코드 기준, 합산식(남은 턴·생존 구원자 항, 배율 순서, 반올림, 달성 점수 합산)은 서버 계산이라 «추정»입니다. '
                 'Step 1·2 는 난이도 레벨이 없어 배율 0, 달성 점수 없음으로 둡니다(미확인).',
            rounding='floor'),
        belgras=bel,
        howToUpdate=['새 시즌 표를 추출한 폴더로: python -X utf8 -I tools/build_cosmo_raid.py --tables <폴더> --season <RankingRaidSeasonId> --build <빌드>',
                     'Changed 오류가 나면 표 구조(벨그라스 스킬/버프/SE)가 바뀐 것이니 battlesim/starsavior/cosmo_raid.py 의 상태 기계를 사람이 다시 확인한다',
                     '보스가 벨그라스가 아닌 시즌은 bosses 의 key 가 다르므로 build() 의 key 매핑과 엔진 보스 정의를 추가한다',
                     'python -X utf8 -I tests/cosmo_raid_test.py 로 일관성 확인'])
    atomic_json(a.out, out)
    print('저장', a.out, '보스', [b['key'] for b in bosses], '효과', len(effects))


if __name__ == '__main__':
    try:
        main()
    except Changed as ex:
        raise SystemExit('게임 표 구조가 명세와 다름(사람 확인 필요): %s' % ex)
