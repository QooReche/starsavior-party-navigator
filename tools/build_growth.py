"""Extract only derived stat growth; never read/copy account samples or ground truth.

python -X utf8 -I tools/build_growth.py --static <private checkout>
Output is always this checkout's data/growth.json. Rates use 1/10000 units.
"""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATIC = Path(r"E:\AI_mk2\starsavior-static-data")
STAT = dict(zip(
    ("NST_ATK", "NST_HP", "NST_DEF", "NST_TURN_SPEED", "NST_RATE_CRITICAL",
     "NST_RATE_CRITICAL_DAMAGE", "NST_RATE_EFFECT_HIT", "NST_RATE_EFFECT_EVADE",
     "NST_NV_RATE_ATK", "NST_NV_RATE_HP", "NST_NV_RATE_DEF"),
    ("atk", "hp", "def", "spd", "cr", "cd", "eh", "er", "atkP", "hpP", "defP")))
KEYS = ("atk", "hp", "def", "spd", "cr", "cd", "eh", "er")
STAT["NST_NV_RATE_TURN_SPEED"] = "spdP"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def stats(raw, key="StatType", value="StatValue", allowed=None):
    pairs = raw.items() if isinstance(raw, dict) else ((s[key], s[value]) for s in (raw or []))
    out = {}
    for k, v in pairs:
        k = STAT.get(k)
        if k and (allowed is None or k in allowed):
            out[k] = out.get(k, 0) + v
    return out


def cumulative(rows, level, extract):
    total, out = {}, {"0": {}}
    for row in sorted(rows, key=lambda r: r[level]):
        for k, v in extract(row).items():
            total[k] = total.get(k, 0) + v
        out[str(row[level])] = dict(total)
    return out


def potential_power_levels(rows):
    """Derived PP totals; only checked costs count, without discounts."""
    total, levels = 0, {"0": 0}
    for row in sorted(rows, key=lambda r: r["PotenLevelValue"]):
        if row.get("PotenBattlePowerCheck", False):
            total += row.get("PotenLevelUpReqPP", 0)
        levels[str(row["PotenLevelValue"])] = total
    return levels


def roster_ids():
    # Same key/unique-name resolution as build_party_html.py's roster uid.
    idx = {k: v for k, v in read(ROOT / "data/saviors_index.json").items() if not k.startswith("_")}
    by_key = {v["key"]: int(k) for k, v in idx.items() if v.get("key")}
    by_name = defaultdict(list)
    for k, v in idx.items():
        by_name[v.get("profile", {}).get("name")].append(int(k))
    out = set()
    for u in read(ROOT / "data/savior_reco.json")["saviors"]:
        uid = by_key.get(u["key"])
        candidates = by_name[u["name"]]
        if uid is None and len(candidates) == 1:
            uid = candidates[0]
        if uid is not None:
            out.add(uid)
    return out


