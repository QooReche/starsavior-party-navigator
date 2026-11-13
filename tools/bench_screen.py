# -*- coding: utf-8 -*-
"""예선·본선 속도/결과 검증틀 — 실제 화면(index.html, Pyodide 작업자)을 Chromium 으로 돌려 스테이지마다
«예선 순위·팀별 결과·본선 결과·총 판 수·시간·최대 메모리»를 적는다. 속도 개선은 결과를 바꾸면 안 되므로
고치기 전 기록(기준)과 고친 뒤 기록을 --compare 로 맞대 본다.

입력은 공개 표준 육성(내 정보 없음)뿐이다. 계정 자료를 넣지 않는다. 결과 파일은 local/(gitignore) 에 둔다.

  <venv-pw python> -X utf8 tools/bench_screen.py --out local/bench/base.json --workers 1,3
  <venv-pw python> -X utf8 tools/bench_screen.py --out local/bench/new.json --workers 1,3,15 --stages "작전 (일반)|36-36|3"
  python -X utf8 tools/bench_screen.py --compare local/bench/base.json local/bench/new.json

--stages = «콘텐츠 이름|스테이지 검색어|재점화 단계» 를 ; 로 이은 것(생략하면 STAGES). --workers = 예선 작업자 수 목록
(navigator.hardwareConcurrency 를 그 수+1 로, deviceMemory 를 8 로 흉내 낸다). 한 번에 한 스테이지씩만 돈다(무거운 작업 동시 실행 금지).
비교(--compare)는 작업자 수와 무관하게 같은 스테이지의 «예선 순위·1차/2차 결과·본선 결과»가 모두 같은지 보고, 시간·판 수·메모리를 표로 낸다.
"""
import argparse
import ctypes
import json
import os
import sys
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# 쉬움(대부분 클리어) · 경계 · 전원 hard(빠른 계산이 모두 «못 깸») · 재점화 3 — 고른 근거는 --probe 출력
# (빠른 계산 상위 80팀 판정, 11/13 표준 육성: 1-1 = 전부 여유 / 36-36 = 여유 17·빠듯 63 / 41-36 = 빠듯 42·못 깸 38 / 38-36 = 못 깸 78 / 31-36 = 못 깸 79)
STAGES = [
    ('작전 (일반)', '1-1', 0),
    ('작전 (일반)', '36-36', 0),
    ('작전 (일반)', '41-36', 0),
    ('작전 (일반)', '38-36', 0),
    ('작전 (일반)', '31-36', 3),
    ('작전 (일반)', '37-18', 3),
]

INIT_JS = """(() => {
  Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>%d});
  Object.defineProperty(navigator,'deviceMemory',{get:()=>8});
  const W=window.Worker,B={made:0,killed:0,posts:[]};window.__bench=B;
  window.Worker=class extends W{
    constructor(...a){super(...a);B.made++}
    postMessage(m,...r){if(m&&m.type==='run')B.posts.push({n:m.n_runs,teams:(m.teams||[]).length,mode:m.mode,off:(m.teams||[]).map(t=>t.options&&t.options.run_offset||0),t:Date.now()});return super.postMessage(m,...r)}
    terminate(){B.killed++;return super.terminate()}
  };
})()"""

COLLECT_JS = """() => {
  const st=cur[$('stage').value],sc=SIMQ.scr[scrKey(st,1)]||null;
  const pick=r=>r?{clear:r.clear,t60:r.t60??null,prog:r.prog??null,ttk:r.ttk??null,n:r.n}:null;
  const map=o=>Object.fromEntries(Object.entries(o||{}).map(([k,v])=>[k,pick(v)]));
  const rows=LASTQ[1].rows.map(t=>{const r=SIMQ.res[simSig(st,t)];return {key:t.keys.slice().sort().join(','),
    res:r?{clear:r.clear,t60:r.t60??null,prog:r.prog??null,ttk:r.ttk??null,ta:r.ta??null,n:r.n,ci:r.ci,wipe:r.wipe,timeout:r.timeout,u:r.u,man:r.man?{c:r.man.c,t:r.man.t,pol:r.man.pol}:null}:null}});
  const B=window.__bench;
  return {stage:st.tab+'|'+st.name,screen:sc&&{done:sc.done,short:!!sc.short,total:sc.total,pool:sc.pool,order:sc.order,up:sc.up||null,res:map(sc.res),res2:map(sc.res2)},
    rows,shown:document.querySelector('.party[data-party="1"]')?.dataset.team||null,
    workersMade:B.made,workersKilled:B.killed,posts:B.posts.length,
    // 판 수별 요청 시각(시작 뒤 ms): [판 수, 첫 요청, 마지막 요청, 요청 수] — 예선 1차·2차·본선이 언제 시작했는지
    phases:[...new Set(B.posts.map(p=>p.n))].map(n=>{const ps=B.posts.filter(p=>p.n===n);return [n,ps[0].t-B.t0,ps[ps.length-1].t-B.t0,ps.length]}),
    runs:B.posts.reduce((s,p)=>s+p.n*p.teams*(p.mode==='manual'?2:1),0),scrWorkers:typeof scrWorkers==='function'?scrWorkers():null}
}"""


