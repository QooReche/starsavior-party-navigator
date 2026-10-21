# -*- coding: utf-8 -*-
"""36-36 첫 별의 파장 계측 + 5개 실측 대조. 엔진 파일 수정 없이 프로세스 안에서만 실험.

python -X utf8 -I tools/boss_hit_diagnostic.py --runs 100 --bs --out docs/enemy_init_cd_diagnostic.json
pre_reduction은 방어율 적용 후, 피해 감소 합/보호막 적용 전이다.
post_reduction은 보호막 전, hp_loss는 타격 즉시 실제 HP 손실(반응 회복 전)이다.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import ingame_check as check
from battlesim import rules
from battlesim.mc import Battle
from battlesim.starsavior.foe import load_foe, foe_stats


def summary(xs):
    xs = sorted(xs)
    def pct(p):
        i = (len(xs) - 1) * p
        return xs[math.floor(i)] * (1 - i % 1) + xs[math.ceil(i)] * (i % 1)
    return dict(n=len(xs), mean=round(statistics.mean(xs), 3),
                p10=round(pct(.1), 3), p90=round(pct(.9), 3),
                min=round(xs[0], 3), max=round(xs[-1], 3))


def experiment(mode, runs, bs):
    rows, battles, facts = [], [], []
    original = {k: getattr(Battle, k) for k in ('deal', 'final_dmg', 'apply_damage', 'lines_of', 'spawn_wave')}

    def spawn(b):
        original['spawn_wave'](b)
        if mode == 'no_boss_atk_variant':
            raw = load_foe()
            for u in b.foes:
                if u.d.boss:
                    # 사본 stats로 교체: 원본 캐시/다음 실행에 영향을 남기지 않는다.
                    x = dict(raw['x'][u.d.xi]) if u.d.xi is not None else {}
                    x['a'] = [a for a in x.get('a', []) if raw['ak'][a[0]][1] not in ('NST_NV_RATE_ATK', 'NST_ATK')]
                    stats, _ = foe_stats(raw, raw['u'][u.d.ui], x, {'lv': u.d.level})
                    u.d.stats = dict(u.d.stats, atk=stats['atk'])

    def lines(b, u):
        result = original['lines_of'](b, u)
        if u.side == 1 and u.d.boss:
            if mode == 'no_gohang':
                result = [ln for ln in result if '〈고행〉' not in ln.raw]
            elif mode == 'no_boss_ramp':
                result = [ln for ln in result if not any(s in ln.raw for s in ('선명해지는 실루엣', '침식 심도 증가'))]
        return result

    def deal(b, a, ctx):
        tracked = (a.side == 1 and a.name == '공허순례자' and ctx.skill.name == '별의 파장'
                   and not getattr(b, '_diag_seen', False))
        if tracked:
            b._diag_seen = True
            b._diag_rows = []
            b._diag_ctx = ctx
            if not facts:
                facts.append(dict(atk=b.atk_stat(a, ctx), stats=a.d.stats, effects=list(a.eff),
                                  mods=dict(a.mods()), fx=b.fx, pen=b.pen, boss_actions=a.actions,
                                  allies=[dict(name=u.name, hp=u.maxhp, defense=b.def_stat(u),
                                               element=u.element, shield=u.shield_total()) for u in b.allies]))
        try:
            return original['deal'](b, a, ctx)
        finally:
            if tracked:
                rows.extend(b._diag_rows)
                battles.append(statistics.mean(row['hp_loss'] for row in b._diag_rows))
                b._diag_ctx = None

    def final(b, a, v, base, ctx, crit, cdv, pen, r, hctx):
        boss = a.side == 1 and a.d.boss
        if boss and (mode == 'boss_no_185' or
                     (mode == 'void_no_185' and a.name in ('공허순례자', '공허습격자'))):
            base /= rules.BASE_MULT
        if boss and mode == 'boss_no_aoe_div' and ctx.skill.all:
            base *= rules.AOE_DIV
        tracked = getattr(b, '_diag_ctx', None) is ctx
        captured = {}
        def profile(frame, event, arg):
            if event == 'return' and frame.f_code is original['final_dmg'].__code__:
                captured.update(frame.f_locals)
        old_profile, old_k, old_elem = sys.getprofile(), rules.DEF_K, a.element
        try:
            if boss and mode == 'boss_def_pvp':
                rules.DEF_K = 300.0  # 문서에 존재하는 PvP 식을 대입하는 민감도, 적용 권고 아님.
            if boss and mode == 'boss_no_element':
                a.element = None
            if tracked:
                sys.setprofile(profile)
            dmg = original['final_dmg'](b, a, v, base, ctx, crit, cdv, pen, r, hctx)
        finally:
            sys.setprofile(old_profile)
            rules.DEF_K, a.element = old_k, old_elem
        if tracked:
            c = captured
            pre = c['dmg'] + base * (1 - c['dr']) * c['dec'] * r * b.pen[a.side]
            row = dict(name=v.name, pre_reduction=100 * math.floor(pre) / v.maxhp,
                       post_reduction=100 * dmg / v.maxhp, hp_loss=0, absorbed=0,
                       defense_rate=c['dr'], reduction=c['dec'], increase=c['inc'], crit=crit)
            b._diag_rows.append(row)
            b._diag_pending = (v, row)
        return dmg

    def apply(b, a, v, dmg, kind, shieldable=True):
        pending = getattr(b, '_diag_pending', None)
        hp, sh = v.hp, v.shield_total()
        result = original['apply_damage'](b, a, v, dmg, kind, shieldable)
        if pending and pending[0] is v:
            row = pending[1]
            row['hp_loss'] = 100 * (hp - v.hp) / v.maxhp
            row['absorbed'] = 100 * (sh - v.shield_total()) / v.maxhp
            b._diag_pending = None
        return result

    ov = {'enemy_same_formula': False} if mode == 'all_enemy_no_185' else {}
    if mode == 'no_fx':
        ov['stage_fx_target'] = 'off'
    with patch.multiple(Battle, deal=deal, final_dmg=final, apply_damage=apply, lines_of=lines, spawn_wave=spawn):
        ratios = [check.run(name, runs, ov=ov, bs=bs) for name in check.SAMPLES]
    by_name = defaultdict(list)
    for row in rows:
        by_name[row['name']].append(row)
    stats = {name: {key: summary([row[key] for row in group])
                    for key in ('pre_reduction', 'post_reduction', 'hp_loss', 'absorbed')}
             for name, group in by_name.items()}
    return dict(mode=mode, ratios=ratios, first_hit=stats, battle_mean=summary(battles),
                facts=facts, hits=rows if mode == 'baseline' else [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=100)
    ap.add_argument('--bs', action='store_true')
    ap.add_argument('--modes', nargs='+', default=['baseline', 'boss_no_185', 'void_no_185', 'all_enemy_no_185',
                    'boss_no_aoe_div', 'no_boss_atk_variant', 'boss_def_pvp', 'boss_no_element',
                    'no_fx', 'no_gohang', 'no_boss_ramp'])
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    output = dict(runs=args.runs, seed=7, break_skill=args.bs, experiments=[])
    for mode in args.modes:
        result = experiment(mode, args.runs, args.bs)
        output['experiments'].append(result)
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k: result[k] for k in ('mode', 'battle_mean', 'first_hit')} |
                         {'ratios': [r['sim_ratio'] for r in result['ratios']]}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
