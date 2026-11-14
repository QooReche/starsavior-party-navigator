# -*- coding: utf-8 -*-
"""브라우저 시뮬 진입점(battlesim/web.py)·엔진 규칙 시험 — 옛 사전 계산 시험(tests/p4_test.py)에서 엔진 쪽만 옮기고 새 진입점을 더함.

사용: python -X utf8 -I tests/web_test.py
화면은 오토 기준만 쓴다(2026-11-14 수동 모드 제거) — 수동 진입점(run_manual·서순 변환)이 없음을 test_no_manual_entry 가 본다."""
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
    return G.party_spec(q, order, 'fei', order, g, st), st


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
    # 클리어율·처치 시간 중앙값은 다른 난수 표본에서도 같을 수 있다. 구원자별 피해/사망도 함께 비교.
    different = (a['clear'], a['ttk'], a['u']) != (c['clear'], c['ttk'], c['u'])
    ok = abs(a['power'] - want) / want < 0.002 and a == b and different
    return ok, '전투력 %.0f (가정 %.0f) / 같은 시드 같음 %s / 다른 시드 피해·사망 포함 결과 다름 %s' % (a['power'], want, a == b, different)


def test_no_manual_entry():
    """화면 진입점에 수동이 없다: run_manual·서순 변환·수동 정책 목록이 없고, 작업자도 run_auto 만 가져온다. 엔진의 수동 정책 규칙은 그대로(test_manual_burst_rule)."""
    gone = [n for n in ('run_manual', 'seq_from_timeline', 'POLICIES', 'CARD') if hasattr(web, n)]
    worker = open(os.path.join(ROOT, 'sim_worker.js'), encoding='utf-8').read()
    p, _ = party()
    a = json.loads(web.run_auto(STAGE, p, 4, 1, OPT))
    ok = not gone and 'run_manual' not in worker and 'manual' not in worker and 'man' not in a
    return ok, '남은 수동 진입점 %s / 작업자에 수동 %s / 오토 결과에 man %s' % (gone, 'manual' in worker, 'man' in a)


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
    simulate(['gwen', 'fei', 'professor-m', 'amora'], {'stage': 'cosmo/길레/길레 1단계'}, dict(seed=1, n_runs=1, formula_override={'COOP_CAP': 0.30}))
    try:
        simulate(['gwen', 'fei', 'professor-m', 'amora'], {'stage': 'cosmo/길레/길레 1단계'}, dict(seed=1, n_runs=1, formula_override={'BASE_MULT': 2}))
        rejected = False
    except ValueError:
        rejected = True
    return brules.COOP_CAP == before and rejected, 'COOP_CAP %s -> %s, 모르는 상수 거부 %s' % (before, brules.COOP_CAP, rejected)


