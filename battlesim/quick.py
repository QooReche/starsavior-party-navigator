# -*- coding: utf-8 -*-
"""빠른 계산(재설계 v1 1단계) — 「평균 육성이면 이 파티로 깰만한가」를 팀당 1ms 안에 판단하는 결정적 근사.

화면(party_template.html 의 Quick)은 이 파일을 그대로 옮긴 JS 다. **둘을 같이 고친다** — tests/quick_test.py 가 같은 입력·같은 결과를 대조한다.
재료 = data/quick.json(tools/build_quick_data.py). 계수 A·B·H 는 확률 엔진(P4 시뮬 결과)에 맞춰 tools/calibrate_quick.py 로 정했다.

모델(라운드 = 속도 100 유닛이 한 번 행동하는 시간):
- 육성: 파티 전투력 P(입력, 없으면 권장 전투력 × growth) → 배율 k = P / (Σ 기준 전투력 × MUL). 공·생·방·피해에 k 를 곱한다
  (전투력이 공·생·방에 비례하는 공식이라 맞아떨어진다). 속도·치명 등은 기준 그대로.
- 역보정: P / 권장 전투력 비율로 power_penalty 표(아군 주는 피해·적 주는 피해).
- 아군: 매 라운드 단일 피해는 보스 → (없으면) 생명력 가장 낮은 적에게, 광역 몫은 나머지 적 각각에게. 방어율 = def/(def+3000).
- 적: 살아 있는 적의 압박 합 × 1.85 × 속도/100 × (1 − 아군 평균 방어율)을 파티 생명력 «합»에서 깎는다(개별 사망은 안 봄 → 시뮬 단계 몫).
- 회복: 힐·보호막 꼬리표 구원자 1명당 매 라운드 최대 생명력의 H.
- 스테이지 난이도 보정 m(보스 콘텐츠): 그 스테이지의 시뮬 표본으로 맞춘 적 피해 배수(빠른 계산이 못 보는 기믹 몫, quick.json sm).
"""
import json
import math
import os

MUL = 1.0           # sv 의 기준 전투력이 이미 엔진 식(돌파·스킬 레벨 배율 포함, api.party_power)이라 추가 배율 없음
PARAMS = dict(A=1.0, B=1.0, H=0.0)     # tools/calibrate_quick.py 결과로 덮어씀(data/quick.json 의 params)
MAX_ROUNDS = 50
SAFE = 0.5          # 남은 생명력 비율이 이 이상이면 「깰만함」
TIGHT = 0.0         # 깼지만 SAFE 미만이면 「빠듯함」


def dr(d):
    return d / (d + 3000.0) if d > 0 else 0.0


def pen_mult(pen, ratio):
    """power_penalty pen 표: [하한, 상한(만분율), 아군×1e4, 적×1e4]. ratio = P/권장."""
    r = math.floor(ratio * 10000 + 1e-6)     # 부동소수 잡음(0.7999999…)으로 구간이 한 칸 내려가지 않게
    for lo, hi, a, e in pen:
        if lo <= r < hi:
            return a / 10000, e / 10000
    if r >= 9000:
        return 1.0, 1.0
    return pen[0][2] / 10000, pen[0][3] / 10000


def _add(xs):
    """왼쪽부터 그냥 더하기 — 내장 sum 은 3.12+ 에서 보정 합산이라 JS 와 끝자리가 달라진다(구간 경계에서 판정이 뒤집힘)"""
    t = 0.0
    for x in xs:
        t += x
    return t


