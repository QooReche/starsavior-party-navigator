# -*- coding: utf-8 -*-
"""적 소환 데이터(SUMMON_TEMPLET) -> data/foe_summon.json (공개 저장소에는 가공 값만).

게임 코드(NKM.decompiled.cs 5174~5212): SE SummonGroupId -> SUMMON_TEMPLET, SummonData 마다
SpawnPosIndex 칸에 유닛 생성. 칸이 범위 밖이거나 차 있으면 건너뜀(빈 칸만 채움).
시작 쿨 = 배치와 같은 로직(AllSkillAvailable/SpecialSkillAvailable/HyperSkillAvailable — NKM 1793~1812).
사망 시 칸 비움(1037~1050). 소환 유닛 레벨 = UnitLevel>0 이면 그 값 아니면 전투 레벨(1714~1748).

출력 groups[그룹ID] = {slots: [{pos, flag, element?}]}.
출력 stages["콘텐츠|탭|스테이지"] = {wave_slots: [[칸번호, ...], ...]} — 소환이 있는 스테이지만.

사용: python -X utf8 -I tools/build_foe_summon.py [--static <비공개 저장소>]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority   # noqa: E402
from battlesim.fileio import atomic_json               # noqa: E402
from battlesim.starsavior import foe as F              # noqa: E402
from tools.build_foe_spawn import battle_rows, candidates, jsonc, same_battle  # noqa: E402

NUAT = {
    'NUAT_ORDER': '질서', 'NUAT_SUN': '태양', 'NUAT_MOON': '달',
    'NUAT_STAR': '별', 'NUAT_CHAOS': '혼돈',
}


def summon_flag(sd):
    """SummonData entry -> spawn flag (A/S/H/B/N), same logic as build_foe_spawn.flag"""
    if sd.get('AllSkillAvailable'):
        return 'A'
    sp = bool(sd.get('SpecialSkillAvailable'))
    hy = bool(sd.get('HyperSkillAvailable'))
    return {(True, True): 'B', (True, False): 'S', (False, True): 'H'}.get((sp, hy), 'N')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--static', default=None)
    args = ap.parse_args()
    low_priority()
    static = static_path(args.static)

    # --- SUMMON_TEMPLET ---
    p = static / 'tables' / 'Plain' / 'SUMMON_TEMPLET.json'
    t = p.read_text(encoding='utf-8', errors='replace')
    t = re.sub(r'(?m)//.*$', '', t)
    t = re.sub(r',(\s*[}\]])', r'\1', t)
    tpl = json.loads(t)
    data = tpl.get('Data', tpl)

    groups = {}
    for rec in data:
        gid = str(rec['SummonGroupId'])
        slots = []
        for sd in rec['SummonData']:
            entry = {'pos': sd['SpawnPosIndex'], 'flag': summon_flag(sd)}
            el = NUAT.get(sd.get('ChangeAdjustType'))
            if el:
                entry['element'] = el
            stat = sd.get('AddStatData') or {}
            if stat and any(v for v in stat.values()):
                entry['stats'] = stat
            slots.append(entry)
        groups[gid] = {'slots': slots}

    # --- 소환 스테이지의 웨이브 칸 번호(BattleScript SpawnPosIndex) ---
    raw = F.load_foe()
    rows = battle_rows(static)
    stage_info = {}
    n_stages = 0

    for g in raw['g']:
        ck = g['k']
        for i_tab, tab in enumerate(g['tabs']):
            for i_stage, st in enumerate(tab['s']):
                if not st.get('sm'):
                    continue
                n_stages += 1
                key = '%s|%s|%s' % (ck, tab['t'], st['n'])
                cands = candidates(ck, tab['t'], st['n'], i_tab, i_stage, rows)
                wave_slots = None
                for c in cands:
                    if c not in rows:
                        continue
                    row = rows[c]
                    if same_battle(ck, st, row, raw, static):
                        bs = jsonc(row[0])
                        waves = (bs.get('Data') or {}).get('Waves') or []
                        wave_slots = []
                        for w in waves:
                            positions = [sp.get('SpawnPosIndex', i) for i, sp in
                                         enumerate(w.get('TeamBSpawnList') or [])]
                            wave_slots.append(positions)
                        break
                if wave_slots is not None:
                    stage_info[key] = {'wave_slots': wave_slots}
                else:
                    print('WARNING: %s 의 배치 연결 실패' % key,
                          file=sys.stderr)

    out = {
        '_source': 'tools/build_foe_summon.py --static',
        'groups': groups,
        'stages': stage_info,
    }
    dst = ROOT / 'data' / 'foe_summon.json'
    atomic_json(str(dst), out, indent=1)
    print('저장', dst, '그룹', len(groups),
          '스테이지', len(stage_info), '/', n_stages)


if __name__ == '__main__':
    main()
