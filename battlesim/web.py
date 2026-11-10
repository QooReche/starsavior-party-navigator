# -*- coding: utf-8 -*-
"""브라우저 시뮬(sim_worker.js, Pyodide) 진입점 — 화면이 부르는 함수 둘. PC 에서도 같은 코드로 시험한다(tests/web_test.py).

run_auto(stage, party, n, seed, extra)   -> JSON 문자열: 오토 결과 요약
run_manual(stage, party, n, seed, extra) -> JSON 문자열: 수동 정책 4종 중 최선 + 그 정책의 대표 1판 서순
stage = "콘텐츠/탭/스테이지", party = {"units": [{key, stats_override}], "leader": 칸 번호 또는 None}(칸 = 전열1, 전열2, 후열1, 후열2),
extra = simulate options 의 JSON(예: {"build": "standard", "rules_override": {"power_penalty": "model"}}).
"""
import json
import math

from .api import simulate

# 수동 정책: (자동 대상, 노바 버스트) — 옛 사전 계산(build_sim_results.POLICIES)과 같다
POLICIES = [('boss_first', 'any_attack'), ('boss_first', 'ult_only'), ('lowest_hp', 'any_attack'), ('lowest_hp', 'ult_only')]
CARD = [1, 2, 0, 3]     # 시뮬 칸(전열1, 전열2, 후열1, 후열2) -> 화면 카드 칸(후열1, 전열1, 전열2, 후열2)
SEQ_TURNS = 12


def _opts(extra, pol=None, **kw):
    o = json.loads(extra or '{}') if isinstance(extra, str) or extra is None else dict(extra)
    if pol:
        ro = dict(o.get('rules_override') or {})
        ro.update(nova_policy='manual', ally_auto_target=pol[0], manual_burst=pol[1])
        o['rules_override'] = ro
    o.update(kw)
    return o


def _enc(stage, o):
    """길방 EX 선택(options.guild = {level, sets, support})이 있으면 BFB 전투, 없으면 기존 스테이지. guild 키는 simulate 옵션에서 뺀다."""
    g = o.pop('guild', None)
    if g:
        return {'guild': g}
    c = o.pop('cosmo_raid', None)       # 코스모 게이트 시즌 전투: {boss, step, level} — api 의 encounter.cosmo_raid
    return {'cosmo_raid': c} if c else {'stage': stage}


def cosmo_summary(cr, top_q=0.2):
    """코스모 판별 점수(score_runs 등) -> 요약값만(판별 배열은 작업자 밖으로 내지 않음): 평균·상위 점수·클리어율·깎은 비율.
    상위 점수 = 판별 점수 상위 top_q 비율(올림) 판의 평균. 반올림은 사사오입(JS Math.round 와 같게; 파이썬 round 는 짝수 반올림)"""
    sc = sorted(cr['score_runs'], reverse=True)
    n = len(sc)
    m = max(1, math.ceil(n * top_q - 1e-9))
    half_up = lambda x: int(math.floor(x + 0.5))
    return dict(mean=half_up(sum(sc) / n), top=half_up(sum(sc[:m]) / m), clear=round(sum(1 for c in cr['clear_runs'] if c) / n, 4),
                frac=round(sum(cr['damage_frac_runs']) / n, 4), n=n)


def _unit_map(party, r):
    """화면 카드용 {구원자 key: [피해 기여, 쓰러질 확률]} — per_unit 은 「이름#칸」 순서가 시뮬 칸 순서"""
    keys = [u['key'] if isinstance(u, dict) else u for u in party['units']]
    out = {}
    for i, v in enumerate(r['per_unit'].values()):
        if i < len(keys):
            out[keys[i]] = [round(v.get('dmg_share') or 0, 3), round(v.get('death_p') or 0, 3)]
    return out


def _break_summary(r):
    return {k: r['break_skill'][k] for k in ('name', 'uses', 'dmg', 'supported')}


