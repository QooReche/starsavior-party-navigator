"""D 영역 변경의 공개 standard 입력(현재 규칙). 단일 프로세스, 계정 입력 없음.

python -X utf8 -I tools/measure_allowlist_rules_1121.py LABEL    # local/allow-d/LABEL.json
옛 --legacy·--legacy-rule(지운 스위치 wave_foe_battle_start·revive_after_spawn·summon·caster_death)은 11/22 코드째 삭제 — 태그 engine-legacy-final 에만 있음.
"""
import json
from pathlib import Path
import sys
from unittest.mock import patch
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.api import simulate
from battlesim.mc import Battle

TEAM = ['gwen', 'amora', 'frey', 'claire']
CASES = [
    ('wave', TEAM, {'stage': 'clo/태양 회랑/FLOOR 250'}),
    ('revive', ['lugh', 'epindel', 'amora', 'claire'], {'stage': 'clo/태양 회랑/FLOOR 250'}),
    ('caster-death', ['white-pearl-luna', 'amora', 'frey', 'claire'], {'stage': 'clo/태양 회랑/FLOOR 250'}),
    ('summon', TEAM, {'stage': 'equip/잊혀진 맹세/잊혀진 맹세 X'}),
    ('summon-shadow', TEAM, {'stage': 'cosmo/올베로스/올베로스 1단계'}),
    ('buff-count', TEAM, {'stage': 'equip/혹한의 습격/혹한의 습격 XⅦ'}),
    ('cosmo', TEAM, {'cosmo_raid': {'boss': 'mogulus', 'step': 3, 'level': 0}}),
]


def main():
    rows = []
    original = Battle.run
    for name, party, encounter in CASES:
        counts = Counter()
        def run(b):
            result = original(b)
            counts.update(b.rule_hits)
            counts['summoned'] += sum(u.summoned for u in b.all_foes)
            counts['waves'] += max(0, b.wave_i)
            return result
        opts = dict(build='standard', n_runs=8, seed=20261121)
        with patch.object(Battle, 'run', run):
            r = simulate(party, encounter, opts)
        assert r['outcome']['progress'] > 0, name
        scores = r.get('cosmo_raid', {}).get('score_runs')
        row = dict(name=name, party=party, encounter=encounter, outcome=r['outcome'],
                   score=sum(scores) / len(scores) if scores else None,
                   progress_score=100 * sum(r['prog_runs']) / len(r['prog_runs']),
                   counts=dict(counts), per_unit=r['per_unit'])
        rows.append(row)
        print(name, row['outcome']['progress'], row['outcome']['clear_p'], row['score'], flush=True)
    dest = ROOT / 'local' / 'allow-d'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / (sys.argv[1] + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
