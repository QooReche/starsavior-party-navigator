# -*- coding: utf-8 -*-
"""P4 시험: 사전 계산(tools/build_sim_results.py)의 스키마·관문 순위·수동 델타·결정성(시드)·결과 없음 처리,
수동 정책 규칙(노바 버스트 궁극기만·개인 풀), 서순 변환, 공식 상수 임시 교체 원복, 플래시 포인트 보스 인자 버그.

  python -X utf8 -I tests/p4_test.py            # 전부(약 1~2분, 판 수를 줄인 --quick 로 임시 폴더에만 씀)
  python -X utf8 -I tests/p4_test.py gate       # 이름에 이 글자가 든 시험만

운영 파일(data/sim)은 건드리지 않는다 — 결과는 임시 폴더에만 쓴다."""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_sim_results as bsr  # noqa: E402
import party_reco as pr  # noqa: E402
from battlesim import rules as brules  # noqa: E402
from battlesim.api import simulate  # noqa: E402

STAGE_RUSH = 'rush/매니저 그레고리/매니저 그레고리 Ⅰ'
STAGE_COSMO = 'cosmo/길레/길레 1단계'
_RUNS = {}


def run_once(stage, seed=bsr.DEFAULT_SEED, tag=None):
    """임시 폴더에 --quick 으로 한 스테이지를 계산해 (index, content 문서) 반환(같은 인자는 한 번만)"""
    key = (stage, seed, tag)
    if key in _RUNS:
        return _RUNS[key]
    out = tempfile.mkdtemp(prefix='p4test_')
    try:
        idx = bsr.main(['--stage', stage, '--quick', '--workers', '1', '--seed', str(seed), '--out', out])
        content = stage.split('/', 1)[0]
        with open(os.path.join(out, content + '.json'), encoding='utf-8') as f:
            doc = json.load(f)
    finally:
        shutil.rmtree(out, ignore_errors=True)
    _RUNS[key] = (idx, doc)
    return idx, doc


def stage_rec(doc, stage):
    _, tab, name = stage.split('/', 2)
    return doc['stages']['%s|%s' % (tab, name)]


# ---------------------------------------------------------------- 스키마
def test_schema():
    """index·콘텐츠 파일 필드, 팀 결과(오토·수동) 필드와 값 범위, 파티 2(코스모), 편성 순서 = 화면 4칸"""
    idx, doc = run_once(STAGE_COSMO)
    need_idx = {'schema_version', 'conditions', 'contents', 'policies', 'sens', 'last_run'}
    miss = need_idx - set(idx)
    if miss:
        return False, 'index 빠짐 %s' % miss
    if doc['schema_version'] != bsr.SCHEMA or set(doc) != {'schema_version', 'content', 'stages'}:
        return False, '콘텐츠 파일 머리 %s' % sorted(doc)
    rec = stage_rec(doc, STAGE_COSMO)
    m = rec.get('meta') or {}
    if m.get('sel') != pr.selection_version() or set(m.get('sv', {})) != {'engine', 'foe_js', 'databook', 'rules', 'code'} \
            or m.get('seed') != bsr.DEFAULT_SEED or m.get('runs') != bsr.QUICK_RUNS or m.get('quick') is not True or not m.get('patch'):
        return False, '스테이지 meta 이상 %s' % m
    if len(rec['parties']) != 2:
        return False, '코스모 파티 수 %d' % len(rec['parties'])
    n_auto = n_man = 0
    for k, t in rec['teams'].items():
        if sorted(t['o']) != k.split(',') or len(t['o']) != 4 or (t['L'] is not None and t['L'] not in t['o']):
            return False, '편성 순서/리더 이상 %s' % k
        for mode in ('auto', 'man'):
            r = t.get(mode)
            if r is None:
                continue
            if mode == 'auto':
                n_auto += 1
            else:
                n_man += 1
            if not r['g']:
                continue
            ok = (0 <= r['c'] <= 1 and len(r['ci']) == 2 and r['ci'][0] <= r['c'] <= r['ci'][1] and 0 <= r['w'] <= 1
                  and abs(r['c'] + r['w'] + r['to'] - 1) < 1e-6 and set(r['u']) == set(t['o']) and r['n'] > 0
                  and (r['t'] is None) == (r['nc'] == 0) and 0 <= r['nd'] <= 1)
            if not ok:
                return False, '%s %s 값 이상 %s' % (k, mode, r)
        if 'man' in t and not (t['man'].get('pol') in [list(p) for p in bsr.POLICIES] and 'd' in t['man']):
            return False, '수동 정책/델타 없음 %s' % k
    p1 = rec['parties'][0]
    ok = (len(p1['top']) == bsr.K_TOP and all(k in rec['teams'] for k in p1['rank']) and len(p1['cont']) >= 2
          and any(s['id'] == 'base' for s in p1['sens']) and any('seq' in rec['teams'][k] for k in p1['rank'][:3]))
    return ok and n_auto > 10 and n_man > 0, '팀 %d(오토 %d, 수동 %d), 파티1 상위 %d·보존 %d·확정 %d·민감도 %d' % (
        len(rec['teams']), n_auto, n_man, len(p1['top']), len(p1['keep']), len(p1['cont']), len(p1['sens']))


