"""foe.js(raw) -> foe_stages.json + foe_summary.md. 실행: python -X utf8 -I build_foe.py (작업 폴더 기준 경로는 이 파일 위치로 계산)"""
import json, re, os, collections as C

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')  # 저장소 루트
s = open(os.path.join(HERE, 'raw', 'foe.js'), encoding='utf8').read()  # 데이터북 data/foe.js 를 tools/raw/ 에 내려받아 둔다
m = re.search(r'__SSD\.foe=', s)
d, _ = json.JSONDecoder().raw_decode(s[m.end():])

EL = {'태양': 'sun', '달': 'moon', '별': 'star', '질서': 'order', '혼돈': 'chaos'}
SKEY = ['hp', 'atk', 'def', 'spd', 'crit', 'critdmg', 'hit', 'evade', 'abs_evade', 'tough']
SK_NST = ['NST_HP', 'NST_ATK', 'NST_DEF', 'NST_TURN_SPEED', 'NST_RATE_CRITICAL', 'NST_RATE_CRITICAL_DAMAGE',
          'NST_RATE_EFFECT_HIT', 'NST_RATE_EFFECT_EVADE', 'NST_RATE_DEFINITE_EFFECT_EVADE', 'NST_SUPER_ARMOR']
RATE = {'NST_NV_RATE_HP': 0, 'NST_NV_RATE_ATK': 1, 'NST_NV_RATE_DEF': 2, 'NST_NV_RATE_TURN_SPEED': 3}
U, X, SK, AK = d['u'], d['x'], d['s'], d['ak']

ROLE_EN = {'스트라이커': 'striker', '캐스터': 'caster', '어쌔신': 'assassin', '레인저': 'ranger', '디펜더': 'defender', '서포터': 'supporter'}

# 유닛별 광역 여부/패시브
def unit_info(u):
    sks = [SK[i] for i in u['sk']]
    aoe = any(x.get('tg') == '적 전체' and x['ty'] in ('액티브', '트리거') for x in sks)
    passives = [x['n'] for x in sks if x['ty'] == '패시브']
    return aoe, passives
UI = [unit_info(u) for u in U]

def adj_text(x):
    out = []
    for a in (x or {}).get('a', []):
        k = AK[a[0]]
        v = a[1]
        out.append(f"{k[0]} {'+' if v > 0 else ''}{(v/100) if k[2] else v}{'%' if k[2] else ''}")
    return out

def stats(u, x, st):
    L = (x and x.get('lv')) or st.get('lv') or 1
    b = list(u['b'])
    for i in range(3):
        b[i] += u['gw'][i] * (L - 1)
    mul = [1, 1, 1, 1]
    for a in (x or {}).get('a', []):
        k = AK[a[0]][1]; v = a[1]
        if k in RATE: mul[RATE[k]] += v / 10000
        elif k in SK_NST: b[SK_NST.index(k)] += v
    for i in range(4): b[i] = int(b[i] * mul[i] + 1e-9)
    return dict(zip(SKEY[:4], b[:4])), L

def enemy(ui, xi, st):
    u = U[ui]; x = X[xi] if xi is not None else None
    el = (x and x.get('el')) or u['el']
    boss = bool((x and x.get('b')) or u['g'] == '보스')
    elite = bool((x and x.get('e')) or u['g'] == '정예')
    stt, L = stats(u, x, st)
    aoe, pas = UI[ui]
    return {'name': u['n'], 'title': u.get('ti'), 'element': EL.get(el, el), 'role': ROLE_EN.get(u['r'], u['r']), 'role_kr': u['r'],
            'attackType': u['k'], 'boss': boss, 'elite': elite, 'level': L, 'stats': stt, 'aoe': aoe,
            'passives': pas, 'adjust': adj_text(x), 'immune': [i['n'] for i in u.get('im', [])]}

