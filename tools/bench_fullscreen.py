# -*- coding: utf-8 -*-
"""후보 전체 훑기(CFG.recommendation.fullScreen) 켬/끔 — 브라우저 실측 시간과 독립 재평가 품질.

browser: 실제 화면(index.html, Pyodide 작업자)을 Chromium 으로 열어 내 정보(비공개 파일)를 넣고, 스테이지마다
  스위치 끔/켬으로 «추천 편성 보기»부터 예선·본선이 다 끝날 때까지의 시간을 잰다(매번 새 브라우저 문맥 = 엔진 준비 포함, 같은 조건).
  작업자 수는 이 PC 의 기본값(scrWorkers). --browser-workers N 이면 저사양 흉내로 N개로 강제한다
  (navigator.hardwareConcurrency 를 N+1, deviceMemory 를 8 로 덮어 scrWorkers() = N — 공통 실행기는 페이지 로드 때 scrWorkers 함수를
  capacity 로 잡아 두므로 window.scrWorkers 만 바꿔서는 작업자 수가 안 바뀜. 로드 뒤 window.scrWorkers 도 N 으로 덮고 scrWorkers() = N 을 확인).
  --stop-after S 이면 켬 모드에서 훑기 시작 S초 뒤 «지금까지 결과로 보기»를 누르고, 누른 뒤 결과(안내 줄)·끝까지 걸린 시간을 잰다(모드 이름 stop). 판 수별 요청 수·시작 시각, 훑기 여부, 화면 1안의 시뮬 명세(simParty·브레이크)를 남긴다.
  한 번에 한 스테이지·한 모드씩만 돈다(무거운 작업 동시 실행 금지). 이미 잰 (스테이지, 모드)는 건너뜀(이어 돌리기).
eval: 화면 1안(끔·켬)을 네이티브 엔진(battlesim.web.run_auto = 작업자와 같은 함수)으로 시드 20261122·400판 독립 재평가.
  평균 진행도·클리어율과 켬−끔 차의 부트스트랩 95% 구간. 1판 훑기로 고른 팀의 소표본 선택 편향은 이 독립 재평가로 판정한다.
report: 공개용 비율 표(시간 배수·개선 폭 %)만 출력.

계정 수치(원값)는 --out(기본 E:/AI_mk2/role-private/casebook_myinfo/site_reco/fullscreen)에만 쓴다.

  set PLAYWRIGHT_BROWSERS_PATH=E:\\AI_mk2\\pw-browsers
  E:/AI_mk2/venv-pw/Scripts/python.exe -X utf8 tools/bench_fullscreen.py browser --myinfo PATH
  python -X utf8 -I tools/bench_fullscreen.py eval --workers 8
  python -X utf8 -I tools/bench_fullscreen.py report
"""
import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = Path('E:/AI_mk2/role-private/casebook_myinfo/site_reco/fullscreen')
SEED = 20261122
# (이름, 콘텐츠 key, 탭(None = 아무 탭), 스테이지 이름) — 어려운 3곳(docs/casebook_search_check.md) + 쉬운 2곳
STAGES = [
    ('회랑 580', 'clo', '성간 회랑', 'FLOOR 580'),
    ('회랑 590', 'clo', '성간 회랑', 'FLOOR 590'),
    ('작전 44-6', 'op', '얼어붙은 바위 산', 'SECTOR 44-6'),
    ('작전 1-1', 'op', None, 'SECTOR 1-1'),
    ('작전 36-36', 'op', None, 'SECTOR 36-36'),
]

INIT_JS = """(() => {
  const W=window.Worker,B={posts:[]};window.__bench=B;
  B.rt=0;B.rtN=0;
  window.Worker=class extends W{constructor(...a){super(...a);this.addEventListener('message',e=>{if(e.data&&e.data.type==='done'&&this.__t){B.rt+=Date.now()-this.__t;B.rtN++;this.__t=0}})}
    postMessage(m,...r){if(m&&m.type==='run'){B.posts.push({n:m.n_runs,teams:(m.teams||[]).length,t:Date.now()});this.__t=Date.now()}return super.postMessage(m,...r)}};
})()"""

