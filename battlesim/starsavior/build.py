# -*- coding: utf-8 -*-
"""P5 육성 프리셋(장비·여정·잠재력) — 구원자별 「표준 세팅」(가정한 엔드게임 육성)을 가이드 DB 와 databook 데이터로 만든다.

근거(설계 docs/battlesim_design.md 「P5 상세」, 가정 값은 battlesim/rules/builds.json):
- 장비 주옵·세트 수치 = databook `equip`(T2 레전더리 +15 = +0 값 + 15 x 강화당 증가), 세트는 필요 개수마다 1회 발동(data).
- 구원자별 목걸이·반지 주옵·세트·잠재력 코드 = 가이드 DB `rawdata/guide_app-core.js` SAVIORS[].detail.equipment.pve(community).
  「A or B」·「A / B」·「A, B」면 첫 값, 세트 후보가 여럿이면 첫 후보. 세팅이 없는 신규 구원자는 builds.json 의 use_class_default 목록만
  클래스 기본값을 쓰고, 그 밖에 세팅이 없거나 읽히지 않으면 오류(BuildError)를 낸다.
- 잠재력 코드(AX5·BX·CX …) = databook `dict.pot` 의 특수 잠재력 「별빛의 궤적-AX5호」 등(효과 줄이 엔진과 같은 문법, data).
- 부옵 = 커뮤니티 1회 최대치 x 평균 롤 비율 x (부위당 4줄 중 역할에 맞는 줄, 줄마다 1 + 5/4 회), 부위 주옵과 같은 종류는 건너뜀(assumed).
- 여정(스텔라 아카이브) = 어려움 기록 예시를 주 스탯에 맞춰 배치, 변환 = 버림(여정 스탯 x 비율 x 클래스 계수), 기본값 쪽에 더함(data).
- 스탯 순서 = floor(((기본+레벨+여정) x (1+공명%) + 공명 정수) x (1+Σ%) + Σ정수), 치명·효과 적중/저항은 단순 합(data, stats.calc_stats).
  잠재력의 상시 스탯은 장비와 같은 Σ%·Σ정수 단계에서 한 번 더한다(전투 중 배율 passive 로 넘기지 않음).

수준: 'none'(장비·여정·잠재력 없음) / 'light'(주옵+세트만) / 'standard'(주옵+세트+부옵+여정+특수 잠재력)."""
import json
import math
import os
import re

from .data import SRC

LEVELS = ('none', 'light', 'standard')
GRADE_IX = 0           # equip.main[].v 의 0번 = T2 레전더리
ENH = 15               # +15
MAIN_KEY = {'공격력': 'atk', '생명력': 'hp', '방어력': 'def', '속도': 'spd', '공격력%': 'atkP', '생명력%': 'hpP', '방어력%': 'defP',
            '치명타 확률': 'cr', '치명타 피해': 'cd', '효과 적중': 'eh', '효과적중': 'eh', '효과 저항': 'er', '효과저항': 'er',
            '효과적중%': 'eh', '효과 적중%': 'eh', '효과저항%': 'er', '효과 저항%': 'er'}
NST_KEY = {'NST_ATK': 'atk', 'NST_HP': 'hp', 'NST_DEF': 'def', 'NST_TURN_SPEED': 'spd', 'NST_NV_RATE_ATK': 'atkP',
           'NST_NV_RATE_HP': 'hpP', 'NST_NV_RATE_DEF': 'defP', 'NST_RATE_CRITICAL': 'cr', 'NST_RATE_CRITICAL_DAMAGE': 'cd',
           'NST_RATE_EFFECT_HIT': 'eh', 'NST_RATE_EFFECT_EVADE': 'er'}
# 잠재력 상시 스탯 줄 -> gear 키와 배율(비율은 1/10000, 정수는 그대로). 강인도는 따로(sa).
POT_STAT = {'공격력%': ('atkP', 100), '생명력%': ('hpP', 100), '방어력%': ('defP', 100), '속도': ('spd', 1), '속도%': ('spdP', 100),
            '치명타 확률': ('cr', 100), '치명타 피해': ('cd', 100), '효과 적중': ('eh', 100), '효과 저항': ('er', 100),
            '공격력': ('atk', 1), '생명력': ('hp', 1), '방어력': ('def', 1)}
RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rules', 'builds.json')


class BuildError(ValueError):
    """가이드 세팅이 없거나 읽히지 않음(조용히 넘어가지 않는다)"""


_RULES = None


def build_rules():
    global _RULES
    if _RULES is None:
        with open(RULES_PATH, encoding='utf-8') as f:
            raw = json.load(f)
        _RULES = {k: v['value'] for k, v in raw.items() if not k.startswith('_')}
    return _RULES


_GUIDE = None


def guide_builds(src=SRC):
    """가이드 DB 의 구원자별 PVE 장비 세팅 {guide id: {necklace, ring, sets, potential, note}}(세팅 없는 구원자는 빠짐)"""
    global _GUIDE
    if _GUIDE is None or _GUIDE[0] != src:
        with open(os.path.join(src, 'rawdata', 'guide_app-core.js'), encoding='utf-8') as f:
            s = f.read()
        i = s.index('const SAVIORS = [')
        j = s.index('[', i)
        body = re.sub(r'\b[A-Z_]+\(\)', 'null', s[j:])     # PENDING_ARCANA() 같은 함수 호출은 JSON 이 아니다
        arr, _ = json.JSONDecoder().raw_decode(body)
        out = {}
        for x in arr:
            pve = ((x.get('detail') or {}).get('equipment') or {}).get('pve')
            if pve and pve.get('ring') and '미정' not in str(pve.get('ring')):
                out[x['id']] = dict(necklace=pve.get('necklace'), ring=pve.get('ring'), sets=list(pve.get('sets') or []),
                                    potential=pve.get('potential') or '', note=pve.get('note') or '')
        _GUIDE = (src, out)
    return _GUIDE[1]


def first_option(text):
    """「속도 or 공격력%」·「속도 / 공격력%」·「속도, 공격력%」 -> 첫 값"""
    t = str(text or '').strip()
    return re.split(r'\s+or\s+|\s*/\s*|\s*,\s*', t)[0].strip()


def parse_sets(text):
    """「통찰(4) + 투지(2)」·「방어(6)」·「생명(4)+ 장벽(2)」 -> [(세트 이름, 칸 수), ...]"""
    return [(m.group(1).strip(), int(m.group(2))) for m in re.finditer(r'([^\s(+]+)\s*\((\d)\)', str(text or ''))]


