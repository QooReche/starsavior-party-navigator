# -*- coding: utf-8 -*-
"""DeadNotDispel 이름 목록만 추출. 동명 true/false 충돌은 보존하지 않는다."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path
from tools.tables import name_sets, strings as table_strings
from battlesim.fileio import atomic_text


def build(static):
    tables = Path(static) / 'tables'
    rows = json.loads((tables / 'BUFF_TEMPLET.json').read_text(encoding='utf-8'))['Data']
    flags = name_sets(rows, table_strings(tables), lambda row: bool(row.get('DeadNotDispel', False)),
                      rename=lambda name: name.removesuffix('(해제불가)'))
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
