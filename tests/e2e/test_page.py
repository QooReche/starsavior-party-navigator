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
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def load_sim(content):
    with open(os.path.join(ROOT, "data", "sim", content + ".json"), encoding="utf-8") as f:
        return json.load(f)


class Ctx:
    def __init__(self, base, shots):
        self.base, self.shots = base, shots
        self.errors = []


def attach(page, ctx):
    page.on("console", lambda m: ctx.errors.append("console: " + m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: ctx.errors.append("pageerror: %s" % e))


def settle(page):
    """디바운스(150ms)·결과 파일 로딩이 끝날 때까지"""
    page.wait_for_timeout(350)
    page.wait_for_function("() => !document.querySelector('.forecast[data-state=\"loading\"]')", timeout=20000)
    page.wait_for_timeout(100)


def choose(page, content, query):
    page.select_option("#content", label=content)
    settle(page)
    page.fill("#q", query)
    settle(page)
    page.select_option("#stage", index=0)
    page.dispatch_event("#stage", "change")
    settle(page)


def tile_text(page, k, party=1):
    return page.inner_text('.party[data-party="%d"] .ft[data-k="%s"]' % (party, k))


def open_page(browser, ctx, query="", viewport=None):
    page = browser.new_page(viewport=viewport or {"width": 1280, "height": 900})
    attach(page, ctx)
    page.goto(ctx.base + "/index.html" + query)
    page.wait_for_selector("#out .party")
    page.wait_for_function("() => window.PN && window.PN.sim.idx", timeout=20000)
    settle(page)
    return page


# ---------------------------------------------------------------- 시험
def test_load_no_errors(browser, ctx):
    """처음 열면 콘솔 오류 0, 기본 스테이지(작전 SECTOR 1-1)에 전투 전망이 뜸"""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    st = page.get_attribute('.party[data-party="1"] .forecast', "data-state")
    errs = list(ctx.errors)
    page.close()
    return st == "ok" and not errs, "전망 상태 %s, 콘솔 오류 %d %s" % (st, len(errs), errs[:3])


def test_stage_switch(browser, ctx):
    """콘텐츠·스테이지를 바꾸면 전망(팀·숫자)이 바뀜: 코스모 길레 1단계 -> 2단계"""
    page = open_page(browser, ctx)
    choose(page, "코스모 게이트", "길레 1단계")
    a = (page.get_attribute('.party[data-party="1"]', "data-team"), tile_text(page, "clear"), tile_text(page, "ttk"))
    choose(page, "코스모 게이트", "길레 2단계")
    b = (page.get_attribute('.party[data-party="1"]', "data-team"), tile_text(page, "clear"), tile_text(page, "ttk"))
    n2 = page.locator('.party[data-party="2"] .forecast[data-state="ok"]').count()
    rec = load_sim("cosmo")["stages"]["길레|길레 2단계"]
    shown = [page.get_attribute('.party[data-party="%d"]' % i, "data-team") for i in (1, 2)]
    want = [p["rank"][0] for p in rec["parties"]]
    page.screenshot(path=os.path.join(ctx.shots, "desktop_cosmo_gille2_auto.png"), full_page=True)
    page.close()
    return a != b and n2 == 1 and shown == want, "1단계 %s / 2단계 %s / 파티2 전망 %d / 화면 팀 = 사전 계산 1위 %s" % (
        a[1].split("\n")[1], b[1].split("\n")[1], n2, shown == want)


def test_mode_toggle(browser, ctx):
    """오토/수동: 숫자(표본 문구·델타)와 서순 표가 바뀌고, localStorage·?mode=manual 로 유지"""
    page = open_page(browser, ctx, "?mode=auto")
    choose(page, "플래시 포인트", "매니저 그레고리 Ⅰ")   # 수동이 클리어 확률을 바꾸는 스테이지(97% -> 100%)
    auto_meta = page.inner_text('.party[data-party="1"] .meta')
    auto_seq = page.locator('.party[data-party="1"] .seq').count()
    auto_tiles = page.inner_text('.party[data-party="1"] .ft[data-k="clear"] .fv')
    page.click('label:has(#m-manual)')
    settle(page)
    man_meta = page.inner_text('.party[data-party="1"] .meta')
    man_tiles = page.inner_text('.party[data-party="1"] .ft[data-k="clear"] .fv')
    seq = page.locator('.party[data-party="1"] .seq[data-state="ok"]').count()
    rows = page.locator('.party[data-party="1"] .seq .sgrid .tl').count()
    url_ok = "mode=manual" in page.url
    page.screenshot(path=os.path.join(ctx.shots, "desktop_rush_gregory1_manual.png"), full_page=True)
    page.reload()
    page.wait_for_function("() => window.PN && window.PN.sim.idx")
    settle(page)
    keep = page.evaluate("() => window.PN.mode()")
    page.close()
    p2 = open_page(browser, ctx, "?mode=manual")
    from_url = p2.evaluate("() => window.PN.mode()") == "manual" and p2.is_checked("#m-manual")
    p2.evaluate("() => localStorage.removeItem('pn.mode')")
    p2.close()
    ok = (auto_seq == 0 and seq == 1 and rows >= 3 and "수동" in man_meta and "오토" in auto_meta and man_tiles != auto_tiles
          and url_ok and keep == "manual" and from_url)
    return ok, "서순 오토 %d/수동 %d(보이는 행 %d), 클리어 확률 %s -> %s, URL %s, 새로고침 유지 %s, ?mode=manual %s" % (
        auto_seq, seq, rows, " ".join(auto_tiles.split()), " ".join(man_tiles.split()), url_ok, keep, from_url)


def test_owned_filter_no_sim(browser, ctx):
    """서랍에서 보유 구원자를 바꿔 사전 계산 후보를 하나도 못 만들면 「근사 점수만 · 시뮬 없음」, 숫자 타일 없음"""
    rec = load_sim("cosmo")["stages"]["길레|길레 2단계"]
    pool_units = sorted({k for key in rec["teams"] for k in key.split(",")})
    page = open_page(browser, ctx, "?mode=auto")
    choose(page, "코스모 게이트", "길레 2단계")
    page.click("#dbtn")
    page.wait_for_selector("#drawer.open")
    back = page.is_visible("#dback")
    page.click("#all")
    for k in pool_units:
        page.click('#own label.tile:has(input[data-k="%s"])' % k)
    page.click("#dback", position={"x": 1200, "y": 400})
    settle(page)
    closed = not page.is_visible("#drawer.open")
    st = page.get_attribute('.party[data-party="1"] .forecast', "data-state")
    chip = page.locator('.party[data-party="1"] .forecast .nochip').inner_text()
    tiles = page.locator('.party[data-party="1"] .ftiles').count()
    page.screenshot(path=os.path.join(ctx.shots, "desktop_owned_filter_nosim.png"), full_page=False)
    page.click("#dbtn")
    page.click("#all")
    page.keyboard.press("Escape")
    page.close()
    return st == "nosim" and "시뮬 없음" in chip and tiles == 0 and back and closed, "뺀 구원자 %d명, 상태 %s, 칩 「%s」, 숫자 타일 %d, 배경 %s, 바깥 클릭 닫힘 %s" % (
        len(pool_units), st, chip, tiles, back, closed)


def test_flash_point(browser, ctx):
    """플래시 포인트(이전 파이썬 KeyError 'bosses' 와 같은 경로) 화면이 오류 없이 전망을 보임"""
    ctx.errors.clear()
    page = open_page(browser, ctx)
    choose(page, "플래시 포인트", "매니저 그레고리 Ⅰ")
    st = page.get_attribute('.party[data-party="1"] .forecast', "data-state")
    txt = page.inner_text("#stinfo")
    errs = list(ctx.errors)
    page.close()
    return st == "ok" and "매니저 그레고리" in txt and not errs, "상태 %s, 콘솔 오류 %d" % (st, len(errs))


def test_mobile_layout(browser, ctx):
    """390x844: 가로 스크롤 없음, 카드 4장이 한 줄에 인게임 순서(사전 계산 편성 순서와 같음), 전망 2x2"""
    page = open_page(browser, ctx, "?mode=manual", viewport={"width": 390, "height": 844})
    choose(page, "코스모 게이트", "길레 2단계")
    sw = page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
    cards = page.evaluate("""() => [...document.querySelectorAll('.party[data-party="1"] .rowcards .gc')].map(g => {
        const r = g.querySelector('.card').getBoundingClientRect(); return [g.dataset.key, Math.round(r.top), Math.round(r.left)] })""")
    team = page.get_attribute('.party[data-party="1"]', "data-team")
    order = load_sim("cosmo")["stages"]["길레|길레 2단계"]["teams"][team]["o"]
    cols = page.evaluate("""() => getComputedStyle(document.querySelector('.party[data-party="1"] .ftiles')).gridTemplateColumns.split(' ').length""")
    page.screenshot(path=os.path.join(ctx.shots, "mobile_cosmo_gille2_manual.png"), full_page=True)
    page.evaluate("() => localStorage.removeItem('pn.mode')")
    page.close()
    same_row = len({c[1] for c in cards}) == 1 and [c[2] for c in cards] == sorted(c[2] for c in cards)
    ok = sw[0] <= sw[1] and len(cards) == 4 and same_row and [c[0] for c in cards] == order and cols == 2
    return ok, "폭 %s, 카드 %s, 사전 계산 순서 %s, 전망 열 %d" % (sw, [c[0] for c in cards], order, cols)


def test_python_js_topk_parity(browser, ctx):
    """여러 보유 필터에서 브라우저 topParties 상위 10 = 파이썬 top_parties 상위 10(조합·순서·점수)"""
    import build_sim_results as bsr
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


def open_owned(browser, ctx, owned, query=""):
    """보유 구원자를 localStorage 로 정해 두고 연다(서랍 클릭 대신 — 서랍 경로는 test_owned_filter_no_sim 이 확인)"""
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    attach(page, ctx)
    page.add_init_script("localStorage.setItem('pn.owned', JSON.stringify(%s))" % json.dumps(sorted(owned)))
    page.goto(ctx.base + "/index.html" + query)
    page.wait_for_selector("#out .party")
    page.wait_for_function("() => window.PN && window.PN.sim.idx", timeout=20000)
    settle(page)
    return page


def test_stage_meta_version(browser, ctx):
    """스테이지마다 실행 정보(meta)를 검사: 한 스테이지의 추천 입력 해시만 바꾸면 그 스테이지만 「시뮬 결과 없음」, 다른 스테이지는 그대로(codex 차단 1)"""
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    attach(page, ctx)

    def patch(route):
        resp = route.fetch()
        doc = resp.json()
        doc["stages"]["매니저 그레고리|매니저 그레고리 Ⅰ"]["meta"]["sel"] = "다른버전"
        route.fulfill(response=resp, body=json.dumps(doc, ensure_ascii=False), headers={"content-type": "application/json"})
    page.route("**/data/sim/rush.json", patch)
    page.goto(ctx.base + "/index.html")
    page.wait_for_function("() => window.PN && window.PN.sim.idx", timeout=20000)
    settle(page)
    choose(page, "플래시 포인트", "매니저 그레고리 Ⅰ")
    s1 = page.get_attribute('.party[data-party="1"] .forecast', "data-state")
    choose(page, "플래시 포인트", "매니저 그레고리 Ⅱ")
    s2 = page.get_attribute('.party[data-party="1"] .forecast', "data-state")
    meta = page.inner_text('.party[data-party="1"] .meta')
    page.close()
    rec = load_sim("rush")["stages"]["매니저 그레고리|매니저 그레고리 Ⅱ"]["meta"]
    ok = s1 == "version" and s2 == "ok" and ("시드 %d" % rec["seed"]) in meta and rec["sv"]["rules"] in meta
    return ok, "해시 바꾼 스테이지 %s / 다른 스테이지 %s / 메타 줄 = 그 스테이지 meta(시드 %d, 규칙 %s) %s" % (s1, s2, rec["seed"], rec["sv"]["rules"], ok)


def test_avoid_mode_tiebreak(browser, ctx):
    """역상성 회피 옵션이면 동점(클리어·처치 턴 같음) 판정에 지금 근사 점수를 씀(사전 계산 rec.a 아님, codex 2 — SECTOR 2-12)"""
    page = open_page(browser, ctx)
    choose(page, "작전 (일반)", "SECTOR 2-12")
    page.click("#optbox summary")      # 옵션은 접힌 상자 안
    page.select_option("#mmode", "avoid")
    settle(page)
    last = page.evaluate("() => window.PN.last")
    shown = page.get_attribute('.party[data-party="1"]', "data-team")
    page.evaluate("() => localStorage.removeItem('pn.mm')")
    page.close()
    import math

    def key(x, score):
        a = x["auto"]
        if not a.get("g"):
            return (1, 0, 1e9, -score, x["key"])
        return (0, -math.floor(a["c"] * 20 + 1e-9), a["t"] if a["t"] is not None else 1e9, -score, x["key"])
    by_v = sorted(last["simmed"], key=lambda x: key(x, round(x["v"], 3)))[0]["key"]
    by_a = sorted(last["simmed"], key=lambda x: key(x, x["a"]))[0]["key"]
    return shown == by_v and by_v != by_a, "화면 %s / 지금 점수 기준 %s / 사전 계산 점수 기준 %s" % (shown, by_v, by_a)


def test_manual_candidate_diff(browser, ctx):
    """수동 화면의 다른 후보 차이 = 후보 수동 - 표시 팀 수동(같은 모드끼리, codex 3 — 그레고리 Ⅰ)"""
    page = open_page(browser, ctx, "?mode=manual")
    choose(page, "플래시 포인트", "매니저 그레고리 Ⅰ")
    shown = page.get_attribute('.party[data-party="1"]', "data-team")
    rows = page.evaluate("""() => [...document.querySelectorAll('.party[data-party="1"] .cands tr[data-dc]')].map(r => [r.dataset.key, +r.dataset.dc])""")
    page.evaluate("() => localStorage.removeItem('pn.mode')")
    page.close()
    teams = load_sim("rush")["stages"]["매니저 그레고리|매니저 그레고리 Ⅰ"]["teams"]
    res = lambda k: teams[k]["man"] if teams[k].get("man", {}).get("g") else teams[k]["auto"]
    bad = [(k, d) for k, d in rows if abs(d - (res(k)["c"] - res(shown)["c"])) > 1e-3]
    mixed = sum(1 for k, _ in rows if abs((res(k)["c"] - res(shown)["c"]) - (res(k)["c"] - teams[shown]["auto"]["c"])) > 1e-3)
    return bool(rows) and not bad and mixed > 0, "후보 %d, 불일치 %d, (오토와 섞으면 달라지는 줄 %d)" % (len(rows), len(bad), mixed)


def test_allzero_recomputed(browser, ctx):
    """「후보 전부 0판」은 지금 보이는 후보·모드로 판단(codex 4): 12-36 보유 4명 오토 = 안내 있음, 13-36 보유 4명 수동(1/200) = 안내 없음, 같은 팀 오토 = 있음"""
    p1 = open_owned(browser, ctx, ["amora", "ceres", "waltz-asherah", "wedding-carmen"], "?mode=auto")
    choose(p1, "작전 (일반)", "SECTOR 12-36")
    a = p1.locator('.party[data-party="1"] [data-k="allzero"]').count()
    st_a = p1.get_attribute('.party[data-party="1"] .forecast', "data-state")
    p1.close()
    p2 = open_owned(browser, ctx, ["professor-m", "waltz-asherah", "wedding-carmen", "wedding-epindel"], "?mode=manual")
    choose(p2, "작전 (일반)", "SECTOR 13-36")
    b = p2.locator('.party[data-party="1"] [data-k="allzero"]').count()
    cb = p2.inner_text('.party[data-party="1"] .ft[data-k="clear"] .fv')
    p2.click('label:has(#m-auto)')
    settle(p2)
    c = p2.locator('.party[data-party="1"] [data-k="allzero"]').count()
    p2.evaluate("() => localStorage.removeItem('pn.mode')")
    p2.close()
    ok = st_a == "ok" and a == 1 and b == 0 and c == 1
    return ok, "12-36 오토 안내 %d(상태 %s) / 13-36 수동 안내 %d(클리어 %s) / 13-36 오토 안내 %d" % (a, st_a, b, cb.split()[0] if cb else "", c)


def test_mobile_seq_target(browser, ctx):
    """모바일 서순 칸에도 대상이 짧게 보임(화살표만 남지 않음), 전체 이름은 title(codex 5)"""
    page = open_page(browser, ctx, "?mode=manual", viewport={"width": 390, "height": 844})
    choose(page, "플래시 포인트", "매니저 그레고리 Ⅰ")
    txt = page.evaluate("""() => [...document.querySelectorAll('.party[data-party="1"] .seq .sgrid .tgt')].filter(e => e.offsetParent).map(e => [e.innerText.trim(), e.title])""")
    page.evaluate("() => localStorage.removeItem('pn.mode')")
    page.close()
    bare = [t for t in txt if t[0].replace("→", "").strip() == ""]
    return bool(txt) and not bare and all(t[1].startswith("대상: ") for t in txt), "보이는 대상 %d개, 화살표만 %d, 예 %s" % (len(txt), len(bare), txt[:3])


TESTS = [test_load_no_errors, test_stage_switch, test_mode_toggle, test_owned_filter_no_sim, test_flash_point, test_mobile_layout,
         test_python_js_topk_parity, test_stage_meta_version, test_avoid_mode_tiebreak, test_manual_candidate_diff, test_allzero_recomputed,
         test_mobile_seq_target]


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
