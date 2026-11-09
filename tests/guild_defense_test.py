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


def test_boss_element_is_star():
    # 배치 ChangeAdjustType = NUAT_STAR 이 실제 속성(유닛 표의 질서는 무시). 엔진 자료(guild_bfb.json)와 같아야 한다.
    EN = {"별": "star", "질서": "order", "태양": "sun", "달": "moon", "혼돈": "chaos"}
    bfb = json.load(open(os.path.join(ROOT, "data", "guild_bfb.json"), encoding="utf-8"))
    assert G["season"]["boss"]["element"] == "star"
    assert EN[bfb["boss"]["element"]] == EN[bfb["minion"]["element"]] == G["season"]["boss"]["element"]


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
    assert gd.score(G, lv12) == {"A": 66000}, gd.score(G, lv12)
    best_level, best_tiers = gd.best_selection(G)
    pct = gd.extra_pct(G, best_level, best_tiers)
    assert best_tiers == (0, 0, 0, 0), "선택 효과는 길방에 없어(클라 확인) 최고 조합에서도 끔"
    assert pct == 120 and gd.score(G, pct) == {"A": 66000}, gd.score(G, pct)
    assert gd.score(G, gd.extra_pct(G, 12, (3, 3, 3, 3))) == {"A": 84000}   # 가정 계산용으로는 남아 있음
    assert gd.score(G, 0) == {"A": 30000}
    # 영상(2026-11-01)으로 확인한 식: 보스 99.9% 깎고 패배 → 전투 중 점수 29,975 x 1.6(6단계) = 47,960
    assert gd.score_at(G, 60, 0.999) == 47960 and gd.score_at(G, 60, 1.0) == 48000
    assert gd.score_at(G, 0, 0.0) == 5000 and gd.score_at(G, 0, 1.5) == 30000     # 보스를 안 깎아도 기본·졸개 5,000, 비율은 0~1 로 제한
    assert G["score"]["conf"] == "확인" and len(G["score"]["hypotheses"]) == 1
    # 단조: 단계·세트가 오르면 점수가 줄지 않는다(그래서 최고 조합 = 최대 선택)
    last = None
    for lv in range(0, 13):
        s = gd.score(G, gd.extra_pct(G, lv))
        assert last is None or s["A"] >= last["A"]
        last = s
    for ex in G["challenge"]["levels"]:  # 효과 단계가 누적이라 표 값과 단계 효과 문구 수가 줄지 않는다
        assert ex["score"] == ex["level"] * 10 if ex["level"] <= 6 else ex["score"] == 60 + (ex["level"] - 6) * 10


def test_score_kills_and_ratio_floor():
    """졸개 처치 수 k·보스 비율 1/10000 내림·정수 점수(클라 실시간 점수). 단계 보너스 반올림은 서버 계산이라 미확인(기존 사사오입)."""
    assert [gd.score_at(G, 0, 0, k) for k in (0, 1, 2)] == [2500, 3750, 5000]
    assert gd.score_at(G, 0, 1.0, 2) == 30000 and gd.score_at(G, 0, 1.0, 0) == 27500
    assert gd.score_at(G, 0, 1.0) == 30000, "kills 생략 = 졸개 전부"
    assert gd.score_at(G, 0, 1.0, 9) == 30000 and gd.score_at(G, 0, 1.0, -3) == 27500, "k 는 0~졸개 수로 제한"
    assert gd.score_at(G, 0, 0.5, 2) == 17500
    assert gd.score_at(G, 0, 0.00005, 2) == 5000, "1/10000 미만은 내림(0.5/10000 -> 0)"
    assert gd.score_at(G, 0, 0.0001, 2) == 5002 and gd.score_at(G, 0, 0.00015, 2) == 5002
    assert gd.score_at(G, 0, 0.29, 2) == 12250, "0.29x10000 부동소수 오차(2899.99…)에도 2900"
    assert gd.score_at(G, 60, 0.999) == 47960 and gd.score_at(G, 60, 1.0, 1) == 46000
    # 단계 보너스 곱셈 뒤 .5 반올림(올림): 합산 10 x 1.05 = 10.5 -> 11, 10 x 1.15 = 11.5 -> 12, 10 x 1.04 = 10.4 -> 10
    g2 = json.loads(json.dumps(G))
    ex = next(x for x in g2["steps"] if x["ex"]); ex["base"], ex["kill"], ex["bossKill"] = 10, 0, 0
    assert [gd.score_at(g2, p) for p in (0, 4, 5, 15)] == [10, 10, 11, 12]
    assert [gd.score(g2, p)['A'] for p in (0, 4, 5, 15)] == [10, 10, 11, 12], 'score() 도 사사오입(Python round 는 10.5 -> 10)'
    # 진행도 -> (처치 졸개, 보스 비율)
    cases = [(-1, (0, 0.0)), (0, (0, 0.0)), (0.24, (0, 0.0)), (0.25, (1, 0.0)), (0.4999, (1, 0.0)), (0.5, (2, 0.0)),
             (0.75, (2, 0.5)), (1, (2, 1.0)), (2, (2, 1.0))]
    for p, want in cases:
        got = gd.prog_parts(G, p)
        assert got[0] == want[0] and abs(got[1] - want[1]) < 1e-12, (p, got, want)
    assert gd.score_from_prog(G, 0, 0.3) == 3750, "졸개 1기만 처치하고 진 판"
    assert gd.score_from_prog(G, 0, 0.1) == 2500 and gd.score_from_prog(G, 0, 1) == 30000


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
    assert c.get("seasonal") and c["boss"] and "BFB" in c["bosses"] and c["bosses"]["BFB"]["enemies"] == ["star"]
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
    # 추천이 실제로 돈다(보스 속성 별, 기믹 줄 포함)
    lines = []
    pr.recommend(gd.CONTENT_NAME, out=lines.append)
    txt = "\n".join(lines)
    assert "적 속성: 별" in txt and "우선 공격 대상 지정" in txt and txt.count("[전열]") == 2 and txt.count("[후열]") == 2, txt
    lines2 = []
    pr.recommend(gd.CONTENT_NAME, stage="3단계", out=lines2.append)
    assert "3단계" in "\n".join(lines2) and "보호막 생성" not in "\n".join(lines2)


