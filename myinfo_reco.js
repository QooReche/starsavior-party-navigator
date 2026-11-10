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
      if (r && r.power > 0) { powers[engineKey(key)] = r.power; finals[key] = r;
        if (profile.sources?.[key]?.source === 'assumed') assumed++; }
      else assumed++;
    }
    return {powers: Object.keys(powers).length ? powers : null, finals, assumed};
  }
  const clone = x => JSON.parse(JSON.stringify(x));
  function assume(key, info, growth, preset = {}) {
    const data = growth?.assumed, spec = data?.units?.[key];
    if (!spec) throw new Error('가정 세팅 없음: ' + key);
    const owned = info.units.find(u => u.id === spec.uid);
    if (preset.kind === 'equipment' && !owned) throw new Error('장비 비교는 보유 구원자만 가능');
    const unit = owned ? clone(owned) : {id: spec.uid, star: 0, sigil: 0, favor: 0, resonance: 0,
      skills: {}, equip: [], gauntlet: {level: 0, journey: [0,0,0,0,0], potentials: [], blessings: []}};
    const fields = preset.fields || (preset.kind === 'equipment' ? ['equip']
      : ['level', 'equip', 'skills', 'resonance', 'journey', 'potentials']);
    const before = clone(unit);
    if(fields.some(f=>f==='journey'||f==='potentials'))unit.gauntlet ||= {};
    // A scenario registers only its target in a virtual slot. Never edit MI.info,
    // or mistake a savior's own level for its effective (slot/source) level.
    const levelTarget = fields.includes('level') ? info.star_link?.level ?? info.star_link_level : null;
    if (levelTarget != null && !Number.isInteger(levelTarget)) throw new Error('스타링크 레벨 없음');
    const targetInfo = levelTarget == null ? info : {...info, star_link:{
      level:levelTarget, source:info.star_link?.source || [],
      slots:[...(info.star_link?.slots || []).filter(s=>s.id!==unit.id), {index:-1,id:unit.id}]}};
    for (const field of fields) {
      if (field === 'level') { if (!unit.level) unit.level = levelTarget; }
      else if (field === 'resonance') {
        const unlock = growth.units[spec.uid].resonance_unlock;
        const level = levelTarget ?? Stats.effective_level(unit,info);
        unit.resonance = Math.max(0, ...Object.keys(unlock).map(Number).filter(n => unlock[n] <= level));
        if (owned) unit.resonance = Math.max(unit.resonance, owned.resonance);
      } else if (field === 'skills') unit.skills = clone(spec.skills);
      else if (field === 'equip') unit.equip = clone(spec.equip);
      else if (field === 'journey') unit.gauntlet.journey = clone(spec.journey);
      else if (field === 'potentials') {
        // Preserve unrelated learned potentials; replace only the special target family.
        const special = new Set(data.special_ids);
        unit.gauntlet.potentials = (unit.gauntlet.potentials || []).filter(p => !special.has(p[0])).concat([clone(spec.potential)]);
      } else throw new Error('지원하지 않는 육성 항목: ' + field);
    }
    const value = (u, f) => ['journey', 'potentials'].includes(f) ? u.gauntlet?.[f] : u[f];
    const changes = Object.fromEntries(fields.map(f=>[f, f==='level'
      ? {before:owned ? Stats.effective_level(owned,info) : null, after:levelTarget}
      : {before:value(before,f),after:value(unit,f)}]));
    const changedFields = fields.filter(f => !owned || JSON.stringify(changes[f].before) !== JSON.stringify(changes[f].after));
    return {unit, source: owned ? 'owned' : 'assumed', changedFields, presetId: data.version,
      changes, levelTarget, targetInfo, kind: preset.kind || 'growth', key};
  }
  function assumedProfile(base, assumed, info, growth, content) {
    const rule = Stats.rule_for_content(content), spec = growth.assumed.units[assumed.key];
    const result = Stats.final_stats(assumed.unit, assumed.targetInfo || info, growth, rule);
    const missing = [...(result?.missing || ['content'])];
    for (const [slot, level] of Object.entries(assumed.unit.skills))
      if (level && !spec.skill_levels[slot]?.includes(level)) missing.push('combat.skill:' + slot);
    for (const [id, level] of assumed.unit.gauntlet?.potentials || [])
      if (level && !growth.assumed.combat_support.potentials[id]?.includes(String(level))) missing.push('combat.potential:' + id);
    if (!result || !Number.isFinite(result.power) || !Object.values(result.stats).every(Number.isFinite)) missing.push('stats');
    if (missing.length) throw new Error('가정 자료 미지원: ' + [...new Set(missing)].join(', '));
    return {...base, results: {...base.results, [assumed.key]: result},
      units: {...base.units, [assumed.key]: assumed.unit}, sources: {...base.sources, [assumed.key]: assumed}};
  }
  function judgment(result, multiplier) {
    const extra = !result.clear && Number.isFinite(multiplier) && multiplier > 1
      ? Math.max(1000, Math.round((result.power * multiplier - result.power) / 1000) * 1000) : null;
    return {label: result.clear ? "오토 가능" : "오토 어려움", extra};
  }
  const api = {hash, profile, team, judgment, assume, assumedProfile};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MyInfoReco = api;
})(typeof window !== "undefined" ? window : globalThis);