def potential_codes(text):
    """잠재력 문구 -> [(코드, 뒤 문구)] (순서 유지). 'AX5 - …부족… \\n AX6 - …95% 이상…' / 'BX / AX1 / EX' / 'AX1 / XX2 (생명력 흡수)'"""
    out = []
    for line in re.split(r'\n|\s/\s', str(text or '')):
        m = re.match(r'\s*([A-H]X\d?|XX\d)\b(.*)$', line.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def _pot_index(db):
    return {p['n']: p for p in db.main['dict']['pot'] if p.get('lv')}


def _main_value(db, slot_name, stat_name):
    """부위·주옵 이름 -> (gear 키, 값). 비율은 1/10000."""
    key = MAIN_KEY.get(stat_name)
    if key is None:
        return None, 0
    nst = {v: k for k, v in NST_KEY.items()}[key]
    for m in db.main['equip']['main']:
        if m['slot'] == slot_name and m['stk'] == nst:
            v0, inc = m['v'][GRADE_IX]
            return key, v0 + inc * ENH
    return None, 0


def _profile(code, ring_key):
    """잠재력 코드 첫 글자·반지 주옵 -> 부옵·여정 프로필(atk/hp/def/spd)"""
    c = (code or 'A')[0]
    if c == 'B':
        return 'hp'
    if c == 'C':
        return 'def'
    if c == 'D':
        return 'spd'
    return 'hp' if ring_key == 'hpP' else 'atk'


def guide_entry(db, key, u):
    """-> (세팅 dict, 출처 'guide'|'override'|'class_default'). 세팅이 없으면 BuildError"""
    R = build_rules()
    gkey = key.split('@')[0]
    gb = guide_builds(db.src).get(gkey)
    src = 'guide'
    if gb is None:
        if gkey not in R['use_class_default']:
            raise BuildError('가이드 DB 에 PVE 세팅이 없는 구원자: %s (rules/builds.json use_class_default 에 넣거나 overrides 로 지정)' % key)
        grp = u['r'] if u['r'] in ('서포터', '디펜더') else 'dealer'
        gb, src = dict(R['class_default'][grp]), 'class_default'
    ov = R['overrides'].get(gkey)
    if ov:
        gb = dict(gb, **ov)
        src = 'override'
    return gb, src


def make_build(db, key, u, level='standard', base_stats=None, passive_cr=0.0):
    """구원자 1명의 프리셋 -> dict(gear{...}, journey{...}, potential(이름 or None), pot_lines[raw], sa_bonus, summary{...}).
    gear/journey 는 stats.calc_stats 의 gear/journey 인자 형식. base_stats = 장비 없는 스탯(치명타 확률 판정용),
    passive_cr = 고유 패시브 상시 치명타 확률(비율, 0.3 = 30%)."""
    if level in (None, 'none'):
        return None
    if level not in LEVELS:
        raise ValueError('모르는 육성 수준: %s' % level)
    R = build_rules()
    gb, src = guide_entry(db, key, u)
    gear = {}
    summary = dict(level=level, source=src)

    def add(k, v):
        gear[k] = gear.get(k, 0) + v

    neck = first_option(gb['necklace'])
    ring = first_option(gb['ring'])
    mains = [('무기', '공격력'), ('장갑', '생명력'), ('갑옷', '방어력'), ('신발', '속도'), ('목걸이', neck), ('반지', ring)]
    piece_main = []
    for slot, st in mains:
        k, v = _main_value(db, slot, st)
        if k is None:
            raise BuildError('%s %s 주옵을 읽지 못함: %r' % (key, slot, st))
        add(k, v)
        piece_main.append(k)
    summary['mains'] = {slot: st for slot, st in mains}
    sets = parse_sets(gb['sets'][0] if gb['sets'] else '')
    if not sets or sum(n for _, n in sets) > 6:
        raise BuildError('%s 세트를 읽지 못함: %r' % (key, gb['sets']))
    sdef = {s['n']: s for s in db.main['equip']['sets']}
    for name, n in sets:
        sd = sdef.get(name)
        if sd is None:
            raise BuildError('%s 모르는 세트: %s' % (key, name))
        for _ in range(n // sd['parts']):
            for _lbl, _txt, nst, val in sd['stats']:
                add(NST_KEY[nst], val)
    summary['sets'] = ['%s(%d)' % s for s in sets]
    codes = potential_codes(gb['potential'])
    if not codes:
        raise BuildError('%s 잠재력 코드를 읽지 못함: %r' % (key, gb['potential']))
    profile = _profile(codes[0][0], MAIN_KEY.get(ring))
    summary['profile'] = profile
    out = dict(gear=gear, journey={}, potential=None, pot_lines=[], sa_bonus=0, summary=summary)
    if level == 'light':
        return out
    # 부옵: 부위마다 주옵과 같은 종류를 빼고 우선순위 앞에서 useful 줄, 줄마다 (1 + 강화 5회/4줄) 회 x 최대치 x 평균 비율
    smax, roll = R['sub_max'], R['sub_roll']
    per_line = 1 + 5.0 / R['sub_lines']
    subs = {}
    for pm in piece_main:
        lines = [k for k in R['sub_priority'][profile] if k != pm][:R['sub_useful_lines']]
        for k in lines:
            subs[k] = subs.get(k, 0) + per_line * smax[k] * roll
    # 여정: 어려움 기록 예시, 주 스탯 자리 바꿈, 클래스 계수
    js = list(R['journey']['stats'])
    mi = R['journey']['main_slot'][profile]
    js[0], js[mi] = js[mi], js[0]
    role = next((r for r in db.main['topics']['roles'] if r['n'] == u['r']), None)
    mul = role['mul'] if role else [1, 1, 1, 1, 1]
    out['journey'] = dict(atk=math.floor(js[0] * 1 * mul[0]), hp=math.floor(js[1] * 6 * mul[1]), **{'def': math.floor(js[2] * 0.5 * mul[2])},
                          eh=math.floor(js[3] * 4 * mul[3]), er=math.floor(js[4] * 4 * mul[4]))   # 집중·보호 1 = 0.04% = 4/10000
    summary['journey'] = dict(zip(('힘', '체력', '인내', '집중', '보호'), js))
    # 잠재력 고르기: 특수 잠재력을 뺀 치명타 확률(기본 + 패시브 상시 + 장비 + 부옵)로 AX5/AX6 같은 갈래를 정한다(순환 없음)
    pp = R['potential_pick']
    cr_pre = (base_stats or {}).get('cr', 500) + passive_cr * 10000 + gear.get('cr', 0) + subs.get('cr', 0)
    code = codes[0][0]
    for c, cond in codes:
        if '95%' in cond and '이상' in cond:
            if cr_pre >= pp['crit_threshold']:
                code = c
                break
        elif '부족' in cond:
            if cr_pre < pp['crit_threshold']:
                code = c
                break
    if not re.match(r'^[A-H]X\d$|^XX\d$', code):
        code = pp['pure'][code]
    name = '별빛의 궤적-%s호' % code
    pot = _pot_index(db).get(name)
    if pot is None:
        raise BuildError('%s 잠재력 데이터 없음: %s' % (key, name))
    out['potential'] = pot['n']
    summary['potential'] = code
    for raw in pot['lv'][-1][4]:
        m = re.match(r'^능력치:\s*(.+)$', raw.strip())
        if not m:
            out['pot_lines'].append(raw)
            continue
        for part in m.group(1).split(','):
            mm = re.match(r'^\s*(.+?)\s+([+-]?\d+(?:\.\d+)?)(%?)\s*$', part)
            nm, val = (mm.group(1).strip(), float(mm.group(2))) if mm else (part.strip(), None)
            if mm and nm == '강인도':
                out['sa_bonus'] += int(val)
            elif mm and nm in POT_STAT:
                k, sc = POT_STAT[nm]
                add(k, val * sc)
            else:
                out['pot_lines'].append('[상시] 능력치: %s' % part.strip())   # 엔진이 모르는 상시 스탯 -> 미지원 목록으로
    # 치명타 확률 100% 넘침 -> 넘는 부옵 몫을 치명타 피해로(롤 수 환산)
    cr_total = (base_stats or {}).get('cr', 500) + passive_cr * 10000 + gear.get('cr', 0) + subs.get('cr', 0)
    if cr_total > 10000 and subs.get('cr'):
        over = min(subs['cr'], cr_total - 10000)
        subs['cr'] -= over
        subs['cd'] = subs.get('cd', 0) + over / smax['cr'] * smax['cd']
    for k, v in subs.items():
        add(k, v)
    summary['subs'] = {k: round(v, 1) for k, v in subs.items()}
    return out


def unit_power(stats, pp=0, skill_level_sum=34):
    """databook 전투력 공식(app.js calcBP): 세 방식 최대값 x (1 + 0.06 + 스킬 레벨 합 x 0.01). stats 단위 = calc_stats(비율 1/10000).
    pp = 전투력 잠재력 PP 합(topics.bp 하나당 200), skill_level_sum = 스킬 레벨 합(가정: 최대 레벨 합 10+10+10+4)."""
    atk, hp, df, spd = stats['atk'], stats['hp'], stats['def'], stats['spd']
    cr = min(1.0, stats['cr'] / 10000.0)
    cdm = min(3.0, stats['cd'] / 10000.0)
    eh, ee = stats.get('eh', 10000) / 10000.0, stats.get('er', 0) / 10000.0
    aB, hB, dB = atk / 10 * 12, hp / 55 * 12, df / 5 * 12
    sp = (100 + (spd - 100) / 5) / 100
    ef = max(0.0, 1 + (eh - 1 + ee) / 10)
    pot = 1 + pp * 0.0001

    def crit_mix(x):
        return max(0.0, x * (1 - cr)) + x * cr * (1 + cdm)
    m1 = (crit_mix(aB) + hB + dB) * pot * sp * ef
    bal = (atk / 10 + hp / 55 + df / 5) / 3 * 12
    m2 = (crit_mix(bal) + hB + dB) * pot * sp * ef
    m3 = (aB + hB + dB) * (1 + (cr / 1 + cdm / 2) / 3) * pot * sp * ef
    return math.floor(max(m1, m2, m3) * (1 + 3 * 0.02 + skill_level_sum * 0.01))
