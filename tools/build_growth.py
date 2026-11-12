"""Extract only derived stat growth; never read/copy account samples or ground truth.

python -X utf8 -I tools/build_growth.py --static <private checkout>
Output is always this checkout's data/growth.json. Rates use 1/10000 units.
"""
import sys
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority
from battlesim.fileio import atomic_text
from battlesim.starsavior.savior_ids import uid_resolver
from battlesim.starsavior.build import setting_spec, build_rules, NST_KEY
from battlesim.starsavior.data import DB
from battlesim.starsavior.parser import UnitDef
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
    resolve = uid_resolver(read(ROOT / "data/saviors_index.json"))
    uids = (resolve(u["key"], u["name"]) for u in read(ROOT / "data/savior_reco.json")["saviors"])
    return {uid for uid in uids if uid is not None}


def assumed_presets(load, game_build):
    """Processed equipment/targets only; policy remains in build.setting_spec.

    Freeze the guide's crit branch/roll conversion at standard Lv200. This is
    a reproducible target set, not optimization of the imported account's gear.
    """
    import hashlib
    db = DB(str(ROOT))
    combat = read(ROOT / 'data/myinfo_combat.json')
    resolve = uid_resolver(read(ROOT / 'data/saviors_index.json'))
    slot_types = dict(zip(('무기', '장갑', '갑옷', '신발', '목걸이', '반지'),
                         ('ET_WEAPON', 'ET_GLOVES', 'ET_ARMOR', 'ET_SHOES', 'ET_NECKLACE', 'ET_RING')))
    nst = {v: k for k, v in NST_KEY.items()}
    items = sorted((r for r in load('EQUIP_ITEM_TEMPLET')
                    if r['EquipTier'] == 2 and r['EquipGrade'] == 'IG_LEGENDARY'), key=lambda r: r['EquipItemId'])
    units, mains = {}, {}
    for savior in read(ROOT / 'data/savior_reco.json')['saviors']:
        key = savior['key']
        d = UnitDef(db, key, level=200, res_stage=10, star=0, build='none')
        spec = setting_spec(db, key, db.units[key], base_stats=d.stats, passive_cr=d.passive['cr'])
        equip = []
        for piece in spec['equipment']:
            stat = nst[piece['main']['stat']]
            matches = [r for r in items if r['EquipType'] == slot_types[piece['slot']]
                       and r.get('SetOptionId', 0) == piece['set'] and r['EquipMainStatType'] == stat]
            if not matches:
                raise ValueError(f'No T2 legendary item for {key}: {piece}')
            item = matches[0]
            value = item['EquipMainStatValue'] + 15 * item['EquipEnchantPerStat']
            if value != piece['main']['value']:
                raise ValueError(f'Guide main stat differs from current table: {key}')
            mains.setdefault(piece['slot'], {})[stat] = value
            equip.append(dict(item_id=item['EquipItemId'], level=2, enhance=15,
                              main=dict(stat=stat, value=value),
                              subs=[dict(stat=nst[k], value=v) for k, v in piece['subs'].items()]))
        skill_levels = {slot: sorted(map(int, rows)) for slot, rows in combat['units'][key].items()}
        pid, lv, _, _ = spec['potential_entry']
        if str(lv) not in combat['potentials'].get(str(pid), {}):
            raise ValueError(f'Unsupported preset potential: {key}/{pid}/{lv}')
        units[key] = dict(uid=resolve(key, savior['name']), equip=equip,
                          journey=spec['journey_raw'], potential=spec['potential_entry'],
                          skills={k: max(v) for k, v in skill_levels.items()}, skill_levels=skill_levels,
                          source=spec['summary']['source'], summary=spec['summary'])
    policy = {k: v for k, v in build_rules().items() if k.startswith('sub_') or k == 'potential_pick'}
    out = dict(game_build=str(game_build), units=units, mains=mains, sub_policy=policy,
               special_ids=sorted(p['id'] for p in db.main['dict']['pot'] if p.get('cat') == '특수'),
               combat_support={k: {pid: list(rows) for pid, rows in combat[k].items()} for k in ['potentials']},
               source=['battlesim/starsavior/build.py:setting_spec', 'rawdata/guide_app-core.js',
                       'battlesim/rules/builds.json', 'data/myinfo_combat.json'],
               selection='standard-lv200-crit; fixed guide target; not account gear optimization')
    out['version'] = 'guide-t2-v1-' + hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:12]
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
    # 클라 표에서 사라진 구원자(10/22 패치에서 1060 삭제)는 공개 로스터에 남아 있으면 이전 성장표 값을 보존한다
    # (tools/build_myinfo_combat.py 와 같은 규칙). 이전 값도 없으면 지금처럼 실패한다.
    missing = ids - set(map(int, units))
    prev_path = ROOT / "data/growth.json"
    if missing and prev_path.exists():
        prev = json.loads(prev_path.read_text(encoding="utf-8")).get("units", {})
        for uid in sorted(missing):
            if str(uid) in prev:
                units[str(uid)] = prev[str(uid)]
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
    potential_unsupported = {pid: '레벨 표 없음' for pid, rows in potentials.items() if not rows}
    if len(potentials) != len(load('SE_POTENTIAL_TEMPLET')):
        raise ValueError('Duplicate potential ID: review table before publishing')
    # Battle power sums checked, undiscounted costs through the learned level;
    # stat rows above remain absolute. Star.Templets.decompiled.cs:21677-21690.
    pp_groups = {}
    for group, rows in pp_rows.items():
        pp_groups[group] = potential_power_levels(rows)
    # 레벨 묶음이 아직 없는 새 잠재력(10/22 패치 11014)은 위 potentials 처럼 빈 값(능력치·전투력 기여 0)
    potential_pp = {str(row["PotenId"]): pp_groups.get(row["PotenLevelGroupId"], {"0": 0})
                    for row in load("SE_POTENTIAL_TEMPLET")}
    return dict(
        _note="Derived numeric stat growth only; rates = 1/10000. Generated by tools/build_growth.py.",
        game_build=str(game_build), units=dict(sorted(units.items(), key=lambda p: int(p[0]))),
        assumed=assumed_presets(load, game_build),
        star_link=cumulative(load("SYNCHRO_LEVEL_TEMPLET"), "SynchroLevel",
                             lambda r: stats(r.get("StatAddPerLevelData", {}))),
        tactics=dict(tactics), facility=facility, potentials=potentials, potential_pp=potential_pp,
        potential_unsupported=potential_unsupported,
        item_sets={str(r["EquipItemId"]): r.get("SetOptionId", 0) for r in load("EQUIP_ITEM_TEMPLET")},
        sets={str(r["SetOptionId"]): dict(parts=r["NeedParts"], stats=stats(r.get("SetStat"), "SetStatType", "SetStatValue"))
              for r in load("EQUIP_SET_OPTION_TEMPLET")})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--static", type=Path)
    ap.add_argument("--game-build", help="Explicit extraction build if README has no build metadata")
    args = ap.parse_args()
    try:
        args.static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    growth = build_growth(args.static, args.game_build)
    dst = ROOT / "data/growth.json"
    atomic_text(dst, json.dumps(growth, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"{dst.name}: {dst.stat().st_size} bytes, {len(growth['units'])} units, build {growth['game_build']}")


if __name__ == "__main__":
    main()
