# -*- coding: utf-8 -*-
"""길드 방어전(시즌제) 시험: 자료 일관성, 점수 범위, 시즌 종료 판정(갱신 대기), 콘텐츠 등록·추천 연결,
화면(JS) 계산과의 일치, 만든 index.html 이 최신인지. 실행: python -X utf8 -I tests/guild_defense_test.py"""
import copy
import datetime
import itertools
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
import guild_defense as gd  # noqa: E402
import party_reco as pr  # noqa: E402

KST = gd.KST
G = gd.load()
RULES = json.load(open(os.path.join(ROOT, "data", "gimmick_rules.json"), encoding="utf-8"))["types"]


def at(s):
    return datetime.datetime.fromisoformat(s).astimezone(KST)


def test_valid():
    assert gd.validate(G, RULES) == [], gd.validate(G, RULES)
    assert G["season"]["id"] == 30111 and gd.range_label(G) == "시즌4 10/29~11/05", gd.range_label(G)
    assert gd.content_title(G) == "길드방어전(시즌4 10/29~11/05)"


def test_validate_catches_bad_data():
    def mutate(fn):
        g = copy.deepcopy(G)
        fn(g)
        return gd.validate(g, RULES)
    assert mutate(lambda g: g["season"].update(end="2026-10-01T04:00:00+09:00")), "종료가 시작보다 앞서는데 통과"
    assert mutate(lambda g: g["season"].update(conf="아마")), "conf 오류 통과"
    assert mutate(lambda g: g["season"].update(src=["없는출처"])), "없는 출처 통과"
    assert mutate(lambda g: g["challenge"]["levels"][5].update(atk=1)), "누적 감소 통과"
    assert mutate(lambda g: g["steps"][6].update(ex=False)), "EX 없음 통과"
    assert mutate(lambda g: g["steps"][2].update(bossKill=1)), "보스 처치 점수 비증가 통과"
    assert mutate(lambda g: g["gimmicks"]["items"][0].update(code="NOPE")), "없는 기믹 코드 통과"
    assert mutate(lambda g: g["sets"]["items"][0]["tiers"].pop()), "세트 단계 수 오류 통과"
    assert mutate(lambda g: g.pop("asOf")), "기준일 없음 통과"


def test_score_range():
    assert gd.base_total(G) == 30000          # 기본 2500 + 졸개 2 x 1250 + 보스 25000
    lv12 = gd.extra_pct(G, 12)
    assert lv12 == 120
    assert gd.score(G, lv12) == {"A": 66000, "B": 36000}, gd.score(G, lv12)
    best_level, best_tiers = gd.best_selection(G)
    pct = gd.extra_pct(G, best_level, best_tiers)
    assert pct == 180 and gd.score(G, pct) == {"A": 84000, "B": 39000}, gd.score(G, pct)
    assert gd.score(G, 0) == {"A": 30000, "B": 30000}
    # 단조: 단계·세트가 오르면 두 가설 모두 점수가 줄지 않는다(그래서 최고 조합 = 최대 선택)
    last = None
    for lv in range(0, 13):
        s = gd.score(G, gd.extra_pct(G, lv))
        assert last is None or (s["A"] >= last["A"] and s["B"] >= last["B"])
        last = s
    for ex in G["challenge"]["levels"]:  # 효과 단계가 누적이라 표 값과 단계 효과 문구 수가 줄지 않는다
        assert ex["score"] == ex["level"] * 10 if ex["level"] <= 6 else ex["score"] == 60 + (ex["level"] - 6) * 10


def test_season_state_and_update_flag():
    cases = [("2026-10-28T12:00:00+09:00", "upcoming", False), ("2026-10-29T00:00:00+09:00", "active", False),
             ("2026-11-05T03:59:59+09:00", "active", False), ("2026-11-05T04:00:00+09:00", "settling", True),
             ("2026-11-12T03:59:59+09:00", "settling", True), ("2026-11-12T04:00:00+09:00", "ended", True)]
    for t, state, upd in cases:
        r = gd.season_state(G, at(t))
        assert r == {"state": state, "needs_update": upd}, (t, r)


def test_content_registration():
    cfg = pr._json(pr.CONT)
    c = cfg["contents"][gd.CONTENT_NAME]
    assert c.get("seasonal") and c["boss"] and "BFB" in c["bosses"] and c["bosses"]["BFB"]["enemies"] == ["order"]
    assert pr.FOE_KEYS[gd.CONTENT_NAME] == gd.CONTENT_KEY
    hits = pr.find_stages(gd.CONTENT_NAME, "EX")
    assert len(hits) == 1 and hits[0][1]["name"] == "7단계 EX" and hits[0][1]["level"] == 1275
    assert hits[0][0] == gd.range_label(G)
    fc = gd.foe_content(G)
    assert [s["name"] for s in fc["tabs"][0]["stages"]][0] == "7단계 EX", "EX 가 맨 앞이어야 기본 선택이 최고 단계"
    assert len(fc["tabs"][0]["stages"]) == 7
    # 기믹 연결: 기존 스테이지 기믹은 그대로, 길드 방어전 키만 더해진다
    rules, merged = pr.gimmick_rules()
    base = json.load(open(pr.GSTAGE, encoding="utf-8"))
    assert all(merged[k] == v for k, v in base.items()), "기존 스테이지 기믹이 바뀜"
    gk = f"guild|{gd.range_label(G)}|7단계 EX"
    assert merged[gk] == {"TARGET_PRIORITY": 3, "SHIELD_GEN": 2, "PCT_HP_DAMAGE": 2}, merged.get(gk)
    assert len(merged) - len(base) == 7 and not (set(base) & set(gd.stage_gimmicks(G)))
    # 추천이 실제로 돈다(보스 속성 질서, 기믹 줄 포함)
    lines = []
    pr.recommend(gd.CONTENT_NAME, out=lines.append)
    txt = "\n".join(lines)
    assert "적 속성: 질서" in txt and "우선 공격 대상 지정" in txt and txt.count("[전열]") == 2 and txt.count("[후열]") == 2, txt
    lines2 = []
    pr.recommend(gd.CONTENT_NAME, stage="3단계", out=lines2.append)
    assert "3단계" in "\n".join(lines2) and "보호막 생성" not in "\n".join(lines2)


