# -*- coding: utf-8 -*-
"""웹 페이지(index.html) Playwright + Chromium 시험.

준비: docs/PORTING.md 7절의 PowerShell 가상환경·PLAYWRIGHT_BROWSERS_PATH 안내 참조하기.
index.html·data/quick.json·sim/manifest.json을 생성한 뒤 해당 가상환경의 Python으로 실행하기.
실행: python -X utf8 tests/e2e/test_page.py [--shots 폴더] [이름 일부 ...]

127.0.0.1의 포트를 직접 소유하는 서버를 띄우고 브라우저 종료 뒤 닫음. 시험·자식 프로세스는 IDLE로 실행함.
스크린샷은 --shots를 권장하며, 생략하면 임시 디렉터리를 사용함. 필터 0건은 실패함.
"""
import datetime as _dt
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import traceback
import json
import os
import random
import socket
import sys
import tempfile
import time
import threading
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
if os.path.isdir(r"E:\AI_mk2\pw-browsers"):
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", r"E:\AI_mk2\pw-browsers")


from tools.runtime import low_priority


class TestHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can let two servers bind the same port. Own it until close.
    allow_reuse_address = False
    request_queue_size = 128

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class TestHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass  # Browser cancellation / page close during a download.


@contextmanager
def test_server():
    # Bind once, without the free-port probe / child startup race. Avoid Chromium's blocked ports.
    for _ in range(100):
        try:
            srv = TestHTTPServer(("127.0.0.1", random.SystemRandom().randint(20000, 60000)),
                                 partial(TestHandler, directory=ROOT))
            break
        except OSError as ex:
            if ex.errno not in (13, 98, 10013, 10048):
                raise
    else:
        raise RuntimeError("시험 서버 포트를 확보하지 못했음")
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % srv.server_port
    try:
        with urllib.request.urlopen(urllib.request.Request(base + "/index.html", method="HEAD"), timeout=10) as response:
            assert response.status == 200
        yield base
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive(), "시험 서버 종료 실패"


class Ctx:
    def __init__(self, base, shots):
        self.base, self.shots = base, shots
        self.errors = []
        self.requests = {}
        self.network = []


def attach(page, ctx):
    page.on("console", lambda m: ctx.errors.append("console: %s [%s]" % (m.text, m.location)) if m.type == "error" else None)
    page.on("pageerror", lambda e: ctx.errors.append("pageerror: %s" % e))
    # Context events include worker requests; page-only listeners miss engine downloads.
    def finished(request):
        ctx.requests.pop(request, None)

    def failed(request):
        ctx.network.append("%s %s (%s): %s" % (request.method, request.url, request.resource_type, request.failure))
        finished(request)

    page.context.on("request", lambda r: ctx.requests.update({r: "%s %s (%s)" % (r.method, r.url, r.resource_type)}))
    page.context.on("requestfinished", finished)
    page.context.on("requestfailed", failed)


def settle(page):
    """디바운스(150ms)가 끝날 때까지"""
    page.wait_for_timeout(450)


def choose(page, content, query):
    labels = page.eval_on_selector_all("#content option", "o => o.map(x => x.textContent)")
    page.select_option("#content", label=next(l for l in labels if l == content or l.startswith(content + "(")))
    settle(page)
    # 모바일 검색은 접힌 필터 안에 있다. 실제 펼치기 동작 후 입력한다.
    folded = not page.locator("#q").is_visible()
    if folded:
        page.click("#filters > summary")
    page.fill("#q", query)
    settle(page)
    page.select_option("#stage", index=0)
    page.dispatch_event("#stage", "change")
    settle(page)
    if folded:
        page.click("#filters > summary")


FIXTURES = os.path.join(ROOT, "tests", "fixtures")
SYNTH = os.path.join(FIXTURES, "myinfo_synthetic.json")         # 8명(가상 계정)
FULL = os.path.join(FIXTURES, "myinfo_full_roster.json")         # 페이지 로스터 57명 전원(가상 값). 로스터가 늘면 다시 만들 것
# 새 탭의 첫 문서에서만 localStorage 를 채운다(sessionStorage 표지) — 새로고침·같은 탭 이동 때 화면이 쓴 값을 덮지 않게
SEED_JS = """(s => { try { if (sessionStorage.getItem('__pn_seed')) return; sessionStorage.setItem('__pn_seed', '1');
  for (const [k, v] of Object.entries(s)) localStorage.setItem(k, v) } catch (e) {} })(%s)"""
SIM_DONE_JS = """ps => !document.querySelector('[data-k="progress"]') && ps.every(p =>
  /시뮬 완료/.test((document.querySelector('.party[data-party="' + p + '"] [data-k="simstate"]') || {}).textContent || ''))"""


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed(page, info=None, simauto="0", excl=None, extra=None):
    """화면이 읽는 저장값(pn.*)을 첫 로드 전에 넣는다. simauto "0" = 「자동 확인 끄기」(내 정보 모드는 기본 자동 시뮬)"""
    s = dict(extra or {})
    if info:
        s["pn.myinfo"] = json.dumps(load_json(info), ensure_ascii=False)
    if simauto is not None:
        s["pn.simauto"] = simauto
    if excl is not None:
        s["pn.excl"] = json.dumps(excl)
    page.add_init_script(SEED_JS % json.dumps(s, ensure_ascii=False))


def wait_myinfo(page, timeout=60000):
    page.wait_for_function("() => window._ready && MI.info && MI.growth && !MI.pending", timeout=timeout)


def wait_sim_done(page, parties=(1,), timeout=600000):
    """예선(1파티)·본선이 모두 끝나 진행 화면이 사라지고 결과의 시뮬 줄이 「시뮬 완료」"""
    page.wait_for_function(SIM_DONE_JS, arg=list(parties), timeout=timeout)


def open_page(browser, ctx, query="", viewport=None, info=FULL, simauto="0", excl=None, setup=None, wait=True, raid_ui=False):
    """내 정보(기본: 로스터 전원 가상 계정)를 넣고 연다. 추천은 내 정보가 있어야만 계산한다.
    ?auto=1 = 버튼 없이 바로 계산(버튼 흐름은 test_press_to_compute). simauto "0" 이면 결과를 바로 보이고(판정 「시뮬 전」),
    시뮬은 시험이 「시뮬로 확인」을 누를 때만 돈다."""
    page = browser.new_page(viewport=viewport or {"width": 1280, "height": 900})
    attach(page, ctx)
    seed(page, info, simauto, excl)
    if not raid_ui:
        page.add_init_script("window.__legacyRaid = 1")   # 코스모 시즌 화면 대신 옛 스테이지 화면(보스별 추천 시험용)
    if setup:
        setup(page)
    if "auto=" not in query:
        query += ("&" if "?" in query else "?") + "auto=1"
    page.goto(ctx.base + "/index.html" + query)
    if not wait:
        page.wait_for_function("() => window._ready")
        return page
    wait_myinfo(page)
    settle(page)
    page.wait_for_selector("#out .party .qbox .qrow[data-key]", timeout=30000)
    settle(page)
    return page


# ---------------------------------------------------------------- 시험
def test_python_js_topk_parity(browser, ctx):
    """여러 보유 필터에서 브라우저 topParties 상위 10 = 파이썬 top_parties 상위 10(조합·순서·점수)"""
    import reco_check as bsr
    import party_reco as pr
    roster = [s["key"] for s in pr.load()[0]]
    page = open_page(browser, ctx)
    cases = [("코스모 게이트", "길레 2단계", "cosmo", "길레"), ("플래시 포인트", "매니저 그레고리 Ⅰ", "rush", "매니저 그레고리"),
             ("작전 (일반)", "SECTOR 1-1", "op", "NOA 상업지구")]
    rng = random.Random(7)
    filters = [roster, sorted(rng.sample(roster, 40)), sorted(rng.sample(roster, 24))]
    bad, n = [], 0
    for cname, q, fk, tab in cases:
        choose(page, cname, q)
        stname = page.evaluate("() => cur[document.getElementById('stage').value].name")
        st = bsr.stage_obj(fk, tab, stname)
        for own in filters:
            js = page.evaluate("(o) => window.PN.topKeys(o, 10)", own)
            cands, dp = bsr.candidates(fk, tab, st)
            cands = [x for x in cands if x["s"]["key"] in set(own)]
            b = bsr.base()
            py = [(bsr.ckey(c), v) for c, v, _ in pr.top_parties(cands, b["cfg"], b["tags"], dp, 10)]
            n += 1
            if [x["key"] for x in js] != [k for k, _ in py] or any(abs(x["v"] - v) > 1e-9 for x, (_, v) in zip(js, py)):
                bad.append((q, len(own), [x["key"] for x in js][:2], [k for k, _ in py][:2]))
    page.close()
    return not bad, "대조 %d건, 불일치 %d %s" % (n, len(bad), bad[:2])


def quick_rows(page, party=1):
    return page.evaluate("""p => [...document.querySelectorAll('.party[data-party="'+p+'"] .qbox .qrow[data-key]')].map(r => [r.dataset.key, r.querySelector('.qsim')?.dataset.sim || 'pending', r.innerText])""", party)


def test_quick_default(browser, ctx):
    """새 기본: 맨 위 「이 스테이지 추천(빠른 계산)」에 1안+차선, 아래 상세 팀 = 1안, 콘솔 오류 0"""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow')
    rows = quick_rows(page)
    shown = page.get_attribute('.party[data-party="1"]', "data-team")
    choose(page, "코스모 게이트", "길레 2단계")
    rows2 = quick_rows(page)
    shown2 = page.get_attribute('.party[data-party="1"]', "data-team")
    page.screenshot(path=os.path.join(ctx.shots, "desktop_quick_cosmo_gille2.png"), full_page=True)
    errs = list(ctx.errors)
    page.close()
    ok = len(rows) >= 2 and shown == rows[0][0] and len(rows2) >= 2 and shown2 == rows2[0][0] and not errs
    return ok, "1-1 %d안 (%s) / 길레2 %d안 (%s) / 상세 = 1안 %s / 오류 %d" % (len(rows), rows and rows[0][1], len(rows2), rows2 and rows2[0][1],
                                                                       shown == (rows and rows[0][0]) and shown2 == (rows2 and rows2[0][0]), len(errs))


def roster_keys():
    import party_reco as pr
    return [s["key"] for s in pr.load()[0]]


def test_quick_owned_small(browser, ctx):
    """내 정보 탭 「추천」 토글로 6명만 남기면(저장값 pn.excl 복원) 추천 팀은 그 6명 안에서만, 「모두 다시 넣기」로 복구"""
    keep = roster_keys()[:6]
    page = open_page(browser, ctx, excl=[k for k in roster_keys() if k not in keep])
    choose(page, "코스모 게이트", "길레 2단계")
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow')
    rows = quick_rows(page)
    inside = all(set(r[0].split(",")) <= set(keep) for r in rows)
    chip = page.inner_text("#mi-chip")
    own = page.evaluate("() => [...document.querySelectorAll('#own input:checked')].map(x => x.dataset.k)")
    page.click("#tab-info")
    off = page.locator(".mi-pick.off").count()
    page.click("#mi-excl button[data-exclclear]")
    settle(page)
    back = page.evaluate("() => [EXCL.size, JSON.parse(localStorage.getItem('pn.excl')), document.querySelectorAll('#own input:checked').length]")
    page.close()
    ok = len(rows) >= 1 and inside and sorted(own) == sorted(keep) and "제외 51명" in chip and off == 51 and back == [0, [], 57]
    return ok, "남긴 6명 -> %d안, 6명 안 %s, 보유 %d, 칩 %s, 꺼진 카드 %d, 다시 넣기 %s" % (len(rows), inside, len(own), chip, off, back)


# test_quick_growth 삭제: 육성 가정(평균·덜 키움·넉넉히)과 「내 파티 전투력」 입력이 화면에서 없어졌다(추천은 내 정보로만, #grow 는 숨김).
# test_savior_power 삭제: 서랍의 구원자별 전투력 입력(#pwl)이 없어졌다(전투력은 내 정보에서 계산).


def test_browser_sim(browser, ctx):
    """「시뮬로 확인」: Pyodide 로 파이썬 엔진을 돌려(예선 뒤 본선) 보인 팀 모두 클리어 확률·95% 구간, 파이썬 결과와 같음, 내 정보 최종 능력치 입력, 콘솔 오류 0, 이 사이트 밖 요청 0"""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    ext = []      # 엔진을 이 사이트 밖에서 받으면 안 된다(lib/pyodide, 2026-10-21)
    page.context.on("request", lambda r: ext.append(r.url) if not r.url.startswith(ctx.base) and not r.url.startswith("data:") and not r.url.startswith("blob:") else None)
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow')
    t0 = time.time()
    page.click('.party[data-party="1"] button[data-sim="1"]')
    wait_sim_done(page)
    dt = time.time() - t0
    n = len(quick_rows(page))
    nsim = page.locator('.party[data-party="1"] .qsim[data-sim]').count()
    txt = page.inner_text('.party[data-party="1"] .mi-verdict')
    stats_title = page.get_attribute('.party[data-party="1"] .mi-verdict', "title")
    state = page.inner_text('.party[data-party="1"] [data-k="simstate"]')
    page.screenshot(path=os.path.join(ctx.shots, "desktop_browser_sim.png"), full_page=False)
    last = page.evaluate("() => { const L = window.PN_SIMQ.lastReq; return {req: L.req, res: Object.fromEntries(Object.entries(L.sigs).map(([k, s]) => [k, window.PN_SIMQ.res[s]]))} }")
    errs = list(ctx.errors)
    page.close()
    # 같은 입력·같은 시드로 이 PC 의 파이썬 엔진을 돌려 브라우저(Pyodide) 결과와 대조
    from battlesim import web
    same = []
    for t in last["req"]["teams"]:      # 브라우저와 같은 진입점·옵션으로 이 PC 에서 다시 돌림
        opt = dict(last["req"]["options"], **t.get("options", {}))
        opt['rules_override'] = dict(last["req"]["options"].get('rules_override', {}), **t.get('options', {}).get('rules_override', {}))
        r = json.loads(web.run_auto(last["req"]["stage"], t["party"], last["req"]["n_runs"], last["req"]["seed"], json.dumps(opt)))
        b = last["res"][t["key"]]
        same.append(r["clear"] == b["clear"] and r["ttk"] == b["ttk"] and r["u"] == b["u"] and r['bs'] == b['bs'])
    # 내 정보 모드: 시뮬 입력은 표준 육성 가정이 아니라 내 정보 최종 능력치(build none + stats_final)
    spec_same = [all(u.get("build") == "none" and u.get("stats_final") for u in t["party"]["units"]) for t in last["req"]["teams"]]
    ok = ("클리어" in txt and "95% 구간" in stats_title and "95% 구간" not in txt and "완료" in state and not errs and same and all(same) and nsim == n - 1
          and all(spec_same) and not ext)
    return ok, "%d팀(시뮬 줄 %d) %.0f초 / 파이썬 결과 같음 %s / 최종 능력치 입력 %s / %s / 바깥 요청 %s / 오류 %s" % (
        n, nsim, dt, same, spec_same, " ".join(txt.split())[:60], ext[:3], errs[:2])