def build_stage(st):
    ens = {}   # (ui,xi) -> record
    waves = []
    total = C.Counter(); aoe_n = 0; n_all = 0; defn = 0; roles = C.Counter()
    for wi, w in enumerate(st['w']):
        cnt = C.Counter()
        for e in w:
            ui, xi = e[0], (e[1] if len(e) > 1 else None)
            cnt[(ui, xi)] += 1
            if (ui, xi) not in ens:
                ens[(ui, xi)] = enemy(ui, xi, st)
        waves.append(cnt)
    for k, rec in ens.items():
        rec['count_by_wave'] = [c[k] for c in waves]
        rec['count'] = sum(rec['count_by_wave'])
        n = rec['count']; n_all += n
        total[rec['element']] += n; roles[rec['role']] += n
        if rec['aoe']: aoe_n += n
    out = {'name': st['n'], 'level': st.get('lv'), 'recommended_power': st['bp'], 'wave_count': len(st['w']),
           'enemy_total': n_all,
           'dominant_element': total.most_common(1)[0][0] if total else None,
           'element_counts': dict(total), 'role_counts': dict(roles),
           'aoe_ratio': round(aoe_n / n_all, 3) if n_all else None,
           'defender_ratio': round(roles['defender'] / n_all, 3) if n_all else None,
           'has_boss': any(r['boss'] for r in ens.values()),
           'enemies': list(ens.values())}
    if st.get('fx'): out['fx'] = st['fx']
    if st.get('fix'): out['fixed_player'] = {'level': st['fix'][0], 'resonance': st['fix'][1]}
    if st.get('lt'): out['turn_limit'] = st['lt']
    if st.get('sea'): out['season_bonus_latest'] = {'season': st['sea'][0][0], 'bonuses': [{'cond': a, 'text': b} for a, b in st['sea'][0][1]], 'kind': st['sea'][0][2] if len(st['sea'][0]) > 2 else None}
    if st.get('ch'): out['star_challenge_ref'] = st['ch']
    if st.get('pick'): out['star_pick'] = st['pick']
    if st.get('sm'):
        out['summons'] = [{'summoner': who, 'summoned': [dict(enemy(ui, xi, st), count=n) for ui, xi, n in lst]} for g, who, lst in st['sm']]
    return out

contents = []
for g in d['g']:
    tabs = []
    for t in g['tabs']:
        tabs.append({'tab': t['t'], 'section': t.get('sec'), 'stages': [build_stage(st) for st in t['s']]})
    contents.append({'key': g['k'], 'name': g['t'], 'tabs': tabs})

