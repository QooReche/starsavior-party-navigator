"""Standard-build follow-up samples, serial execution and no account input.

python -X utf8 tools/measure_allowlist_followup.py before|reaction|after
before·reaction(옛 값 reaction_single_target_rng·barrier_formula — 엔진 다이어트 4단계 1묶음에서 지운 스위치)은
태그 engine-legacy-final 의 worktree 에서만 동작. 이 브랜치에서는 바로 종료함. after 는 그대로 동작.
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
from battlesim.rules import MC_OPTS

TEAM = ['asherah-order-striker', 'gille', 'amora', 'wedding-carmen']
SHIELDS = ['haydee', 'frey', 'amora', 'wedding-carmen']
SAMPLES = [
    ('BFB 6단계', TEAM, {'stage': 'guild/BFB/길드 방어전 6단계'}),
    ('티엔 6단계', TEAM, {'stage': 'guild/티엔/길드 방어전 6단계'}),
    ('공허결집자 어려움39-10', TEAM, {'stage': 'oph/고대 지하 유적/SECTOR 39-10'}),
    ('처단자 동반 벨그라스1', SHIELDS, {'stage': 'cosmo/벨그라스/벨그라스 1단계'}),
    ('모굴루스3', SHIELDS, {'cosmo_raid': {'boss': 'mogulus', 'step': 3, 'level': 0}}),
    ('태양 회랑250', SHIELDS, {'stage': 'clo/태양 회랑/FLOOR 250'}),
]


def main():
    mode = sys.argv[1]
    overrides = {
        'before': {'reaction_single_target_rng': 'legacy', 'barrier_formula': 'legacy'},
        'reaction': {'barrier_formula': 'legacy'},
        'after': {},
    }[mode]
    gone = sorted(k for k in overrides if k not in MC_OPTS)
    if gone:
        raise SystemExit('%s 모드는 태그 engine-legacy-final 의 worktree 에서만 동작 — 지운 규칙 키: %s' % (mode, ', '.join(gone)))
    counts = Counter()
    original_run, original_local = Battle.run, Battle.run_per_target

    def run(b):
        result = original_run(b)
        counts.update(b.rule_hits)
        counts['shield_given'] += sum(u.shield_given for u in b.allies + b.all_foes)
        return result

    def local(b, owner, ln, ctx):
        if owner.d.name == '공허결집자':
            counts['cohesion_local'] += 1
        return original_local(b, owner, ln, ctx)

    rows = []
    with patch.object(Battle, 'run', run), patch.object(Battle, 'run_per_target', local):
        for label, team, enc in SAMPLES:
            counts.clear()
            r = simulate(team, enc, {'build': 'standard', 'n_runs': 8, 'seed': 20261121,
                                     'rules_override': overrides})
            if not label.startswith('공허결집자'):
                assert r['outcome']['progress'] > 0, label
            scores = r.get('cosmo_raid', {}).get('score_runs')
            row = dict(label=label, team=team, encounter=enc, outcome=r['outcome'],
                       score=sum(scores) / len(scores) if scores else None,
                       counts=dict(counts), informative=r['outcome']['progress'] > 0)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    dest = ROOT / 'local' / 'allow-fu'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / (mode + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