def test_browser_sim_blocked(browser, ctx):
    """엔진 내려받기가 막히면 「시뮬 실패 · 다시 시도」, 빠른 계산 추천은 그대로(codex 안전장치 2)"""
    def block(pg):
        pg.route("**/lib/pyodide/**", lambda r: r.abort())
        pg.context.route("**/lib/pyodide/**", lambda r: r.abort())
    page = open_page(browser, ctx, setup=block)
    n = len(quick_rows(page))
    page.click('.party[data-party="1"] button[data-sim="1"]')
    page.wait_for_function("() => /시뮬 실패/.test((document.querySelector('[data-k=\"simstate\"]')||{}).textContent||'')", timeout=120000)
    retry = page.locator('.party[data-party="1"] button[data-sim="1"]').count()
    n2 = len(quick_rows(page))
    page.close()
    ctx.errors.clear()
    return retry == 1 and n2 == n, "실패 표시 + 다시 시도 버튼 %d, 빠른 계산 %d안 유지 %s" % (retry, n2, n2 == n)


def test_sim_timeout_partial(browser, ctx):
    """실제 UI 중단 경로: 한 팀 완료 뒤 시간 초과→부분 결과 표시→남은 팀만 재시도."""
    page = open_page(browser, ctx)
    page.clock.install()
    page.evaluate("""() => {
      window.__workers=[];
      window.Worker=class {
        constructor(){__workers.push(this)}
        postMessage(req){this.req=req}
        terminate(){this.stopped=true}
      };
      window.__finishTeam=(w,i)=>w.onmessage({data:{type:'team',id:w.req.id,key:w.req.teams[i].key,
        result:{n:w.req.n_runs,clear:0.75,prog:0.9,progs:[0.8,1],via:{coop:0},ci:[0.65,0.85],ttk:10}}});
      if(!simScreen(1))throw Error('예선 시작 실패');
      __workers.forEach(w=>w.onmessage({data:{type:'stage',id:w.req.id,msg:'준비 끝'}}));
      __finishTeam(__workers[0],0);
    }""")
    page.clock.run_for(60000)
    assert page.evaluate("""() => Object.values(SIMQ.scr).some(s=>s.done && s.cut && s.order.length===1)
      && __workers.every(w=>w.stopped) && Object.keys(SIMQ.res).length===0""")
    page.evaluate('() => {window.__workers=[]}')
    page.click('.party[data-party="1"] [data-sim="1"]')
    page.evaluate("""() => {
      const w=__workers[0];w.onmessage({data:{type:'stage',id:w.req.id,msg:'준비 끝'}});__finishTeam(w,0);
    }""")
    assert page.evaluate('() => Object.keys(SIMQ.res).length') == 1
    page.clock.run_for(240000)
    page.wait_for_selector('[data-k="simstate"]:has-text("시뮬 실패")')
    assert '끝난 팀은 이어서 계산해요' in page.locator('[data-k="simstate"]').inner_text()
    assert page.locator('[data-k="progress"]').count() == 0
    assert '75%' in page.locator('.party[data-party="1"] .mi-verdict').inner_text()
    assert page.locator('.party[data-party="1"] .alternatives .qrow .qt:has-text("시뮬 전")').count() == 2
    assert page.evaluate('() => __workers[0].stopped && SIMQ.busy===null')
    page.click('.party[data-party="1"] [data-sim="1"]')
    assert page.evaluate("""() => __workers[1].req.teams.length===__workers[0].req.teams.length-1
      && !__workers[1].req.teams.some(t=>t.key===__workers[0].req.teams[0].key)""")
    page.evaluate("""() => {
      const old=__workers[0],w=__workers[1];__finishTeam(old,1);
      old.onmessage({data:{type:'done',id:old.req.id}});
      if(Object.keys(SIMQ.res).length!==1 || SIMQ.busy!==1)throw Error('늦은 결과가 현재 요청을 바꿈');
      w.onmessage({data:{type:'stage',id:w.req.id,msg:'준비 끝'}});
      w.req.teams.forEach((_,i)=>__finishTeam(w,i));w.onmessage({data:{type:'done',id:w.req.id}});
    }""")
    wait_sim_done(page, timeout=10000)
    assert page.locator('.party[data-party="1"] .qrow[data-key] .qsim').count() == 2
    assert '75%' in page.locator('.party[data-party="1"] .mi-verdict').inner_text()
    assert not ctx.errors, ctx.errors
    page.close()
    return True, '예선 부분 순위→본선 시간 초과→1팀 결과·안내→2팀 재시도 완료, 늦은 메시지 무시'


def test_sim_auto_and_override(browser, ctx):
    """한 번 시뮬을 누르면 다음 스테이지부터 자동 확인, 시뮬 결과가 있으면 판정 배지가 시뮬 기준(title)으로 바뀜, 「자동 확인 끄기」"""
    page = open_page(browser, ctx)
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow[data-key]')
    page.click('.party[data-party="1"] button[data-sim="1"]')
    wait_sim_done(page)
    choose(page, "작전 (일반)", "SECTOR 1-2")
    wait_sim_done(page)
    auto = page.locator('.party[data-party="1"] .qsim').count()
    titles = page.evaluate("() => [...document.querySelectorAll('.party[data-party=\"1\"] .mi-verdict[title]')].map(e => e.title)")
    off = page.locator('button[data-simauto="0"]').count()
    if off:
        page.click("#optbox > summary")
        page.click('button[data-simauto="0"]')
    flag = page.evaluate("() => localStorage.getItem('pn.simauto')")
    page.close()
    ok = auto >= 1 and titles and all("95% 구간" in t for t in titles) and off == 1 and flag == "0"
    return ok, "자동 시뮬 %d팀, 배지 기준 %s, 끄기 버튼 %d, 끈 뒤 저장값 %s" % (auto, titles[:3], off, flag)


def test_request_diagnostics(browser, ctx):
    """실제 닫힌 서버 요청으로 ERR_CONNECTION_REFUSED URL 수집을 검증한다."""
    diagnostic = Ctx(ctx.base, ctx.shots)
    page = browser.new_page()
    attach(page, diagnostic)
    page.goto(ctx.base + '/index.html')     # (.md 는 새 Chromium 에서 «다운로드 시작»으로 이동이 실패함 — 출처만 필요)
    with test_server() as closed:
        url = closed + '/intentionally-closed-server'
    page.evaluate('url => fetch(url).catch(() => null)', url)
    assert any(url in line and 'ERR_CONNECTION_REFUSED' in line for line in diagnostic.network), diagnostic.network
    assert any(url in line and 'ERR_CONNECTION_REFUSED' in line for line in diagnostic.errors), diagnostic.errors
    assert not diagnostic.requests, diagnostic.requests
    page.close()
    return True, '실제 연결 거부의 URL·요청 종류·오류 수집'


def test_load_no_errors(browser, ctx):
    """내 정보가 있으면 처음 열 때 콘솔 오류 0, 추천 카드(1안+차선)와 상세 카드 4장, 옛 사전 계산 파일(data/sim)을 부르지 않음"""
    ctx.errors.clear()
    reqs = []
    page = open_page(browser, ctx, setup=lambda pg: pg.on("request", lambda r: reqs.append(r.url)))
    n = len(quick_rows(page))
    cards = page.locator('.party[data-party="1"] .rowcards .gc').count()
    old = [u for u in reqs if "/data/sim/" in u]      # growth.json 은 이제 내 정보 계산에 쓴다
    errs = list(ctx.errors)
    page.close()
    return n >= 2 and cards == 4 and not old and not errs, "추천 %d안, 카드 %d, 옛 결과 요청 %d, 오류 %s" % (n, cards, len(old), errs[:2])


def test_mobile_layout(browser, ctx):
    """390x844: 가로 스크롤 없음, 상세 카드 4장이 한 줄(인게임 순서), 추천 줄이 화면 안"""
    page = open_page(browser, ctx, viewport={"width": 390, "height": 844})
    choose(page, "코스모 게이트", "길레 2단계")
    sw = page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
    cards = page.evaluate("""() => [...document.querySelectorAll('.party[data-party="1"] .rowcards .gc')].map(g => {
        const r = g.querySelector('.card').getBoundingClientRect(); return [g.dataset.key, Math.round(r.top), Math.round(r.left)] })""")
    qw = page.evaluate("""() => Math.max(...[...document.querySelectorAll('.qbox .qrow')].map(e => e.getBoundingClientRect().right))""")
    page.screenshot(path=os.path.join(ctx.shots, "mobile_cosmo_gille2.png"), full_page=True)
    page.close()
    same_row = len({c[1] for c in cards}) == 1 and [c[2] for c in cards] == sorted(c[2] for c in cards)
    ok = sw[0] <= sw[1] and len(cards) == 4 and same_row and qw <= sw[1] + 1
    return ok, "폭 %s, 카드 %s 한 줄 %s, 추천 줄 오른쪽 끝 %.0f" % (sw, [c[0] for c in cards], same_row, qw)


def test_manual_mode(browser, ctx):
    """수동: 시뮬을 누르면 정책 4종 중 최선으로 수동 클리어 확률 + 서순 표(카드 순서 열), ?mode=manual 유지"""
    page = open_page(browser, ctx, "?mode=manual")
    choose(page, "작전 (일반)", "SECTOR 1-3")
    pend = page.locator('.party[data-party="1"] .seq[data-state="pending"]').count()
    page.click('.party[data-party="1"] button[data-sim="1"]')
    wait_sim_done(page)
    page.wait_for_timeout(300)
    seq =page.locator('.party[data-party="1"] .seq[data-state="ok"]').count()
    rows = page.locator('.party[data-party="1"] .seq .sgrid .tl').count()
    heads = page.evaluate("() => [...document.querySelectorAll('.party[data-party=\"1\"] .seq .sgrid .hd')].map(e => e.textContent)")
    cards = page.evaluate("() => [...document.querySelectorAll('.party[data-party=\"1\"] .rowcards .gc .cnm')].map(e => e.textContent)")
    man = page.locator('.party[data-party="1"] .qsim[data-man="1"]').count()
    page.screenshot(path=os.path.join(ctx.shots, "desktop_manual_seq.png"), full_page=True)
    url_ok = "mode=manual" in page.url
    page.evaluate("() => { localStorage.removeItem('pn.mode'); localStorage.removeItem('pn.simauto') }")
    page.close()
    ok = pend == 1 and seq == 1 and rows >= 1 and heads == cards and man >= 1 and url_ok
    return ok, "누르기 전 안내 %d, 서순 %d(행 %d), 열 = 카드 순서 %s, 수동 결과 %d줄, URL %s" % (pend, seq, rows, heads == cards, man, url_ok)


def test_cosmo_joint(browser, ctx):
    """코스모(2파티): 파티 1·2가 겹치지 않고, 함께 고른 표시, 두 파티 모두 추천 카드"""
    page = open_page(browser, ctx)
    choose(page, "코스모 게이트", "길레 2단계")
    t1 = page.get_attribute('.party[data-party="1"]', "data-team")
    t2 = page.get_attribute('.party[data-party="2"]', "data-team")
    note = page.inner_text('.party[data-party="1"] .qbox .qh')
    r2 = len(quick_rows(page, 2))
    # 시뮬(자동 확인으로 파티 1 -> 2)이 끝나 순서가 바뀐 뒤에도 두 파티가 겹치지 않아야 함(codex 3차 차단 2)
    page.click('.party[data-party="1"] button[data-sim="1"]')
    wait_sim_done(page, (1, 2), timeout=900000)
    page.wait_for_timeout(300)
    u1 = page.get_attribute('.party[data-party="1"]', "data-team")
    u2 = page.get_attribute('.party[data-party="2"]', "data-team")
    page.evaluate("() => localStorage.removeItem('pn.simauto')")
    page.close()
    disjoint = bool(t1 and t2) and not (set(t1.split(",")) & set(t2.split(",")))
    after = bool(u1 and u2) and not (set(u1.split(",")) & set(u2.split(",")))
    return disjoint and after and "파티 1" in note and r2 >= 1, "파티1 %s / 파티2 %s 겹침 없음 %s, 시뮬 뒤 %s / %s 겹침 없음 %s, 파티 표시 %s" % (
        t1, t2, disjoint, u1, u2, after, "파티 1" in note)


def test_rekindle_ui(browser, ctx):
    """작전 재점화 버프: 고르면 머리말에 「재점화 N단계」, 빠른 계산 아군·적 피해 계수에 반영, 시뮬 옵션 rekindle, 다른 콘텐츠엔 안 붙음"""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    choose(page, "작전 (일반)", "36-36")
    h0 = page.inner_text('.party[data-party="1"] .qbox .qh')
    page.evaluate("() => { document.getElementById('optbox').open = true }")
    page.select_option("#rk", "3")
    settle(page)
    h1 = page.inner_text('.party[data-party="1"] .qbox .qh')
    opt = page.evaluate("() => simOpt('op')")
    cz = page.evaluate("() => simOpt('cosmo')")
    saved = page.evaluate("() => localStorage.getItem('pn.rk')")
    page.select_option("#rk", "0")
    settle(page)
    errs = list(ctx.errors)
    page.close()
    ok = ("재점화" not in h0 and "재점화 3단계" in h1 and opt.get("rekindle") == 3 and "rekindle" not in cz
          and saved == '"3"' and not errs)
    return ok, "전 %s / 후 %s / 시뮬 옵션 %s / 코스모 %s / 저장 %s / 오류 %s" % ("재점화" in h0, "재점화 3단계" in h1, opt.get("rekindle"), cz.get("rekindle"), saved, errs[:2])


def test_break_skill_select(browser, ctx):
    """390px 선택·추천·저장·보유 해제·팀별 요청·이전 요청 무시. Worker만 가로채며 실제 엔진은 별도 시험."""
    page = open_page(browser, ctx, viewport={'width': 390, 'height': 844})
    sel = '.party[data-party="1"] .bsel'
    default = page.eval_on_selector(sel, "s => ({value:s.value, recommended:s.selectedOptions[0].textContent.includes('추천'), key:s.dataset.bkey})")
    chosen = page.eval_on_selector(sel, "s => [...s.options].find(o => o.value && o.value !== s.value).value")
    page.select_option(sel, chosen)
    settle(page)
    saved = page.evaluate("k => JSON.parse(localStorage.getItem('pn.brksel.v1'))[k]", default['key'])
    page.reload()
    wait_myinfo(page)
    page.wait_for_selector(sel)
    settle(page)
    restored = page.input_value(sel)
    fit = page.eval_on_selector(sel, "s => s.getBoundingClientRect().right <= innerWidth && parseFloat(getComputedStyle(s).fontSize) >= 16")
    page.evaluate("""() => {
      simAuto(false); window.__bw=[];
      window.Worker=class {constructor(){window.__bw.push(this)} postMessage(req){this.req=req} terminate(){this.stopped=true}};
    }""")
    page.click('button[data-sim="1"]')
    req = page.evaluate("() => window.__bw[0].req")
    team_key = default['key'].split('|', 1)[1]
    team = next(t for t in req['teams'] if t['key'] == team_key)
    options_ok = team['options']['break_skill'] == {'name': chosen, 'level': 5} and all('break_skill' in t['options'] for t in req['teams'])
    # 실행 중 선택 변경 후 이전 worker의 지연된 결과를 직접 배달해도 캐시에 넣지 않는다.
    # 시뮬 중에는 진행 화면만 보이므로 자동 확인을 끄고 다시 그려 결과 카드(.bsel)를 띄운다.
    page.evaluate("() => {simAuto(false); run(true)}")
    page.select_option(sel, '')
    stale = page.evaluate("""() => {const w=window.__bw[0],before=Object.keys(SIMQ.res).length;
      w.onmessage({data:{type:'team',id:w.req.id,key:w.req.teams[0].key,result:{clear:1}}});
      return w.stopped && Object.keys(SIMQ.res).length===before} """)
    page.click('button[data-sim="1"]')
    none_req = page.evaluate("() => window.__bw.at(-1).req")
    none_ok = next(t for t in none_req['teams'] if t['key'] == team_key)['options']['break_skill'] is None
    page.evaluate("""key => {simAuto(false);const w=window.__bw.at(-1);w.onmessage({data:{type:'team',id:w.req.id,key,
      result:{clear:0.5,ci:[0.4,0.6],n:100,bs:{name:null,uses:0,dmg:0,supported:false}}}});run(true)}""", team_key)
    chip = page.locator('.party[data-party="1"] .bbar .bschip').is_visible()
    page.select_option(sel, chosen)
    page.evaluate("""name => {const x=[...document.querySelectorAll('#brk input')].find(x=>x.dataset.b===name);
      x.checked=false;x.dispatchEvent(new Event('change',{bubbles:true}))}""", chosen)
    settle(page)
    invalidated = page.evaluate("k => !(k in JSON.parse(localStorage.getItem('pn.brksel.v1')))", default['key'])
    removed = page.eval_on_selector(sel, "(s,n) => ![...s.options].some(o=>o.value===n)", chosen)
    page.close()
    ok = default['recommended'] and saved == chosen and restored == chosen and fit and options_ok and stale and none_ok and chip and invalidated and removed
    return ok, '추천 %s, 저장/복원 %s, 390px %s, 팀 옵션 %s, 이전 요청 무시 %s, 미장착 %s, 칩 %s, 보유 해제 %s' % (
        default['recommended'], saved == restored == chosen, fit, options_ok, stale, none_ok, chip, invalidated and removed)


