# -*- coding: utf-8 -*-
"""브라우저 시뮬 진입점(battlesim/web.py)·엔진 규칙 시험 — 옛 사전 계산 시험(tests/p4_test.py)에서 엔진 쪽만 옮기고 새 진입점을 더함.

사용: python -X utf8 -I tests/web_test.py
일부러 깨뜨려 보기: web.CARD 를 [0, 1, 2, 3] 으로 바꾸면 test_seq_from_timeline 이 실패해야 한다."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from battlesim import rules as brules  # noqa: E402
from battlesim import web  # noqa: E402
from battlesim.api import simulate  # noqa: E402

STAGE = 'op/NOA 상업지구/SECTOR 1-3'
OPT = json.dumps({'build': 'standard', 'rules_override': {'power_penalty': 'model'}})


def party(g=1.0):
    """화면 simParty 와 같은 변환으로 만든 파티(gen_quick_calib.party_spec)"""
    import gen_quick_calib as G
    from battlesim import quick
    q, pen = quick.load(ROOT)
    st = q['st']['op']['NOA 상업지구|SECTOR 1-3']
    order = ['emily', 'fei', 'professor-m', 'wedding-carmen']     # 화면 카드 순서(후열1, 전열1, 전열2, 후열2)
    return G.party_spec(q, pen, order, 'fei', order, g, st), st


def test_seq_from_timeline():
    """서순: 모델 기준 턴 행·화면 카드 칸 매핑(시뮬 칸 0,1,2,3 -> 카드 1,2,0,3), 적 행동 제외, 협공은 협공한 구원자 칸, 버스트 표시"""
    tl = [dict(actor='x', side=0, pos=0, skill='기본기', targets=['보스'], turn=0.8, all=False, tgt_side=1, tgt_boss=True),
          dict(actor='y', side=0, pos=3, skill='기본기(추가)', targets=['보스'], turn=0.8, via='coop', all=False, tgt_side=1, tgt_boss=True),
          dict(actor='boss', side=1, pos=0, skill='궁극기', targets=['x'], turn=0.9),
          dict(actor='z', side=0, pos=2, skill='궁극기', targets=['a', 'b'], turn=1.0, nb=True, all=True, tgt_side=1),
          dict(actor='w', side=0, pos=1, skill='특수기', targets=['f0'], turn=1.4, all=False, tgt_side=0),
          dict(actor='x', side=0, pos=0, skill='기본기', targets=['쫄몹'], turn=13.2, all=False, tgt_side=1, tgt_boss=False)]
    sq = web.seq_from_timeline(tl)
    r1, r2 = sq['rows'][0], sq['rows'][1]
    ok = (len(sq['rows']) == 2 and sq['turns'] == 14 and r1['t'] == 1 and r1['c'][1] == [{'k': 'B', 'tg': '보스'}]
          and r1['c'][3] == [{'k': 'B', 'tg': '보스', 'v': 'coop'}] and r1['c'][0] == [{'k': 'U', 'tg': '전체', 'nb': 1}]
          and r1['nb'] == [[0, 'U']] and r2['t'] == 2 and r2['c'][2] == [{'k': 'S', 'tg': '아군 f0'}])
    return ok, json.dumps(sq, ensure_ascii=False)[:160]


def test_slot_order():
    """화면 카드 순서 -> 시뮬 칸: 전열(카드 2·3번째)이 시뮬 0·1번 칸, 리더 번호도 시뮬 칸 기준(2026-10-20 버그: 카드 순서를 그대로 넘겼음)"""
    p, _ = party()
    keys = [u['key'] for u in p['units']]
    return keys == ['fei', 'professor-m', 'emily', 'wedding-carmen'] and p['leader'] == 0, '%s 리더 %s' % (keys, p['leader'])


def test_run_auto_power_and_determinism():
    """run_auto: 엔진이 스탯으로 계산한 파티 전투력 = 가정 전투력(권장 × 0.8), 같은 시드 = 같은 결과, 다른 시드 = 다른 판"""
    p, st = party(0.8)
    a = json.loads(web.run_auto(STAGE, p, 30, 1, OPT))
    b = json.loads(web.run_auto(STAGE, p, 30, 1, OPT))
    c = json.loads(web.run_auto(STAGE, p, 30, 2, OPT))
    want = st['bp'] * 0.8
    ok = abs(a['power'] - want) / want < 0.002 and a == b and (a['clear'], a['ttk']) != (c['clear'], c['ttk'])
    return ok, '전투력 %.0f (가정 %.0f) / 같은 시드 같음 %s / 다른 시드 %s vs %s' % (a['power'], want, a == b, (a['clear'], a['ttk']), (c['clear'], c['ttk']))


def test_run_manual_shape():
    """run_manual: 정책 4종 중 하나, 서순 행·카드 4칸, 대표 판 종류"""
    p, _ = party()
    m = json.loads(web.run_manual(STAGE, p, 30, 1, OPT))
    sq = m['seq']
    ok = tuple(m['pol']) in web.POLICIES and sq['rows'] and all(len(r['c']) == 4 for r in sq['rows']) and sq['kind'] in ('clear', 'wipe', 'timeout')
    return bool(ok), '정책 %s, 클리어 %s, 서순 %d행, %s' % (m['pol'], m['c'], len(sq['rows']), sq['kind'])


def test_manual_burst_rule():
    """수동 노바 버스트: ult_only 면 버스트가 궁극기에서만, any_attack 이면 다른 스킬에도 있을 수 있음, 오토는 버스트 없음"""
    pt = {'units': ['gwen', 'fei', 'professor-m', 'amora'], 'leader': 0}
    enc = {'waves': [[dict(name='샌드백', hp=10 ** 12, atk=1, boss=True)]], 'max_turns': 15}

    def bursts(over):
        res = simulate(pt, enc, dict(seed=3, n_runs=1, timeline=True, rules_override=over))
        return [e['skill'] for e in res['timeline'] if e.get('nb')]
    ult = bursts(dict(nova_policy='manual', manual_burst='ult_only'))
    anyb = bursts(dict(nova_policy='manual', manual_burst='any_attack'))
    auto = bursts(dict(nova_policy='auto'))
    ok = ult and all(s.startswith('궁극기') for s in ult) and anyb and not auto
    return bool(ok), '궁극기만 %s / 아무 공격 %s / 오토 %s' % (ult[:3], anyb[:3], auto)


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


def test_manifest_complete():
    """sim/manifest.json 의 파일만 빈 폴더에 복사해 run_auto(표준 육성)·run_manual 이 돌아가는가 — 브라우저(Pyodide)와 같은 조건.
    (2026-10-20: 표준 육성이 읽는 builds.json·가이드 파일이 목록에서 빠질 뻔함)"""
    import shutil
    import subprocess
    import tempfile
    man = json.load(open(os.path.join(ROOT, 'sim', 'manifest.json'), encoding='utf-8'))
    tmp = tempfile.mkdtemp(prefix='simpack_')
    try:
        for f in man['files']:
            dst = os.path.join(tmp, *f.split('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(ROOT, *f.split('/')), dst)
        p, _ = party()
        code = ("import os,sys,json;os.environ['PN_SRC']=sys.argv[1];sys.path.insert(0,sys.argv[1]);"
                "from battlesim.web import run_auto,run_manual;"
                "a=json.loads(run_auto(sys.argv[2],json.loads(sys.argv[3]),5,1,sys.argv[4]));"
                "m=json.loads(run_manual(sys.argv[2],json.loads(sys.argv[3]),6,1,sys.argv[4]));print(a['clear'],m['c'])")
        r = subprocess.run([sys.executable, '-X', 'utf8', '-I', '-c', code, tmp, STAGE, json.dumps(p), OPT],
                           capture_output=True, text=True, encoding='utf-8', cwd=tmp)
        ok = r.returncode == 0
        return ok, ('파일 %d개만으로 실행 %s' % (len(man['files']), r.stdout.strip())) if ok else r.stderr.strip()[-300:]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_pyodide_local():
    """브라우저 엔진(Pyodide)은 lib/pyodide 에서 받고(외부 CDN 금지), 파일은 공식 패키지 해시와 같다(lib/pyodide/SHA256SUMS)"""
    import hashlib
    d = os.path.join(ROOT, 'lib', 'pyodide')
    bad = []
    n = 0
    for line in open(os.path.join(d, 'SHA256SUMS'), encoding='utf-8'):
        h, name = line.split()
        name = name.lstrip('*')
        n += 1
        if hashlib.sha256(open(os.path.join(d, name), 'rb').read()).hexdigest() != h:
            bad.append(name)
    w = open(os.path.join(ROOT, 'sim_worker.js'), encoding='utf-8').read()
    ext = 'https://' in w or 'http://' in w
    return n == 5 and not bad and not ext, '파일 %d개, 해시 다름 %s, 작업자에 바깥 주소 %s' % (n, bad, ext)


TESTS = [test_seq_from_timeline, test_slot_order, test_run_auto_power_and_determinism, test_run_manual_shape, test_manual_burst_rule,
         test_formula_override_restored, test_manifest_complete, test_pyodide_local]


def main():
    ok_all = True
    for t in TESTS:
        try:
            ok, msg = t()
        except Exception as ex:
            ok, msg = False, '오류: %r' % (ex,)
        print('%s %s - %s' % ('PASS' if ok else 'FAIL', t.__name__, msg), flush=True)
        ok_all = ok_all and ok
    print('ALL', 'OK' if ok_all else 'FAILED')
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
