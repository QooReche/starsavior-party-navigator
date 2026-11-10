# -*- coding: utf-8 -*-
"""플래시 포인트(BOSS_RUSH) 스테이지 효과의 대상 조건 -> data/stage_fx.json (공개 저장소에는 가공 값만).

게임: BATTLE_TEMPLET_BOSS_RUSH.BattleEffectData[].BattleEffectId -> BATTLE_EFFECT_TEMPLET(AteamEffectTarget ALL,
BteamEffectTarget 없음, TargetAdjustType = 속성 / TargetRoleType = 직업 한정) -> SE_TEMPLET_BATTLE_EFFECT(NSETT_SELF, NSEAT_BATTLE_START).
클라 판정: NKM.Templets.decompiled.cs:36765-36799 (OBF_15649.OBF_22615: 팀별 대상 + 직업 + 속성 일치).
데이터북 스테이지 fx 문장(rawdata/foe.js)과 효과가 같은 순서로 대응하는지 능력치·수치를 대조해, 안 맞는 스테이지는 뺀다.

출력: stages["콘텐츠|탭|스테이지"] = fx 문장 순서대로 [속성|null, 직업|null].
사용: python -X utf8 -I tools/build_stage_fx.py [--static <비공개 저장소>]
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority   # noqa: E402
from tools import build_foe_spawn as SP   # noqa: E402
from battlesim.fileio import atomic_text   # noqa: E402
from battlesim.starsavior import foe as F   # noqa: E402

ADJ = {'NUAT_SUN': '태양', 'NUAT_MOON': '달', 'NUAT_STAR': '별', 'NUAT_ORDER': '질서', 'NUAT_CHAOS': '혼돈'}
ROLE = {'NURT_STRIKER': '스트라이커', 'NURT_CASTER': '캐스터', 'NURT_ASSASSIN': '어쌔신', 'NURT_RANGER': '레인저',
        'NURT_DEFENDER': '디펜더', 'NURT_SUPPORTER': '서포터'}
# 버프 -> 데이터북 문장 정규식(수치는 만분율 / 100 = %)
TEXT = {
    'BI_STAT_NST_RATE_CRITICAL_INFINITE': r'^치명타 확률이 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_RATE_CRITICAL_DAMAGE_INFINITE': r'^치명타 피해가 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_NV_RATE_DEF_INFINITE': r'^방어력이 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_NV_RATE_ATK_INFINITE': r'^공격력이 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_NV_RATE_HP_INFINITE': r'^생명력이 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_NV_RATE_TURN_SPEED_INFINITE': r'^속도가 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_RATE_DAMAGE_REDUCE_INFINITE': r'^받는 피해량이 (\d+)% 감소합니다\.$',
    'BI_STAT_NST_RATE_DAMAGE_UP_SKILL_ENEMY_ALL_INFINITE': r'^전체 공격으로 주는 피해량이 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_RATE_DAMAGE_UP_SKILL_ENEMY_ONE_INFINITE': r'^단일 공격으로 주는 피해량이 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_RATE_EFFECT_EVADE_INFINITE': r'^효과 저항이 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_RATE_EFFECT_HIT_INFINITE': r'^효과 적중이 (\d+)% 증가합니다\.$',
    'BI_STAT_NST_RATE_DAMAGE_VAMPIRISM_INFINITE': r'^생명력 흡수율이 (\d+)% 증가합니다\.$',
}


def table(static, name):
    return json.loads((Path(static) / 'tables' / (name + '.json')).read_text(encoding='utf-8'))['Data']


def build(static):
    report = Counter()
    eff = {r['BattleEffectId']: r for r in table(static, 'BATTLE_EFFECT_TEMPLET')}
    se = {r['m_SEStrID']: r for r in table(static, 'SE_TEMPLET_BATTLE_EFFECT')}
    rush = {r['BattleStrID']: r for r in table(static, 'BATTLE_TEMPLET_BOSS_RUSH')}
    sids = {}
    SP.build(static, sids)
    raw = F.load_foe(str(ROOT))
    texts = {}
    for c in raw['g']:
        for tb in c['tabs']:
            for s in tb['s']:
                texts['%s|%s|%s' % (c['k'], tb['t'], s['n'])] = s.get('fx') or []
    stages = {}
    for key, bid in sids.items():
        if bid not in rush:
            continue
        fx = texts.get(key) or []
        ids = [e['BattleEffectId'] for e in rush[bid].get('BattleEffectData') or []]
        if len(ids) != len(fx):
            report['효과 수와 문장 수 다름(제외)'] += 1
            continue
        conds, ok = [], True
        for i, t in zip(ids, fx):
            e = eff.get(i)
            try:
                if e.get('AteamEffectTarget') != 'ALL' or e.get('BteamEffectTarget') not in (None, 'NOT_APPLY') or e.get('TargetUnitId'):
                    raise ValueError('대상 %s/%s' % (e.get('AteamEffectTarget'), e.get('BteamEffectTarget')))
                s = se[e['BattleEffectSeStrId'][0]]
                if s['m_BuffTargetType'] != 'NSETT_SELF' or s['m_Condition']['m_ActiveType'] != 'NSEAT_BATTLE_START':
                    raise ValueError('SE 형식')
                m = re.match(TEXT[s['m_BuffStrID']], t)
                if not m or int(m.group(1)) * 100 != s['Stats'][0]['NKM_STAT_TYPE_RATE']:
                    raise ValueError('문장·수치 불일치 %s' % t)
                adj = ADJ[e['TargetAdjustType']] if e.get('TargetAdjustType') else None
                role = ROLE[e['TargetRoleType']] if e.get('TargetRoleType') else None
                conds.append([adj, role])
            except (KeyError, ValueError, TypeError, IndexError) as ex:
                report['제외 %s %s' % (key, ex)] += 1
                ok = False
                break
        if ok:
            stages[key] = conds
            report['연결'] += 1
    return stages, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    try:
        static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    stages, report = build(static)
    out = dict(_note='스테이지 효과 대상 조건(tools/build_stage_fx.py). stages[콘텐츠|탭|스테이지] = fx 문장 순서대로 [속성|null, 직업|null] — '
                     '게임 표는 A팀(아군) 전체 중 그 속성·직업 한정 자기 버프, B팀(적) 대상 없음.',
               stages=dict(sorted(stages.items())))
    atomic_text(ROOT / 'data' / 'stage_fx.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('stage_fx.json: 스테이지', len(stages))
    for k, v in sorted(report.items()):
        print('  ', v, k)


if __name__ == '__main__':
    main()
