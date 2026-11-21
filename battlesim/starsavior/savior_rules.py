# -*- coding: utf-8 -*-
"""구원자별 예외 규칙 표 — 새 구원자에게 숨은 표지·특수 대상 규칙이 있으면 이 파일의 표에 행만 더한다.

표 해석기는 아래 matches() 한 벌이다. 조건(cond) 문법:
  'kind': 'buff'               효과 사전(ln.eff)의 값이 같음        'kind_in': ('buff', 'gauge')  값이 목록 안에 있음
  'consume': TRUTHY            효과 값이 참                          'ln_slot' / 'ln_src' / 'ln_kind'(_in)  줄(Line) 속성
  'ln_raw_has': '문자열'        줄 원문에 포함
표의 행 순서 = 옛 if/elif 순서(먼저 맞는 행이 이긴다). 키 오타는 tests/savior_rules_test.py 가 시뮬 DB 키와 대조해 잡는다.
절차라 표로 못 옮긴 것(세레스·메이드 리디아 5쌍 전개, 스마일 물폭탄 삽입)은 marker_se.normalize 의 후처리로 남는다.
"""

TRUTHY = object()


def matches(ln, cond):
    e = ln.eff
    for k, want in cond.items():
        if k.startswith('ln_'):
            if k == 'ln_raw_has':
                ok = want in ln.raw
            elif k.endswith('_in'):
                ok = getattr(ln, LINE_ATTR[k[:-3]]) in want
            else:
                ok = getattr(ln, LINE_ATTR[k]) == want
        elif want is TRUTHY:
            ok = bool(e.get(k))
        elif k.endswith('_in'):
            ok = e.get(k[:-3]) in want
        else:
            ok = e.get(k) == want
        if not ok:
            return False
    return True


LINE_ATTR = {'ln_slot': 'slot', 'ln_src': 'src_kind', 'ln_kind': 'kind'}


# ------------------------------------------------------------------ 패시브를 액티브 뒤에 실행(mc_semantics.after_active_se)
# AfterActiveSkillSe 예외(build 26610546 SE_TEMPLET_SKILL_1, SE 10024023·10154022·10174012·10254013/14·10404015/16·10434018/19·10444012).
# 패시브 줄만 해당. 키 목록 중 하나라도 맞으면 참(순서 무관).
AFTER_ACTIVE = [
    (('smile', 'tyria', 'gwen', 'claire'), {'kind': 'extra_cast'}),
    (('trish',), {'name': '도약'}),
    (('cristelle',), {'kind': 'chain'}),
    (('tyria',), {'name': '참극의 가시(해제불가)'}),
    (('gwen',), {'name': '전기 충격(해제불가)', 'consume': TRUTHY}),
    (('scarlet',), {'kind': 'remove', 'name_in': ('노멀볼(해제불가)', '세븐볼(해제불가)')}),
]


def after_active(key, ln):
    return any(key in keys and matches(ln, cond) for keys, cond in AFTER_ACTIVE)


# ------------------------------------------------------------------ 숨은 표지 SE(marker_se, 스위치 marker_se_flow=client)
# 26752678 U1–U7. 표지 이름은 marker_se 상수와 같다(여기서 다시 적는 것은 표 가독성 때문 — marker_se 가 이 값을 가져다 씀).
LYN = '린 아군 버프 타겟 판별용'
PRAYER = '소심한 기도'
CERES_Z, CERES_X = '특수기 체크용 Z', '특수기 체크용 X'
LYDIA = '게이지 감소 체크용 버프'
FRESH, OLD = '물폭탄 미부착 체크용 버프', '물폭탄 제거 체크용 버프'
WEDDING, DAMAGE = '궁극기 카운팅 디버프', '피해량 개별 체크용 버프'
TURN, COUNT = '아군 턴 카운팅 버프', '대상 수 체크용 버프'
LOCK = '메이드 리디아 패시브 행게 카운팅 버프'

# 키 -> 표지 SE 로 다시 펴는 줄의 범위(marker_se.scope). 이 표의 키 = marker_se.KEYS
MARKER_SCOPE = {
    'lyn': {'ln_src': 'active', 'ln_slot': '궁극기'},
    'elisa': {'ln_src': 'active', 'ln_slot': '궁극기'},
    'wedding-epindel': {'ln_src': 'active', 'ln_slot': '궁극기'},
    'lydia': {'ln_src': 'active', 'ln_slot': '특수기'},
    'ceres': {'ln_src': 'passive', 'ln_raw_has': '특수기 체크용'},
    'sunshine-cat-smile': {'ln_src': 'passive', 'ln_kind': 'own_post'},
    'lydia-moon-caster': {'ln_src': 'passive', 'ln_kind_in': ('ally_ts', 'ally_pre', 'ally_post', 'enemy_ts')},
}

