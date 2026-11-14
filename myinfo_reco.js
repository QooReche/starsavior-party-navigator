// Pure adapters for personalized recommendations; no storage or network access.
(function (root) {
  "use strict";
  const Stats = typeof module !== "undefined" && module.exports ? require("./myinfo_stats.js") : root.MyInfoStats;
  const itemSlots = typeof module !== "undefined" && module.exports ? require("./data/myinfo_slots.json") : null;
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
    const currentLevel = Stats.level_info(unit,info), levelUnknown = !!owned && currentLevel.source==='legacy';
    if(levelUnknown && fields.length===1 && fields[0]==='level')
      throw Object.assign(new Error('레벨 자료 없음 · 다시 불러오기 필요'),{code:'level-data'});
    // NKC:420258-420264 excludes sources. A growth target must never lower a level.
    const linkLevel = info.star_link?.level ?? info.star_link_level;
    const register = fields.includes('level') && !levelUnknown && !info.star_link?.source?.includes(unit.id)
      && (!owned || linkLevel>currentLevel.level);
    const levelTarget = register ? linkLevel : null;
    if (levelTarget != null && !Number.isInteger(levelTarget)) throw new Error('스타링크 레벨 없음');
    const targetInfo = levelTarget == null ? info : {...info, star_link:{
      level:levelTarget, source:info.star_link?.source || [],
      slots:[...(info.star_link?.slots || []).filter(s=>s.id!==unit.id), {index:-1,id:unit.id}]}};
    for (const field of fields) {
      if (field === 'level') { if (!unit.level) unit.level = levelTarget; }
      else if (field === 'resonance') {
        const unlock = growth.units[spec.uid].resonance_unlock;
        const level = Stats.effective_level(unit,targetInfo);
        unit.resonance = Math.max(0, ...Object.keys(unlock).map(Number).filter(n => unlock[n] <= level));
        if (owned) unit.resonance = Math.max(unit.resonance, owned.resonance);
      } else if (field === 'favor') unit.favor = 30;
      else if (field === 'skills') unit.skills = clone(spec.skills);
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
      ? {before:owned ? currentLevel.level : null, after:Stats.effective_level(unit,targetInfo)}
      : {before:value(before,f),after:value(unit,f)}]));
    const changedFields = fields.filter(f => !owned || JSON.stringify(changes[f].before) !== JSON.stringify(changes[f].after));
    return {unit, source: owned ? 'owned' : 'assumed', changedFields, presetId: data.version,
      changes, levelTarget, levelUnknown, targetInfo, kind: preset.kind || 'growth', key};
  }
  function assumedProfile(base, assumed, info, growth, content) {
    const rule = Stats.rule_for_content(content), spec = growth.assumed.units[assumed.key];
    const result = Stats.final_stats(assumed.unit, assumed.targetInfo || info, growth, rule);
    // Legacy levels still use the documented fallback; other missing stats block evaluation.
    const missing = [...(result?.missing || ['content'])].filter(k=>
      !(assumed.levelUnknown && ['unit.level','star_link.level','star_link.source','star_link.slots'].includes(k)));
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
  // Compare equipment by body part, without depending on import array order.
  function equipmentValue(equip, slots) {
    return (equip||[]).map(e=>[slots?.[e.item_id]??-1,e]).sort((a,b)=>a[0]-b[0]||a[1].item_id-b[1].item_id);
  }
  // Independent account snapshot. Equipment is selected as one complete bundle.
  const OVERWRITE_VERSION='grown-account-v6';   // v6: 아카이브 주력 판단 = 공략 DB 여정 스탯 우선순위, 장비×기록 조합 비교 / v5: 기록 통째 교체(칸별 섞기 금지)
  // Recommendation policy, not a battle rule. Included verbatim in history/cache signatures.
  const THRESHOLD_POLICY=Object.freeze({skillMax:7,skillTarget:10,passive:false,
    equipMin:12,equipSum:84,archiveMain:950,favorMax:20,favorTarget:30,
    resonanceMax:10,linkGap:10,potentialTarget:1,ownedOnly:true,archiveWhole:true,archivePriority:'guide'});
  // ── 스텔라 아카이브(여정 기록) 목표 ──
  // 아카이브 5칸은 한 번의 여정 결과로 통째로 정해진다(사용자 확인 11/14: 한 칸 SG 는 현실적, 두 칸 동시 SG 는 어려움) → 칸별로 큰 값을 골라 섞지 않는다.
  // 주력 판단은 공략 DB 의 «여정 스탯 우선순위»(data/journey_priority.json, tools/extract_journey_priority.js)를 따른다:
  //   rows = [우선순위 줄…], 줄 = [[칸…] > [칸…] …](같은 묶음 안은 동률). 일반 디펜더는 두 줄(퓨어탱커 / 공격력 탱커) — 가이드가 하나를 고르지 않으므로 둘 다 본다.
  //   · 충족: 어느 줄이든 첫 묶음의 칸 가운데 하나가 archiveMain 이상 → 아카이브는 키울 항목이 아님(예: 왈츠 아세라 = [힘, 체력] 이 첫 묶음 → 체력 SG 면 충족)
  //   · 미충족: 줄마다 «다시 만든 기록» 후보 하나 — 기준표 예시 기록의 값(큰 순)을 우선순위 순서대로 배정. 같은 묶음 안에서는 지금 값이 높은 칸에 큰 값을 준다
  //     (동률인 칸이면 이미 더 키운 쪽을 주력으로 삼는 편이 지금 기록에 가까운 목표이기 때문. 지금 값도 같으면 칸 번호 순)
  // 우선순위 표가 없으면(옛 호출) 기준표 기록의 주력 칸만 보고 기준표 기록 그대로를 후보로 쓴다.
  function archiveRows(key,priority){const rows=priority?.units?.[key];return rows?.length?rows.map(r=>r.groups):null;}
  function archiveMet(journey,spec,rows){
    const main=spec.journey.indexOf(Math.max(...spec.journey)),first=rows?rows.map(g=>g[0]):[[main]];
    return first.some(group=>group.some(i=>(journey?.[i]||0)>=THRESHOLD_POLICY.archiveMain));
  }
  function archiveCandidates(journey,spec,rows){
    if(!rows)return [clone(spec.journey)];
    const values=[...spec.journey].sort((a,b)=>b-a),seen=new Set(),out=[];
    for(const groups of rows){
      const order=groups.flatMap(group=>group.slice().sort((a,b)=>(journey?.[b]||0)-(journey?.[a]||0)||a-b)),record=Array(5).fill(0);
      order.forEach((slot,i)=>{record[slot]=values[i];});
      const id=record.join(',');if(!seen.has(id)){seen.add(id);out.push(record);}
    }
    return out;
  }
  function growthFields(old,info,growth,spec,content,slots,rows=null){
    const fields=[],level=Stats.level_info(old,info);
    const fixed=Stats.rule_for_content(content)==='fixed200';
    if(!fixed&&level.source!=='legacy'&&!info.star_link?.source?.includes(old.id)
      &&info.star_link.level-level.level>=THRESHOLD_POLICY.linkGap)fields.push('level');
    const equip=old.equip||[],parts=new Set(equip.map(e=>slots?.[e.item_id]));
    if([0,1,2,3,4,5].some(i=>!parts.has(i))||equip.some(e=>e.enhance<THRESHOLD_POLICY.equipMin)
      ||equip.reduce((sum,e)=>sum+e.enhance,0)<THRESHOLD_POLICY.equipSum)fields.push('equip');
    if(['basic','special','ultimate'].some(k=>(old.skills?.[k]||0)<=THRESHOLD_POLICY.skillMax))fields.push('skills');
    if(!fixed)fields.push('resonance');
    // 스텔라 아카이브: 주력 미충족(archiveMet)이면 «기록 다시 만들기»를 후보로 올린다. 채택 여부는 overwrite 가 지금 기록과 비교해 정한다
    if(!old.gauntlet||!archiveMet(old.gauntlet.journey,spec,rows))fields.push('journey');
    if(!(old.gauntlet?.potentials||[]).some(p=>growth.assumed.special_ids.includes(p[0])&&p[1]>0))fields.push('potentials');
    if(old.favor<=THRESHOLD_POLICY.favorMax)fields.push('favor');
    return fields;
  }
  function overwrite(info, roster, growth, content, {excluded=[], slots=itemSlots, priority=null}={}) {
    const target=clone(info), changes={}, errors=[], banned=new Set(excluded);
    let out=profile(info,roster,growth,content);
    for(const s of roster){
      if(banned.has(s.key)||!out.units[s.key])continue;
      try{
        const old=out.units[s.key],spec=growth.assumed.units[s.key];
        if(!spec)throw Error('가정 세팅 없음: '+s.key);
        const rows=archiveRows(s.key,priority),fields=growthFields(old,info,growth,spec,content,slots,rows);
        const a=assume(s.key,info,growth,{fields}),u=a.unit;
        if(fields.includes('skills'))u.skills={...old.skills,
          ...Object.fromEntries(['basic','special','ultimate'].map(k=>[k,(old.skills[k]||0)<=THRESHOLD_POLICY.skillMax?Math.max(old.skills[k]||0,THRESHOLD_POLICY.skillTarget):old.skills[k]]))};
        if(fields.includes('resonance'))u.resonance=Math.max(old.resonance,Math.min(THRESHOLD_POLICY.resonanceMax,u.resonance));
        if(fields.includes('favor'))u.favor=THRESHOLD_POLICY.favorTarget;
        if(fields.includes('potentials'))u.gauntlet.potentials.at(-1)[1]=THRESHOLD_POLICY.potentialTarget;
        if(fields.includes('equip')||fields.includes('journey')){
          // 장비 묶음(지금 것 / 기준표 것)과 아카이브 기록(지금 것 / 다시 만든 후보)은 «통째로» 고른다 — 서로 섞지 않는다(스탯·옵션을 합치지 않음).
          // 다른 육성값(레벨·스킬·공명·호감도·잠재력)을 먼저 정한 뒤 모든 조합의 전투력을 비교해 가장 높은 조합 하나를 쓴다.
          // 한 축을 먼저 정해 버리면(예: 기준표 장비로 기록을 고른 뒤 장비를 되돌림) «지금 장비 + 지금 기록»보다 약한 조합이 남을 수 있다(11/14 리뷰).
          // 지금 것을 먼저 놓고 «더 클 때만» 바꾸므로 같으면 지금 것을 유지하고, 결과가 지금 장비·지금 기록보다 약해지는 일은 없다.
          const rule=Stats.rule_for_content(content);
          const equips=fields.includes('equip')?[old.equip,u.equip]:[u.equip];
          const records=!fields.includes('journey')?[null]:[...(old.gauntlet?.journey?[old.gauntlet.journey]:[]),...archiveCandidates(old.gauntlet?.journey,spec,rows)];
          let best=null;
          for(const equip of equips)for(const record of records){
            const unit=record?{...u,equip,gauntlet:{...u.gauntlet,journey:record}}:{...u,equip};
            const power=Stats.final_stats(unit,a.targetInfo,growth,rule).power;
            if(!best||power>best.power)best={power,equip,record};
          }
          u.equip=clone(best.equip);if(best.record)u.gauntlet.journey=clone(best.record);
        }
        const value=(x,f)=>['journey','potentials'].includes(f)?x.gauntlet?.[f]:x[f];
        for(const f of Object.keys(a.changes))if(f!=='level')a.changes[f]={before:old?value(old,f):null,after:value(u,f)};
        const comparable=(f,v)=>f==='equip'?equipmentValue(v,slots):f==='skills'?Object.entries(v||{}).sort(([a],[b])=>a.localeCompare(b)):v;
        a.changedFields=Object.keys(a.changes).filter(f=>!old||JSON.stringify(comparable(f,a.changes[f].before))!==JSON.stringify(comparable(f,a.changes[f].after)));
        a.overwrite=true;
        if(!a.changedFields.length)continue;
        out=assumedProfile(out,a,info,growth,content);
        const i=target.units.findIndex(x=>x.id===u.id);if(i<0)target.units.push(u);else target.units[i]=u;
        if(a.levelTarget!=null){target.star_link ||= clone(a.targetInfo.star_link);
          target.star_link.slots=target.star_link.slots.filter(x=>x.id!==u.id).concat({index:-1,id:u.id});}
        changes[s.key]=a;
      }catch(e){errors.push({key:s.key,reason:e.message});}
    }
    return {info:target,profile:out,changes,errors,version:OVERWRITE_VERSION,preset:growth.assumed.version};
  }
  const api = {hash, profile, team, judgment, assume, assumedProfile, overwrite, OVERWRITE_VERSION, THRESHOLD_POLICY};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MyInfoReco = api;
})(typeof window !== "undefined" ? window : globalThis);
