"""12 SE 교정의 공개 표준 육성 영향. before/after/compare, 계정 입력 없음.

python -X utf8 -I tools/measure_autotarget_12.py before
python -X utf8 -I tools/measure_autotarget_12.py after
python -X utf8 -I tools/measure_autotarget_12.py compare
결과는 local/autotarget/에만 저장. 골든 기대값은 쓰지 않음.

옛 legacy 모드(지운 스위치 auto_* 5개)는 11/22 코드째 삭제 — 태그 engine-legacy-final 에만 있음. compare 는 before·after 만 비교.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.api import simulate
from battlesim.mc import Battle
from battlesim.starsavior.data import get_db

# 경로 확인용 rule_hits 카운터(스위치는 지웠고 카운터 이름만 남음)
HIT_KEYS = ('auto_unable_break', 'auto_remove_filter', 'auto_se_reselect', 'auto_hp_float32', 'auto_empty_marker')
TEAMS = {
    'professor-m': ['professor-m', 'gwen', 'serpang', 'dana'],
    'harley': ['harley', 'cristelle', 'bunny-charlotte', 'wedding-carmen'],
    'tyria': ['tyria', 'amora', 'frey', 'gwen'],
    'waltz-asherah': ['waltz-asherah', 'gwen', 'dana', 'cristelle'],
    'besta-bloom': ['besta@개화(SSR)', 'gwen', 'dana', 'wedding-carmen'],
    'control': ['luna', 'fei', 'frey', 'wedding-carmen'],
    'u-lane': ['lyn', 'lydia-moon-caster', 'wedding-epindel', 'sunshine-cat-smile'],
}
ENCOUNTERS = {
    'clo-moon100': {'stage': 'clo/달 회랑/FLOOR 100'},
    'clo-sun250': {'stage': 'clo/태양 회랑/FLOOR 250'},
    'operation': {'stage': 'op/바람의 유적/SECTOR 10-28'},
    'rush': {'stage': 'rush/매니저 그레고리/매니저 그레고리 Ⅰ'},
    'cosmo': {'cosmo_raid': {'boss': 'baskerville', 'step': 1, 'level': 0}},
    'guild': {'guild': {'level': 0}},
}
FIELDS = ('outcome', 'per_unit', 'progress', 'prog_runs', 'ally_via')
DEST = ROOT / 'local/autotarget'


def measure(mode):
    rows = {}
    teams = dict(TEAMS)
    # 공개 59명 + 개화 8형태 전수, 나머지 세 칸은 공통 표준 육성.
    for key in get_db().units:
        teams['roster:' + key] = [key] + [k for k in ('gwen', 'frey', 'wedding-carmen', 'dana') if k != key][:3]
    for team, party in teams.items():
        for content, encounter in ENCOUNTERS.items():
            hits = Counter()
            original = Battle.run
            def run(b):
                result = original(b)
                hits.update({k: v for k, v in b.rule_hits.items() if k in HIT_KEYS or k.startswith('auto_hp_float32')})
                return result
            options = dict(seed=20261119, n_runs=6, build='standard')
            with patch.object(Battle, 'run', run):
                result = simulate(party, encounter, options)
            key = team + '/' + content
            rows[key] = {k: result.get(k) for k in FIELDS}
            rows[key]['hits'] = dict(hits)
            # 0진행 표본만으로 무영향이라고 결론내리지 않음.
            assert max(result['prog_runs']) > 0, (key, result['prog_runs'])
            print(key, result['prog_runs'], dict(hits), flush=True)
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / (mode + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf8')


def compare():
    data = {m: json.loads((DEST / (m + '.json')).read_text(encoding='utf8'))
            for m in ('before', 'after')}
    changed = []
    contents, teams, units = Counter(), Counter(), Counter()
    progress_changes = []
    for key, old in data['before'].items():
        new = data['after'][key]
        fields = [f for f in FIELDS if old[f] != new[f]]
        if fields:
            changed.append(dict(case=key, fields=fields, hits=new['hits']))
            team, content = key.split('/')
            teams[team] += 1
            contents[content] += 1
            units.update(n for n, v in old['per_unit'].items() if v != new['per_unit'].get(n))
        if old['prog_runs'] != new['prog_runs']:
            progress_changes.append(dict(case=key, old=old['prog_runs'], new=new['prog_runs']))
    summary = dict(cases=len(data['before']), runs_per_mode=len(data['before'])*6,
                   changed=len(changed), by_content=dict(contents), by_team=dict(teams),
                   per_unit_changed=dict(units), changes=changed, progress_changes=progress_changes)
    (DEST / 'comparison.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('before', 'after', 'compare'))
    mode = parser.parse_args().mode
    compare() if mode == 'compare' else measure(mode)
