# -*- coding: utf-8 -*-
"""설명문에 근거한 확률 전투용 의미 보정. 공유 Line/UnitDef는 변경하지 않는다."""
import copy
import re
from collections import defaultdict

from .parser import Line, ally_stack_trigger, parse_props, _perm_apply


def description(sk):
    return sk.raw.get('dx') or sk.raw.get('d1') or ''


def trigger_rule(sk, lines):
    desc = description(sk)
    stack = ally_stack_trigger(sk, lines)
    if stack:
        return dict(event='ally_post', stack=stack, exclude_self=True)
    m = re.match(r'\[([^]]+)\] 사용 후 적의 생명력이 (\d+)% 이하이면', desc)
    if m:
        return dict(event='own_post', skill=m[1], hp=int(m[2]) / 100)
    if desc.startswith('전체 공격에 피격 후 타격자에게'):
        return dict(event='hit', aoe=True)
    if desc.startswith('적에게 피격 후 회피 발생 시 타격자에게'):
        return dict(event='hit', evade=True)
    m = re.match(r'자신을 제외한 아군이 \[([^]]+)\] 상태인 적을 타격 후 자신의 \[([^]]+)\] 스택이 (\d+)개 이상이면', desc)
    if m:
        return dict(event='ally_post', mark=m[1], stack=(m[2], int(m[3])), exclude_self=True,
                    consume=int(m[3]), trigger_only=True)
    m = re.match(r'아군이 타격 후 자신의 \[([^]]+)\][이가] 최대 중첩 상태이면', desc)
    if m and '자신이 가장 최근에 타격한 적을 우선 공격' in desc:
        caps = {ln.eff['max'] for ln in lines if ln.eff.get('name') == m[1] and ln.eff.get('max')}
        if len(caps) == 1:
            return dict(event='ally_post', stack=(m[1], caps.pop()), recent=True, consume_all=True)
    return None