# ---- 브라우저 프로세스 묶음의 메모리(개인 커밋 합계) — psutil 없이 Windows API 로 잰다
def _tree_private_mb(root_pid):
    if os.name != 'nt':
        return 0.0
    from ctypes import wintypes
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    ps = ctypes.WinDLL('psapi', use_last_error=True)

    class PE(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', ctypes.c_long), ('dwFlags', wintypes.DWORD),
                    ('szExeFile', ctypes.c_wchar * 260)]

    class PMC(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t), ('PrivateUsage', ctypes.c_size_t)]

    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k.Process32FirstW.argtypes = k.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PE)]
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    ps.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    snap = k.CreateToolhelp32Snapshot(2, 0)
    procs, e = {}, PE()
    e.dwSize = ctypes.sizeof(PE)
    ok = k.Process32FirstW(snap, ctypes.byref(e))
    while ok:
        procs[e.th32ProcessID] = (e.th32ParentProcessID, e.szExeFile.lower())
        ok = k.Process32NextW(snap, ctypes.byref(e))
    k.CloseHandle(snap)
    kids, todo = set(), [root_pid]
    while todo:
        p = todo.pop()
        for pid, (parent, _) in procs.items():
            if parent == p and pid not in kids:
                kids.add(pid)
                todo.append(pid)
    total = 0
    for pid in kids:
        if not any(x in procs[pid][1] for x in ('chrome', 'headless')):
            continue
        h = k.OpenProcess(0x1000 | 0x0010, False, pid)
        if not h:
            continue
        m = PMC()
        m.cb = ctypes.sizeof(PMC)
        if ps.GetProcessMemoryInfo(h, ctypes.byref(m), m.cb):
            total += m.PrivateUsage
        k.CloseHandle(h)
    return total / 1048576


class MemPeak:
    def __init__(self):
        self.peak, self._stop = 0.0, threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while not self._stop.wait(1.0):
            try:
                self.peak = max(self.peak, _tree_private_mb(os.getpid()))
            except Exception:
                pass

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        self._t.join(timeout=5)


def run_one(browser, base, content, query, rk, workers, mode, timeout):
    import test_page as tp
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.add_init_script(INIT_JS % (workers + 1))
    page.add_init_script('window.__legacyRaid = 1')
    try:
        page.goto(base + '/index.html?auto=0&dev=1')
        page.wait_for_function('() => window._ready')
        if page.evaluate('() => !!MI.info'):
            raise RuntimeError('내 정보가 들어 있음 — 표준 육성 입력만 쓴다')
        tp.settle(page)
        tp.choose(page, content, query)
        page.evaluate("() => { document.getElementById('optbox').open = true }")
        page.select_option('#rk', str(rk))
        if mode == 'manual':
            page.evaluate("() => { const b=document.querySelector('input[name=\"mode\"][value=\"manual\"]'); if(b){b.checked=true;b.dispatchEvent(new Event('change',{bubbles:true}))} }")
        tp.settle(page)
        with MemPeak() as mem:
            t0 = time.time()
            page.evaluate('() => { window.__bench.t0 = Date.now() }')
            page.click('button[data-go]')
            page.wait_for_selector('.party[data-party="1"] .qbox .qrow[data-key]', timeout=timeout)
            tp.wait_sim_done(page, timeout=timeout)
            dt = time.time() - t0
        out = page.evaluate(COLLECT_JS)
        out.update(content=content, query=query, rk=rk, workers=workers, mode=page.evaluate('() => MODE'), seconds=round(dt, 1), peakMB=round(mem.peak),
                   errors=errors, quick=page.evaluate("""() => {const c={};for(const t of (LASTQ[1].all||[]).slice(0,80))c[t.vd]=(c[t.vd]||0)+1;return c}"""))
        return out
    finally:
        page.close()


