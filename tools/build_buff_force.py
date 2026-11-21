"""BUFF_TEMPLET + 한국어 번역에서 강제 적용 강화의 이름만 추출한다.

python -X utf8 -I tools/build_buff_force.py --static <비공개 저장소>
원문·BuffStrID는 출력 JSON에 저장하지 않는다. 동명 효과의 판정이 다르면 제외한다.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path
from tools.tables import jsonc, name_sets, strings as table_strings, unanimous
from battlesim.fileio import atomic_json


def extract(rows, strings, warn=print):
    def flags(row):
        return bool(row.get('IsBuff')), bool(row.get('ForceApplyEffect'))
    for row in rows:
        if not strings.get(row.get('m_BuffName'), {}).get('ko') and flags(row) == (True, True):
            warn('WARNING: 강제 강화 번역 없음: ' + row['m_BuffStrID'])
    one = unanimous(name_sets(rows, strings, flags), warn,
                    lambda name, _: 'WARNING: 동명 효과 IsBuff/ForceApplyEffect 충돌, 제외: ' + name)
    return [name for name, v in one.items() if v == (True, True)]


def extract_immune_pass(rows, strings, warn=print):
    """〈면역〉(CantGetMoreDebuff)이 거부하지 않는 효과 이름(NKM:4339-4343): IsPositive 이거나 DeleteBuff 이거나 ForceApplyEffect.
    같은 이름의 행이 모두 통과일 때만 담는다(일부만 통과하는 이름은 이름만으로 구분 못 해 제외 = 거부로 둠)."""
    one = unanimous(name_sets(rows, strings, lambda row: bool(row.get('IsPositive')) or bool(row.get('DeleteBuff'))
                              or bool(row.get('ForceApplyEffect'))), warn,
                    lambda name, _: 'WARNING: 동명 효과 면역 통과 여부 혼재, 제외(거부 처리): ' + name)
    return [name for name, v in one.items() if v]


def extract_global_turn(rows, strings, warn=print):
    """BUFF_TEMPLET.GlobalTurnCounting 이 참인 효과 이름. 클라는 이런 효과를 «모든 행동이 끝날 때마다 전원 차감, 걸린 행동도 차감»한다
    (NKM:3973-3983 틱 함수, 13546 호출, 4571 예외 판정 = 게임 빌드 26314877). 같은 이름의 행이 모두 참일 때만 담는다(일부만 참인 이름은 이름만으로 구분 못 해 제외)."""
    one = unanimous(name_sets(rows, strings, lambda row: bool(row.get('GlobalTurnCounting'))), warn,
                    lambda name, _: 'WARNING: 동명 효과 GlobalTurnCounting 혼재, 제외: ' + name)
    return [name for name, v in one.items() if v]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static')
    ap.add_argument('--out', default=str(ROOT / 'data/buff_force.json'))
    ap.add_argument('--out-immune', default=str(ROOT / 'data/buff_immune_pass.json'))
    ap.add_argument('--out-clock', default=str(ROOT / 'data/buff_global_turn.json'))
    args = ap.parse_args()
    tables = static_path(args.static) / 'tables'
    rows = jsonc(tables / 'BUFF_TEMPLET.json')['Data']
    strings = table_strings(tables)
    names = extract(rows, strings, lambda msg: print(msg, file=sys.stderr))
    atomic_json(args.out, names)
    print('강제 적용 강화 이름', len(names), '저장:', args.out)
    passed = extract_immune_pass(rows, strings, lambda msg: print(msg, file=sys.stderr))
    atomic_json(args.out_immune, passed)
    print('면역 통과 효과 이름', len(passed), '저장:', args.out_immune)
    clock = extract_global_turn(rows, strings, lambda msg: print(msg, file=sys.stderr))
    atomic_json(args.out_clock, clock)
    print('전체 턴 시계 효과 이름', len(clock), '저장:', args.out_clock)


if __name__ == '__main__':
    main()
