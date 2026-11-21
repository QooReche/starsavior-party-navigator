# -*- coding: utf-8 -*-
"""26752678 U1–U7: hidden buff SEs, in client order.

Only processed facts are kept here; private source locations are documented in
docs/marker_se_26752678.md. Normal targeting remains owned by mc.py.
"""
import copy
import math

from .savior_rules import (MARKER_SCOPE, CERES_X, CERES_Z, COUNT, DAMAGE, FRESH, LOCK, LYDIA, LYN, OLD, PRAYER,  # noqa: F401
                           TURN, WEDDING, marker_target, matches)

RULE = 'marker_se_flow'
KEYS = frozenset(MARKER_SCOPE)      # 구원자 키·범위·대상 규칙 = savior_rules.MARKER_SCOPE·MARKER_TARGETS 표
HIDDEN = frozenset((LYN, PRAYER, CERES_Z, CERES_X, LYDIA, FRESH, OLD,
                    WEDDING, DAMAGE, TURN, COUNT, LOCK))


def scope(key, ln):
    cond = MARKER_SCOPE.get(key)
    return cond is not None and matches(ln, cond)


def enabled(d, rules):
    return rules.get(RULE) == 'client' and d.key in KEYS


def clone(ln):
    ln = copy.copy(ln)
    ln.eff, ln.params = dict(ln.eff), list(ln.params)
    return ln


def normalize(d, lines):
    """Restore flattened SE pairs, explicit targets and template lifetimes."""
    out = []
    for original in lines:
        if not scope(d.key, original):
            out.append(original)
            continue
        ln = clone(original)
        e, name = ln.eff, ln.eff.get('name')
        e.update(native_se=True, rule_key=RULE)
        if e['kind'] == 'buff' and name in HIDDEN:
            e['native_hidden'] = True
        upd = marker_target(d.key, ln)        # 키별 대상 규칙 표(savior_rules.MARKER_TARGETS), 먼저 맞는 행 하나
        if upd:
            e.update(upd)
        if d.key in ('ceres', 'lydia-moon-caster'):
            counter = CERES_X if d.key == 'ceres' else COUNT
            mark = CERES_Z if d.key == 'ceres' else COUNT
            if e['kind'] == 'buff' and name == counter and e.get('max') == 5:
                # Five grant/delete pairs. Each condition is re-evaluated after
                # the preceding deletion (NKM:16103-16116,16374-16405).
                delete = next(x for x in lines if x.slot == ln.slot and x.kind == ln.kind
                              and x.eff['kind'] == 'remove' and x.eff.get('name') == mark
                              and '자동 지정' in x.eff['target'])
                for _ in range(5):
                    grant, remove = clone(ln), clone(delete)
                    grant.eff.update(times=1)
                    remove.eff.update(native_se=True, rule_key=RULE,
                                      native_target=('enemy_one_has', mark))
                    out.extend((grant, remove))
                continue
            if e['kind'] == 'remove' and name == mark and '자동 지정' in e['target']:
                continue
        out.append(ln)
    if d.key == 'sunshine-cat-smile':
        # The public text folds two unconditional grants into its first row.
        grant = next((x for x in out if x.eff.get('native_target') == ('enemy_has', FRESH)), None)
        if grant:
            last = max(i for i, x in enumerate(out) if x.eff.get('name') == OLD)
            out.insert(last + 1, clone(grant))
    return out


def targets(b, owner, ln, ctx):
    spec = ln.eff.get('native_target')
    if spec is None:
        return None
    kind, name = spec
    if kind == 'target':
        # NKM:16550-16559 resolves caster.TargetUid, not every hit record.
        return [ctx.target] if ctx.target is not None and not ctx.target.dead else []
    pool = b.alive(owner.side if kind.startswith('ally') else 1 - owner.side)
    if kind == 'ally_all':
        return list(pool)
    if kind == 'ally_element':
        return [x for x in pool if x.element == name]
    if kind == 'enemy_shield':
        # AutoTarget 42 names the PC shield buff templates, not shield HP.
        names = ('보호막', '보호막(해제불가)', '공허 방패(해제불가)',
                 '저항 장막(해제불가)', '파프닐의 강림(해제불가)')
        return [x for x in pool if any(x.has(n) for n in names)]
    if kind == 'ally_other_one_has':
        pool = [x for x in pool if x is not owner]
    selected = [x for x in pool if x.has(name) != ('not_has' in kind)]
    if 'one' in kind:
        selected = selected or list(pool)  # single-target filter failure keeps candidates
        if selected:
            return [selected[0] if len(selected) == 1 else b.R(owner.side).choice(selected)]
    return selected


def run_batch(b, owner, lines, ctx):
    if not any(ln.eff.get('native_se') for ln in lines):
        return False
    for ln in lines:
        if b._per_target(owner, ln, ctx):
            b.run_per_target(owner, ln, ctx)
        elif ln.eff.get('native_se') and any(k in ('대상이 보유', '대상이 미보유') for k, _ in ln.params):
            # AfterMyAttack checks current buff state against one hit record;
            # the SE receiver remains caster.TargetUid (not the matching record).
            for target in ctx.targets:
                probe = copy.copy(ctx)
                probe.target, probe.targets = target, [target]
                if b.line_ok(owner, ln, probe):
                    b.exec_line(owner, ln, ctx)
                    break
        elif b.line_ok(owner, ln, ctx):
            b.exec_line(owner, ln, ctx)
    return True


def apply_hidden(b, owner, ln, ctx):
    e = ln.eff
    if not e.get('native_hidden'):
        return False
    name = e['name']
    props = {}
    if e.get('native_count_damage'):
        n = min(3, sum(x.stack(WEDDING) for x in b.alive(1 - owner.side)))
        props = {'피해 증가': 15 * n}
    tg = targets(b, owner, ln, ctx)
    if tg is None:
        tg = b.resolve(owner, e['target'], ctx)
    for x in tg or ():
        if x.dead:
            continue
        persistent = name in (CERES_X, LOCK) or (name == COUNT and x is owner)
        duration = 1 if name == TURN else math.inf
        obj = b.put_eff(x, name, props, dur=duration, maxs=e.get('max') or 1,
                       add=e.get('times', 1), src=owner, cat='marker',
                       fixed=name in (LYN, TURN, LOCK), refresh_props=True)
        obj.check = not persistent and name != TURN
        if obj.check:
            obj.check_turn = b.global_turns
            b.check_pending.append((x, name))
        if name == TURN:
            obj.clock, obj.fresh = 'any_turn', False
            obj.dur = 1
        b.dirty(x)
    return True
