"""Synthetic Python/Node parity + optional PRIVATE accuracy gate (never copies inputs).

python -X utf8 -I tests/myinfo_stats_test.py
python -X utf8 -I tests/myinfo_stats_test.py SyntheticTests
python -X utf8 -I tests/myinfo_stats_test.py --mutations
STARSAVIOR_STATIC selects the read-only private checkout; absent checkout -> skip.
The five same-date ground truths gate regression; older samples only print.
"""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import api
from battlesim.mc import Battle
from battlesim.starsavior import myinfo_stats as ms
from battlesim.starsavior.build import unit_power
from battlesim.starsavior.data import get_db
from tools.build_growth import build_growth, roster_ids, potential_power_levels

STATIC = Path(os.environ.get("STARSAVIOR_STATIC", r"E:\AI_mk2\starsavior-static-data"))
# 2026-10-22 same-date five-unit max error: 0% for each stat + 0.5%p.
# Frozen limits: never derive the acceptance threshold from the current run.
REGRESSION_LIMITS = {"atk": 0.005, "hp": 0.005, "def": 0.005}


def fixture():
    """Invented numbers/IDs only; not account data or a game-answer fixture."""
    groups = ["TG_SAVIOR", "TG_ARCANA", "TG_TEST_ELEMENT", "TG_TEST_ROLE"]
    template = dict(base=dict(atk=101, hp=1001, **{"def": 53}, spd=97, cr=500, cd=5000, eh=10000, er=0),
                    per_level=dict(atk=2, hp=7, **{"def": 1}), journey_mul=[11000, 9000, 12000],
                    tactics_groups=groups[2:],
                    passive={"0": {}, "1": {}, "2": dict(atkP=400, hpP=600, defP=800),
                             "3": dict(atkP=900, hpP=1200, defP=1700, spdP=300,
                                       cr=170, cd=230, eh=310, er=370)},
                    resonance={"0": {}, "2": dict(atk=17, hp=31, **{"def": 11}, atkP=300, hpP=500, defP=700, spd=2),
                               "10": dict(atk=27, hp=41, **{"def": 13}, atkP=600, hpP=800, defP=900, spd=3)},
                    favor={"0": {}, "3": dict(atk=5, hp=9, **{"def": 3})},
                    star={"0": {}, "1": dict(atkP=1000), "2": dict(atkP=2000, hpP=1000, defP=500)})
    tactics = {g: {kind: {"0": {}, "1": {stat: n}}
                   for kind, stat, n in (("ATTACK", "atk", 3), ("DEFENSE", "def", 5), ("HP", "hp", 11))}
               for g in groups}
    tactics["TG_COMMON"] = {"MAIN": {"0": {}, "1": dict(atk=7, hp=13, **{"def": 2})}}
    growth = dict(game_build="synthetic-build", units={"900001": template}, tactics=tactics,
                  star_link={"0": {}, "199": {}, "200": dict(atk=10), "201": dict(atk=30), "400": dict(atk=70)},
                  facility={"0": {}, "1": dict(atkP=100, hpP=100, defP=100)},
                  item_sets={"900011": 0, "900012": 2, "900014": 4},
                  potential_pp={"900101": {"0": 0, "1": 0, "2": 0},
                                "900102": {"0": 0, "1": 0}, "900103": {"0": 0, "1": 0}},
                  potentials={"900101": {"1": dict(atkP=500, hpP=700, defP=1100, spdP=1300),
                                         "2": dict(atkP=900, hpP=1200, defP=1700, spdP=1900)},
                              "900102": {"1": dict(atk=7, hp=13, **{"def": 3}, spd=11,
                                                   cr=170, cd=230, eh=310, er=370)},
                              "900103": {"1": {}}},
                  sets={"2": dict(parts=2, stats=dict(atkP=500)), "4": dict(parts=4, stats=dict(spd=9, cd=700))})
    unit = dict(id=900001, star=1, sigil=1, resonance=2, favor=3,
                skills=dict(basic=2, special=3, ultimate=4, passive=1),
                equip=[dict(item_id=900011, main=dict(stat="NST_ATK", value=23),
                            subs=[dict(stat="NST_NV_RATE_ATK", value=400), dict(stat="NST_HP", value=19),
                                  dict(stat="NST_TURN_SPEED", value=5)])],
                gauntlet=dict(journey=[11, 13, 17, 19, 23], potentials=[], blessings=[]))
    info = dict(game_build="synthetic-build", star_link_level=2,
                tactics=dict(facility_level=1, common_level=1,
                             groups={g: dict(level=1, attack=1, defense=1, hp=1) for g in groups}))
    return unit, info, growth


def node_cases(cases, operation="final_stats"):
    script = "const a=require('./myinfo_stats.js');const xs=JSON.parse(require('fs').readFileSync(0,'utf8'));" \
             "process.stdout.write(JSON.stringify(xs.map(x=>a[process.argv[1]](...x))));"
    p = subprocess.run(["node", "-e", script, operation], input=json.dumps(cases), capture_output=True,
                       text=True, encoding="utf-8", cwd=ROOT, check=True)
    return json.loads(p.stdout)


