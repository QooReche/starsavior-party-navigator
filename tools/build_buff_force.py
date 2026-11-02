"""BUFF_TEMPLET + 한국어 번역에서 강제 적용 강화의 이름만 추출한다.

python -X utf8 -I tools/build_buff_force.py --static <비공개 저장소>
원문·BuffStrID는 출력 JSON에 저장하지 않는다. 동명 효과의 판정이 다르면 제외한다.
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


def extract(rows, strings, warn=print):
    names = defaultdict(set)
    for row in rows:
        name = strings.get(row.get('m_BuffName'), {}).get('ko')
        flags = (bool(row.get('IsBuff')), bool(row.get('ForceApplyEffect')))
        if not name:
            if flags == (True, True):
                warn('WARNING: 강제 강화 번역 없음: ' + row['m_BuffStrID'])
            continue
        names[name].add(flags)
    out = []
    for name, flags in sorted(names.items()):
        if len(flags) > 1:
            warn('WARNING: 동명 효과 IsBuff/ForceApplyEffect 충돌, 제외: ' + name)
        elif flags == {(True, True)}:
            out.append(name)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static')
    ap.add_argument('--out', default=str(ROOT / 'data/buff_force.json'))
    args = ap.parse_args()
    tables = static_path(args.static) / 'tables'
    rows = jsonc(tables / 'BUFF_TEMPLET.json')['Data']
    strings = json.loads((tables / 'Strings/STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))
    names = extract(rows, strings, lambda msg: print(msg, file=sys.stderr))
    atomic_json(args.out, names)
    print('강제 적용 강화 이름', len(names), '저장:', args.out)


if __name__ == '__main__':
    main()
