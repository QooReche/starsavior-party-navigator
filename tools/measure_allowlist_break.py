"""브레이크 잔여 규칙 영향: 공개 표준 육성, 순차 8판. 계정 입력 없음."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.api import simulate
from battlesim.mc import Battle, Eff
from battlesim.starsavior import cosmo_raid as C

PARTY = ['asherah-order-striker', 'gille', 'amora', 'wedding-carmen']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('label')
    ap.add_argument('--legacy', action='store_true')
    ap.add_argument('--break-only', action='store_true')
    args = ap.parse_args()
    rows = []
    scenarios = [
        ('sun250-cube', {'stage': 'clo/태양 회랑/FLOOR 250'}, '큐브 과부하', False, False),
        ('mogulus3-cube', {'cosmo_raid': {'boss': 'mogulus', 'step': 3, 'level': 0}}, '큐브 과부하', False, False),
        ('belgras3', {'cosmo_raid': {'boss': 'belgras', 'step': 3, 'level': 0}}, '특이점 관측', False, True),
        ('belgras3-guard-fixture', {'cosmo_raid': {'boss': 'belgras', 'step': 3, 'level': 0}}, '특이점 관측', True, True),
    ]
    original_spawn, original_break, original_fixed = Battle.spawn_wave, Battle._use_break_skill, Battle.fixed_true_damage
    for name, encounter, skill, guard_fixture, old_season in scenarios:
        counts = Counter()
        def spawn(b, *a, **kw):
            result = original_spawn(b, *a, **kw)
            if guard_fixture and len(b.foes) > 1:
                u = b.foes[-1]
                e = Eff('수호', {'피해 분담(수호)': 50}, 1, float('inf'), u, False)
                e.stacks = 1
                u.eff[e.name] = e
                b.dirty(u)
                counts['guard_fixture'] += 1
            return result
        def use(b, *a, **kw):
            before = b.break_skill_uses
            split_before = b.rule_hits['break_skill_guard']
            dead = sum(u.dead for u in b.allies)
            guards = sum(u.mods()['guard'] > 0 for u in b.alive(1))
            result = original_break(b, *a, **kw)
            counts['break_guard_splits'] += b.rule_hits['break_skill_guard'] - split_before
            if b.break_skill_uses > before:
                counts['break_uses'] += 1
                counts['break_with_dead'] += int(dead > 0)
                counts['break_with_guard'] += int(guards > 0)
            return result
        def fixed(b, source, target, damage, **kw):
            counts['fixed_hits'] += 1
            counts['fixed_with_guard'] += int(any(u is not target and u.mods()['guard'] > 0 for u in b.alive(target.side)))
            before = b.rule_hits['add_damage_guard']
            result = original_fixed(b, source, target, damage, **kw)
            counts['fixed_guard_splits'] += b.rule_hits['add_damage_guard'] - before
            return result
        opts = dict(build='standard', n_runs=8, seed=20261121, break_skill={'name': skill, 'level': 1})
        if args.legacy:
            opts['rules_override'] = dict(break_skill_residuals='existing_model', add_damage_guard='off')
        elif args.break_only:
            opts['rules_override'] = dict(add_damage_guard='off')
        old = C._DATA_FILE
        try:
            if old_season:
                C.use_data(str(ROOT / 'tests/fixtures/cosmo_raid_1022.json'))
            with patch.object(Battle, 'spawn_wave', spawn), patch.object(Battle, '_use_break_skill', use), patch.object(Battle, 'fixed_true_damage', fixed):
                r = simulate(PARTY, encounter, opts)
        finally:
            C.use_data(old)
        assert r['outcome']['progress'] > 0, name
        if guard_fixture:
            assert counts['break_with_guard'] > 0 and counts['fixed_with_guard'] > 0, name
        scores = r.get('cosmo_raid', {}).get('score_runs')
        row = dict(name=name, skill=skill, controlled_guard=guard_fixture, counts=dict(counts),
                   outcome=r['outcome'], score=sum(scores)/len(scores) if scores else None)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    dest = ROOT / 'local/allow-brk'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / (args.label+'.json')).write_text(json.dumps(dict(party=PARTY, build='standard', seed=20261121, runs=8, rows=rows), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
