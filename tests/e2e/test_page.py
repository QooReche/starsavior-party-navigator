# -*- coding: utf-8 -*-
"""웹 페이지(index.html) 실제 브라우저 시험(Playwright + Chromium).

준비(저장소 밖 가상환경, C: 용량 문제로 브라우저도 E: 에):
  python -m venv E:\\AI_mk2\\venv-pw
  E:\\AI_mk2\\venv-pw\\Scripts\\python -m pip install playwright
  set PLAYWRIGHT_BROWSERS_PATH=E:\\AI_mk2\\pw-browsers
  E:\\AI_mk2\\venv-pw\\Scripts\\python -m playwright install chromium
실행(저장소 폴더에서, index.html·data/sim 이 만들어진 상태):
  E:\\AI_mk2\\venv-pw\\Scripts\\python -X utf8 tests\\e2e\\test_page.py [--shots 폴더] [이름 일부 ...]

스스로 127.0.0.1 의 빈 포트에 `python -m http.server` 를 띄우고 끝나면 그 PID 만 끈다. 이 프로세스와 자식(서버·브라우저)은
낮은 우선순위(Idle)로 돈다. 스크린샷 기본 저장 위치 = E:\\AI_mk2\\work\\p4\\shots(없으면 저장소 밖 임시 폴더)."""
import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
if os.path.isdir(r"E:\AI_mk2\pw-browsers"):
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", r"E:\AI_mk2\pw-browsers")


def low_priority():
    try:
        if os.name == "nt":
            import ctypes
            k = ctypes.windll.kernel32
            k.SetPriorityClass(k.GetCurrentProcess(), 0x40)
        else:
            os.nice(19)
    except Exception:
        pass


def free_port():
    """빈 포트. 크롬이 막는 포트(5060·5061·6000·6665~6669 등)를 피하려고 10100 이상만 쓴다."""
    while True:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]
        s.close()
        if p >= 10100:
            return p


class Ctx:
    def __init__(self, base, shots):
        self.base, self.shots = base, shots
        self.errors = []


