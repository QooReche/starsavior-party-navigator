# -*- coding: utf-8 -*-
"""길드 방어전 EX 별의 도전 단계별 클리어율 표 -> data/guild_sim.json (화면 길방 패널의 «시뮬 추정»).

후보 = 길드방어전 추천 상위 k 팀(party_reco 근사 점수, 7단계 EX) + 커뮤니티 사례 팀 1개.
육성 가정 = 표준 육성(build standard) 공·생·방을 배수로 맞춰 파티 전투력 = 권장 전투력 x g(화면 «평균(권장 100%)» 과 같은 방식).
오토 전투, 전투력 보정 model(화면 시뮬과 같은 옵션). 선택 효과 프리셋별 결과는 실측 대조가 없는 «시뮬 추정»이다.

사용: python -X utf8 -I tools/build_guild_sim.py [--runs 60] [--teams 4] [--growth 1,1.5,2,2.5,3]
추가 프리셋 예: --sets off,max,no_void=3330 (효과 순서: 소멸·불멸·쇠락·허무, 각 0~3)
엔진·자료(battlesim, data/guild_bfb.json, data/guild_defense.json)나 추천 자료를 바꾸면 다시 돌린다.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
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
PASS = 0.5     # «클리어 가능» = 클리어율 50% 이상(표시 기준, 가정)
SETS = {'off': [0, 0, 0, 0], 'max': [3, 3, 3, 3]}


def parse_sets(value):
    presets = {}
    for token in value.split(','):
        if token in SETS:
            name, tiers = token, SETS[token][:]
        else:
            name, sep, digits = token.partition('=')
            if (not sep or not name.isidentifier() or name in SETS or len(digits) != 4
                    or any(d not in '0123' for d in digits)):
                raise argparse.ArgumentTypeError('--sets: off,max 또는 이름=3330 형식')
            tiers = [int(d) for d in digits]
        if name in presets:
            raise argparse.ArgumentTypeError('--sets: 중복 이름 ' + name)
        presets[name] = tiers
    if 'off' not in presets:
        raise argparse.ArgumentTypeError('--sets: 하위 호환용 off 필수')
    return presets


def sim_tables(units, leader, growth, sups, tiers, runs, seed, season=None):
    from battlesim.starsavior.guild import load
    import guild_defense as GD
    g=load(season)
    levels=list(range(len(g["challenge"]["levels"])+1))
    tables = {key: {s: {} for s in sups} for key in ('bySupport', 'progBySupport', 'fracBySupport', 'scoreBySupport')}
    for sup in sups:
        row, prow, frow, srow = [], [], [], []
        for lv in levels:
            r = simulate({'units': units, 'leader': leader}, {'guild': {'seasonId':g['season']['id'],'dataVersion':g['dataVersion'],'level': lv, 'support': sup, 'sets': tiers}},
                         {'seed': seed, 'n_runs': runs, 'build': 'standard', 'rules_override': {'power_penalty': 'model'}})
            row.append(r['outcome']['clear_p'])
            prow.append(r['outcome']['progress'])
            # 평균 진행도를 절단하지 않고 판마다 보스 깎은 비율을 계산한다.
            pr = r['prog_runs']
            frow.append(round(sum(max(0.0, min(1.0, GD.prog_parts(g,p)[1])) for p in pr) / len(pr), 4))

            pct=GD.extra_pct(g,lv,tiers)
            scores=[(v*(100+pct)+50)//100 for v in r['guild']['base_scores']] if r.get('guild') else [GD.score_from_prog(g,pct,p) for p in pr]
            srow.append(sum(scores)/len(scores))
        for key, values in zip(tables, (row, prow, frow, srow)):
            tables[key][sup][growth] = values
    return tables


def run_jobs(jobs, workers):
    """각 칸의 seed·판수와 결과 순서는 단일 실행과 같고 독립된 칸만 병렬 계산한다."""
    if workers == 1:
        for job in jobs:
            yield sim_tables(*job)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(sim_tables, *job) for job in jobs]
            for future in futures:
                yield future.result()


def summarize(teams, growth, sups, preset='off', levels=None):
    summary = {}
    for g in growth:
        best = None
        for i, t in enumerate(teams):
            tab = t if preset == 'off' else t['bySets'][preset]
            for sup in sups:
                rr = tab['bySupport'][sup][g]
                ok = [(lv, p) for lv, p in zip(levels if levels is not None else range(len(rr)), rr) if p >= PASS]
                if ok:
                    top, p = max(ok)
                    if best is None or (top, p) > (best['level'], best['p']):
                        best = dict(level=top, team=i, p=p, support=sup)
        summary[g] = best
    return summary


def reco_teams(k, gd=None):
    roster, growth, mains, cfg, tags = PR.load()
    c = cfg['contents'][CONTENT]
    if gd is None:
        tab, st = PR.find_stages(CONTENT, '7단계')[0]
    else:
        from guild_defense import foe_content
        t=foe_content(gd)['tabs'][0];tab,st=t['tab'],t['stages'][0]
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


def scaled_units(db, keys, leader, target, season=None):
    base = simulate({'units': keys, 'leader': leader}, {'guild': {'seasonId':season,'level': 0}}, {'n_runs': 1, 'build': 'standard'})['party']['power']
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
    ap.add_argument('--growth', default='1,1.5,2,2.5,3')
    ap.add_argument('--sets', type=parse_sets, default='off,max')
    ap.add_argument('--workers', type=int, default=1, help='독립 칸 병렬 계산 수(1 = 순차)')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--supports')
    ap.add_argument('--season',type=int)
    ap.add_argument('--out', default=str(ROOT / 'data' / 'guild_sim.json'))
    a = ap.parse_args()
    if a.workers < 1:
        ap.error('--workers 는 1 이상')
    db = get_db()
    from battlesim.starsavior.guild import load
    from guild_defense import ex_step
    gd=load(a.season)
    levels=list(range(len(gd['challenge']['levels'])+1))
    supports=list(dict.fromkeys(['none', *gd['search']['final']['supports']]))
    rec=ex_step(gd)['power']
    growth = ['%g' % float(x) for x in a.growth.split(',')]   # 키 = '1', '1.5', '2'(JS String(숫자) 와 같게 문자열로 둠)
    sups = [s for s in (a.supports or ','.join(supports)).split(',') if s]
    if any(s not in supports for s in sups) or 'none' not in sups:
        raise SystemExit('--supports 는 none 을 포함한 %s 의 부분집합' % supports)
    teams = reco_teams(a.teams,gd)
    if gd['season']['boss']['engine']=='bfb' and COMMUNITY not in [t['keys'] for t in teams]:
        teams.append(dict(src='community', keys=COMMUNITY, leader=0))
    t0 = time.time()
    jobs, slots = [], []
    for t in teams:
        t['names'] = [db.units[k]['n'] for k in t['keys']]
        t['bySets'] = {name: {} for name in a.sets if name != 'off'}
        for g in growth:
            units = scaled_units(db, t['keys'], t['leader'], rec * float(g),gd['season']['id'])
            for name, tiers in a.sets.items():
                jobs.append((units, t['leader'], g, sups, tiers, a.runs, a.seed,gd['season']['id']))
                slots.append((t, g, name))
    print('계산', len(jobs), '칸, workers', a.workers, flush=True)
    for (t, g, name), tables in zip(slots, run_jobs(jobs, a.workers)):
        dest = t if name == 'off' else t['bySets'][name]
        for key, values in tables.items():
            for sup in sups:
                dest.setdefault(key, {}).setdefault(sup, {}).update(values[sup])
        print(t['src'], ','.join(t['keys']), 'x' + g, name, '%.0fs' % (time.time() - t0), flush=True)
    for t in teams:
        t['rates'] = t['bySupport']['none']      # 호환: 지원을 안 고른 경우
    summary = summarize(teams, growth, sups,levels=levels)
    out = dict(
        _note='tools/build_guild_sim.py 가 만든 시뮬 추정(실측 대조 없음). rates[육성 배수] = levels 순서의 별의 도전 클리어율(0단계 = 별의 도전 없음, 알리시아 지원 안 고름), bySupport[지원][육성 배수] = 같은 값을 지원별로.',
        asOf=gd['asOf'], season=gd['season']['id'], dataVersion=gd['dataVersion'], runs=a.runs, seed=a.seed, recPower=rec, growth=growth, levels=levels, pass_p=PASS,
        basis='표준 육성을 파티 전투력 = 권장 전투력 x 배수로 맞춤, 오토 전투, 선택 효과 프리셋 비교, 전투력 보정 적용, 브레이크 스킬 미장착',
        supports=sups, sets=a.sets, teams=teams, summary=summary,
        summaryBySets={name: summarize(teams, growth, sups, name,levels=levels) for name in a.sets if name != 'off'})
    atomic_json(a.out, out, indent=1)
    print('저장', a.out, '%.0fs' % (time.time() - t0))
    if os.path.abspath(a.out) == str(ROOT / 'data' / 'guild_sim.json'):
        from tools.rules_stamp import stamp
        print('규칙 도장', stamp('guild_sim', 'build_guild_sim 재생성'))


if __name__ == '__main__':
    main()