def test_break_skill_compare(browser, ctx):
    """실제 Worker 10판 비교: 미지원 제외, 캐시 장착/재비교, 390px 가로 넘침 없음."""
    ctx.errors.clear()
    page = open_page(browser, ctx, viewport={'width': 390, 'height': 844})
    choose(page, '작전 (일반)', 'SECTOR 1-3')
    card = '.party[data-party="1"]'
    before = page.locator(card + ' .bcompare').count()
    setup = page.evaluate('''() => {
      simAuto(false); window.PN_SIMQ.n=10; window.__breakRequests=[];
      const NativeWorker=window.Worker;
      window.Worker=class extends NativeWorker {
        postMessage(req,...args) {if(req.type==='run') window.__breakRequests.push(req);return super.postMessage(req,...args)}
      };
      const key=document.querySelector('.party[data-party="1"]').dataset.team;
      const t=LASTQ[1].rows.find(t=>ckey(t.combo)===key);
      return {key, party:simParty(t), owned:breakOwned(), supported:CFG.breakSupported};
    }''')
    page.click(card + ' button[data-bcompare]')
    page.wait_for_selector(card + ' .bcompare .bcrow')
    progress = page.locator(card + ' .bcompare button[data-simcancel]').count()
    page.wait_for_function('''() => !window.PN_SIMQ.busy &&
      [...document.querySelectorAll('.party[data-party="1"] .bcrow')].every(r=>!r.textContent.includes('대기'))''', timeout=300000)
    rows = page.locator(card + ' .bcrow').count()
    requests = page.evaluate('() => window.__breakRequests')
    expected = [None] + [n for n in setup['owned'] if n in setup['supported']]
    actual = [t['options']['break_skill']['name'] if t['options']['break_skill'] else None for t in requests[0]['teams']]
    unsupported = page.locator(card + ' .bcrow', has_text='미지원').count()
    names = page.eval_on_selector_all(card + ' .bcrow', 'els => els.map(e=>e.dataset.bname)')
    chosen = page.eval_on_selector(card + ' .bsel', '(s,names) => names.find(n=>n && n!==s.value)', expected)
    page.locator(card + ' .bcrow').filter(has=page.locator('button[data-bequip="' + chosen + '"]')).get_by_role('button', name='장착', exact=True).click()
    settle(page)
    selected = page.input_value(card + ' .bsel')
    cache = page.evaluate('''() => {
      const el=document.querySelector('.party[data-party="1"]'),s=el.querySelector('.bsel');
      const t=LASTQ[1].rows.find(t=>ckey(t.combo)===el.dataset.team),r=SIMQ.res[simSig(cur[$('stage').value],t)];
      return !!r && r.bs.name===s.value && JSON.parse(localStorage.getItem('pn.brksel.v1'))[s.dataset.bkey]===s.value;
    }''')
    page.click(card + ' button[data-bcompare]')
    settle(page)
    count = page.evaluate('() => window.__breakRequests.length')
    bounds = page.evaluate('''() => ({sw:document.documentElement.scrollWidth, iw:innerWidth,
      right:Math.max(...[...document.querySelectorAll('.bbar,.bcompare,.bcrow')].map(e=>e.getBoundingClientRect().right))})''')
    page.screenshot(path=os.path.join(ctx.shots, 'mobile_break_compare.png'), full_page=True)
    errs = list(ctx.errors)
    page.close()
    ok = (before == 0 and progress == 1 and rows == len(setup['owned']) + 1 and names == [''] + setup['owned']
          and actual == expected and unsupported == len(setup['owned']) + 1 - len(expected)
          and all(t['party'] == setup['party'] for t in requests[0]['teams'])
          and selected == chosen and cache and count == 1
          and bounds['sw'] <= bounds['iw'] and bounds['right'] <= bounds['iw'] and not errs)
    return ok, '목록 %d/%d, 실행 %d(미지원 %d), 캐시 장착 %s, 요청 %d, 390px %s, 오류 %s' % (
        rows, len(setup['owned']) + 1, len(actual), unsupported, selected == chosen and cache, count, bounds, errs[:2])


def test_break_compare_cancel_after_team_change(browser, ctx):
    """비교 도중 1안 팀이 바뀌어 비교 목록이 사라져도 취소가 보이고 동작해야 한다(멈춘 busy 회귀)."""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    choose(page, '작전 (일반)', 'SECTOR 1-3')
    card = '.party[data-party="1"]'
    page.evaluate('() => {simAuto(false); window.PN_SIMQ.n=400}')
    page.click(card + ' button[data-bcompare]')
    page.wait_for_selector(card + ' [data-k="breakstate"]')
    other = page.evaluate('''() => {const cur=document.querySelector('.party[data-party="1"]').dataset.team;
      const b=[...document.querySelectorAll('button[data-pick="1"]')].find(b=>b.dataset.key!==cur);if(!b)return null;b.click();return b.dataset.key}''')
    settle(page)
    state = page.evaluate('''() => ({busy:window.PN_SIMQ.busy, list:!!document.querySelector('.party[data-party="1"] .bcompare'),
      cancel:document.querySelectorAll('.party[data-party="1"] [data-simcancel]').length})''')
    if state['cancel']:
        page.click(card + ' [data-simcancel]')
        settle(page)
    after = page.evaluate('() => window.PN_SIMQ.busy')
    errs = list(ctx.errors)
    page.close()
    ok = other is not None and state['busy'] == 1 and not state['list'] and state['cancel'] == 1 and after is None and not errs
    return ok, '다른 팀 %s, 바뀐 뒤 %s, 취소 뒤 busy %s, 오류 %s' % (other is not None, state, after, errs[:2])

def gimmick_slot_audit(page):
    """화면의 전체 슬롯 담당을 페이지 데이터·현재 편성·기존 gimTeam 판정과 대조."""
    return page.evaluate('''() => {
      const errors = []; let checked = 0, compared = 0;
      for (const party of document.querySelectorAll('.party[data-team]')) {
        const team = party.dataset.team.split(',').map(key => ({s:BYKEY[key]}));
        const report = gimTeam(team)[1];
        for (const row of party.querySelectorAll('.gimrow[data-code]')) {
          const rule = D.grules[row.dataset.code], slots = rule?.slots || [];
          const shown = [...row.querySelectorAll('.gimslot')];
          if (shown.length !== slots.length) errors.push(row.dataset.code + ': 슬롯 수');
          slots.forEach((slot, i) => {
            checked++;
            const el = shown[i];
            if (!el) return;
            const expected = team.filter(x => (x.s.gt || []).some(t => slot.tags_any.includes(t)));
            const actual = [...el.querySelectorAll('[data-savior]')].map(e => e.dataset.savior);
            // 쉬운 말 개편: 한 줄 = .gimfix(대처 이름 + 구원자 칩 또는 「대처할 구원자 없음」)
            const names = [...el.querySelectorAll('.gimwho')].map(e => e.textContent);
            if (el.dataset.slot !== String(i) || !el.classList.contains(actual.length ? 'ok' : 'none') ||
                !el.querySelector('.fixname')?.textContent ||
                (actual.length ? JSON.stringify(names) !== JSON.stringify(actual.map(key => BYKEY[key]?.name || key))
                               : !el.querySelector('.nobody')) ||
                JSON.stringify([...actual].sort()) !== JSON.stringify(expected.map(x => x.s.key).sort()))
              errors.push(row.dataset.code + '/' + slot.name + ': 담당 불일치');
            const old = report.find(r => r[0] === rule.name && r[1] === slot.name);
            if (old) {
              compared++;
              if (Boolean(old[2]) !== (actual.length > 0)) errors.push(slot.name + ': gimTeam 불일치');
            }
          });
        }
      }
      return {checked, compared, errors};
    }''')


def test_gimmick_slot_owned(browser, ctx):
    """5-10: DISPEL 없는 4명만 보유하면 강화 해제 없음, 별도 폭딜 슬롯에 리디아."""
    keep = ["lydia-moon-caster", "gwen", "asherah-voyager", "smile"]
    # 보유 = 내 정보 보유 전원 − 「추천」 토글로 뺀 구원자(pn.excl)
    page = open_page(browser, ctx, excl=[k for k in roster_keys() if k not in keep])
    choose(page, "작전 (일반)", "SECTOR 5-10")
    team = page.get_attribute('.party[data-party="1"]', "data-team").split(",")
    row = page.locator('.party[data-party="1"] .gimrow[data-code="SELF_BUFF_DEPENDENT"]')
    text = row.text_content()
    no_dispel = page.evaluate("keys => keys.every(k => !BYKEY[k].gt.includes('DISPEL'))", keep)
    audit = gimmick_slot_audit(page)
    fixes = row.locator(".gimfix")
    dispel_line, dealer_line = fixes.nth(0), fixes.nth(1)
    dispel_txt, dealer_txt = dispel_line.text_content(), dealer_line.text_content()
    dispel_nobody, dealer_nobody = dispel_line.locator(".nobody").count(), dealer_line.locator(".nobody").count()
    dispel_none = dispel_line.evaluate("e => e.classList.contains('none')")
    page.close()
    ok = (set(team) == set(keep) and no_dispel
          and "적 버프 지우기" in dispel_txt and dispel_nobody == 1
          and dispel_none
          and "리디아" in dealer_txt and dealer_nobody == 0
          and audit["checked"] > 0 and audit["compared"] > 0 and not audit["errors"])
    return ok, "5-10 %s / 슬롯 대조 %s" % (text, audit)


def test_gimmick_avoid(browser, ctx):
    """실제 스테이지/가상 보유 4명: 불리한 2명의 이유·추정·점수 배지, 접기·조건 변경."""
    keep = ['smile', 'gwen', 'bell', 'asherah-voyager']
    for width in (1280, 390):
        page = open_page(browser, ctx, viewport={'width': width, 'height': 900},
                         excl=[k for k in roster_keys() if k not in keep])
        assert page.locator('.gimavoid').count() == 0  # 1-1: 기피 태그 없음
        choose(page, '작전 (일반)', 'SECTOR 1-2')
        box = page.locator('.party[data-party="1"] .gimavoid')
        assert box.locator('summary').inner_text().startswith('이 스테이지에서 불리한 구원자 2명')
        assert not box.evaluate('e => e.open')
        box.locator('summary').click()
        assert set(box.locator('li[data-savior]').evaluate_all('els => els.map(e=>e.dataset.savior)')) == {'smile', 'gwen'}
        for key in ('smile', 'gwen'):
            row = box.locator('li[data-savior="%s"]' % key)
            assert row.is_visible()
            assert page.evaluate('k => BYKEY[k].name', key) in row.inner_text()
            why = row.locator('.avoidwhy').first
            assert '연타형' in why.inner_text()
            assert page.evaluate('() => D.plain.avoid.MULTIHIT.why') in why.inner_text()
            assert why.locator('.guess:not(.scored)').inner_text() == '추정'
            assert why.locator('.scored').inner_text() == '점수에 반영됨'
        assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth + 1')
        box.locator('summary').click()
        assert not box.locator('li').first.is_visible()
        choose(page, '작전 (일반)', 'SECTOR 1-1')
        assert page.locator('.gimavoid').count() == 0
        page.close()
    assert not ctx.errors, ctx.errors
    return True, '1280/390px: 불리한 2명·이유·추정/점수 배지·접기·조건 변경'


def test_boss_gimmick_mobile(browser, ctx):
    """37-3: 슬롯별 태그·담당 대조, 큰 보스전 경고(1-1 에는 없음), 모바일 배치·더 보기, 접힌 수동 서순에서 모드 전환."""
    page = open_page(browser, ctx, viewport={"width": 390, "height": 844})
    no_big = page.locator('#out [data-k="bigboss"]').count()
    choose(page, "작전 (일반)", "37-3")
    big = page.locator('#out [data-k="bigboss"]').count()
    big_txt = page.inner_text('#out [data-k="bigboss"]') if big else ""
    box = page.locator('.party[data-party="1"] .gimbox')
    lines = box.locator(".gimlist > .gimrow")
    n = lines.count()
    txt = box.text_content()
    severities = lines.evaluate_all("els => els.map(e => +e.dataset.severity)")
    all_n = box.locator(".gimrow").count()
    folded = not box.evaluate("e => e.open")
    assert box.locator(".gimrow:visible").count() == 0
    box.locator("summary").click()
    expanded_n = box.locator(".gimrow:visible").count()
    audit = gimmick_slot_audit(page)
    layout = page.evaluate('''() => {
      const cards = [...document.querySelectorAll('.party[data-party="1"] .card')].map(e => e.getBoundingClientRect());
      // 옛 「내 구원자」 고정 버튼(#dbtn)이 얼굴을 가리던 검사는 버튼이 없어져 「없음」 확인으로 바꿈
      return {sw:document.documentElement.scrollWidth, iw:innerWidth,
        cards:cards.length, same:cards.every(r => Math.abs(r.top-cards[0].top)<1),
        clear:!document.querySelector('#dbtn')};
    }''')
    manual = page.locator('.party[data-party="1"] .manual-details')
    manual_folded = not manual.evaluate("e => e.open") and not page.locator("#m-manual").is_visible()
    manual.locator("summary").click()
    page.locator('label:has(#m-manual)').click()
    settle(page)
    manual_ok = (manual_folded and manual.evaluate("e => e.open")
                 and page.locator("#m-manual").is_checked() and "mode=manual" in page.url
                 and page.evaluate("() => MODE === 'manual' && LS.get('mode') === 'manual'"))
    page.close()
    ok = (n >= 3 and "보스" in txt and "(추정)" not in txt
          and ("대응 미확인" not in txt and "대처" in txt)
          and severities == sorted(severities, reverse=True) and folded and expanded_n == all_n
          and audit["checked"] > 0 and audit["compared"] > 0 and not audit["errors"] and manual_ok
          and layout["sw"] <= layout["iw"] and layout["cards"] == 4 and layout["same"] and layout["clear"]
          and no_big == 0 and big == 1 and "큰 보스전" in big_txt)
    return ok, "기믹 %d/%d줄, 심각도 %s, 더 보기 %s, 모바일 %s, 슬롯 %s, 수동 %s, 큰 보스 경고 1-1 %d / 37-3 %d" % (
        n, all_n, severities, expanded_n == all_n, layout, audit, manual_ok, no_big, big)


