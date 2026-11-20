# Frozen pre-role-removal policy from 5139b2e, solely for guild_existing_reco.sha.
# Current policy is tested by reco_reuse/placement tests. Do not update the golden hash.
LEAD_OPEN_TAGS = ("힐", "보호막", "속도증가", "적방어력감소", "아군공격력증가")

def team_value(combo, cfg, tags, def_pen):
    w = cfg["weights"]
    v = _sum_in_order(x["score"] for x in combo)
    roles = [x["s"]["className"] for x in combo]
    if SUPPORT in roles:
        v += w["supportBonus"]
    v -= def_pen * max(0, roles.count(DEFENDER) - 1)  # 2번째 디펜더부터 감점
    if roles.count(SUPPORT) > 1:
        v -= 4
    got = set()
    for x in combo:
        got.update(tags.get(x["s"]["key"], []))
    for tag, weight in cfg["tagWeights"].items():
        if tag in got:
            v += weight
    v += min(_sum_in_order(h[0] for h in party_synergy([x["s"]["key"] for x in combo], cfg)), cfg["synergy"]["cap"])
    v += gimmick_team(combo, cfg)[0]
    v += _DM[1] * dmg_score([x["s"]["key"] for x in combo], _DM[0])
    return v, got

def leader_pick(party, cfg, tags):
    """리더(속도 +10) 추천: 팀 동료에게 제공하는 연계(유형 1~4) 점수가 가장 큰 구성원. (구성원, 점수, 이유 목록) 또는 None."""
    keys = [x["s"]["key"] for x in party]
    gain = {k: 0.0 for k in keys}
    why = {k: [] for k in keys}
    for pts, p in party_synergy(keys, cfg):
        if int(p["type"].split(":")[0]) > 4:
            continue
        givers = [p["a"]] if p.get("directed") else [p["a"], p["b"]]
        for g in givers:
            gain[g] += pts / len(givers)
            why[g].append(p["reason"])
    for x in party:  # 동률이면 첫 턴 지원 효과(힐·보호막 등)가 있는 쪽
        gain[x["s"]["key"]] += 0.3 * sum(1 for t in tags.get(x["s"]["key"], []) if t in LEAD_OPEN_TAGS)
    k = max(keys, key=lambda k: gain[k])
    if gain[k] <= 0:
        return None
    return next(x for x in party if x["s"]["key"] == k), gain[k], why[k][:2]

def place(party):
    """전열 2/후열 2: 디펜더·서포터를 앞에, 나머지는 뒤(게임 공략 정석: 딜러/디펜더/서포터/딜러)."""
    order = sorted(party, key=lambda x: (x["s"]["className"] not in FRONT_ROLES, -x["score"]))
    return order[:2], order[2:]