# 메인 스레드 계측(--profile): 전역 함수를 감싸 누적 ms·호출 수를 잰다. 작업자 왕복(보냄→done)과 메인 지연(setTimeout 0 지연 합)도 잰다.
PROF_JS = """() => {
  const P=window.__prof={fn:{},lag:0,lagN:0,rt:0,rtN:0};
  for(const name of ['scrOrder','scrFullRank','simProgressSync','simProgress','recoGwenShow','scrDone']){const f=window[name];if(typeof f!=='function')continue;
    window[name]=function(...a){const t=performance.now();try{return f.apply(this,a)}finally{const o=P.fn[name]||(P.fn[name]={ms:0,n:0});o.ms+=performance.now()-t;o.n++}}}
  let last=performance.now();setInterval(()=>{const t=performance.now(),d=t-last-50;if(d>0){P.lag+=d;P.lagN++}last=t},50);
}"""

# --browser-workers: 페이지 스크립트보다 먼저 navigator 값을 덮음(scrWorkerCount = min(코어−1, 8, 메모리 예산))
WORKERS_JS = "Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>%d,configurable:true});Object.defineProperty(navigator,'deviceMemory',{get:()=>8,configurable:true});"
# --stop-after: 훑기 진행 중인가 — 진행 문구(SIMQ.msg «후보 전체 훑는 중»)와 «지금까지 결과로 보기» 단추로 감지(상태 객체 키에 기대지 않음)
SCAN_JS = "()=>String(SIMQ.msg||'').includes('후보 전체 훑는 중')&&!!document.querySelector('button[data-scrstop]')"
STOP_WAIT = 600
# 멈춘 뒤 결과가 보임 = 진행 화면이 닫히고 1파티 결과 줄이 있음(«중간에 멈춰서 …» 안내 scrNote 유무는 STOP_STATE_JS 로 기록)
STOP_SHOWN_JS = "()=>!document.querySelector('[data-k=\"progress\"]')&&!!document.querySelector('.party[data-party=\"1\"] .qbox .qrow[data-key]')"
STOP_STATE_JS = """()=>{const ss=document.querySelector('.party[data-party="1"] [data-k="simstate"]');
  return {busy:SIMQ.busy,simstate:ss?.dataset?.state||null,done:SIMQ.busy==null&&ss?.dataset?.state==='done',note:document.querySelector('[data-k="scr-short"]')?.textContent||'',err:SIMQ.err||''}}"""
SCAN_STATE_JS = """()=>{const sc=Object.values(SIMQ.scr||{}).find(x=>x&&x.full)||null;
  return {scanning:String(SIMQ.msg||'').includes('후보 전체 훑는 중')&&!!document.querySelector('button[data-scrstop]'),msg:SIMQ.msg||'',
    scanned:Object.keys(sc?.res0||{}).length,all:sc?.full?.length??null}}"""
SCAN_DEBUG_JS = """()=>({msg:SIMQ.msg||'',busy:SIMQ.busy,screening:!!SIMQ.screening,full:!!CFG.recommendation.fullScreen,workers:scrWorkers(),
  scr:Object.entries(SIMQ.scr||{}).map(([k,x])=>({k:String(k).slice(0,40),full:x.full?x.full.length:null,round:x.round,done:!!x.done})),
  stopBtn:!!document.querySelector('button[data-scrstop]'),progress:!!document.querySelector('[data-k="progress"]')})"""

COLLECT_JS = """() => {
  const c=contents[$('content').value],st=cur[$('stage').value],sc=SIMQ.scr[scrKey(st,1)]||null,B=window.__bench;
  const shown=document.querySelector('.party[data-party="1"]')?.dataset.team||null,rows=LASTQ[1].rows;
  const ck=t=>t.keys.slice().sort().join(',');
  const spec=t=>{const r=SIMQ.res[simSig(st,t)],b=teamBreak(t);return {keys:t.keys,party:simParty(t),bname:b?.name||null,blv:b?brkLv(b.name):null,
    res:r?{clear:r.clear,prog:r.prog??null,n:r.n}:null}};
  const top=rows.find(t=>ck(t)===shown)||rows[0];
  const vd={};for(const t of LASTQ[1].all)vd[t.vd]=(vd[t.vd]||0)+1;
  const byN={};for(const p of B.posts){const o=byN[p.n]||(byN[p.n]={posts:0,first:p.t-B.t0,last:0});o.posts++;o.last=p.t-B.t0}
  return {stage:st.tab+'|'+st.name,stageStr:c.key+'/'+st.tab+'/'+st.name,options:simOpt(c.key),workers:scrWorkers(),
    fullFlag:!!CFG.recommendation.fullScreen,full:!!(sc&&sc.full),fullN:sc?.fullN??null,scanned:sc?.full?.length??null,poolN:sc?.pool?.length??null,
    short:!!sc?.short,candidates:LASTQ[1].all.length,vd,byN,runs:B.posts.reduce((s,p)=>s+p.n*p.teams,0),
    top:spec(top),rows:rows.map(spec),err:SIMQ.err||'',prof:window.__prof||null,rt:B.rt,rtN:B.rtN,teamsPosted:B.posts.reduce((s,p)=>s+p.teams,0)}
}"""