def run_auto(stage, party, n, seed, extra=None):
    op = _opts(extra, n_runs=n, seed=seed)
    top_q = op.pop('cosmo_top_q', 0.2)
    r = simulate(party, _enc(stage, op), op)
    o = r['outcome']
    extra_out = {'cosmo': cosmo_summary(r['cosmo_raid'], top_q)} if r.get('cosmo_raid') else {}
    first = sorted(((v.get('first_death_p') or 0, k) for k, v in r['per_unit'].items()), reverse=True)
    st = r.get('star_turn')
    return json.dumps(dict(clear=o['clear_p'], t60=(st['p'] if st else None), prog=o.get('progress'), progs=r.get('prog_runs'), via=r.get('ally_via') or {}, wipe=o['wipe_p'], timeout=o['timeout_p'], ci=o['ci95']['clear'], n=o['n_runs'],
                           ttk=o['ttk_median'], ta=o.get('ttk_actions_median'), first=(first[0][1] if first and first[0][0] > 0 else None),
                           first_p=(first[0][0] if first else 0), gate=r['unsupported'].get('gate_ok', True),
                           power=r.get('party', {}).get('power'), u=_unit_map(party, r), bs=_break_summary(r), **extra_out), ensure_ascii=False)


def seq_from_timeline(tl, max_turns=SEQ_TURNS):
    """타임라인 -> 서순 행: 모델 기준 턴(100틱) 하나 = 한 행, 칸 = 화면 카드 순서(4칸), 칸마다 행동 목록(옛 build_sim_results 와 같은 규칙)"""
    rows, last = {}, 0
    for e in tl or []:
        if e.get('side') != 0 or 'pos' not in e:
            continue
        turn = max(1, int(math.ceil(e['turn'] - 1e-9)))
        last = max(last, turn)
        if turn > max_turns:
            continue
        sl = e['skill']
        k = 'U' if sl.startswith('궁극기') else 'S' if sl.startswith('특수기') else 'B'
        if e.get('all'):
            tg = '전체'
        elif e.get('tgt_side') == 1:
            tg = '보스' if e.get('tgt_boss') else (e['targets'][0] if e.get('targets') else '')
        elif e.get('tgt_side') == 0:
            tg = ('아군 ' + e['targets'][0]) if e.get('targets') else ''
        else:
            tg = ''
        a = {'k': k, 'tg': tg}
        if e.get('via'):
            a['v'] = e['via']
        if e.get('nb'):
            a['nb'] = 1
        c = CARD[e['pos']]
        row = rows.setdefault(turn, {'t': turn, 'c': [[], [], [], []]})
        row['c'][c].append(a)
        if e.get('nb'):
            row.setdefault('nb', []).append([c, k])
    return dict(rows=[rows[t] for t in sorted(rows)], turns=last)


def run_manual(stage, party, n, seed, extra=None):
    best = None
    for pol in POLICIES:
        op = _opts(extra, pol, n_runs=max(10, n // 3), seed=seed + 11)
        o = simulate(party, _enc(stage, op), op)['outcome']
        key = (o['clear_p'], -(o['ttk_median'] if o['ttk_median'] is not None else 1e9))
        if best is None or key > best[0]:
            best = (key, pol)
    pol = best[1]
    op = _opts(extra, pol, n_runs=n, seed=seed, per_run=True)
    r = simulate(party, _enc(stage, op), op)
    o = r['outcome']
    runs = r.get('runs') or []
    clears = [(i, t) for i, (res, t) in enumerate(runs) if res == 'clear']
    if clears:      # 대표 1판: 클리어한 판 중 처치 턴이 중앙값에 가장 가까운 판(같으면 앞 번호), 없으면 첫 판(실패 예시)
        ts = sorted(t for _, t in clears)
        med = ts[(len(ts) - 1) // 2]
        idx = min(clears, key=lambda it: (abs(it[1] - med), it[0]))[0]
        kind = 'clear'
    else:
        idx, kind = 0, (runs[0][0] if runs else 'wipe')
    op = _opts(extra, pol, n_runs=1, seed=seed, run_offset=idx, timeline=True)
    tl = simulate(party, _enc(stage, op), op).get('timeline')
    sq = seq_from_timeline(tl)
    sq.update(run=idx, kind=kind, ttk=(runs[idx][1] if runs else None))
    return json.dumps(dict(c=o['clear_p'], ci=o['ci95']['clear'], t=o['ttk_median'], n=o['n_runs'],
                           prog=o.get('progress'), progs=r.get('prog_runs'),
                           pol=list(pol), seq=sq, bs=_break_summary(r)), ensure_ascii=False)