def within_tolerance(stat, actual, expected):
    # cr/cd/eh/er are engine basis points here; one percentage point = 100.
    limit = abs(expected) * 0.01 if stat == "hp" else 1 if stat == "spd" else 100
    return abs(actual - expected) <= limit


class SyntheticTests(unittest.TestCase):
    def test_formula(self):
        u, i, g = fixture()
        out = ms.final_stats(u, i, g)
        # x_atk=(101+2+12)*1.03+17=135.45; R2=.10+.04+.01;
        # remaining flat=5+7+4*3+23=47. Resonance flat is multiplied by R2.
        self.assertEqual(out["stats"], dict(atk=202, hp=1259, **{"def": 105}, spd=104,
                                            cr=500, cd=5000, eh=10076, er=92))
        self.assertEqual(out["power"], unit_power(out["stats"], 0, 10))
        self.assertEqual(out["missing"], [])
        # Unknown potential tuples / blessings must not be guessed or change any stat.
        u["gauntlet"].update(potentials=[[999999, 1, 2, 3]], blessings=[999999])
        changed = ms.final_stats(u, i, g)
        self.assertEqual(changed["stats"], out["stats"])
        self.assertEqual(changed["missing"], ["gauntlet.potential:999999", "gauntlet_blessings", "power_pp"])

    def test_unit_passive(self):
        u, i, g = fixture()
        cases = []
        # Absolute rows: level 3 is not 1+2+3. R2 multiplies x, not flat
        # equipment/tactics/favor. These distinct rates catch max-level reuse.
        for level, expected in ((0, (202, 1259, 105)), (1, (202, 1259, 105)),
                                (2, (208, 1329, 111)), (3, (214, 1399, 118))):
            u["skills"]["passive"] = level
            out = ms.final_stats(u, i, g)
            self.assertEqual(tuple(out["stats"][k] for k in ("atk", "hp", "def")), expected)
            self.assertFalse(any(s.startswith("unit_passive") for s in out["missing"]))
            cases.append([deepcopy(u), i, deepcopy(g)])
        self.assertEqual({k: out["stats"][k] for k in ("spd", "cr", "cd", "eh", "er")},
                         dict(spd=106, cr=670, cd=5230, eh=10386, er=462))
        u["skills"]["passive"] = 3.0
        self.assertEqual(ms.final_stats(u, i, g), out)
        cases.append([deepcopy(u), i, deepcopy(g)])
        u["skills"]["passive"] = 99
        self.assertIn("unit_passive:level", ms.final_stats(u, i, g)["missing"])
        cases.append([deepcopy(u), i, deepcopy(g)])
        del g["units"]["900001"]["passive"]
        self.assertIn("unit_passive", ms.final_stats(u, i, g)["missing"])
        cases.append([u, i, g])
        self.assertEqual(node_cases(cases), [ms.final_stats(*args) for args in cases])

    def test_sigil_and_resonance_buckets(self):
        u, i, g = fixture()
        original = ms.final_stats(u, i, g)["stats"]
        for star in (0, 7, 99):
            u["star"] = star
            self.assertEqual(ms.final_stats(u, i, g)["stats"], original)
        del u["star"]
        self.assertEqual(ms.final_stats(u, i, g)["stats"], original)
        u["sigil"] = 2
        # x=135.45, sigil R2=.20; NOT an R1 multiplier of the whole base.
        self.assertEqual(ms.final_stats(u, i, g)["stats"]["atk"], 216)
        g["units"]["900001"]["resonance_unlock"] = {"2": 3, "10": 200}
        self.assertEqual(ms.final_stats(u, i, g)["stats"]["atk"], 190)  # locked
        i["star_link_level"] = 3
        self.assertEqual(ms.final_stats(u, i, g)["stats"]["atk"], 218)
        cases = [[deepcopy(u), deepcopy(i), g, rule] for rule in ("normal", "fixed200")]
        self.assertEqual(node_cases(cases), [ms.final_stats(*args) for args in cases])

    def test_gauntlet_potentials(self):
        u, i, g = fixture()
        # All eight stats plus four rates. a selects one absolute row; b/c are
        # unrelated metadata. level=0 is unlearned, even when c is nonzero.
        u["gauntlet"].update(level=99, potentials=[[900101, 2, 1, 5], [900102, 1, 4, 3],
                                                  [900103, 1, 0, 0], [900102, 0, 5, 5]])
        out = ms.gauntlet_stats(u, g)
        self.assertEqual(out, dict(journey=dict(atk=12, hp=70, **{"def": 10}, eh=76, er=92),
                                   potential=dict(atkP=900, hpP=1200, defP=1700, spdP=1900,
                                                  atk=7, hp=13, **{"def": 3}, spd=11,
                                                  cr=170, cd=230, eh=310, er=370), power_pp=0, missing=[]))
        # Independent formula: journey truncates BEFORE x1; potential flat is
        # outside R1/R2 multiplication; its percentages join R2 additively.
        # HP: (1078*1.05+31)*(1+.01+.12)+98 = 1412.947
        # DEF: (64*1.07+11)*(1+.01+.17)+28 = 121.7864
        expected = dict(atk=221, hp=1412, **{"def": 121}, spd=133,
                        cr=670, cd=5230, eh=10386, er=462)
        self.assertEqual(ms.final_stats(u, i, g)["stats"], expected)
        u["gauntlet"]["level"] = 1
        for entry in u["gauntlet"]["potentials"]:
            entry[2:] = [0, 0]
        self.assertEqual(ms.final_stats(u, i, g)["stats"], expected)
        u["gauntlet"]["potentials"][0][:2] = [900101.0, 2.0]
        self.assertEqual(ms.final_stats(u, i, g)["stats"], expected)
        self.assertEqual(node_cases([[u, i, g]]), [ms.final_stats(u, i, g)])

    def test_gauntlet_unknowns_and_blessings(self):
        u, i, g = fixture()
        base = ms.final_stats(u, i, g)["stats"]
        cases = []
        for entries, labels in (([[900101, 0, 2, 4]], []), ([[900103, 1, 1, 1]], []),
                                ([[900101, 9, 1, 0]], ["gauntlet.potential:900101:level"]),
                                ([[999999, 1, 0, 0]], ["gauntlet.potential:999999"]),
                                ([[900102, -1, 0, 0]], ["gauntlet.potentials.entry"]),
                                ([[900102, 1.5, 0, 0]], ["gauntlet.potentials.entry"]),
                                ([[900102, True, 0, 0]], ["gauntlet.potentials.entry"]),
                                ([[900102, 1]], ["gauntlet.potentials.entry"]),
                                (None, ["gauntlet.potentials"])):
            u["gauntlet"]["potentials"] = entries
            self.assertEqual(ms.gauntlet_stats(u, g)["missing"], labels + (["power_pp"] if labels else []))
            self.assertEqual(ms.final_stats(u, i, g)["stats"], base)
            cases.append([deepcopy(u), i, g])
        # The v1 list is NOT established as extra stat blessings. Keep it visible
        # as unresolved and never apply arbitrary IDs (or add journey twice).
        u["gauntlet"].update(potentials=[], blessings=[900101, 900102])
        self.assertEqual(ms.final_stats(u, i, g)["stats"], base)
        self.assertEqual(ms.gauntlet_stats(u, g)["missing"], ["gauntlet_blessings"])
        cases.append([u, i, g])
        self.assertEqual(node_cases(cases), [ms.final_stats(*args) for args in cases])

    def test_journey_clamp_and_truncation(self):
        u, i, g = fixture()
        u["gauntlet"]["journey"] = [1501, 1502, 1503, 1504, 1505]
        self.assertEqual(ms.gauntlet_stats(u, g)["journey"],
                         dict(atk=1650, hp=8100, **{"def": 900}, eh=6000, er=6000))
        u["gauntlet"]["journey"] = [1, 1, 1, 0, 0]
        self.assertEqual(ms.gauntlet_stats(u, g)["journey"],
                         dict(atk=1, hp=5, **{"def": 0}, eh=0, er=0))

    def test_level_boundary_and_fixed(self):
        u, i, g = fixture()
        u.update(star=0, sigil=0, favor=0, resonance=0, equip=[], gauntlet=dict(journey=[0]*5))
        i["tactics"] = dict(common_level=0, facility_level=0,
                            groups={k: dict(attack=0, defense=0, hp=0) for k in i["tactics"]["groups"]})
        for level, atk in ((1, 101), (199, 497), (200, 509), (201, 531), (400, 969)):
            i["star_link_level"] = level
            with self.subTest(level=level):
                self.assertEqual(ms.final_stats(u, i, g)["stats"]["atk"], atk)
                fixed = ms.final_stats(u, i, g, "fixed200")
                self.assertEqual(fixed["stats"]["atk"], 555)  # (101+2*199)*1.06 + 27, floor
                self.assertEqual(fixed["stats"]["spd"], 100)  # forced resonance 10
        i.pop("star_link_level")
        u.pop("resonance")
        fixed = ms.final_stats(u, i, g, "fixed200")
        self.assertNotIn("star_link_level", fixed["missing"])
        self.assertNotIn("resonance", fixed["missing"])

    def test_set_counts(self):
        u, i, g = fixture()
        original = ms.final_stats(u, i, g)["stats"]
        for sid, stat, amounts in ((900012, "atk", [202, 202, 209, 209, 216, 216, 223]),
                                   (900014, "spd", [104, 104, 104, 104, 113, 113, 113])):
            for n, expected in enumerate(amounts):
                v = deepcopy(u)
                v["equip"] += [dict(item_id=sid, main=dict(stat="NST_ATK", value=0), subs=[]) for _ in range(n)]
                with self.subTest(set=sid, count=n):
                    out = ms.final_stats(v, i, g)["stats"]
                    self.assertEqual(out[stat], expected)
                    if sid == 900014:
                        self.assertEqual(out["cd"], original["cd"] + (700 if n >= 4 else 0))

    def test_missing_and_unknown(self):
        u, i, g = fixture()
        full = ms.final_stats(u, i, g)
        # An unknown item still contributes imported main/sub values; its set is unknown.
        u["equip"][0]["item_id"] = 999999
        out = ms.final_stats(u, i, g)
        self.assertEqual(out["stats"], full["stats"])
        self.assertIn("item:999999", out["missing"])
        u["equip"][0]["subs"].append(dict(stat="NST_FUTURE", value=99999))
        self.assertIn("equip.stat:NST_FUTURE", ms.final_stats(u, i, g)["missing"])
        out = ms.final_stats(dict(id=900001), {}, g)
        for label in ("star_link_level", "sigil", "favor", "resonance", "equip", "gauntlet.journey", "skills.basic", "game_build"):
            self.assertIn(label, out["missing"])
        out = ms.final_stats(dict(id=999998), i, g)
        self.assertEqual(out["stats"], dict.fromkeys(ms.KEYS, 0))
        self.assertEqual(out["power"], 0)
        self.assertIn("unit:999998", out["missing"])
        i["star_link_level"] = 401
        self.assertIn("growth:star_link:level", ms.final_stats(u, i, g)["missing"])

    def test_build_and_content(self):
        u, i, g = fixture()
        original = ms.final_stats(u, i, g)
        i["game_build"] = "different"
        changed = ms.final_stats(u, i, g)
        self.assertTrue(changed.pop("build_mismatch"))
        self.assertEqual(changed, original)
        self.assertNotIn("build_mismatch", original)
        contents = ["op", "작전", "clo", "회랑", "cosmo", "CosmoGate", "코스모 게이트", "rush", "플래시 포인트", "BossRush", "daily", "__proto__"]
        expected = ["normal"]*4 + ["fixed200"]*6 + [None]*2
        self.assertEqual([ms.rule_for_content(c) for c in contents], expected)
        self.assertEqual(node_cases([[c] for c in contents], "rule_for_content"), expected)
        self.assertIsNone(ms.final_stats(u, i, g, None))
        self.assertIsNone(ms.final_stats(u, i, g, "PvP"))

    def test_python_js_parity(self):
        cases = []
        for level in (1, 199, 200, 201, 400, 401):
            for rule in ("normal", "fixed200", None, "unknown"):
                u, i, g = fixture()
                i["star_link_level"] = level
                cases.append([u, i, g, rule])
        rng = random.Random(572)
        for _ in range(60):
            u, i, g = fixture()
            i["star_link_level"] = rng.randrange(1, 401)
            u.update(star=rng.randrange(3), sigil=rng.randrange(3), resonance=rng.randrange(11))
            u["skills"]["passive"] = rng.randrange(5)
            u["gauntlet"]["journey"] = [rng.randrange(1500) for _ in range(5)]
            u["gauntlet"]["potentials"] = [[900101, rng.randrange(3), rng.randrange(6), rng.randrange(6)],
                                           [900102, rng.randrange(2), 0, rng.randrange(6)]]
            u["gauntlet"]["blessings"] = rng.choice([[], [900201]])
            u["equip"] += [dict(item_id=rng.choice([900012, 900014, 999999]),
                                main=dict(stat=rng.choice(list(ms.NST_KEY)), value=rng.randrange(3000)), subs=[])
                           for _ in range(rng.randrange(7))]
            cases.append([u, i, g, rng.choice(["normal", "fixed200"])])
        u, i, g = fixture()
        cases.extend([[{}, {}, g], [dict(id=999999), i, g], [dict(id=900001), {}, g], [u, i, {}]])
        i["game_build"] = "mismatch"
        cases.append([u, i, g])
        js = node_cases(cases)
        for n, (args, actual) in enumerate(zip(cases, js)):
            with self.subTest(case=n):
                self.assertEqual(actual, ms.final_stats(*args))
        self.assertEqual(len(js), 89)
        pairs = [[args[0], args[2]] for args in cases]
        self.assertEqual(node_cases(pairs, "gauntlet_stats"), [ms.gauntlet_stats(*args) for args in pairs])
        # Browser UMD path, without CommonJS.
        p = subprocess.run(["node", "-e", "const vm=require('vm'),fs=require('fs'),c={};vm.createContext(c);"
                            "vm.runInContext(fs.readFileSync('ui_shared.js','utf8'),c);"
                            "vm.runInContext(fs.readFileSync('myinfo_stats.js','utf8'),c);"
                            "if(c.MyInfoStats.rule_for_content('op')!=='normal')process.exit(1);"], cwd=ROOT)
        self.assertEqual(p.returncode, 0)

    def test_power(self):
        stat = dict(atk=1000, hp=5500, **{"def": 500}, spd=100, cr=0, cd=0, eh=10000, er=0)
        self.assertEqual(unit_power(stat, 0, 0), 3816)
        self.assertEqual(node_cases([[stat, 0, 0]], "unit_power"), [3816])
        cases = [[dict(stat, cr=cr, cd=cd, spd=spd), pp, skills]
                 for cr, cd in ((0, 0), (500, 5000), (10000, 30000), (15000, 40000))
                 for spd in (1, 99, 200) for pp in (0, 500) for skills in (0, 10, 34)]
        self.assertEqual(node_cases(cases, "unit_power"), [unit_power(*args) for args in cases])

    def test_pp_cost_accumulation(self):
        rows = [dict(PotenLevelValue=level, PotenBattlePowerCheck=checked, PotenLevelUpReqPP=cost)
                for level, checked, cost in ((3, True, 275), (1, True, 125), (2, False, 999))]
        self.assertEqual(potential_power_levels(rows), {"0": 0, "1": 125, "2": 125, "3": 400})
        self.assertEqual(potential_power_levels([]), {"0": 0})

    def test_imported_power_pp_and_skills(self):
        u, i, g = fixture()
        # Exact 3600 base score, with no stat effects from the test potential.
        template = g["units"]["900001"]
        template.update(base=dict(atk=1000, hp=5500, **{"def": 500}, spd=100, cr=0, cd=0, eh=10000, er=0),
                        per_level={}, tactics_groups=[])
        i.update(star_link_level=1, tactics={})
        u.update(sigil=0, resonance=0, favor=0, equip=[])
        u["gauntlet"].update(journey=[0]*5, potentials=[[900103, 1, 5, 9]])
        g["potential_pp"]["900103"]["1"] = 400
        out = ms.final_stats(u, i, g)
        self.assertEqual(out["power"], 4343)  # floor(3600 * 1.04 * (1.06 + .10))
        self.assertNotIn("power_pp", out["missing"])
        cases = [[deepcopy(u), deepcopy(i), deepcopy(g), rule] for rule in ("normal", "fixed200")]
        # Every exported slot, including passive, contributes once.
        for skill in ("basic", "special", "ultimate", "passive"):
            changed = deepcopy(u)
            changed["skills"][skill] += 1
            # Neutralize the synthetic passive stat bonus to isolate its level.
            gg = deepcopy(g)
            gg["units"]["900001"]["passive"]["2"] = {}
            self.assertEqual(ms.final_stats(changed, i, gg)["power"], 4380)
            cases.append([changed, i, gg])
        # No separate PP from star/sigil, equipment, discount or blessing level.
        for star in (0, 3):
            changed = deepcopy(u)
            changed["star"] = star
            changed["gauntlet"]["potentials"][0][2:] = [0, 0]
            self.assertEqual(ms.final_stats(changed, i, g)["power"], 4343)
            cases.append([changed, i, deepcopy(g)])
        changed, gg = deepcopy(u), deepcopy(g)
        changed["gauntlet"]["potentials"].append([900102, 1, 0, 0])
        gg["potentials"]["900102"]["1"] = {}
        gg["potential_pp"]["900102"]["1"] = 125
        self.assertEqual(ms.final_stats(changed, i, gg)["power"], 4395)  # PP=525
        cases.append([changed, i, gg])
        for level in (0, 99):
            changed = deepcopy(u)
            changed["gauntlet"]["potentials"][0][1] = level
            result = ms.final_stats(changed, i, g)
            self.assertEqual(result["power"], 4176)
            self.assertEqual("power_pp" in result["missing"], level == 99)
            cases.append([changed, i, deepcopy(g)])
        del g["potential_pp"]  # stale growth must not silently claim complete PP
        self.assertIn("power_pp", ms.final_stats(u, i, g)["missing"])
        cases.append([u, i, g])
        self.assertEqual(node_cases(cases), [ms.final_stats(*args) for args in cases])

    def test_engine_final_none(self):
        u, i, g = fixture()
        u["skills"]["passive"] = 3  # calculator result already includes permanent rates
        final = ms.final_stats(u, i, g)["stats"]
        # Real permanent HP passive and actual standard potential lines as controls.
        db = get_db()
        spec = dict(key="white-pearl-luna", build="none", stats_override=final, stats_final=True)
        plain = api._norm_party([dict(key=spec["key"], build="none")], db, "fixed", "standard")[0][0]
        standard = api._norm_party([spec["key"]], db, "fixed", "standard")[0][0]
        self.assertGreater(plain.passive["hpp"], 0)
        self.assertIsNotNone(standard.build)
        self.assertGreater(len(standard.lines), len(plain.lines))
        with patch("battlesim.starsavior.build.make_build", side_effect=AssertionError("standard build applied")):
            defs, _ = api._norm_party([spec], db, "fixed", "standard")
            api.simulate([spec], dict(waves=[[dict(name="dummy", hp=100000, atk=1)]], max_turns=1),
                         dict(build="standard", n_runs=1, seed=1))
        d = defs[0]
        self.assertIsNone(d.build)
        self.assertEqual([x.raw for x in d.lines], [x.raw for x in plain.lines])
        self.assertEqual({k: d.stats[k] for k in ms.KEYS}, final)
        for keys in api.FINAL_PASSIVE_KEYS.values():
            for key in keys:
                self.assertEqual(d.passive[key], 0)
        battle = Battle(defs, [[api._CustomFoe(dict(hp=100000, atk=1), 0)]], random.Random(1))
        self.assertEqual(battle.allies[0].maxhp, final["hp"])
        self.assertEqual(battle.allies[0].spd(), final["spd"])
        raw_spec = dict(spec, stats_final=False)
        raw_defs, _ = api._norm_party([raw_spec], db, "fixed", "standard")
        raw_battle = Battle(raw_defs, [[api._CustomFoe(dict(hp=100000, atk=1), 0)]], random.Random(1))
        self.assertGreater(raw_battle.allies[0].maxhp, final["hp"])
        self.assertEqual(api.party_power(defs), unit_power(final))

        # End-to-end controls for all three multiplicative stats. No turns or
        # conditional buffs: stats_final must suppress the real DB passive.
        for key, stat, getter in (("1040", "atk", Battle.atk_stat),
                                  ("1045", "hp", Battle.hp_stat),
                                  ("haydee", "def", Battle.def_stat)):
            for is_final in (True, False):
                defs, _ = api._norm_party([dict(key=key, build="none", stats_override=final,
                                               stats_final=is_final)], db, "fixed", "standard")
                b = Battle(defs, [[api._CustomFoe(dict(hp=100000, atk=1), 0)]], random.Random(1))
                actual = getter(b, b.allies[0])
                if is_final:
                    self.assertEqual(actual, final[stat])
                else:
                    self.assertGreater(actual, final[stat])

    def test_sim_imported_power(self):
        info = json.loads((ROOT / "tests/fixtures/myinfo_synthetic.json").read_text(encoding="utf-8"))
        growth = json.loads((ROOT / "data/growth.json").read_text(encoding="utf-8"))
        units = []
        for u in info["units"]:
            if u["id"] in (1001, 1002, 1003, 1005):
                final = ms.final_stats(u, info, growth, "normal")
                units.append(dict(key=str(u["id"]), build="none", stats_override=final["stats"],
                                  stats_final=True, power=final["power"]))
        self.assertEqual(len(units), 4)
        self.assertEqual(sum(u["power"] for u in units), 39000)
        db = get_db()
        # Only one short battle; exercise the public API's operation penalty path.
        encounter = api._norm_encounter(dict(waves=[[dict(name="dummy", hp=100000, atk=1)]], max_turns=1))
        waves, limit, fx, unknown, _ = encounter
        with patch.object(api, "_norm_encounter", return_value=(waves, limit, fx, unknown,
                          dict(content="op", recommended_power=50000))):
            result = api.simulate(units, dict(max_turns=1),
                                  dict(n_runs=1, build="standard", rules_override=dict(power_penalty="model")))
        self.assertEqual(result["party"]["power"], 39000)
        self.assertEqual(result["party"]["penalty"], [0.78, 1.22])
        # Omitted fields retain the old skill-level-sum=34 calculation, including mixed parties.
        legacy = [{k: v for k, v in u.items() if k != "power"} for u in units]
        defs, _ = api._norm_party(legacy, db, "fixed", "standard")
        self.assertEqual(api.party_power(defs), 45501)
        mixed, _ = api._norm_party([units[0], *legacy[1:]], db, "fixed", "standard")
        self.assertEqual(api.party_power(mixed), units[0]["power"] + api.party_power(defs[1:]))

    def test_accuracy_gate(self):
        self.assertEqual(REGRESSION_LIMITS, dict(atk=0.005, hp=0.005, **{"def": 0.005}))
        for key, expected, tolerance in (("hp", 10000, 100), ("spd", 150, 1), ("cr", 6500, 100),
                                         ("cd", 14000, 100), ("eh", 12000, 100), ("er", 2000, 100)):
            for sign in (-1, 1):
                self.assertTrue(within_tolerance(key, expected + sign * tolerance, expected))
                self.assertFalse(within_tolerance(key, expected + sign * (tolerance + 1), expected))

    def test_published_schema(self):
        g = json.loads((ROOT / "data/growth.json").read_text(encoding="utf-8"))
        self.assertEqual(set(g), {"_note", "game_build", "units", "star_link", "tactics", "facility", "item_sets", "sets", "potentials", "potential_pp"})
        self.assertEqual(set(map(int, g["units"])), roster_ids())
        allowed = set(ms.KEYS) | set(ms.RATE_KEYS)

        def check_stats(row):
            self.assertLessEqual(set(row), allowed)
            self.assertTrue(all(type(v) in (int, float) and math.isfinite(v) for v in row.values()))

        def check_table(table):
            self.assertTrue(all(k.isdecimal() for k in table))
            for row in table.values():
                check_stats(row)

        for u in g["units"].values():
            self.assertEqual(set(u), {"base", "per_level", "journey_mul", "tactics_groups", "resonance", "resonance_unlock", "favor", "star", "passive"})
            self.assertEqual(set(u["base"]), set(ms.KEYS))
            check_stats(u["base"])
            check_stats(u["per_level"])
            self.assertEqual(len(u["journey_mul"]), 3)
            self.assertTrue(all(type(v) in (int, float) for v in u["journey_mul"]))
            self.assertEqual(len(u["tactics_groups"]), 2)
            self.assertTrue(all(k.isdecimal() and type(v) is int for k, v in u["resonance_unlock"].items()))
            for field in ("resonance", "favor", "star", "passive"):
                check_table(u[field])
        check_table(g["star_link"])
        check_table(g["facility"])
        self.assertTrue(all(k.isdecimal() for k in g["potentials"]))
        for levels in g["potentials"].values():
            check_table(levels)
        self.assertEqual(set(g["potential_pp"]), set(g["potentials"]))
        for pid, levels in g["potential_pp"].items():
            self.assertEqual(set(levels), set(g["potentials"][pid]) | {"0"})
            self.assertTrue(all(k.isdecimal() and type(v) is int and v >= 0 for k, v in levels.items()))
            values = [levels[k] for k in sorted(levels, key=int)]
            self.assertEqual(values, sorted(values))
        for kinds in g["tactics"].values():
            for table in kinds.values():
                check_table(table)
        for effect in g["sets"].values():
            self.assertEqual(set(effect), {"parts", "stats"})
            self.assertIn(effect["parts"], (2, 4))
            check_stats(effect["stats"])
        self.assertTrue(all(k.isdecimal() and isinstance(v, int) for k, v in g["item_sets"].items()))


