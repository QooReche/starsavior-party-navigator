# -*- coding: utf-8 -*-
"""빠른 계산(재설계 v1 1단계)용 데이터 data/quick.json 을 만든다. 사전 계산이 아니라 «재료» 요약이라 수십 초면 끝난다.

- 구원자(sv): 기준 상태(Lv200·공명10·장비 없음 = damage_index·P4 시뮬과 같은 조건)의 공·생·방·속도, 그 상태의 전투력(데이터북 공식),
  턴당 기대 피해(단일 s, 3명일 때 합 a — damage_index 를 방어 0 기준으로 되돌린 값), 역할 꼬리표(힐·보호막·도발·자가생존).
- 스테이지(st): 웨이브별 적 [생명력, 방어력, 속도, 단일 압박, 광역 압박(1명당), 보스 여부]. 압박 = 공격력 × 행동당 평균 스킬 계수.
  스테이지 효과(fx)의 공격력%·생명력%·방어력%·속도%·받는 피해 감소는 적에게 반영.
화면·battlesim/quick.py 가 이 파일을 읽는다. 형식은 battlesim/quick.py 맨 위 설명과 같이 고칠 것.

사용: python -X utf8 -I tools/build_quick_data.py [출력 경로]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from battlesim.api import party_power                     # noqa: E402
from battlesim.metrics import unit_def, unit_metrics        # noqa: E402
from battlesim.starsavior.data import get_db               # noqa: E402
from battlesim.rules import DEFAULT_OPTS                    # noqa: E402
from battlesim.starsavior.foe import FoeDef, load_foe, parse_fx   # noqa: E402

DATA = os.path.join(ROOT, 'data')
BUILD = 'standard'
FLAG_TAGS = {'힐': 'h', '보호막': 's', '도발/방어지원': 't', '자가생존': 'v', '부활': 'r'}


def power_base(st):
    """데이터북 전투력 공식(app.js calcBP)의 «마지막 배율 전» 값. 잠재력 0, 효과 배율 포함. 스탯 단위: cr/cd/eh/er 1/10000."""
    atk, hp, df, spd = st['atk'], st['hp'], st['def'], st['spd']
    cr = min(1.0, st.get('cr', 0) / 10000)
    cdm = min(3.0, st.get('cd', 0) / 10000)
    eh, ee = st.get('eh', 0) / 10000, st.get('er', 0) / 10000
    aB, hB, dB = atk / 10 * 12, hp / 55 * 12, df / 5 * 12
    sp = (100 + (spd - 100) / 5) / 100
    ef = max(0.0, 1 + (eh - 1 + ee) / 10)
    mix = lambda x: max(0.0, x * (1 - cr)) + x * cr * (1 + cdm)
    m1 = (mix(aB) + hB + dB) * sp * ef
    bal = (atk / 10 + hp / 55 + df / 5) / 3 * 12
    m2 = (mix(bal) + hB + dB) * sp * ef
    m3 = (aB + hB + dB) * (1 + (cr + cdm / 2) / 3) * sp * ef
    return max(m1, m2, m3)


def build_saviors():
    tags = {s['key']: s for s in json.load(open(os.path.join(DATA, 'synergy_tags.json'), encoding='utf-8'))['saviors']}
    ref_def = DEFAULT_OPTS['enemy_def']
    keep = 1 - ref_def / (ref_def + 3000)          # 기준 적 방어율을 되돌린다
    out = {}
    for key in sorted(get_db().units):
        # 기준 = Lv200·공명10 + P5 표준 육성(BUILD: 가이드 세팅·T2 레전더리 +15·여정·특수 잠재력). 브라우저 시뮬도 같은 build 로 돌린다
        m = unit_metrics(key, build=BUILD)
        m = dict(s=round(m['single_dpt']), a=round(m['aoe_dpt']))
        d = unit_def(key, build=BUILD)
        st = d.stats
        t = tags.get(key, {})
        flags = ''.join(v for k, v in FLAG_TAGS.items() if k in t.get('tags', []))
        # 전투력 = 엔진(api.party_power)과 같은 식 — 시뮬이 스탯으로 계산하는 전투력·역보정과 같은 값이 되게
        out[key] = [t.get('class') or d.role, st['atk'], st['hp'], st['def'], st['spd'], round(party_power([d]), 1),
                    round(m['s'] / keep, 1), round(m['a'] / keep, 1), flags]
    return out


def foe_press(f):
    """행동당 평균 피해 계수(단일, 광역) — 쿨타임 있는 공격 스킬은 1/쿨 비율로 쓰고 나머지는 기본기. 근거 = 추정(빠른 계산용)."""
    att = [s for s in f.skills.values() if s.is_attack and s.cf[0] > 0]
    if not att:
        return 0.0, 0.0
    basic = [s for s in att if not s.cd]
    other = sorted([s for s in att if s.cd], key=lambda s: -s.cd)
    single = aoe = 0.0
    used = 0.0
    for s in other:
        r = min(1.0 / max(1, s.cd), 1.0 - used)
        if r <= 0:
            break
        used += r
        if s.all:
            aoe += r * s.cf[0] / 10000
        else:
            single += r * s.cf[0] / 10000
    if basic:
        b = basic[0]
        if b.all:
            aoe += (1 - used) * b.cf[0] / 10000
        else:
            single += (1 - used) * b.cf[0] / 10000
    return single, aoe


def build_stages():
    raw = load_foe()
    out = {}
    for g in raw['g']:
        ck = g['k']
        cs = out.setdefault(ck, {})
        for t in g['tabs']:
            for s in t['s']:
                fx, _ = parse_fx(s.get('fx') or [])
                hp_m = 1 + fx.get('생명력%', 0) / 100
                atk_m = 1 + fx.get('공격력%', 0) / 100
                def_m = 1 + fx.get('방어력%', 0) / 100
                spd_m = 1 + fx.get('속도%', 0) / 100
                red = fx.get('받는 피해 감소', 0) / 100
                waves = []
                for w in s.get('w') or []:
                    row = []
                    for e in w:
                        f = FoeDef(raw, e[0], e[1] if len(e) > 1 else None, s)
                        ps, pa = foe_press(f)
                        a = f.stats['atk'] * atk_m
                        # 받는 피해 감소는 생명력을 늘리는 것과 같게 본다
                        row.append([round(f.stats['hp'] * hp_m / max(0.05, 1 - red)), round(f.stats['def'] * def_m),
                                    round(f.stats['spd'] * spd_m), round(a * ps, 1), round(a * pa, 1), 1 if f.boss else 0])
                    waves.append(row)
                row = dict(bp=s.get('bp'), lt=s.get('lt'), w=waves)
                if ck == 'rush':
                    row['np'] = 1          # 플래시 포인트는 전투력 역보정 미적용(공식 공지, 엔진 api.power_pen 과 같게)
                cs[t['t'] + '|' + s['n']] = row
    return out


def main():
    dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, 'quick.json')
    raw = load_foe()
    data = dict(_note='빠른 계산 재료(tools/build_quick_data.py). sv[key]=[클래스,공,생,방,속도,기준 전투력(엔진 식),단일 턴당 피해(방어 0),3명 합 피해(방어 0),꼬리표]; '
                      'st[콘텐츠][탭|스테이지]={bp,lt,w:[[생명력,방어력,속도,단일 압박,광역 압박,보스]...],np(역보정 없음)}. 기준 = Lv200·공명10·표준 육성(build=standard).',
                build=BUILD,
                ver=raw.get('v') or '', sv=build_saviors(), st=build_stages())
    # 맞춘 계수(params·calib, tools/calibrate_quick.py)는 다시 만들어도 보존한다 — 없으면 화면이 조용히 기본 계수로 돌아간다(codex 검토)
    if os.path.exists(dst):
        old = json.load(open(dst, encoding='utf-8'))
        for k in ('params', 'pc', 'sm', 'calib'):
            if k in old:
                data[k] = old[k]
    if 'params' not in data:
        print('경고: 계수(params)가 없습니다 — tools/calibrate_quick.py --write 를 돌리세요')
    tmp = dst + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, dst)
    print('저장', dst, os.path.getsize(dst), 'bytes', '구원자', len(data['sv']), '콘텐츠', len(data['st']),
          '스테이지', sum(len(v) for v in data['st'].values()))


if __name__ == '__main__':
    main()
