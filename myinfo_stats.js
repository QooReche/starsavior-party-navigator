// ss-myinfo-v1 final stats. Keep arithmetic/order in sync with starsavior/myinfo_stats.py.
// All percentage stats and *P rates use 1/10000. No network/storage access.
(function (root) {
  "use strict";
  const KEYS = ["atk", "hp", "def", "spd", "cr", "cd", "eh", "er"];
  const ALL = KEYS.concat(["atkP", "hpP", "defP", "spdP"]);
  const NST = Object.fromEntries([
    "NST_ATK", "NST_HP", "NST_DEF", "NST_TURN_SPEED", "NST_RATE_CRITICAL",
    "NST_RATE_CRITICAL_DAMAGE", "NST_RATE_EFFECT_HIT", "NST_RATE_EFFECT_EVADE",
    "NST_NV_RATE_ATK", "NST_NV_RATE_HP", "NST_NV_RATE_DEF"
  ].map((k, i) => [k, ALL[i]]));
  const get = (o, k, fallback = 0) => Object.prototype.hasOwnProperty.call(o, k) ? o[k] : fallback;

  function rule_for_content(content) {
    // Flash Point/rush -> BossRush is assumed; localized mapping is unverified.
    return get({op: "normal", "작전": "normal", clo: "normal", "회랑": "normal", Cloister: "normal",
      cosmo: "fixed200", "코스모 게이트": "fixed200", CosmoGate: "fixed200",
      rush: "fixed200", "플래시 포인트": "fixed200", BossRush: "fixed200"}, content, null);
  }

  function unit_power(stats, pp = 0, skill_level_sum = 34) {
    // Port of battlesim/starsavior/build.py (including caps and operation order).
    const {atk, hp, def: df, spd} = stats;
    const cr = Math.min(1.0, stats.cr / 10000.0), cdm = Math.min(3.0, stats.cd / 10000.0);
    const eh = get(stats, "eh", 10000) / 10000.0, ee = get(stats, "er") / 10000.0;
    const aB = atk / 10 * 12, hB = hp / 55 * 12, dB = df / 5 * 12;
    const sp = (100 + (spd - 100) / 5) / 100, ef = Math.max(0.0, 1 + (eh - 1 + ee) / 10);
    const pot = 1 + pp * 0.0001;
    const crit_mix = x => Math.max(0.0, x * (1 - cr)) + x * cr * (1 + cdm);
    const m1 = (crit_mix(aB) + hB + dB) * pot * sp * ef;
    const bal = (atk / 10 + hp / 55 + df / 5) / 3 * 12;
    const m2 = (crit_mix(bal) + hB + dB) * pot * sp * ef;
    const m3 = (aB + hB + dB) * (1 + (cr / 1 + cdm / 2) / 3) * pot * sp * ef;
    return Math.floor(Math.max(m1, m2, m3) * (1 + 3 * 0.02 + skill_level_sum * 0.01));
  }

  function gauntlet_stats(unit, growth) {
    unit = unit || {}; growth = growth || {};
    const gauntlet = unit.gauntlet || {}, template = get(growth.units || {}, String(unit.id), {});
    const missing = new Set(), journey = {}, potential = {}, raw = gauntlet.journey;
    let power_pp = 0;
    if (!Array.isArray(raw) || raw.length !== 5 || raw.some(v => !Number.isFinite(v) || v < 0)) {
      missing.add("gauntlet.journey");
    } else {
      // StatFactorBundle (reference:112-136; March NKM.cs:18575-18591):
      // clamp at 1500, cast each conversion. JOURNEY_STAT_ROLE_TYPE_TEMPLET
      // MultiplyPower/Health/Endurance; Focus/Protect=10000 verified by builder.
      const mul = template.journey_mul;
      if (!Array.isArray(mul) || mul.length !== 3) missing.add("growth:journey_mul");
      else for (const [i, [k, factor]] of [["atk", 1], ["hp", 6], ["def", 0.5]].entries()) {
        journey[k] = Math.floor(Math.min(raw[i], 1500) * factor * mul[i] / 10000);
      }
      journey.eh = Math.floor(Math.min(raw[3], 1500) * 4);
      journey.er = Math.floor(Math.min(raw[4], 1500) * 4);
    }
    let entries = gauntlet.potentials;
    if (!Array.isArray(entries)) { missing.add("gauntlet.potentials"); missing.add("power_pp"); entries = []; }
    for (const entry of entries) {
      // NKM.Templets.cs:18436-18452 Serialize = id, level(a), discount(b),
      // blessing(c). NKM.cs:18628-18643 only uses a for the exact level row.
      if (!Array.isArray(entry) || entry.length !== 4 || entry.some(v => !Number.isInteger(v) || v < 0)) {
        missing.add("gauntlet.potentials.entry"); missing.add("power_pp"); continue;
      }
      const [pid, level] = entry;
      if (level === 0) continue;
      // Cumulative checked, undiscounted PP costs (Star.Templets:21677-21690).
      const pp = get(get(growth.potential_pp || {}, String(pid), {}), String(level), null);
      if (!Number.isInteger(pp) || pp < 0) missing.add("power_pp");
      else power_pp += pp;
      const table = get(growth.potentials || {}, String(pid), null), label = "gauntlet.potential:" + pid;
      if (table === null) missing.add(label);
      else if (!Object.prototype.hasOwnProperty.call(table, String(level))) missing.add(label + ":level");
      else for (const [k, v] of Object.entries(table[String(level)])) {
        if (ALL.includes(k)) potential[k] = get(potential, k) + v;
      }
    }
    // Current export's 'blessings' col13 remains unverified. March client
    // NKC.cs:268033-268094 passes only journey+SePoten to stats, and its list
    // goes to SetHurdleList (231872). STAT_POTENTIAL_TEMPLET uses JST_*, so
    // adding it again to imported journey would risk counting it twice.
    if (gauntlet.blessings != null && (!Array.isArray(gauntlet.blessings) || gauntlet.blessings.length)) {
      missing.add("gauntlet_blessings");
    }
    return {journey, potential, power_pp, missing: Array.from(missing).sort()};
  }

  function final_stats(unit, info, growth, rule = "normal") {
    if (rule !== "normal" && rule !== "fixed200") return null;
    unit = unit || {}; info = info || {}; growth = growth || {};
    const missing = new Set();
    function number(obj, key, label, fallback = 0, minimum = 0) {
      const v = obj[key];
      if (!Number.isFinite(v) || v < minimum || !Number.isInteger(v)) {
        missing.add(label); return fallback;
      }
      return v;
    }
    function at(table, level, label) {
      if (!table || typeof table !== "object" || !Object.keys(table).length) {
        missing.add(label); return {};
      }
      const levels = Object.keys(table).map(Number).sort((a, b) => a - b);
      if (level > levels[levels.length - 1]) missing.add(label + ":level");
      const eligible = levels.filter(n => n <= level);
      return eligible.length ? table[String(eligible[eligible.length - 1])] : {};
    }
    function add(dst, src, times = 1) {
      for (const k of ALL) dst[k] = get(dst, k) + get(src, k) * times;
    }
    const stats = Object.fromEntries(KEYS.map(k => [k, 0]));
    const gauntlet = gauntlet_stats(unit, growth);
    for (const m of gauntlet.missing) missing.add(m);
    const uid = unit.id;
    const template = Number.isFinite(uid) ? get(growth.units || {}, String(uid), null) : null;
    if (!template) {
      missing.add("unit:" + (uid == null ? "missing" : String(uid)));
    } else {
      const level = rule === "fixed200" ? 200 : number(info, "star_link_level", "star_link_level", 1, 1);
      const resonance = rule === "fixed200" ? 10 : number(unit, "resonance", "resonance");
      // NKM.Templets.cs:17837-17842 / NKM.cs:1979-1982: only sigil is
      // StarGrade; star is limit break and must not be added to it.
      const star = number(unit, "sigil", "sigil");
      const favor = number(unit, "favor", "favor");
      const base = template.base || {}, inc = template.per_level || {};
      const syn = rule === "fixed200" ? {} : at(growth.star_link, level, "growth:star_link");
      // IUnitResonanceTemplet, NKM.Templets.cs:25673-25690: UnlockLevel gate.
      const unlock = template.resonance_unlock || {};
      let unlocked = resonance;
      for (const grade of Object.keys(unlock).map(Number).sort((a, b) => a - b)) {
        if (grade <= resonance && level < unlock[String(grade)]) { unlocked = grade - 1; break; }
      }
      const res = at(template.resonance, unlocked, "growth:resonance");
      const stars = at(template.star, star, "growth:star");
      const flat = Object.assign({}, stars);
      add(flat, at(template.favor, favor, "growth:favor"));
      const tactics = info.tactics || {}, tables = growth.tactics || {};
      const common = number(tactics, "common_level", "tactics.common_level");
      add(flat, at((tables.TG_COMMON || {}).MAIN, common, "growth:tactics.TG_COMMON.MAIN"));
      const groups = tactics.groups || {};
      for (const group of ["TG_SAVIOR", "TG_ARCANA"].concat(template.tactics_groups || [])) {
        for (const [kind, field] of [["ATTACK", "attack"], ["DEFENSE", "defense"], ["HP", "hp"]]) {
          const label = "tactics." + group + "." + field;
          const lv = number(groups[group] || {}, field, label);
          add(flat, at((tables[group] || {})[kind], lv, "growth:" + label));
        }
      }
      const facility = number(tactics, "facility_level", "tactics.facility_level");
      add(flat, at(growth.facility, facility, "growth:facility"));
      let equipment = unit.equip;
      if (!Array.isArray(equipment)) { missing.add("equip"); equipment = []; }
      const counts = {};
      for (const item of equipment) {
        const iid = String(get(item, "item_id", "None"));
        const sid = get(growth.item_sets || {}, iid, null);
        if (sid == null) missing.add("item:" + iid);
        else if (sid) counts[String(sid)] = get(counts, String(sid)) + 1;
        if (!item.main || typeof item.main !== "object" || Array.isArray(item.main)) missing.add("equip.main");
        if (!Array.isArray(item.subs)) missing.add("equip.subs");
        for (const opt of [item.main || {}].concat(item.subs || [])) {
          const k = get(NST, opt.stat, null), v = opt.value;
          if (k === null || !Number.isFinite(v)) missing.add("equip.stat:" + String(get(opt, "stat", "missing")));
          else flat[k] = get(flat, k) + v;
        }
      }
      for (const sid of Object.keys(counts).sort()) {
        const effect = (growth.sets || {})[sid];
        if (!effect || !(effect.parts > 0)) missing.add("set:" + sid);
        else add(flat, effect.stats || {}, Math.floor(counts[sid] / effect.parts));
      }
      const jf = gauntlet.journey;
      // StatFactorBundle -> FinalStatCombiner: potential flat/R2, separate
      // from journey x1/R1 (March NKM.cs:18263,18344; current reference same).
      add(flat, gauntlet.potential);
      // NKM.cs:18563-18608 / 18269-18271: permanent SkillLevelStat joins R2.
      // Absolute learned-level row (Star.Templets.cs:26156-26170), not max level.
      const passiveLevel = number(unit.skills || {}, "passive", "skills.passive");
      if (!template.passive || typeof template.passive !== "object") missing.add("unit_passive");
      else if (!Object.prototype.hasOwnProperty.call(template.passive, String(passiveLevel))) missing.add("unit_passive:level");
      else add(flat, template.passive[String(passiveLevel)]);
      for (const k of KEYS) {
        if (!Object.prototype.hasOwnProperty.call(base, k)) missing.add("growth:base." + k);
        const lvl_a = get(inc, k) * (Math.min(level, 200) - 1);
        const lvl_b = get(inc, k) * Math.max(0, level - 200) + get(syn, k);
        const x1 = get(base, k) + lvl_a + lvl_b + get(jf, k);
        // NKM.cs:18541-18556,18260-18261,18342: resonance rate in R1,
        // resonance flat after R1, sigil rate in R2. See Python source mapping.
        const r1 = (get(base, k + "P") + get(res, k + "P")) / 10000;
        const x = x1 + get(res, k) + x1 * r1;
        const y = x + get(flat, k) + x * (get(flat, k + "P") / 10000);
        stats[k] = Math.max(0, Math.floor(y));
      }
    }
    const skills = unit.skills || {};
    let skillSum = 0;
    for (const k of ["basic", "special", "ultimate", "passive"]) skillSum += number(skills, k, "skills." + k);
    // Slots 1..4 include unique passive; retain the current databook formula.
    const result = {stats, missing: [], power: unit_power(stats, gauntlet.power_pp, skillSum)};
    if (info.game_build == null || growth.game_build == null) missing.add("game_build");
    else if (String(info.game_build) !== String(growth.game_build)) result.build_mismatch = true;
    result.missing = Array.from(missing).sort();
    result.combat = {
      skills: Object.fromEntries(["basic", "special", "ultimate", "passive"].filter(k => k in skills).map(k => [k, skills[k]])),
      potentials: (Array.isArray(unit.gauntlet?.potentials) ? unit.gauntlet.potentials : [])
        .filter(p => Array.isArray(p) && p.length === 4 && p.every(v => Number.isInteger(v) && v >= 0) && p[1] > 0).map(p => [p[0], p[1]])
    };
    return result;
  }
  const api = {final_stats, gauntlet_stats, rule_for_content, unit_power};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MyInfoStats = api;
})(typeof window !== "undefined" ? window : globalThis);
