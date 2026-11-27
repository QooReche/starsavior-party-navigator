"""Native transport, browser timer and analysis for the production-JS measurement driver."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))


def save_json(file, value):
    temp = file.with_suffix(file.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding='utf-8')
    temp.replace(file)


def memory_guard():
    class Status(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (k, ctypes.c_ulonglong) for k in ('physical', 'available', 'page', 'available_page', 'virtual', 'available_virtual', 'extended')]
    s = Status()
    s.length = ctypes.sizeof(s)
    if os.name == 'nt':
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)):
            raise RuntimeError('Memory check failed')
        if s.available < 6 * 1024**3:
            raise RuntimeError('Need at least 6 GiB available memory')


def worker():
    from battlesim.web import run_auto, AutoBatch
    for line in sys.stdin:
        m = json.loads(line)
        try:
            batch = AutoBatch(m['stage'], m['n_runs'], m['seed']) if len(m['teams']) > 1 else None
            for t in m['teams']:
                opts = {**m.get('options', {}), **t.get('options', {})}
                if batch:
                    r = batch.run(t['party'], opts)
                else:
                    r = run_auto(m['stage'], t['party'], m['n_runs'], m['seed'], opts)
                print(json.dumps(dict(type='team', key=t['key'], result=json.loads(r))), flush=True)
            print(json.dumps(dict(type='done')), flush=True)
        except Exception as e:
            print(json.dumps(dict(type='error', msg=repr(e))), flush=True)


def browser(a):
    from stage_reco_check import serve
    from bench_screen import MemPeak
    from playwright.sync_api import sync_playwright
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', r'E:\AI_mk2\_env\pw-browsers')
    rows = json.loads(Path(a.collect).read_text(encoding='utf-8'))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    scratch = out.resolve() / 'tmp'
    scratch.mkdir(parents=True, exist_ok=True)
    os.environ['TEMP'] = os.environ['TMP'] = str(scratch)
    server = serve()
    base = 'http://127.0.0.1:%d/' % server.server_port
    try:
        with sync_playwright() as p:
            for row in rows:
                if a.ids and row['id'] not in a.ids.split(','):
                    continue
                check_output(row, out)
                for seed in map(int, a.seeds.split(',')):
                    for method in a.methods.split(','):
                        file = out / f"{row['id']}_{seed}_{method}_browser.json"
                        if file.exists():
                            continue
                        if any(t['vd'] != 'hard' for t in row['qt']):
                            save_json(file, dict(id=row['id'], method=method, seed=seed, private=row['private'],
                                                excluded='quick_not_all_hard', backend='browser', measured=False))
                            continue
                        memory_guard()
                        br = p.chromium.launch()
                        try:
                            page = br.new_page()
                            page.add_init_script("Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>9}); Object.defineProperty(navigator,'deviceMemory',{get:()=>8});")
                            page.add_init_script("document.addEventListener('DOMContentLoaded',()=>{simAutoOn=()=>false;},{once:true})")
                            if row['private']:
                                info = Path(a.myinfo).read_text(encoding='utf-8')
                                page.add_init_script('(s=>localStorage.setItem("pn.myinfo",s))(%s)' % json.dumps(info))
                            page.goto(base + 'index.html?auto=0&pm=reco')
                            page.wait_for_function('window._ready && QK.d', timeout=120000)
                            if row['private']:
                                page.wait_for_function('MI.info && MI.growth && !MI.pending', timeout=120000)
                            else:
                                page.evaluate('RECO.standard=true')
                            ci = page.evaluate('k=>contents.findIndex(c=>c.key===k)', row['c']['key'])
                            page.select_option('#content', str(ci))
                            page.wait_for_timeout(500)
                            si = page.evaluate('([t,n])=>cur.findIndex(s=>s.tab===t&&s.name===n)', [row['st']['tab'], row['st']['name']])
                            assert si >= 0
                            page.evaluate("()=>{const q=$('q');q.value='';q.dispatchEvent(new Event('input'));}")
                            page.wait_for_timeout(300)
                            page.select_option('#stage', str(si))
                            page.select_option('#rk', str(row['options'].get('rekindle', 0)), force=True)
                            page.wait_for_timeout(500)
                            page.evaluate("directNavigate('direct')")
                            page.wait_for_function('!!DIRECT.draft')
                            page.add_script_tag(url=base + 'tools/learned_reco_measure.js')
                            page.add_script_tag(url=base + 'tools/learned_reco_browser.js')
                            with MemPeak() as peak:
                                page.evaluate("""({row,method,seed})=>{
                                  window.measurePhase='start';
                                  window.measureDone=false;
                                  runLearnedRecoBrowser(row,method,seed,(p,n)=>window.measurePhase=p+':'+n)
                                    .then(r=>window.measureResult=r).catch(e=>window.measureError=e.stack).finally(()=>window.measureDone=true);
                                }""", dict(row=row, method=method, seed=seed))
                                while not page.evaluate('window.measureDone'):
                                    page.wait_for_timeout(10000)
                                    print(row['id'], seed, method, page.evaluate('window.measurePhase'), flush=True)
                                error = page.evaluate('window.measureError')
                                if error:
                                    raise RuntimeError(error)
                                result = page.evaluate('window.measureResult')
                            result.update(backend='browser', workers=8, peakMB=peak.peak)
                            save_json(file, result)
                        finally:
                            br.close()
    finally:
        server.shutdown()


def check_output(row, out):
    private = Path('E:/AI_mk2/_private/role-private/learned_reco').resolve()
    if row.get('private') and not out.resolve().is_relative_to(private):
        raise ValueError('Account results must stay in the designated private directory')


def native(a):
    import psutil
    out = Path(a.out)
    rows = json.loads(Path(a.collect).read_text(encoding='utf-8'))
    for row in rows:
        if a.ids and row['id'] not in a.ids.split(','):
            continue
        check_output(row, out)
        for seed in a.seeds.split(','):
            for method in a.methods.split(','):
                file = out / f"{row['id']}_{seed}_{method}_native.json"
                if file.exists():
                    continue
                memory_guard()
                proc = subprocess.Popen(['node', str(ROOT / 'tools/learned_reco_measure_cli.js'), a.collect, a.out, a.python, method, seed, row['id']], cwd=ROOT)
                peak = 0
                while proc.poll() is None:
                    try:
                        parent = psutil.Process(proc.pid)
                        processes = [parent] + parent.children(recursive=True)
                        size = 0
                        for p in processes:
                            try:
                                m = p.memory_info()
                                size += getattr(m, 'private', m.rss)
                            except psutil.NoSuchProcess:
                                pass
                        peak = max(peak, size / 1048576)
                    except psutil.NoSuchProcess:
                        pass
                    time.sleep(.5)
                if proc.returncode:
                    raise RuntimeError('Node measurement failed')
                result = json.loads(file.read_text(encoding='utf-8'))
                result['peakMB'] = peak
                save_json(file, result)


def compare(a):
    """Inference only; never selects a winner from the independent evaluation."""
    import numpy as np
    out = Path(a.out)
    data = [json.loads(p.read_text(encoding='utf-8')) for p in out.glob('*_native.json')]
    for r in data:
        check_output(r, out)
    collected = json.loads(Path(a.collect or out / 'collect.json').read_text(encoding='utf-8'))
    pools = {r['id']: set(r['pool']) for r in collected}
    rows = []
    for r in data:
        if r.get('excluded'):
            rows.append({k: r.get(k) for k in ('id', 'method', 'seed', 'excluded')})
            continue
        f = next(x for x in data if x['id'] == r['id'] and x['seed'] == r['seed'] and x['method'] == 'F')
        if r['fallback']:
            learning_games = sum(p['runs'] for p in r['phases'] if p['label'] in ('sample', 'selected', 'audit'))
            assert r['screen'] == f['screen'], 'Fallback screening differs from F'
            assert r['winner']['party'] == f['winner']['party'], 'Fallback winner differs from F'
            assert r['winner']['brk'] == f['winner']['brk'], 'Fallback break differs from F'
            assert r['result']['raw'] == f['result']['raw'], 'Fallback evaluation differs from F'
            assert r['searchGames'] == learning_games + f['searchGames'], 'Fallback cost must include learning plus F'
        raw, ref = json.loads(r['result']['raw']), json.loads(f['result']['raw'])
        assert len(raw) == len(ref) == 400
        if r['options'].get('star_turns'):
            metric = 't60_pp'
            values = lambda xs: [float(x[0] == 'clear' and x[2] <= r['options']['star_turns']) for x in xs]
        elif any(x[0] == 'clear' for x in raw + ref):
            metric = 'clear_pp'
            values = lambda xs: [float(x[0] == 'clear') for x in xs]
        else:
            metric = 'progress_relative_pct'
            values = lambda xs: [x[3] for x in xs]
        x, y = np.asarray(values(raw)), np.asarray(values(ref))
        rng = np.random.default_rng(20261127 + r['seed'])
        # Independent resampling is deliberately conservative despite shared combat seed.
        bx = x[rng.integers(0, 400, (10000, 400))].mean(axis=1)
        by = y[rng.integers(0, 400, (10000, 400))].mean(axis=1)
        if metric == 'progress_relative_pct':
            delta = (x.mean() / y.mean() - 1) * 100 if y.mean() else None
            diffs = (bx / by - 1) * 100 if y.mean() else np.full(10000, np.nan)
        else:
            delta = (x.mean() - y.mean()) * 100
            diffs = (bx - by) * 100
        ci = np.quantile(diffs, [.025, .975]).tolist() if np.isfinite(diffs).all() else [None, None]
        if r['method'] == 'F':
            delta, ci = 0, [0, 0]
        browser_file = out / f"{r['id']}_{r['seed']}_{r['method']}_browser.json"
        fb_file = out / f"{r['id']}_{r['seed']}_F_browser.json"
        br = json.loads(browser_file.read_text(encoding='utf-8')) if browser_file.exists() else None
        fb = json.loads(fb_file.read_text(encoding='utf-8')) if fb_file.exists() else None
        if br:
            assert r['winner']['party'] == br['winner']['party'], 'Native/browser winner mismatch'
            assert r['winner']['brk'] == br['winner']['brk'], 'Native/browser break mismatch'
            assert r['searchGames'] == br['searchGames'], 'Native/browser search path mismatch'
            assert r['evaluationGames'] == br['evaluationGames'], 'Native/browser independent sample count mismatch'
            assert r['screen'] == br['screen'], 'Native/browser screening order mismatch'
            assert r['result']['progs'] == br['result']['progs'], 'Native/browser independent result mismatch'
            assert json.loads(r['result']['raw']) == json.loads(br['result']['raw']), 'Native/browser raw result mismatch'
        near_zero = max(x[3] for x in raw + ref) < .01 or ci[0] is None
        verdict = 'excluded_near_zero' if near_zero else 'b' if ci[0] > 0 else 'a' if ci[0] > -1 and br and fb and br['seconds'] < fb['seconds'] else 'insufficient'
        if r['method'] == 'F' and not near_zero:
            verdict = 'reference'
        diagnostic = max([dict(team=r['winner'], result=r['result']), *r['diagnostics']],
                         key=lambda d: (d['result'].get('t60') if d['result'].get('t60') is not None else d['result']['clear'],
                                        d['result']['clear'], d['result']['prog']))
        row = dict(id=r['id'], method=r['method'], seed=r['seed'], private=r['private'], stage=r['stage'],
                   winner=r['winner']['keys'], party=r['winner']['party'], brk=r['winner']['brk'], metric=metric, delta=delta, ci=ci,
                   verdict=verdict, fallback=r['fallback'], games=r['searchGames'], evaluation_games=r['evaluationGames'], native_seconds=r['seconds'],
                   browser_seconds=br and br['seconds'], native_peakMB=r['peakMB'], browser_peakMB=br and br['peakMB'],
                   outside_pool=[k for k in r['winner']['keys'] if k not in pools[r['id']]],
                   diagnostic_best=diagnostic['result'], diagnostic_keys=diagnostic['team']['keys'])
        rows.append(row)
    save_json(out / 'summary.json', rows)
    labels = {s['s']['key']: s['s']['name'] for c in collected for s in c['cands']}
    labels['gille'] = '구원자 길레'
    lines = ['# 일반 추천 학습 선별 측정 결과', '',
             '시간은 탐색 전체(학습·복귀·예선·본선·자리 비교) 기준임. 판 수는 탐색/독립을 분리했으며 독립은 고정 1위 400판과 나머지 최대 4팀 진단을 합한 값임. 독립 평가는 탐색 시간에서 제외함. 메모리는 독립 평가를 포함한 실행의 최대 private commit임.', '',
             '| 대상 | 시드 | 방식 | 고정 1위 (엔진 순서 / 리더 / 브레이크) | 주지표 차 [95%] | 복귀 | 탐색/독립 판 수 | 네이티브/브라우저 초 | 최대 MB (N/B) | 판정 |',
             '|---|---:|---|---|---|---|---:|---:|---:|---|']
    for r in sorted(rows, key=lambda r:(r['id'], r['seed'], 'FAC'.index(r['method']))):
        if r.get('excluded'):
            lines.append(f"| {r['id']} | {r['seed']} | {r['method']} | — | — | — | — | — | — | 제외: {r['excluded']} |")
            continue
        units = r['party']['units']
        team = ' · '.join(labels.get(u['key'], u['key']) + '(' + u['key'] + ')' for u in units)
        leader = r['party']['leader']
        team += ' / ' + (labels.get(units[leader]['key'], units[leader]['key']) if leader is not None else '리더 없음')
        team += ' / 브레이크: ' + (r['brk']['name'] if r['brk'] else '없음')
        unit = '%' if r['metric'] == 'progress_relative_pct' else '%p'
        diff = '정의 불가' if r['delta'] is None or r['ci'][0] is None else f"{r['delta']:+.2f} [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}]{unit}"
        bt = '미측정' if r['browser_seconds'] is None else f"{r['browser_seconds']:.1f}"
        bm = '—' if r['browser_peakMB'] is None else f"{r['browser_peakMB']:.0f}"
        lines.append(f"| {r['stage']} | {r['seed']} | {r['method']} | {team} | {diff} | {'예' if r['fallback'] else '아니오'} | {r['games']}/{r['evaluation_games']} | {r['native_seconds']:.1f}/{bt} | {r['native_peakMB']:.0f}/{bm} | {r['verdict']} |")
    lines += ['', '## 상위 최대 5팀 독립 평가 진단', '',
              '아래 최댓값은 재선택·채택 판정에 사용하지 않았음. 각 방식이 실제로 본선에서 보여 준 팀만 포함함.', '',
              '| 대상 | 시드 | 방식 | 진단 최고 팀 | 클리어율 | 평균 진행도 |',
              '|---|---:|---|---|---:|---:|']
    for r in sorted(rows, key=lambda r:(r['id'], r['seed'], 'FAC'.index(r['method']))):
        if r.get('excluded'):
            continue
        d = r['diagnostic_best']
        team = ' · '.join(labels.get(k, k) for k in r['diagnostic_keys'])
        lines.append(f"| {r['stage']} | {r['seed']} | {r['method']} | {team} | {100*d['clear']:.2f}% | {d['prog']:.6f} |")
    (out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    # Account summary stays private too. Public documentation uses only relative differences/verdicts.
    for r in rows:
        print(r['id'], r['seed'], r['method'], r.get('verdict', r.get('excluded')), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['worker', 'native', 'browser', 'compare'])
    ap.add_argument('--collect')
    ap.add_argument('--out')
    ap.add_argument('--methods', default='F,A,C')
    ap.add_argument('--seeds', default='1,2,3')
    ap.add_argument('--ids', default='')
    ap.add_argument('--python', default=sys.executable, help='전투 작업자 Python (Pyodide 대조에는 CPython 3.12 32-bit)')
    ap.add_argument('--myinfo', default='E:/AI_mk2/_private/role-private/op4212/myinfo_1121.json')
    a = ap.parse_args()
    if a.cmd == 'worker':
        worker()
        return
    if a.cmd == 'compare':
        compare(a)
        return
    memory_guard()
    if a.cmd == 'browser':
        browser(a)
    else:
        native(a)


if __name__ == '__main__':
    main()
