"""BUFF_TEMPLET + 한국어 번역에서 엔진이 이름으로 판정하는 버프 표식을 뽑는다 -> data/buff_flags.json.

python -X utf8 -I tools/build_buff_flags.py --static <비공개 저장소>
원문·BuffStrID는 저장하지 않는다. 같은 이름의 행끼리 값이 다르면 그 이름은 빼고(이름만으로 못 가름) 경고한다.
- priority: ShowIconPriority(0 이 아닌 것만). 클라 버프 목록 정렬(OBF_25553: 우선순위 내림차순 → 양성 먼저 → 넣은 순,
  build 26610546 NKM.decompiled.cs 4505-4520·4916-4929) = 해제 후보 순서(mc.dispel_order).
- dispel_attack: DispelCondition=DC_ATTACK. 공격 스킬 끝에 시전자에게서 제거(OBF_20893 NKM:4084-4097, 호출 15719-15722, mc.dispel_attack_names).
- cant_more_debuff: m_bDebuffBan = CantGetMoreDebuff(Star.Templets 4739 플래그 19). 이름과 무관하게 새 약화 거부(NKM:4394-4398, mc.debuff_ban_flag).
- immune_gauge_up: ImmuneSpeedGaugeUp. 행동 게이지 증가(SpeedGaugeUp) 효과 거부(NKM:4412-4416, mc.gauge_up_immune).
- cc: 기절·수면·침묵·도발 효과 이름과 각각의 면역 버프 이름(m_bImmuneStun 등). 면역 보유자는 해당 효과 거부(NKM:4407-4411, mc.cc_immune_buff).
- turn_infinite: TurnInfinite(수명 무한). 지속 표기 없는 효과 줄이라도 수명 0 정리 대상이 아님(mc.check_buff_scope=all, «타격 후 해제» 나태·헥사 너트).
- force_apply: ForceApplyEffect(버프 강제 적용). 부여 검사의 면역 목록·회피·강화/약화 불가·상태이상/게이지 증가 면역을 건너뜀
  (OBF_8151 = SE 행 강제 || 버프 강제, 생성자 NKM:6112, mc.se_force_apply).
- sleep: m_bSleep(수면). 마지막 타격 피해가 0보다 크면 피격자에게서 제거(OBF_2209 NKM:8314-8335, mc.sleep_wake).
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


def flagged(rows, strings, key, warn=print):
    """표식 key 가 참인 이름(같은 이름 행이 모두 참일 때만)."""
    return sorted(n for n, v in by_name(rows, strings, lambda r: bool(r.get(key)), warn, key).items() if v)


def extract(rows, strings, warn=print):
    pri = by_name(rows, strings, lambda r: int(r.get('ShowIconPriority') or 0), warn, 'ShowIconPriority')
    return {
        '_note': '이름별 버프 표식(tools/build_buff_flags.py, BUFF_TEMPLET). 같은 이름 행끼리 값이 다르면 뺌.',
        'priority': {n: v for n, v in pri.items() if v},
        'sleep': flagged(rows, strings, 'm_bSleep', warn),
        'cant_more_debuff': flagged(rows, strings, 'm_bDebuffBan', warn),
        'immune_gauge_up': flagged(rows, strings, 'ImmuneSpeedGaugeUp', warn),
        'turn_infinite': flagged(rows, strings, 'TurnInfinite', warn),
        'force_apply': flagged(rows, strings, 'ForceApplyEffect', warn),
        'cc': {k: {'effects': flagged(rows, strings, f, warn), 'immune': flagged(rows, strings, im, warn)}
               for k, f, im in (('stun', 'm_bStun', 'm_bImmuneStun'), ('sleep', 'm_bSleep', 'm_bImmuneSleep'),
                                ('silence', 'm_bSilence', 'm_bImmuneSilence'), ('aggro', 'm_bAggro', 'm_bImmuneAggro'))},
        'dispel_attack': sorted(n for n, v in by_name(rows, strings, lambda r: r.get('DispelCondition') == 'DC_ATTACK', warn,
                                                      'DispelCondition').items() if v),
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