def test_partial_merge_keeps_stage_meta():
    """--stage 부분 재생성: 새로 계산한 스테이지만 새 실행 정보, 손대지 않은 스테이지는 원래 meta(시드·판 수·규칙 해시) 유지,
    추천 입력 해시가 다른 기존 스테이지는 버림(codex P4 검토 차단 1)"""
    selv = pr.selection_version()
    sv_old = dict(engine='old-engine', foe_js='x', databook='y', rules='OLDRULES', code='z')
    old_a = dict(teams={}, parties=[], meta=bsr.stage_meta(selv, sv_old, 111, bsr.QUICK_RUNS, True))
    stale = dict(teams={}, parties=[], meta=bsr.stage_meta('다른입력', sv_old, 111, bsr.QUICK_RUNS, True))
    prev = dict(schema_version=bsr.SCHEMA, content='rush', stages={'A|a': old_a, 'S|s': stale, 'B|b': dict(old_a)})
    new_b = dict(teams={'k': 1}, parties=[], meta=bsr.stage_meta(selv, dict(sv_old, rules='NEWRULES'), 222, bsr.RUNS, False))
    merged = bsr.merge_stages(prev, {'B|b': new_b}, selv)
    ok1 = (set(merged) == {'A|a', 'B|b'} and merged['A|a']['meta']['sv']['rules'] == 'OLDRULES' and merged['A|a']['meta']['seed'] == 111
           and merged['B|b']['meta']['sv']['rules'] == 'NEWRULES' and merged['B|b']['meta']['seed'] == 222)
    # 실제 도구로: 같은 임시 폴더에 스테이지 A(시드 1) 다음 스테이지 B(시드 2) -> A 의 meta 는 시드 1 그대로
    out = tempfile.mkdtemp(prefix='p4merge_')
    try:
        bsr.main(['--stage', 'cube/커널/커널', '--quick', '--workers', '1', '--seed', '1', '--out', out])
        bsr.main(['--stage', 'cube/인터페이스/인터페이스', '--quick', '--workers', '1', '--seed', '2', '--out', out])
        with open(os.path.join(out, 'cube.json'), encoding='utf-8') as f:
            doc = json.load(f)
        with open(os.path.join(out, 'index.json'), encoding='utf-8') as f:
            idx = json.load(f)
    finally:
        shutil.rmtree(out, ignore_errors=True)
    seeds = {k: v['meta']['seed'] for k, v in doc['stages'].items()}
    ok2 = seeds == {'커널|커널': 1, '인터페이스|인터페이스': 2} and idx['last_run']['seed'] == 2 and idx['last_run']['only'] is True
    tpl = open(os.path.join(ROOT, 'party_template.html'), encoding='utf-8').read()
    ok3 = 'rec.meta.sel!==D.selver' in tpl and 'rec.meta.seed' in tpl
    return ok1 and ok2 and ok3, '병합 %s / 도구 시드 %s / 페이지 스테이지별 검사 %s' % (sorted(merged), seeds, ok3)