def attach(page, ctx):
    page.on("console", lambda m: ctx.errors.append("console: " + m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: ctx.errors.append("pageerror: %s" % e))


def settle(page):
    """디바운스(150ms)가 끝날 때까지"""
    page.wait_for_timeout(450)


def choose(page, content, query):
    page.select_option("#content", label=content)
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


def open_page(browser, ctx, query="", viewport=None, legacy=None):
    """legacy 는 옛 사전 계산 화면용 인자(퇴역, 무시)"""
    page = browser.new_page(viewport=viewport or {"width": 1280, "height": 900})
    attach(page, ctx)
    page.goto(ctx.base + "/index.html" + query)
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
    return page.evaluate("""p => [...document.querySelectorAll('.party[data-party="'+p+'"] .qbox .qrow[data-key]')].map(r => [r.dataset.key, r.querySelector('.qv').className.split(' ')[1], r.innerText])""", party)


def test_quick_default(browser, ctx):
    """새 기본: 맨 위 「이 스테이지 추천(빠른 계산)」에 1안+차선, 아래 상세 팀 = 1안, 콘솔 오류 0"""
    ctx.errors.clear()
    page = open_page(browser, ctx, legacy=False)
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


def test_quick_owned_small(browser, ctx):
    """보유를 6명으로 줄여도 빠른 계산 추천이 뜸(옛 문제 「시뮬 없음」 해소), 추천 팀은 보유 안에서만"""
    page = open_page(browser, ctx, legacy=False)
    choose(page, "코스모 게이트", "길레 2단계")
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow')
    keep = page.evaluate("() => Object.keys(window.PN_Q_SV()).filter(k => !k.includes('@')).slice(0, 6)")
    page.click("#dbtn")
    page.click("#none")
    for k in keep:
        page.click('#own label.tile:has(input[data-k="%s"])' % k)
    page.click("#dclose")
    settle(page)
    rows = quick_rows(page)
    inside = all(set(r[0].split(",")) <= set(keep) for r in rows)
    page.click("#dbtn")
    page.click("#all")
    page.keyboard.press("Escape")
    page.close()
    return len(rows) >= 1 and inside, "보유 6명 -> %d안, 보유 안 %s, 1안 판정 %s" % (len(rows), inside, rows and rows[0][1])


def test_quick_growth(browser, ctx):
    """육성 가정을 바꾸면 가정 전투력이 바뀌고, 어려운 스테이지는 「권장의 약 N%면 깸」을 보여 줌"""
    page = open_page(browser, ctx, legacy=False)
    choose(page, "코스모 게이트", "길레 1단계")
    h1 = page.inner_text('.party[data-party="1"] .qbox .qh')
    page.select_option("#grow", "0.8")
    settle(page)
    h2 = page.inner_text('.party[data-party="1"] .qbox .qh')
    page.select_option("#grow", "1")
    settle(page)
    page.click("#optbox summary")
    page.fill("#mypow", "20000")
    settle(page)
    rows = quick_rows(page)
    page.fill("#mypow", "")
    page.evaluate("() => { localStorage.removeItem('pn.pow'); localStorage.removeItem('pn.grow') }")
    page.close()
    need = rows and rows[0][1] == "hard" and "권장의" in rows[0][2] and "면 깸" in rows[0][2]
    return h1 != h2 and "20,000" not in h1 and bool(need), "가정 문구 바뀜 %s / 전투력 20,000 일 때 1안 %s %s" % (
        h1 != h2, rows and rows[0][1], rows and " ".join(rows[0][2].split())[:80])


def test_savior_power(browser, ctx):
    """서랍에 구원자별 전투력을 넣으면 빠른 계산에 반영(가정 줄에 「N명 반영」, 1안 전투력 바뀜), 저장·삭제"""
    page = open_page(browser, ctx, legacy=False)
    choose(page, "코스모 게이트", "길레 2단계")
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow')
    h1 = page.inner_text('.party[data-party="1"] .qbox .qh')
    k = quick_rows(page)[0][0].split(",")[0]
    page.click("#dbtn")
    page.fill('#pwl input[data-pk="%s"]' % k, "90000")
    page.click("#dclose")
    settle(page)
    h2 = page.inner_text('.party[data-party="1"] .qbox .qh')
    saved = page.evaluate("() => JSON.parse(localStorage.getItem('pn.pw') || '{}')")
    page.click("#dbtn")
    page.fill('#pwl input[data-pk="%s"]' % k, "")
    page.click("#dclose")
    settle(page)
    h3 = page.inner_text('.party[data-party="1"] .qbox .qh')
    page.close()
    ok = "1명 반영" in h2 and "반영" not in h1 and h2 != h1 and saved.get(k) == 90000 and "반영" not in h3
    return ok, "입력 전 %s / 입력 후 %s / 저장 %s / 지운 뒤 %s" % ("반영" in h1, "1명 반영" in h2, saved.get(k), "반영" in h3)


def test_browser_sim(browser, ctx):
    """「위 3팀 시뮬로 확인」: Pyodide 로 파이썬 엔진을 돌려 3팀 모두 클리어 확률·95% 구간 표시, 콘솔 오류 0, 이 사이트 밖 요청 0"""
    ctx.errors.clear()
    page = open_page(browser, ctx, legacy=False)
    ext = []      # 엔진을 이 사이트 밖에서 받으면 안 된다(lib/pyodide, 2026-10-21)
    page.context.on("request", lambda r: ext.append(r.url) if not r.url.startswith(ctx.base) and not r.url.startswith("data:") and not r.url.startswith("blob:") else None)
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow')
    n = len(quick_rows(page))
    t0 = time.time()
    page.click('.party[data-party="1"] button[data-sim="1"]')
    page.wait_for_function("n => document.querySelectorAll('.party[data-party=\"1\"] .qsim').length >= n", arg=n, timeout=300000)
    dt = time.time() - t0
    txt = page.inner_text('.party[data-party="1"] .qsim')
    state = page.inner_text('.party[data-party="1"] [data-k="simstate"]')
    page.screenshot(path=os.path.join(ctx.shots, "desktop_browser_sim.png"), full_page=False)
    last = page.evaluate("() => { const L = window.PN_SIMQ.lastReq; return {req: L.req, res: Object.fromEntries(Object.entries(L.sigs).map(([k, s]) => [k, window.PN_SIMQ.res[s]]))} }")
    errs = list(ctx.errors)
    page.close()
    # 같은 입력·같은 시드로 이 PC 의 파이썬 엔진을 돌려 브라우저(Pyodide) 결과와 대조
    from battlesim import web
    same = []
    for t in last["req"]["teams"]:      # 브라우저와 같은 진입점·옵션(표준 육성·엔진 역보정)으로 이 PC 에서 다시 돌림
        opt = dict(last["req"]["options"], **t.get("options", {}))
        opt['rules_override'] = dict(last["req"]["options"].get('rules_override', {}), **t.get('options', {}).get('rules_override', {}))
        r = json.loads(web.run_auto(last["req"]["stage"], t["party"], last["req"]["n_runs"], last["req"]["seed"], json.dumps(opt)))
        b = last["res"][t["key"]]
        same.append(r["clear"] == b["clear"] and r["ttk"] == b["ttk"] and r["u"] == b["u"] and r['bs'] == b['bs'])
    # 화면이 시뮬에 넘긴 스탯 = 계수 맞춤 표본(tools/gen_quick_calib.party_spec)이 쓰는 스탯(기본 육성 가정 1.0, codex 차단 3)
    import gen_quick_calib as G
    from battlesim import quick as Q
    q, pen = Q.load(ROOT)
    ck, tab, name = last["req"]["stage"].split("/", 2)
    st = q["st"][ck][tab + "|" + name]
    spec_same = []
    for t in last["req"]["teams"]:
        so = [u["key"] for u in t["party"]["units"]]           # 시뮬 칸(전열1, 전열2, 후열1, 후열2)
        order = [so[2], so[0], so[1], so[3]]                     # -> 화면 카드 순서(후열1, 전열1, 전열2, 후열2)
        lead = so[t["party"]["leader"]] if t["party"]["leader"] is not None else None
        ps = G.party_spec(q, pen, order, lead, t["key"].split(","), 1.0, st)
        spec_same.append(ps["units"] == t["party"]["units"] and ps["leader"] == t["party"]["leader"])
    ok = "클리어" in txt and "95% 구간" in txt and "완료" in state and not errs and all(same) and len(same) == n and all(spec_same) and not ext
    txt = txt + " / 바깥 요청 %s" % ext[:3]
    txt = txt + " / 입력 같음 %s" % spec_same
    txt = txt + " / 파이썬과 같음 %s" % same
    return ok, "%d팀 %.0f초 / 파이썬 결과 같음 %s / 입력 같음 %s / %s / 오류 %s" % (n, dt, same, spec_same, " ".join(txt.split())[:60], errs[:2])


def test_browser_sim_blocked(browser, ctx):
    """엔진 내려받기가 막히면 「시뮬 실패 · 다시 시도」, 빠른 계산 추천은 그대로(codex 안전장치 2)"""
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    attach(page, ctx)
    page.route("**/lib/pyodide/**", lambda r: r.abort())
    page.context.route("**/lib/pyodide/**", lambda r: r.abort())
    page.goto(ctx.base + "/index.html")
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow')
    n = len(quick_rows(page))
    page.click('.party[data-party="1"] button[data-sim="1"]')
    page.wait_for_function("() => /시뮬 실패/.test((document.querySelector('[data-k=\"simstate\"]')||{}).textContent||'')", timeout=120000)
    retry = page.locator('.party[data-party="1"] button[data-sim="1"]').count()
    n2 = len(quick_rows(page))
    page.close()
    ctx.errors.clear()
    return retry == 1 and n2 == n, "실패 표시 + 다시 시도 버튼 %d, 빠른 계산 %d안 유지 %s" % (retry, n2, n2 == n)


def test_sim_auto_and_override(browser, ctx):
    """한 번 시뮬을 누르면 다음 스테이지부터 자동 확인, 시뮬 결과가 있으면 판정 배지가 시뮬 기준(title)으로 바뀜, 「자동 확인 끄기」"""
    page = open_page(browser, ctx, legacy=False)
    page.wait_for_selector('.party[data-party="1"] .qbox .qrow[data-key]')
    page.click('.party[data-party="1"] button[data-sim="1"]')
    page.wait_for_function("() => document.querySelectorAll('.party[data-party=\"1\"] .qsim').length >= 3", timeout=300000)
    choose(page, "작전 (일반)", "SECTOR 1-2")
    page.wait_for_function("() => /완료/.test((document.querySelector('.party[data-party=\"1\"] [data-k=\"simstate\"]')||{}).textContent||'')", timeout=300000)
    auto = page.locator('.party[data-party="1"] .qsim').count()
    titles = page.evaluate("() => [...document.querySelectorAll('.party[data-party=\"1\"] .qrow[data-key] .qv[title]')].map(e => e.title)")
    off = page.locator('button[data-simauto="0"]').count()
    if off:
        page.click('button[data-simauto="0"]')
    flag = page.evaluate("() => localStorage.getItem('pn.simauto')")
    page.close()
    ok = auto >= 1 and titles and all(t == "전투 시뮬 기준" for t in titles) and off == 1 and flag == "0"
    return ok, "자동 시뮬 %d팀, 배지 기준 %s, 끄기 버튼 %d, 끈 뒤 저장값 %s" % (auto, titles[:3], off, flag)


def test_load_no_errors(browser, ctx):
    """처음 열면 콘솔 오류 0, 추천 카드(1안+차선)와 상세 카드 4장, 옛 사전 계산 파일(data/sim)을 부르지 않음"""
    ctx.errors.clear()
    reqs = []
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    attach(page, ctx)
    page.on("request", lambda r: reqs.append(r.url))
    page.goto(ctx.base + "/index.html")
    page.wait_for_selector("#out .party .qbox .qrow[data-key]")
    settle(page)
    n = len(quick_rows(page))
    cards = page.locator('.party[data-party="1"] .rowcards .gc').count()
    old = [u for u in reqs if "/data/sim/" in u]
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
    page.wait_for_function("() => /완료/.test((document.querySelector('.party[data-party=\"1\"] [data-k=\"simstate\"]')||{}).textContent||'')", timeout=300000)
    page.wait_for_timeout(300)
    seq = page.locator('.party[data-party="1"] .seq[data-state="ok"]').count()
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
    page.wait_for_function("""() => [1, 2].every(p => /완료/.test((document.querySelector('.party[data-party="' + p + '"] [data-k="simstate"]') || {}).textContent || ''))""", timeout=600000)
    page.wait_for_timeout(300)
    u1 = page.get_attribute('.party[data-party="1"]', "data-team")
    u2 = page.get_attribute('.party[data-party="2"]', "data-team")
    page.evaluate("() => localStorage.removeItem('pn.simauto')")
    page.close()
    disjoint = bool(t1 and t2) and not (set(t1.split(",")) & set(t2.split(",")))
    after = bool(u1 and u2) and not (set(u1.split(",")) & set(u2.split(",")))
    return disjoint and after and "함께" in note and r2 >= 1, "파티1 %s / 파티2 %s 겹침 없음 %s, 시뮬 뒤 %s / %s 겹침 없음 %s, 함께 표시 %s" % (
        t1, t2, disjoint, u1, u2, after, "함께" in note)


def test_rekindle_ui(browser, ctx):
    """작전 재점화 버프: 고르면 머리말에 「재점화 버프 N단계 반영」, 빠른 계산 아군·적 피해 계수에 반영, 시뮬 옵션 rekindle, 다른 콘텐츠엔 안 붙음"""
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
    ok = ("재점화" not in h0 and "재점화 버프 3단계 반영" in h1 and opt.get("rekindle") == 3 and "rekindle" not in cz
          and saved == '"3"' and not errs)
    return ok, "전 %s / 후 %s / 시뮬 옵션 %s / 코스모 %s / 저장 %s / 오류 %s" % ("재점화" in h0, "3단계 반영" in h1, opt.get("rekindle"), cz.get("rekindle"), saved, errs[:2])


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
    page.evaluate("() => simAuto(false)")
    page.select_option(sel, '')
    stale = page.evaluate("""() => {const w=window.__bw[0],before=Object.keys(SIMQ.res).length;
      w.onmessage({data:{type:'team',id:w.req.id,key:w.req.teams[0].key,result:{clear:1}}});
      return w.stopped && Object.keys(SIMQ.res).length===before} """)
    page.click('button[data-sim="1"]')
    none_req = page.evaluate("() => window.__bw.at(-1).req")
    none_ok = next(t for t in none_req['teams'] if t['key'] == team_key)['options']['break_skill'] is None
    page.evaluate("""key => {simAuto(false);const w=window.__bw.at(-1);w.onmessage({data:{type:'team',id:w.req.id,key,
      result:{clear:0.5,ci:[0.4,0.6],n:100,bs:{name:null,uses:0,dmg:0,supported:false}}}})}""", team_key)
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
            const text = slot.name + ': ' + (actual.length
              ? '담당: ' + actual.map(key => BYKEY[key]?.name || key).join('·') : '✗ 없음');
            if (el.dataset.slot !== String(i) || el.textContent !== text ||
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
    page = open_page(browser, ctx)
    choose(page, "작전 (일반)", "SECTOR 5-10")
    keep = ["lydia-moon-caster", "gwen", "asherah-voyager", "smile"]
    page.click("#dbtn")
    page.click("#none")
    for key in keep:
        page.click('#own label.tile:has(input[data-k="%s"])' % key)
    page.click("#dclose")
    settle(page)
    team = page.get_attribute('.party[data-party="1"]', "data-team").split(",")
    row = page.locator('.party[data-party="1"] .gimrow[data-code="SELF_BUFF_DEPENDENT"]')
    text = row.text_content()
    no_dispel = page.evaluate("keys => keys.every(k => !BYKEY[k].gt.includes('DISPEL'))", keep)
    audit = gimmick_slot_audit(page)
    page.close()
    ok = (set(team) == set(keep) and no_dispel and "강화 해제: ✗ 없음" in text
          and "폭딜: 담당: " in text and "리디아" in text.split("폭딜: 담당: ")[-1]
          and audit["checked"] > 0 and audit["compared"] > 0 and not audit["errors"])
    return ok, "5-10 %s / 슬롯 대조 %s" % (text, audit)


def test_boss_gimmick_mobile(browser, ctx):
    """37-3: 슬롯별 태그·담당 대조, 모바일 배치·더 보기, 접힌 수동 서순에서 모드 전환."""
    page = open_page(browser, ctx, viewport={"width": 390, "height": 844})
    choose(page, "작전 (일반)", "37-3")
    box = page.locator('.party[data-party="1"] .gimbox')
    lines = box.locator(".gimlist > .gimrow")
    n = lines.count()
    txt = box.inner_text()
    severities = lines.evaluate_all("els => els.map(e => +e.dataset.severity)")
    all_n = box.locator(".gimrow").count()
    more = box.locator("details")
    folded = more.count() == 0 or not more.evaluate("e => e.open")
    if more.count():
        more.locator("summary").click()
    expanded_n = box.locator(".gimrow:visible").count()
    audit = gimmick_slot_audit(page)
    layout = page.evaluate('''() => {
      const cards = [...document.querySelectorAll('.party[data-party="1"] .card')].map(e => e.getBoundingClientRect());
      const button = document.querySelector('#dbtn').getBoundingClientRect();
      const faces = document.querySelector('.party[data-party="1"] .qrow .faces').getBoundingClientRect();
      return {sw:document.documentElement.scrollWidth, iw:innerWidth,
        cards:cards.length, same:cards.every(r => Math.abs(r.top-cards[0].top)<1),
        clear:button.bottom<=faces.top || button.top>=faces.bottom || button.right<=faces.left || button.left>=faces.right};
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
    ok = (3 <= n <= 5 and "보스" in txt and "(추정)" in txt
          and ("대응 미확인" in txt or "담당:" in txt)
          and severities == sorted(severities, reverse=True) and folded and expanded_n == all_n
          and audit["checked"] > 0 and audit["compared"] > 0 and not audit["errors"] and manual_ok
          and layout["sw"] <= layout["iw"] and layout["cards"] == 4 and layout["same"] and layout["clear"])
    return ok, "기믹 %d/%d줄, 심각도 %s, 더 보기 %s, 모바일 %s, 슬롯 %s, 수동 %s" % (n, all_n, severities, expanded_n == all_n, layout, audit, manual_ok)


TESTS = [test_load_no_errors, test_quick_default, test_quick_owned_small, test_quick_growth, test_savior_power, test_browser_sim,
         test_browser_sim_blocked, test_sim_auto_and_override, test_manual_mode, test_cosmo_joint, test_rekindle_ui, test_mobile_layout, test_python_js_topk_parity]
TESTS.append(test_break_skill_select)
TESTS.append(test_break_skill_compare)
TESTS.append(test_break_compare_cancel_after_team_change)
TESTS.append(test_gimmick_slot_owned)
TESTS.append(test_boss_gimmick_mobile)


def main():
    args = sys.argv[1:]
    shots = None
    if "--shots" in args:
        i = args.index("--shots")
        shots = args[i + 1]
        del args[i:i + 2]
    if not shots:
        shots = r"E:\AI_mk2\work\p4\shots" if os.path.isdir(r"E:\AI_mk2\work") else tempfile.mkdtemp(prefix="pn_shots_")
    os.makedirs(shots, exist_ok=True)
    low_priority()
    from playwright.sync_api import sync_playwright
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % port
    ok_all = True
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(base + "/index.html", timeout=1).close()
                break
            except Exception:
                time.sleep(0.2)
        print("서버 PID %d %s, 스크린샷 %s" % (srv.pid, base, shots), flush=True)
        ctx = Ctx(base, shots)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                for t in TESTS:
                    if args and not any(x in t.__name__ for x in args):
                        continue
                    try:
                        ok, msg = t(browser, ctx)
                    except Exception as ex:
                        ok, msg = False, "오류: %r" % (ex,)
                    print("%s %s - %s" % ("PASS" if ok else "FAIL", t.__name__, msg), flush=True)
                    ok_all = ok_all and ok
            finally:
                browser.close()
    finally:
        srv.terminate()      # 내가 띄운 서버 PID 만 종료
        try:
            srv.wait(timeout=5)
        except Exception:
            srv.kill()
    print("ALL", "OK" if ok_all else "FAILED")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