def test_manifest_complete():
    """sim/manifest.json 의 파일만 빈 폴더에 복사해 run_auto(표준 육성)가 돌아가는가 — 브라우저(Pyodide)와 같은 조건.
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
                "from battlesim.web import run_auto;"
                "a=json.loads(run_auto(sys.argv[2],json.loads(sys.argv[3]),5,1,sys.argv[4]));print(a['clear'])")
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


def test_rekindle():
    """재점화 메타·콘텐츠 경계·전투력 배율 분리. 실제 합산 경로는 rekindle_1112_test."""
    p, _ = party()
    o = dict(build='standard', rules_override={'power_penalty': 'model'}, n_runs=3, seed=1)
    op0 = simulate(p, {'stage': 'op/아가논 시가지/SECTOR 36-36'}, o)['party']
    op3 = simulate(p, {'stage': 'op/아가논 시가지/SECTOR 36-36'}, dict(o, rekindle=3))['party']
    cz = simulate(p, {'stage': 'cosmo/길레/길레 1단계'}, dict(o, rekindle=3))['party']
    oh0 = simulate(p, {'stage': 'oph/플로라/SECTOR 13-10'}, o)['party']
    oh1 = simulate(p, {'stage': 'oph/플로라/SECTOR 13-10'}, dict(o, rekindle=1))['party']   # 작전(어려움)도 재점화 대상(2026-11-08 영상 판: 13-10 에서 1단계가 붙어 있었음, 사용자 확인)
    ok = (op3['rekindle'] == 3 and op3['penalty'] == op0['penalty']
          and cz['rekindle'] == 0 and op0['rekindle'] == 0
          and oh1['rekindle'] == 1 and oh0['rekindle'] == 0 and oh1['penalty'] == oh0['penalty'])
    try:
        simulate(p, {'stage': 'op/아가논 시가지/SECTOR 36-36'}, dict(o, rekindle=9))
        bad = False
    except ValueError:
        bad = True
    return ok and bad, '0단계 %s / 3단계 %s / 코스모 %s / 잘못된 단계 거부 %s' % (op0['penalty'], op3['penalty'], cz['rekindle'], bad)


def test_stats_final_and_luna_reaction():
    """stats_final: 화면 최종값이면 상시 패시브 % 를 다시 곱하지 않는다(전투력이 화면 값 그대로의 공식과 같음).
    화이트 펄 루나 「썸머 템테이션♡」: 다른 아군이 치명타 피격되면 반응 발동(2026-10-21)"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import ingame_check as I
    from battlesim.starsavior.build import unit_power
    ov = dict(I.REAL['white-pearl-luna'])
    p_final = simulate({'units': [dict(key='white-pearl-luna', stats_override=ov, stats_final=True)]},
                       {'stage': 'op/아가논 시가지/SECTOR 36-36'}, dict(build='standard', n_runs=1, seed=1))['party']['power']
    p_raw = simulate({'units': [dict(key='white-pearl-luna', stats_override=ov)]},
                     {'stage': 'op/아가논 시가지/SECTOR 36-36'}, dict(build='standard', n_runs=1, seed=1))['party']['power']
    want = unit_power(dict(ov))
    import gen_quick_calib as G
    from battlesim import quick
    q, pen = quick.load(ROOT)
    ck, sk, order, lead, pw, rk = I.SAMPLES['37-2'][:6]          # 실측 37-2 와 같은 파티(긴 잡몹전 — 치명 피격이 충분히 나옴)
    spec = G.party_spec(q, order, lead, list(order), pw / q['st'][ck][sk]['bp'], q['st'][ck][sk])
    fired = 0
    for seed in range(1, 41):     # 드문 사건(치명 피격 반응) — wave_carry=client 뒤 1~12 에선 0회라 범위를 넓힘
        r = simulate(spec, {'stage': 'op/모나스티르 광장/SECTOR 37-2'}, dict(G.SIMOPT, n_runs=1, seed=seed, timeline=True))
        fired += sum(1 for e in r['timeline'] if e.get('via') == 'reaction' and e.get('actor') == '루나')
        if fired:
            break
    from battlesim.api import _norm_party
    from battlesim.starsavior.data import get_db
    part = _norm_party({'units': [dict(key='white-pearl-luna', stats_override={'atk': 12314}, stats_final=True)]}, get_db(), 'fixed', 'standard')[0][0]
    partial_ok = part.passive['atkp'] == 0 and part.passive['hpp'] > 0      # 공격력만 넣으면 생명력 % 는 그대로(codex 리뷰)
    ok = abs(p_final - want) < 1 and p_raw > p_final and fired > 0 and partial_ok
    return ok, '최종값 전투력 %.0f(공식 %.0f) / 재증폭 %.0f / 루나 반응 %d회 / 부분 입력 %s' % (p_final, want, p_raw, fired, partial_ok)


TESTS = [test_slot_order, test_run_auto_power_and_determinism, test_no_manual_entry, test_manual_burst_rule,
         test_formula_override_restored, test_manifest_complete, test_pyodide_local, test_rekindle, test_stats_final_and_luna_reaction]


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
