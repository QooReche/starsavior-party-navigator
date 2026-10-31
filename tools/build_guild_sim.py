# -*- coding: utf-8 -*-
"""길드 방어전 EX 별의 도전 단계별 클리어율 표 -> data/guild_sim.json (화면 길방 패널의 «시뮬 추정»).

후보 = 길드방어전 추천 상위 k 팀(party_reco 근사 점수, 7단계 EX) + 커뮤니티 사례 팀 1개.
육성 가정 = 표준 육성(build standard) 공·생·방을 배수로 맞춰 파티 전투력 = 권장 전투력 x g(화면 «평균(권장 100%)» 과 같은 방식).
오토 전투, 전투력 보정 model(화면 시뮬과 같은 옵션). 선택 효과는 끔. 결과는 실측 대조가 없는 «시뮬 추정»이다.

사용: python -X utf8 -I tools/build_guild_sim.py [--runs 60] [--teams 4] [--growth 1,1.5,2]
엔진·자료(battlesim, data/guild_bfb.json, data/guild_defense.json)나 추천 자료를 바꾸면 다시 돌린다.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import party_reco as PR                                   # noqa: E402
from battlesim import simulate                            # noqa: E402
from battlesim.fileio import atomic_json                  # noqa: E402
from battlesim.starsavior.data import get_db              # noqa: E402
from battlesim.starsavior.parser import UnitDef           # noqa: E402

CONTENT = '길드방어전'
# 커뮤니티 EX 12단 클리어 사례(arca 187456382: 웨딩 카르멘 + 아모라 + 메레스 + 티리아). «메레스» = 신규 구원자 메이드 세레스
# (세레스, 유닛 1059, 키 ceres-sun-supporter; 사용자 확인 2026-10-30).
COMMUNITY =['wedding-carmen', 'ceres-sun-supporter', 'amora', 'tyria']
LEVELS = list(range(0, 13))
PASS = 0.5     # «클리어 가능» = 클리어율 50% 이상(표시 기준, 가정)


def reco_teams(k):
    roster, growth, mains, cfg, tags = PR.load()
    c = cfg['contents'][CONTENT]
    tab, st = PR.find_stages(CONTENT, '7단계')[0]
    enemies = PR.stage_enemies(st)
    def_pen = c.get('defenderPenalty', cfg['weights']['defenderPenalty'])
    # recommend() 와 같은 전처리(근사 점수의 화력 가중·시즌 보너스·기믹)
    PR._DM[0] = min(1.0, (st['enemy_total'] - 1) / 2)
    PR._DM[1] = cfg['damage']['weightBoss']
    PR._SB[0] = (st.get('season_bonus_latest') or {}).get('bonuses', [])
    PR._GIM[0] = PR.stage_gimmicks(f"{PR.FOE_KEYS[CONTENT]}|{tab}|{st['name']}", cfg)
    cands = []
    for s in roster:
        v, parts = PR.score(s, growth, mains, cfg, c['main'], enemies, True)
        cands.append({'s': s, 'g': growth.get(s['key']), 'score': v, 'parts': parts})
    out = []
    for combo, v, _ in PR.top_parties(cands, cfg, tags, def_pen, k):
        front, back = PR.place(list(combo))
        party = front + back
        ld = PR.leader_pick(party, cfg, tags)
        out.append(dict(src='reco', keys=[x['s']['key'] for x in party], leader=party.index(ld[0]) if ld else None))
    return out


def scaled_units(db, keys, leader, target):
    base = simulate({'units': keys, 'leader': leader}, {'guild': {'level': 0}}, {'n_runs': 1, 'build': 'standard'})['party']['power']
    k = target / base
    units = []
    for key in keys:
        d = UnitDef(db, key, 200, 10, 0, 'fixed', build='standard')
        units.append(dict(key=key, build='standard', stats_override={s: int(d.stats[s] * k + 0.5) for s in ('atk', 'hp', 'def')}))
    return units


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=60)
    ap.add_argument('--teams', type=int, default=4)
    ap.add_argument('--growth', default='1,1.5,2')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--out', default=str(ROOT / 'data' / 'guild_sim.json'))
    a = ap.parse_args()
    db = get_db()
    gd = json.load(open(ROOT / 'data' / 'guild_defense.json', encoding='utf-8'))
    bfb = json.load(open(ROOT / 'data' / 'guild_bfb.json', encoding='utf-8'))
    rec = bfb['power']
    growth = ['%g' % float(x) for x in a.growth.split(',')]   # 키 = '1', '1.5', '2'(JS String(숫자) 와 같게 문자열로 둠)
    teams = reco_teams(a.teams)
    if COMMUNITY not in [t['keys'] for t in teams]:
        teams.append(dict(src='community', keys=COMMUNITY, leader=0))
    t0 = time.time()
    for t in teams:
        t['names'] = [db.units[k]['n'] for k in t['keys']]
        t['rates'] = {}
        for g in growth:
            units = scaled_units(db, t['keys'], t['leader'], rec * float(g))
            row = []
            for lv in LEVELS:
                r = simulate({'units': units, 'leader': t['leader']}, {'guild': {'level': lv}},
                             {'seed': a.seed, 'n_runs': a.runs, 'build': 'standard', 'rules_override': {'power_penalty': 'model'}})
                row.append(r['outcome']['clear_p'])
            t['rates'][str(g)] = row
            print(t['src'], ','.join(t['keys']), 'x' + g, row, '%.0fs' % (time.time() - t0), flush=True)
    summary = {}
    for g in growth:
        best = None
        for i, t in enumerate(teams):
            ok = [lv for lv, p in zip(LEVELS, t['rates'][str(g)]) if p >= PASS]
            top = max(ok) if ok else None
            if top is not None and (best is None or top > best['level'] or (top == best['level'] and t['rates'][str(g)][top] > best['p'])):
                best = dict(level=top, team=i, p=t['rates'][str(g)][top])
        summary[str(g)] = best
    out = dict(
        _note='tools/build_guild_sim.py 가 만든 시뮬 추정(실측 대조 없음). rates[육성 배수] = 별의 도전 0~12단계 클리어율(0단계 = 별의 도전 없음).',
        asOf=gd['asOf'], season=gd['season']['id'], runs=a.runs, seed=a.seed, recPower=rec, growth=growth, levels=LEVELS, pass_p=PASS,
        basis='표준 육성을 파티 전투력 = 권장 전투력 x 배수로 맞춤, 오토 전투, 선택 효과 끔, 전투력 보정 적용',
        teams=teams, summary=summary)
    atomic_json(a.out, out, indent=1)
    print('저장', a.out, '%.0fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