def test_existing_contents_unchanged():
    # 기존 콘텐츠 추천 출력이 길드 방어전 추가 전과 같다(golden 은 별도). 고정 입력 2건의 출력 해시를 확인한다.
    import hashlib
    from unittest.mock import patch
    import battlesim.engine as engine
    from battlesim.metrics import build_index

    # 공개 화력표는 새 규칙으로 재생성되므로, 이 고정 해시만 옛 협공 상한으로
    # 추천 입력(s/a/g)을 계산한다. ref95·turns는 pack_damage처럼 그대로 둔다.
    legacy_damage = pr._json(pr.DMG)
    with patch.object(engine, 'COOP_CAP', 0.30), patch.dict(engine.DEFAULT_OPTS, coop_order='capped'):
        index = build_index()
    for key, unit in legacy_damage['units'].items():
        row = index[key]
        unit.update(s=round(row['single_dpt']), a=round(row['aoe_dpt']), g=row['ally_dmg_gain_pct'])
    outs = []
    with patch.object(pr, '_DI', legacy_damage):
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
            for sup in s["supports"]:      # 알리시아 지원까지 포함해 가장 높은 단계
                r = t["bySupport"][sup][str(g)]
                ok = [lv for lv, p in zip(s["levels"], r) if p >= s["passP"]]
                if ok and (best is None or max(ok) > best[0] or (max(ok) == best[0] and r[max(ok)] > best[2])):
                    best = (max(ok), i, r[max(ok)])
        assert gd.sim_best(s, str(g)) == best, (g, best)
    assert s["supports"][0] == "none" and all(t["rates"] == t["bySupport"]["none"] for t in s["teams"])
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.json")
        raw = json.load(open(gd.SIM_PATH, encoding="utf-8"))
        raw["season"] = 1
        json.dump(raw, open(p, "w", encoding="utf-8"))
        assert gd.sim_payload(G, p) is None, "다른 시즌 결과를 실음"
    assert "sim" in gd.page_payload(G)


def test_sim_presets_payload():
    raw = json.load(open(gd.SIM_PATH, encoding='utf-8'))
    s = gd.sim_payload(G)
    assert s['growth'] == ['1', '1.5', '2', '2.5', '3']
    assert s['sets'] == raw['sets'] == {'off': [0]*4, 'max': [3]*4}
    assert s['summaryBySets'] == raw['summaryBySets']
    for name in s['sets']:
        summary = s['summary'] if name == 'off' else s['summaryBySets'][name]
        for g in s['growth']:
            candidates = []
            for i, (t, rt) in enumerate(zip(s['teams'], raw['teams'])):
                assert t['bySets'] == rt['bySets'], '화면 전달 중 프리셋 누락'
                tab = t if name == 'off' else t['bySets'][name]
                for sup in s['supports']:
                    rr, pp, ff = [tab[k][sup][g] for k in ('bySupport', 'progBySupport', 'fracBySupport')]
                    assert len(rr) == len(pp) == len(ff) == len(s['levels'])
                    assert all(0 <= v <= 1 for row in (rr, pp, ff) for v in row)
                    assert all(f >= max(0, 2*p-1) - 1e-3 for p, f in zip(pp, ff))
                    candidates += [(lv, p, i, sup) for lv, p in zip(s['levels'], rr) if p >= s['passP']]
            best = max(candidates, key=lambda x: (x[0], x[1])) if candidates else None
            expected = dict(zip(('level', 'p', 'team', 'support'), best)) if best else None
            assert summary[g] == expected, (name, g, summary[g], expected)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'old.json')
        for k in ('sets', 'summaryBySets'):
            raw.pop(k)
        for t in raw['teams']:
            t.pop('bySets')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(raw, f)
        old = gd.sim_payload(G, path)
        assert old['sets'] == {'off': [0]*4} and old['summaryBySets'] == {}
        assert all(t['bySets'] == {} for t in old['teams'])


