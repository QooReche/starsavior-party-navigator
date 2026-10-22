"""ss-myinfo-v1 -> final PvE stats (reference implementation of myinfo_stats.js).

No file access: only the imported unit, account info, and derived growth are used.
cr/cd/eh/er and *P use 1/10000, matching UnitDef/stats_override.
Unknown contributions remain zero and are explicitly listed in missing.
"""
import math

from .build import NST_KEY, unit_power

KEYS = ("atk", "hp", "def", "spd", "cr", "cd", "eh", "er")
RATE_KEYS = ("atkP", "hpP", "defP", "spdP")


def rule_for_content(content):
    """Unmapped content -> None, so callers retain their existing assumptions.

    rush / Flash Point -> BossRush is an assumption (no localized table link).
    BossRush/CosmoGate fixed level/resonance are verified in BATTLE_STAT_APPLY.
    """
    return {"op": "normal", "작전": "normal", "clo": "normal", "회랑": "normal", "Cloister": "normal",
            "cosmo": "fixed200", "코스모 게이트": "fixed200", "CosmoGate": "fixed200",
            "rush": "fixed200", "플래시 포인트": "fixed200", "BossRush": "fixed200"}.get(content)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def gauntlet_stats(unit, growth):
    """Return separate journey (x1) and potential (flat/R2) contributions.

    The UI gauntlet tab adds their flat values, but their formula stages differ.
    All values use engine units, including percentage points * 100.
    """
    unit, growth = unit or {}, growth or {}
    gauntlet = unit.get("gauntlet") or {}
    template = growth.get("units", {}).get(str(unit.get("id")), {})
    missing, journey, potential = set(), {}, {}
    raw = gauntlet.get("journey")
    if not isinstance(raw, list) or len(raw) != 5 or any(not _number(v) or v < 0 for v in raw):
        missing.add("gauntlet.journey")
    else:
        # StatFactorBundle.cs (reference:112-136; March NKM.cs:18575-18591):
        # clamp each journey value to 1500 and cast each converted value to int.
        # JOURNEY_STAT_ROLE_TYPE_TEMPLET MultiplyPower/Health/Endurance;
        # MultiplyFocus/Protect are 10000 for every role (builder verifies).
        mul = template.get("journey_mul")
        if not isinstance(mul, list) or len(mul) != 3:
            missing.add("growth:journey_mul")
        else:
            for i, (k, factor) in enumerate((("atk", 1), ("hp", 6), ("def", 0.5))):
                journey[k] = math.floor(min(raw[i], 1500) * factor * mul[i] / 10000)
        journey["eh"] = math.floor(min(raw[3], 1500) * 4)
        journey["er"] = math.floor(min(raw[4], 1500) * 4)
    entries = gauntlet.get("potentials")
    if not isinstance(entries, list):
        missing.add("gauntlet.potentials")
        entries = []
    for entry in entries:
        # NKM.Templets.cs:18436-18452 OBF_14766.Serialize = id, level,
        # discount index, standard blessing level. NKM.cs:18628-18643 reads
        # ONLY level (a), not discount (b) or blessing level (c).
        if (not isinstance(entry, list) or len(entry) != 4 or
                any(not _number(v) or v < 0 or v != math.floor(v) for v in entry)):
            missing.add("gauntlet.potentials.entry")
            continue
        pid, level, _discount, _blessing = entry
        pid, level = int(pid), int(level)  # JSON 1 and 1.0 use the same JS key.
        if level == 0:
            continue  # unlearned, even when discount / inherited blessing > 0
        table = growth.get("potentials", {}).get(str(pid))
        label = "gauntlet.potential:" + str(pid)
        if table is None:
            missing.add(label)
        elif str(level) not in table:
            missing.add(label + ":level")  # exact lookup; never clamp/extrapolate
        else:
            for k, v in table[str(level)].items():
                if k in KEYS + RATE_KEYS:
                    potential[k] = potential.get(k, 0) + v
    # ss-myinfo-v1 exports raw gauntlet col13 as 'blessings'. The March client
    # NKCStellarMemory adapter (NKC.cs:268033-268094) passes journey+SePoten
    # only; its separate list goes to SetHurdleList (231872). Current export
    # mapping is not verified, so do not turn these IDs into stat bonuses.
    # STAT_POTENTIAL_TEMPLET is JST_* (journey), not a second NST_* bonus.
    if gauntlet.get("blessings") not in (None, []):
        missing.add("gauntlet_blessings")
    return dict(journey=journey, potential=potential, missing=sorted(missing))


