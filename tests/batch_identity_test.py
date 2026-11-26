# -*- coding: utf-8 -*-
"""묶음 실행 동일성 시험 — web.run_auto_batch(여러 팀을 한 묶음으로, 조우·의미 해석 캐시 공유) == 팀마다 run_auto 를 따로 부른 것.

작업자(sim_worker.js)는 훑기·예선에서 여러 팀을 한 요청으로 받아 AutoBatch 로 돌린다(docs/fullscreen_measure_1121.md «묶음 후»).
판 시드(seed*1000003 + run_offset + r)는 팀·판 번호만으로 정해지므로 결과 JSON 이 글자 그대로 같아야 한다.
섞는 것: 작전·회랑·코스모(팀마다 다른 난이도 = 다른 조우) 스테이지, 1판·8판, 같은 팀 두 번, 팀별 브레이크·재점화·raw_runs·merge_raw(이어 돌리기)·규칙 덮어쓰기.

사용: python -X utf8 -I tests/batch_identity_test.py
일부러 깨뜨려 보기(시험 안에서 돌림 — 각각 묶음 결과가 달라져야 함 = 이 시험이 팀 간 누수를 잡는다):
  - 조우 캐시 키에서 팀 옵션을 빼먹음(스테이지 이름만): 코스모 난이도가 다른 팀이 앞 팀 조우를 받음
  - 의미 해석 캐시(묶음 공유) 키를 정의 대신 칸(진영·칸 번호)으로: 다음 팀이 앞 팀 구원자의 줄을 받음
    (정적 검사 support_report 재사용은 run_auto 요약에 나오는 값이 바뀌지 않아 이 시험으로 못 잡음 — 그래서 묶음 공유 대상에서 뺐음)
  - 아군 정의(defs)를 묶음 첫 팀 것으로 재사용
대조군: 팀끼리 결과가 실제로 달라야 한다(모두 같으면 누수를 못 잡음)."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from battlesim import api, mc, web  # noqa: E402

BASE = {'build': 'standard', 'rng_streams': True, 'rules_override': {'power_penalty': 'model'}}


def _teams(q):
    ks = sorted(q['sv'])
    return [['emily', 'fei', 'professor-m', 'wedding-carmen'], ks[0:4], ks[9:13], ks[20:24], ks[30:34]]


def batches():
    """(stage, n, 요청 options, [팀 {key, party, options}]) — 화면 예선·훑기 요청과 같은 모양"""
    import gen_quick_calib as G
    from battlesim import quick
    q, _ = quick.load(ROOT)
    out = []
    for content, sk, stage, extra in (('op', '아가논 시가지|SECTOR 36-36', 'op/아가논 시가지/SECTOR 36-36', {}),
                                      ('op', '레이븐 월|SECTOR 31-36', 'op/레이븐 월/SECTOR 31-36', {'rekindle': 3}),
                                      ('clo', '성간 회랑|FLOOR 300', 'clo/성간 회랑/FLOOR 300', {'star_turns': 40})):
        st = q['st'][content][sk]
        parties = [G.party_spec(q, o, o[1], o, 1.0, st) for o in _teams(q)]
        for n in (1, 8):
            teams = []
            for i, p in enumerate(parties + parties[:1]):       # 같은 팀 두 번(묶음 안 재사용)
                o = {'break_skill': {'name': '큐브 과부하', 'level': 5} if i % 2 else None}
                if i == 2:
                    o['raw_runs'] = True
                if i == 3:
                    o['rules_override'] = {'power_penalty': 'off'}   # 팀별 규칙 차이(남은 스위치)
                teams.append({'key': 't%d' % i, 'party': p, 'options': o})
            out.append((stage, n, dict(BASE, **extra), teams))
    # 이어 돌리기(예선 2차): 1차 raw 를 merge_raw 로
    stage, n, opt, teams = out[0]
    first = {t['key']: json.loads(web.run_auto(stage, t['party'], 8, 1, json.dumps(web.team_options(opt, dict(t['options'], raw_runs=True)))))['raw']
             for t in teams}
    out.append((stage, 24, opt, [dict(t, options=dict(t['options'], run_offset=8, merge_raw=first[t['key']])) for t in teams]))
    # 코스모: 팀마다 다른 난이도(= 다른 조우)를 한 묶음에
    st = q['st']['op']['아가논 시가지|SECTOR 36-36']
    parties = [G.party_spec(q, o, o[1], o, 1.0, st) for o in _teams(q)[:3]]
    cos = [{'key': 'c%d' % i, 'party': parties[i % 3], 'options': {'cosmo_raid': {'step': 3, 'level': lv}}} for i, lv in enumerate((0, 12, 0, 18))]
    out.append(('cosmo/x/y', 2, dict(BASE), cos))
    # 길방: 팀마다 다른 EX 선택(레벨·지원·세트 = 다른 조우·BFB 상태 기계)을 한 묶음에
    gd = [({'level': 6, 'support': 'fire', 'sets': [0] * 4}), ({'level': 6, 'support': 'fire', 'sets': [3] * 4}),
          ({'level': 2, 'support': 'none', 'sets': [0] * 4}), ({'level': 6, 'support': 'fire', 'sets': [0] * 4})]
    gd = [dict(g, seasonId=30111) for g in gd]
    out.append(('guild/x/EX', 2, dict(BASE), [{'key': 'g%d' % i, 'party': parties[i % 3], 'options': {'guild': g}} for i, g in enumerate(gd)]))
    return out


def individual(stage, n, opt, teams):
    return [(t['key'], web.run_auto(stage, t['party'], n, 1, json.dumps(web.team_options(opt, t['options'])))) for t in teams]


def batched(stage, n, opt, teams):
    return list(web.run_auto_batch(stage, teams, n, 1, json.dumps(opt)))


def compare():
    bad, total, distinct = [], 0, 0
    for stage, n, opt, teams in batches():
        a, b = individual(stage, n, opt, teams), batched(stage, n, opt, teams)
        total += len(teams)
        bad += [(stage, n, x[0]) for x, y in zip(a, b) if x != y]
        distinct += len({r for _, r in a}) > 2
    return bad, total, distinct


def test_batch_equals_individual():
    bad, total, distinct = compare()
    nb = len(batches())
    return not bad and distinct == nb, '%d묶음 %d팀 중 다름 %d %s / 팀끼리 결과가 갈린 묶음 %d/%d' % (nb, total, len(bad), bad[:2], distinct, nb)


def _mutants():
    orig_enc, orig_party = api._shared_encounter, api._norm_party

    def enc_key_stage_only(spec, shared):
        if shared is None:
            return orig_enc(spec, shared)
        k = 'only-one'
        if k not in shared.enc:
            shared.enc[k] = api._norm_encounter(spec)
        w, tl, fx, un, meta = shared.enc[k]
        return [list(x) for x in w], tl, fx, un, dict(meta)

    orig_lines = mc.Battle.lines_of

    def lines_leak(self, u):
        sc = self._semantic_cache
        if sc is None or (u.side == 1 and not self.enemy_lines):
            return orig_lines(self, u)
        k = ('slot', u.side, u.pos)
        if k not in sc:
            sc[k] = orig_lines(self, u)
        return sc[k]

    first = {}

    def party_leak(spec, db, mode, build=None, mc=None):
        r = orig_party(spec, db, mode, build, mc)
        return first.setdefault('v', r)

    def leak_party_batch(run):
        def f(*a):
            first.clear()
            return run(*a)
        return f

    yield '조우 키에서 팀 옵션 누락', lambda: setattr(api, '_shared_encounter', enc_key_stage_only), lambda: setattr(api, '_shared_encounter', orig_enc), None
    yield '의미 해석 캐시 키 = 칸', lambda: setattr(mc.Battle, 'lines_of', lines_leak), lambda: setattr(mc.Battle, 'lines_of', orig_lines), None
    yield '아군 정의 재사용', lambda: setattr(api, '_norm_party', party_leak), lambda: setattr(api, '_norm_party', orig_party), leak_party_batch


def test_mutants_caught():
    """누수를 일부러 넣으면 묶음 결과가 개별 결과와 달라져야 함(개별 결과는 원래 코드로 먼저 구함)"""
    cases = batches()
    want = [individual(*c) for c in cases]
    caught, names = 0, []
    for name, on, off, wrap in _mutants():
        diff = 0
        for c, w in zip(cases, want):
            on()
            try:
                run = wrap(batched) if wrap else batched
                got = run(*c)
            finally:
                off()
            diff += got != w
        caught += diff > 0
        names.append('%s→%d묶음 다름' % (name, diff))
    return caught == 3, ', '.join(names)


TESTS = [test_batch_equals_individual, test_mutants_caught]


def main():
    fail = 0
    for t in TESTS:
        ok, msg = t()
        print('%s %s - %s' % ('PASS' if ok else 'FAIL', t.__name__, msg), flush=True)
        fail += not ok
    print('ALL', 'OK' if not fail else 'FAILED')
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
