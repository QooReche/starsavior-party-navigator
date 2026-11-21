"""Check whether follow-up rules change the existing quick calibration labels.

Serial, same 400/content + opboss, seed, 40-run jobs as the last calibration.
Only jobs whose executed shields can differ need a second run. Writes local/.
Frozen 26752678 data scope: RECEIVE providers / self-based enemy shields are
absent, and client_auto reactions belong to Shien/BFB (no guild calibration).
Re-audit these exclusions before reusing this detector with newer data.
"""
import json
import math
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.mc import Battle, RX_SHIELD
from tools import gen_quick_calib as gen


def main():
    changed = []
    touched = 0
    candidate = False
    jobs = 0
    original_special, original_job = Battle.run_special, gen.job

    def special(b, owner, ln, ctx, rest):
        nonlocal candidate
        m = RX_SHIELD.match(rest)
        if m and '보호막 = 대상 ' not in rest:
            stat = {'생명력': owner.maxhp, '공격력': b.atk_stat(owner), '방어력': b.def_stat(owner)}[m.group(5)]
            scaled = stat * float(m.group(6)) / 100.0
            give = owner.mods()['barrier_give']
            old = math.floor(scaled * max(0.0, 1 + give))
            base = int(scaled)
            # Resolve would consume RNG; inspect every ally as a conservative
            # superset of recipients instead. False positives only cost a rerun.
            for x in b.alive(owner.side):
                new = max(0, base + int(base * (give + x.mods()['barrier_receive'])))
                if new != old or new == 0:
                    candidate = True
        return original_special(b, owner, ln, ctx, rest)

    def job(args):
        nonlocal candidate, touched, jobs
        candidate = False
        new = original_job(args)
        assert new[4] is not None, new
        jobs += 1
        if candidate:
            touched += 1
            legacy_opts = dict(gen.SIMOPT, rules_override=dict(gen.SIMOPT['rules_override'],
                               barrier_formula='legacy', reaction_single_target_rng='legacy'))
            with patch.object(gen, 'SIMOPT', legacy_opts):
                old = original_job(args)
            assert old[4] is not None, old
            if old[4] != new[4]:
                changed.append(dict(job=args, before=old[4], after=new[4],
                                    label_changed=(old[4] >= .5) != (new[4] >= .5)))
        return new

    def save(*args):
        result = dict(jobs=jobs, touched=touched, changed=changed,
                      labels_changed=sum(r['label_changed'] for r in changed))
        dest = ROOT / 'local' / 'allow-fu' / 'quick.json'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False), flush=True)

    assert not any(row[0] == 'guild' for row in gen.teams()), 'reaction cases require a separate check'
    with patch.object(Battle, 'run_special', special), patch.object(gen, 'job', job), patch.object(gen, 'save_samples', save):
        sys.argv = [__file__, '--workers', '1', '--per-content', '400', '--opboss', '--runs', '40']
        gen.main()


if __name__ == '__main__':
    main()
