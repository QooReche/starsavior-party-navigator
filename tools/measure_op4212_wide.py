"""op4212 전수 대조(11/21) 고친 두 규칙의 표준 육성 영향. 계정 입력 없음, 순차 실행.

python -X utf8 -I tools/measure_op4212_wide.py before|after
before = unique_id_stack=off·random_basic_not_self=legacy, after = 기본(client).
결과는 local/op4212-wide/<mode>.json (gitignore 대상 local/).
"""
from collections import Counter
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.api import simulate
from battlesim.mc import Battle

OP = ['frey', 'waltz-asherah', 'professor-m', 'gwen']
SHIELDS = ['haydee', 'frey', 'amora', 'wedding-carmen']
SAMPLES = [
    ('작전 42-12(영혼 구속)', OP, {'stage': 'op/NOA 중앙지구/SECTOR 42-12'}),
    ('달 회랑 245(영혼 구속)', SHIELDS, {'stage': 'clo/달 회랑/FLOOR 245'}),
    ('달 회랑 240(찬탈의 흔적)', SHIELDS, {'stage': 'clo/달 회랑/FLOOR 240'}),
    ('달 회랑 410(제행무상)', SHIELDS, {'stage': 'clo/달 회랑/FLOOR 410'}),
    ('길드 그레고리 6(보안 강화)', SHIELDS, {'stage': 'guild/매니저 그레고리/길드 방어전 6단계'}),
    ('해피 68호 Ⅳ(인형실)', SHIELDS, {'stage': 'rush/레디메이드 해피 68호/레디메이드 해피 68호 Ⅳ'}),
]
MODES = {
    'before': {'unique_id_stack': 'off', 'random_basic_not_self': 'legacy'},
    'after': {},
}


def main():
    mode = sys.argv[1]
    overrides = MODES[mode]
    counts = Counter()
    original_run = Battle.run

    def run(b):
        result = original_run(b)
        counts.update({k: v for k, v in b.rule_hits.items() if k in ('unique_id_stack', 'random_basic_not_self')})
        return result

    rows = []
    with patch.object(Battle, 'run', run):
        for label, team, enc in SAMPLES:
            counts.clear()
            r = simulate(team, enc, {'build': 'standard', 'n_runs': 8, 'seed': 20261121, 'rules_override': overrides})
            row = dict(label=label, team=team, encounter=enc, clear=r['outcome']['n_clear'],
                       progress=round(r['outcome']['progress'] * 100, 3), counts=dict(counts))
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    dest = ROOT / 'local' / 'op4212-wide'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / (mode + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
