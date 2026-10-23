# -*- coding: utf-8 -*-
"""BUFF_TEMPLET 이름별 [IsBuff, IsPositive] -> data/buff_count.json.

사용: python -X utf8 -I tools/build_buff_count.py --static <비공개 저장소>
양성 = IsBuff && IsPositive (NKM.Templets.decompiled.cs:36344).
동명 행의 필드 쌍을 보존한다. 원본 ID·설명·내정보는 출력하지 않는다.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path
from battlesim.fileio import atomic_text


def build(static):
    tables = Path(static) / 'tables'
    strings = json.loads((tables / 'Strings/STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))
    rows = json.loads((tables / 'BUFF_TEMPLET.json').read_text(encoding='utf-8'))['Data']
    out = {}
    for row in rows:
        name = strings.get(row.get('m_BuffName'), {}).get('ko')
        if not name:
            continue
        flags = (row['IsBuff'], row['IsPositive'])
        if not all(isinstance(v, bool) for v in flags):
            raise ValueError('invalid buff flags: ' + name)
        out.setdefault(name, set()).add(flags)
    return {name: sorted(out[name]) for name in sorted(out)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    buffs = build(static_path(args.static))
    out = {'_note': '이름별 [IsBuff, IsPositive] 후보. 양성은 두 값 모두 true. 동명 양성 충돌·미등록 이름은 legacy 분류.',
           'buffs': buffs}
    atomic_text(ROOT / 'data/buff_count.json', json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print('buff_count.json:', len(buffs), 'names')


if __name__ == '__main__':
    main()
