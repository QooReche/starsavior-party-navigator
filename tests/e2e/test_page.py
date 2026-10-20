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
    page.fill("#q", query)
    settle(page)
    page.select_option("#stage", index=0)
    page.dispatch_event("#stage", "change")
    settle(page)


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
    """「위 3팀 시뮬로 확인」: Pyodide 로 파이썬 엔진을 돌려 3팀 모두 클리어 확률·95% 구간 표시, 콘솔 오류 0(인터넷 필요)"""
    ctx.errors.clear()
    page = open_page(browser, ctx, legacy=False)
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
        r = json.loads(web.run_auto(last["req"]["stage"], t["party"], last["req"]["n_runs"], last["req"]["seed"], json.dumps(last["req"]["options"])))
        b = last["res"][t["key"]]
        same.append(r["clear"] == b["clear"] and r["ttk"] == b["ttk"] and r["u"] == b["u"])
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
    ok = "클리어" in txt and "95% 구간" in txt and "완료" in state and not errs and all(same) and len(same) == n and all(spec_same)
    txt = txt + " / 입력 같음 %s" % spec_same
    txt = txt + " / 파이썬과 같음 %s" % same
    return ok, "%d팀 %.0f초 / 파이썬 결과 같음 %s / 입력 같음 %s / %s / 오류 %s" % (n, dt, same, spec_same, " ".join(txt.split())[:60], errs[:2])


def test_browser_sim_blocked(browser, ctx):
    """엔진 내려받기가 막히면 「시뮬 실패 · 다시 시도」, 빠른 계산 추천은 그대로(codex 안전장치 2)"""
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    attach(page, ctx)
    page.route("**/cdn.jsdelivr.net/**", lambda r: r.abort())
    page.context.route("**/cdn.jsdelivr.net/**", lambda r: r.abort())
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


TESTS = [test_load_no_errors, test_quick_default, test_quick_owned_small, test_quick_growth, test_savior_power, test_browser_sim,
         test_browser_sim_blocked, test_sim_auto_and_override, test_manual_mode, test_cosmo_joint, test_mobile_layout, test_python_js_topk_parity]


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
