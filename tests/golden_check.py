# -*- coding: utf-8 -*-
"""시뮬레이터 회귀 기준(골든) 저장·대조.

  python -X utf8 -I tests/golden_check.py --write   # 현재 결과를 tests/golden/ 에 저장
  python -X utf8 -I tests/golden_check.py           # 저장된 골든과 대조 (다르면 종료코드 1)

담는 것: 구원자별 지표(build_index 의 수치 항목), 기준 적 상대 파티 150팀 10턴 피해, 대표 파티 10팀의 대표 스테이지 5개 처치 턴,
그리고 입력 자료 해시(rawdata·data). 입력 해시가 다르면 결과 차이는 「코드 회귀」가 아니라 「자료 변경」이므로 따로 알린다.
구조 분리(P1)는 정확 일치, 규칙 교정(P2~)은 docs/battlesim_design.md 5절대로 순위 안정성 + 변경 사유로 관리한다."""
import argparse
import hashlib
import json
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sim_damage as sd  # noqa: E402

GOLDEN = os.path.join(ROOT, 'tests', 'golden', 'sim_golden.json')
INPUTS = ['rawdata/databook_main.json', 'rawdata/foe.js', 'data/synergy_tags.json', 'data/foe_stages.json']
INDEX_FIELDS = ['single_dpt', 'aoe_dpt', 'hits_per_turn', 'actions_per_turn', 'extra_hit_dmg_share', 'ally_dmg_gain_pct',
                'combined_dpt', 'norm_global', 'norm_role', 'stats']
NAMED = {
    '4딜덱': ['프로페서M', '그웬', '페이', '아모라'],
}
SEED = 20261020
N_TEAMS = 150
N_STAGE_TEAMS = 9


def sha(path):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, path), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:16]


def capture():
    db = sd.get_db()
    keys = sorted(db.units)
    idx = sd.build_index(10, None, 0, db)
    index = {k: {f: v[f] for f in INDEX_FIELDS} for k, v in idx.items() if k != '_meta'}
    rng = random.Random(SEED)
    teams = [sorted(rng.sample(keys, 4)) for _ in range(N_TEAMS)]
    party = []
    for t in teams:
        r = sd.simulate_party(t, None, 10, None, 0, db=db)
        party.append(dict(team=t, total=round(r['total_damage'], 3), hits=round(r['hits'], 4),
                          src={k: round(v, 3) for k, v in r['dmg_src'].items()}))
    named = {n: [sd._find_key(db, x) for x in v] for n, v in NAMED.items()}
    stage_teams = list(named.items()) + [('rand%d' % i, teams[i]) for i in range(N_STAGE_TEAMS)]
    stages = []
    for name, t in stage_teams:
        rows = sd.stage_report(t, 10, None, 0, db=db)
        stages.append(dict(name=name, team=t, rows=[dict(stage=r['stage'], dmg=r['dmg'],
                                                         ttk=None if r['ttk'] is None else round(r['ttk'], 4)) for r in rows]))
    return dict(inputs={p: sha(p) for p in INPUTS}, index=index, party=party, stages=stages)


def diff(old, new, path='', out=None, limit=40):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new), key=str):
            if k not in old or k not in new:
                out.append('%s/%s: %s' % (path, k, '추가됨' if k not in old else '없어짐'))
            else:
                diff(old[k], new[k], '%s/%s' % (path, k), out, limit)
    elif isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        for i, (a, b) in enumerate(zip(old, new)):
            diff(a, b, '%s[%d]' % (path, i), out, limit)
    elif old != new:
        out.append('%s: %r -> %r' % (path, old, new))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    cur = capture()
    if a.write:
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        tmp = GOLDEN + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(cur, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, GOLDEN)
        print('골든 저장:', GOLDEN, '구원자', len(cur['index']), '/ 파티', len(cur['party']), '/ 스테이지 팀', len(cur['stages']))
        return 0
    with open(GOLDEN, encoding='utf-8') as f:
        old = json.load(f)
    cur = json.loads(json.dumps(cur, ensure_ascii=False, sort_keys=True))
    if old['inputs'] != cur['inputs']:
        print('[주의] 입력 자료가 골든 저장 때와 다름 -> 차이는 자료 변경 때문일 수 있음')
        for line in diff(old['inputs'], cur['inputs'], 'inputs'):
            print('  ', line)
    d = diff({k: old[k] for k in ('index', 'party', 'stages')}, {k: cur[k] for k in ('index', 'party', 'stages')})
    if not d:
        print('골든 일치: 구원자', len(cur['index']), '/ 파티', len(cur['party']), '/ 스테이지 팀', len(cur['stages']))
        return 0
    print('골든 불일치 (앞 %d건):' % len(d))
    for line in d:
        print('  ', line)
    return 1


if __name__ == '__main__':
    sys.exit(main())
