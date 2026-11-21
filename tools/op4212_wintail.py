"""작전 42-12 승리 꼬리 판별: 판마다 사건 특징을 모아 이긴 판·진 판을 비교한다(읽기 전용 계측).

ingame_check 와 같은 입력·시드·실제 브레이크 스킬. 엔진 함수에 가로채기만 걸고 계산은 바꾸지 않는다.
결과(판별 특징 원값)는 저장소 밖에만 쓴다. 공개 문서엔 비율·효과 크기만 옮긴다.
턴 = 전역 턴(유닛 행동마다 +1, 적 포함 — 게임 좌상단 TURN 과 같은 단위).
"""
import argparse
from collections import Counter
from contextlib import ExitStack
import json
import math
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import ingame_check as check
from battlesim.mc import Battle

WATCH = ('영혼 구속', '침식', '응축')


def _boss(b):
    return next((u for u in b.all_foes if getattr(u.d, 'boss', False) and not u.summoned), None)


def measure(stage, runs, seed, myinfo, override=None):
    orig = {k: getattr(Battle, k) for k in ('run', 'final_dmg', 'log', 'cast', 'act', 'tough_hit')}
    rows = []

    def st(b):
        w = b.__dict__.get('_w')
        if w is None:
            w = b.__dict__['_w'] = dict(order=[], boss_slots=Counter(), boss_targets=Counter(), boss_first_target=Counter(),
                                        boss_breaks=[], foe_breaks=[], bskill=[], deaths=[], crit=[], heals=Counter(),
                                        ally_slots=Counter(), soul_max=0, soul_sum_max=0, eff_max=Counter(),
                                        boss_hp_at={}, ties=0, boss_casts=[], tough=[], opening=[], boss_acts_before_bs=None, start=None)
        return w

    def act(b, u):
        w = st(b)
        if w['start'] is None:
            w['start'] = {f'{x.name}#{x.side}{x.pos}': dict(spd=round(x.spd(), 2), prio=x._turn_prio) for x in b.allies + b.all_foes}
        living = [x for x in b.allies + b.all_foes if not x.dead and x is not u]
        if any(abs(x.gauge - u.gauge) < 1 and abs(x.spd() - u.spd()) < 1e-9 for x in living):
            w['ties'] += 1
        w['order'].append((b.global_turns, u.side, u.name, u.pos))
        r = orig['act'](b, u)
        if b.global_turns == 1:
            w['gwen_soul_t1'] = int(any(x.name == '그웬' and x.eff.get('영혼 구속') is not None
                                        and x.eff['영혼 구속'].stacks > 0 for x in b.allies))
        boss = _boss(b)
        if boss is not None:
            for t in (10, 20, 25, 30, 40):
                if b.global_turns >= t and t not in w['boss_hp_at']:
                    w['boss_hp_at'][t] = max(0.0, boss.hp) / boss.maxhp
            for n, e in boss.eff.items():
                if any(k in n for k in WATCH) and e.stacks > 0:
                    w['eff_max'][n] = max(w['eff_max'][n], e.stacks)
        souls = [max(x.eff['영혼 구속'].stacks, len(x.eff['영혼 구속'].inst or ())) for x in b.allies
                 if not x.dead and '영혼 구속' in x.eff and x.eff['영혼 구속'].stacks > 0]
        if souls:
            w['soul_max'] = max(w['soul_max'], max(souls))
            w['soul_sum_max'] = max(w['soul_sum_max'], sum(souls))
        return r

    def final(b, a, v, base, ctx, crit, *rest):
        if a.side == 0 and v.side == 1:
            st(b)['crit'].append(bool(crit))
        return orig['final_dmg'](b, a, v, base, ctx, crit, *rest)

    def cast(b, u, sk, *args, **kw):
        res = orig['cast'](b, u, sk, *args, **kw)
        if res is not None:
            w = st(b)
            if u.side == 1 and getattr(u.d, 'boss', False):
                w['boss_slots'][res.skill.slot] += 1
                w['boss_casts'].append((b.global_turns, res.skill.slot))
                for x in res.targets:
                    if x.side == 0:
                        w['boss_targets'][x.name] += 1
                if res.targets and res.targets[0].side == 0 and not res.skill.all:
                    w['boss_first_target'][res.targets[0].name] += 1
            elif u.side == 0:
                w['ally_slots'][(u.name, res.skill.slot, res.via or '')] += 1
            if b.global_turns <= 4:
                w['opening'].append((b.global_turns, u.name, res.skill.slot, res.via or ''))
        return res

    def tough(b, a, v, ctx):
        boss = _boss(b)
        if v is not boss:
            return orig['tough_hit'](b, a, v, ctx)
        before = v.sa
        r = orig['tough_hit'](b, a, v, ctx)
        if v.sa != before:
            st(b)['tough'].append((b.global_turns, a.name, ctx.skill.slot, ctx.via or '', before, v.sa))
        return r

    def log(b, **kw):
        w = st(b)
        if 'brk' in kw:
            boss = _boss(b)
            if boss is not None and kw['brk'] == boss.name:
                w['boss_breaks'].append(b.global_turns)
            elif any(x.name == kw['brk'] for x in b.all_foes):
                w['foe_breaks'].append(b.global_turns)
        elif 'bskill' in kw:
            w['bskill'].append(b.global_turns)
            if w['boss_acts_before_bs'] is None:
                boss = _boss(b)
                w['boss_acts_before_bs'] = boss.actions if boss is not None else None
        elif 'death' in kw:
            side = next((x.side for x in b.allies + b.all_foes if x.name == kw['death']), None)
            w['deaths'].append((b.global_turns, side, kw['death']))
        elif 'heal' in kw and 'to' in kw:
            w['heals'][kw['heal']] += 1
        return orig['log'](b, **kw)

    def run(b):
        result = orig['run'](b)
        w = st(b)
        boss = _boss(b)
        crit = w['crit']
        streak = best = 0
        for c in crit:
            streak = streak + 1 if c else 0
            best = max(best, streak)
        ally_deaths = [(t, n) for t, s, n in w['deaths'] if s == 0]
        foe_deaths = [(t, n) for t, s, n in w['deaths'] if s == 1 and (boss is None or n != boss.name)]
        rows.append(dict(
            result=b.result, turns=b.global_turns,
            boss_left=(max(0.0, boss.hp) / boss.maxhp) if boss is not None else None,
            boss_actions=boss.actions if boss is not None else None,
            boss_slots=dict(w['boss_slots']), boss_targets=dict(w['boss_targets']),
            boss_first_target=dict(w['boss_first_target']),
            boss_breaks=w['boss_breaks'], foe_breaks=w['foe_breaks'], bskill=w['bskill'],
            boss_acts_before_bs=w['boss_acts_before_bs'],
            ally_deaths=ally_deaths, foe_deaths=foe_deaths,
            crit_n=len(crit), crit_rate=(sum(crit) / len(crit)) if crit else None, crit_streak=best,
            heals=dict(w['heals']), ally_slots={'|'.join(k): v for k, v in w['ally_slots'].items()},
            soul_max=w['soul_max'], soul_sum_max=w['soul_sum_max'], eff_max=dict(w['eff_max']),
            boss_hp_at={str(k): v for k, v in w['boss_hp_at'].items()},
            opening=w['opening'], gwen_soul_t1=w.get('gwen_soul_t1'), ties=w['ties'], boss_casts=w['boss_casts'], tough=w['tough'], boss_sa_max=boss.sa_max if boss is not None else None, first_order=[f'{n}' for _, s, n, p in w['order'][:8]], start=w['start']))
        return result

    with ExitStack() as scope:
        for name, fn in dict(run=run, final_dmg=final, log=log, cast=cast, act=act, tough_hit=tough).items():
            scope.enter_context(patch.object(Battle, name, fn))
        summary = check.run(stage, runs, override, seed, myinfo=myinfo, bs_real=True)
    assert len(rows) == runs, (len(rows), runs)
    return dict(summary={k: summary[k] for k in ('sim_clear', 'runs', 'seed', 'party_power') if k in summary}, rows=rows)