def browser(myinfo, out, only, modes, timeout, profile=False, chunk=None, nworkers=None, stop_after=None):
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', r'E:\AI_mk2\pw-browsers')
    sys.path.insert(0, str(ROOT / 'tests' / 'e2e'))
    if stop_after is not None:
        modes = ['stop']
    import test_page as tp
    from playwright.sync_api import sync_playwright
    info = Path(myinfo).read_text(encoding='utf-8')
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'browser.json'
    res = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    have = {(r['name'], r['mode']) for r in res}
    with tp.test_server() as base, sync_playwright() as p:
        br = p.chromium.launch()
        try:
            for name, ck, tab, sname in STAGES:
                if only and name not in only:
                    continue
                for mode in modes:
                    if (name, mode) in have:
                        continue
                    ctx = br.new_context(viewport={'width': 1280, 'height': 900})
                    page = ctx.new_page()
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.add_init_script("(s=>{for(const [k,v] of Object.entries(s))localStorage.setItem(k,v)})(%s)" % json.dumps({'pn.myinfo': info}))
                    page.add_init_script(INIT_JS)
                    if nworkers:
                        page.add_init_script(WORKERS_JS % (nworkers + 1))
                    page.goto(base + '/index.html?auto=0&pm=reco')
                    page.wait_for_function("() => window._ready && MI.info && MI.growth && !MI.pending", timeout=180000)
                    assert page.evaluate('miMode()'), '내 정보 모드가 아님'
                    ci = page.evaluate("k=>contents.findIndex(c=>c.key===k)", ck)
                    page.select_option('#content', value=str(ci))
                    tp.settle(page)
                    si = page.evaluate("([t,n])=>cur.findIndex(s=>(!t||s.tab===t)&&s.name===n)", [tab, sname])
                    assert si >= 0, (name, tab, sname)
                    page.evaluate("()=>{const q=document.querySelector('#q');if(q&&q.value){q.value='';q.dispatchEvent(new Event('input'))}}")
                    tp.settle(page)
                    page.select_option('#stage', value=str(si))
                    page.dispatch_event('#stage', 'change')
                    tp.settle(page)
                    assert page.evaluate("()=>cur[$('stage').value].name") == sname
                    if nworkers:
                        page.evaluate("n=>{window.scrWorkers=()=>n}", nworkers)
                        assert page.evaluate('scrWorkerCount({cores:navigator.hardwareConcurrency,memGB:navigator.deviceMemory})') == nworkers, '작업자 수 강제 실패'
                    page.evaluate("on=>{CFG.recommendation.fullScreen=on}", mode in ('on', 'stop'))
                    if profile:
                        page.evaluate(PROF_JS)
                    if chunk:       # 묶음 크기 고정(1 = 묶기 전 배차, 단계별 측정용)
                        page.evaluate("n=>{SearchExecutor.chunkSize=()=>n}", chunk)
                    t0 = time.time()
                    page.evaluate('() => { window.__bench.t0 = Date.now() }')
                    page.click('button[data-go]')
                    page.wait_for_selector('.party[data-party="1"] .qbox .qrow[data-key]', state='visible', timeout=timeout)
                    stop = None
                    if mode == 'stop':
                        try:
                            page.wait_for_function(SCAN_JS, timeout=STOP_WAIT * 1000)
                        except Exception:     # 훑기 시작을 못 봄 — 기다리지 않고 상태만 남김
                            dbg = page.evaluate(SCAN_DEBUG_JS)
                            print('  훑기 시작 감지 실패:', dbg, flush=True)
                            ctx.close()
                            res.append(dict(name=name, mode=mode, errors=errors, forced_workers=nworkers, stop=dict(scan_seen=False, debug=dbg)))
                            path.with_suffix('.tmp').write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
                            os.replace(path.with_suffix('.tmp'), path)
                            continue
                        ts = time.time()
                        page.wait_for_timeout(int(stop_after * 1000))
                        st0 = page.evaluate(SCAN_STATE_JS)
                        assert st0['scanning'], '훑기가 이미 끝났음 — --stop-after 를 줄일 것'
                        tc = time.time()
                        page.click('button[data-scrstop]')
                        # 멈춘 뒤에는 화면 1~9안 전부가 결과를 갖지 않을 수 있어 «계산 완료»(SIM_DONE_JS)가 안 올 수 있음 —
                        #  진행 화면이 닫히고 결과·안내 줄이 보일 때까지를 «결과가 나온 시간»으로 잼(그 뒤 쉬는 상태는 최대 STOP_WAIT 초, 넘으면 기록만)
                        try:
                            page.wait_for_function(STOP_SHOWN_JS, timeout=STOP_WAIT * 1000)
                            tn = time.time()
                        except Exception:
                            tn = None
                        try:
                            page.wait_for_function("()=>SIMQ.busy==null&&!document.querySelector('[data-k=\"progress\"]')", timeout=STOP_WAIT * 1000)
                            idle = round(time.time() - tc, 1)
                        except Exception:
                            idle = None
                        stop = dict(scan_start=round(ts - t0, 1), click=round(tc - t0, 1), scanned_at_click=st0['scanned'], scan_all=st0['all'],
                                    to_result=tn and round(tn - tc, 1), to_idle=idle, state=page.evaluate(STOP_STATE_JS))
                        if not stop['state']['done']:
                            ctx.close()
                            res.append(dict(name=name, mode=mode, seconds=round(time.time() - t0, 1), errors=errors, forced_workers=nworkers, stop=stop))
                            print('  stop:', stop, flush=True)
                            path.with_suffix('.tmp').write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
                            os.replace(path.with_suffix('.tmp'), path)
                            continue
                    else:
                        tp.wait_sim_done(page, timeout=timeout)
                    dt = time.time() - t0
                    r = page.evaluate(COLLECT_JS)
                    r.update(name=name, mode=mode, seconds=round(dt, 1), errors=errors, chunk=chunk, forced_workers=nworkers, stop=stop)
                    ctx.close()
                    res.append(r)
                    if stop:
                        print('  stop:', stop, flush=True)
                    print('%s %s: %.1f초 작업자 %d 훑기 %s(%s팀→%s) 판 %d 1안 진행 %s' % (name, mode, dt, r['workers'], r['full'], r['scanned'], r['fullN'], r['runs'],
                                                                         r['top']['res'] and round(r['top']['res']['prog'] or 0, 3)), flush=True)
                    tmp = path.with_suffix('.tmp')
                    tmp.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
                    os.replace(tmp, path)
        finally:
            br.close()


