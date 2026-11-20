"""Native worker with per-run scores for private independent validation only."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from battlesim.api import simulate
from battlesim.web import _enc, cosmo_summary

for line in sys.stdin:
    m = json.loads(line)
    try:
        for t in m['teams']:
            op = dict(m.get('options') or {})
            op.update(t.get('options') or {})
            op.update(n_runs=m['n_runs'], seed=m['seed'])
            top_q = op.pop('cosmo_top_q', .2)
            r = simulate(t['party'], _enc(m['stage'], op), op)
            result = dict(prog=r['outcome']['progress'], progs=r['prog_runs'],
                          clear=r['outcome']['clear_p'], n=m['n_runs'], via=r.get('ally_via') or {})
            if r.get('cosmo_raid'):
                result.update(cosmo=cosmo_summary(r['cosmo_raid'], top_q), scores=r['cosmo_raid']['score_runs'])
            print(json.dumps(dict(type='team', key=t['key'], result=result)), flush=True)
        print(json.dumps(dict(type='done', id=m['id'])), flush=True)
    except Exception as exc:
        print(json.dumps(dict(type='error', msg=repr(exc))), flush=True)
