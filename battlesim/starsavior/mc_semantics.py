# -*- coding: utf-8 -*-
"""설명문에 근거한 확률 전투용 의미 보정. 공유 Line/UnitDef는 변경하지 않는다."""
import copy
import re

from .parser import Line, ally_stack_trigger


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
    return lines