def recommend(content, boss=None, owned=None, have_break=None, out=print, stage=None, power=None):
    roster, growth, mains, cfg, tags = load()
    c = cfg["contents"][content]
    enemies = c.get("enemies", [])
    note = c.get("note", "")
    if boss and boss not in c.get("bosses", {}):
        # 보스 표가 없는 콘텐츠(플래시 포인트 등)는 보스 이름을 스테이지 검색어로 쓴다(이전: KeyError 'bosses')
        if not stage:
            stage = boss
        boss = None
    if boss:
        b = c["bosses"][boss]
        enemies, note = b["enemies"], f'{boss}: {EL[b["enemies"][0]]} {b["role"]} {b["atk"]} {b.get("note", "")}'
    if c.get("seasonal") and not stage:
        stage = "7단계"  # 시즌제 콘텐츠(길드 방어전)는 스테이지를 안 주면 최고 단계(EX)
    rest = None  # 속성 제한 콘텐츠(예: 태양 회랑은 태양 속성만)
    if stage:
        hits = find_stages(content, stage)
        if not hits:
            out(f"스테이지 '{stage}' 없음 (콘텐츠 {content})")
            return
        tab, st = hits[0]
        rest = c.get("restrictTabs", {}).get(tab)
        if rest:
            out(f"※ {tab}: {EL[rest]} 속성 구원자만 편성 가능")
        enemies = stage_enemies(st)
        note = (f'{tab} {st["name"]} Lv{st["level"]} 적 {st["enemy_total"]}체 / 지배 속성 '
                f'{EL.get(st["dominant_element"], "?")} / 광역 {st["aoe_ratio"]:.0%} / 디펜더 {st["defender_ratio"]:.0%}'
                f' (일치 {len(hits)}건 중 첫 번째)')
    def_pen = c.get("defenderPenalty", cfg["weights"]["defenderPenalty"])
    _GIM[0] = []
    _SB[0] = []
    _DM[0] = min(1.0, (st["enemy_total"] - 1) / 2) if stage else 0.5
    _DM[1] = cfg["damage"]["weightBoss"] if (c.get("boss", False) or bool(boss)) else cfg["damage"]["weightMob"]
    if stage:
        _SB[0] = (st.get("season_bonus_latest") or {}).get("bonuses", [])
        if _SB[0]:
            sbk = st["season_bonus_latest"]
            out("시즌 보너스(" + str(sbk.get("season", "")) + "): " + " / ".join(f"{b['cond']} {b['text']}" for b in _SB[0]))
    if stage:
        _GIM[0] = stage_gimmicks(f"{FOE_KEYS[content]}|{tab}|{st['name']}", cfg)
        if _GIM[0]:
            rl, _ = gimmick_rules()
            out("스테이지 기믹: " + ", ".join(f"{rl['types'][c]['name']}(심각도{sv})" for c, sv in _GIM[0]))
    if stage and power:
        rec = st.get("recommended_power")
        pp = power_penalty(power, rec)
        if pp:
            ratio, a, b, warn = pp
            out(f"전투력 {power:,} / 권장 {rec:,} = {ratio:.1f}% -> " + (f"아군 피해 x{a:.3f}, 적 피해 x{b:.3f}" + (f" [{warn}]" if warn else "") if a < 1 else "보정 없음 (90% 이상)"))
            if a < 1:
                out("  (참고용: 추천 편성은 전투력을 반영하지 않습니다. 편성을 바꾸면 전투력도 달라지므로)")
    out(f"== {content} {boss or ''} (적 속성: {'/'.join(sorted({EL[e] for e in enemies})) or '미지정'}) {note}")
    used = set()
    for p in range(1, c.get("parties", 1) + 1):
        cands = []
        for s in roster:
            if s["key"] in used or (owned is not None and s["key"] not in owned) or (rest and s["element"] != rest):
                continue
            v, parts = score(s, growth, mains, cfg, c["main"], enemies, c.get("boss", False) or bool(boss))
            cands.append({"s": s, "g": growth.get(s["key"]), "score": v, "parts": parts})
        if len(cands) < 4:
            out(f"-- 파티 {p}: 후보가 4명 미만")
            break
        party, v, got = best_party(cands, cfg, tags, def_pen)
        out(f"-- 파티 {p} (점수 {v:.1f}) 팀 기능: {', '.join(sorted(got)) or '-'}")
        used |= {x["s"]["key"] for x in party}
        front, back = place(party)
        out(f"  [화력 지표] {dmg_score([x['s']['key'] for x in party], _DM[0]):.1f}/10 (10턴 기대 피해 근사, 장비 제외 상대 비교용)")
        ld = leader_pick(party, cfg, tags)
        if ld:
            out(f"  [리더 추천] {ld[0]['s']['name']}({ld[0]['s']['subtitle']}) - 속도 +10 으로 먼저 행동해 팀에 줄 효과가 가장 많음(추정, 점수 {ld[1]:.1f})")
        for label, grp in (("전열", front), ("후열", back)):
            for x in grp:
                out(f"  [{label}] " + fmt(x))
                a = alts(x, party, cands, cfg, tags, def_pen, used)
                if a:
                    out("        대체: " + " > ".join(y["s"]["name"] for y in a))
        if _GIM[0]:
            for tn, sn, who in gimmick_team(party, cfg)[1]:
                out(f"  [기믹 슬롯] {tn} / {sn}: " + (who if who else "비어 있음"))
        bk = pick_break(party, cfg, content, note, have_break)
        if bk:
            out(f"  [브레이크 스킬] {bk[1]} - {bk[2]} (직업 구성 기준 추정)")
    out("(자동 계산한 참고용. 가중치·브레이크 추천은 추정치)")