# ---------- 판별
def features(r):
    """판 하나 → 비교할 숫자 특징(없으면 None). 승패를 직접 담은 값(남은 생명력·끝 턴)은 따로 둔다."""
    inf = math.inf
    ad = r['ally_deaths']
    bb = r['boss_breaks']
    f = {
        '보스 브레이크 횟수': len(bb),
        '보스 첫 브레이크 턴': bb[0] if bb else None,
        '보스 둘째 브레이크 턴': bb[1] if len(bb) > 1 else None,
        '보스 첫 궁극기 턴(없으면 끝 턴)': next((t for t, s in r['boss_casts'] if s == '궁극기'), r['turns']),
        '보스 브레이크 있음(0/1)': int(bool(bb)),
        '턴 3 그웬 추가 특수기(0/1)': int(any(t == 3 and n == '그웬' and v == 'extra' for t, n, s, v in r.get('opening', []))),
        '턴 1 그웬 영혼 구속 걸림(0/1)': r.get('gwen_soul_t1'),
        '졸개 브레이크 횟수': len(r['foe_breaks']),
        '브레이크 스킬 첫 발동 턴': r['bskill'][0] if r['bskill'] else None,
        '브레이크 스킬 발동 횟수': len(r['bskill']),
        '브레이크 스킬 전 보스 행동 수': r['boss_acts_before_bs'],
        '보스 행동 수(턴 30까지 환산 X, 원값)': r['boss_actions'],
        '보스 특수기 횟수': r['boss_slots'].get('특수기', 0),
        '보스 궁극기 횟수': r['boss_slots'].get('궁극기', 0),
        '보스 기본기 횟수': r['boss_slots'].get('기본기', 0),
        '감시자 첫 사망 턴': r['foe_deaths'][0][0] if r['foe_deaths'] else None,
        '감시자 둘째 사망 턴': r['foe_deaths'][1][0] if len(r['foe_deaths']) > 1 else None,
        '아군 첫 사망 턴(없으면 끝 턴)': ad[0][0] if ad else r['turns'],
        '아군 사망 있음(0/1)': int(bool(ad)),
        '아군 치명률(보스·졸개 대상 계산)': r['crit_rate'],
        '아군 치명 최장 연속': r['crit_streak'],
        '회복 발생 수': sum(r['heals'].values()),
        '영혼 구속 최대 중첩(한 명)': r['soul_max'],
        '영혼 구속 최대 합(아군 전체)': r['soul_sum_max'],
        '동률 행동 수(게이지·속도 같음)': r['ties'],
        '턴 20 보스 남은 생명력': r['boss_hp_at'].get('20'),
        '턴 30 보스 남은 생명력': r['boss_hp_at'].get('30'),
    }
    for n, v in r['eff_max'].items():
        f[f'보스 {n} 최대 중첩'] = v
    tot = sum(r['boss_targets'].values()) or None
    for n in ('프로페서M', '프레이', '아세라', '그웬'):
        hit = sum(v for k, v in r['boss_targets'].items() if n in k)
        f[f'보스 대상 비율: {n}'] = hit / tot if tot else None
    first = ad[0][1] if ad else None
    for n in ('프로페서M', '프레이', '아세라', '그웬'):
        f[f'첫 사망이 {n}(0/1)'] = int(first is not None and n in first)
    for k, v in r['ally_slots'].items():
        f['아군 시전: ' + k] = v
    return f


