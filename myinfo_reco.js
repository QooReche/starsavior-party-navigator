// Pure adapters for personalized recommendations; no storage or network access.
(function (root) {
  "use strict";
  const Stats = typeof module !== "undefined" && module.exports ? require("./myinfo_stats.js") : root.MyInfoStats;
  function hash(info) {
    const s = JSON.stringify(info); let h = 2166136261;
    for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
    return (h >>> 0).toString(16);
  }
  function profile(info, roster, growth, content) {
    const rule = Stats.rule_for_content(content), results = {}, units = {};
    if (info) {
      const byId = new Map(info.units.map(u => [u.id, u]));
      for (const s of roster) {
        const u = byId.get(s.uid); if (!u) continue;
        units[s.key] = u;
        if (rule && growth?.units?.[u.id]) results[s.key] = Stats.final_stats(u, info, growth, rule);
      }
    }
    return {rule, results, units, mismatch: !!(info && growth && String(info.game_build) !== String(growth.game_build))};
  }
  function team(keys, profile, engineKey) {
    const powers = {}, finals = {}; let assumed = 0;
    for (const key of keys) {
      const r = profile.results[key];
      if (r && r.power > 0) { powers[engineKey(key)] = r.power; finals[key] = r; }
      else assumed++;
    }
    return {powers: Object.keys(powers).length ? powers : null, finals, assumed};
  }
  function judgment(result, multiplier) {
    const extra = !result.clear && Number.isFinite(multiplier) && multiplier > 1
      ? Math.max(1000, Math.round((result.power * multiplier - result.power) / 1000) * 1000) : null;
    return {label: result.clear ? "오토 가능" : "오토 어려움", extra};
  }
  const api = {hash, profile, team, judgment};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MyInfoReco = api;
})(typeof window !== "undefined" ? window : globalThis);
