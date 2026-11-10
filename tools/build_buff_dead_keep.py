# -*- coding: utf-8 -*-
"""DeadNotDispel 이름 목록만 추출. 동명 true/false 충돌은 보존하지 않는다."""
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
    flags = {}
    for row in rows:
        name = strings.get(row.get('m_BuffName'), {}).get('ko')
        if name:
            flags.setdefault(name.removesuffix('(해제불가)'), set()).add(bool(row.get('DeadNotDispel', False)))
    return {'_note': '동명 행 모두 DeadNotDispel=true인 이름만 보존. ambiguous는 기존 삭제 유지.',
            'names': sorted(n for n, values in flags.items() if values == {True}),
            'ambiguous': sorted(n for n, values in flags.items() if len(values) > 1)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    out = build(static_path(args.static))
    atomic_text(ROOT / 'data/buff_dead_keep.json', json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print('DeadNotDispel:', len(out['names']), 'names;', len(out['ambiguous']), 'ambiguous')
