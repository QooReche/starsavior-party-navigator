"""Public standard builds, paired seeds; no accounts, workers or browsers."""
from collections import Counter
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import api
from battlesim.mc import Battle
from battlesim.rules import MC_OPTS
from battlesim.starsavior.data import get_db

OLD = dict(evade_model='rate_minus_acc', guard_precision='legacy', chain_timing='immediate')
CASES = [
    ('페이·회랑250', ['fei', 'amora', 'frey', 'claire'], {'stage': 'clo/태양 회랑/FLOOR 250'}),
    ('페이·모굴루스3', ['fei', 'amora', 'frey', 'claire'], {'cosmo_raid': {'boss': 'mogulus', 'step': 3, 'level': 0}}),
    ('루·부활', ['lugh', 'epindel', 'amora', 'claire'], {'stage': 'clo/태양 회랑/FLOOR 250'}),
    ('도발', ['white-pearl-luna', 'amora', 'frey', 'claire'], {'stage': 'clo/태양 회랑/FLOOR 250'}),
    ('잊혀진 맹세 X', ['gwen', 'amora', 'frey', 'claire'], {'stage': 'equip/잊혀진 맹세/잊혀진 맹세 X'}),
    ('크리스텔·회랑250', ['cristelle', 'smile', 'amora', 'claire'], {'stage': 'clo/태양 회랑/FLOOR 250'}),
    ('아세라·회랑250', ['asherah-order-striker', 'amora', 'frey', 'claire'], {'stage': 'clo/태양 회랑/FLOOR 250'}),
    # Controlled encounter: 13000 HIT is an actual journey boss table value;
    # other stats are declared synthetic inputs, not a real journey stage.
    ('명중130% 통제', ['fei', 'amora', 'frey', 'claire'], {'waves': [[dict(
        name='명중 통제 보스', hp=500000, atk=2500, spd=160, hit=13000, boss=True,
        skills=[dict(slot='기본기', dm=100, all=True)])]], 'max_turns': 30}),
]


def measure():
    rows = []
    original, cast = Battle.run, Battle.cast
    for name, party, encounter in CASES:
        for mode, overrides in [('before', OLD), ('after', {})]:
            counts = Counter()
            def run(b):
                result = original(b)
                counts.update(b.rule_hits)
                return result
            def observe(b, *args, **kw):
                ctx = cast(b, *args, **kw)
                if ctx and ctx.src.side == 1:
                    counts['enemy_evaded_targets'] += len(ctx.evaded)
                return ctx
            with patch.object(Battle, 'run', run), patch.object(Battle, 'cast', observe):
                r = api.simulate(party, encounter, dict(build='standard', n_runs=8, seed=20261121,
                                                       rules_override=overrides))
            assert r['outcome']['progress'] > 0, name
            scores = r.get('cosmo_raid', {}).get('score_runs') or [p * 100 for p in r['prog_runs']]
            row = dict(name=name, mode=mode, party=party, encounter=encounter,
                       score=sum(scores)/len(scores), clear=r['outcome']['clear_p'], counts=dict(counts))
            rows.append(row)
            print(name, mode, row['score'], row['clear'], counts['enemy_evaded_targets'], flush=True)
    return rows


def survey_heal():
    counts, fallbacks, missing = Counter(), Counter(), []
    resolve, pick, run = Battle.resolve, Battle.pick_ally, Battle.run
    def observe(b, owner, text, ctx, kind='buff'):
        before = b.rule_hits['heal_target_fallback'] + b.rule_hits['heal_target_description']
        result = resolve(b, owner, text, ctx, kind)
        after = b.rule_hits['heal_target_fallback'] + b.rule_hits['heal_target_description']
        if after > before:
            fallbacks[(owner.key, b._cur_line.raw if b._cur_line else text, kind)] += after-before
        return result
    def observe_pick(b, u, *args, **kw):
        fallbacks[(u.key, 'skill_targets → pick_ally', kw.get('sk_kind', 'buff'))] += 1
        return pick(b, u, *args, **kw)
    def observe_run(b):
        for u in b.allies:
            for ln in b.lines_of(u):
                if '(자동 지정)' in ln.raw and '아군' in ln.raw and b.line_spec(u, ln) is None:
                    missing.append((u.key, ln.slot, ln.raw))
        result = run(b); counts.update(b.rule_hits); return result
    db = get_db()
    with patch.object(Battle, 'resolve', observe), patch.object(Battle, 'pick_ally', observe_pick), patch.object(Battle, 'run', observe_run):
        for key in db.units:
            fill = [k for k in ['gwen', 'amora', 'frey', 'claire'] if k != key][:3]
            r = api.simulate([key] + fill, {'stage': 'clo/태양 회랑/FLOOR 250'},
                             dict(build='standard', n_runs=1, seed=20261121))
            assert r['outcome']['progress'] > 0, key
    return dict(forms=len(db.units), missing=missing,
                counts={k:v for k,v in counts.items() if k.startswith('heal_target')},
                fallbacks=[[*k,v] for k,v in fallbacks.items()])


if __name__ == '__main__':
    out = ROOT / 'local/allow-d2'; out.mkdir(parents=True, exist_ok=True)
    result = survey_heal() if '--heal' in sys.argv else measure()
    name = 'heal_survey.json' if '--heal' in sys.argv else 'impact.json'
    (out / name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if '--heal' in sys.argv: print(json.dumps(result, ensure_ascii=False))