@unittest.skipUnless(STATIC.is_dir(), "private STARSAVIOR_STATIC checkout unavailable")
class PrivateTests(unittest.TestCase):
    def test_power_reference(self):
        info = json.loads((STATIC / "samples/myinfo_2026-10-22.json").read_text(encoding="utf-8"))
        growth = build_growth(STATIC)
        units = {u["id"]: u for u in info["units"]}
        cases = []
        # Older screen observations are reports, not same-date exact targets.
        for uid, screen, pp in ((1045, 96286, 400), (1044, 100077, 0), (1054, 112926, 0),
                                (1055, 94920, 400), (1039, 103240, 400)):
            u = units[uid]
            out = ms.final_stats(u, info, growth)
            self.assertEqual(ms.gauntlet_stats(u, growth)["power_pp"], pp)
            self.assertNotIn("power_pp", out["missing"])
            before = unit_power(out["stats"], 0, sum(u["skills"].values()))
            after = out["power"]
            print(f"POWER reference {uid}: screen={screen}, PP={pp}, "
                  f"before={before} ({(before/screen-1)*100:+.3f}%), "
                  f"after={after} ({(after/screen-1)*100:+.3f}%)", flush=True)
            cases.append([u, info, growth])
        self.assertEqual(node_cases(cases), [ms.final_stats(*args) for args in cases])

    def test_rebuild(self):
        generated = build_growth(STATIC)
        published = json.loads((ROOT / "data/growth.json").read_text(encoding="utf-8"))
        self.assertEqual(generated, published)

    def test_gauntlet_tab(self):
        info = json.loads((STATIC / "samples/myinfo_2026-10-22.json").read_text(encoding="utf-8"))
        truth = json.loads((STATIC / "analysis/groundtruth.json").read_text(encoding="utf-8"))["units"]
        growth = build_growth(STATIC)
        units = {str(u["id"]): u for u in info["units"]}
        cases = [[units[uid], growth] for uid in truth]
        outputs = [ms.gauntlet_stats(*args) for args in cases]
        self.assertEqual(node_cases(cases, "gauntlet_stats"), outputs)
        for (uid, answer), result in zip(truth.items(), outputs):
            if "gauntlet_tab" not in answer:
                continue  # Only two private records contain tab observations.
            actual = {}
            for key in ms.KEYS:
                value = result["journey"].get(key, 0) + result["potential"].get(key, 0)
                actual[key.upper()] = ([value, result["potential"].get(key + "P", 0) / 100]
                                       if key in ("atk", "hp", "def") else
                                       value / (100 if key in ("cr", "cd", "eh", "er") else 1))
            with self.subTest(unit=uid):
                self.assertEqual(actual, answer["gauntlet_tab"])
            print("PRIVATE gauntlet tab", answer["name"], actual, flush=True)

    def test_groundtruth(self):
        info = json.loads((STATIC / "samples/myinfo_2026-10-22.json").read_text(encoding="utf-8"))
        truth = json.loads((STATIC / "analysis/groundtruth.json").read_text(encoding="utf-8"))["units"]
        growth = build_growth(STATIC)
        units = {str(u["id"]): u for u in info["units"]}
        cases = [[units[uid], info, growth] for uid in truth]
        outputs = [ms.final_stats(*args) for args in cases]
        self.assertEqual(node_cases(cases), outputs)
        print("\nPRIVATE accuracy: actual / expected (delta; atk/hp/def %, other stats points)", flush=True)
        for (uid, answer), result in zip(truth.items(), outputs):
            cells = []
            for key in ms.KEYS:
                want = answer["final"][key.upper()]
                actual = result["stats"][key] / (100 if key in ("cr", "cd", "eh", "er") else 1)
                delta = (actual - want) / want * 100 if key in ("atk", "hp", "def") else actual - want
                cells.append(f"{key}={actual:g}/{want:g} ({delta:+.2f})")
            print(answer["name"] + " | " + " | ".join(cells), flush=True)
        self.assertEqual(len(truth), 5)
        open_targets = []
        for (uid, answer), result in zip(truth.items(), outputs):
            self.assertFalse(any(s.startswith("unit_passive") for s in result["missing"]))
            for key in ms.KEYS:
                expected = round(answer["final"][key.upper()] * (100 if key in ("cr", "cd", "eh", "er") else 1))
                actual = result["stats"][key]
                if key in ("hp", "spd", "cr", "cd", "eh", "er") and not within_tolerance(key, actual, expected):
                    open_targets.append(f"{answer['name']}.{key} {actual} vs {expected}")
                with self.subTest(unit=uid, stat=key):
                    if key in REGRESSION_LIMITS:
                        self.assertLessEqual(abs(actual - expected), abs(expected) * REGRESSION_LIMITS[key],
                                             f"{key}: {actual} vs {expected}; missing={result['missing']}")
                    else:
                        self.assertTrue(within_tolerance(key, actual, expected),
                                        f"{key}: {actual} vs {expected}; missing={result['missing']}")
        print("PRIVATE target ±1% not yet met: " + ("; ".join(open_targets) or "none"), flush=True)
        # Public 10/21 screens vs 10/22 import: report only, never an accuracy gate.
        for uid, name, observed in (("1044", "클레어", (16002, 65538, 4915)),
                                     ("1045", "화이트펄 루나", (12314, 66887, 5206)),
                                     ("1054", "왈츠 아세라", (9909, 95464, 5522))):
            if uid not in units:
                print("REFERENCE unavailable:", name)
                continue
            actual = ms.final_stats(units[uid], info, growth)["stats"]
            cells = [f"{k}={actual[k]}/{v} ({(actual[k] / v - 1) * 100:+.2f}%)"
                     for k, v in zip(("atk", "hp", "def"), observed)]
            print("REFERENCE 10/21 (not gated): " + name + " | " + " | ".join(cells), flush=True)


