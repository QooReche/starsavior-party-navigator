# -*- coding: utf-8 -*-
"""
sim_damage.py - 스타세이비어 구원자 화력 지표 / 파티 시뮬레이터 (기대값 기반 이벤트 시뮬레이터)

구성
  1) calc_stats()      databook app.js 의 sCalc 와 같은 스탯 공식 (Lv/공명/각인/동기화) + 장비 확장 훅(gear)
  2) UnitDef           databook_main.json 의 스킬(cf/cd/nv/ef 줄)을 파싱해 만든 구원자 정의
  3) Sim               행동 게이지(10,000, 필요 틱=(10000-게이지)/속도) 방식의 이벤트 시뮬레이터. 난수 없이 기대값(확률 가중) 계산
  4) build_index()     구원자별 단일/광역 N턴 기대 피해 + 0~10 정규화 점수 (damage_index.json)
  5) simulate_party()  파티 4명 N턴 총 피해 + 적 총 HP 대비 처치 턴 수
  6) CLI               python -X utf8 -I sim_damage.py {index,party,stage,stats,validate} ...

가정/단순화는 sim_report.md 와 ASSUMPTIONS 상수에 명시. 데이터는 읽기 전용.
"""
import argparse
import json
import math
import os

from .metrics import ally_gain, build_index, describe, simulate_party, stage_report, unit_def, unit_metrics
from .engine import Sim
from .starsavior.data import OUT_DIR, _find_key, get_db
from .starsavior.parser import Line


def _jsonable(x):
    """math.inf 는 표준 JSON 에 없으므로 'inf' 문자열로 바꾼다."""
    if isinstance(x, float) and math.isinf(x):
        return 'inf' if x > 0 else '-inf'
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    return x


def dump_lines(db):
    """구원자별 파싱된 Line 목록 + 해석 못 한 줄·조건(unparsed). docs/battlesim_design.md 1절의 Line 덤프."""
    units, unparsed = {}, []
    known = set(Sim.COND_KEYS)
    for key in db.units:
        d = unit_def(key, db=db)
        rows = []
        for ln in d.lines:
            rows.append(dict(slot=ln.slot, src_kind=ln.src_kind, phase=ln.phase, kind=ln.kind, trigger=ln.trig,
                             params=[[k, v] for k, v in ln.params], hp_weight=ln.hpw, bound=ln.bound, non_attack=ln.na,
                             effect=_jsonable(ln.eff), raw=ln.raw))
            if ln.kind == 'unmodeled':
                unparsed.append(dict(unit=key, slot=ln.slot, reason='trigger', detail=ln.trig or ln.phase, raw=ln.raw))
            if ln.eff['kind'] == 'ignored' and ln.eff.get('why') in ('미해석', '상시미해석'):
                unparsed.append(dict(unit=key, slot=ln.slot, reason='effect', detail=ln.eff['why'], raw=ln.raw))
            for k, _ in ln.params:
                if k not in known:
                    unparsed.append(dict(unit=key, slot=ln.slot, reason='condition', detail=k, raw=ln.raw))
        # 노바 버스트 줄(d.nb): 엔진은 '<슬롯> 사용 시' 의 게이지 효과만 실행하고 +15% 는 상수로 처리한다(engine.Sim.cast)
        for nkey, raws in d.nb.items():
            if not (nkey == '발동 즉시' or nkey.endswith(' 사용 시')) or not isinstance(raws, list):
                continue   # desc·gl·hl 은 설명/표시용
            slot = nkey.replace(' 사용 시', '') if nkey.endswith(' 사용 시') else None
            for raw in raws:
                if not isinstance(raw, str):
                    continue
                ln = Line(raw, slot or nkey, 'active')
                # '발동 즉시' 의 피해 증가 +15% 는 엔진이 상수(ctx.inc += 0.15)로 반영
                applied = (slot is None and '피해 증가 +15%' in raw) or (slot is not None and ln.eff['kind'] == 'gauge')
                rows.append(dict(slot=slot, src_kind='nova', phase=nkey, kind=ln.kind, trigger=ln.trig,
                                 params=[[k, v] for k, v in ln.params], hp_weight=ln.hpw, bound=ln.bound, non_attack=ln.na,
                                 effect=_jsonable(ln.eff), raw=raw, applied=applied))
                if not applied:
                    unparsed.append(dict(unit=key, slot=slot, reason='nova', detail=nkey, raw=raw))
        for msg in sorted(set(d.unmodeled)):
            if msg.startswith('변형') or msg.startswith('반응'):
                unparsed.append(dict(unit=key, slot=None, reason='skill', detail=msg, raw=None))
        units[key] = rows
    return dict(units=units, unparsed=unparsed,
                counts=dict(units=len(units), lines=sum(len(v) for v in units.values()), unparsed=len(unparsed)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    p = sub.add_parser('index', help='damage_index.json 생성')
    p.add_argument('--out', default=os.path.join(OUT_DIR, 'damage_index.json'))
    p.add_argument('--turns', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    p = sub.add_parser('stats', help='구원자 스탯 출력')
    p.add_argument('unit')
    p.add_argument('--level', type=int, default=200)
    p.add_argument('--res', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    p = sub.add_parser('party', help='파티 4명 시뮬: party a,b,c,d')
    p.add_argument('units')
    p.add_argument('--turns', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    p.add_argument('--stages', action='store_true', help='대표 스테이지 처치 턴 수도 출력')
    p = sub.add_parser('stage', help='구원자 key 목록으로 대표 스테이지 5개 처치 턴')
    p.add_argument('units')
    p.add_argument('--turns', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    p = sub.add_parser('unit', help='구원자 1명 지표 상세')
    p.add_argument('unit')
    p.add_argument('--turns', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    p = sub.add_parser('lines', help='구원자별 파싱된 스킬 줄(Line) + 해석 못 한 목록을 JSON 으로 덤프')
    p.add_argument('--out', default=os.path.join(OUT_DIR, 'lines.json'))
    args = ap.parse_args(argv)
    db = get_db()
    if args.cmd == 'index':
        idx = build_index(args.turns, None, args.star, db)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(idx, f, ensure_ascii=False, indent=1)
        print('wrote', args.out, len(idx) - 1, 'units')
    elif args.cmd == 'stats':
        k = _find_key(db, args.unit)
        d = unit_def(k, args.level, args.res, args.star)
        print(k, d.name, d.role, d.element, json.dumps(d.stats, ensure_ascii=False), dict(d.passive))
    elif args.cmd == 'party':
        keys = [_find_key(db, x) for x in args.units.split(',')]
        r = simulate_party(keys, None, args.turns, None, args.star)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        if args.stages:
            for row in stage_report(keys, args.turns, None, args.star):
                print(row)
    elif args.cmd == 'stage':
        keys = [_find_key(db, x) for x in args.units.split(',')]
        for row in stage_report(keys, args.turns, None, args.star):
            print(row)
    elif args.cmd == 'unit':
        k = _find_key(db, args.unit)
        d = unit_def(k, star=args.star)
        m = unit_metrics(k, args.turns, None, args.star)
        print(k, describe(d))
        print(json.dumps(m, ensure_ascii=False, indent=1))
        print('ally_gain', ally_gain(k, args.turns, None, args.star))
        for u in sorted(set(d.unmodeled)):
            print('  unmodeled:', u)
    elif args.cmd == 'lines':
        out = dump_lines(db)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        tmp = args.out + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, args.out)
        c = out['counts']
        print('wrote', args.out, 'units', c['units'], 'lines', c['lines'], 'unparsed', c['unparsed'])
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
