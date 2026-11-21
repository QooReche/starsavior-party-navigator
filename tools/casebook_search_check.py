"""공략 사례집 기준 탐색 타당성 검사(단계 ②: 탐색이 공략 조합을 놓치지 않는가).

공개 표준 육성·전체 보유만 씀(계정 자료 없음). 원시 결과는 무시되는 local/casebook_search/ 에 둠.

  python -X utf8 -I tools/casebook_search_check.py catalog
  python -X utf8 -I tools/casebook_search_check.py search cosmo1023|cosmo1022|guild [--workers 8]
  python -X utf8 -I tools/casebook_search_check.py eval [--runs 400]
  python -X utf8 -I tools/casebook_search_check.py worker [--data FIXTURE]   (node 드라이버 전용)

탐색 = 실제 화면 정책 JS(cosmo_search.js / guild_planner.js)를 node 로 부르고 전투만 네이티브 파이썬으로 돌림
(tools/casebook_search_check.js). 작전·회랑은 화면 후보 생성의 파이썬 짝(party_reco.top_parties)을 후보로 씀.
재평가 = 사례 편성과 탐색 상위 편성을 같은 시드·같은 판 수로 다시 돌림(탐색에 쓴 시드와 다름).
탐색 정책·기본값은 바꾸지 않음.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
import math
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'local' / 'casebook_search'
FIX1022 = ROOT / 'tests' / 'fixtures' / 'cosmo_raid_1022.json'
SEED = 20261122          # 재평가 시드(탐색 시드 1·2·3·5·13·20261119.. 와 다름)
TOP_Q = 0.2

# 사례 편성. 이름 대응: 편마=asherah-order-striker, 길레=gille(집행자), 에데=haydee, 세레스=ceres(서부 탈환대),
# 메레스=ceres-sun-supporter(메이드 세레스, uid1059 = 엔진 감사 M7), 웨르멘=wedding-carmen, 왈=waltz-asherah(추정),
# 프엠/교수=professor-m(추정), 바샤를=bunny-charlotte(추정), 메북이·메디아=lydia-moon-caster(레디 메이드 퍼피, 추정),
# 수마일=sunshine-cat-smile(추정), 아세라=asherah-voyager(추정), 리디아=lydia(서부 탈환대, M14).
COSMO8, COSMO7 = 'cosmo1023', 'cosmo1022'
CASES = [
    dict(id='01', kind=COSMO8, boss='mogulus', level=18, keys=['asherah-order-striker', 'ceres', 'haydee', 'gille'],
         leader='asherah-order-striker', brk='차원 강습', note='편성·리더·브레이크 모두 글에 있음',
         premise={'ceres': {'spd': 180}, 'asherah-order-striker': {'spd': 187}, 'gille': {'spd': 168}}),
    dict(id='03', kind=COSMO8, boss='mogulus', level=6, keys=['asherah-order-striker', 'gille', 'haydee', 'asherah-voyager'],
         leader=None, brk='행성 정화', note='단계 미기재 → 글의 «뉴비 6~8단계» 하한 6으로 둠. 아세라=보이저(추정)'),
    dict(id='13', kind=COSMO7, boss='carnelia', level=18, keys=['sunshine-cat-smile', 'lyn', 'lydia', 'amora'],
         leader=None, brk='차원 강습', note='수마일=선샤인 캣(추정)',
         premise={'lyn': {'spd': 185, 'er': 12000}, 'lydia': {'spd': 185}, 'sunshine-cat-smile': {'spd': 163}, 'amora': {'spd': 166}}),
    dict(id='14', kind=COSMO7, boss='tyria', level=18, keys=['gwen', 'fei', 'smile', 'luna'],
         leader=None, brk='특이점 관측',
         note='«리사 브레이크» = ORBITAL_ARRAY_LISA(m_SkillID 101) → SI_SINGULARITY_OBSERVATION = 특이점 관측'),
    dict(id='16-1', kind=COSMO8, boss='mogulus', level=18, keys=['asherah-order-striker', 'haydee', 'clarissa', 'sunshine-cat-smile'],
         leader=None, brk=None, note='질문글 3파티 구상. 보스 배정이 없어 세 팀×세 보스 중 최대 합 배정으로 봄', triple='16'),
    dict(id='16-2', kind=COSMO8, boss='baskerville', level=18, keys=['professor-m', 'hilde', 'smile', 'bunny-charlotte'],
         leader=None, brk=None, note='', triple='16'),
    dict(id='16-3', kind=COSMO8, boss='disparity', level=18, keys=['fei', 'gwen', 'amora', 'gille'],
         leader=None, brk=None, note='', triple='16'),
    dict(id='17', kind=COSMO8, boss='baskerville', level=18, keys=['professor-m', 'sunshine-cat-smile', 'gwen', 'waltz-asherah'],
         leader=None, brk=None, note='넷째 자리는 글의 후보 «왈??»(왈츠 아세라)로 채움'),
    dict(id='10', kind='guild', level=12, keys=['amora', 'bunny-charlotte', 'lydia-moon-caster', 'wedding-carmen'],
         leader='amora', brk=None, note='리더는 «아모라 리더 효과» 언급만 있어 아모라/탐색 기본 둘 다 봄'),
    dict(id='12', kind='guild', level=9, keys=['bunny-charlotte', 'lydia-moon-caster', 'wedding-carmen', 'amora'],
         leader=None, brk=None, note='실패 후기(반례). 같은 4명을 9단계에서 봄'),
]
# 부분 편성: 글에 있는 구원자를 포함한 탐색 평가 팀 중 최고를 같은 판 수로 재평가(나머지 자리는 탐색이 채움)
PARTIAL = [
    dict(id='02', kind=COSMO8, boss='mogulus', level=18, members=['asherah-order-striker', 'ceres']),
    dict(id='11', kind='guild', level=12, members=['amora', 'bunny-charlotte']),
    dict(id='15', kind=COSMO7, boss='belgras', level=18, members=['professor-m', 'ceres-sun-supporter']),
    dict(id='18', kind=COSMO8, boss='baskerville', level=18, members=['asherah-order-striker', 'professor-m', 'sunshine-cat-smile']),
]
# 작전·회랑: 표준 육성 진행도 확인만(전원≈0이면 비교 불가)
STAGE_CASES = [
    dict(id='04', stage='clo/성간 회랑/FLOOR 580', keys=['asherah-order-striker', 'gille', 'amora', 'wedding-carmen']),
    dict(id='05', stage='clo/성간 회랑/FLOOR 590', keys=['ceres-sun-supporter', 'asherah-order-striker', 'wedding-carmen', 'amora']),
    dict(id='09', stage='op/얼어붙은 바위 산/SECTOR 44-6', keys=['wedding-carmen', 'ceres-sun-supporter', 'amora', 'professor-m']),
]


def worker(data):
    from battlesim.web import run_auto
    if data:
        from battlesim.starsavior import cosmo_raid
        cosmo_raid.use_data(data)
    for line in sys.stdin:
        m = json.loads(line)
        try:
            for t in m['teams']:
                opts = dict(m.get('options') or {})
                opts.update(t.get('options') or {})
                r = json.loads(run_auto(m['stage'], t['party'], m['n_runs'], m['seed'], opts))
                r = {k: r.get(k) for k in ('prog', 'clear', 'n', 'via', 'progs', 'cosmo')}
                print(json.dumps(dict(type='team', key=t['key'], result=r)), flush=True)
            print(json.dumps(dict(type='done', id=m['id'])), flush=True)
        except Exception as exc:
            print(json.dumps(dict(type='error', msg=repr(exc))), flush=True)


def catalog():
    from battlesim import api
    db = api.get_db()
    rows = []
    for key in sorted(db.units):
        if '@' in key:
            continue
        defs, _ = api._norm_party([key], db, 'fixed', 'standard')
        rows.append(dict(key=key, power=api.party_power(defs), stats=defs[0].stats))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'catalog.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    return rows


def break_max():
    from battlesim.mc import break_skill_levels
    lv = break_skill_levels()
    names = ['큐브 과부하', '특이점 관측', '스타피어서', '차원 강습', '행성 정화']
    return [dict(name=n, level=len(lv[n]['dmg'])) for n in names if n in lv]


def search_file(kind, level=18):
    """탐색 결과 파일. 코스모는 난이도별(18 = 기본 파일명)."""
    return OUT / ((kind if kind == 'guild' or level == 18 else '%s-L%d' % (kind, level)) + '.json.gz')


def search(kind, workers, level=18):
    if not (OUT / 'catalog.json').exists():
        catalog()
    data = ''
    if kind == COSMO7:
        data = str(FIX1022)
    level = str(level)
    cmd = ['node', '--max-old-space-size=8192', str(ROOT / 'tools/casebook_search_check.js'),
           'guild' if kind == 'guild' else 'cosmo', str(search_file(kind, int(level))), str(OUT / 'catalog.json'),
           str(workers), sys.executable, data, level, json.dumps(break_max(), ensure_ascii=False)]
    subprocess.run(cmd, check=True, cwd=ROOT)


# ---------- 재평가 ----------

def party_spec(keys, leader, overrides=None):
    units = []
    for k in keys:
        u = {'key': k, 'build': 'standard'}
        if overrides and k in overrides:
            # 글의 목표 능력치를 최종값으로 덮음(그 능력치의 상시 % 만 뺌). 나머지는 표준 육성 그대로
            u.update(stats_override=overrides[k], stats_final=True)
        units.append(u)
    return {'units': units, 'leader': keys.index(leader) if leader else 0}


def default_order(keys):
    """탐색 기본 배치(guild_search.party): 디펜더·서포터 먼저 → 전투력 순, 첫 칸 리더."""
    cat = {r['key']: r for r in json.loads((OUT / 'catalog.json').read_text(encoding='utf-8'))}
    cls = {r['key']: r['cls'] for r in roster()}
    front = ('디펜더', '서포터')
    return sorted(keys, key=lambda k: (0 if cls[k] in front else 1, -cat[k]['power'], k))


_ROSTER = []


def roster():
    if not _ROSTER:
        import re
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        _ROSTER.extend(json.loads(re.search(r'const D=(\{[^\n]+\});', html).group(1))['roster'])
    return _ROSTER


def battle(task):
    """task = (label, kind, boss/stage, level, order, leader, brk, sup, runs) -> per-run arrays."""
    from battlesim import simulate
    from battlesim.web import _enc
    from battlesim.starsavior import cosmo_raid
    label, kind, target, level, order, leader, brk, sup, runs, *extra = task
    cosmo_raid.use_data(str(FIX1022) if kind == COSMO7 else None)
    party = party_spec(order, leader, extra[0] if extra else None)
    lv = {b['name']: b['level'] for b in break_max()}
    op = {'n_runs': runs, 'seed': SEED}
    if brk:
        op['break_skill'] = {'name': brk, 'level': lv[brk]}
    if kind in (COSMO7, COSMO8):
        op['cosmo_raid'] = {'boss': target, 'step': 3, 'level': level}
        stage = '코스모 게이트'
    elif kind == 'guild':
        op['guild'] = {'level': level, 'sets': [0, 0, 0, 0], 'support': sup or 'none'}
        stage = 'guild/BFB/길드 방어전 EX스테이지'
    else:
        stage = target
    r = simulate(party, _enc(stage, dict(op)), dict(op, **({} if kind in ('guild',) else {})))
    o = r['outcome']
    cr = r.get('cosmo_raid')
    row = dict(label=label, kind=kind, target=target, level=level, order=order, leader=leader or order[0], brk=brk, sup=sup, n=o['n_runs'],
               progress=o.get('progress'), clear=o['clear_p'], progs=r.get('prog_runs'))
    if cr:
        row.update(scores=cr['score_runs'], clears=[bool(c) for c in cr['clear_runs']])
    return row


def topq(xs, q=TOP_Q):
    s = sorted(xs, reverse=True)
    m = max(1, math.ceil(len(s) * q - 1e-9))
    return sum(s[:m]) / m


def boot_diff(a, b, stat, n=2000, seed=7):
    """(stat(a)-stat(b)) 의 부트스트랩 95% 구간(독립 표본)."""
    rnd = random.Random(seed)
    d = []
    for _ in range(n):
        x = [a[rnd.randrange(len(a))] for _ in a]
        y = [b[rnd.randrange(len(b))] for _ in b]
        d.append(stat(x) - stat(y))
    d.sort()
    return d[int(n * .025)], d[int(n * .975)]


def load_search(kind, level=18):
    p = search_file(kind, level)
    if not p.exists() and kind != 'guild':
        p = search_file(kind, 18)
    if not p.exists():
        return None
    with gzip.open(p, 'rt', encoding='utf-8') as f:
        return json.load(f)


def search_teams(kind, boss, top=5, level=18):
    """탐색 결과에서 보스별 비교 대상: 최종 1위 삼중의 해당 보스 팀(브레이크 포함) + 정밀(재순위) 단계 단일 보스 상위."""
    s = load_search(kind, level)
    if not s:
        return []
    out = []
    if kind == 'guild':
        for i, t in enumerate(s['result']['rows'][:top]):
            t = t.get('teams', [t])[0] if 'teams' in t else t
            out.append(dict(label='탐색 %d위' % (i + 1), order=t['order'], leader=t.get('leaderKey') or t['order'][0],
                            brk=(t.get('options') or {}).get('break_skill', {}) and t['options']['break_skill'].get('name') if t.get('options') else t.get('brk'),
                            sup=t.get('sup'), level=t.get('level')))
        # 탐색은 점수가 큰 단계를 고름. 사례 단계와 같은 단계로 본선(40판)에서 평가된 팀도 비교 대상에 넣음
        fin = [j for p in s['phases'] if p['runs'] == 40 for j in p['jobs'] if j['level'] == level]
        fin.sort(key=lambda j: -((j.get('clear') or 0) * 10 + (j.get('prog') or 0)))
        seen = set()
        for j in fin:
            k = tuple(sorted(j['keys']))
            if k in seen:
                continue
            seen.add(k)
            out.append(dict(label='탐색 본선 %d단계 %d위' % (level, len(seen)), order=j['order'], leader=j['leaderKey'] or j['order'][0],
                            brk=j['brk'], sup=j['sup'], level=level))
            if len(seen) >= 3:
                break
        return out
    bosses = s['meta']['bosses']
    bi = bosses.index(boss)
    row = s['result']['rows'][0]
    t = row['teams'][bi]
    out.append(dict(label='탐색 최종 1위 삼중', order=t['order'], leader=t.get('leaderKey') or t['order'][0], brk=t.get('brk')))
    # 정밀 단계(재순위) 단일 보스 상위: 가장 판 수가 많은(rerank) 단계의 이 보스 작업
    rer = [p for p in s['phases'] if p['runs'] == s['meta']['settings']['rerank']['runs']]
    jobs = [j for p in rer for j in p['jobs'] if j['boss'] == boss and j['cosmo']]
    jobs.sort(key=lambda j: -j['cosmo']['top'])
    seen = {tuple(sorted(t['order']))}
    for j in jobs:
        k = tuple(sorted(j['keys']))
        if k in seen:
            continue
        seen.add(k)
        out.append(dict(label='탐색 정밀 단일 %d위' % (len(out)), order=j['order'], leader=j['leaderKey'], brk=None))
        if len(out) > top:
            break
    return out


def trace(kind, case):
    """사례 4명이 탐색 각 단계에 들어갔는지·몇 위였는지."""
    s = load_search(kind, case.get('level', 18))
    if not s:
        return None
    ids = tuple(sorted(case['keys']))
    rows = []
    for p in s['phases']:
        js = [j for j in p['jobs'] if (kind == 'guild' or j['boss'] == case.get('boss'))]
        if not js:
            continue
        def val(j):
            if j.get('cosmo'):
                return j['cosmo']['top']
            return (j.get('clear') or 0) * 10 + (j.get('prog') or 0)
        best = {}
        for j in js:
            k = tuple(sorted(j['keys']))
            best[k] = max(best.get(k, -1), val(j))
        order = sorted(best.items(), key=lambda kv: -kv[1])
        rank = next((i + 1 for i, (k, _) in enumerate(order) if k == ids), None)
        rows.append(dict(phase=p['i'], runs=p['runs'], teams=len(order), rank=rank))
    return rows


def stage_candidates(content, query, k=10):
    """화면 일반 추천의 후보 생성 파이썬 짝(party_reco.top_parties, 근사 점수 상위 k). 전체 보유."""
    import party_reco as pr
    roster_, growth, mains, cfg, tags = pr.load()
    c = cfg['contents'][content]
    tab, st = pr.find_stages(content, query)[0]
    enemies = pr.stage_enemies(st)
    pr._DM[0] = min(1.0, (st['enemy_total'] - 1) / 2)
    pr._DM[1] = cfg['damage']['weightBoss'] if c.get('boss', False) else cfg['damage']['weightMob']
    pr._SB[0] = (st.get('season_bonus_latest') or {}).get('bonuses', [])
    pr._GIM[0] = pr.stage_gimmicks(f"{pr.FOE_KEYS[content]}|{tab}|{st['name']}", cfg)
    cands = []
    for s in roster_:
        v, parts = pr.score(s, growth, mains, cfg, c['main'], enemies, c.get('boss', False))
        cands.append({'s': s, 'g': growth.get(s['key']), 'score': v, 'parts': parts})
    def_pen = c.get('defenderPenalty', cfg['weights']['defenderPenalty'])
    return [[x['s']['key'] for x in combo] for combo, _, _ in pr.top_parties(cands, cfg, tags, def_pen, k)]


def partial_best(c):
    """탐색이 실제로 평가한 팀 중 글의 구원자를 모두 포함한 최고(가장 많은 판 수 단계 기준) + 그 단계의 전체 순위."""
    s = load_search(c['kind'], c.get('level', 18))
    if not s:
        return None
    want = set(c['members'])
    best = None
    for p in sorted(s['phases'], key=lambda p: -p['runs']):
        js = [j for j in p['jobs'] if (c['kind'] == 'guild' or j['boss'] == c['boss'])]
        if not js:
            continue
        val = (lambda j: j['cosmo']['top']) if c['kind'] != 'guild' else (lambda j: (j.get('clear') or 0) * 10 + (j.get('prog') or 0))
        js = sorted([j for j in js if j.get('cosmo') or c['kind'] == 'guild'], key=lambda j: -val(j))
        hit = [(i + 1, j) for i, j in enumerate(js) if want <= set(j['keys'])]
        if hit:
            rank, j = hit[0]
            best = dict(order=j['order'], leader=j['leaderKey'], sup=j.get('sup'), phase=p['i'], runs=p['runs'], rank=rank, of=len(js))
            break
    return best


ALT_L6 = ('01', '13', '14')
SUPPORTS = ['none', 'fire', 'gust', 'focus', 'strike', 'mountain']


def case_variants(c):
    """(이름, 배치, 리더, 브레이크). 글에 자리 정보가 없으므로 자리는 탐색 기본 배치, 리더만 글을 따름."""
    dflt = default_order(c['keys'])
    out = [('사례 그대로', dflt, c['leader'], c['brk'])]
    for k in dflt:
        if k != (c['leader'] or dflt[0]):
            out.append(('사례 4명·리더 ' + k, dflt, k, c['brk']))
    if c['kind'] != 'guild':
        for b in break_max():
            if b['name'] != c['brk']:
                out.append(('사례 4명·사례 리더+' + b['name'], dflt, c['leader'], b['name']))
        if c['brk']:
            out.append(('사례 4명·사례 리더·미장착', dflt, c['leader'], None))
    return out


def evaluate(runs, workers):
    tasks = []
    meta = []
    cases = list(CASES)
    for c in CASES:
        if c['kind'] in (COSMO7, COSMO8) and c['id'] in ALT_L6:
            # 보조: 표준 육성이 조금 더 버티는 6단계(탐색도 6단계로 다시 돌린 결과와 비교). 판정 표의 본행은 글의 단계
            cases.append(dict(c, id=c['id'] + '@L6', level=6))
    for c in cases:
        kind, tgt = c['kind'], c.get('boss')
        for lab, order, leader, brk in case_variants(c):
            for sp in (SUPPORTS if kind == 'guild' else [None]):
                tasks.append(('%s|%s%s' % (c['id'], lab, '|' + sp if sp else ''), kind, tgt, c['level'], order, leader, brk, sp, runs))
        if c.get('premise'):
            # 공략 전제(속도·저항 목표) 반영: 판정에는 넣지 않는 진단용 행(표준 육성이 아님)
            tasks.append(('%s|전제 반영(글의 속도·저항 목표)' % c['id'], kind, tgt, c['level'], default_order(c['keys']), c['leader'],
                          c['brk'], None, runs, c['premise']))
        for t in search_teams(kind, tgt, level=c['level']):
            tasks.append(('%s|%s' % (c['id'], t['label']), kind, tgt, c['level'], t['order'], t['leader'], t['brk'], t.get('sup'), runs))
        meta.append(dict(case=c, trace=trace(kind, c)))
    # 질문글 16: 세 팀을 세 보스 모두에서 평가(보스 배정 자유)
    for c in [x for x in CASES if x.get('triple')]:
        for b in ['mogulus', 'baskerville', 'disparity']:
            if b != c['boss']:
                tasks.append(('%s|보스 %s' % (c['id'], b), c['kind'], b, c['level'], default_order(c['keys']), None, None, None, runs))
    for c in PARTIAL:
        best = partial_best(c)
        meta.append(dict(case=c, partial=best))
        if best:
            tasks.append(('%s|사례 부분 편성 포함 최고' % c['id'], c['kind'], c.get('boss'), c['level'], best['order'], best['leader'], None,
                          best.get('sup'), runs))
            for t in search_teams(c['kind'], c.get('boss'), level=c['level'])[:1]:
                tasks.append(('%s|%s' % (c['id'], t['label']), c['kind'], c.get('boss'), c['level'], t['order'], t['leader'],
                              t['brk'] if c['kind'] == 'guild' else None, t.get('sup'), runs))
    for c in STAGE_CASES:
        tasks.append(('%s|사례 그대로' % c['id'], 'stage', c['stage'], None, c['keys'], None, None, None, 40))
        content = '회랑' if c['stage'].startswith('clo/') else '작전'
        for i, keys in enumerate(stage_candidates(content, c['stage'].split('/')[-1])[:5]):
            tasks.append(('%s|탐색 근사 후보 %d위' % (c['id'], i + 1), 'stage', c['stage'], None, default_order(keys), None, None, None, 40))
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(battle, tasks, chunksize=1))
    out = dict(seed=SEED, runs=runs, rows=res, meta=meta)
    (OUT / 'eval.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    summarize(out)


def metric_of(r):
    """탐색 순위 지표와 같은 쪽: 코스모 = 판별 점수 상위 20% 평균, 길드·스테이지 = 진행도 상위 20% 평균(길드 점수는 진행도 단조)."""
    xs = r['scores'] if r.get('scores') else (r['progs'] or [0])
    return xs, topq(xs)


def verdicts(out):
    by = {}
    for r in out['rows']:
        by.setdefault(r['label'].split('|')[0], []).append(r)
    res = []
    for cid, rs in by.items():
        case = [r for r in rs if r['label'].split('|')[1].startswith('사례')]
        srch = [r for r in rs if r['label'].split('|')[1].startswith('탐색')]
        if not case or not srch:
            continue
        cb = max(case, key=lambda r: metric_of(r)[1])
        sb = max(srch, key=lambda r: metric_of(r)[1])
        as_is = [r for r in case if r['label'].split('|')[1] == '사례 그대로']
        a0 = max(as_is, key=lambda r: metric_of(r)[1]) if as_is else cb
        d = metric_of(cb)[1] - metric_of(sb)[1]
        lo, hi = boot_diff(metric_of(cb)[0], metric_of(sb)[0], topq)
        d0 = metric_of(a0)[1] - metric_of(sb)[1]
        lo0, hi0 = boot_diff(metric_of(a0)[0], metric_of(sb)[0], topq)
        v = '탐색이 놓침' if lo > 0 else ('탐색 우위' if hi < 0 else '유의차 없음')
        res.append(dict(id=cid, case_best=cb['label'].split('|', 1)[1], case_best_v=metric_of(cb)[1], case_best_clear=cb['clear'],
                        case_best_prog=cb['progress'], as_is=metric_of(a0)[1], as_is_clear=a0['clear'], as_is_prog=a0['progress'],
                        search_best=sb['label'].split('|', 1)[1], search_best_v=metric_of(sb)[1], search_best_clear=sb['clear'],
                        search_best_prog=sb['progress'], search_order=sb['order'], search_leader=sb['leader'], search_brk=sb['brk'],
                        search_sup=sb['sup'], diff=d, ci=[lo, hi], diff_as_is=d0, ci_as_is=[lo0, hi0], verdict=v))
    return res


def summarize(out):
    rows = out['rows']
    by = {}
    for r in rows:
        by.setdefault(r['label'].split('|')[0], []).append(r)
    lines = []
    for cid, rs in by.items():
        lines.append('== ' + cid)
        for r in rs:
            if r.get('scores'):
                lines.append('  %-44s top=%10.0f mean=%10.0f clear=%.3f frac=%.4f lead=%s brk=%s order=%s' % (
                    r['label'].split('|', 1)[1], topq(r['scores']), sum(r['scores']) / len(r['scores']), r['clear'], r['progress'],
                    r['leader'], r['brk'], ','.join(r['order'])))
            else:
                lines.append('  %-44s prog=%.4f top20prog=%.4f clear=%.3f lead=%s sup=%s brk=%s order=%s' % (
                    r['label'].split('|', 1)[1], r['progress'] or 0, topq(r['progs'] or [0]), r['clear'], r['leader'], r['sup'],
                    r['brk'], ','.join(r['order'])))
    for m in out['meta']:
        lines.append('trace %s: %s' % (m['case']['id'], m.get('trace') if 'trace' in m else m.get('partial')))
    v = verdicts(out)
    for x in v:
        lines.append(('verdict %(id)s: %(verdict)s case_best=%(case_best)s %(case_best_v).4g / search=%(search_best)s '
                      '%(search_best_v).4g diff=%(diff).4g ci=%(ci)s as_is_diff=%(diff_as_is).4g ci=%(ci_as_is)s') % x)
    (OUT / 'verdicts.json').write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding='utf-8')
    text = '\n'.join(lines)
    (OUT / 'eval.txt').write_text(text, encoding='utf-8')
    print(text)


def compare(a_label, b_label, metric='top'):
    out = json.loads((OUT / 'eval.json').read_text(encoding='utf-8'))
    m = {r['label']: r for r in out['rows']}
    a, b = m[a_label], m[b_label]
    if a.get('scores'):
        stat = topq if metric == 'top' else (lambda xs: sum(xs) / len(xs))
        return stat(a['scores']) - stat(b['scores']), boot_diff(a['scores'], b['scores'], stat)
    return (sum(a['progs']) / len(a['progs']) - sum(b['progs']) / len(b['progs']),
            boot_diff(a['progs'], b['progs'], lambda xs: sum(xs) / len(xs)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['worker', 'catalog', 'search', 'eval', 'summary', 'compare'])
    ap.add_argument('arg', nargs='*')
    ap.add_argument('--data', default='')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--runs', type=int, default=400)
    a = ap.parse_args()
    if a.cmd == 'worker':
        worker(a.data)
    elif a.cmd == 'catalog':
        print(len(catalog()))
    elif a.cmd == 'search':
        search(a.arg[0], a.workers, int(a.arg[1]) if len(a.arg) > 1 else 18)
    elif a.cmd == 'eval':
        evaluate(a.runs, a.workers)
    elif a.cmd == 'summary':
        summarize(json.loads((OUT / 'eval.json').read_text(encoding='utf-8')))
    elif a.cmd == 'compare':
        print(compare(a.arg[0], a.arg[1], a.arg[2] if len(a.arg) > 2 else 'top'))


if __name__ == '__main__':
    main()
