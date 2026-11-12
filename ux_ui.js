// Presentation only: probability labels, accessible help, and isolated power comparisons.
(function(root){
  'use strict';
  const U=typeof module!=='undefined'&&module.exports?require('./ui_shared'):root.UiShared;
  const S=typeof module!=='undefined'&&module.exports?require('./myinfo_stats'):root.MyInfoStats;
  const esc=U.esc, num=v=>Number.isFinite(v)?Math.round(v).toLocaleString('ko-KR'):'—';
  const labels={level:'스타링크',equip:'장비',skills:'스킬',resonance:'공명',journey:'스텔라 아카이브',potentials:'잠재력',favor:'호감도'};
  const names=['힘','체력','인내','집중','보호'];
  const skillNames={basic:'기본',special:'특수',ultimate:'궁'};
  const clone=x=>JSON.parse(JSON.stringify(x));
  function verdict(p){return p>=.9?['safe','안정적']:p>=.7?['ok','깰 수 있어요']:p>=.5?['shaky','아슬아슬']:['risk','어려워요'];}
  function help(title,text){return `<button type="button" class="ux-help" data-help="${esc(text)}" aria-label="${esc(title)} 설명" aria-expanded="false">ⓘ</button>`;}
  let grades=null;
  function setGrades(table){grades=table;}
  function grade(value,index,table=grades){const rows=table?.stats?.[index];if(!Number.isFinite(value)||!rows||value>1500)return '';return rows.reduce((g,r)=>value>=r[0]?r[1]:g,'');}
  function archive(value,index,table){const g=grade(value,index,table);return (g?g+' ':'')+num(value);}
  function chip(p){const [state,label]=verdict(p);return `<span class="verdict-chip g-${state}" data-verdict="${state}">${label}</span>`;}
  const signed=v=>v==null?'자료 없음':(v>=0?'+':'−')+num(Math.abs(v));
  function member(a,info,growth,content,table,view={}){
    const old=info.units.find(u=>u.id===a.unit.id),rule=S.rule_for_content(content),before=old?S.final_stats(old,info,growth,rule).power:0;
    if(!old)return null;
    const after=S.final_stats(a.unit,a.targetInfo||info,growth,rule).power;
    const fields=a.changedFields.filter(f=>rule!=='fixed200'||!['level','resonance'].includes(f)).map(f=>{
      // A missing unit has no account baseline. Do not invent its starting power.
      let delta=null;
      if(old){const unit=clone(old);let account=info;
        if(f==='level')account=a.targetInfo||info;
        else if(f==='journey'||f==='potentials'){unit.gauntlet||={};unit.gauntlet[f]=clone(a.unit.gauntlet[f]);}
        else unit[f]=clone(a.unit[f]);
        delta=S.final_stats(unit,account,growth,rule).power-before;
      }
      const c=a.changes[f]||{},b=c.before,t=c.after;let short='',detail='';
      if(f==='level')short=`Lv ${num(b)}→${num(t)}`;
      if(f==='resonance'||f==='favor')short=`${num(b??0)}→${num(t)}`;
      if(f==='skills'){
        const changed=Object.keys(skillNames).filter(k=>t?.[k]>(b?.[k]||0));
        const line=k=>`${skillNames[k]||k} ${b?.[k]||0}→${t?.[k]??b?.[k]??0}`;
        detail=Object.keys(skillNames).map(line).join('\n');
        short=changed.length<=2?changed.map(line).join(' · '):`${changed.length}종`;
      }
      if(f==='equip'){
        const levels=(b||[]).map(e=>e.enhance||0);short=(levels.length?'+'+Math.min(...levels):'없음')+'→+15';
        short+=' · '+[...new Set((t||[]).map(e=>view.sets?.[growth.item_sets?.[e.item_id]]).filter(Boolean))].join('·');
        detail='세트: '+[...new Set((t||[]).map(e=>view.sets?.[growth.item_sets?.[e.item_id]]).filter(Boolean))].join('·')+'\n'+(t||[]).map(e=>{const slot=view.itemSlots?.[e.item_id],prev=(b||[]).find(x=>view.itemSlots?.[x.item_id]===slot);
          return `${['무기','장갑','갑옷','신발','목걸이','반지'][slot]||'장비'} ${prev?'+'+(prev.enhance||0):'없음'}→+${e.enhance} · ${view.sets?.[growth.item_sets?.[e.item_id]]||'세트 정보 없음'}`;}).join('\n');
      }
      if(f==='journey'){
        const ix=(t||[]).map((v,i)=>i).filter(i=>t[i]>(b?.[i]||0));
        const main=ix.slice().sort((i,j)=>t[j]-t[i])[0];
        short=main==null?'':`${names[main]} ${grade(b?.[main]||0,main,table)||num(b?.[main]||0)}→${grade(t[main],main,table)||num(t[main])}${t[main]===1250?' (MAX)':''}${ix.length>1?' · 외 '+(ix.length-1)+'항목':''}`;
        detail=ix.map(i=>`${names[i]} ${archive(b?.[i]||0,i,table)} → ${archive(t[i],i,table)}${t[i]===1250?' (MAX)':''}`).join('\n');
      }
      if(f==='potentials'){
        const changes=(t||[]).filter(p=>!(b||[]).some(q=>q[0]===p[0]&&q[1]>=p[1]));
        short=changes.map(p=>`${view.potentials?.[p[0]]?.name||''} ${(b||[]).find(q=>q[0]===p[0])?.[1]||'미습득'}→${p[1]}`).join(' · ');
        detail=changes.map(p=>`${view.potentials?.[p[0]]?.name||'잠재력 '+p[0]} ${(b||[]).find(q=>q[0]===p[0])?.[1]||'미습득'} → ${p[1]}`).join('\n');
      }
      return {field:f,label:labels[f],short,detail:detail||short,delta};
    });
    return {before,after,fields,missing:!old};
  }
  function todosHtml(m){return (m?.fields||[]).filter(f=>f.delta!==0).map(f=>`<button type="button" class="growth-todo" data-growth-field="${f.field}" data-power-delta="${f.delta??''}" data-help="${esc(f.detail+'\n전투력 '+signed(f.delta)+' · 이 항목만 목표로 올렸을 때의 증가예요.')}" aria-expanded="false">${esc(f.label)} ${esc(f.short)} <small>(${signed(f.delta)})</small></button>`).join('');}
  function memberHtml(m,withTodos=true){if(!m)return '';return `<div class="growth-power" data-k="member-power">전투력 ${num(m.before)} → ${num(m.after)}</div>`+(withTodos?`<div class="growth-todos">${todosHtml(m)}</div>`:'');}
  function resultTabState({enabled,phase,better,baseline,best,kind='op',message='',errors=[]}){
    const probability=kind==='op'||kind==='clo',field=kind==='guild'?'score':'sum';
    const metric=r=>probability?(Number.isFinite(r?.clear)?Math.round(r.clear*100)+'%':'계산 전'):
      (Number.isFinite(r?.[field])?num(r[field])+'점':'계산 전');
    return {show:!!enabled&&(phase==='running'||phase==='error'||phase==='done'&&!!better),
      now:(probability?'클리어 ':'점수 ')+metric(baseline),
      growth:phase==='running'?'계산 중'+(message?' · '+message:''):phase==='error'?'미완료'+(errors.length?' · 실패':''):'맞추면 '+metric(best)+' ↑',
      recommend:Number.isFinite(baseline?.clear)&&baseline.clear<.5,phase};
  }
  // The choice lives only in this controller. Never persist it or add it to share state.
  function createResultTabs(){
    const doc=root.document;
    let selected='now',nav=null,panels=[];
    function release(){for(const p of panels){p.classList.remove('ux-tab-hidden');p.removeAttribute('role');p.removeAttribute('aria-labelledby');p.removeAttribute('tabindex');}panels=[];}
    function reset(){release();nav?.remove();nav=null;selected='now';}
    function select(key){selected=key;
      panels.forEach((p,i)=>p.classList.toggle('ux-tab-hidden',(i===0?'now':'growth')!==selected));
      nav.querySelectorAll('[role=tab]').forEach(b=>{const active=b.dataset.resultTab===selected;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
    }
    function update(now,growth,state){
      if(!state.show||!now||!growth){reset();return;}
      if(!nav){nav=doc.createElement('div');nav.id='result-tabs';nav.className='result-tabs';nav.setAttribute('role','tablist');nav.setAttribute('aria-label','추천 결과');
        nav.innerHTML=['now','growth'].map((key,i)=>`<button type="button" role="tab" id="result-tab-${key}" data-result-tab="${key}"><span class="result-tab-title">${i?'클리어 추천 육성':'지금 내 구원자로'}</span><span class="result-tab-sep"> · </span><span data-tab-metric></span>${i?'<span class="result-recommend" hidden>추천</span>':''}</button>`).join('');
        nav.addEventListener('click',e=>{const b=e.target.closest('[role=tab]');if(b)select(b.dataset.resultTab);});
        nav.addEventListener('keydown',e=>{const b=e.target.closest('[role=tab]');if(!b||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
          e.preventDefault();const buttons=[...nav.querySelectorAll('[role=tab]')],next=e.key==='Home'?buttons[0]:e.key==='End'?buttons[1]:buttons[1-buttons.indexOf(b)];
          buttons.forEach(x=>x.tabIndex=x===next?0:-1);next.focus();});
      }
      release();panels=[now,growth];now.id||='result-now';if(nav.nextSibling!==now)now.before(nav);
      panels.forEach((p,i)=>{const key=i?'growth':'now',b=nav.querySelector(`[data-result-tab=${key}]`);
        p.setAttribute('role','tabpanel');p.setAttribute('aria-labelledby',b.id);p.tabIndex=0;b.setAttribute('aria-controls',p.id);
        b.querySelector('[data-tab-metric]').textContent=state[key];});
      nav.querySelector('.result-recommend').hidden=!state.recommend;
      const b=nav.querySelector('[data-result-tab=growth]');b.dataset.state=state.phase;
      b.querySelector('[data-tab-metric]').setAttribute('role','status');
      select(selected);
    }
    return {update,reset};
  }
  function mount(){
    const doc=root.document;if(!doc)return;
    const pop=doc.createElement('div');pop.id='ux-popover';pop.className='ux-popover';pop.role='tooltip';pop.hidden=true;doc.body.append(pop);
    let owner=null,pinned=false,timer;
    function close(){clearTimeout(timer);if(owner){owner.setAttribute('aria-expanded','false');owner.removeAttribute('aria-describedby');}owner=null;pinned=false;pop.hidden=true;}
    function place(){if(!owner?.isConnected){close();return;}const r=owner.getBoundingClientRect(),vw=doc.documentElement.clientWidth,vh=root.innerHeight;
      pop.style.left=Math.max(8,Math.min(r.left,vw-pop.offsetWidth-8))+'px';
      pop.style.top=Math.max(8,Math.min(r.bottom+8,vh-pop.offsetHeight-8))+'px';}
    function show(b,pin=false){clearTimeout(timer);if(owner!==b)close();owner=b;pinned=pin;pop.textContent=b.dataset.help;pop.hidden=false;b.setAttribute('aria-expanded','true');b.setAttribute('aria-describedby',pop.id);place();}
    doc.addEventListener('click',e=>{const b=e.target.closest('[data-help]');if(b){e.preventDefault();e.stopPropagation();if(owner===b&&pinned)close();else show(b,true);}else if(!pop.contains(e.target))close();});
    doc.addEventListener('pointerover',e=>{const b=e.target.closest('[data-help]');if(e.pointerType==='mouse'&&b&&!pinned)show(b);if(pop.contains(e.target))clearTimeout(timer);});
    doc.addEventListener('pointerout',e=>{if(!pinned&&(e.target.closest('[data-help]')||pop.contains(e.target)))timer=setTimeout(close,150);});
    doc.addEventListener('keydown',e=>{if(e.key==='Escape'){const b=owner;close();b?.focus();doc.querySelectorAll('.ux-menu[open]').forEach(d=>d.open=false);}});
    doc.addEventListener('focusout',e=>{if(owner===e.target&&!pinned)close();});
    root.addEventListener('resize',()=>{if(owner)place();});root.addEventListener('scroll',()=>{if(owner)place();},true);
  }
  const api={verdict,help,grade,archive,setGrades,chip,signed,num,labels,member,todosHtml,memberHtml,resultTabState,createResultTabs,mount};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.Ux=api;
})(typeof globalThis!=='undefined'?globalThis:this);