def run_team(task):
    from battlesim.web import run_auto
    stage, party, n, seed, opts = task
    r = json.loads(run_auto(stage, party, n, seed, opts))
    return {k: r.get(k) for k in ('prog', 'clear', 'n', 'progs')}


def boot(a, b, stat, n=2000, seed=7):
    rnd = random.Random(seed)
    d = sorted(stat([a[rnd.randrange(len(a))] for _ in a]) - stat([b[rnd.randrange(len(b))] for _ in b]) for _ in range(n))
    return d[int(n * .025)], d[int(n * .975)]


def mean(x):
    return sum(x) / len(x)


def evaluate(out, runs, workers):
    data = json.loads((out / 'browser.json').read_text(encoding='utf-8'))
    by = {}
    for r in data:
        by.setdefault(r['name'], {})[r['mode']] = r
    rep = []
    with ProcessPoolExecutor(workers) as ex:
        for name, m in by.items():
            if not ('off' in m and 'on' in m):
                continue
            ev = {}
            for mode in ('off', 'on'):
                r, t = m[mode], m[mode]['top']
                opt = dict(r['options'], break_skill={'name': t['bname'], 'level': t['blv']} if t['bname'] else None)
                ev[mode] = dict(keys=t['keys'], **run_team((r['stageStr'], t['party'], runs, SEED, opt)))
            # 같은 팀이면 차이 0(다시 돌리지 않음과 같음)
            same = sorted(ev['on']['keys']) == sorted(ev['off']['keys'])
            a, b = ev['on']['progs'], ev['off']['progs']
            ca, cb = [1.0 if p >= 1 else 0.0 for p in a], [1.0 if p >= 1 else 0.0 for p in b]
            row = dict(name=name, same=same, off=ev['off'], on=ev['on'],
                       prog_diff=mean(a) - mean(b), prog_ci=boot(a, b, mean), prog_rel=(mean(a) - mean(b)) / mean(b) if mean(b) else None,
                       clear_diff=mean(ca) - mean(cb), clear_ci=boot(ca, cb, mean))
            rep.append(row)
            print(name, '같은 팀' if same else '다른 팀', '진행 %+.3f [%+.3f, %+.3f]' % (row['prog_diff'], *row['prog_ci']),
                  '(%+.1f%%)' % (100 * row['prog_rel']) if row['prog_rel'] is not None else '', '클리어 %+.3f [%+.3f, %+.3f]' % (row['clear_diff'], *row['clear_ci']), flush=True)
    (out / 'eval.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')