def node_json(code):
    p = subprocess.run(["node", "-e", code], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_js_parity():
    try:
        subprocess.run(["node", "-v"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        from tools.runtime import skip_note
        skip_note("guild_defense_test.test_js_parity: node 없음")
        return
    combos = [[lv, list(t)] for lv in range(0, 13) for t in itertools.product(range(4), repeat=4)]
    js = node_json("const V=require('./guild_view.js'),G=JSON.parse(require('fs').readFileSync('data/guild_defense.json','utf8'));"
                   "const C=[];for(let l=0;l<=12;l++)for(let a=0;a<4;a++)for(let b=0;b<4;b++)for(let c=0;c<4;c++)for(let d=0;d<4;d++)C.push([l,[a,b,c,d]]);"
                   "console.log(JSON.stringify(C.map(([l,t])=>{const p=V.extraPct(G,l,t);return [p,V.score(G,p)]})))")
    assert len(js) == len(combos) == 13 * 256
    for (lv, t), (p, s) in zip(combos, js):
        pp = gd.extra_pct(G, lv, tuple(t))
        assert p == pp and s == gd.score(G, pp), (lv, t, p, s, pp)
    fractions = [-1, 0, 0.00002, 0.5, 0.999, 1, 2]  # 0.00002는 5000.5점 경계
    pcs = [gd.extra_pct(G, lv, tiers) for lv in (0, 6, 12) for tiers in ([0]*4, [3]*4, [3,3,3,0])]
    values = node_json("const V=require('./guild_view.js'),G=require('./data/guild_defense.json');"
                       + "console.log(JSON.stringify(" + json.dumps(pcs) + ".map(p=>"
                       + json.dumps(fractions) + ".map(f=>V.scoreAt(G,p,f)))))")
    assert values == [[gd.score_at(G, pc, f) for f in fractions] for pc in pcs]
    ks = [None, 0, 1, 2, 5]
    fr2 = [0, 0.00005, 0.0001, 0.00015, 0.29, 0.5, 0.9999, 1]
    vals = node_json("const V=require('./guild_view.js'),G=require('./data/guild_defense.json');"
                     "const out=[];for(const p of [0,60,120])for(const k of " + json.dumps(ks) + ")for(const f of " + json.dumps(fr2) + ")out.push(V.scoreAt(G,p,f,k));"
                     "console.log(JSON.stringify(out))")
    assert vals == [gd.score_at(G, p, f, k) for p in (0, 60, 120) for k in ks for f in fr2]
    progs = [-1, 0, 0.1, 0.24, 0.25, 0.3, 0.4999, 0.5, 0.75, 0.999, 1, 2]
    pv = node_json("const V=require('./guild_view.js'),G=require('./data/guild_defense.json');"
                   "console.log(JSON.stringify(" + json.dumps(progs) + ".map(p=>[V.progParts(G,p),V.scoreFromProg(G,60,p)])))")
    for p, (parts, sc) in zip(progs, pv):
        k, f = gd.prog_parts(G, p)
        assert parts["k"] == k and abs(parts["f"] - f) < 1e-12 and sc == gd.score_from_prog(G, 60, p), (p, parts, sc)
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


def test_search_excluded():
    """편성 찾기 제외 목록: 스킬 문구 «협공» 구원자(+ 직접 지정 excludeKeys, 지금은 없음). 추가 발동형(그웬)은 빼지 않고 시뮬이 가린다. 키는 모두 실제 구원자여야 하고 화면 자료에 실린다."""
    from battlesim.starsavior.data import get_db
    ex = gd.excluded_units(G["search"]["excludeText"], G["search"]["excludeKeys"])
    assert {"professor-m", "waltz-asherah"} <= set(ex) and "gwen" not in ex, ex
    assert set(ex) <= set(get_db().units), "없는 구원자 키"
    assert gd.page_payload(G)["search"]["excluded"] == ex
    assert gd.excluded_units([], []) == []


def test_search_notes():
    """제외·주의 구원자 목록(화면 표시용): 키는 실제 구원자, 종류·근거 수준은 정해진 값, 실제로 빠지는 구원자는 모두 설명이 있어야 한다."""
    from battlesim.starsavior.data import get_db
    notes = G["search"]["notes"]
    assert notes and set(get_db().units) >= {n["key"] for n in notes}, "없는 구원자 키"
    assert all(n["kind"] in ("exclude", "caution") and n["basis"] in ("client", "community", "inference") and n["why"] for n in notes)
    ex = set(gd.excluded_units(G["search"]["excludeText"], G["search"]["excludeKeys"]))
    assert ex <= {n["key"] for n in notes if n["kind"] == "exclude"}, "설명 없는 제외 구원자: %s" % (ex - {n["key"] for n in notes})
    assert {n["key"] for n in notes if n["kind"] == "exclude"} <= ex, "목록엔 제외인데 실제로는 안 빠짐"
    assert gd.page_payload(G)["search"]["notes"] == notes


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("ok", name)
    print("OK", n)
