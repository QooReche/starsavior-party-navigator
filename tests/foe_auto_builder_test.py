# -*- coding: utf-8 -*-
"""tools/build_foe_auto.py 문구 파싱 경계(빌더 함수 단위, 비공개 표 없이 돎).

- 대상 머리말 RX_HEAD_NEW/new_auto_kinds: 「…」 효과 이름 안의 괄호(«「환상(해제불가)」 상태인 적 전체에게»)를 머리말로 읽음
  (11/14 수정 — 옛 정규식은 괄호에서 끊겨 홍염 양각 보스 «솟구치는 환영» 스킬 전체 짝짓기가 실패했음).
- effect_part: 조건 괄호 안의 대괄호·괄호 중첩을 세어 효과 부분만 남김.
- pair_lines: 대상 머리말은 효과 부분에서 읽음 — 피격 조건 «[스킬 대상 유형: 적 전체; …]» 의 낱말을 대상으로 읽어
  «… 자신에게 〈어긋난 시계바늘(해제불가)〉» 같은 줄(적 데이터 24줄)의 스킬 짝짓기가 실패하던 결함(11/14 수정).
- filters/conds: has/not_has·스택 조건·모르는 어휘.
실행: python -X utf8 -I tests/foe_auto_builder_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]
from tools.build_foe_auto import (AUTO_KINDS, RX_HEAD_NEW, Unknown, conds, effect_part, filters,   # noqa: E402
                                  new_auto_kinds, pair_lines)

ENEMY, ALLY = AUTO_KINDS['적'], AUTO_KINDS['아군']


def _h(line):
    m = RX_HEAD_NEW.search(line)
    return m.group('h').strip() if m else None


def test_head_paren_inside_quote():
    ln = "[스킬 사용 후] (조건: 내 공격 후 [특정 효과 보유 적 존재: 환상(해제불가)]) 「환상(해제불가)」 상태인 적 전체에게 '착란 체크용 버프' 해제"
    assert _h(ln) == '「환상(해제불가)」 상태인 적 전체'
    assert new_auto_kinds(ln) == ENEMY


def test_head_nested_and_multiple_quotes():
    ln = ('[스킬 사용 시작 시] (조건: 내 공격 시 [대상이 미보유: 보호막, 보호막(해제불가), 공허 방패(해제불가)]) '
          '「보호막, 보호막(해제불가), 공허 방패(해제불가)」 상태가 아닌 적 전체에게 〈X〉 (1턴)')
    assert _h(ln) == '「보호막, 보호막(해제불가), 공허 방패(해제불가)」 상태가 아닌 적 전체'
    ln = "[스킬 사용 후] 「착란」 · 「환상(해제불가)」 상태가 아닌 적 전체에게 〈착란〉 (지속 무한)"
    assert _h(ln) == '「착란」 · 「환상(해제불가)」 상태가 아닌 적 전체' and new_auto_kinds(ln) == ENEMY
    ln = '[스킬 사용 후] 「A(B(C))」 상태인 적 1명에게 〈X〉 (1턴)'                # 「」 안 겹친 괄호
    assert _h(ln) == '「A(B(C))」 상태인 적 1명'
    ln = '[스킬 사용 후] 「신부 경쟁(해제불가)」 상태인 적 중 공격력이 가장 높은 1명에게 〈Y〉 (지속 무한)'
    assert _h(ln) == '「신부 경쟁(해제불가)」 상태인 적 중 공격력이 가장 높은 1명' and new_auto_kinds(ln) == ENEMY


def test_head_plain_and_self_not_auto():
    assert new_auto_kinds('[스킬 사용 후] 적 전체에게 〈방어력 감소〉 (2턴)') is None
    assert new_auto_kinds('[스킬 사용 후] 스킬 대상에게 〈X〉 (2턴)') is None
    assert new_auto_kinds('[스킬 사용 후] 적 1명(자동 지정)에게 〈X〉 (2턴)') is None      # 옛 표기는 HEAD 표가 처리
    assert new_auto_kinds('[스킬 사용 후] 자신에게 〈X〉 (2턴)') is None
    assert new_auto_kinds('[턴 종료 시] 다른 아군 1명에게 〈초즌〉 (지속 무한)') == ALLY
    # 조건 괄호 안 «적 전체» 뒤에 «에게»가 오지 않으면 머리말이 아님 — 효과 부분 «자신에게»
    assert new_auto_kinds('[피해 처리 후] (조건: 내가 피격될 때 [스킬 대상 유형: 적 전체; 자신이 보유: A]) 자신에게 〈B〉') is None


def test_head_old_regex_regression():
    """옛 정규식(「…」 허용 전)은 효과 이름 안 괄호에서 머리말을 놓쳤다 — 같은 줄을 지금 정규식은 읽어야 함."""
    import re
    old = re.compile(r'(?:[)\]]\s+|^)(?P<h>[^()\[\]〈〉]*?(?:아군|적)(?: 중 [^()\[\]〈〉]*?)?(?: \d+명| 전체)?)(?:에게|의)\s')
    ln = '[스킬 사용 후] 「불협화음(해제불가)」 상태가 아닌 적 전체에게 행동 게이지 25%p 감소'
    m = old.search(ln)
    assert m is None or m.group('h').strip() != '「불협화음(해제불가)」 상태가 아닌 적 전체'
    assert _h(ln) == '「불협화음(해제불가)」 상태가 아닌 적 전체'


def test_effect_part():
    assert effect_part('[스킬 사용 후] (조건: 내 공격 후 [대상이 보유: A(해제불가), B]) 자신에게 기본기 추가 발동') == '자신에게 기본기 추가 발동'
    assert effect_part('[스킬 사용 후] (조건: 내 공격 후 [스킬 대상 유형: 적 전체]) (추가) 적 전체에게 X') == '(추가) 적 전체에게 X'
    assert effect_part('[스킬 사용 후] 적 전체에게 〈A(해제불가)〉 (2턴)') == '적 전체에게 〈A(해제불가)〉 (2턴)'
    assert effect_part('적 전체에게 X') == '적 전체에게 X'


def test_pair_uses_effect_part_head():
    ln = '[피해 처리 후] (조건: 내가 피격될 때 [스킬 대상 유형: 적 전체; 자신이 보유: 타임 패러독스]) 자신에게 〈어긋난 시계바늘(해제불가)〉 (지속 무한)'
    assert pair_lines([ln], [{'m_BuffTargetType': 'NSETT_SELF'}]) is not None
    assert pair_lines([ln], [{'m_BuffTargetType': 'NSETT_ENEMY_ALL'}]) is None
    # 효과 부분이 적 전체면 그대로 ENEMY_ALL
    ln2 = '[스킬 사용 후] (조건: 내 공격 후 [자신이 보유: A]) 적 전체에게 〈B〉 (2턴)'
    assert pair_lines([ln2], [{'m_BuffTargetType': 'NSETT_ENEMY_ALL'}]) is not None
    assert pair_lines([ln2], [{'m_BuffTargetType': 'NSETT_SELF'}]) is None
    # 조건 괄호 안 «(자동 지정)» 낱말이 아니라 효과 부분의 자동 지정 여부로 판정
    ln3 = '[스킬 사용 후] (조건: 내 공격 후 [대상: 적 1명(자동 지정)]) 자신에게 〈C〉'
    assert pair_lines([ln3], [{'m_BuffTargetType': 'NSETT_SELF'}]) is not None


def test_pair_new_head_and_times():
    auto = {'m_BuffTargetType': 'NSETT_AUTO_ENEMY', 'AutoTargetId': 30}
    ln = '[스킬 사용 후] 「환상(해제불가)」 상태인 적 전체에게 〈착란 체크용 버프〉'
    assert pair_lines([ln], [auto]) == [(0, auto)]
    assert pair_lines([ln], [{'m_BuffTargetType': 'NSETT_ENEMY_ALL'}]) is None      # 풀어 쓴 조건 머리말 = AUTO 계열만
    ln2 = '[스킬 사용 후] 스킬 대상에게 〈X〉 {2회 부여}'
    tgt = {'m_BuffTargetType': 'NSETT_TARGET'}
    assert pair_lines([ln2], [tgt, tgt]) == [(0, tgt), (0, tgt)]
    assert pair_lines([ln2], [tgt]) is None


def test_filters_has_not_has():
    bname = {'BI_A': '초즌', 'BI_A2': '초즌', 'BI_B': '협공 불가'}
    assert filters({'IsSpecificBuff': ['BI_A', 'BI_A2']}, bname) == [['has', ['초즌']]]       # 같은 이름은 한 번
    assert filters({'IsNotSpecificBuff': ['BI_B'], 'IsBoss': True}, bname) == [['not_has', ['협공 불가']], 'boss']
    assert filters({'FrontLineTargetRate': 5000}, bname) == [['front', 0.5]]
    for bad in ({'IsSpecificBuff': ['BI_NONE']}, {'IsSomethingNew': True}, {'IsBoss': False}):
        try:
            filters(bad, bname)
        except Unknown:
            pass
        else:
            raise AssertionError(bad)
    t = {'IsNotUnableToAct': True, 'IsNotSpecificBuff': ['BI_DISABLE_CROSS_ATTACK'], 'IsHighAtk': True}
    assert filters(t, bname, forced_coop=True) == ['not_unable_to_coop', ['not_has', ['협공 불가']], 'high_atk']


def test_conds():
    bname = {'BI_A': '응집된 생기(해제불가)', 'BI_B': '초즌', 'BI_C': '다른 것'}
    assert conds({'SelfSpecificBuff': ['BI_A'], 'SelfBuffLevelCount': 3}, bname) == [['self_stack_eq', '응집된 생기(해제불가)', 3]]
    assert conds({'SelfSpecificBuff': ['BI_A'], 'ExistAllySpecificBuff': ['BI_B'], 'AllyDie': True}, bname) == [
        ['self_has', ['응집된 생기(해제불가)']], ['ally_has', ['초즌']], ['ally_dead']]
    for bad in ({'SelfSpecificBuff': ['BI_A', 'BI_C'], 'SelfBuffLevelCount': 1}, {'Unknown': 1}):
        try:
            conds(bad, bname)
        except Unknown:
            pass
        else:
            raise AssertionError(bad)


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
