// Imported account viewer. Text comes only from public data/myinfo_view.json.
(function(root){
  'use strict';
  const Stats=typeof module!=='undefined'&&module.exports?require('./myinfo_stats.js'):root.MyInfoStats;
  const names={atk:'공격력',hp:'생명력',def:'방어력',spd:'속도',cr:'치명타 확률',cd:'치명타 피해',eh:'효과 적중',er:'효과 저항',atkP:'공격력 비율',hpP:'생명력 비율',defP:'방어력 비율',spdP:'속도 비율'};
  const {NST:nst} = typeof module !== 'undefined' && module.exports ? require('./ui_shared.js') : root.UiShared;
  const groups={TG_COMMON:'공통',TG_SAVIOR:'구원자',TG_ARCANA:'아르카나',TG_SUN:'태양',TG_MOON:'달',TG_STAR:'별',TG_ORDER:'질서',TG_CHAOS:'혼돈',TG_DEFENDER:'디펜더',TG_STRIKER:'스트라이커',TG_RANGER:'레인저',TG_CASTER:'캐스터',TG_ASSASSIN:'어쌔신',TG_SUPPORTER:'서포터'};
  const labels={base:'기본',level:'레벨·스타링크',equipment_main:'장비 주옵',equipment_sub:'장비 부옵',equipment_set:'장비 세트',favor:'호감도',tactics:'전술 분석',facility:'시설',journey:'여정',potential:'잠재력',resonance:'공명',sigil:'각인',passive:'고유 패시브',bundle:'묶음 비율 효과',rounding:'버림·하한 보정'};
  const order=Object.keys(labels),keys=Object.keys(names).slice(0,8);
  const {esc} = typeof module !== 'undefined' && module.exports ? require('./ui_shared.js') : globalThis.UiShared;
  const num=v=>Number.isFinite(v)?v.toLocaleString('ko-KR',{maximumFractionDigits:8}):'—';
  const rate=k=>['cr','cd','eh','er'].includes(k)||k.endsWith('P');
  const value=(k,v)=>Number.isFinite(v)?num(rate(k)?v/100:v)+(rate(k)?'%':''):'—';
  const values=v=>Object.entries(v||{}).filter(([,n])=>n!==0).map(([k,n])=>`${names[k]||esc(k)} +${value(k,n)}`).join(' · ')||'추가 없음';
  const line=(a,b)=>`<div class="mi-detail-line"><span>${a}</span><b>${b}</b></div>`;
  const section=(title,html)=>`<section class="skill-card"><h3>${title}</h3>${html}</section>`;
  const level=v=>Number.isFinite(v)?num(v):'—';
  function at(table,lv){const n=Object.keys(table||{}).map(Number).filter(n=>n<=lv).sort((a,b)=>b-a)[0];return table?.[n]||{}}
  function account(info,growth){
    const t=info.tactics||{},gs=t.groups||{};
    return section('계정 내실',line('공통',`Lv${level(t.common_level)} · ${values(at(growth.tactics?.TG_COMMON?.MAIN,t.common_level))}`)+line('시설',`Lv${level(t.facility_level)} · ${values(at(growth.facility,t.facility_level))}`)+
      `<table class="mi-group-table"><caption>전술 분석 그룹별 레벨</caption><thead><tr><th scope="col">그룹</th><th scope="col">레벨</th><th scope="col">공</th><th scope="col">방</th><th scope="col">생</th></tr></thead><tbody>${Object.entries(gs).map(([g,v])=>`<tr><th scope="row">${esc(groups[g]||g)}</th>${['level','attack','defense','hp'].map(k=>`<td>${level(v[k])}</td>`).join('')}</tr>`).join('')}</tbody></table>${Object.keys(gs).length?'':'<p class="mut">그룹 정보 없음</p>'}`);
  }
  function breakdown(result){
    const b=result.breakdown;
    if(!Object.keys(b.stats).length)return '<p>성장표에 없는 구원자 · 분해 불가</p>';
    return `<p class="mut mi-formula">기본·레벨·여정 → 공명 비율 R1 → 공명 고정 → 나머지 고정 + R2 → 버림</p><div class="mi-detail-grid">${keys.map(k=>{
      const s=b.stats[k];
      return `<details class="mi-stat-detail"><summary>${names[k]} <b>${value(k,s.final)}</b></summary>${order.map(id=>{
        const raw=b.sources.filter(t=>t.id===id).reduce((n,t)=>n+(t.values[k+'P']||0),0);
        return line(labels[id],`${value(k,s.components[id]||0)}${raw?` <small>비율 ${value(k+'P',raw)} (${id==='base'||id==='resonance'?'R1':'R2'})</small>`:''}`);
      }).join('')}${line('R1 / R2',`${num(s.r1*100)}% / ${num(s.r2*100)}%`)}${line('최종',value(k,s.final))}</details>`;
    }).join('')}</div>`;
  }
  function equipment(unit,growth,publicData){
    const equip=unit.equip||[],slots=publicData.slots||[],assigned=new Map(),unknown=[];
    for(const item of equip){const slot=publicData.itemSlots?.[item.item_id];if(Number.isInteger(slot)&&slot>=0&&slot<6&&!assigned.has(slot))assigned.set(slot,item);else unknown.push(item)}
    const option=o=>o?`${esc(names[nst[o.stat]]||o.stat)} ${nst[o.stat]?value(nst[o.stat],o.value):num(o.value)}`:'정보 없음';
    const card=(item,title)=>`<div class="mi-gear"><b>${esc(title)}${item?` · +${level(item.enhance)}`:''}</b>${item?`<small>#${item.item_id}</small><p>주옵 · ${option(item.main)}</p><p class="mut">부옵 · ${(item.subs||[]).map(option).join(' · ')||'없음'}</p>`:'<p class="mut">'+(unknown.length?'부위 확인 불가':'미장착')+'</p>'}</div>`;
    const counts={};for(const item of equip){const id=growth.item_sets?.[item.item_id];if(id)counts[id]=(counts[id]||0)+1}
    return `<div class="mi-detail-grid">${Array.from({length:6},(_,i)=>card(assigned.get(i),slots[i]||`부위 ${i+1}`)).join('')}${unknown.map(e=>card(e,'부위 미확인')).join('')}</div>`+
      Object.entries(counts).map(([id,n])=>{const e=growth.sets?.[id],times=e?.parts?Math.floor(n/e.parts):0;
        const total=e?Object.fromEntries(Object.entries(e.stats||{}).map(([k,v])=>[k,v*(times||1)])):null;
        return line(`${esc(publicData.sets?.[id]||`세트 #${id}`)} ${n}/${e?.parts||'?'}`,`${times?`완성 ×${times}`:'미완성'} · ${e?values(total):'효과 미해석'}${times?'':' (완성 시)'}`)}).join('');
  }
  function combatEffects(pid,lv,publicData,combat){
    const row=combat.potentials?.[pid]?.[lv],pot=publicData.potentials?.[pid];
    if(!row||!pot)return {known:false,active:false,text:'전투 효과 미해석'};
    const lines=pot.levels?.[lv]||[];
    const effects=(row.lines||[]).map(i=>lines[i]||`효과 #${i}`);
    for(const [k,n] of Object.entries(row.stats||{}))effects.push(`${k==='NST_SUPER_ARMOR'?'강인도':k} +${n}`);
    return {known:true,active:effects.length>0,text:effects.join(' · ')||'추가 전투 효과 없음'};
  }
  function render(unit,info,growth,result,publicData,combat,simulation){
    const b=result.breakdown,gauntlet=unit.gauntlet||{},learned=result.combat.potentials;
    const effects=learned.map(([id,lv])=>combatEffects(id,lv,publicData,combat));
    const status=effects.some(e=>e.active)?'있음':effects.some(e=>!e.known)?'미해석':'없음';
    const chips=[simulation?'시뮬 입력':'참고값 · 현재 시뮬 미적용',...keys.map(k=>`${names[k]} ${value(k,result.stats[k])}`),`전투력 ${num(result.power)}`,...[['basic','기본'],['special','특수'],['ultimate','궁극'],['passive','패시브']].map(([k,n])=>`${n} Lv${level(result.combat.skills[k])}`),`잠재력 전투 효과 ${status}`];
    const seenGroups=new Set();
    const inner=b.sources.filter(s=>['favor','tactics','facility'].includes(s.id)).map(s=>{
      let header='';
      if(s.id==='tactics'&&s.group!=='TG_COMMON'&&!seenGroups.has(s.group)){
        seenGroups.add(s.group);header=`<h4>${esc(groups[s.group]||s.group)} · Lv${level(info.tactics?.groups?.[s.group]?.level)}</h4>`;
      }
      return header+line(`${s.id==='tactics'?esc(groups[s.group]||s.group)+(s.field==='level'?'':` · ${{attack:'공',defense:'방',hp:'생'}[s.field]}`):labels[s.id]} Lv${s.level}`,values(s.values));
    }).join('');
    const journey=['공격','생명','인내','집중','보호'].map((n,i)=>{const raw=gauntlet.journey?.[i];return line(n,`${num(raw)}${raw>1500?' → 1,500 (상한 적용)':''}`)}).join('');
    const potentials=learned.map(([id,lv],i)=>`<li><b>${esc(publicData.potentials?.[id]?.name||`잠재력 #${id}`)} · Lv${lv}</b><small>#${id}</small><p>${growth.potentials?.[id]?.[lv]?values(growth.potentials[id][lv]):'능력치 미해석'}</p>${effects[i].active?`<details><summary>시뮬 전투 효과</summary><p class="mut">${esc(effects[i].text)}</p></details>`:`<p class="mut">${esc(effects[i].text)}</p>`}</li>`).join('');
    return `<div class="mi-sim-chips" aria-label="시뮬 반영 값">${chips.map(c=>`<span class="tag">${esc(c)}</span>`).join('')}</div>`+
      section('능력치 출처',breakdown(result))+section('내실',inner||'정보 없음')+section('장비',equipment(unit,growth,publicData))+
      section(`건틀렛 Lv${level(gauntlet.level)}`,`<p class="mut">여정 · 각 항목 상한 1,500</p>${journey}<ul class="mi-potentials">${potentials||'<li>습득 잠재력 없음</li>'}</ul>${line('축복 · 미해석',esc((gauntlet.blessings||[]).map(id=>`#${id}`).join(' · ')||'없음'))}`)+
      (result.missing.length?`<details class="mi-diagnostics"><summary>미확인 정보 ${result.missing.length}</summary><p>${result.missing.map(esc).join(' · ')}</p></details>`:'');
  }
  function mount(getContext){
    const opened=new Set(),cache=new Map();let contextKey=null,publicData,combat,pending;
    function sync(){const c=getContext();const key=[c.info,c.growth,c.rule,c.simulation];if(!contextKey||key.some((v,i)=>v!==contextKey[i])){cache.clear();contextKey=key}if(!c.info)opened.clear();return c}
    function load(){if(publicData&&combat)return Promise.resolve();if(!pending)pending=Promise.all(['data/myinfo_view.json','data/myinfo_combat.json','data/myinfo_slots.json'].map(url=>fetch(url).then(r=>{if(!r.ok)throw new Error(r.status);return r.json()}))).then(([p,c,s])=>{publicData={...p,itemSlots:s};combat=c}).finally(()=>pending=null);return pending}
    function button(uid){sync();const open=opened.has(String(uid));return `<button type="button" class="sec" data-mi-detail="${uid}" aria-expanded="${open}" aria-controls="mi-detail-${uid}">${uid==='account'?'계정 내실':'상세'} <span aria-hidden="true">${open?'▴':'▾'}</span></button>`}
    function panel(uid){return `<div id="mi-detail-${uid}" class="mi-detail-content"${opened.has(String(uid))?'':' hidden'}></div>`}
    async function fill(uid){
      const c=sync(),target=document.getElementById(`mi-detail-${uid}`);if(!target||!c.info)return;
      if(cache.has(uid)){target.replaceChildren(cache.get(uid));return}
      if(!c.growth){target.textContent='성장표를 불러온 뒤 다시 펼쳐 주세요.';return}
      target.innerHTML='<p role="status">불러오는 중…</p>';
      try{
        if(uid!=='account')await load();
        const now=getContext();if(!target.isConnected||c.info!==now.info||c.growth!==now.growth||c.rule!==now.rule||c.simulation!==now.simulation)return;
        // Another refresh may already have filled this uid while fetch was pending.
        if(cache.has(uid)){target.replaceChildren(cache.get(uid));return}
        const node=document.createElement('div');
        if(uid==='account')node.innerHTML=account(c.info,c.growth);
        else {const unit=c.info.units.find(u=>String(u.id)===uid);if(!unit)return;
          const r=Stats.final_stats(unit,c.info,c.growth,c.rule||'normal',true);
          node.innerHTML=render(unit,c.info,c.growth,r,publicData,combat,c.simulation&&!!c.growth.units?.[unit.id]&&r.power>0);
        }
        cache.set(uid,node);target.replaceChildren(node);
      }catch(e){if(target.isConnected)target.innerHTML=`<p role="status">상세를 불러오지 못했습니다. <button type="button" class="sec" data-mi-retry="${uid}">다시 시도</button></p>`}
    }
    function refresh(){sync();for(const uid of opened)fill(uid)}
    document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
      if(b.hasAttribute('data-mi-retry')){fill(b.dataset.miRetry);return}
      if(!b.hasAttribute('data-mi-detail'))return;
      const uid=b.dataset.miDetail,target=document.getElementById(b.getAttribute('aria-controls')),open=target.hidden;
      target.hidden=!open;b.setAttribute('aria-expanded',String(open));b.querySelector('span').textContent=open?'▴':'▾';
      if(open){opened.add(uid);fill(uid)}else opened.delete(uid);
    });
    return {button,panel,refresh};
  }
  const api={names,groups,value,account,breakdown,equipment,combatEffects,render,mount};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MyInfoView=api;
})(typeof window!=='undefined'?window:globalThis);