def evaluate(keys, stage, sv, pen, params=None, growth=1.0, power=None, use_pen=True, powers=None, scale=1.0):
    """-> dict(ok, clear, rounds, left, k, power, ratio) / 재료 없는 구원자가 있으면 ok=False
    powers = {구원자 key: 그 구원자 전투력}(「내 구원자」 서랍 입력, 선택). 없는 구원자는 (power 또는 권장×growth)를 기준 전투력 비율로 나눈 몫.
    scale = 모든 구원자 전투력에 곱하는 배수(「얼마나 더 키우면 깨나」 탐색용)."""
    p = dict(PARAMS)
    if params:
        p.update(params)
    units = [sv.get(k) for k in keys]
    if any(u is None for u in units) or not stage.get('w'):
        return dict(ok=False)
    rs = _add(u[5] for u in units)
    ref = rs * MUL
    bp = stage.get('bp') or ref
    base = power if power else bp * growth
    pi = [((powers or {}).get(keys[i]) or base * units[i][5] / rs) * scale for i in range(len(units))]
    P = _add(pi)
    ks = [pi[i] / (units[i][5] * MUL) for i in range(len(units))]
    k = P / ref
    ratio = P / bp if bp else 1.0
    pa, pe = pen_mult(pen, ratio) if use_pen and not stage.get('np') else (1.0, 1.0)
    hp_max = _add(units[i][2] * ks[i] for i in range(len(units)))
    team_dr = dr(_add(units[i][3] * ks[i] for i in range(len(units))) / len(units))
    # 턴당 피해(s·a)는 이미 「속도 100 기준 한 턴」 동안의 피해라 속도를 또 곱하지 않는다
    s_out = [units[i][6] * ks[i] * p['A'] * pa for i in range(len(units))]
    x_out = [max(0.0, (units[i][7] - units[i][6]) / 2) * ks[i] * p['A'] * pa for i in range(len(units))]
    healers = sum(1 for u in units if ('h' in u[8] or 's' in u[8]))
    heal = healers * p['H'] * hp_max
    hp = hp_max
    limit = stage.get('lt') or MAX_ROUNDS
    rnd = 0
    for wave in stage['w']:
        foes = [[e[0], e[1], e[2], e[3], e[4], e[5]] for e in wave]     # 현재 생명력, 방어, 속도, 단일, 광역, 보스
        while any(f[0] > 0 for f in foes):
            rnd += 1
            if rnd > limit:
                return dict(ok=True, clear=False, rounds=limit, left=max(0.0, hp / hp_max), k=k, power=P, ratio=ratio, why='time')
            alive = [f for f in foes if f[0] > 0]
            boss = [f for f in alive if f[5]]
            focus = boss[0] if boss else min(alive, key=lambda f: f[0])
            for i in range(len(units)):
                focus[0] -= s_out[i] * (1 - dr(focus[1]))
                if x_out[i]:
                    for f in alive:
                        if f is not focus:
                            f[0] -= x_out[i] * (1 - dr(f[1]))
            dmg = _add((f[3] + f[4]) * f[2] / 100 for f in foes if f[0] > 0)
            hp -= dmg * 1.85 * (1 - team_dr) * p['B'] * pe * (stage.get('m') or 1.0)
            if hp <= 0:
                return dict(ok=True, clear=False, rounds=rnd, left=0.0, k=k, power=P, ratio=ratio, why='wipe')
            hp = min(hp_max, hp + heal)
    return dict(ok=True, clear=True, rounds=rnd, left=hp / hp_max, k=k, power=P, ratio=ratio, why='')


def verdict(r):
    if not r.get('ok'):
        return 'na'
    if not r['clear']:
        return 'hard'
    return 'safe' if r['left'] >= SAFE else 'tight'


LADDER = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.15, 1.3, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0]
FINE = 10


def _base(b):
    b = b or {}
    return dict(growth=b.get('growth') or 1.0, power=b.get('power'), powers=b.get('powers'))


def ladder_step(keys, stage, sv, pen, params=None, want='safe', upto=None, base=None):
    """LADDER 를 낮은 쪽부터 훑어 처음 성공하는 칸 번호(없으면 None). upto 칸까지만 본다(그보다 늦으면 비교에서 질 팀은 일찍 멈춤).
    육성이 늘면 집중 대상 순서가 바뀌어 결과가 단조롭지 않을 수 있어 이분 탐색 대신 «처음 성공»을 찾는다(codex 검토)."""
    ok = (lambda r: verdict(r) == 'safe') if want == 'safe' else (lambda r: r.get('ok') and r['clear'])
    last = len(LADDER) - 1 if upto is None else min(upto, len(LADDER) - 1)
    b = _base(base)
    for i in range(last + 1):
        if ok(evaluate(keys, stage, sv, pen, params, scale=LADDER[i], **b)):
            return i
    return None


def need_growth(keys, stage, sv, pen, params=None, want='safe', step=None, base=None):
    """깰만함(want='tight' 이면 클리어)이 되는 가장 작은 배수(지금 가정한 전투력 대비) 추정. 4.0 배에서도 안 되면 None.
    base = dict(growth, power, powers) = 지금 가정(evaluate 와 같은 뜻).
    LADDER 에서 처음 성공한 칸과 그 앞 칸 사이를 FINE 등분해 다시 «처음 성공»을 찾는다. step 을 주면 사다리 훑기를 건너뛴다."""
    ok = (lambda r: verdict(r) == 'safe') if want == 'safe' else (lambda r: r.get('ok') and r['clear'])
    cur = _base(base)
    i = ladder_step(keys, stage, sv, pen, params, want, None, base) if step is None else step
    if i is None:
        return None
    if i == 0:
        return LADDER[0]
    a, b = LADDER[i - 1], LADDER[i]
    for j in range(1, FINE):
        g = a + (b - a) * j / FINE
        if ok(evaluate(keys, stage, sv, pen, params, scale=g, **cur)):
            return g
    return b


def load(root=None):
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    q = json.load(open(os.path.join(root, 'data', 'quick.json'), encoding='utf-8'))
    pen = json.load(open(os.path.join(root, 'data', 'power_penalty.json'), encoding='utf-8'))['pen']
    merge_sm(q)
    return q, pen


def merge_sm(q):
    """스테이지별 난이도 보정(sm, tools/calibrate_quick.py)을 st 에 m 으로 넣는다 — 화면(QK 로딩)도 같게"""
    for ck, d in (q.get('sm') or {}).items():
        for sk, m in d.items():
            if sk in q['st'].get(ck, {}):
                q['st'][ck][sk]['m'] = m