def import_synthetic(page, path=SYNTH):
    """내 정보 불러오기 팝업(#mi-open → #mi-file → #dclose)으로 파일을 올린다"""
    page.click('#mi-open')
    page.wait_for_selector('#drawer.open')
    page.set_input_files('#mi-file', path)
    page.wait_for_function('n => MI.growth && MI.info && MI.info.units.length === n && !MI.pending', arg=len(load_json(path)['units']))
    page.click('#dclose')
    settle(page)


# test_myinfo_legacy_power 삭제: 옛 저장값(pn.pow·pn.pw·육성 배율)을 「내 전투력」 모드로 옮기던 기능이 없어졌다.
# 추천은 내 정보로만 계산하고 옛 링크의 g/p 는 무시한다(test_myinfo_required·test_share_link 에서 확인).


def test_myinfo_required(browser, ctx):
    """내 정보 없음: ?auto=1 이어도 계산하지 않고 안내 카드(data-k=miguide), 안내 버튼·#mi-open 으로 불러오기 팝업, 옛 링크 g/p 무시"""
    ctx.errors.clear()
    page = open_page(browser, ctx, "?g=0.8&p=123456&c=op", info=None, wait=False)
    settle(page)
    guide = page.locator('#out [data-k="miguide"]').count()
    state = page.evaluate('''() => ({rows:document.querySelectorAll('#out .qrow[data-key]').length, lastq:Object.keys(LASTQ).length,
      busy:SIMQ.busy, worker:SIMQ.w, grow:$('grow').value, pow:$('mypow').value, old:!!SHARE.oldGrow, chip:$('mi-chip').textContent,
      dbtn:!!document.querySelector('#dbtn'), own:document.querySelectorAll('#own input:checked').length})''')
    page.click('#out button[data-miopen="1"]')
    assert page.locator('.mihow li').count() == 3
    assert not page.locator('#mi-cmd').is_visible()
    assert all(page.locator('#' + key).is_hidden() for key in ('share-link', 'mi-view', 'mi-clear'))
    assert '완전히 종료 후 재실행' in page.inner_text('.mihow')
    assert '사이트가 자동으로 열리며 반영' in page.inner_text('.mihow')
    assert page.locator('#dclose').bounding_box()['height'] >= 39.9
    opened = page.evaluate('() => document.querySelector("#drawer").classList.contains("open") && document.activeElement === $("dclose")')
    page.click('#dclose')
    closed = not page.evaluate('() => document.querySelector("#drawer").classList.contains("open")')
    page.click('#mi-open')
    reopened = page.evaluate('() => document.querySelector("#drawer").classList.contains("open")')
    page.keyboard.press('Escape')
    # 버튼 흐름(?auto=1 없이)에서도 「추천 편성 보기」 대신 안내가 나오고, 계산은 하지 않는다
    page.goto(ctx.base + '/index.html')
    page.wait_for_function('() => window._ready')
    settle(page)
    guide2 = page.locator('#out [data-k="miguide"]').count() + page.locator('#out button[data-go]').count() * 10
    sw = page.evaluate('() => document.documentElement.scrollWidth <= innerWidth')
    errs = list(ctx.errors)
    page.close()
    ok = (guide == 1 and state['rows'] == 0 and state['lastq'] == 0 and state['busy'] is None and state['worker'] is None
          and state['grow'] != '0.8' and state['pow'] == '' and state['old'] and '내 정보 없음' in state['chip']
          and not state['dbtn'] and state['own'] == 0 and opened and closed and reopened and guide2 == 1 and sw and not errs)
    return ok, '안내 %d, 상태 %s, 팝업 열기 %s/닫기 %s/#mi-open %s, 버튼 흐름 안내 %d, 오류 %s' % (guide, state, opened, closed, reopened, guide2, errs[:2])


def test_myinfo_import_clear(browser, ctx):
    """불러오기 팝업으로 파일 → 보유 반영(#own = 내 정보 8명)·내실·추천 칩·판정 「시뮬 전」·저장 복원·카드 격자·지우기·캐시 무효화."""
    ctx.errors.clear()
    page = open_page(browser, ctx, info=None, wait=False)
    requests = []
    page.on('request', lambda r: requests.append(r.url))
    import_synthetic(page)
    page.wait_for_selector('#out .party .qbox .qrow[data-key]')
    choose(page, '작전 (일반)', 'SECTOR 1-3')
    assert page.input_value('#grow') == 'myinfo'
    assert page.locator('#share-mi').is_checked()
    assert len([u for u in requests if '/data/growth.json' in u]) == 1
    keys = page.evaluate('() => MyInfoImport.mapOwned(MI.info, R).keys.sort()')
    own = page.evaluate("() => [...document.querySelectorAll('#own input:checked')].map(x => x.dataset.k).sort()")
    assert len(keys) == 8 and own == keys, (own, keys)
    assert '보유 8명' in page.inner_text('#mi-chip')
    assert page.evaluate('() => LASTQ[1].rows.every(t => t.keys.every(k => %s.includes(k)))' % json.dumps(keys))
    assert page.locator('.party[data-party="1"] .mi-member-power').count() == 4
    assert page.locator('.party[data-party="1"] .mi-member-star').count() == 4
    assert '시뮬 전' in page.inner_text('.party[data-party="1"] .mi-verdict')      # 시뮬 전에는 판정을 보이지 않는다
    assert '시뮬 전' in page.locator('.alternatives').inner_text()
    audit = page.evaluate('''() => {const t=LASTQ[1].rows[0];
      return {sum:t.keys.reduce((n,k)=>n+miProfile().results[k].power,0),actual:t.q.power,
        units:simParty(t).units.every(u=>u.stats_final && u.build==='none'),
        sig:simSig(cur[$('stage').value],t),hash:MI.hash,busy:SIMQ.busy}}''')
    assert audit['sum'] == audit['actual'] and audit['units'] and audit['hash'] in audit['sig'] and audit['busy'] is None, audit
    assert '빌드 다름' in page.inner_text('.party[data-party="1"] .qh')
    page.click('#tab-info')
    assert '보유 8명' in page.inner_text('#mi-meta') and '스타링크 Lv120' in page.inner_text('#mi-meta')
    assert '전술 공통 Lv20' in page.inner_text('#mi-meta') and '저장됨 10-01 ' in page.inner_text('#mi-saved')
    assert page.locator('#mi-list .mi-pick').count() == 8
    assert page.locator('#mi-list .mi-pick input[data-use]:checked').count() == 8
    assert '구원자별 레벨 없음' not in page.inner_text('#mi-meta')
    assert page.locator('#mi-list .mi-link').count() == 3
    assert page.locator('#mi-list [data-uid="1001"] .mi-level').inner_text() == 'Lv140'
    assert all(t == '스타링크 · 슬롯' for t in page.locator('#mi-list .mi-link').all_text_contents())
    pw = page.locator('#mi-list .mi-pw').all_text_contents()
    assert all('—' not in t for t in pw), pw
    vals = [int(t.strip().replace(',', '')) for t in pw]
    assert vals == sorted(vals, reverse=True), vals
    page.fill('#mi-q', '루나')
    assert page.locator('#mi-list .mi-pick').count() == 1
    page.fill('#mi-q', '')
    page.select_option('#mi-sort', 'name')
    page.screenshot(path=os.path.join(ctx.shots, 'myinfo_desktop.png'), full_page=True)
    page.reload()
    page.wait_for_function('() => window._ready && MI.growth && !MI.pending && LASTQ[1]?.rows[0]?.b.finals')
    assert page.input_value('#grow') == 'myinfo'
    assert page.evaluate("() => [...document.querySelectorAll('#own input:checked')].map(x => x.dataset.k).sort()") == keys
    page.evaluate('() => {SIMQ.res.stale={clear:1}; SIMQ.more.stale=9}')
    page.click('#tab-info')
    page.click('#mi-panel-clear')
    settle(page)
    assert page.evaluate('() => !LS.get("myinfo") && !MI.info && !Object.keys(SIMQ.res).length && !Object.keys(SIMQ.more).length')
    assert '불러온 정보 없음' in page.inner_text('#mi-meta')
    # 지운 뒤 숨은 #own 체크는 남는다(miReset 이 syncOwn 을 안 부름) — 내 정보가 없으면 계산하지 않아 화면 영향은 없어 검사하지 않음
    page.click('#tab-reco')
    assert page.locator('#out [data-k="miguide"]').count() == 1 and page.locator('#out .qrow[data-key]').count() == 0
    assert '내 정보 없음' in page.inner_text('#mi-chip')
    assert not ctx.errors, ctx.errors
    page.close()
    return True, '팝업 불러오기·보유 8명 반영·합산·최종 스탯·칩·시뮬 전·카드 격자·검색·저장 복원·지우기·캐시'


def test_myinfo_use_toggle(browser, ctx):
    """내 정보 탭 「추천」 토글을 끄면 EXCL·저장(pn.excl)·보유에서 빠지고 추천 후보에 안 나옴, 「모두 다시 넣기」로 복구"""
    ctx.errors.clear()
    page = open_page(browser, ctx, info=SYNTH)
    choose(page, '작전 (일반)', 'SECTOR 1-3')
    k = page.get_attribute('.party[data-party="1"]', 'data-team').split(',')[0]
    page.click('#tab-info')
    page.locator('#mi-list input[data-use="%s"]' % k).uncheck()
    settle(page)
    state = page.evaluate('''k => ({excl:[...EXCL], saved:JSON.parse(localStorage.getItem('pn.excl')),
      own:!!document.querySelector('#own input[data-k="'+k+'"]:checked'), n:document.querySelectorAll('#own input:checked').length,
      off:document.querySelectorAll('.mi-pick.off').length, btn:!!document.querySelector('#mi-excl button[data-exclclear]')})''', k)
    page.click('#tab-reco')
    settle(page)
    rows = quick_rows(page)
    team = page.get_attribute('.party[data-party="1"]', 'data-team').split(',')
    gone = all(k not in r[0].split(',') for r in rows) and k not in team
    gone_all = page.evaluate('k => LASTQ[1].all.every(t => !t.keys.includes(k))', k)
    chip = page.inner_text('#mi-chip')
    page.click('#tab-info')
    page.click('#mi-excl button[data-exclclear]')
    settle(page)
    back = page.evaluate('() => [EXCL.size, JSON.parse(localStorage.getItem("pn.excl")), document.querySelectorAll("#own input:checked").length, document.querySelectorAll(".mi-pick.off").length]')
    errs = list(ctx.errors)
    page.close()
    ok = (state == {'excl': [k], 'saved': [k], 'own': False, 'n': 7, 'off': 1, 'btn': True} and gone and gone_all
          and '제외 1명' in chip and back == [0, [], 8, 0] and not errs)
    return ok, '끈 구원자 %s, 상태 %s, 추천에서 빠짐 %s/전체 후보 %s, 칩 %s, 다시 넣기 %s, 오류 %s' % (k, state, gone, gone_all, chip, back, errs[:2])


def test_myinfo_rules_mobile(browser, ctx):
    """fixed200·미보유 혼합·미매핑 복귀·판정 「시뮬 전」·390px 내 정보/추천 카드."""
    ctx.errors.clear()
    page = open_page(browser, ctx, viewport={'width': 390, 'height': 844}, info=None, wait=False)
    import_synthetic(page)
    page.wait_for_selector('#out .party .qbox .qrow[data-key]')
    choose(page, '작전 (일반)', 'SECTOR 1-3')
    normal = page.evaluate('() => miProfile().results.luna.power')
    page.click('#tab-info')
    assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=os.path.join(ctx.shots, 'myinfo_mobile.png'), full_page=True)
    page.click('#tab-reco')
    choose(page, '코스모 게이트', '길레 2단계')
    assert page.evaluate('() => miProfile().rule') == 'fixed200'
    assert normal != page.evaluate('() => miProfile().results.luna.power')
    page.click('#tab-info')
    assert all(t == 'Lv200' for t in page.locator('#mi-list .mi-level').all_text_contents())
    assert page.locator('#mi-list .mi-link').count() == 0
    page.click('#tab-reco')
    assert 'Lv200 · 공명 10' in page.inner_text('.party[data-party="1"] .qh')
    assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=os.path.join(ctx.shots, 'myinfo_reco_mobile.png'), full_page=True)
    choose(page, '플래시 포인트', '매니저 그레고리 Ⅰ')
    assert page.evaluate('() => miProfile().rule') == 'fixed200'
    choose(page, '작전 (일반)', 'SECTOR 15-3')
    # 시뮬 전에는 근사 판정(오토 가능/어려움·부족 전투력)을 보이지 않는다 — 시뮬 클리어 50% 미만일 때만 「근사 추정」으로 붙는다
    verdict = page.inner_text('.mi-verdict')
    assert '시뮬 전' in verdict and '오토 어려움' not in verdict and '전투력 필요' not in verdict, verdict
    mixed = page.evaluate('''() => {const missing=R.find(s=>!MI.info.units.some(u=>u.id===s.uid)&&QK.d.sv[s.key]);
      const keys=[...Object.keys(miProfile().results).slice(0,3),missing.key];
      document.querySelectorAll('#own input').forEach(x=>x.checked=keys.includes(x.dataset.k));run();
      return {assumed:LASTQ[1].rows[0].b.assumed,final:simParty(LASTQ[1].rows[0]).units.filter(u=>u.stats_final).length}}''')
    assert mixed == {'assumed': 1, 'final': 3} and '일부 가정' in page.inner_text('.qh'), mixed
    choose(page, '일일 재화 던전', '')
    assert page.evaluate('() => miProfile().rule') == 'normal'
    assert '미매핑 · 평균 가정' not in page.inner_text('.qh')
    page.click('#tab-info')
    # 10/23 c2a3f20: 일일·장비 탐색·작전 하드·큐브도 내 정보 규칙(normal) — 「일반 능력치(미매핑 대체)」 표지가 없어야 함
    assert '일반 능력치' not in page.inner_text('#mi-meta')
    assert all('—' not in t for t in page.locator('#mi-list .mi-pw').all_text_contents())
    assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth')
    assert not ctx.errors, ctx.errors
    page.close()
    return True, 'fixed200·혼합·미매핑·시뮬 전 판정·390px'