# ---------------------------------------------------------------- 관문 순위
def test_gate_order():
    """관문: 클리어 5%p 묶음이 높으면 처치 턴이 느려도 앞, 같은 묶음이면 처치 턴 빠른 쪽, 계산 불가는 맨 뒤 + 실제 결과의 rank 가 이 규칙과 같음"""
    R = lambda c, t, g=True: dict(c=c, t=t, g=g)
    teams = {'a': dict(a=50, auto=R(0.96, 6.0)), 'b': dict(a=60, auto=R(0.90, 3.0)), 'c': dict(a=70, auto=R(0.97, 4.0)),
             'd': dict(a=99, auto=R(1.0, 9.0, g=False)), 'e': dict(a=40, auto=R(0.0, None)), 'f': dict(a=80, auto=R(0.96, 6.0))}
    order = bsr.rank_keys(teams, list(teams))
    want = ['c', 'f', 'a', 'b', 'e', 'd']   # c·f·a 같은 묶음(0.95~): 처치 턴 4 < 6, 6 동률은 근사 점수 80 > 50
    if order != want:
        return False, '합성 순위 %s (기대 %s)' % (order, want)
    _, doc = run_once(STAGE_RUSH)
    rec = stage_rec(doc, STAGE_RUSH)
    p = rec['parties'][0]
    again = bsr.rank_keys(rec['teams'], p['rank'])
    keys = [bsr.gate_key(rec['teams'][k]['auto'], rec['teams'][k]['a']) for k in p['rank']]
    return again == p['rank'] and keys == sorted(keys), '합성 %s · 실제 1~3위 키 %s' % (order, keys[:3])


# ---------------------------------------------------------------- 수동 델타
def test_manual_delta_sign():
    """수동 델타 = 수동 - 오토(클리어 확률·처치 턴), 부호가 실제 차이와 같다"""
    _, doc = run_once(STAGE_RUSH)
    rec = stage_rec(doc, STAGE_RUSH)
    n = bad = 0
    for k, t in rec['teams'].items():
        m, a = t.get('man'), t.get('auto')
        if not (m and a and m.get('g') and a.get('g')):
            continue
        n += 1
        if abs(m['d']['c'] - round(m['c'] - a['c'], 3)) > 1e-9:
            bad += 1
        if m['t'] is not None and a['t'] is not None:
            if abs(m['d']['t'] - round(m['t'] - a['t'], 2)) > 1e-9 or (m['d']['t'] < 0) != (m['t'] < a['t']) and abs(m['t'] - a['t']) > 0.005:
                bad += 1
        elif m['d']['t'] is not None:
            bad += 1
    return n > 0 and bad == 0, '팀 %d, 불일치 %d' % (n, bad)


# ---------------------------------------------------------------- 결정성
def test_determinism_seed():
    """같은 시드 = 스테이지 결과 전부 같음, 다른 시드 = 다름"""
    _, d1 = run_once(STAGE_RUSH)
    _RUNS.pop((STAGE_RUSH, bsr.DEFAULT_SEED, None), None)
    _, d2 = run_once(STAGE_RUSH, tag='again')
    _, d3 = run_once(STAGE_RUSH, seed=bsr.DEFAULT_SEED + 100)
    _RUNS[(STAGE_RUSH, bsr.DEFAULT_SEED, None)] = (None, d1)
    a, b, c = (json.dumps(stage_rec(d, STAGE_RUSH), sort_keys=True) for d in (d1, d2, d3))
    return a == b and a != c, '같은 시드 %s, 다른 시드 %s' % ('같음' if a == b else '다름', '다름' if a != c else '같음')


