"""BUFF_TEMPLET + 한국어 번역에서 엔진이 이름으로 판정하는 버프 표식을 뽑는다 -> data/buff_flags.json.

python -X utf8 -I tools/build_buff_flags.py --static <비공개 저장소>
원문·BuffStrID는 저장하지 않는다. 같은 이름의 행끼리 값이 다르면 그 이름은 빼고(이름만으로 못 가름) 경고한다.
- priority: ShowIconPriority(0 이 아닌 것만). 클라 버프 목록 정렬(OBF_25553: 우선순위 내림차순 → 양성 먼저 → 넣은 순,
  build 26610546 NKM.decompiled.cs 4505-4520·4916-4929) = 해제 후보 순서(mc.dispel_order).
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path
from tools.build_foe_spawn import jsonc
from battlesim.fileio import atomic_json


def by_name(rows, strings, value, warn=print, label=''):
    """이름 -> 값(같은 이름 행이 모두 같은 값일 때만)."""
    names = defaultdict(set)
    for row in rows:
        name = strings.get(row.get('m_BuffName'), {}).get('ko')
        if name:
            names[name].add(value(row))
    out = {}
    for name, vals in sorted(names.items()):
        if len(vals) == 1:
            out[name] = vals.pop()
        else:
            warn('WARNING: 동명 효과 %s 혼재, 제외: %s %s' % (label, name, sorted(vals, key=str)))
    return out


def extract(rows, strings, warn=print):
    pri = by_name(rows, strings, lambda r: int(r.get('ShowIconPriority') or 0), warn, 'ShowIconPriority')
    return {
        '_note': '이름별 버프 표식(tools/build_buff_flags.py, BUFF_TEMPLET). 같은 이름 행끼리 값이 다르면 뺌.',
        'priority': {n: v for n, v in pri.items() if v},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static')
    ap.add_argument('--out', default=str(ROOT / 'data/buff_flags.json'))
    args = ap.parse_args()
    tables = static_path(args.static) / 'tables'
    rows = jsonc(tables / 'BUFF_TEMPLET.json')['Data']
    strings = json.loads((tables / 'Strings/STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))
    out = extract(rows, strings, lambda msg: print(msg, file=sys.stderr))
    atomic_json(args.out, out)
    print('저장:', args.out, {k: len(v) for k, v in out.items() if isinstance(v, (dict, list))})


if __name__ == '__main__':
    main()