def test_myinfo_sim(browser, ctx):
    """자동 확인을 끈 상태에선 시뮬이 안 돎, 버튼으로 내 정보 auto/manual 확률과 최종 스탯 요청 검증(예선 포함)."""
    ctx.errors.clear()
    page = open_page(browser, ctx, info=SYNTH)
    choose(page, '작전 (일반)', 'SECTOR 1-3')
    assert page.evaluate('() => SIMQ.w === null && SIMQ.busy === null')
    assert '클리어' not in page.inner_text('.mi-verdict') and '수동 ' not in page.inner_text('.mi-verdict')
    page.evaluate('() => {SIMQ.n=10;run()}')
    page.click('.party[data-party="1"] button[data-sim="1"]')
    wait_sim_done(page)
    assert '클리어' in page.inner_text('.mi-verdict') and '수동 ' not in page.inner_text('.mi-verdict')
    assert page.evaluate('() => SIMQ.lastReq.req.teams.every(t=>t.party.units.every(u=>u.build==="none"&&u.stats_final))')
    page.click('.manual-details > summary')
    page.locator('label:has(#m-manual)').click()
    page.wait_for_function('() => !document.querySelector("[data-k=progress]") && LASTQ[1].rows.every(t=>SIMQ.res[simSig(cur[$("stage").value],t)]?.man)', timeout=600000)
    settle(page)
    assert page.evaluate('''() => {const t=LASTQ[1].rows.find(t=>ckey(t.combo)===document.querySelector('.party').dataset.team),r=SIMQ.res[simSig(cur[$('stage').value],t)];return document.querySelector('.mi-verdict').textContent.includes('클리어 '+Math.round(r.man.c*100)+'%')}''')
    assert not ctx.errors, ctx.errors
    page.close()
    return True, '버튼 실행·최종 스탯 요청·오토/수동 확률'


def test_share_link(browser, ctx):
    """링크 복사: 조건(c·s·m·rk·b)만, 「내 정보 포함」이면 #shared= — 받는 쪽은 그 정보로 보되 저장 안 함(#shared-bar), 자기 내 정보는 그대로, 옛 g/p·잘못된 값 무시."""
    from urllib.parse import urlsplit, parse_qs
    page = open_page(browser, ctx, viewport={'width': 390, 'height': 844}, info=SYNTH)
    choose(page, '작전 (일반)', '37-3')
    page.evaluate('''() => { $('rk').value='3'; $('rk').dispatchEvent(new Event('change'));setMode('manual',true);run();
      Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>window.copied=text}});
    }''')
    settle(page)
    page.select_option('.party[data-party="1"] .bsel', '')
    expected = page.evaluate('() => [contents[$("content").value].key,cur[$("stage").value].name,MODE,$("rk").value]')
    # 1) 「내 정보 포함」 끔: 조건만
    assert page.locator('#share-mi').is_visible()
    page.uncheck('#share-mi')
    page.click('#share-link')
    page.wait_for_function('() => !!window.copied')
    url = page.evaluate('() => window.copied')
    params = parse_qs(urlsplit(url).query, keep_blank_values=True)
    assert set(params) == {'c', 's', 'm', 'rk', 'b', 'ag', 'ae', 'ao'}, params
    assert params['ag'] == ['0'] and params['ae'] == ['0'] and params['ao'] == ['1']
    assert not urlsplit(url).fragment
    # 2) 「내 정보 포함」: 해시 #shared=
    page.check('#share-mi')
    page.evaluate('() => { window.copied = null }')
    page.click('#share-link')
    page.wait_for_function('() => !!window.copied')
    mi_url = page.evaluate('() => window.copied')
    assert parse_qs(urlsplit(mi_url).query, keep_blank_values=True) == params
    assert urlsplit(mi_url).fragment.startswith('shared=')
    page.close()
    prefs = {'pn.rk': '"5"', 'pn.mode': '"auto"', 'pn.excl': '[]', 'pn.simauto': '0'}
    # 받는 쪽 A: 내 정보 없음 → 공유받은 정보로 보기, 저장 안 함
    recipient = browser.new_context(viewport={'width': 390, 'height': 844})
    target = recipient.new_page()
    attach(target, ctx)
    target.add_init_script(SEED_JS % json.dumps(prefs))
    target.goto(mi_url)
    target.wait_for_function('() => window._ready && MI.info && MI.shared && MI.growth && !MI.pending', timeout=60000)
    settle(target)
    # 참고(검사 안 함): 공유 정보를 비동기로 적용하면서 miReset→rerun→condChanged 가 REQ 를 끄므로, 이 링크는 바로 계산하지 않고
    # 「추천 편성 보기」 안내가 뜬다(조건만 담은 공유 링크는 바로 계산). 화면 쪽 판단이 필요해 시험으로는 고정하지 않는다.
    shared_view = 'idle' if target.locator('#out [data-k="idle"]').count() else 'computed'
    assert target.evaluate('() => [contents[$("content").value].key,cur[$("stage").value].name,MODE,$("rk").value]') == expected
    assert target.evaluate('() => MI.info.units.length') == 8
    assert target.evaluate('() => localStorage.getItem("pn.myinfo")') is None
    assert target.is_visible('#shared-bar') and '공유받은' in target.inner_text('#shared-bar')
    assert '공유받은' in target.inner_text('#mi-chip')
    assert 'shared=' not in target.evaluate('() => location.hash')
    got = target.evaluate('keys=>Object.fromEntries(keys.map(k=>[k,localStorage.getItem(k)]))', list(prefs))
    assert got == prefs, got
    assert target.evaluate('() => document.documentElement.scrollWidth<=innerWidth')
    target.screenshot(path=os.path.join(ctx.shots, 'share_recipient_mobile.png'), full_page=False)
    # 저장하지 않았으므로 다시 열면 내 정보 없음 안내
    target.goto(ctx.base + '/index.html?auto=1')
    target.wait_for_function('() => window._ready')
    settle(target)
    assert target.locator('#out [data-k="miguide"]').count() == 1 and target.is_hidden('#shared-bar')
    # 잘못된 값·옛 육성(g/p) 링크는 기본값으로, g/p 는 쓰지 않음
    target.goto(ctx.base + '/index.html?c=bad&s=bad&g=0.8&p=123456&m=bad&rk=999&b=bad&pick=old&auto=1')
    target.wait_for_function('() => window._ready')
    assert target.evaluate('() => [contents[$("content").value].key,cur[$("stage").value].name,MODE,$("rk").value,$("mypow").value,!!SHARE.oldGrow]') == ['op', 'SECTOR 1-1', 'auto', '0', '', True]
    target.goto(ctx.base + '/index.html?mode=manual&pick=old')
    target.wait_for_function('() => window._ready')
    assert target.evaluate('() => MODE') == 'manual'
    target.goto(ctx.base + '/index.html')
    target.wait_for_function('() => window._ready')
    assert target.input_value('#rk') == '5'
    recipient.close()
    # 받는 쪽 B: 자기 내 정보(57명)가 있음 → 공유 정보로 보다가 「내 정보로 돌아가기」, 저장된 자기 정보는 그대로
    recipient = browser.new_context(viewport={'width': 390, 'height': 844})
    target = recipient.new_page()
    attach(target, ctx)
    seed(target, FULL)
    target.goto(mi_url)
    target.wait_for_function('() => window._ready && MI.shared && MI.info.units.length===8 && MI.growth && !MI.pending', timeout=60000)
    mine = target.evaluate('() => JSON.parse(localStorage.getItem("pn.myinfo")).units.length')
    target.click('#shared-back')
    target.wait_for_function('() => !MI.shared && MI.info && MI.info.units.length===57 && !MI.pending', timeout=60000)
    assert mine == 57 and target.is_hidden('#shared-bar')
    recipient.close()
    return True, '받는 쪽 첫 화면 %s · ' % shared_view + '조건만/내 정보 포함 링크·받는 쪽 저장 안 함·공유 표시·자기 정보 복귀·잘못된 값·옛 g/p 무시·390px'