notes = [
 "원본: starsavior-databook.pages.dev data/foe.js (window.__SSD.foe). g=콘텐츠>tabs>s(스테이지), s.w=웨이브 목록, 웨이브=[유닛idx, 변형idx(x)] 목록(같은 항목 반복=여러 마리).",
 "element: sun=태양 moon=달 star=별 order=질서 chaos=혼돈. 변형 x.el 이 있으면 유닛 기본 속성을 덮어씀. 유닛 원본 기본 속성은 대부분 혼돈이지만 스테이지 변형으로 3속성이 지정되는 경우가 많음.",
 "role: 원본 r(스트라이커/캐스터/어쌔신/레인저/디펜더/서포터). attackType: 원본 k(참격/타격/원소/정신/공허). 필드 의미는 앱 표기 기준(확정).",
 "boss: 변형 x.b 또는 유닛 g=='보스'. elite: x.e 또는 g=='정예'. (추정: x.e 는 정예 표시)",
 "level: 변형 x.lv > 스테이지 lv > 1. stats: 앱(app.js)과 같은 공식으로 계산(기본 b + gw*(Lv-1), 변형 a 보정 반영). 생명력/공격력/방어력 gw 성장은 앱 코드 근거. 별의 도전 보정은 미반영.",
 "aoe(적 광역 여부): 해당 유닛 스킬 중 액티브/트리거 대상이 '적 전체'인 것이 하나라도 있으면 true. 스킬 사용 빈도·쿨타임은 반영 안 함(추정 지표).",
 "dominant_element: 스테이지 전 웨이브의 적 수(소환 제외) 기준 최다 속성. 동률이면 먼저 나온 속성. 작전·회랑은 3속성이 균등해 동률이 많음.",
 "aoe_ratio: 광역 스킬 보유 적 수 / 전체 적 수. defender_ratio: 디펜더 수 / 전체 적 수 (필요 역할 힌트).",
 "recommended_power=원본 bp(권장 전투력). 성간 회랑 등 lv 가 없는 스테이지는 level=null.",
 "fx(스테이지 효과), fix(구원자 레벨·공명 고정), lt(턴 제한), sea(시즌 보너스, 가장 최근만), sm(소환 적)은 원본 필드 그대로 의미 해석(sea 의 'ex'/'pick' 종류는 의미 추정 불가, 그대로 kind 에 보존).",
 "star_challenge_ref(ch)/star_pick(pick): 별의 도전 EX 참조 키. 의미는 앱 코드 근거, 상세 보정치는 raw star 테이블에 있어 미포함.",
]
res = {'_source': 'https://starsavior-databook.pages.dev/data/foe.js?v=48a4b5df', '_notes': notes, 'contents': contents}
json.dump(res, open(os.path.join(ROOT, 'data', 'foe_stages.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=None, separators=(',', ':'))

# ---- 요약
stages = [(c, t, st) for c in contents for t in c['tabs'] for st in t['stages']]
lines = ['# 팬 데이터북 적 정보 요약', '', '원본: https://starsavior-databook.pages.dev/#foe (data/foe.js). 생성: build_foe.py', '', '## 콘텐츠별 규모', '',
         '| 콘텐츠 | 탭 | 스테이지 | 적 인스턴스(웨이브 합) | 보스 스테이지 | 평균 aoe_ratio | 평균 defender_ratio |', '|---|---|---|---|---|---|---|']
tot_e = 0
for c in contents:
    sts = [st for t in c['tabs'] for st in t['stages']]
    ne = sum(s_['enemy_total'] for s_ in sts); tot_e += ne
    av = lambda k: sum(s_[k] or 0 for s_ in sts) / len(sts)
    lines.append(f"| {c['name']} ({c['key']}) | {len(c['tabs'])} | {len(sts)} | {ne} | {sum(s_['has_boss'] for s_ in sts)} | {av('aoe_ratio'):.2f} | {av('defender_ratio'):.2f} |")
lines += ['', f'합계: 콘텐츠 {len(contents)}, 스테이지 {len(stages)}, 적 인스턴스 {tot_e}, 고유 적 유닛(원본 u) {len(U)}', '',
          '## 적 속성 분포 (콘텐츠별 적 인스턴스 수)', '', '| 콘텐츠 | sun | moon | star | order | chaos |', '|---|---|---|---|---|---|']
for c in contents:
    cc = C.Counter()
    for t in c['tabs']:
        for st in t['stages']: cc.update(st['element_counts'])
    lines.append(f"| {c['name']} | " + ' | '.join(str(cc.get(k, 0)) for k in ['sun', 'moon', 'star', 'order', 'chaos']) + ' |')
lines += ['', '## 스테이지 지배 속성 분포 (스테이지 수)', '', '| 콘텐츠 | ' + ' | '.join(['sun', 'moon', 'star', 'order', 'chaos']) + ' |', '|---|---|---|---|---|---|']
for c in contents:
    cc = C.Counter(st['dominant_element'] for t in c['tabs'] for st in t['stages'])
    lines.append(f"| {c['name']} | " + ' | '.join(str(cc.get(k, 0)) for k in ['sun', 'moon', 'star', 'order', 'chaos']) + ' |')
# 보스 표: 이름+속성+역할 단위로 중복 제거, 콘텐츠 모음
boss = {}
for c, t, st in stages:
    for e in st['enemies']:
        if e['boss']:
            boss.setdefault((e['name'], e['element'], e['role']), set()).add(c['name'])
lines += ['', f'## 보스 목록 (이름·속성·역할 고유 조합 {len(boss)}개)', '', '| 이름 | 속성 | 역할 | 콘텐츠 |', '|---|---|---|---|']
for (n, el, r), cs in sorted(boss.items(), key=lambda kv: (sorted(kv[1])[0], kv[0][0])):
    lines.append(f"| {n} | {el} | {r} | {', '.join(sorted(cs))} |")
lines += ['', '## 스키마 (foe_stages.json)', '',
 '- 최상위: `_source`, `_notes`(필드 의미/추정 명시), `contents[]`',
 '- contents[]: `key`(op/oph/daily/equip/cube/rush/clo/cosmo), `name`, `tabs[]`(`tab`, `section`, `stages[]`)',
 '- stage: `name, level, recommended_power, wave_count, enemy_total, dominant_element, element_counts, role_counts, aoe_ratio, defender_ratio, has_boss, enemies[]`, 선택: `fx, fixed_player, turn_limit, season_bonus_latest, star_challenge_ref, star_pick, summons[]`',
 '- enemy: `name, title, element, role, role_kr, attackType, boss, elite, level, stats{hp,atk,def,spd}, aoe, passives[], adjust[], immune[], count_by_wave[], count`', '',
 '## 한계', '',
 '- 코스모 게이트·성간 회랑 일부는 level 이 없을 수 있음. 별의 도전 EX 보정, 시즌 보너스 전체 이력, 스킬 상세(효과 문구·쿨타임)는 JSON에 넣지 않음(raw foe.js 의 s 테이블 참고).',
 '- aoe_ratio 는 광역 스킬 보유 여부만 본 추정치. 동률 시 먼저 나온 속성이 선택됨.',
 '- 소환되는 적(summons)은 분포·비율 계산에서 제외.',
 '- 일부 콘텐츠(성간 회랑 등)는 스테이지 수가 많아 JSON 크기가 큼.']
open(os.path.join(ROOT, 'docs', 'foe_summary.md'), 'w', encoding='utf8').write('\n'.join(lines) + '\n')
print(len(contents), len(stages), tot_e, len(boss))