def test_existing_contents_unchanged():
    # 기존 콘텐츠 추천 출력이 길드 방어전 추가 전과 같다(golden 은 별도). 고정 입력 2건의 출력 해시를 확인한다.
    import hashlib
    outs = []
    for content, kw in (("작전", {"stage": "36-36"}), ("코스모 게이트", {"boss": "길레"})):
        lines = []
        pr.recommend(content, out=lines.append, **kw)
        outs.append("\n".join(lines))
    assert all("== " in o for o in outs)
    h = hashlib.sha256("\n".join(outs).encode("utf-8")).hexdigest()[:16]
    ref = os.path.join(ROOT, "tests", "fixtures", "guild_existing_reco.sha")
    if os.environ.get("GD_WRITE_REF"):
        open(ref, "w").write(h)
    assert open(ref).read().strip() == h, "기존 콘텐츠 추천 출력이 달라짐 " + h


def test_sim_payload():
    """시뮬 추정 표: 같은 시즌만 화면에 싣고, 요약(최고 단계)이 클리어율 표와 맞는다. 다른 시즌 파일이면 싣지 않는다."""
    s = gd.sim_payload(G)
    assert s and set(s["summary"]) == {str(g) for g in s["growth"]} and len(s["levels"]) == 13
    for g in s["growth"]:
        best = None
        for i, t in enumerate(s["teams"]):
            r = t["rates"][str(g)]
            ok = [lv for lv, p in zip(s["levels"], r) if p >= s["passP"]]
            if ok and (best is None or max(ok) > best[0] or (max(ok) == best[0] and r[max(ok)] > best[2])):
                best = (max(ok), i, r[max(ok)])
        assert gd.sim_best(s, str(g)) == best, (g, best)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.json")
        raw = json.load(open(gd.SIM_PATH, encoding="utf-8"))
        raw["season"] = 1
        json.dump(raw, open(p, "w", encoding="utf-8"))
        assert gd.sim_payload(G, p) is None, "다른 시즌 결과를 실음"
    assert "sim" in gd.page_payload(G)


def node_json(code):
    p = subprocess.run(["node", "-e", code], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_js_parity():
    try:
        subprocess.run(["node", "-v"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        print("  (node 없음: JS 일치 시험 건너뜀)")
        return
    combos = [[lv, list(t)] for lv in range(0, 13) for t in itertools.product(range(4), repeat=4)]
    js = node_json("const V=require('./guild_view.js'),G=JSON.parse(require('fs').readFileSync('data/guild_defense.json','utf8'));"
                   "const C=[];for(let l=0;l<=12;l++)for(let a=0;a<4;a++)for(let b=0;b<4;b++)for(let c=0;c<4;c++)for(let d=0;d<4;d++)C.push([l,[a,b,c,d]]);"
                   "console.log(JSON.stringify(C.map(([l,t])=>{const p=V.extraPct(G,l,t);return [p,V.score(G,p)]})))")
    assert len(js) == len(combos) == 13 * 256
    for (lv, t), (p, s) in zip(combos, js):
        pp = gd.extra_pct(G, lv, tuple(t))
        assert p == pp and s == gd.score(G, pp), (lv, t, p, s, pp)
    st = node_json("const V=require('./guild_view.js'),G=JSON.parse(require('fs').readFileSync('data/guild_defense.json','utf8'));"
                   "const T=['2026-10-28T12:00:00+09:00','2026-10-29T00:00:00+09:00','2026-11-05T03:59:59+09:00','2026-11-05T04:00:00+09:00','2026-11-12T03:59:59+09:00','2026-11-12T04:00:00+09:00'];"
                   "console.log(JSON.stringify(T.map(t=>V.seasonState(G.season,Date.parse(t)))))")
    exp = [gd.season_state(G, at(t)) for t in ("2026-10-28T12:00:00+09:00", "2026-10-29T00:00:00+09:00", "2026-11-05T03:59:59+09:00",
                                               "2026-11-05T04:00:00+09:00", "2026-11-12T03:59:59+09:00", "2026-11-12T04:00:00+09:00")]
    assert [{"state": a["state"], "needs_update": a["needsUpdate"]} for a in st] == exp, (st, exp)


def test_built_page_is_current():
    import build_party_html as bp
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "index.html")
        old = sys.stdout
        sys.stdout = open(os.devnull, "w")
        try:
            bp.main(out)
        finally:
            sys.stdout.close()
            sys.stdout = old
        built = open(out, encoding="utf-8").read()
    live = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    assert built == live, "index.html 이 최신이 아님: python -X utf8 -I build_party_html.py index.html"
    assert json.dumps(gd.content_title(G), ensure_ascii=False)[1:-1] in built or gd.content_title(G) in built
    assert '"guild":{"asOf":"%s"' % G["asOf"] in built
    assert '<script src="guild_view.js"></script>' in built


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("ok", name)
    print("OK", n)