def test_sim_runs(browser, ctx):
    """Mock only Worker computation; real UI, request, result handling and cache signatures."""
    page = open_page(browser, ctx, viewport={'width': 390, 'height': 844})
    page.evaluate('''() => {simAuto(false);window.requests=[];
      window.Worker=class {postMessage(req){requests.push(req);this.req=req} terminate(){this.stopped=true}};
      window.completeSim=()=>{const w=SIMQ.w,r=w.req;r.teams.forEach((t,i)=>w.onmessage({data:{type:'team',id:r.id,key:t.key,
        result:{n:r.n_runs,clear:[0.35,0.65,0.9][i%3],ci:[0.2,0.8],ttk:10,gate:true}}}));
        w.onmessage({data:{type:'done',id:r.id}})};
    }''')
    assert page.locator('input[name="runs"]').count() == 0      # 시뮬은 100판으로 충분해서 판 수 선택(300판 정밀)을 없앴다
    page.click('button[data-sim="1"]')
    assert page.evaluate('() => requests.at(-1).n_runs') == 100
    page.evaluate('() => {simAuto(false);completeSim()}')
    assert page.locator('button[data-refine]').count() == 0
    assert page.evaluate('() => document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=os.path.join(ctx.shots, 'share_runs_mobile.png'), full_page=True)
    page.close()
    return True, '100판 요청·300판 옵션 없음·390px'


def test_press_to_compute(browser, ctx):
    """「추천 편성 보기」: 누르기 전엔 계산 안 함 → 누르면 진행 화면만(예선 → 본선, 결과 카드 안 보임) → 끝나면 결과(판정은 모두 시뮬 기준), 조건을 바꾸면 안내로."""
    ctx.errors.clear()
    page = open_page(browser, ctx, query="?auto=0", simauto=None, wait=False)     # ?auto=1 없이 연다. 자동 확인 저장값 없음(기본)
    wait_myinfo(page)
    settle(page)
    assert page.locator('[data-k="idle"]').count() == 1 and page.locator('.qrow[data-key]').count() == 0
    assert page.evaluate('() => !!document.querySelector(".mi-tabs #share-link") && !!document.querySelector(".mi-tabs #mi-open") && !document.querySelector("#dbtn") && !!(document.querySelector(".mi-tabs").compareDocumentPosition(document.querySelector(".input-panel")) & Node.DOCUMENT_POSITION_FOLLOWING)')
    assert page.evaluate('() => SIMQ.w === null && SIMQ.busy === null')
    # 진행 중에 결과(.qbox)가 한 번이라도 보이면 기록한다
    page.evaluate('''() => {window.__seen={bad:0,pre:0,main:0,progress:0,mislabel:0};
      new MutationObserver(()=>{const o=document.getElementById('out'),pg=o.querySelector('[data-k="progress"]');
        if(pg){__seen.progress++;const tx=pg.textContent;if(SIMQ.screening&&/후보 거르는 중/.test(tx))__seen.pre++;
          if(SIMQ.screening&&/상위 팀 확인 중/.test(tx))__seen.mislabel++;if(!SIMQ.screening&&/상위 팀 확인 중/.test(tx))__seen.main++}
        if(o.querySelector('.party[data-party] .qbox')&&simWaiting(cur[$('stage').value]))__seen.bad++}).observe(document.getElementById('out'),{childList:true,subtree:true,characterData:true})}''')
    t0 = time.time()
    page.click('button[data-go]')
    page.wait_for_selector('#out [data-k="progress"]', timeout=10000)
    first = page.evaluate('() => ({qbox:document.querySelectorAll("#out .qbox").length, drawer:document.querySelector("#drawer").classList.contains("open")})')
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow[data-key]', timeout=600000)
    wait_sim_done(page)
    dt = time.time() - t0
    seen = page.evaluate('() => window.__seen')
    res = page.evaluate('''() => {const st=cur[$('stage').value],k=scrKey(st,1),sc=SIMQ.scr[k];
      return {done:!!sc&&sc.done,n:sc&&sc.n,order:sc&&sc.order.length,pending:document.querySelectorAll('#out .qv.pending').length,
        sim:LASTQ[1].rows.every(t=>SIMQ.res[simSig(st,t)]),prog:Object.values(SIMQ.res).some(r=>r&&r.prog!=null),
        approx:document.querySelectorAll('#out .qv.approx').length}}''')
    page.screenshot(path=os.path.join(ctx.shots, 'desktop_press_result.png'), full_page=False)
    page.select_option('#stage', index=1)
    page.wait_for_selector('[data-k="idle"]')               # 조건을 바꾸면 결과를 비우고 안내로 돌아간다
    idle_rows = page.locator('.qrow[data-key]').count()
    assert page.locator('#gmode').count() == 1  # 결과→대기 전환에도 자세히의 그래프 설정 보존
    errs = list(ctx.errors)
    page.close()
    ok = (first == {'qbox': 0, 'drawer': False} and seen['bad'] == 0 and seen['pre'] > 0 and seen['main'] > 0
          and res['done'] and 3 < res['n'] <= 120 and res['order'] > 0 and res['pending'] == 0 and res['sim'] and res['prog']
          and res['approx'] == 0 and idle_rows == 0 and not errs)
    return ok, '%.0f초, 처음 %s, 진행 기록 %s, 결과 %s, 조건 변경 뒤 결과 %d, 오류 %s' % (dt, first, seen, res, idle_rows, errs[:2])


def test_skill_view(browser, ctx):
    """Lazy data, owned levels(내 정보), 상세 팝업의 스킬 레벨 → 스킬 설명 팝업, nested folds, glossary, keyboard and 390px layout."""
    for width in (1280, 390):
        ctx.errors.clear()
        page = open_page(browser, ctx, viewport={'width': width, 'height': 900 if width == 1280 else 844}, info=SYNTH)
        requests = []
        page.on('request', lambda r: requests.append(r.url) if '/savior_skills.json' in r.url else None)
        assert page.evaluate('() => !performance.getEntriesByType("resource").some(r=>r.name.includes("savior_skills.json"))')
        face = page.locator('.party[data-party="1"] .qrow .skill-face').first
        fkey = face.get_attribute('data-skill-open')
        face.click()
        page.wait_for_selector('#skills-body .skill-card')
        assert page.locator('#skills-body .skill-card').count() == 4
        own = page.evaluate('key => MI.info.units.find(u=>u.id===BYKEY[key].uid).skills', fkey)
        assert page.locator('#skills-body .skill-card').evaluate_all('(cards)=>cards.map(c=>+c.dataset.level)') == [own[k] for k in ('basic', 'special', 'ultimate', 'passive')]
        page.keyboard.press('Escape')
        assert not page.locator('#skills-dialog').is_visible()
        page.wait_for_function("b => b === document.activeElement && b.getAttribute(\"aria-expanded\")===\"false\"", arg=face.element_handle(), timeout=3000)
        choose(page, '작전 (일반)', 'SECTOR 1-3')
        page.click('#tab-info')
        page.click('#mi-list button[data-mi-sheet="1001"]')
        page.wait_for_selector('#mi-dlg-body .ms-head')
        assert page.locator('#mi-dlg-body .ms-skill b').all_text_contents() == ['Lv3', 'Lv4', 'Lv5', 'Lv2']
        page.click('#mi-dlg-body [data-skill-open]')
        page.wait_for_selector('#skills-body .skill-card')
        body = page.locator('#skills-body')
        assert body.locator('.skill-card').evaluate_all('(cards)=>cards.map(c=>+c.dataset.level)') == [3, 4, 5, 2]
        assert '쿨 5턴' in body.locator('[data-slot="special"] .skill-meta').inner_text()
        assert '다음 강화: Lv5' in body.locator('[data-slot="special"] .skill-next').inner_text()
        upgrades = body.locator('.skill-upgrades').first
        assert upgrades.get_attribute('open') is None
        upgrades.locator('summary').click()
        assert upgrades.locator('.achieved').count() == 3 and upgrades.locator('.unlearned').count() == 7
        term = body.locator('.skill-description .skill-term').first
        term.click()
        assert term.get_attribute('aria-expanded') == 'true'
        assert term.locator('..').locator('.skill-tip').is_visible()
        assert term.get_attribute('title') == term.locator('..').locator('.skill-tip').inner_text()
        assert page.evaluate('''() => {const d=document.querySelector('#skills-dialog');return document.documentElement.scrollWidth<=innerWidth && d.scrollWidth<=d.clientWidth && d.getBoundingClientRect().right<=innerWidth}''')
        page.screenshot(path=os.path.join(ctx.shots, 'skills_myinfo_%d.png' % width), full_page=False)
        page.click('#skills-dialog [data-skill-close]')
        assert not page.locator('#skills-dialog').is_visible() and page.locator('#mi-dlg').is_visible()
        page.click('#mi-dlg [data-mi-dlg-close]')
        assert not page.locator('#mi-dlg').is_visible()
        page.click('#tab-reco')
        settle(page)
        card = page.locator('.party[data-party="1"] .skill-open-card').first
        key = card.get_attribute('data-skill-open')
        expected = page.evaluate('key => MI.info.units.find(u=>u.id===BYKEY[key].uid).skills', key)
        card.focus()
        page.keyboard.press('Enter')
        page.wait_for_selector('#skills-body .skill-card')
        assert page.locator('#skills-body .skill-card').evaluate_all('(cards)=>cards.map(c=>+c.dataset.level)') == [expected[k] for k in ('basic', 'special', 'ultimate', 'passive')]
        assert page.evaluate('''() => {const d=document.querySelector('#skills-dialog');return document.documentElement.scrollWidth<=innerWidth && d.scrollWidth<=d.clientWidth && d.getBoundingClientRect().right<=innerWidth}''')
        assert page.locator('#skills-dialog').evaluate('(d)=>d.contains(document.activeElement)')
        modal_term = page.locator('#skills-body .skill-description .skill-term').first
        modal_term.click()
        page.evaluate('() => SKILLS.refresh()')
        assert modal_term.get_attribute('aria-expanded') == 'true'
        page.screenshot(path=os.path.join(ctx.shots, 'skills_reco_%d.png' % width), full_page=False)
        page.click('[data-skill-close]')
        assert card.evaluate('(b)=>b===document.activeElement')
        assert len(requests) == 1, requests
        assert not ctx.errors, ctx.errors
        page.close()
    return True, 'desktop/390px: 4 slots, owned levels, 상세 팝업 → 스킬 팝업, folds, glossary, keyboard, lazy fetch once, no overflow'


def test_skill_retry(browser, ctx):
    """A failed lazy request can be retried without reloading the page."""
    page = open_page(browser, ctx)
    page.route('**/data/savior_skills.json*', lambda route: route.fulfill(status=503, body='unavailable'))
    page.locator('.skill-open-card').first.click()
    page.wait_for_selector('[data-skill-retry]')
    page.unroute('**/data/savior_skills.json*')
    page.click('[data-skill-retry]')
    page.wait_for_selector('#skills-body .skill-card')
    assert page.locator('#skills-body .skill-card').count() == 4
    page.close()
    return True, 'failed fetch → retry → skill cards'


def test_myinfo_full(browser, ctx):
    """내 정보 카드 → 상세 팝업(#mi-dlg): 지연 로드·계산 1회, 능력치 8칸·스킬 4칸·장비 6부위, 시뮬 사용 표시(작전 on / 미매핑 off), 닫기·Esc, 390px 가로 넘침 없음."""
    for width in (1280, 390):
        ctx.errors.clear()
        page = open_page(browser, ctx, viewport={'width': width, 'height': 900}, info=SYNTH)
        choose(page, '작전 (일반)', 'SECTOR 1-3')
        page.evaluate('''() => {window.detailCalls=0;const f=MyInfoStats.final_stats;
          MyInfoStats.final_stats=(...a)=>{if(a[4])detailCalls++;return f(...a)}}''')
        page.click('#tab-info')
        assert page.evaluate('() => detailCalls') == 0
        assert page.evaluate('() => !performance.getEntriesByType("resource").some(r=>r.name.includes("myinfo_view.json"))')
        assert page.locator('#mi-list .mi-pick').count() == 8
        button = page.locator('#mi-list button[data-mi-sheet="1001"]')
        assert button.get_attribute('aria-haspopup') == 'dialog'
        button.focus()
        page.keyboard.press('Enter')
        page.wait_for_selector('#mi-dlg-body .ms-head')
        dlg = page.locator('#mi-dlg')
        assert dlg.evaluate('d => d.open')
        assert page.evaluate('() => detailCalls') == 1
        assert page.evaluate('() => performance.getEntriesByType("resource").some(r=>r.name.includes("myinfo_view.json"))')
        body = page.locator('#mi-dlg-body')
        assert body.locator('.ms-grid .ms-tiles').first.locator('.ms-tile').count() == 8
        assert body.locator('.ms-skill').count() == 4
        assert body.locator('.mi-gear').count() == 6  # synthetic item 800001 maps to slot 0 in the public slot table
        assert body.locator('.ms-sim.on').count() == 1, body.locator('.ms-sim').inner_text()
        power = body.locator('.ms-power b').inner_text()
        assert power == page.evaluate('() => miProfile().results[R.find(s=>s.uid===1001).key].power.toLocaleString("ko-KR",{maximumFractionDigits:8})'), power
        fit = page.evaluate('''() => {const d=document.querySelector('#mi-dlg');
          return {sw:document.documentElement.scrollWidth, iw:innerWidth, dsw:d.scrollWidth, dcw:d.clientWidth, right:Math.round(d.getBoundingClientRect().right)}}''')
        assert fit['sw'] <= fit['iw'] and fit['dsw'] <= fit['dcw'] and fit['right'] <= fit['iw'], fit
        page.screenshot(path=os.path.join(ctx.shots, 'myinfo_sheet_%d.png' % width), full_page=False)
        page.click('#mi-dlg [data-mi-dlg-close]')
        assert not dlg.evaluate('d => d.open')
        # 일일 재화 던전도 내 정보 규칙(10/23 c2a3f20) — 상세가 「이 수치로 시뮬」, Esc 로 닫힘
        page.click('#tab-reco')
        choose(page, '일일 재화 던전', '')
        page.click('#tab-info')
        page.click('#mi-list button[data-mi-sheet="1001"]')
        page.wait_for_selector('#mi-dlg-body .ms-head')
        assert page.locator('#mi-dlg-body .ms-sim.on').count() == 1 and '이 수치로 시뮬' in page.inner_text('#mi-dlg-body .ms-sim')
        page.keyboard.press('Escape')
        assert not dlg.evaluate('d => d.open')
        assert page.evaluate('() => document.documentElement.scrollWidth<=innerWidth')
        assert not ctx.errors, ctx.errors
        page.close()
    return True, '1280/390px: 지연 로드·계산 1회, 능력치·스킬·장비, 시뮬 사용 표시, 닫기·Esc, 가로 넘침 없음'


def test_graph_evidence(browser, ctx):
    """근거 보기 켬 → 그래프 그려짐 → 선 탭 시 syn_detail.json 요청 후 근거 표시."""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    # 근거 보기(show-why) 켜기
    page.click('.party[data-party="1"] .score-details > summary')
    page.check('#showwhy')
    settle(page)
    # cytoscape가 로드·그려질 때까지 대기(cy 전역이 null이 아님)
    page.wait_for_function("() => typeof cy !== 'undefined' && cy && typeof cy.edges === 'function'", timeout=30000)   # let 전역(window 속성 아님 — cy 는 id=cy 요소)
    cy_drawn = page.evaluate("() => cy != null && cy.edges().length > 0")
    # 첫 번째 엣지 탭 — 로딩 중 표시 후 근거로 교체
    page.evaluate("() => cy.edges()[0].trigger('tap')")
    page.wait_for_function("() => !$('cyinfo').innerHTML.includes('불러오는 중')", timeout=15000)
    info_text = page.inner_text("#cyinfo")
    # syn_detail.json이 요청됐는지 확인
    syn_loaded = page.evaluate("() => _sd != null")
    # 두 번째 탭: 이미 _sd 있으므로 다시 요청 안 함(캐시)
    req_count = page.evaluate("""() => {
      let n = 0;
      const orig = window.fetch;
      window.fetch = (...a) => { if (String(a[0]).includes('syn_detail')) n++; return orig(...a); };
      cy.edges().length > 1 && cy.edges()[1].trigger('tap');
      window.fetch = orig;
      return n;
    }""")
    errs = list(ctx.errors)
    page.screenshot(path=os.path.join(ctx.shots, "graph_evidence.png"))
    page.close()
    ok = (cy_drawn and syn_loaded and info_text and "불러오는 중" not in info_text
          and "불러오지 못했습니다" not in info_text and req_count == 0 and not errs)
    return ok, "그래프 그려짐 %s, syn_detail 로드 %s, 근거 표시 %s, 2차 탭 재요청 %d, 오류 %s" % (
        cy_drawn, syn_loaded, bool(info_text), req_count, errs[:1])


def test_guild_defense(browser, ctx):
    """길드방어전(시즌제): 콘텐츠 이름에 시즌 기간, 기본 스테이지=EX, 안내 패널(최고 점수 조합·가설 A/B·추정 배지·재사용 제한·기준일),
    단계 선택 반영, 시즌 종료 뒤 「갱신 대기」, 다른 콘텐츠로 바꾸면 패널 숨김, 추천 4명이 나오고 콘솔 오류 0"""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    names = page.eval_on_selector("#content", "s => [...s.options].map(o => o.textContent)")
    name = next(n for n in names if n.startswith("길드방어전"))
    page.select_option("#content", label=name)
    settle(page)
    page.wait_for_selector('#out .party[data-party="1"] .rowcards .gc', timeout=30000)
    first_stage = page.eval_on_selector("#stage", "s => s.selectedOptions[0].textContent")
    panel = page.locator("#guild-panel")
    shown = panel.is_visible()
    text = panel.inner_text()
    sim_sets = panel.locator('[data-k="gd-sim-set"]').all_text_contents()
    sim_data_ok = page.evaluate("""() => D.guild.sim.growth.join(',') === '1,1.5,2,2.5,3'
        && D.guild.sim.sets.max.join(',') === '3,3,3,3'
        && D.guild.sim.teams.every(t => !!t.bySets.max.fracBySupport)
        && D.guild.sim.growth.every(g => ['off','max'].includes(GuildView.simExpect(D.guild,D.guild.sim,g).set))""")
    cards = page.locator('.party[data-party="1"] .rowcards .gc').count()
    gim = page.locator('.party[data-party="1"] .gimrow[data-code="TARGET_PRIORITY"]').count()
    page.select_option('#guild-panel select[data-g="level"]', "6")
    page.wait_for_function("() => document.querySelector('#guild-panel .gd-now').textContent.includes('추가 점수 60%')")
    sel6 = panel.locator('[data-k="gd-now"]').inner_text()
    page.click('#guild-panel button[data-g="best"]')
    best_back = "(최고 조합)" in panel.locator('[data-k="gd-now"]').inner_text()
    # 시즌 종료 뒤 표시: 화면 함수에 시즌 끝난 시각을 넣어 본다(실제 오늘 날짜와 무관하게 판정)
    stale = page.evaluate("() => GuildView.panelHtml(D.guild, null, 7, Date.parse('2026-11-06T00:00:00+09:00'), esc)")
    live = page.evaluate("() => GuildView.panelHtml(D.guild, null, 7, Date.parse('2026-10-30T12:00:00+09:00'), esc)")
    page.select_option("#stage", index=1)
    page.dispatch_event("#stage", "change")
    settle(page)
    lower = panel.inner_text()
    choose(page, "작전 (일반)", "36")
    hidden = not panel.is_visible()
    errs = list(ctx.errors)
    page.close()
    ok = (name == "길드방어전(시즌4 10/29~11/05)" and first_stage.startswith("7단계 EX") and shown and cards == 4 and gim == 1
          and "최고 점수가 나오는 조합" in text and "보스를 깎은 비율" in text and "가설 B" not in text and "추정" in text
          and "시뮬 추정: 깰 수 있는 최고 단계" in text and "개발 중" in text
          and sim_data_ok and len(sim_sets) == 5 and all(s in ('선택 효과 끔', '모두 최대') for s in sim_sets)
          and '×2.5' in text and '×3' in text and '지원별 클리어 가능 최고 단계 (×2)' in text
          and "일일 초기화 전까지" in text and "기준" in text and "추가 점수 60%" in sel6 and best_back
          and "갱신 대기" in stale and "갱신 대기" not in live and "6단계에는 별의 도전이 없습니다" in lower
          and hidden and not errs)
    return ok, "%s / %s / 카드 %d / 기믹줄 %d / 패널 %s / 오류 %s" % (name, first_stage, cards, gim, shown, errs[:2])


def test_guild_season_rollover(browser, ctx):
    """시즌 종료 시각(11/05 04:00)을 넘기면 열어 둔 화면도 «갱신 대기»로 바뀜(가짜 시계로 03:59:50 에 열고 20초 진행)"""
    ctx.errors.clear()
    page = open_page(browser, ctx, setup=lambda pg: pg.clock.install(time=_dt.datetime(2026, 11, 5, 3, 59, 50, tzinfo=_dt.timezone(_dt.timedelta(hours=9)))))
    names = page.eval_on_selector("#content", "s => [...s.options].map(o => o.textContent)")
    page.select_option("#content", label=next(n for n in names if n.startswith("길드방어전")))
    settle(page)
    page.wait_for_selector("#guild-panel [data-k=gd-dev]", timeout=30000)
    before = page.locator("#guild-panel [data-k=gd-stale]").count()
    page.clock.fast_forward(20000)
    page.wait_for_selector("#guild-panel [data-k=gd-stale]", timeout=10000)
    after = page.locator("#guild-panel [data-k=gd-stale]").count()
    errs = list(ctx.errors)
    page.close()
    return before == 0 and after == 1 and not errs, "전 %d / 후 %d / 오류 %s" % (before, after, errs[:2])


def test_guild_search(browser, ctx):
    """길방 «내 정보로 최고 점수 편성 찾기»: 내 정보가 없으면 버튼 없음 안내, 있으면 예선→본선을 브라우저 작업자로 끝까지 돌려
    기대 점수 순위 표가 나오고, 위에서 선택 효과를 바꾸면 낡은 결과 경고, 길방이 아닌 스테이지에서는 숨김. (시험 속도를 위해 탐색 크기만 줄여 돌린다)"""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    names = page.eval_on_selector("#content", "s => [...s.options].map(o => o.textContent)")
    page.select_option("#content", label=next(n for n in names if n.startswith("길드방어전")))
    settle(page)
    shown = page.locator("#guild-search").is_visible()
    has_btn = page.locator('#guild-search button[data-gs="start"]').count()
    # 탐색 크기를 줄인다(풀 8명·상위 2팀·단계 4 하나·판수 2) — 로직은 그대로
    page.evaluate("""() => {const S=D.guild.search;S.poolSize=8;S.minRole={'서포터':1,'디펜더':1};S.minPowerRatio=0;S.screen2={keep:3,runs:2};S.finalists=2;S.screen.runs=2;S.final.runs=2;S.final.levels=[4];S.final.supports=['fire','gust']}""")
    page.click('#guild-search button[data-gs="start"]')
    page.wait_for_selector('#guild-search [data-k="gd-search-table"]', timeout=540000)
    rows = page.locator('#guild-search [data-k="gd-search-table"] tbody tr').count()
    txt = page.locator('#guild-search').inner_text()
    score_ok = page.evaluate("""() => [...document.querySelectorAll('#guild-search tbody tr')].every(tr => /^[0-9,]+$/.test(tr.children[4].innerText.trim()) && +tr.children[4].innerText.replace(/,/g,'') > 0)""")
    # 선택 효과를 바꾸면 낡은 결과 경고
    page.select_option('#guild-panel select[data-g="set"][data-i="0"]', "1")
    page.wait_for_function("() => !!document.querySelector('#guild-search [data-k=gd-search-stale]')")
    page.select_option("#stage", index=1)
    page.dispatch_event("#stage", "change")
    settle(page)
    hidden = not page.locator("#guild-search").is_visible()
    errs = list(ctx.errors)
    page.close()
    ok = shown and has_btn == 1 and 1 <= rows <= 5 and score_ok and "추정" in txt and hidden and not errs
    return ok, "패널 %s / 버튼 %d / 결과 %d줄 / 점수 %s / 숨김 %s / 오류 %s" % (shown, has_btn, rows, score_ok, hidden, errs[:2])


def test_guild_search_dropped(browser, ctx):
    """Worker 메시지→3단계 탐색→협공 제외 수/점수/화면. 제외 해제하면 해당 팀도 복귀."""
    page = open_page(browser, ctx)
    names = page.locator('#content option').all_text_contents()
    page.select_option('#content', label=next(n for n in names if n.startswith('길드방어전')))
    settle(page)
    page.evaluate("""() => {
      const S=D.guild.search;
      Object.assign(S,{poolSize:5,minPowerRatio:0,minRole:{},minFront:0,minDealer:0,
        screen2:{keep:5,runs:2},finalists:5});
      S.screen.runs=2;S.final.runs=2;S.final.levels=[4];S.final.supports=['fire','gust'];
      window.__jobs=[];window.__banned=null;
      window.Worker=class {
        postMessage(req){
          __jobs.push(req);
          for(const t of req.teams){
            const key=t.party.units.map(u=>u.key).sort().join(',');
            if(!__banned)__banned=key;
            const banned=key===__banned;
            const result={n:req.n_runs,clear:banned?1:0.5,prog:banned?1:0.5,
              progs:banned?[1,1]:[0,1],via:banned?{forced_coop:0.1}:{trigger:1}};
            setTimeout(()=>{if(!this.dead)this.onmessage({data:{id:req.id,type:'team',key:t.key,result}})},0);
          }
          setTimeout(()=>{if(!this.dead)this.onmessage({data:{id:req.id,type:'done'}})},0);
        }
        terminate(){this.dead=true}
      };
    }""")
    page.click('#guild-search [data-gs="start"]')
    page.wait_for_selector('#guild-search [data-k="gd-search-table"]')
    notes = page.locator('#guild-search [data-k="gd-notes"]')
    notes.locator('summary').click()
    dropped = notes.locator('[data-k="gd-search-dropped"]')
    assert dropped.is_visible() and dropped.inner_text().endswith('팀: 1개')
    state = page.evaluate("""() => ({dropped:GSR.dropped,rows:GSR.rows.length,
      banned:GSR.rows.some(r=>r.keys.slice().sort().join(',')===__banned),
      phases:[...new Set(__jobs.map(j=>j.seed))].sort(),
      scores:GSR.rows.map(r=>r.score),
      expected:GuildView.scoreAt(D.guild,GuildView.extraPct(D.guild,4,gsTiers()),1)})   // 순위 점수 = 판별 점수 상위 20% 평균(2판이면 최고 1판 = 상한)""")
    assert state['dropped'] == 1 and state['rows'] == 4 and not state['banned'], state
    assert state['phases'] == [1, 2, 3] and all(s == state['expected'] and s > 0 for s in state['scores']), state
    shown = page.locator('#guild-search tbody tr').all_text_contents()
    assert len(shown) == 4 and all(format(state['expected'], ',') in row for row in shown), shown
    page.uncheck('#guild-search [data-gs="coop"]')
    page.click('#guild-search [data-gs="start"]')
    page.wait_for_selector('#guild-search [data-k="gd-search-table"]')
    assert page.evaluate("() => GSR.dropped===0 && GSR.rows.length===5 && GSR.rows.some(r=>r.keys.slice().sort().join(',')===__banned)")
    assert page.locator('[data-k="gd-search-dropped"]').count() == 0
    assert not ctx.errors, ctx.errors
    page.close()
    return True, '협공 1팀 제외→4팀/판별 기대 점수 표시, 제외 해제→5팀 복귀'


def test_equip_goal_option(browser, ctx):
    """장비 탐사 목표 옵션: 장비 탐사에서만 보이고, «60턴 안에 클리어»면 안내 문구가 있고 «클리어만»이면 사라짐"""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    page.evaluate("() => { document.getElementById('optbox').open = true }")
    hidden_op = page.locator("#goalbox").is_hidden()
    choose(page, "장비 탐사", "혹한")
    page.wait_for_selector('.party[data-party="1"] .qbox')
    vis = page.locator("#goalbox").is_visible()
    note_on = page.locator('.qbox [data-k="starnote"]').count() > 0
    page.select_option("#goal", "0")
    settle(page)
    page.wait_for_selector('.party[data-party="1"] .qbox')
    note_off = page.locator('.qbox [data-k="starnote"]').count() == 0
    saved = page.evaluate("() => localStorage.getItem('pn.goal')")
    errs = list(ctx.errors)
    page.close()
    ok = hidden_op and vis and note_on and note_off and saved == '"0"' and not errs
    return ok, "작전에서 숨김 %s / 장비 탐사 표시 %s / 안내 켬 %s / 끔 %s / 저장 %s / 오류 %d" % (hidden_op, vis, note_on, note_off, saved, len(errs))


def test_cosmo_search(browser, ctx):
    """코스모 게이트 «3보스 최고 점수 편성 찾기»(가상 계정 전원 로스터): 코스모에서만 패널 표시, 난이도 선택 뒤 찾기 -> 완료,
    표에 보스 3행 + 합계, 12명 모두 다름, 합계 = 세 팀 점수 합, 취소 버튼, 콘솔 오류 0. (시험 속도를 위해 탐색 크기만 줄인다)"""
    ctx.errors.clear()
    page = open_page(browser, ctx, raid_ui=True)
    panel = page.locator("#cosmo-search")
    hidden_first = not panel.is_visible()
    page.select_option("#content", label=next(l for l in page.eval_on_selector_all("#content option", "o => o.map(x => x.textContent)") if l.startswith("코스모 게이트(시즌")))
    settle(page)
    season_ui = page.evaluate("() => [document.getElementById('filters').hidden, document.querySelector('.stage-filter').hidden, document.getElementById('out').innerText.trim()]")
    assert season_ui[0] and season_ui[1] and season_ui[2] == "", "시즌 화면에 섹터·스테이지 선택이나 보스별 추천이 남아 있음: %r" % (season_ui,)
    shown = panel.is_visible()
    has_btn = page.locator('#cosmo-search button[data-cs="start"]').count()
    # 기본은 전수 탐색이라 시험에서만 풀을 12명으로 제한(maxPool)하고 저장된 이 PC 속도를 지운다
    page.evaluate("""() => {const S=D.cosmoRaid.search;S.maxPool=12;S.screen.runs=1;S.rerank.keep=40;S.rerank.runs=2;S.combine.topTriples=3;S.final.runs=2;try{localStorage.removeItem('pn.cosmo.speed')}catch(e){}}""")
    page.select_option('#cosmo-search select[data-cs="level"]', "3")
    lvl = page.eval_on_selector('#cosmo-search select[data-cs="level"]', "s => s.value")
    # 시작 전 안내: 이 PC 속도를 모르면 «시작하면 몇 초 뒤 예상 시간이 표시됩니다»
    pre0 = page.locator('#cosmo-search [data-k="cs-eta-pre"]').all_text_contents()
    pre0_ok = len(pre0) == 1 and "시작하면 몇 초 뒤 예상 시간이 표시됩니다" in pre0[0]
    # 취소: 진행 표시가 보이면 눌러 처음 상태로 돌아가고, 잠시 뒤에도 결과가 끼어들지 않아야 함
    page.click('#cosmo-search button[data-cs="start"]')
    page.wait_for_selector('#cosmo-search [data-k="cs-progress"]', timeout=30000)
    eta_run = page.locator('#cosmo-search [data-k="cs-eta"]').all_text_contents()
    eta_run_ok = len(eta_run) == 1 and "남은 시간" in eta_run[0]
    # 진행 갱신 때 취소 버튼을 다시 만들지 않음(같은 요소가 유지되는지)
    page.evaluate("""() => { window.__cancelBtn = document.querySelector('#cosmo-search button[data-cs="cancel"]') }""")
    page.wait_for_timeout(600)
    keep_btn = page.evaluate("""() => CSR.phase !== 'run' || document.querySelector('#cosmo-search button[data-cs="cancel"]') === window.__cancelBtn""")
    page.click('#cosmo-search button[data-cs="cancel"]')
    page.wait_for_selector('#cosmo-search button[data-cs="start"]', timeout=5000)
    page.wait_for_timeout(1500)
    cancel_ok = page.evaluate("() => CSR.phase === 'idle' && !CSR.handle") and page.locator('#cosmo-search [data-k="cs-table"]').count() == 0
    # 실제 완주
    page.click('#cosmo-search button[data-cs="start"]')
    page.wait_for_selector('#cosmo-search [data-k="cs-table"], #cosmo-search [data-k="cs-err"]', timeout=300000)
    err_txt = page.locator('#cosmo-search [data-k="cs-err"]').all_text_contents()
    assert not err_txt, err_txt
    rows = page.locator('#cosmo-search [data-k="cs-best"] [data-k="cs-team"]').count()
    state = page.evaluate("""() => { const r = CSR.rows[0]; const keys = r.teams.flatMap(t => t.keys);
      return {n: CSR.rows.length, bosses: r.teams.map(t => t.boss), uniq: new Set(keys).size, nkeys: keys.length, sum: r.sum,
              parts: r.teams.reduce((a, t) => a + CosmoSearch.metric(t.st, CSR.mode), 0), level: CSR.level, phase: CSR.phase,
              shown: document.querySelector('[data-k=cs-sum]').textContent.replace(/,/g, '')} }""")
    names = page.locator('#cosmo-search [data-k="cs-best"] .cs-bh > b').all_text_contents()[:3]
    # 완주하면 이 PC 속도가 저장되고, 끝난 화면의 시작 전 안내가 «예상 약 …»(저장 속도 기준)으로 바뀜
    speed = page.evaluate("() => { try { return JSON.parse(localStorage.getItem('pn.cosmo.speed')) } catch (e) { return null } }")
    want_w = page.evaluate("() => csWorkers()")        # 작업자 수 자동 결정(코어·메모리·모바일): 저장된 속도의 작업자 수와 같아야 하고 코어 수를 넘지 않음
    cores = page.evaluate("() => navigator.hardwareConcurrency || 4")
    speed_ok = bool(speed) and len(speed.get("sec", [])) == 4 and all(x > 0 for x in speed["sec"]) and speed.get("workers", 0) > 0 and speed["workers"] == want_w and 1 <= want_w <= cores
    pre1 = page.locator('#cosmo-search [data-k="cs-eta-pre"]').all_text_contents()
    pre1_ok = len(pre1) == 1 and "지난 실행 속도 기준 예상 약" in pre1[0]
    # 추천 제외 목록이 바뀌면 «낡은 결과»
    old0 = page.locator('#cosmo-search [data-k="cs-old"]').count()
    page.evaluate("() => { EXCL.add(R[0].key); renderCosmoSearch() }")
    old1 = page.locator('#cosmo-search [data-k="cs-old"]').count()
    page.evaluate("() => { EXCL.delete(R[0].key); renderCosmoSearch() }")
    old2 = page.locator('#cosmo-search [data-k="cs-old"]').count()
    # 난이도를 바꾸면 낡은 결과 경고
    page.select_option('#cosmo-search select[data-cs="level"]', "4")
    stale = page.locator('#cosmo-search [data-k="cs-stale"]').count()
    choose(page, "작전 (일반)", "36")
    hidden_after = not panel.is_visible()
    errs = list(ctx.errors)
    page.close()
    ok = (hidden_first and shown and has_btn == 1 and lvl == "3" and cancel_ok and rows == 3
          and state["bosses"] == ["belgras", state["bosses"][1], state["bosses"][2]] and len(set(state["bosses"])) == 3 and len(set(names)) == 3
          and state["nkeys"] == 12 and state["uniq"] == 12 and state["sum"] > 0 and abs(state["sum"] - state["parts"]) < 1e-6
          and state["shown"] == str(round(state["sum"])) and state["level"] == 3 and state["phase"] == "done"
          and stale == 1 and hidden_after and not errs
          and pre0_ok and eta_run_ok and keep_btn and speed_ok and pre1_ok and (old0, old1, old2) == (0, 1, 0))
    return ok, "처음 숨김 %s / 코스모 표시 %s / 취소 %s / 표 %d줄 %s / 12명 중복 없음 %s / 합계 %s / 낡은 경고 %d / 숨김 %s / 오류 %s / 시작 전 안내 %s %s / 남은 시간 칸 %s %s / 취소 버튼 유지 %s / 속도 저장 %s / 낡은 결과 %s" % (
        hidden_first, shown, cancel_ok, rows, names, state["uniq"] == 12, state["sum"], stale, hidden_after, errs[:2],
        pre0_ok, pre0[:1], eta_run_ok, eta_run[:1], keep_btn, speed_ok, (old0, old1, old2))


def test_cosmo_auto_level(browser, ctx):
    """코스모 난이도 «자동»(기본값) 실제 화면 경로: 기본 선택이 자동이고, 끝까지 돌아 오류 없이 «점수가 가장 높은 난이도»가 표시됨.
    (2026-11-08: 화면이 levelMax 를 안 넘겨 35분 계산 뒤 오류가 난 사고 — 시험이 화면 호출을 안 거쳐 놓쳤음)"""
    ctx.errors.clear()
    page = open_page(browser, ctx, raid_ui=True)
    page.select_option("#content", label=next(l for l in page.eval_on_selector_all("#content option", "o => o.map(x => x.textContent)") if l.startswith("코스모 게이트(시즌")))
    settle(page)
    page.evaluate("""() => {const S=D.cosmoRaid.search;S.maxPool=12;S.screen.runs=1;S.rerank.keep=40;S.rerank.runs=2;S.combine.topTriples=3;S.final.runs=2;S.auto.probeRuns=1;try{localStorage.removeItem('pn.cosmo.speed')}catch(e){}}""")
    default_auto = page.eval_on_selector('#cosmo-search select[data-cs="level"]', "s => s.value") == "-1"
    page.click('#cosmo-search button[data-cs="start"]')
    page.wait_for_selector('#cosmo-search [data-k="cs-table"], #cosmo-search [data-k="cs-err"]', timeout=300000)
    err_txt = page.locator('#cosmo-search [data-k="cs-err"]').all_text_contents()
    assert not err_txt, err_txt
    info = page.locator('#cosmo-search [data-k="cs-level"]').all_text_contents()
    lv = page.evaluate("() => [CSR.level, CSR.reqLevel, (CSR.probe || []).length, D.cosmoRaid.levelMax, CSR.rows[0].teams.map(t => t.level)]")
    stale = page.locator('#cosmo-search [data-k="cs-stale"]').count()
    # 기존 추천 양식: 보스마다 카드 4장(전열 2·후열 2), 리더 왕관 1개, 난이도 표시, 브레이크 스킬 줄
    shape = page.evaluate("""() => [...document.querySelectorAll('#cosmo-search [data-k="cs-best"] [data-k="cs-team"]')].map(b => ({
      cards: b.querySelectorAll('.gc').length, front: b.querySelectorAll('.slotlbl.front').length, back: b.querySelectorAll('.slotlbl.back').length,
      crown: b.querySelectorAll('.crown').length, imgs: b.querySelectorAll('.gc img, .gc .fallback').length, bbar: b.querySelectorAll('.bbar').length,
      lvtxt: (b.querySelector('.cs-lv') || {}).textContent || ''}))""")
    shape_ok = len(shape) == 3 and all(x["cards"] == 4 and x["front"] == 2 and x["back"] == 2 and x["crown"] == 1 and x["bbar"] == 1 and x["imgs"] >= 4 and x["lvtxt"].startswith("난이도 ") for x in shape)
    ok = (default_auto and len(info) == 1 and "보스마다" in info[0] and lv[1] == -1 and lv[0] is None and lv[2] == lv[3] + 1 and all(0 <= x <= lv[3] for x in lv[4])
          and shape_ok and stale == 0 and not ctx.errors)
    return ok, "기본 자동 %s / 안내 %s / 보스별 난이도 %s 요청 %s 비교 %d개(최대 %s) / 카드 양식 %s %s / 낡은 경고 %d / 오류 %s" % (default_auto, info[:1], lv[4], lv[1], lv[2], lv[3], shape_ok, shape[:1], stale, ctx.errors[:2])


def test_assumed_growth(browser, ctx):
    """Real Pyodide: checkbox -> owned search -> one-savior stage -> comparison table.

    Only SYNTH supplies account values. Its intentionally absent tactics fields
    are explicitly zeroed in memory to exercise the strict missing-data gate.
    PN_DISABLE_ASSUMED=1 deliberately disconnects the feature; this test MUST fail.
    """
    page = open_page(browser, ctx, info=SYNTH)
    choose(page, '작전 (일반)', 'SECTOR 1-3')
    page.evaluate('''async () => {
      const info=JSON.parse(JSON.stringify(MI.info));
      for(const group of Object.keys(MI.growth.tactics))info.tactics.groups[group]={level:0,attack:0,defense:0,hp:0};
      await miApply(info);window.assumedOriginal=JSON.stringify(info);
    }''')
    settle(page)
    if os.environ.get('PN_DISABLE_ASSUMED') == '1':
        page.evaluate('growthMaybe=()=>{}')
    page.click('#tab-info')
    assert page.locator('label:has(#assume-growth)').inner_text().strip() == '육성 가이드(미보유·덜 키운 구원자 가정)'
    assert page.locator('label:has(#assume-equipment)').inner_text().strip() == '장비 가정(가이드 기본 세트 +15)'
    page.check('#assume-growth')
    page.check('#assume-equipment')
    page.click('#tab-reco')
    page.click('button[data-go]')
    page.wait_for_function("() => GROW.phase==='done'||GROW.phase==='error'", timeout=240000)
    assert page.evaluate("GROW.phase") == 'done', page.evaluate('GROW.msg')
    page.wait_for_selector('[data-k="growth-table"]')
    result = page.evaluate('''() => ({
      runs:GROW.result.runs, ms:GROW.result.ms, scope:GROW.result.scope,
      rows:GROW.result.rows.filter(r=>r.result).slice(0,5).map(r=>({key:r.key,kind:r.kind,clear:r.result.clear,
        prog:r.result.prog,n:r.result.n,delta:r.delta,ci:r.ci})),
      baseline:GROW.result.baseline,
      owned:JSON.stringify(MI.info)===window.assumedOriginal,
      one:GROW.result.rows.filter(r=>r.team).every(r=>r.team.party.units.filter(u=>
        u.key===r.key).length===1&&r.team.party.units.every(u=>u.stats_final&&u.build==='none')),
      history:localStorage.getItem('pn.growth.history')
    })''')
    assert result['runs'] > 0 and result['runs'] <= 7200, result
    assert result['scope']['evaluated'] > 0 and result['rows'], result
    assert all(r['prog'] > 0 and r['n'] == result['baseline']['n'] for r in result['rows']), result
    assert result['owned'] and result['one'], result
    assert page.locator('[data-k="assumed-badge"]').count() == 1
    assert result['history'] and 'progs' not in result['history'] and 'item_id' not in result['history']
    # Full share payload must remain the original account, while options travel in search.
    shared = page.evaluate('''async () => {const url=await shareUrlMi();
      const u=new URL(url),decoded=await MyInfoImport.fromHash(u.hash.replace('#shared=','#myinfo='));
      return {same:JSON.stringify(decoded)===window.assumedOriginal,ag:u.searchParams.get('ag'),ae:u.searchParams.get('ae')};}''')
    assert shared == dict(same=True, ag='1', ae='1'), shared
    # Shared mode storage guard uses the actual page completion path's helper.
    unchanged = page.evaluate('''() => {const old=LS.get('growth.history');MI.shared=true;
      const entry=GrowthGuide.summary(GROW.result,'op/shared/test','new',MI.hash,'other');
      GrowthGuide.save(LS,MI.shared,entry);MI.shared=false;
      return JSON.stringify(old)===JSON.stringify(LS.get('growth.history'));}''')
    assert unchanged
    # Deadline covers candidate generation too; no quick/combination work after expiry.
    assert page.evaluate('''async () => {const c=contents[$('content').value],st=cur[$('stage').value];
      const targets=await growthCandidates(c,st,()=>true,Date.now()-1);
      return targets.length>0&&targets.every(t=>t.limited&&t.candidates.length===0);}''')
    page.screenshot(path=os.path.join(ctx.shots, 'assumed_growth.png'), full_page=True)
    with open(os.path.join(ctx.shots, 'assumed_measurement.json'), 'w', encoding='utf8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    # Complete an actual shared-account search; completion must not write local history.
    saved_history = page.evaluate("localStorage.getItem('pn.growth.history')")
    page.evaluate('''async () => {await miApply(JSON.parse(JSON.stringify(MI.info)),{shared:true});condChanged();showReco();}''')
    page.wait_for_function("GROW.phase==='done'||GROW.phase==='error'", timeout=240000)
    assert page.evaluate("GROW.phase==='done' && Object.keys(GROW.history).length>0")
    assert page.evaluate("localStorage.getItem('pn.growth.history')") == saved_history
    page.evaluate('MI.shared=false')
    page.click('#tab-info')
    page.uncheck('#assume-growth')
    page.uncheck('#assume-equipment')
    assert page.evaluate("GROW.phase==='idle' && GROW.result===null && SIMQ.busy===null")
    page.click('#mi-panel-clear')
    assert page.evaluate("localStorage.getItem('pn.growth.history')===null")
    assert not ctx.errors, ctx.errors
    return True, '합성 계정 1-3: %.1f초 / %d판 / 평가 %s명 / 원본·출처·공유·기록 삭제' % (result['ms']/1000, result['runs'], result['scope']['evaluated'])


def test_assumed_manual(browser, ctx):
    page = open_page(browser, ctx, info=SYNTH)
    choose(page, '작전 (일반)', 'SECTOR 1-3')
    page.evaluate('''async () => {const info=JSON.parse(JSON.stringify(MI.info));
      for(const k of Object.keys(MI.growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
      await miApply(info);setMode('manual',true);condChanged();}''')
    settle(page)
    page.click('#tab-info')
    page.check('#assume-equipment')
    page.click('#tab-reco')
    page.click('button[data-go]')
    page.wait_for_function("GROW.phase==='done'||GROW.phase==='error'", timeout=240000)
    assert page.evaluate('''() => {const r=GROW.result;return r&&r.runs<=7200&&r.baseline.n===100&&
      r.rows.some(x=>x.result)&&r.rows.filter(x=>x.result).every(x=>x.result.n===100&&x.result.prog>0&&
        x.result.prog===x.result.man.prog&&x.result.progs.length===100);}''')
    # In-flight invalidation: a new option change must discard the entire scenario.
    page.evaluate('''() => {growthCancel();growthStart(contents[$('content').value],cur[$('stage').value]);}''')
    page.click('#tab-info')
    page.uncheck('#assume-equipment')
    settle(page)
    assert page.evaluate("GROW.result===null&&GROW.phase==='idle'&&SIMQ.busy===null")
    assert not ctx.errors, ctx.errors
    return True, '수동 진행도·100판 재평가·정책 탐색 판수 상한·진행 중 무효화'


def test_assumed_corridor(browser, ctx):
    page = open_page(browser, ctx, info=SYNTH)
    page.select_option('#content', value=page.evaluate("String(contents.findIndex(c=>c.key==='clo'))"))
    settle(page)
    page.select_option('#tab', label='달 회랑')
    settle(page)
    page.select_option('#stage', value=page.evaluate("String(cur.findIndex(s=>s.name==='FLOOR 100'))"))
    settle(page)
    page.evaluate('''async () => {const info=JSON.parse(JSON.stringify(MI.info));
      for(const k of Object.keys(MI.growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
      await miApply(info);}''')
    settle(page)
    page.click('#tab-info')
    page.check('#assume-growth')
    page.click('#tab-reco')
    page.click('button[data-go]')
    page.wait_for_function("GROW.phase==='done'||GROW.phase==='error'", timeout=240000)
    result = page.evaluate('''() => {const r=GROW.result;return r&&{baseline:r.baseline,runs:r.runs,ms:r.ms,
      rows:r.rows.filter(x=>x.result).map(x=>({key:x.key,n:x.result.n,prog:x.result.prog,delta:x.delta,
        valid:x.team.party.units.every(u=>BYKEY[u.key].el==='moon')&&x.team.party.units.filter(u=>
          miProfile().units[u.key]).length===3}))};}''')
    assert result and result['baseline'] is None and result['runs'] > 0, result
    assert result['rows'] and all(r['valid'] and r['delta'] is None and r['n'] == 100 for r in result['rows']), result
    assert any(r['prog'] > 0 for r in result['rows']), result
    assert page.locator('[data-k="growth-table"]').count() == 1
    assert not ctx.errors, ctx.errors
    return True, '합성 계정 달 회랑 100: %.1f초 / %d판 / 보유 3명+가정 1명·속성 제한·기준 없음' % (result['ms']/1000, result['runs'])


TESTS = [test_assumed_growth, test_assumed_manual, test_assumed_corridor, test_load_no_errors, test_quick_default, test_quick_owned_small, test_browser_sim,
         test_browser_sim_blocked, test_sim_auto_and_override, test_manual_mode, test_cosmo_joint, test_rekindle_ui, test_mobile_layout, test_python_js_topk_parity]
TESTS.append(test_cosmo_auto_level)
TESTS.append(test_guild_search)
TESTS.append(test_request_diagnostics)
TESTS.append(test_sim_timeout_partial)
TESTS.append(test_guild_search_dropped)
TESTS.append(test_guild_season_rollover)
TESTS.append(test_break_skill_select)
TESTS.append(test_break_skill_compare)
TESTS.append(test_break_compare_cancel_after_team_change)
TESTS.append(test_gimmick_slot_owned)
TESTS.append(test_gimmick_avoid)
TESTS.append(test_boss_gimmick_mobile)
TESTS.extend([test_myinfo_required, test_myinfo_import_clear, test_myinfo_use_toggle, test_myinfo_rules_mobile, test_myinfo_sim])
TESTS.extend([test_share_link, test_sim_runs, test_press_to_compute])
TESTS.extend([test_skill_view, test_skill_retry])
def test_myinfo_level_compat(browser, ctx):
    """Legacy warning, source boundary, and unknown-slot warning in the real UI."""
    ctx.errors.clear()
    page = open_page(browser, ctx, info=os.path.join(FIXTURES, 'myinfo_legacy.json'))
    choose(page, '작전 (일반)', 'SECTOR 1-3')
    page.click('#tab-info')
    assert '구원자별 레벨 없음 · 다시 불러오기 권장' in page.inner_text('#mi-meta')
    assert all(t == 'Lv120' for t in page.locator('#mi-list .mi-level').all_text_contents())
    updated = json.loads(open(SYNTH, encoding='utf-8').read())
    updated['star_link_level'] = updated['star_link']['level'] = 201
    updated['star_link']['slots'].append(dict(index=99, id=900099))
    page.evaluate('(info) => miApply(info)', updated)
    page.wait_for_function('() => !MI.pending && !!MI.growth')
    assert '구원자별 레벨 없음' not in page.inner_text('#mi-meta')
    assert '스타링크 슬롯 구원자 정보 없음' in page.inner_text('#mi-meta')
    assert page.locator('#mi-list [data-uid="1001"] .mi-level').inner_text() == 'Lv201'
    assert page.locator('#mi-list [data-uid="1001"] .mi-link').inner_text() == '스타링크 · 소스'
    page.click('#mi-list button[data-mi-sheet="1001"]')
    page.wait_for_selector('#mi-dlg .mi-level')
    assert page.locator('#mi-dlg .mi-level').inner_text() == 'Lv201'
    assert page.locator('#mi-dlg .mi-link').inner_text() == '스타링크 · 소스'
    assert not ctx.errors, ctx.errors
    page.close()
    return True, '옛 형식 경고·201 소스·슬롯 경고·상세 실효 레벨'


TESTS.extend([test_myinfo_full, test_myinfo_level_compat])
TESTS.append(test_graph_evidence)
TESTS.append(test_equip_goal_option)
TESTS.append(test_guild_defense)
TESTS.append(test_cosmo_search)


def main():
    args = sys.argv[1:]
    shots = None
    if "--shots" in args:
        i = args.index("--shots")
        shots = args[i + 1]
        del args[i:i + 2]
    selected = [t for t in TESTS if not args or any(x in t.__name__ for x in args)]
    if not selected:
        print("FAIL: 시험 필터에 일치하는 항목 없음")
        return 1
    if not shots:
        shots = tempfile.mkdtemp(prefix="pn_shots_")
    os.makedirs(shots, exist_ok=True)
    low_priority()
    from playwright.sync_api import sync_playwright
    ok_all = True
    with test_server() as base:
        print("서버 PID %d %s, 스크린샷 %s" % (os.getpid(), base, shots), flush=True)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                for t in selected:
                    ctx = Ctx(base, shots)
                    try:
                        ok, msg = t(browser, ctx)
                    except Exception as ex:
                        ok, msg = False, "오류: %r (줄 %s)" % (ex, [f.lineno for f in traceback.extract_tb(ex.__traceback__) if f.filename == __file__][-1])
                    finally:
                        # Also close pages/workers left behind when an assertion or navigation fails.
                        pending = list(ctx.requests.values())
                        network = list(ctx.network)
                        for context in browser.contexts:
                            context.close()
                    if not ok:
                        msg += " / 콘솔 %s / 실패 요청 %s / 미완료 요청 %s" % (ctx.errors, network, pending)
                        with open(os.path.join(shots, t.__name__ + "_network.json"), "w", encoding="utf-8") as f:
                            json.dump({"base": base, "errors": ctx.errors, "failed": network, "pending": pending}, f, ensure_ascii=False, indent=2)
                    print("%s %s - %s" % ("PASS" if ok else "FAIL", t.__name__, msg), flush=True)
                    ok_all = ok_all and ok
            finally:
                browser.close()
    print("ALL", "OK" if ok_all else "FAILED")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