def normalized_lines(d):
    """카운팅용 내부 효과를 원자적 승급/실제 타격 수로 치환한다."""
    lines = list(d.lines)
    # 최대 스택 -> 임시 표지 -> 소비/승급 -> 표지 삭제의 공통 패턴.
    for marker in list(lines):
        e, p = marker.eff, dict(marker.params)
        if marker.kind != 'own_ts' or e['kind'] != 'buff' or '카운팅' not in e['name']:
            continue
        source, threshold = p.get('자신이 보유'), p.get('중첩수')
        if not source or not threshold:
            continue
        upgrade = next((ln for ln in lines if ln.slot == marker.slot and ln.kind == 'own_ts'
                        and dict(ln.params).get('자신이 보유') == e['name'] and ln.eff['kind'] == 'buff'), None)
        consume = next((ln for ln in lines if ln.slot == marker.slot and ln.kind == 'own_ts'
                        and ln.eff['kind'] == 'remove' and ln.eff['name'] == source), None)
        if upgrade is None or consume is None or not upgrade.eff.get('max'):
            continue
        replacement = copy.copy(marker)
        replacement.eff = dict(kind='stack_promote', source=source, threshold=int(threshold),
                               upgrade=upgrade.eff, upgrade_raw=upgrade.raw)
        lines = [replacement if ln is marker else ln for ln in lines
                 if ln is not upgrade and ln is not consume
                 and not (ln.eff['kind'] == 'remove' and ln.eff['name'] == e['name'])]

    for raw in getattr(d, 'u', {}).get('sk', []):
        desc = raw.get('dx') or raw.get('d1') or ''
        if '타격한 대상의 수' not in desc:
            continue
        slot = raw['sl']
        m = re.search(r'\[([^]]+)\] 사용 후 타격한 대상의 수에 비례하여 자신의 행동 게이지를 \[?(\d+)%\]? 증가시키며 최대 \[?(\d+)%\]?', desc)
        if m:
            skill = next((s for s in d.skills.values() if s.name == m[1]), None)
            if skill is None:
                continue
            affected = [ln for ln in lines if ln.slot == slot and dict(ln.params).get('사용 스킬') == skill.slot
                        and ('체크용' in ln.raw)]
            ln = Line('[스킬 사용 후] (조건: 내 공격 후 [사용 스킬: %s]) 자신에게 행동 게이지 %s%%p 증가' % (skill.slot, m[2]), slot, 'passive')
            ln.eff = dict(ln.eff, per_hit=True, hit_cap=int(m[3]) // int(m[2]))
            lines = [x for x in lines if x not in affected] + [ln]
        m = re.search(r'\[([^]]+)\] 상태인 아군이.*?해당 아군 턴에 타격 후 타격한 대상의 수만큼 자신에게 \[([^]]+)\][을를] 발생시키며 타격 당 최대 (\d+)회', desc)
        if m:
            mark, name, cap = m[1], m[2], int(m[3])
            grant = next(ln for ln in lines if ln.slot == slot and ln.kind == 'ally_post'
                         and ln.eff.get('name') == name and ln.eff['kind'] == 'buff')
            count = copy.copy(grant)
            count.params = [('자신 포함', '아니오'), ('시전자가 보유', mark), ('시전자 턴', '예')]
            count.eff = dict(grant.eff, per_hit=True, hit_cap=cap)
            new = []
            for ln in lines:
                if ln.slot == slot and ('대상 수 체크용' in ln.raw or '아군 턴 카운팅 버프' in ln.raw):
                    if ln.kind == 'ally_post' and ln.eff['kind'] in ('gauge', 'buff') and ln.eff.get('name') != name and '대상 수 체크용' not in ln.raw:
                        ln = copy.copy(ln)
                        ln.params = [(k, mark if k == '시전자가 보유' else v) for k, v in ln.params] + [('시전자 턴', '예')]
                        new.append(ln)
                    continue
                new.append(ln)
            lines = new + [count]
    return description_lines(d, lines)


def normalized_definition(d):
    """공유 정의는 보존하고 쉼표 복합 상시 능력치를 확률 전투에만 적용."""
    if getattr(d, '_compound_normalized', False):
        return d
    compound = [ln for ln in d.lines if ln.kind == 'perm' and ',' in ln.raw]
    if not compound:
        return d
    result = copy.copy(d)
    result._compound_normalized = True
    result.passive = copy.copy(d.passive)
    for ln in compound:
        _, props = parse_props(ln.raw.split('능력치:', 1)[1])
        for stat, val in props.items():
            _perm_apply(result.stats, result.passive, dict(stat=stat, val=val))
    return result


def description_lines(d, lines):
    """정본에 명시된 범위·순서를 ef에 보충한다. key별 예외를 만들지 않는다."""
    raws = {s['sl']: s for s in getattr(d, 'u', {}).get('sk', []) if not s['sl'].startswith('변형')}
    if not raws:
        return lines
    out = []
    for original in lines:
        if original.kind == 'perm' and ',' in original.raw:
            _, props = parse_props(original.raw.split('능력치:', 1)[1])
            for stat, val in props.items():
                part = Line('[상시] 능력치: %s %+g%%' % (stat, val), original.slot, original.src_kind)
                if not _perm_apply({}, defaultdict(float), part.eff):
                    part.eff = dict(kind='ignored', why='상시 능력치 미지원: ' + stat)
                out.append(part)
            continue
        ln = copy.copy(original)
        ln.eff, ln.params = dict(original.eff), list(original.params)
        desc = raws.get(ln.slot, {})
        desc = desc.get('dx') or desc.get('d1') or ''
        # ef의 49.99 이하 표현은 정본이 명시한 50 미만으로 복원한다.
        hp = re.search(r'자신의 생명력이 ([\d.]+)% 미만', desc)
        if hp:
            ln.raw = re.sub(r'자신 HP ([\d.]+)% 이하',
                            lambda m: '자신 HP %s%% 미만' % hp[1]
                            if abs(float(m[1]) - (float(hp[1]) - 0.01)) < 1e-8 else m[0], ln.raw)
        if re.search(r'\(자신 HP [\d.]+%', ln.raw):
            ln = Line(ln.raw, ln.slot, ln.src_kind, decimal_hp=True)
        e = ln.eff
        name = e.get('name', '')
        if e['kind'] == 'buff' and name:
            # 수혜자 속성: 공격 대상 조건/시전자 속성과 독립적으로 필터링한다.
            for sentence in desc.split('. '):
                if '[' + name + ']' not in sentence:
                    continue
                elem = re.search(r'(태양|달|별|질서|혼돈) 속성 아군 (전체|한명)', sentence)
                conditional = re.search(r'아군 대상이 (태양|달|별|질서|혼돈) 속성이라면', sentence)
                if elem and '아군' in e.get('target', ''):
                    e['target'] = ('자신 제외 ' if '자신을 제외한' in sentence else '') + elem[1] + ' 속성 아군 ' + ('전체' if elem[2] == '전체' else '1명')
                elif conditional and e.get('target') == '스킬 대상':
                    e['beneficiary_element'] = conditional[1]
            crit = re.search(r'치명타가 발생한 대상의 수만큼 자신에게 \[' + re.escape(name) + r'\].*?최대 (\d+)회', desc)
            if crit:
                e.update(per_crit=True, hit_cap=int(crit[1]))
        # 정본과 ef 양쪽에서 확인된 비례 피해만 시전 문맥으로 옮긴다.
        count = re.search(r'(적이 보유한 (?:강화 효과|약화 효과|\[[^]]+\])|자신이 보유한 강화 효과|적 전체의 \[보호막\])'
                          r' 개수 당 피해량이 \[?([\d.]+)%\]? 증가하며 최대 (\d+)개', desc)
        if count and count[1] == '적 전체의 [보호막]':
            # 실제 보호막으로 직접 판정하므로 간접 카운팅 표지는 생성하지 않는다.
            if e['kind'] == 'buff' and '카운팅' in name:
                continue
            if e['kind'] == 'gauge' and re.search(r'타격 시 \[보호막\] 상태인 대상의 행동 게이지', desc):
                e.update(target='스킬 대상', shield_only=True)
                ln.params = []
                ln.kind, ln.trig = 'own_pre', None
        if count and '1개당 위 수치만큼 적용' in ln.raw:
            named = re.search(r'\[([^]]+)\]', count[1])
            scope = ('shield_all' if count[1].startswith('적 전체') else 'self_good' if count[1].startswith('자신')
                     else 'target_named' if named else 'target_harmful' if '약화' in count[1] else 'target_good')
            ln.eff = dict(kind='count_damage', scope=scope, name=named[1] if named else None,
                          val=float(count[2]), cap=int(count[3]))
            ln.params = [(k, v) for k, v in ln.params if k not in ('대상 약화효과 보유', '대상이 보유', '특정 효과 보유 적 존재')]
        if '효과 지속 턴' in ln.raw:
            ext = re.search(r'(?:\[([^]]+)\]|모든 약화 효과)를 (\d+)턴 연장', desc)
            if ext:
                ln.eff = dict(kind='extend', target='스킬 대상', name=ext[1], val=int(ext[2]), judge='효과 적중 판정' in ln.raw)
        if '스킬 쿨타임' in ln.raw and '증가' in ln.raw:
            cd = re.search(r'(기본기|특수기|궁극기) 쿨타임을 (\d+)턴 증가', desc)
            if cd:
                e['cd_slot'] = cd[1]
        if re.search(r'강인도 격파 (?:후|시)', desc):
            ln.params = [('이번 타격 격파' if k == '대상 브레이크' else k, v) for k, v in ln.params]
        if '약화 효과를 모두 해제하고' in desc and '약화효과 해제' in ln.raw:
            ln.kind, ln.bound = 'before_heal', True
        # 사용 시/타격 시 최대 스택 소거와 타격 후 부여는 서로 다른 단계다.
        if e['kind'] == 'remove' and e.get('target') == '자신' and ln.kind == 'own_post':
            for sentence in desc.split('. '):
                before = re.search(r'(?:타격 시|사용 시).*?(?:모두 소거|모두 소거하고)', sentence)
                if before and e['name'] in before[0] and not re.search(r'(?:타격 후|사용 후)', before[0]):
                    ln.kind = 'own_pre'
                    ln.trig = (ln.trig or '').replace('내 공격 후', '내 공격 시')
                    break
        out.append(ln)
    # 표지는 선행 조건용이며 지속 버프가 아니다. 명칭 대신 참조 관계로 식별.
    references = {n.strip() for ln in out for k, v in ln.params
                  if k in ('자신이 보유', '자신이 미보유', '대상이 보유', '시전자가 보유') for n in v.split(',')}
    for ln in out:
        e = ln.eff
        if (e['kind'] == 'buff' and e['name'] in references and not e['props']
                and ln.phase in ('스킬 사용 시작 시', '스킬 사용 후', '피해 처리 직전', '피해 처리 후')
                and not e.get('max') and e.get('dur') in (None, float('inf'))):
            e['cast_marker'] = True
        consumers = [other for other in out if other is not ln and other.kind == ln.kind and other.phase == ln.phase]
        own = e.get('target') == '자신'
        refkeys = ('자신이 보유', '자신이 미보유') if own else ('대상이 보유', '대상이 미보유')
        used_here = any(e.get('name') in [n.strip() for n in v.split(',')]
                        for other in consumers for k, v in other.params if k in refkeys)
        if (e['kind'] == 'buff' and used_here and not e.get('consume')
                and not any(k in ('자신이 보유', '자신이 미보유', '대상이 보유', '대상이 미보유')
                            and e['name'] in [n.strip() for n in v.split(',')] for k, v in ln.params)):
            e['pre_grant'] = True
    return out