# ---------------------------------------------------------------- 결과 없음
def test_missing_result():
    """시뮬 실패·미계산은 숫자 없이 사유만(지어내지 않음), 후보 풀 밖 조합은 결과 조회가 비어 있음"""
    team = dict(sim=['a', 'b', 'c', 'd'], o=['c', 'a', 'b', 'd'])
    r = bsr.summarize(None, team, '이벤트 한도 초과: x')
    ok1 = r['g'] is False and 'c' not in r and 't' not in r and r['us'] == ['이벤트 한도 초과: x']
    res, err = bsr.run_sim('cosmo/없는탭/없는 스테이지', dict(sim=['gwen', 'fei', 'professor-m', 'amora'], li=0), 2, 1)
    ok2 = res is None and err
    _, doc = run_once(STAGE_RUSH)
    rec = stage_rec(doc, STAGE_RUSH)
    used = {k for key in rec['teams'] for k in key.split(',')}
    outsider = sorted(x['key'] for x in pr.load()[0] if x['key'] not in used)[:4]
    ok3 = ','.join(sorted(outsider)) not in rec['teams']
    tpl = open(os.path.join(ROOT, 'party_template.html'), encoding='utf-8').read()
    ok4 = '근사 점수만 · 시뮬 없음' in tpl and '시뮬 미계산 스테이지' in tpl and 'rec.meta.sel!==D.selver' in tpl
    return ok1 and ok2 and ok3 and ok4, '실패 요약 %s / 없는 스테이지 오류 %r / 풀 밖 조합 %s 없음 %s / 페이지 문구 %s' % (ok1, (err or '')[:40], outsider, ok3, ok4)


# ---------------------------------------------------------------- 엔진 수동 규칙
def test_manual_burst_rule():
    """수동 노바 버스트: ult_only 면 버스트가 궁극기에서만, any_attack 이면 다른 스킬에도 있을 수 있음, 오토는 버스트 없음"""
    party = {'units': ['gwen', 'fei', 'professor-m', 'amora'], 'leader': 0}
    enc = {'waves': [[dict(name='샌드백', hp=10 ** 12, atk=1, boss=True)]], 'max_turns': 15}   # 오래 버티는 적(노바가 모이도록)

    def bursts(over):
        res = simulate(party, enc, dict(seed=3, n_runs=1, timeline=True, rules_override=over))
        return [e['skill'] for e in res['timeline'] if e.get('nb')]
    ult = bursts(dict(nova_policy='manual', manual_burst='ult_only'))
    anyb = bursts(dict(nova_policy='manual', manual_burst='any_attack'))
    auto = bursts(dict(nova_policy='auto'))
    unit = bursts(dict(nova_policy='manual', manual_burst='any_attack', nova_pool='unit'))
    ok = ult and all(s.startswith('궁극기') for s in ult) and anyb and not auto and unit and unit != anyb
    return bool(ok), '궁극기만 %s / 아무 공격 %s / 오토 %s / 개인 풀 %s' % (ult[:3], anyb[:3], auto, unit[:3])


def test_formula_override_restored():
    """민감도용 공식 상수 교체(COOP_CAP)는 실행 뒤 원래 값으로, 모르는 상수는 거부"""
    before = brules.COOP_CAP
    simulate(['gwen', 'fei', 'professor-m', 'amora'], {'stage': 'cosmo/길레/길레 1단계'}, dict(seed=1, n_runs=1, formula_override={'COOP_CAP': 1.0}))
    try:
        simulate(['gwen', 'fei', 'professor-m', 'amora'], {'stage': 'cosmo/길레/길레 1단계'}, dict(seed=1, n_runs=1, formula_override={'BASE_MULT': 2}))
        rejected = False
    except ValueError:
        rejected = True
    return brules.COOP_CAP == before and rejected, 'COOP_CAP %s -> %s, 모르는 상수 거부 %s' % (before, brules.COOP_CAP, rejected)


