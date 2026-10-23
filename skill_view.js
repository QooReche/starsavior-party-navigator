/* Public databook presentation rules. No combat/simulation dependencies. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.SkillView=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const slots={'기본기':'basic','특수기':'special','궁극기':'ultimate','고유 패시브':'passive'};
  function normalize(s){
    return {...s,slot:slots[s.sl.replace(/^변형 /,'')]||'passive',mx:Math.max(1,Number(s.mx)||1),
      d1:s.d1||'',dx:s.dx||s.d1||'',
      lv:(s.lv||[]).map(x=>[Number(x[0]),String(x[1])]).sort((a,b)=>a[0]-b[0]),
      gl:(s.gl||[]).map(g=>Array.isArray(g)?g.slice(0,3):[g.n||'',g.k||'',g.d||''])};
  }
  function cooldown(s,level){
    if(s.cd==null)return null;
    const base=Number(s.cd),max=s.cdm==null?base:Number(s.cdm);
    if(level>=s.mx)return max;
    const reductions=s.lv.flatMap(([lv,text])=>{
      const m=text.match(/쿨타임\s*(?:(\d+)\s*턴\s*)?감소(?:\s*(\d+)\s*턴)?/);
      return m?[[lv,Number(m[1]||m[2]||1)]]:[];
    });
    if(!reductions.length)return level>=Math.min(6,s.mx)?max:base;
    return Math.max(max,base-reductions.reduce((n,[lv,amount])=>n+(level>=lv?amount:0),0));
  }
  function select(raw,skills){
    const s=normalize(raw),own=skills!=null;
    const value=own?Number(skills[s.slot]??1):s.mx;
    const level=Math.min(s.mx,Math.max(0,Number.isFinite(value)?Math.floor(value):1));
    return {...s,own,level,cooldown:cooldown(s,level),description:level===s.mx?s.dx:s.d1,
      next:s.lv.find(([lv])=>lv>level)||null};
  }
  const {esc} = typeof module !== 'undefined' && module.exports ? require('./ui_shared.js') : globalThis.UiShared;
  function terms(text,gl){
    return String(text).split(/(\[[^\]]+\])/g).map(part=>{
      const g=gl.find(([name])=>part===`[${name}]`);
      if(!g)return esc(part);
      const explanation=[g[1],g[2]].filter(Boolean).join(' · ');
      return `<span class="skill-term-wrap"><button type="button" class="skill-term" aria-expanded="false" title="${esc(explanation)}">${esc(part)}</button><span class="skill-tip" hidden>${esc(explanation)}</span></span>`;
    }).join('');
  }
  function skillCard(raw,skills,variants=[],uid=null){
    const s=select(raw,skills);
    return `<section class="${s.sl.startsWith('변형 ')?'skill-variant':'skill-card'}" data-slot="${s.slot}" data-level="${s.level}">
      <div class="skill-heading"><span class="skill-badge ${s.slot}">${(globalThis.UiShared&&globalThis.UiShared.icon)?(uid!=null&&globalThis.UiShared.skillIcon?globalThis.UiShared.skillIcon(uid,s.slot):globalThis.UiShared.icon(s.slot)):''}${esc(s.sl)}</span><span class="skill-level">${s.own?'내 레벨':'최대 레벨'} ${s.level} / ${s.mx}</span></div>
      <h3>${esc(s.n)}</h3><div class="skill-meta">${esc([s.tg,s.ty].filter(Boolean).join(' · '))}${s.cooldown==null?'':` · 쿨 ${s.cooldown}턴`}${s.level===0?' · 미습득':''}</div>
      <p class="skill-description">${terms(s.description,s.gl)}</p>
      ${s.next?`<p class="skill-next">다음 강화: Lv${s.next[0]} ${terms(s.next[1],s.gl)}</p>`:''}
      <details class="skill-upgrades"><summary>레벨 강화</summary><ul>${s.lv.map(([lv,t])=>`<li class="${lv<=s.level?'achieved':'unlearned'}"><span aria-label="${lv<=s.level?'달성':'미달성'}">${lv<=s.level?'✓':'○'}</span> Lv${lv} ${terms(t,s.gl)}</li>`).join('')}</ul></details>
      ${variants.length?`<details class="skill-variants"><summary>변형 스킬</summary>${variants.map(v=>skillCard(v,skills)).join('')}</details>`:''}
    </section>`;
  }
  function render(rows,skills,uid=null){
    if(!rows?.length)return '<p class="mut">공개 스킬 정보 없음</p>';
    const variants=rows.filter(s=>s.sl.startsWith('변형 '));
    return `<div class="skill-grid">${rows.filter(s=>!s.sl.startsWith('변형 ')).map(s=>skillCard(s,skills,variants.filter(v=>normalize(v).slot===normalize(s).slot),uid)).join('')}</div>`;
  }
  function mount({url,getUnit,getSavior}){
    const opened=new Set(),rendered=new WeakMap(),dialog=document.getElementById('skills-dialog'),body=document.getElementById('skills-body');
    let data,pending,modalKey=null,opener=null;
    function load(){
      if(data)return Promise.resolve(data);
      if(!pending)pending=fetch(url).then(r=>{if(!r.ok)throw new Error(r.status);return r.json()}).then(d=>data=d).finally(()=>{pending=null});
      return pending;
    }
    async function fill(target,uid){
      const signature=JSON.stringify([String(uid),getUnit(uid)?.skills]);
      // Background recommendation refreshes must not close a glossary/upgrade fold.
      if(rendered.get(target)===signature)return;
      rendered.delete(target);
      target.dataset.uid=String(uid);
      target.innerHTML='<p class="mut" role="status">불러오는 중…</p>';
      try{
        const all=await load();
        if(target.isConnected&&target.dataset.uid===String(uid)){
          target.innerHTML=render(all[uid],getUnit(uid)?.skills,uid);
          rendered.set(target,JSON.stringify([String(uid),getUnit(uid)?.skills]));
        }
      }catch(e){
        if(target.isConnected&&target.dataset.uid===String(uid))target.innerHTML='<p role="status">스킬을 불러오지 못했습니다. <button type="button" class="sec" data-skill-retry>다시 시도</button></p>';
      }
    }
    function fold(uid){
      const open=opened.has(String(uid));
      return `<div class="mi-skills"><button type="button" class="sec" data-skill-fold="${uid}" aria-expanded="${open}" aria-controls="mi-skills-${uid}">스킬 <span aria-hidden="true">${open?'▴':'▾'}</span></button><div id="mi-skills-${uid}" class="skill-content"${open?'':' hidden'}></div></div>`;
    }
    function refresh(){
      for(const uid of opened){const target=document.getElementById(`mi-skills-${uid}`);if(target)fill(target,uid)}
      for(const button of document.querySelectorAll('[data-skill-open]'))button.setAttribute('aria-expanded',String(dialog.open&&button.dataset.skillOpen===modalKey));
      if(dialog.open&&modalKey)fill(body,getSavior(modalKey).uid);
    }
    document.addEventListener('click',e=>{
      const button=e.target.closest('button');if(!button)return;
      if(button.hasAttribute('data-skill-fold')){
        const uid=button.dataset.skillFold,target=document.getElementById(button.getAttribute('aria-controls')),open=target.hidden;
        target.hidden=!open;button.setAttribute('aria-expanded',String(open));button.querySelector('span').textContent=open?'▴':'▾';
        if(open){opened.add(uid);fill(target,uid)}else opened.delete(uid);
      }else if(button.hasAttribute('data-skill-open')){
        const s=getSavior(button.dataset.skillOpen);if(!s)return;
        modalKey=s.key;opener=button;
        document.getElementById('skills-title').textContent=`${s.name} · 스킬`;
        document.getElementById('skills-subtitle').textContent=s.sub||'';
        dialog.showModal();refresh();
      }else if(button.hasAttribute('data-skill-close'))dialog.close();
      else if(button.hasAttribute('data-skill-retry')){const target=button.parentElement.parentElement;fill(target,target.dataset.uid)}
      else if(button.classList.contains('skill-term')){
        const tip=button.nextElementSibling;tip.hidden=!tip.hidden;button.setAttribute('aria-expanded',String(!tip.hidden));
      }
    });
    dialog.addEventListener('close',()=>{
      const key=modalKey;modalKey=null;body.dataset.uid='';body.innerHTML='';rendered.delete(body);
      for(const button of document.querySelectorAll('[data-skill-open]')){
        button.setAttribute('aria-expanded','false');
        if(!opener?.isConnected&&button.dataset.skillOpen===key)opener=button;
      }
      opener?.focus();
    });
    return {fold,refresh};
  }
  return {normalize,cooldown,select,render,mount};
});
