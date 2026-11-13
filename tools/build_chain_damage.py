"""SE의 연쇄 피해 유형만 공개 스킬에 연결한다(원문 표는 출력하지 않음).

현재 한 스킬의 모든 레벨/대상은 같은 유형이다. 혼합 유형이 생기면 조용히
스킬 전체를 바꾸지 않고 실패하여 줄별 매핑을 요구한다.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.fileio import atomic_text
from battlesim.starsavior.savior_ids import keys_by_id
from tools.build_auto_skill import form_bindings
from tools.runtime import static_path


def build(static):
    tables = Path(static) / 'tables'
    load = lambda path: json.loads(path.read_text(encoding='utf-8'))
    groups = {}
    for n in (1, 2):
        for row in load(tables / f'SE_TEMPLET_SKILL_{n}.json')['Data']:
            if 'AddDamageRate' not in row:
                continue
            match = re.fullmatch(r'COND_(.+)_\d+_\d+', row.get('m_SEStrID', ''))
            if match:
                groups.setdefault(match[1], []).append(row)
    keys = keys_by_id(load(ROOT / 'data/saviors_index.json'))
    book = load(ROOT / 'rawdata/databook_main.json')['units']
    out = {}
    for key, bu, _unit, ids in form_bindings(tables, keys, book):
        for slot, sid in zip(('기본기', '특수기', '궁극기', '고유 패시브'), ids):
            name = sid.replace('NKM_UNIT_', '', 1)
            rows = groups.get(name) or groups.get(name.replace('S_', '', 1)) or []
            types = {'ADT_STAT_TRUE' if r.get('AddTrueDamageByStat') else 'ADT_NORMAL' for r in rows}
            if 'ADT_STAT_TRUE' not in types:
                continue
            if len(types) != 1:
                raise ValueError(f'{key}/{slot}: 연쇄 피해 유형이 혼합됨 — 줄별 매핑 필요')
            sk = next(s for s in bu['sk'] if s['sl'] == slot)
            lines = sk['ef'] + sk.get('L', {}).get('ln', [])
            if not any('연쇄 피해 = 자신 ' in line for line in lines):
                raise ValueError(f'{key}/{slot}: 능력치 연쇄 피해 줄 없음')
            out.setdefault(key, {})[slot] = types.pop()
    return dict(sorted(out.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    units = build(static_path(args.static))
    payload = dict(_note='tools/build_chain_damage.py: AddTrueDamageByStat → ADT_STAT_TRUE. '
                        '스킬의 모든 레벨·대상 SE 유형이 같을 때만 등록. 없는 스킬은 ADT_NORMAL.', units=units)
    atomic_text(ROOT / 'data/chain_damage.json', json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('chain_damage.json:', units)


if __name__ == '__main__':
    main()
