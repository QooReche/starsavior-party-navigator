"""시간·횟수 필드 전수 대조(11/21, docs/timing_audit_1121.md)에서 고친 두 규칙의 표준 육성 영향. 계정 입력 없음, 순차 실행.

python -X utf8 -I tools/measure_timing_1121.py before|after [--runs N]
before = revive_se_reset·skill_cool_change legacy, after = 기본(client).
결과는 local/timing-1121/<mode>.json (gitignore 대상 local/).
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.api import simulate
from battlesim.mc import Battle

KEYS = ('revive_se_reset', 'skill_cool_change')
OP = ['frey', 'waltz-asherah', 'professor-m', 'gwen']
SAMPLES = [
    # 부활(엘리사 궁극기) 뒤 전투당 1회(로자리아 고유 패시브)·재발동 제한이 다시 걸리는가
    ('엘리사+로자리아 태양 회랑 200', ['elisa', 'rosaria', 'frey', 'gwen'], {'stage': 'clo/태양 회랑/FLOOR 200'}),
    ('엘리사+로자리아 태양 회랑 250', ['elisa', 'rosaria', 'frey', 'gwen'], {'stage': 'clo/태양 회랑/FLOOR 250'}),
    # 루그 궁극기 «스킬 대상 궁극기 쿨 1 증가»의 최대 쿨 상한
    ('루그 태양 회랑 250', ['lugh', 'frey', 'professor-m', 'gwen'], {'stage': 'clo/태양 회랑/FLOOR 250'}),
    # 코스모 힐데(지크프리트) 〈인내〉 «자신 스킬 쿨 1 감소» — 모든 칸
    ('코스모 힐데 2단계', OP, {'stage': 'cosmo/힐데/힐데 2단계'}),
    ('코스모 힐데 3단계', OP, {'stage': 'cosmo/힐데/힐데 3단계'}),
    # 괴리의 표상 〈심상 균열〉 «적 전체 스킬 쿨 1 감소»(아군에게)·특수기 «스킬 대상 스킬 쿨 1 증가»(상한)
    ('코스모 괴리의 표상 2단계', OP, {'stage': 'cosmo/괴리의 표상/괴리의 표상 2단계'}),
    ('코스모 괴리의 표상(시즌) 3단계 Lv0', OP, {'cosmo_raid': {'boss': '괴리의 표상', 'step': 3, 'level': 0}}),
]
MODES = {
    'before': {'revive_se_reset': 'legacy', 'skill_cool_change': 'legacy'},
    'after': {},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=MODES)
    ap.add_argument('--runs', type=int, default=200)
    a = ap.parse_args()
    counts = Counter()
    original_run = Battle.run

    def run(b):
        result = original_run(b)
        counts.update({k: v for k, v in b.rule_hits.items() if k in KEYS})
        return result

    rows = []
    with patch.object(Battle, 'run', run):
        for label, team, enc in SAMPLES:
            counts.clear()
            r = simulate(team, enc, {'build': 'standard', 'n_runs': a.runs, 'seed': 20261121, 'rules_override': MODES[a.mode]})
            row = dict(label=label, team=team, encounter=enc, runs=a.runs, clear=r['outcome']['n_clear'],
                       progress=round(r['outcome']['progress'] * 100, 3), counts=dict(counts))
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    dest = ROOT / 'local' / 'timing-1121'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / (a.mode + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
