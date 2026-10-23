# -*- coding: utf-8 -*-
"""서든데스(전역 턴이 길어지면 아군 능력치 감소) -> data/sudden_death.json (공개 저장소에는 가공 수치만).

게임: BATTLE_TEMPLET.SuddenDeathId -> SUDDEN_DEATH_TEMPLET(SDBT_PVE·SDT_ALWAYS) -> SUDDEN_DEATH_GROUP_TEMPLET 단계 행
(EndLevelTurn = 그 단계가 끝나는 전역 턴, 마지막 단계는 없음 = 끝까지) -> ATeamBattleEffectList -> BATTLE_EFFECT_TEMPLET
(AteamEffectTarget ALL, 능력치 4종 만분율). 컨트롤러는 전역 턴이 바뀔 때마다 단계를 적용함(NKM.decompiled.cs 16989~17013).
스테이지 연결은 tools/build_foe_spawn 과 같은 매칭(권장 전투력·레벨·웨이브 구성)을 쓴다.

출력: groups["그룹"] = 단계마다 [끝 턴|null, 생명력%, 방어력%, 주는 회복량%, 주는 보호막량%] (음수 %),
      stages["콘텐츠|탭|스테이지"] = 그룹(문자열).
모르는 능력치·대상(아군 전체가 아님·B팀 효과)이 나온 그룹은 통째로 빼고 보고한다(조용히 다른 값으로 바꾸지 않음).

사용: python -X utf8 -I tools/build_sudden_death.py [--static <비공개 저장소>]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority   # noqa: E402
from tools import build_foe_spawn as SP   # noqa: E402
from battlesim.fileio import atomic_text   # noqa: E402
from battlesim.starsavior import foe as F   # noqa: E402

STAT = {'NST_NV_RATE_HP': 1, 'NST_NV_RATE_DEF': 2, 'NST_RATE_HEAL_GIVE': 3, 'NST_RATE_BARRIER_GIVE': 4}


def table(static, name):
    return json.loads((Path(static) / 'tables' / (name + '.json')).read_text(encoding='utf-8'))['Data']


def groups(static, report):
    """SuddenDeathId -> 단계표. PVE·상시·아군 전체·아는 능력치만"""
    eff = {r['BattleEffectStrId']: r for r in table(static, 'BATTLE_EFFECT_TEMPLET')}
    lv = {}
    for r in table(static, 'SUDDEN_DEATH_GROUP_TEMPLET'):
        lv.setdefault(r['SuddenDeathGroupId'], []).append(r)
    out = {}
    for t in table(static, 'SUDDEN_DEATH_TEMPLET'):
        sid = t['SuddenDeathId']
        if t.get('SuddenDeathBattleType') != 'SDBT_PVE' or t.get('SuddenDeathType') != 'SDT_ALWAYS':
            report['PVE 상시 아님(제외): %s' % sid] += 1
            continue
        rows = sorted(lv.get(t['SuddenDeathGroupId'], []), key=lambda r: r['SuddenDeathLevel'])
        steps = []
        try:
            for i, r in enumerate(rows):
                end = r.get('EndLevelTurn')
                if (end is None) != (i == len(rows) - 1):
                    raise ValueError('끝 턴 없는 단계가 마지막이 아님')
                if r.get('BTeamBattleEffectList'):
                    raise ValueError('B팀 효과')
                step = [end, 0.0, 0.0, 0.0, 0.0]
                for e in r.get('ATeamBattleEffectList') or []:
                    e = eff[e]
                    if e.get('AteamEffectTarget') != 'ALL' or e.get('BteamEffectTarget') not in (None, 'NOT_APPLY'):
                        raise ValueError('대상 %s/%s' % (e.get('AteamEffectTarget'), e.get('BteamEffectTarget')))
                    k = STAT.get(e.get('BattleEffectStatType'))
                    if k is None:
                        raise ValueError('능력치 ' + str(e.get('BattleEffectStatType')))
                    step[k] += e['BattleEffectStatValue'] / 100.0
                steps.append(step)
            if not steps or any(a[0] is not None and b[0] is not None and a[0] >= b[0] for a, b in zip(steps, steps[1:])):
                raise ValueError('끝 턴이 오름차순 아님')
        except (KeyError, ValueError) as ex:
            report['모르는 형식(제외): %s %s' % (sid, ex)] += 1
            continue
        out[sid] = steps
    return out


def build(static):
    report = Counter()
    table_sd = groups(static, report)
    sd_of = {}
    for p in (Path(static) / 'tables').glob('BATTLE_TEMPLET_*.json'):
        for r in json.loads(p.read_text(encoding='utf-8'))['Data']:
            if r.get('SuddenDeathId'):
                sd_of[r['BattleStrID']] = r['SuddenDeathId']
    sids = {}
    SP.build(static, sids)
    rows = SP.battle_rows(static)
    # 매칭은 첫 후보에서 멈추므로, 권장 전투력·레벨이 같은 다른 후보가 다른 서든데스를 가지면 그 스테이지는 뺀다
    alt = {}
    for c in F.load_foe(str(ROOT))['g']:
        for ti, tb in enumerate(c['tabs']):
            for si, s in enumerate(tb['s']):
                key = '%s|%s|%s' % (c['k'], tb['t'], s['n'])
                if key in sids:
                    alt[key] = {sd_of.get(b) for b in SP.candidates(c['k'], tb['t'], s['n'], ti, si, rows)
                                if b in rows and rows[b][1] == str(s.get('bp')) and rows[b][2] == str(s.get('lv'))}
    stages = {}
    for key, bid in sids.items():
        g = sd_of.get(bid)
        if len(alt.get(key, ())) > 1:
            report['후보끼리 서든데스 다름(제외):' + key.split('|', 1)[0]] += 1
            continue
        if g is None:
            continue
        if g not in table_sd:
            report['그룹 없음/제외 스테이지'] += 1
            continue
        stages[key] = str(g)
        report['연결:' + key.split('|', 1)[0]] += 1
    # 서든데스가 있는 게임 전투 중 데이터북 스테이지와 연결 안 된 수(콘텐츠 머리별)
    linked = set(sids.values())
    for bid, g in sd_of.items():
        if bid not in linked:
            report['데이터북 연결 없음:' + '_'.join(bid.split('_')[:4])] += 1
    used = sorted({int(g) for g in stages.values()})
    return {str(g): table_sd[g] for g in used}, stages, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    try:
        static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    grp, stages, report = build(static)
    out = dict(_note='서든데스(tools/build_sudden_death.py). groups[그룹] = 단계마다 [끝 전역 턴|null(끝까지), 생명력%, 방어력%, '
                     '주는 회복량%, 주는 보호막량%] — 아군 전체에 적용. stages[콘텐츠|탭|스테이지] = 그룹. 없는 스테이지는 서든데스 없음.',
               groups=grp, stages=dict(sorted(stages.items())))
    atomic_text(ROOT / 'data' / 'sudden_death.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('sudden_death.json: 그룹', len(grp), '스테이지', len(stages))
    for k, v in sorted(report.items()):
        print('  ', v, k)


if __name__ == '__main__':
    main()
