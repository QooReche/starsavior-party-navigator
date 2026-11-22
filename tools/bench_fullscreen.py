# -*- coding: utf-8 -*-
"""후보 전체 훑기(항상 켬) — 브라우저 실측 시간과 독립 재평가 품질.
끔 비교(스위치 recommendation.fullScreen 끔/켬)는 커밋 3e3a694 이전의 이 도구로 잰다(11/22 스위치 삭제).

browser: 실제 화면(index.html, Pyodide 작업자)을 Chromium 으로 열어 내 정보(비공개 파일)를 넣고, 스테이지마다
  «추천 편성 보기»부터 예선·본선이 다 끝날 때까지의 시간을 잰다(매번 새 브라우저 문맥 = 엔진 준비 포함, 같은 조건).
  작업자 수는 이 PC 의 기본값(scrWorkers). 판 수별 요청 수·시작 시각, 훑기 여부, 화면 1안의 시뮬 명세(simParty·브레이크)를 남긴다.
  한 번에 한 스테이지씩만 돈다(무거운 작업 동시 실행 금지). 이미 잰 스테이지는 건너뜀(이어 돌리기).
eval: 화면 1안을 네이티브 엔진(battlesim.web.run_auto = 작업자와 같은 함수)으로 시드 20261122·400판 독립 재평가.
  평균 진행도·클리어율과 부트스트랩 95% 구간. 1판 훑기로 고른 팀의 소표본 선택 편향은 이 독립 재평가로 판정한다.
report: 스테이지별 훑기 발동·시간·판 수·1안 진행도 표.

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
    full:!!(sc&&sc.full),fullN:sc?.fullN??null,scanned:sc?.full?.length??null,poolN:sc?.pool?.length??null,
    short:!!sc?.short,candidates:LASTQ[1].all.length,vd,byN,runs:B.posts.reduce((s,p)=>s+p.n*p.teams,0),
    top:spec(top),rows:rows.map(spec),err:SIMQ.err||'',prof:window.__prof||null,rt:B.rt,rtN:B.rtN,teamsPosted:B.posts.reduce((s,p)=>s+p.teams,0)}
}"""


def browser(myinfo, out, only, timeout, profile=False, chunk=None):
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', r'E:\AI_mk2\pw-browsers')
    sys.path.insert(0, str(ROOT / 'tests' / 'e2e'))
    import test_page as tp
    from playwright.sync_api import sync_playwright
    info = Path(myinfo).read_text(encoding='utf-8')
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'browser.json'
    res = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    have = {r['name'] for r in res if r.get('mode', 'on') == 'on'}
    with tp.test_server() as base, sync_playwright() as p:
        br = p.chromium.launch()
        try:
            for name, ck, tab, sname in STAGES:
                if only and name not in only:
                    continue
                for mode in ('on',):
                    if name in have:
                        continue
                    ctx = br.new_context(viewport={'width': 1280, 'height': 900})
                    page = ctx.new_page()
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.add_init_script("(s=>{for(const [k,v] of Object.entries(s))localStorage.setItem(k,v)})(%s)" % json.dumps({'pn.myinfo': info}))
                    page.add_init_script(INIT_JS)
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
                    if profile:
                        page.evaluate(PROF_JS)
                    if chunk:       # 묶음 크기 고정(1 = 묶기 전 배차, 단계별 측정용)
                        page.evaluate("n=>{SearchExecutor.chunkSize=()=>n}", chunk)
                    t0 = time.time()
                    page.evaluate('() => { window.__bench.t0 = Date.now() }')
                    page.click('button[data-go]')
                    page.wait_for_selector('.party[data-party="1"] .qbox .qrow[data-key]', state='visible', timeout=timeout)
                    tp.wait_sim_done(page, timeout=timeout)
                    dt = time.time() - t0
                    r = page.evaluate(COLLECT_JS)
                    r.update(name=name, mode=mode, seconds=round(dt, 1), errors=errors, chunk=chunk)
                    ctx.close()
                    res.append(r)
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


def boot(a, stat, n=2000, seed=7):
    rnd = random.Random(seed)
    d = sorted(stat([a[rnd.randrange(len(a))] for _ in a]) for _ in range(n))
    return d[int(n * .025)], d[int(n * .975)]


def mean(x):
    return sum(x) / len(x)


def latest(data):
    """스테이지별 마지막 켬 측정(예전 파일의 'off' 줄은 무시)."""
    by = {}
    for r in data:
        if r.get('mode', 'on') == 'on':
            by[r['name']] = r
    return by


def evaluate(out, runs, workers):
    by = latest(json.loads((out / 'browser.json').read_text(encoding='utf-8')))
    rep = []
    with ProcessPoolExecutor(workers) as ex:
        for name, r in by.items():
            t = r['top']
            opt = dict(r['options'], break_skill={'name': t['bname'], 'level': t['blv']} if t['bname'] else None)
            ev = dict(keys=t['keys'], **run_team((r['stageStr'], t['party'], runs, SEED, opt)))
            a = ev['progs']
            ca = [1.0 if p >= 1 else 0.0 for p in a]
            row = dict(name=name, on=ev, prog=mean(a), prog_ci=boot(a, mean), clear=mean(ca), clear_ci=boot(ca, mean))
            rep.append(row)
            print(name, '진행 %.3f [%.3f, %.3f]' % (row['prog'], *row['prog_ci']), '클리어 %.3f [%.3f, %.3f]' % (row['clear'], *row['clear_ci']), flush=True)
    (out / 'eval.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')


def report(out):
    by = latest(json.loads((out / 'browser.json').read_text(encoding='utf-8')))
    ev = {r['name']: r for r in json.loads((out / 'eval.json').read_text(encoding='utf-8'))} if (out / 'eval.json').exists() else {}
    print('|스테이지|훑기 발동|작업자|시간(초)|판 수|1안 평균 진행도 [95%]|1안 클리어율 [95%]|')
    print('|---|---|---|---|---|---|---|')
    for name, b in by.items():
        e = ev.get(name)
        pr = ('%.3f [%.3f, %.3f]' % (e['prog'], *e['prog_ci'])) if e and 'prog' in e else '–'
        cl = ('%.1f%% [%.1f, %.1f]' % (100 * e['clear'], 100 * e['clear_ci'][0], 100 * e['clear_ci'][1])) if e and 'clear' in e else '–'
        print('|%s|%s|%d|%.0f|%d|%s|%s|' % (name, '예' if b['full'] else '아니오', b['workers'], b['seconds'], b['runs'], pr, cl))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['browser', 'eval', 'report'])
    ap.add_argument('--myinfo')
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--only', help='스테이지 이름을 , 로')
    ap.add_argument('--timeout', type=int, default=7200)
    ap.add_argument('--runs', type=int, default=400)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--profile', action='store_true', help='메인 스레드 함수 누적 시간을 결과(prof)에 남김')
    ap.add_argument('--chunk', type=int, help='훑기·예선 묶음 크기 고정(1 = 묶기 전 배차)')
    a = ap.parse_args()
    out = Path(a.out)
    if a.cmd == 'browser':
        browser(a.myinfo, out, set(a.only.split(',')) if a.only else None, a.timeout * 1000, a.profile, a.chunk)
    elif a.cmd == 'eval':
        evaluate(out, a.runs, a.workers)
    else:
        report(out)


if __name__ == '__main__':
    main()