def test_seq_from_timeline():
    """서순: 모델 기준 턴 행·화면 칸(편성 순서) 매핑, 적 행동 제외, 협공은 협공한 구원자 칸, 버스트 표시"""
    team = dict(sim=['f0', 'f1', 'b0', 'b1'], o=['b0', 'f0', 'f1', 'b1'])
    tl = [dict(actor='x', side=0, pos=0, skill='기본기', targets=['보스'], turn=0.8, all=False, tgt_side=1, tgt_boss=True),
          dict(actor='y', side=0, pos=3, skill='기본기(추가)', targets=['보스'], turn=0.8, via='coop', all=False, tgt_side=1, tgt_boss=True),
          dict(actor='boss', side=1, pos=0, skill='궁극기', targets=['x'], turn=0.9),
          dict(actor='z', side=0, pos=2, skill='궁극기', targets=['a', 'b'], turn=1.0, nb=True, all=True, tgt_side=1),
          dict(actor='w', side=0, pos=1, skill='특수기', targets=['f0'], turn=1.4, all=False, tgt_side=0),
          dict(actor='x', side=0, pos=0, skill='기본기', targets=['쫄몹'], turn=13.2, all=False, tgt_side=1, tgt_boss=False)]
    sq = bsr.seq_from_timeline(tl, team)
    r1, r2 = sq['rows'][0], sq['rows'][1]
    ok = (len(sq['rows']) == 2 and sq['turns'] == 14 and r1['t'] == 1 and r1['c'][1] == [{'k': 'B', 'tg': '보스'}]
          and r1['c'][3] == [{'k': 'B', 'tg': '보스', 'v': 'coop'}] and r1['c'][0] == [{'k': 'U', 'tg': '전체', 'nb': 1}]
          and r1['nb'] == [[0, 'U']] and r2['t'] == 2 and r2['c'][2] == [{'k': 'S', 'tg': '아군 f0'}])
    return ok, json.dumps(sq, ensure_ascii=False)[:160]


# ---------------------------------------------------------------- 추천 쪽
def test_top_parties_and_flash_point():
    """best_party = top_parties 1위, 플래시 포인트 보스 인자(이전 KeyError 'bosses')가 스테이지 검색으로 동작"""
    lines = []
    pr.recommend('플래시 포인트', '매니저 그레고리', out=lines.append)
    ok1 = any('매니저 그레고리 Ⅰ' in x for x in lines) and any(x.startswith('-- 파티 1') for x in lines)
    st = bsr.stage_obj('cosmo', '길레', '길레 2단계')
    cands, dp = bsr.candidates('cosmo', '길레', st)
    roster, growth, mains, cfg, tags = pr.load()
    top = pr.top_parties(cands, cfg, tags, dp, 10)
    best = pr.best_party(cands, cfg, tags, dp)
    ok2 = bsr.ckey(top[0][0]) == bsr.ckey(best[0]) and all(top[i][1] >= top[i + 1][1] for i in range(len(top) - 1))
    return ok1 and ok2, '플래시 포인트 %s줄 / 상위 1위 %s' % (len(lines), bsr.ckey(best[0]))


TESTS = [test_schema, test_partial_merge_keeps_stage_meta, test_gate_order, test_manual_delta_sign, test_determinism_seed, test_missing_result, test_manual_burst_rule,
         test_formula_override_restored, test_seq_from_timeline, test_top_parties_and_flash_point]


def main():
    sel = sys.argv[1:]
    ok_all = True
    for t in TESTS:
        if sel and not any(x in t.__name__ for x in sel):
            continue
        try:
            ok, msg = t()
        except Exception as ex:   # 시험 자체 오류도 실패로
            import traceback
            traceback.print_exc()
            ok, msg = False, '오류: %r' % (ex,)
        print('%s %s - %s' % ('PASS' if ok else 'FAIL', t.__name__, msg), flush=True)
        ok_all = ok_all and ok
    print('ALL', 'OK' if ok_all else 'FAILED')
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