def report(out):
    data = json.loads((out / 'browser.json').read_text(encoding='utf-8'))
    ev = {r['name']: r for r in json.loads((out / 'eval.json').read_text(encoding='utf-8'))} if (out / 'eval.json').exists() else {}
    by = {}
    for r in data:
        by.setdefault(r['name'], {})[r['mode']] = r
    print('|스테이지|훑기 발동|작업자|시간 끔→켬(초)|배수|판 수 배수|1안 같음|평균 진행도 차(끔 대비 %) [95%]|클리어율 차 [95%]|')
    print('|---|---|---|---|---|---|---|---|---|')
    for name, m in by.items():
        if not ('off' in m and 'on' in m):
            continue
        a, b, e = m['off'], m['on'], ev.get(name)
        base = e and e['off']['prog']
        pr = ('%+.1f%% [%+.1f, %+.1f]' % (100 * e['prog_rel'], 100 * e['prog_ci'][0] / base, 100 * e['prog_ci'][1] / base)) if e and base else '–'
        cl = ('%+.1f%%p [%+.1f, %+.1f]' % (100 * e['clear_diff'], 100 * e['clear_ci'][0], 100 * e['clear_ci'][1])) if e else '–'
        print('|%s|%s|%d|%.0f→%.0f|×%.2f|×%.2f|%s|%s|%s|' % (name, '예' if b['full'] else '아니오', b['workers'], a['seconds'], b['seconds'], b['seconds'] / a['seconds'],
                                                     b['runs'] / a['runs'], ('예' if e['same'] else '아니오') if e else '–', pr, cl))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['browser', 'eval', 'report'])
    ap.add_argument('--myinfo')
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--only', help='스테이지 이름을 , 로')
    ap.add_argument('--modes', default='off,on')
    ap.add_argument('--timeout', type=int, default=7200)
    ap.add_argument('--runs', type=int, default=400)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--profile', action='store_true', help='메인 스레드 함수 누적 시간을 결과(prof)에 남김')
    ap.add_argument('--chunk', type=int, help='훑기·예선 묶음 크기 고정(1 = 묶기 전 배차)')
    ap.add_argument('--browser-workers', type=int, help='브라우저 작업자 수 강제(저사양 흉내, 예: 2)')
    ap.add_argument('--stop-after', type=float, help='켬 모드 훑기 시작 이 초 뒤 «지금까지 결과로 보기»(모드 stop 으로 기록)')
    a = ap.parse_args()
    out = Path(a.out)
    if a.cmd == 'browser':
        browser(a.myinfo, out, set(a.only.split(',')) if a.only else None, a.modes.split(','), a.timeout * 1000, a.profile, a.chunk, a.browser_workers, a.stop_after)
    elif a.cmd == 'eval':
        evaluate(out, a.runs, a.workers)
    else:
        report(out)


if __name__ == '__main__':
    main()