def mutation_checks():
    """Inject wrong values in memory, prove rejection, restore; no files change.

    Each mutation must fail by assertion, and its restored test must pass.
    """
    original_final, original_node = ms.final_stats, node_cases
    original_read, original_build = Path.read_text, build_growth
    original_gauntlet = ms.gauntlet_stats

    def wrong_gauntlet(*args):
        result = original_gauntlet(*args)
        result["journey"]["atk"] = result["journey"].get("atk", 0) + 1
        return result

    def wrong_pp(*args):
        result = original_gauntlet(*args)
        result["power_pp"] += 200
        return result

    def wrong_stat(*args):
        result = original_final(*args)
        if result is not None:
            result["stats"]["atk"] += 1
        return result

    def wrong_missing(*args):
        result = original_final(*args)
        result["missing"] = []
        return result

    def wrong_build(*args):
        result = original_final(*args)
        result["build_mismatch"] = False
        return result

    def wrong_power(*args, **kwargs):
        result = original_node(*args, **kwargs)
        result[0] += 1
        return result

    def wrong_schema(path, *args, **kwargs):
        raw = original_read(path, *args, **kwargs)
        if path == ROOT / "data/growth.json":
            obj = json.loads(raw)
            obj["forbidden_field"] = 123
            return json.dumps(obj)
        return raw

    def wrong_growth(*args):
        obj = original_build(*args)
        obj["game_build"] = "intentionally-wrong"
        return obj

    module = sys.modules[__name__]
    mutations = {
        "test_formula": (ms, "final_stats", wrong_stat),
        "test_unit_passive": (ms, "final_stats", wrong_stat),
        "test_sigil_and_resonance_buckets": (ms, "final_stats", wrong_stat),
        "test_gauntlet_potentials": (ms, "gauntlet_stats", wrong_gauntlet),
        "test_gauntlet_unknowns_and_blessings": (ms, "final_stats", wrong_stat),
        "test_journey_clamp_and_truncation": (ms, "gauntlet_stats", wrong_gauntlet),
        "test_level_boundary_and_fixed": (ms, "final_stats", wrong_stat),
        "test_set_counts": (ms, "final_stats", wrong_stat),
        "test_missing_and_unknown": (ms, "final_stats", wrong_missing),
        "test_build_and_content": (ms, "final_stats", wrong_build),
        "test_python_js_parity": (ms, "final_stats", wrong_stat),
        "test_power": (module, "node_cases", wrong_power),
        "test_pp_cost_accumulation": (module, "potential_power_levels", lambda rows: {"0": 0}),
        "test_imported_power_pp_and_skills": (ms, "gauntlet_stats", wrong_pp),
        "test_power_reference": (ms, "gauntlet_stats", wrong_pp),
        "test_engine_final_none": (api, "FINAL_PASSIVE_KEYS", {}),
        "test_accuracy_gate": (module, "within_tolerance", lambda *a: True),
        "test_published_schema": (Path, "read_text", wrong_schema),
        "test_rebuild": (module, "build_growth", wrong_growth),
        "test_gauntlet_tab": (ms, "gauntlet_stats", wrong_gauntlet),
        "test_groundtruth": (ms, "final_stats", wrong_stat),
    }
    detected = 0
    for name, (target, attribute, replacement) in mutations.items():
        cls = PrivateTests if name in ("test_rebuild", "test_gauntlet_tab", "test_groundtruth", "test_power_reference") else SyntheticTests
        if cls is PrivateTests and not STATIC.is_dir():
            print("SKIP mutation", name)
            continue
        with patch.object(target, attribute, replacement):
            result = unittest.TestResult()
            cls(name).run(result)
        if not result.failures or result.errors:
            raise AssertionError(f"Mutation not rejected by an assertion: {name}: {result.errors}")
        detected += 1
        restored = unittest.TestResult()
        cls(name).run(restored)
        if not restored.wasSuccessful():
            raise AssertionError(f"Restoration failed: {name}: {restored.failures}")
        print("DETECTED", name, "(restored PASS)")
    print(f"{detected} mutations detected; no files changed")


if __name__ == "__main__":
    if sys.argv[1:] == ["--mutations"]:
        mutation_checks()
    else:
        unittest.main(verbosity=2)