# 키 -> [(조건, 효과 사전에 덮어쓸 값)] — 줄마다 먼저 맞는 행 하나만. 주석 숫자 = AutoTarget id
MARKER_TARGETS = {
    'lyn': [
        ({'name': LYN, 'kind': 'buff'}, {'native_target': ('ally_element', '별')}),          # 40
        ({'name': '치명타 피해 증가'}, {'native_target': ('ally_has', LYN)}),                # 41; 빈 대상은 빈 채로
    ],
    'elisa': [
        ({'name': PRAYER}, {'native_target': ('ally_all', None)}),
        ({'kind': 'gauge', 'val': 80}, {'native_target': ('ally_not_has', PRAYER)}),           # 1010
        # TARGET 은 죽은 유닛 제외(부활 자신만 예외)
        ({'target': '스킬 대상', 'kind_in': ('buff', 'gauge')}, {'native_target': ('target', None)}),
    ],
    'lydia': [
        ({'name': LYDIA}, {'native_target': ('enemy_has', '미지의 주문')}),                   # 10341
        ({'kind': 'gauge'}, {'native_target': ('enemy_has', LYDIA)}),                          # 10342
    ],
    'wedding-epindel': [
        ({'name': WEDDING}, {'native_target': ('enemy_shield', None)}),                        # 42
        ({'name': DAMAGE}, {'native_count_damage': True}),
        ({'kind': 'gauge'}, {'native_target': ('enemy_has', WEDDING)}),                        # 10561
    ],
    'sunshine-cat-smile': [
        ({'name': OLD}, {'native_target': ('enemy_not_has', FRESH)}),                         # 10461
        ({'name': '물폭탄', 'kind': 'remove'}, {'native_target': ('enemy_has', OLD), 'native_after': True}),   # 10463
        # SE10464016·10464020 은 따로 있는 두 줄(RepeatBuffCount 아님)
        ({'name': '물폭탄', 'times': 2}, {'times': 1, 'native_target': ('enemy_has', FRESH)}),               # 10462
        ({'target': '스킬 대상'}, {'native_target': ('target', None)}),
    ],
    # 세레스·메이드 리디아: 5쌍 전개(카운터 표지 부여/삭제)는 marker_se.normalize 절차. 아래는 그 밖의 줄
    'ceres': [
        ({'name': TURN}, {'native_target': ('ally_other_one_has', '책임 전가(해제불가)')}),
    ],
    'lydia-moon-caster': [
        ({'name': TURN}, {'native_target': ('ally_other_one_has', '책임 전가(해제불가)')}),
    ],
}


def marker_target(key, ln):
    """MARKER_TARGETS 에서 이 줄에 맞는 첫 행의 덮어쓸 값(없으면 None)."""
    for cond, upd in MARKER_TARGETS.get(key, ()):
        if matches(ln, cond):
            return upd
    return None


# ------------------------------------------------------------------ 데이터 자동 대상 규칙을 표지 보유자가 없어도 그대로 씀(mc.Battle.line_spec)
# PC 26752678 NKM:7152-7178(스마일·길레 표지는 보유자가 없을 수 있음 — 복수 대상 실패는 빈 대상), NKM:7135-7187·7523-7546(길레 승급:
# 전체 대상 필터 불일치면 대상 없음). (키, 스위치, 스위치 값, 조건, rule_hits 이름) — 먼저 맞는 행.
KEEP_NATIVE_SELECTOR = [
    ('sunshine-cat-smile', 'supported_marker_targets', 'client', {'native_target': TRUTHY}, 'supported_marker_targets'),
    ('gille', 'supported_marker_targets', 'client', {'kind': 'remove', 'name': '길레 마지막 타격 체크용 버프'},
     'supported_marker_targets'),
    ('gille', 'gille_promotion_target', 'marker', {'ln_slot': '특수기', 'name': '피날레(해제불가)'}, 'gille_promotion_target'),
]


def keep_native_selector(key, ln, mc):
    """맞는 행의 rule_hits 이름(없으면 None)."""
    for k, switch, on, cond, hit in KEEP_NATIVE_SELECTOR:
        if k == key and mc[switch] == on and matches(ln, cond):
            return hit
    return None


def table_keys():
    """표에 오른 구원자 키 전부(오타 검사용)."""
    keys = {k for keys, _ in AFTER_ACTIVE for k in keys}
    keys |= set(MARKER_SCOPE) | set(MARKER_TARGETS) | {row[0] for row in KEEP_NATIVE_SELECTOR}
    return keys