def build_growth(static, game_build=None):
    static = Path(static)

    def load(name):
        return read(static / "tables" / (name + ".json"))["Data"]

    if game_build is None:
        match = re.search(r"Steam 빌드\s*`(\d+)`", (static / "README.md").read_text(encoding="utf-8"))
        if not match:
            raise ValueError("Cannot identify game build; specify --game-build")
        game_build = match[1]
    templates = {r["m_StatStrID"]: r for i in (1, 2, 3) for r in load(f"UNIT_STAT_TEMPLET{i}")}
    increments = {r["StatAddPerLevelStrID"]: stats(r["StatAddPerLevelData"])
                  for i in (1, 2, 3) for r in load(f"STAT_ADD_PER_LEVEL{i}")}
    roles = {r["JourneyStatRoleType"]: r for r in load("JOURNEY_STAT_ROLE_TYPE_TEMPLET")}
    # Focus/protect are globally x4, so no extra role fields are published.
    if any(r["MultiplyFocus"] != 10000 or r["MultiplyProtect"] != 10000 for r in roles.values()):
        raise ValueError("Journey focus/protect conversion changed; review calculator")
    grouped = {}
    resonance_unlock = defaultdict(dict)
    for row in load("RESONANCE_TEMPLET"):
        resonance_unlock[row["UnitId"]][str(row["ResonanceGrade"])] = row["UnlockLevel"]
    # TABLES.md: SKILL_TEMPLET -> SkillLevelGroup -> SKILL_LEVEL_GROUP_TEMPLET.
    # Star.Templets.decompiled.cs:25785,26156-26170: SkillLevelStat is the
    # selected level's absolute row, NOT a cumulative sum or a combat SE buff.
    skills = {r["m_SkillStrID"]: r for n in (1, 2) for r in load(f"SKILL_TEMPLET_{n}")}
    passive_levels = defaultdict(dict)
    for row in [r for n in (1, 2) for r in load(f"SKILL_LEVEL_GROUP_TEMPLET_{n}")]:
        values = {}
        for entry in row.get("SkillLevelStat", []):
            key = STAT.get(entry["SkillLevelStatType"])
            if key is None:
                continue  # combat-only stats outside the eight displayed stats
            values[key] = values.get(key, 0) + entry.get("SkillLevelStatRate", entry.get("SkillLevelStatValue", 0))
        passive_levels[row["SkillLevelGroupID"]][str(row["SkillLevelValue"])] = values
    for name, level, field, allowed in (
        ("RESONANCE_TEMPLET", "ResonanceGrade", "StatData", None),
        ("FAVOR_TEMPLET", "FavorLevel", "FavorRewardStat", KEYS),
        ("STAR_GRADE_TEMPLET", "StarGrade", "StatData", ("atkP", "hpP", "defP")),
    ):
        rows = defaultdict(list)
        for r in load(name):
            rows[r["UnitId"]].append(r)
        grouped[name] = {uid: cumulative(rs, level, lambda r: stats(r.get(field), allowed=allowed))
                         for uid, rs in rows.items()}
    units = {}
    ids = roster_ids()
    for row in load("UNIT_TEMPLET_BASE1"):
        uid = row["m_UnitID"]
        if uid not in ids:
            continue
        template = templates[row["m_StatStrID"]]
        base = stats(template["m_StatData"], allowed=KEYS)
        role = roles[row["JourneyStatRoleType"]]
        # The v1 exporter exposes skill slot 4 as skills.passive. Fail closed if
        # the roster gains another passive slot rather than silently omit it.
        unit_skills = [skills[s] for s in row["m_listSkill"]]
        passive_slots = [n for n, s in enumerate(unit_skills)
                         if s["m_NKM_SKILL_TYPE"] in ("NST_PASSIVE", "NST_UNIQUE_PASSIVE")]
        if passive_slots != [3] or len(unit_skills) != 4:
            raise ValueError(f"Review exported passive slot for unit {uid}")
        units[str(uid)] = dict(
            base={k: base.get(k, 0) for k in KEYS},
            per_level=increments[template["m_StatAddPerLevelStrID"]],
            journey_mul=[role[k] for k in ("MultiplyPower", "MultiplyHealth", "MultiplyEndurance")],
            tactics_groups=["TG_" + row["NKM_UNIT_ADJUST_TYPE"].removeprefix("NUAT_"),
                            "TG_" + row["m_NKM_UNIT_ROLE_TYPE"].removeprefix("NURT_")],
            resonance=grouped["RESONANCE_TEMPLET"].get(uid, {"0": {}}),
            resonance_unlock=resonance_unlock[uid],
            passive={"0": {}, **passive_levels[unit_skills[3]["SkillLevelGroup"]]},
            favor=grouped["FAVOR_TEMPLET"].get(uid, {"0": {}}),
            star=grouped["STAR_GRADE_TEMPLET"].get(uid, {"0": {}}))
    if set(map(int, units)) != ids:
        raise ValueError("Roster unit absent from private growth tables")
    tactics = defaultdict(dict)
    rows = defaultdict(list)
    for r in load("CENTRAL_TACTICS_TEMPLET"):
        rows[r["TacticsGroup"], r["TacticsType"]].append(r)
    for (group, kind), rs in sorted(rows.items()):
        tactics[group][kind] = cumulative(rs, "TacticsLevel", lambda r: stats(r.get("TacticsStat")))
    facility = cumulative(
        [r for r in load("CENTRAL_FACILITY_TEMPLET") if r["FacilityType"] == "FACILITY_TACTICS"],
        "FacilityLevel", lambda r: {k: r.get("BonusValue", 0) for k in ("atkP", "hpP", "defP")}
        if r.get("BonusType") == "TACTICS_COMMON_RATE_TRINITY" else {})
    # NKMSePotenTemplet.PotenLevelGroupId -> NKMSePotenLevelGroupTemplet
    # .PotenLevelValue / PotenLevelStat(Type, Rate/Value). Rows are absolute,
    # not cumulative (Star.Templets.decompiled.cs:21665-21674,21821-21828).
    potential_levels = defaultdict(dict)
    pp_rows = defaultdict(list)
    for row in load("POTENTIAL_LEVEL_GROUP_TEMPLET"):
        pp_rows[row["PotenLevelGroupId"]].append(row)
        values = {}
        for entry in row.get("PotenLevelStat", []):
            key = STAT.get(entry["PotenLevelStatType"])
            if key:
                values[key] = values.get(key, 0) + entry.get("PotenLevelStatRate", entry.get("PotenLevelStatValue", 0))
        potential_levels[row["PotenLevelGroupId"]][str(row["PotenLevelValue"])] = values
    # Keep empty rows too: known combat-only potentials contribute zero to these
    # eight stats, whereas an unknown ID/level must remain a diagnostic.
    potentials = {str(row["PotenId"]): potential_levels[row["PotenLevelGroupId"]]
                  for row in load("SE_POTENTIAL_TEMPLET")}
    # Battle power sums checked, undiscounted costs through the learned level;
    # stat rows above remain absolute. Star.Templets.decompiled.cs:21677-21690.
    pp_groups = {}
    for group, rows in pp_rows.items():
        pp_groups[group] = potential_power_levels(rows)
    potential_pp = {str(row["PotenId"]): pp_groups[row["PotenLevelGroupId"]]
                    for row in load("SE_POTENTIAL_TEMPLET")}
    return dict(
        _note="Derived numeric stat growth only; rates = 1/10000. Generated by tools/build_growth.py.",
        game_build=str(game_build), units=dict(sorted(units.items(), key=lambda p: int(p[0]))),
        star_link=cumulative(load("SYNCHRO_LEVEL_TEMPLET"), "SynchroLevel",
                             lambda r: stats(r.get("StatAddPerLevelData", {}))),
        tactics=dict(tactics), facility=facility, potentials=potentials, potential_pp=potential_pp,
        item_sets={str(r["EquipItemId"]): r.get("SetOptionId", 0) for r in load("EQUIP_ITEM_TEMPLET")},
        sets={str(r["SetOptionId"]): dict(parts=r["NeedParts"], stats=stats(r.get("SetStat"), "SetStatType", "SetStatValue"))
              for r in load("EQUIP_SET_OPTION_TEMPLET")})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--static", type=Path, default=Path(os.environ.get("STARSAVIOR_STATIC", DEFAULT_STATIC)))
    ap.add_argument("--game-build", help="Explicit extraction build if README has no build metadata")
    args = ap.parse_args()
    if not args.static.is_dir():
        print("SKIP: private static checkout unavailable")
        return
    growth = build_growth(args.static, args.game_build)
    dst = ROOT / "data/growth.json"
    dst.write_text(json.dumps(growth, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{dst.name}: {dst.stat().st_size} bytes, {len(growth['units'])} units, build {growth['game_build']}")


if __name__ == "__main__":
    main()
