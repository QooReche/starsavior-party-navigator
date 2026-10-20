# -*- coding: utf-8 -*-
"""규칙 교정(P2~)의 영향 측정: 지금 엔진 결과를 골든(기준)과 비교해 순위가 얼마나 바뀌었는지 보여 준다.

  python -X utf8 -I tests/rank_check.py                                   # 지금 기본 규칙 vs 골든
  python -X utf8 -I tests/rank_check.py --base legacy                     # 교정 전(legacy) 규칙 -> 골든과 정확히 같아야 함
  python -X utf8 -I tests/rank_check.py --base legacy --rules-override '{"coop_trigger": "basic_only"}'   # 교정 하나만
  python -X utf8 -I tests/rank_check.py --matrix --md out.md --golden tests/golden/sim_golden_p1.json   # 교정마다 따로 + 전부

--rules-override: JSON 문자열 또는 @파일. 키가 rules/default.json 의 opts 이름이면 옵션, 대문자(formula, 예 COOP_CAP)면 엔진 상수.
--base: legacy = rules/default.json 의 legacy 값(교정 전) 위에 덮어쓰기 / default = 지금 기본값 위에 덮어쓰기.

보고: (a) 구원자 지표(combined_dpt, ally_dmg_gain_pct) 순위 상관(Spearman)·크게 움직인 구원자,
(b) 기준 적 상대 150팀 10턴 총 피해 Spearman·상위 20팀 겹침, (c) 대표 스테이지 처치 턴 변화(4딜덱 + 무작위 9팀)."""
import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
sys.path.insert(0, ROOT)
import golden_check as gc  # noqa: E402  (tools/ 를 path 에 넣고 sim_damage 를 읽는다)
import battlesim.engine as engine  # noqa: E402
import battlesim.metrics as metrics  # noqa: E402
import battlesim.rules as rules  # noqa: E402

PRISTINE = dict(rules.DEFAULT_OPTS)
PRISTINE_F = {k: getattr(engine, k) for k in rules.RULES['formula']}

# 교정 항목(설명용 이름, 덮어쓸 값) — 각각 「교정 전」 위에 하나만 켠다
CORRECTIONS = [
    ('협공: 기본기 뒤에만', {'coop_trigger': 'basic_only'}),
    ('협공: 1번에 1명', {'coop_single': True}),
    ('노바: 오토(버스트 안 씀)', {'nova_policy': 'auto'}),
    ('노바: 팀 공용 풀(수동 기준)', {'nova_pool': 'team'}),
    ('효과 적중 공식', {'debuff_model': 'hit_resist'}),
    ('강제 협공 대상 = 현재 공격력', {'forced_coop_target': 'live_atk'}),
    ('DoT 매 틱 재계산', {'dot_snapshot': 'live'}),
    ('장비 반영 순서', {'gear_order': 'databook'}),
    ('감소 합(상한 50%)', {'dmg_reduction': 'sum_cap'}),
    ('강제 협공이 협공 1명 자리 공유', {'forced_coop_slot': 'shared'}),
    ('강제 협공 자리 공유 + 협공 1명', {'forced_coop_slot': 'shared', 'coop_single': True}),
    ('약화 상태 시전자별·실패 시 그대로', {'debuff_state': 'per_caster'}),
    ('게이지 증감 기대값(경계)', {'gauge_expect': 'exact'}),
]


def apply_rules(base='default', override=None):
    """DEFAULT_OPTS(공유 dict)와 엔진 상수를 제자리에서 바꾼다. 캐시(UnitDef)도 비운다."""
    rules.DEFAULT_OPTS.clear()
    rules.DEFAULT_OPTS.update(PRISTINE)
    for k, v in PRISTINE_F.items():
        setattr(engine, k, v)
    if base == 'legacy':
        rules.DEFAULT_OPTS.update(rules.LEGACY_OPTS)
    for k, v in (override or {}).items():
        if k in PRISTINE:
            rules.DEFAULT_OPTS[k] = v
        elif k in PRISTINE_F:
            setattr(engine, k, v)
        else:
            raise SystemExit('모르는 규칙 이름: %s' % k)
    metrics._CACHE.clear()


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for t in range(i, j + 1):
                r[order[t]] = (i + j) / 2.0 + 1
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy) if vx and vy else 1.0


_NAMES = {}


