# -*- coding: utf-8 -*-
"""적 시작 쿨 표시(배치 데이터) -> data/foe_spawn.json (공개 저장소에는 가공 표시만).

게임 코드(NKM.decompiled.cs 1765~1810): 적이 등장할 때 배치의 AllSkillAvailable 이 켜져 있으면 모든 스킬 쿨 0,
아니면 모든 스킬 쿨 가득. 그 위에 SpecialSkillAvailable·HyperSkillAvailable 이 켜져 있으면 특수기·궁극기만 0.
배치 = 비공개 저장소 tables/BattleScript/*.json(파일명 = BATTLE_TEMPLET_*.BattleTempletFileName).

출력 stages["콘텐츠|탭|스테이지"] = 웨이브별 문자열 목록, 칸마다 한 글자:
  A = 모든 스킬 0, S = 특수기만 0, H = 궁극기만 0, B = 특수기·궁극기 0, N = 모두 가득.
데이터북 스테이지와 웨이브 수·웨이브별 적 수가 같고 데이터북 보스 칸이 게임에서도 보스일 때만 적는다(안 맞으면 엔진이 등급 규칙으로 대신함).
지금 연결하는 콘텐츠: 작전(일반·어려움, 같은 섹터), 성간·태양·달·별 회랑(층 번호), 큐브 팰리스·일일 재화 던전(순서).
연결 조건: 권장 전투력(BattlePower)·레벨(BattleLevel)이 같고 웨이브 구성이 맞을 것.

사용: python -X utf8 -I tools/build_foe_spawn.py [--static <비공개 저장소>]
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority   # noqa: E402
from battlesim.fileio import atomic_text   # noqa: E402
from battlesim.starsavior import foe as F   # noqa: E402

CLO = {'성간 회랑': 'INTERSTELLAR', '태양 회랑': 'SUN', '달 회랑': 'MOON', '별 회랑': 'STAR'}
ROMAN = {'Ⅰ': 1, 'Ⅱ': 2, 'Ⅲ': 3, 'Ⅳ': 4, 'Ⅴ': 5, 'Ⅵ': 6, 'Ⅶ': 7, 'Ⅷ': 8, 'Ⅸ': 9, 'Ⅹ': 10}


def jsonc(path):
    t = Path(path).read_text(encoding='utf-8', errors='replace')
    t = re.sub(r'(?m)//.*$', '', t)
    t = re.sub(r',(\s*[}\]])', r'\1', t)
    return json.loads(t)


def flag(u):
    if u.get('AllSkillAvailable'):
        return 'A'
    sp, hy = bool(u.get('SpecialSkillAvailable')), bool(u.get('HyperSkillAvailable'))
    return {(True, True): 'B', (True, False): 'S', (False, True): 'H'}.get((sp, hy), 'N')


def battle_rows(static):
    """BattleStrID -> (배치 파일 경로, 권장 전투력, 레벨)"""
    out = {}
    for p in (Path(static) / 'tables').glob('BATTLE_TEMPLET_*.json'):
        for r in json.loads(p.read_text(encoding='utf-8'))['Data']:
            fn = (r.get('BattleTempletFileName') or '').replace('.txt', '.json')
            if fn:
                out[r['BattleStrID']] = (Path(static) / 'tables' / 'BattleScript' / fn, str(r.get('BattlePower')), str(r.get('BattleLevel')))
    return out


def candidates(ck, tab, name, i_tab, i_stage, rows=()):
    """데이터북 스테이지 -> 배치 BattleStrID 후보(권장 전투력·레벨이 같은 것만 쓰므로 넓게 줘도 된다)"""
    if ck in ('op', 'oph'):
        m = re.match(r'SECTOR (\d+)-(\d+)$', name)
        if m:
            # 작전(일반)은 데이터북 번호가 게임 번호와 어긋난 섹터가 있어(2-7 = 게임 2-8) 같은 섹터 전체를 후보로
            kind = 'NORMAL' if ck == 'op' else 'HARD'
            head = 'NORMAL_BATTLE_OPERATION_%s_SECTOR%s_' % (kind, m.group(1))
            same = head + '%03d' % int(m.group(2))
            return [same] + sorted(k for k in rows if k.startswith(head) and k != same)
    if ck == 'clo' and tab in CLO:
        m = re.match(r'FLOOR (\d+)$', name)
        if m:
            return ['NORMAL_BATTLE_CLOISTER_%s_%03d' % (CLO[tab], int(m.group(1)))]
    if ck == 'cube':
        return ['NORMAL_BATTLE_CUBE_MATERIAL_%03d' % (i_tab + 1)]
    if ck == 'daily':
        m = re.search(r'([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ])$', name)
        lv = ROMAN.get(m.group(1)) if m else i_stage + 1
        return ['NORMAL_BATTLE_DAILY_%s_%03d' % (k, lv) for k in ('GOLD', 'CRYSTAL', 'MATERIAL')]
    return []


def build(static):
    raw = F.load_foe(str(ROOT))
    rows = battle_rows(static)
    stages, why = {}, Counter()
    for c in raw['g']:
        ck = c['k']
        for ti, t in enumerate(c['tabs']):
            for si, s in enumerate(t['s']):
                cands = candidates(ck, t['t'], s['n'], ti, si, rows)
                if not cands:
                    why['연결 규칙 없음:' + ck] += 1
                    continue
                db_boss = [[raw['u'][e[0]].get('g') == '보스' for e in w] for w in s['w']]
                hit = None
                for sid in cands:
                    row = rows.get(sid)
                    if not row or not row[0].exists():
                        continue
                    path, bp, lv = row
                    if bp != str(s.get('bp')) or lv != str(s.get('lv')):   # 권장 전투력·레벨이 같아야 같은 전투
                        continue
                    waves = (jsonc(path).get('Data') or {}).get('Waves') or []
                    lists = [w.get('TeamBSpawnList') or [] for w in waves]
                    if [len(x) for x in lists] != [len(w) for w in db_boss]:
                        continue
                    # 데이터북은 게임에서 보스로 표시된 정예를 「일반」으로 적기도 한다 -> 데이터북 보스 칸만 게임에서도 보스인지 본다
                    if any(b and not u.get('IsBoss') for x, w in zip(lists, db_boss) for u, b in zip(x, w)):
                        continue
                    hit = [''.join(flag(u) for u in x) for x in lists]
                    break
                if hit is None:
                    why['배치 불일치:' + ck] += 1
                    continue
                stages['%s|%s|%s' % (ck, t['t'], s['n'])] = hit
                why['연결:' + ck] += 1
    return stages, why


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    try:
        static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    stages, why = build(static)
    out = dict(_note='적 시작 쿨 표시(tools/build_foe_spawn.py). 칸마다 A=모든 스킬 0, S=특수기만 0, H=궁극기만 0, '
                     'B=특수기·궁극기 0, N=모두 가득. 없는 스테이지는 엔진이 등급 규칙(보스 S, 그 밖 A)으로 대신함.',
               stages=dict(sorted(stages.items())))
    atomic_text(ROOT / 'data' / 'foe_spawn.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('foe_spawn.json: 스테이지', len(stages), dict(sorted(why.items())))


if __name__ == '__main__':
    main()
