"""Guide targets preserve the standard engine build, with potential counted once."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.starsavior.build import make_build, setting_spec, NST_KEY
from battlesim.starsavior.data import DB
from battlesim.starsavior.parser import UnitDef
from battlesim.starsavior.myinfo_combat import select_skills, apply_potentials


class AssumedBuildTests(unittest.TestCase):
    def test_all_targets_and_separate_sources(self):
        db = DB(str(ROOT))
        growth = json.loads((ROOT / 'data/growth.json').read_text(encoding='utf8'))
        presets = growth['assumed']['units']
        self.assertEqual({s['uid'] for s in presets.values()}, set(map(int, growth['units'])))
        for key, spec in presets.items():
            d = UnitDef(db, key, level=200, res_stage=10, star=0, build='none')
            old = make_build(db, key, db.units[key], base_stats=d.stats, passive_cr=d.passive['cr'])
            structured = setting_spec(db, key, db.units[key], base_stats=d.stats, passive_cr=d.passive['cr'])
            self.assertEqual(structured['journey_raw'], spec['journey'])
            self.assertEqual(len(spec['equip']), 6)
            gear, counts = {}, {}
            for piece in spec['equip']:
                self.assertEqual(piece['enhance'], 15)
                sid = str(growth['item_sets'][str(piece['item_id'])])
                counts[sid] = counts.get(sid, 0) + 1
                for opt in [piece['main']] + piece['subs']:
                    k = NST_KEY[opt['stat']]
                    gear[k] = gear.get(k, 0) + opt['value']
            for sid, count in counts.items():
                effect = growth['sets'][sid]
                for k, v in effect['stats'].items():
                    gear[k] = gear.get(k, 0) + v * (count // effect['parts'])
            pid, lv, _, _ = spec['potential']
            potential = growth['potentials'][str(pid)][str(lv)]
            for k in set(old['gear']) | set(gear) | set(potential):
                # gear above contains equipment ONLY, permanent potential added exactly once.
                self.assertAlmostEqual(old['gear'].get(k, 0), gear.get(k, 0) + potential.get(k, 0), places=7, msg=key+'/'+k)
            combat = dict(skills=spec['skills'], potentials=[[pid, lv]])
            selected = select_skills(db.units[key], key, combat)
            self.assertEqual(len(selected['sk']), len(db.units[key]['sk']))
            before = list(d.unmodeled)
            apply_potentials(d, db, combat)
            self.assertEqual(d.unmodeled, before, key)


if __name__ == '__main__':
    unittest.main()
