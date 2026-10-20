# -*- coding: utf-8 -*-
"""스탯 계산 (databook app.js sCalc 재현)."""
import math
from collections import defaultdict

from ..rules import DEFAULT_OPTS

# ------------------------------------------------------------------ 스탯 (app.js sCalc 재현)
STAT_MODES = {
    'normal': (1.0, 1.0),
    'fixed': (1.0, 0.0),     # 플래시 포인트/코스모 게이지: Lv200, 공명10, 200초과분 0
    'rank': (0.1, 0.0),      # 랭크전(PvP): 성장 능력치 10%만
}

def calc_stats(db, u, level=200, res_stage=10, star=0, mode='fixed', gear=None, gear_order=None, journey=None):
    """gear(확장 훅): 정수 {'atk','hp','def','spd','cr','cd','eh','er'}(cr/cd/eh/er 은 1/10000) + 비율 {'atkP','hpP','defP','spdP'}(1/10000).
    gear_order(기본 = rules 의 gear_order): 'databook' = floor(((기본+레벨)x(1+공명%)+공명 정수) x (1+각인%+장비%) + 장비 정수),
    'legacy' = 각인%만 곱해 버림한 뒤 장비 정수를 더함(장비%는 이 함수가 아니라 UnitDef.gear_atkp 로 전투 중 곱함).
    journey(P5): 여정 변환 정수 {'hp','atk','def'}(기본값 쪽 — 공명%·Σ% 를 받음) + {'eh','er'}(1/10000, 단순 합). 없으면 교정 전과 같은 연산."""
    if gear_order is None:
        gear_order = DEFAULT_OPTS['gear_order']
    gear = gear or {}
    journey = journey or {}
    new_order = gear_order == 'databook'
    ST = db.main['stat']
    m = ST['units'][str(u['id'])]
    sid = m['sid'] if u['v'] == '기본' else m.get('bsid', m['sid'])
    t = ST['tmpl'][sid]
    b, g = t['base'], t['grow']
    s1, s2 = STAT_MODES[mode]
    L = level
    n1 = min(L, 200) - 1
    n2 = max(0, L - 200)
    J = {'hp': 0, 'atk': 0, 'def': 0}
    if L >= 200:
        for lv, d in ST['sync']['jumps']:
            if lv <= L:
                for k, v in d.items():
                    J[k] = J.get(k, 0) + v
    R = ST['res'].get(str(u['id']), [])
    rn = 0
    for i in range(min(res_stage, len(R))):
        if R[i][0] > L:
            break
        rn += 1
    rf, rp = defaultdict(float), defaultdict(float)
    for ul, sts in R[:rn]:
        for k, v in sts:
            if k.endswith('P'):
                rp[k] += v
            else:
                rf[k] += v
    starP = sum(next((x[1] for x in sts if x[0] == 'atkP'), 0) for _, sts in ST['star'][:star])
    out = {}
    for k in ('hp', 'atk', 'def', 'spd'):
        main = k != 'spd'
        sc1 = s1 * 1.0 if main else 1.0
        sc2 = s2 * 1.0 if main else 1.0
        lv_int = g[k] * n1 if main else 0
        amp_int = (g[k] * n2 + J.get(k, 0)) if main else 0
        v = b[k] + lv_int * sc1 + amp_int * sc2
        if journey.get(k):
            v = v + journey[k]
        v = v + rf.get(k, 0) * sc1 + v * (rp.get(k + 'P', 0) * 1e-4)
        if new_order:
            # ⓓ(% 합: 각인% + 장비%)을 한 번 곱하고 ⓑ(장비 정수)를 더한 뒤 버림. 장비가 없으면 교정 전과 같은 연산이 된다.
            gp = gear.get(k + 'P', 0)
            if gp:
                v = v + v * ((starP if main else 0) + gp) * 1e-4
            elif main:
                v = v + v * starP * 1e-4      # 교정 전과 같은 부동소수 연산(버림 경계 보존)
            v = v + gear.get(k, 0)
        elif main:
            v = v + v * starP * 1e-4
        out[k] = max(0, math.floor(v))
    for k in ('cr', 'cd', 'eh', 'er', 'der'):
        v = math.floor(b[k] + rf.get(k, 0) + (gear.get(k, 0) if new_order else 0) + journey.get(k, 0))   # 치명·효과 적중/저항은 단순 합
        cap = ST['cap'].get({'cr': 'NST_RATE_CRITICAL', 'cd': 'NST_RATE_CRITICAL_DAMAGE'}.get(k, ''), 0)
        if cap and v > cap:
            v = cap
        out[k] = max(0, v)
    out['sa'] = b['sa']
    if gear and not new_order:   # 교정 전 순서: 버림한 최종값에 정수를 더함(비율 키는 무시)
        for k, v in gear.items():
            if k in out:
                out[k] += v
    out['_template'] = sid
    return out