def final_stats(unit, info, growth, rule="normal"):
    """Return {stats, missing, power[, build_mismatch]}, or None for an unknown rule.

    unit is one imported info.units entry (id = roster uid). Absent fields use
    neutral defaults, with diagnostics. Cumulative rows use the last known level;
    levels beyond published tables are flagged, never silently extrapolated.
    """
    if rule not in ("normal", "fixed200"):
        return None
    unit, info, growth = unit or {}, info or {}, growth or {}
    missing = set()

    def number(obj, key, label, default=0, minimum=0):
        v = obj.get(key)
        if not _number(v) or v < minimum or v != math.floor(v):
            missing.add(label)
            return default
        return v

    def at(table, level, label):
        if not isinstance(table, dict) or not table:
            missing.add(label)
            return {}
        levels = sorted(int(k) for k in table)
        if level > levels[-1]:
            missing.add(label + ":level")
        eligible = [n for n in levels if n <= level]
        return table[str(eligible[-1])] if eligible else {}

    def add(dst, src, times=1):
        for k in KEYS + RATE_KEYS:
            dst[k] = dst.get(k, 0) + src.get(k, 0) * times

    stats = {k: 0 for k in KEYS}
    uid = unit.get("id")
    template = growth.get("units", {}).get(str(uid)) if _number(uid) else None
    if template is None:
        missing.add("unit:" + (str(uid) if uid is not None else "missing"))
    else:
        level = 200 if rule == "fixed200" else number(info, "star_link_level", "star_link_level", 1, 1)
        resonance = 10 if rule == "fixed200" else number(unit, "resonance", "resonance")
        # NKM.Templets.cs:17837-17842 serializes limit break (star), StarGrade
        # (sigil), resonance separately. NKM.cs:1979-1982,18553-18556 passes
        # ONLY StarGrade to STAR_GRADE_TEMPLET, never star + sigil.
        star = number(unit, "sigil", "sigil")
        favor = number(unit, "favor", "favor")
        base = template.get("base", {})
        inc = template.get("per_level", {})
        syn = {} if rule == "fixed200" else at(growth.get("star_link"), level, "growth:star_link")
        # IUnitResonanceTemplet (NKM.Templets.cs:25673-25690) stops at
        # UnlockLevel. Even an inconsistent imported grade cannot bypass it.
        unlock = template.get("resonance_unlock", {})
        unlocked = resonance
        for grade in sorted(map(int, unlock)):
            if grade <= resonance and level < unlock[str(grade)]:
                unlocked = grade - 1
                break
        res = at(template.get("resonance"), unlocked, "growth:resonance")
        stars = at(template.get("star"), star, "growth:star")
        flat = dict(stars)
        add(flat, at(template.get("favor"), favor, "growth:favor"))

        tactics = info.get("tactics") or {}
        common = number(tactics, "common_level", "tactics.common_level")
        tables = growth.get("tactics", {})
        add(flat, at(tables.get("TG_COMMON", {}).get("MAIN"), common, "growth:tactics.TG_COMMON.MAIN"))
        groups = tactics.get("groups") or {}
        for group in ["TG_SAVIOR", "TG_ARCANA"] + template.get("tactics_groups", []):
            for kind, field in (("ATTACK", "attack"), ("DEFENSE", "defense"), ("HP", "hp")):
                label = "tactics." + group + "." + field
                lv = number(groups.get(group) or {}, field, label)
                add(flat, at(tables.get(group, {}).get(kind), lv, "growth:" + label))
        facility = number(tactics, "facility_level", "tactics.facility_level")
        add(flat, at(growth.get("facility"), facility, "growth:facility"))

        equipment = unit.get("equip")
        if not isinstance(equipment, list):
            missing.add("equip")
            equipment = []
        counts = {}
        for item in equipment:
            iid = str(item.get("item_id"))
            sid = growth.get("item_sets", {}).get(iid)
            if sid is None:
                missing.add("item:" + iid)
            elif sid:
                counts[str(sid)] = counts.get(str(sid), 0) + 1
            if not isinstance(item.get("main"), dict):
                missing.add("equip.main")
            if not isinstance(item.get("subs"), list):
                missing.add("equip.subs")
            for opt in [item.get("main") or {}] + (item.get("subs") or []):
                k = NST_KEY.get(opt.get("stat"))
                v = opt.get("value")
                if k is None or not _number(v):
                    missing.add("equip.stat:" + str(opt.get("stat", "missing")))
                else:
                    flat[k] = flat.get(k, 0) + v
        for sid, count in sorted(counts.items()):
            effect = growth.get("sets", {}).get(sid)
            if not effect or not effect.get("parts", 0) > 0:
                missing.add("set:" + sid)
            else:
                add(flat, effect.get("stats", {}), count // effect["parts"])

        gauntlet = gauntlet_stats(unit, growth)
        jf = gauntlet["journey"]
        # StatFactorBundle potential bucket -> FinalStatCombiner R2 and flat,
        # NOT journey/R1 (March NKM.cs:18263,18344; current reference same).
        add(flat, gauntlet["potential"])
        missing.update(gauntlet["missing"])
        # StatFactorBundle NKM.cs:18563-18608 builds passive / unique passive;
        # FinalStatCombiner 18269-18271 puts their rates in R2 (flat:18346-18347).
        # Current reference StatFactorBundle.cs:118-119 and combiner:193-195
        # preserve the same buckets. Use the learned level's absolute stat row.
        passive_level = int(number(unit.get("skills") or {}, "passive", "skills.passive"))
        passive = template.get("passive")
        if not isinstance(passive, dict):
            missing.add("unit_passive")
        elif str(passive_level) not in passive:
            missing.add("unit_passive:level")
        else:
            add(flat, passive[str(passive_level)])
        for k in KEYS:
            if k not in base:
                missing.add("growth:base." + k)
            # Normal PvE uses both level buckets equally; fixed200 suppresses LvlB/synchro.
            lvl_a = inc.get(k, 0) * (min(level, 200) - 1)
            lvl_b = inc.get(k, 0) * max(0, level - 200) + syn.get(k, 0)
            x1 = base.get(k, 0) + lvl_a + lvl_b + jf.get(k, 0)
            # NKM.cs:18541-18556 resolves IUnitResonanceTemplet -> R1 bucket
            # OBF_9851; IUnitStarGradeTemplet -> R2 bucket OBF_3415.
            # Combiner:18260-18261,18342: resonance flat is AFTER R1 and
            # BEFORE R2. Facilities/tactics/sets stay in R2 (18265,18846).
            r1 = (base.get(k + "P", 0) + res.get(k + "P", 0)) / 10000
            x = x1 + res.get(k, 0) + x1 * r1
            y = x + flat.get(k, 0) + x * (flat.get(k + "P", 0) / 10000)
            stats[k] = max(0, math.floor(y))
    skills = unit.get("skills") or {}
    skill_sum = sum(number(skills, k, "skills." + k) for k in ("basic", "special", "ultimate", "passive"))
    missing.add("power_pp")
    result = dict(stats=stats, missing=[], power=unit_power(stats, pp=0, skill_level_sum=skill_sum))
    if info.get("game_build") is None or growth.get("game_build") is None:
        missing.add("game_build")
    elif str(info["game_build"]) != str(growth["game_build"]):
        result["build_mismatch"] = True
    result["missing"] = sorted(missing)
    return result