def _mw_auc(xs, ys):
    """AUC = P(이긴 판 값 > 진 판 값) + 0.5·P(같음). 0.5 = 차이 없음. 순위 합으로 계산."""
    allv = sorted([(v, 0) for v in xs] + [(v, 1) for v in ys])
    ranks, i = {}, 0
    rank_sum_x = 0.0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        avg = (i + j + 1) / 2
        rank_sum_x += avg * sum(1 for k in range(i, j) if allv[k][1] == 0)
        i = j
    n1, n2 = len(xs), len(ys)
    u = rank_sum_x - n1 * (n1 + 1) / 2
    auc = u / (n1 * n2)
    z = (u - n1 * n2 / 2) / math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12) if n1 and n2 else 0.0
    return auc, z


def contrast(rows, conditional_turn=None):
    """이긴 판 대 진 판. conditional_turn 이 있으면 그 턴 이상 버틴 판만(생존 길이 효과를 덜어냄)."""
    rs = [r for r in rows if conditional_turn is None or r['turns'] >= conditional_turn]
    feats = [features(r) for r in rs]
    win = [f for f, r in zip(feats, rs) if r['result'] == 'clear']
    lose = [f for f, r in zip(feats, rs) if r['result'] != 'clear']
    keys = sorted({k for f in feats for k in f})
    out = []
    for k in keys:
        xs = [f[k] for f in win if f.get(k) is not None]
        ys = [f[k] for f in lose if f.get(k) is not None]
        if len(xs) < 10 or len(ys) < 10:
            continue
        auc, z = _mw_auc(xs, ys)
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sd = math.sqrt((sum((v - mx) ** 2 for v in xs) + sum((v - my) ** 2 for v in ys)) / max(1, len(xs) + len(ys) - 2))
        out.append(dict(feature=k, win_mean=mx, lose_mean=my, win_n=len(xs), lose_n=len(ys),
                        auc=auc, z=z, d=(mx - my) / sd if sd else 0.0))
    out.sort(key=lambda r: -abs(r['auc'] - 0.5))
    return dict(n=len(rs), win=len(win), lose=len(lose), table=out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only', choices=check.SAMPLES, default='op4212')
    p.add_argument('--myinfo', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runs', type=int, default=1000)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--ov', type=json.loads)
    a = p.parse_args()
    if a.output.resolve().is_relative_to(ROOT):
        p.error('비공개 결과는 저장소 밖에만')
    if a.output.resolve() == Path(a.myinfo).resolve():
        p.error('입력 파일을 덮어쓰지 않음')
    check.low_priority()
    out = measure(a.only, a.runs, a.seed, a.myinfo, a.ov)
    out['contrast'] = contrast(out['rows'])
    out['contrast_survive30'] = contrast(out['rows'], 30)
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('clear', out['summary'].get('sim_clear'), 'saved', a.output)
    for r in out['contrast']['table'][:25]:
        print(f"{r['auc']:.3f} z={r['z']:+.1f} win={r['win_mean']:.3g} lose={r['lose_mean']:.3g}  {r['feature']}")


if __name__ == '__main__':
    main()