def label(db, k):
    """이름이 하나뿐이면 이름, 같은 이름이 여럿이면 이름[key] (예: 아세라[waltz-asherah])"""
    u = db.units.get(k)
    if not u:
        return k
    if not _NAMES:
        for x in db.units.values():
            _NAMES[x['n']] = _NAMES.get(x['n'], 0) + 1
    return u['n'] if _NAMES[u['n']] == 1 else '%s[%s]' % (u['n'], k)


def compare(old, cur, db, top=6):
    keys = sorted(k for k in old['index'] if k in cur['index'])
    o = [old['index'][k]['combined_dpt'] for k in keys]
    n = [cur['index'][k]['combined_dpt'] for k in keys]
    og = [old['index'][k]['ally_dmg_gain_pct'] for k in keys]
    ng = [cur['index'][k]['ally_dmg_gain_pct'] for k in keys]
    rank_o = {k: i + 1 for i, k in enumerate(sorted(keys, key=lambda k: -old['index'][k]['combined_dpt']))}
    rank_n = {k: i + 1 for i, k in enumerate(sorted(keys, key=lambda k: -cur['index'][k]['combined_dpt']))}
    movers = []
    for k, a, b in zip(keys, o, n):
        pct = (b / a - 1) * 100 if a else 0.0
        movers.append(dict(key=k, name=label(db, k), old=a, new=b, pct=round(pct, 1), rank_old=rank_o[k], rank_new=rank_n[k]))
    movers.sort(key=lambda m: -abs(m['pct']))
    gmov = [dict(key=k, name=label(db, k), old=a, new=b, diff=round(b - a, 1)) for k, a, b in zip(keys, og, ng) if a != b]
    gmov.sort(key=lambda m: -abs(m['diff']))
    # 파티 150팀
    pt_o = [p['total'] for p in old['party']]
    pt_n = [p['total'] for p in cur['party']]
    top_o = set(sorted(range(len(pt_o)), key=lambda i: -pt_o[i])[:20])
    top_n = set(sorted(range(len(pt_n)), key=lambda i: -pt_n[i])[:20])
    pmov = sorted(range(len(pt_o)), key=lambda i: -abs(pt_n[i] / pt_o[i] - 1) if pt_o[i] else 0)[:3]
    # 스테이지
    cells, changed, rows = 0, 0, []
    for so, sn in zip(old['stages'], cur['stages']):
        ch = []
        for ro, rn in zip(so['rows'], sn['rows']):
            cells += 1
            if ro['ttk'] != rn['ttk']:
                changed += 1
            ch.append((ro['stage'], ro['ttk'], rn['ttk']))
        rows.append(dict(name=so['name'], team=[label(db, k) for k in so['team']], cells=ch))
    exact = not gc.diff({k: old[k] for k in ('index', 'party', 'stages')}, {k: cur[k] for k in ('index', 'party', 'stages')}, limit=1)
    return dict(exact=exact,
                index_spearman=round(spearman(o, n), 4), gain_spearman=round(spearman(og, ng), 4),
                index_movers=[m for m in movers if m['pct'] != 0][:top], gain_movers=gmov[:top],
                index_changed=sum(1 for a, b in zip(o, n) if a != b), n_units=len(keys),
                party_spearman=round(spearman(pt_o, pt_n), 4), top20_overlap=len(top_o & top_n),
                party_mean_pct=round((sum(pt_n) / sum(pt_o) - 1) * 100, 2),
                party_movers=[dict(team=[label(db, k) for k in old['party'][i]['team']], old=round(pt_o[i]), new=round(pt_n[i]),
                                   pct=round((pt_n[i] / pt_o[i] - 1) * 100, 1)) for i in pmov],
                stage_cells=cells, stage_changed=changed, stages=rows)


def fmt_ttk(x):
    return '-' if x is None else ('%.1f' % x)


def run_one(golden, db, base, override, top):
    apply_rules(base, override)
    cur = json.loads(json.dumps(gc.capture(), ensure_ascii=False, sort_keys=True))
    return compare(golden, cur, db, top)