def strip(r):
    """결과 비교용: 작업자 수·시간과 무관해야 하는 것만"""
    return {'screen': r['screen'], 'rows': r['rows'], 'shown': r['shown']}


def compare(paths):
    sets = [json.load(open(p, encoding='utf-8')) for p in paths]
    by = {}
    for p, s in zip(paths, sets):
        for r in s['results']:
            by.setdefault((r['content'], r['query'], r['rk'], r.get('mode', 'auto')), []).append((os.path.basename(p), r))
    bad = 0
    print('%-34s %-10s %3s %7s %7s %7s %5s %5s  결과' % ('스테이지', '파일', 'W', '초', '판', 'MB', '생성', '종료'))
    for key, rows in by.items():
        # 기준 = 첫 파일의 작업자 1개 기록(후보 순서대로 끝나므로 동률 순서가 정해져 있다). 고치기 전 코드는 작업자가 여럿이면 동률 순위가 끝난 순서에 따라 달라졌다
        ref = strip(min(rows, key=lambda x: (x[0] != os.path.basename(paths[0]), x[1]['workers']))[1])
        for name, r in rows:
            same = strip(r) == ref
            why = ''
            if not same:
                bad += 1
                a, b = ref, strip(r)
                why = ' / 다른 곳: ' + ', '.join(k for k in ('shown', 'rows') if a[k] != b[k])
                if a['screen'] != b['screen']:
                    why += ', screen(' + ', '.join(k for k in (a['screen'] or {}) if (a['screen'] or {}).get(k) != (b['screen'] or {}).get(k)) + ')'
            print('%-34s %-10s %3d %7.1f %7d %7d %5d %5d  %s%s' % ('%s %s rk%d %s' % (key[0], key[1], key[2], key[3]), name[:10], r['workers'], r['seconds'], r['runs'],
                                                                r['peakMB'], r['workersMade'], r['workersKilled'], '같음' if same else '다름', why))
    print('결과 다른 줄 %d' % bad)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--workers', default='1')
    ap.add_argument('--stages')
    ap.add_argument('--mode', default='auto', choices=['auto', 'manual'])
    ap.add_argument('--timeout', type=int, default=3600)
    ap.add_argument('--compare', nargs='+')
    ap.add_argument('--root', default=ROOT, help='화면을 내줄 저장소 폴더(기준 기록은 고치기 전 사본 폴더를 준다)')
    a = ap.parse_args()
    if a.compare:
        return compare(a.compare)
    if not a.out:
        ap.error('--out 필요')
    stages = [(c, q, int(r)) for c, q, r in (s.split('|') for s in a.stages.split(';'))] if a.stages else STAGES
    root = os.path.abspath(a.root)
    sys.path.insert(0, root)
    sys.path.insert(0, os.path.join(root, 'tests', 'e2e'))
    import test_page as tp       # 시험 서버는 이 모듈이 있는 저장소를 내준다
    assert os.path.normcase(tp.ROOT) == os.path.normcase(root), tp.ROOT
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    results = []
    if os.path.exists(a.out):       # 이어 돌리기: 이미 있는 (스테이지, 작업자 수)는 건너뛴다
        results = json.load(open(a.out, encoding='utf-8'))['results']
    have = {(r['content'], r['query'], r['rk'], r['workers'], r.get('mode', 'auto')) for r in results}
    with tp.test_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for w in [int(x) for x in a.workers.split(',')]:
                for c, q, rk in stages:
                    if (c, q, rk, w, a.mode) in have:
                        continue
                    r = run_one(browser, base, c, q, rk, w, a.mode, a.timeout * 1000)
                    results.append(r)
                    sc = r['screen'] or {}
                    print('%s %s rk%d W%d: %.1f초 %d판 %dMB 후보 %s 빠른계산 %s 1위 %s 단계 %s' % (c, q, rk, w, r['seconds'], r['runs'], r['peakMB'], sc.get('total'), r['quick'],
                                                                                    [(x['res'] or {}).get('clear') for x in r['rows']], r.get('phases')), flush=True)
                    tmp = a.out + '.tmp'
                    with open(tmp, 'w', encoding='utf-8') as f:
                        json.dump({'results': results}, f, ensure_ascii=False)
                    os.replace(tmp, a.out)
        finally:
            browser.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