def print_report(title, r, out):
    out('== %s' % title)
    out('  골든과 정확히 같음: %s' % ('예' if r['exact'] else '아니오'))
    out('  (a) 구원자 지표 combined_dpt Spearman %.4f (값이 바뀐 구원자 %d/%d), 아군 피해 증가(ally_gain) Spearman %.4f'
        % (r['index_spearman'], r['index_changed'], r['n_units'], r['gain_spearman']))
    for m in r['index_movers']:
        out('      %-28s %6d -> %6d (%+.1f%%)  순위 %d -> %d' % (m['name'], m['old'], m['new'], m['pct'], m['rank_old'], m['rank_new']))
    for m in r['gain_movers']:
        out('      [아군 피해 증가] %-20s %+.1f%% -> %+.1f%% (%+.1f%%p)' % (m['name'], m['old'], m['new'], m['diff']))
    out('  (b) 150팀 총 피해 Spearman %.4f, 상위 20팀 겹침 %d/20, 평균 변화 %+.2f%%' % (r['party_spearman'], r['top20_overlap'], r['party_mean_pct']))
    for m in r['party_movers']:
        out('      %s: %d -> %d (%+.1f%%)' % (', '.join(m['team']), m['old'], m['new'], m['pct']))
    out('  (c) 처치 턴 바뀐 칸 %d/%d' % (r['stage_changed'], r['stage_cells']))
    for s in r['stages']:
        diffs = ['%s %s->%s' % (st, fmt_ttk(a), fmt_ttk(b)) for st, a, b in s['cells'] if a != b]
        if diffs or s['name'] == '4딜덱':
            out('      %s [%s]: %s' % (s['name'], ', '.join(s['team']), '; '.join(diffs) or '변화 없음'))


def md_table(results):
    lines = ['| 항목 | 골든 재현 | 지표 Spearman | 값 바뀐 구원자 | 아군피해증가 Spearman | 150팀 Spearman | 상위20 겹침 | 150팀 평균 | 처치 턴 바뀐 칸 | 지표 최대 변동(상위 3) |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for title, r in results:
        mv = ', '.join('%s %+.1f%%' % (m['name'], m['pct']) for m in r['index_movers'][:3]) or '-'
        lines.append('| %s | %s | %.4f | %d/%d | %.4f | %.4f | %d/20 | %+.2f%% | %d/%d | %s |' % (
            title, '예' if r['exact'] else '아니오', r['index_spearman'], r['index_changed'], r['n_units'], r['gain_spearman'],
            r['party_spearman'], r['top20_overlap'], r['party_mean_pct'], r['stage_changed'], r['stage_cells'], mv))
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--golden', default=gc.GOLDEN)
    ap.add_argument('--base', choices=['default', 'legacy'], default='default')
    ap.add_argument('--rules-override', default=None)
    ap.add_argument('--matrix', action='store_true', help='교정 전 기준 + 교정 하나씩 + 전부(새 기본값) + 새 기본값의 수동 모드')
    ap.add_argument('--top', type=int, default=6)
    ap.add_argument('--md', default=None, help='표(markdown)를 이 파일에 저장')
    ap.add_argument('--json', default=None, help='전체 결과를 이 파일에 저장')
    a = ap.parse_args()
    with open(a.golden, encoding='utf-8') as f:
        golden = json.load(f)
    db = gc.sd.get_db()
    override = None
    if a.rules_override:
        txt = a.rules_override
        if txt.startswith('@'):
            with open(txt[1:], encoding='utf-8') as f:
                txt = f.read()
        override = json.loads(txt)
    results = []
    if a.matrix:
        plan = [('교정 전(legacy) - 골든 재현 확인', 'legacy', None)]
        plan += [(t, 'legacy', ov) for t, ov in CORRECTIONS]
        plan += [('전부 적용(새 기본값, 오토)', 'default', None), ('새 기본값 + 수동(노바 버스트 사용)', 'default', {'nova_policy': 'manual'})]
    else:
        plan = [('%s%s' % (a.base, (' + ' + json.dumps(override, ensure_ascii=False)) if override else ''), a.base, override)]
    for title, base, ov in plan:
        r = run_one(golden, db, base, ov, a.top)
        results.append((title, r))
        print_report(title, r, print)
    apply_rules('default', None)
    if a.md:
        tmp = a.md + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(md_table(results) + '\n')
        os.replace(tmp, a.md)
        print('표 저장:', a.md)
    if a.json:
        tmp = a.json + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump([dict(title=t, **r) for t, r in results], f, ensure_ascii=False, indent=1)
        os.replace(tmp, a.json)
    if a.matrix and not results[0][1]['exact']:
        print('[실패] 교정 전(legacy) 규칙이 골든을 재현하지 못함 -> legacy 경로가 바뀌었음')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
