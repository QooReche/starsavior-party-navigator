// 코스모 게이트 직접 편성(3파티) 화면 부품. 상태는 갖지 않고 view 를 그대로 그림 — 바꾸는 일은 전부 콜백(h)으로 넘김.
// 기존 직접 편성(direct_ui.js)과 같은 문서에 있어도 부딪히지 않게 id 는 cd- 접두, data-direct-* 속성은 쓰지 않음.
// 팀 draft 는 DirectParty 형식 그대로: slots 는 엔진 순서(전열1·전열2·후열1·후열2), 화면에는 후열1·전열1·전열2·후열2 로 놓음.
(function(root){
  'use strict';
  const node=typeof module!=='undefined'&&module.exports;
  const EL={sun:'태양',moon:'달',star:'별',order:'질서',chaos:'혼돈'};
  const ROLE={스트라이커:'striker',레인저:'ranger',캐스터:'caster',디펜더:'defender',서포터:'supporter',어쌔신:'assassin'};
  const CROWN='<svg viewBox="0 0 34 26" aria-hidden="true"><path d="M2 22 L5 6 L12 14 L17 3 L22 14 L29 6 L32 22 Z" fill="#ffd24a" stroke="#8a5a00" stroke-width="1.5" stroke-linejoin="round"/><rect x="2" y="22" width="30" height="3" rx="1" fill="#e6a800"/></svg>';
  const SCREEN=[2,0,1,3],LABELS=['전열1','전열2','후열1','후열2'];
  const STEPS=[['보스 고르기','보스'],['구원자 4명 넣기','구원자 4명'],['브레이크·난이도(선택)','브레이크(선택)'],['확인','확인']];
  const GROW_HELP='체크하면 이 구원자를 더 키웠다고 치고 계산';
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const num=n=>Math.round(n).toLocaleString('ko-KR');
  const pct=x=>Math.round(x*100);
  // 줄인 보스 이름(좁은 화면·이유 문구). season 에 short 가 있으면 그것, 없으면 «○○의 △△» → ○○, 그 밖엔 마지막 낱말.
  const shortOf=b=>b.short||(/^(.+?)의\s/.exec(b.name)||[])[1]||b.name.split(/\s+/).pop();
  const emptyDraft=()=>({v:1,slots:[null,null,null,null],leader:null,brk:null});
  const powerText=p=>p==null?'—':p>=1000?(p/1000).toFixed(1)+'k':num(p);

  // view 를 읽기 쉬운 모양으로 한 번 정리. usedBy 는 Map·객체 둘 다 받음.
  function read(view){
    const bosses=view.season.bosses,state=view.state,levelMax=view.season.levelMax??18;
    const active=bosses.some(b=>b.key===state.active)?state.active:bosses[0].key;
    const by=new Map((view.roster||[]).map(s=>[s.key,s]));
    const used=view.usedBy instanceof Map?view.usedBy:new Map(Object.entries(view.usedBy||{}));
    const team=k=>state.teams?.[k]||{level:6,draft:emptyDraft()};
    const draft=k=>team(k).draft||emptyDraft();
    const count=k=>draft(k).slots.filter(Boolean).length;
    const check=k=>view.validation?.teams?.[k]||null;
    const res=k=>view.summary?.teams?.[k]||{status:count(k)?'ready':'empty'};
    const done=k=>res(k).status==='done';
    const total=view.summary?.total??null,doneCount=view.summary?.done??bosses.filter(b=>done(b.key)).length;
    // 실행을 막는 이유(팀별). 4명 미만이면 인원 문구, 4명인데 검증 실패면 그 메시지.
    const blocks=k=>{const n=count(k),c=check(k);
      if(n<4)return [`4명 필요`];
      return c&&!c.ok?[...new Set(c.errors.map(e=>e.message))]:[];};
    const icon=view.icons||{};
    const attr=el=>`<img src="${esc(icon.attr?.[el]||`assets/ui_icons/attr_${el}.webp`)}" alt="">`;
    const dia=(s,px)=>`<span class="dia e-${esc(s.el)}" style="width:${px}px;height:${px}px"><img src="${esc(icon.role?.[s.cls]||`assets/ui_icons/role_${ROLE[s.cls]||'striker'}.webp`)}" alt="${esc(s.cls)}" style="width:${Math.round(px*.66)}px;height:${Math.round(px*.66)}px"></span>`;
    return {view,bosses,state,levelMax,active,boss:bosses.find(b=>b.key===active),by,used,team,draft,count,check,res,done,total,doneCount,blocks,attr,dia,
      short:k=>shortOf(bosses.find(b=>b.key===k)||{name:String(k)})};
  }
  const levels=(max,sel)=>Array.from({length:max+1},(_,i)=>`<option value="${i}"${i===sel?' selected':''}>${i?'레벨 '+i:'레벨 0(없음)'}</option>`).join('');

  function stepsHtml(m){
    const lacking=m.bosses.some(b=>m.count(b.key)<4);
    const cur=m.total!=null?0:[1,2,3,4].includes(m.view.step)?m.view.step:lacking?2:4;
    return STEPS.map(([f,s],i)=>{const n=i+1,done=cur===0||n<cur&&n!==3;
      return `<li${n===cur?' aria-current="step"':''}${done?' class="done"':''}><span>${done?'✓':'①②③④'[i]} <span class="f">${f}</span><span class="s">${s}</span></span></li>`;}).join('');
  }
  // 보스 카드 = 탭: 리더 초상 · 편성 n/4 · 점수(+클리어율)만. 실행 못 하는 이유(4명 필요 등)도 여기 한 낱말로.
  function tabsHtml(m,interactive=true){
    return m.bosses.map(b=>{
      const d=m.draft(b.key),n=m.count(b.key),lead=m.by.get(d.leader),sel=b.key===m.active,r=m.res(b.key),done=m.done(b.key),bad=n===4&&m.blocks(b.key).length>0;
      const clear=r.clear!=null?`클리어 ${pct(r.clear)}%`:'';
      const wait=n===0?'비어 있음 · 눌러서 편성':n<4?'편성 중':'확인 전';
      const need=n<4?'4명 필요':bad?'고칠 곳 있음':'';
      const label=[`${b.name} 팀`,`편성 ${n}/4`,need,lead?'리더 '+lead.name:'',done?`${num(r.score)}점${clear?', '+clear:''}`:n===0?'비어 있음, 눌러서 편성':n<4?'':'확인 전'].filter(Boolean).join(' · ');
      const open=interactive?`<button type="button" role="tab" class="cg-tab" id="cd-tab-${esc(b.key)}" data-cd-boss="${esc(b.key)}" aria-selected="${sel}" aria-controls="cd-panel" tabindex="${sel?0:-1}" aria-label="${esc(label)}">`:`<section class="cg-tab" aria-label="${esc(label)}">`;
      return open
        +`<span class="cg-face" aria-hidden="true">${lead?`<img class="lead" src="${esc(lead.img)}" alt="">${CROWN}`:'<span class="vacant">＋</span>'}</span>`
        +`<span class="cg-head" aria-hidden="true">${m.attr(b.element)}<b><span class="cg-name-full">${esc(b.name)}</span><span class="cg-name-short">${esc(shortOf(b))}</span></b></span>`
        +`<span class="cg-count" aria-hidden="true"><span class="lbl">편성 </span>${n}/4${need?` · <span class="need">${need}</span>`:''}</span>`
        +`<span class="cg-score${done?'':' none'}" aria-hidden="true">${done?`<b>${num(r.score)}</b>${clear?`<small>${clear}</small>`:''}`:`<b>${wait}</b>`}</span>${interactive?'</button>':'</section>'}`;}).join('');
  }
  function totalLine(m){const all=m.total!=null;return `<div class="cg-total-line"><span>합계</span><b class="cg-total-num${all?'':' pending'}" role="status" aria-live="polite" data-cd-total>${all?num(m.total):`미완료 · ${m.doneCount}/${m.bosses.length}`}</b></div>`;}
  function summaryHtml(view){const m=read(view);return `<div class="cg-top"><div class="cg-tabs" data-k="cs-boss-summary">${tabsHtml(m,false)}</div><aside class="cg-total">${totalLine(m).replace('data-cd-total','data-k="cs-sum"')}</aside></div>`;}
  // 팀별 난이도는 왼쪽 «이 팀 난이도»에서만 고름(11/19 PM: 3팀 일괄 난이도 줄 제거)
  function totalHtml(m){return totalLine(m);}
  const titleHtml=m=>`${m.attr(m.boss.element)}<span>${esc(m.boss.name)} 팀</span><span class="tag">${esc(EL[m.boss.element]||m.boss.element||'')}</span>`;
  function boardHtml(m,ui){
    const d=m.draft(m.active),powers=m.view.powers?.[m.active],errors=m.check(m.active)?.errors||[];
    return SCREEN.map(i=>{
      const slot=d.slots[i],s=slot&&(m.by.get(slot.key)||{key:slot.key,name:slot.key,el:'',cls:''}),leader=!!slot&&d.leader===slot.key,chosen=ui.sel===i;
      return `<section class="direct-slot${chosen?' selected':''}${leader?' direct-leader':''}" data-pos="${i<2?'front':'back'}" data-cd-slot="${i}">`
        +`<div class="direct-card-wrap"><button type="button" class="direct-member sec${s?'':' direct-vacant'}" data-cd-act="slot" data-slot="${i}" aria-pressed="${chosen}" aria-label="${LABELS[i]} ${s?esc(s.name)+' 선택':'빈 칸 · 구원자 넣기'}">`
        +(s?`<span class="fallback">${esc(s.name[0])}</span>${s.art||s.img?`<img class="art" src="${esc(s.art||s.img)}" width="512" height="512" alt="" loading="lazy">`:''}<span class="direct-name" title="${esc(s.name)}">${m.dia(s,20)}<span>${esc(s.name)}</span></span>`
          :'<span class="direct-empty" aria-hidden="true">＋</span><span class="direct-name">+ 구원자 넣기</span>')
        +`<b class="direct-position">${LABELS[i]}</b></button>`
        +(slot?`<button type="button" class="sec direct-leader-toggle" data-cd-act="leader" data-key="${esc(slot.key)}" aria-label="${LABELS[i]} 리더 지정" aria-pressed="${leader}"><span aria-hidden="true">${leader?'★':'☆'}</span>${leader?`<span class="crown" aria-hidden="true">${CROWN}<span>리더</span></span>`:''}</button>`
          +`<div class="direct-slot-tools"><button type="button" class="sec" data-cd-act="remove" data-slot="${i}" aria-label="${LABELS[i]} 빼기">✕</button></div>`:'')
        +`</div><button type="button" class="sec direct-grow" data-cd-act="grown" data-slot="${i}" aria-pressed="${!!slot?.grown}" title="${GROW_HELP}"${slot?'':' disabled'}><b class="direct-power">${slot?powerText(powers?.[i]):'—'}</b><span>${slot?.grown?'☑':'☐'} 육성했다면</span></button>`
        +errors.filter(e=>e.slot===i).map(e=>`<small class="direct-invalid">${esc(e.message)}</small>`).join('')+`</section>`;}).join('');
  }
  // 칸을 고른 뒤 쓰는 단추(터치 화면에는 칸 위 ✕ 가 안 보이므로). 고른 칸이 없으면 비어 있어 자리도 차지하지 않음.
  function selectionHtml(m,ui){
    const slot=ui.sel==null?null:m.draft(m.active).slots[ui.sel];if(!slot)return '';
    return `<small>고른 칸: ${LABELS[ui.sel]} ${esc(m.by.get(slot.key)?.name||'')}</small><div><button type="button" class="sec" data-cd-act="leader" data-key="${esc(slot.key)}">★ 리더로</button><button type="button" class="sec" data-cd-act="remove" data-slot="${ui.sel}">✕ 빼기</button><button type="button" class="sec" data-cd-act="deselect">선택 취소</button></div>`;
  }
  function toolsHtml(m){
    return `<button type="button" class="sec" data-cd-act="arrange" aria-label="자리 자동 배치"${m.count(m.active)===4?'':' disabled'}><span class="f">자리 자동 배치</span><span class="s">자동 배치</span></button>`
      +`<button type="button" class="sec" data-cd-act="clear"${m.count(m.active)?'':' disabled'}>비우기</button>`
      +`<button type="button" class="sec" data-cd-act="undo"${m.view.canUndo?'':' disabled'}>되돌리기</button>`;
  }
  // 구원자 목록: 이 팀 → 다른 팀에서 쓰는 중 → 나머지. 다른 팀 것은 넣을 수 없고(aria-disabled) 누르면 그 팀 탭으로.
  function listHtml(m,ui){
    const d=m.draft(m.active),mine=new Set(d.slots.filter(Boolean).map(s=>s.key)),q=(ui.query||'').trim().toLowerCase();
    const owner=k=>mine.has(k)?m.active:m.used.get(k)||null;
    const rank=s=>mine.has(s.key)?0:owner(s.key)?1:2;
    return (m.view.roster||[]).filter(s=>(s.owned!==false||ui.unowned||owner(s.key))&&(!q||s.name.toLowerCase().includes(q)))
      .map((s,i)=>[s,i]).sort((a,b)=>rank(a[0])-rank(b[0])||a[1]-b[1]).map(([s])=>{
        const u=owner(s.key),face=`<img src="${esc(s.img)}" alt="" loading="lazy">`,name=esc(s.name);
        if(u&&u!==m.active){const t=esc(m.short(u));
          return `<button type="button" class="sec direct-candidate cg-used" data-cd-act="jump" data-cd-goto="${esc(u)}" data-key="${esc(s.key)}" aria-disabled="true" aria-label="${name} · ${t} 팀 사용 중이라 넣을 수 없음 · 누르면 ${t} 팀 탭으로 이동" title="${t} 팀 사용 중 · 누르면 그 팀으로 이동">${face}<span>${name}<small>${t} 팀 사용 중 ›</small></span></button>`;}
        if(u)return `<button type="button" class="sec direct-candidate cg-in" data-key="${esc(s.key)}" disabled>${face}<span>${name}<small>편성됨</small></span></button>`;
        if(s.owned===false)return `<button type="button" class="sec direct-candidate direct-unowned" data-key="${esc(s.key)}" aria-disabled="true" aria-label="${name} · 보유하지 않아 넣을 수 없음">${face}<span>${name}<small>미보유</small></span></button>`;
        return `<button type="button" class="sec direct-candidate" data-cd-act="pick" data-key="${esc(s.key)}">${face}<span>${name}<small>${esc(EL[s.el]||s.el)} · ${esc(s.cls)}</small></span></button>`;}).join('');
  }
  // 브레이크는 선택 항목 — 안 고른 상태는 «장착 안 함». draft 가 'auto' 이면 그 사실을 감추지 않고 «자동 선택» 을 보여 줌.
  function controlsHtml(m){
    const t=m.team(m.active),brk=t.draft?.brk,name=brk&&brk!=='auto'?brk.name:null,list=m.view.breaks||[];
    return `<label><span>브레이크 스킬 <i>(선택)</i></span><select id="cd-break" data-cd-change="brk" aria-label="브레이크 스킬(선택)">`
      +`<option value="auto"${brk==='auto'?' selected':''}>자동 선택</option><option value=""${brk?'':' selected'}>장착 안 함</option>`
      +list.map(b=>`<option value="${esc(b.name)}" data-level="${b.level}"${b.name===name?' selected':''}>${esc(b.name)} Lv.${b.name===name?brk.level:b.level}</option>`).join('')
      +(name&&!list.some(b=>b.name===name)?`<option value="${esc(name)}" data-level="${brk.level}" selected>${esc(name)} Lv.${brk.level}</option>`:'')+`</select></label>`
      +`<label><span>이 팀 난이도</span><select id="cd-level" data-cd-change="level" aria-label="이 팀 난이도">${levels(m.levelMax,t.level)}</select></label>`;
  }
  // 실행 단추: 안 되면 흐리게(aria-disabled — 초점은 받음) + 이유 한 줄(aria-describedby).
  function gate(m){
    const own=m.blocks(m.active),n=m.count(m.active),others=m.bosses.filter(b=>b.key!==m.active);
    const lack=others.filter(b=>m.count(b.key)<4),bad=others.filter(b=>m.count(b.key)===4&&m.blocks(b.key).length);
    const names=xs=>xs.map(b=>shortOf(b)).join('·'),lines=[];
    if(m.view.running)lines.push('확인하는 중 · 끝나면 다시 누를 수 있음');
    else{
      if(n<4)lines.push(`이 팀에 ${4-n}명을 더 넣으면 확인 가능`+(lack.length?` · ${names(lack)} 팀도 4명 필요`:''));
      else if(own.length)lines.push(own.join(' · ')+(lack.length?` · ${names(lack)} 팀도 4명 필요`:''));
      else if(lack.length)lines.push(`«3팀 모두 확인»은 ${names(lack)} 팀 4명을 채운 뒤 가능`);
      for(const b of bad)lines.push(`${shortOf(b)} 팀: ${m.blocks(b.key)[0]}`);
      const rest=(m.view.validation?.errors||[]).map(e=>e.message).filter(x=>x&&!lines.some(l=>l.includes(x)));
      if(!lines.length&&m.view.validation&&m.view.validation.ok===false&&rest.length)lines.push(rest[0]);
    }
    const one=!!m.view.running||own.length>0;
    const all=!!m.view.running||one||lack.length>0||bad.length>0||m.view.validation?.ok===false;
    return {one,all,reason:lines.join(' · ')};
  }
  function runHtml(m){
    const g=gate(m);
    return `<div class="cg-actions"><button type="button" class="sec" id="cd-run-one" data-cd-act="run-one" aria-disabled="${g.one}" aria-describedby="cd-reason">이 팀 확인</button><button type="button" id="cd-run-all" data-cd-act="run-all" aria-disabled="${g.all}" aria-describedby="cd-reason">3팀 모두 확인</button></div>`
      +`<p id="cd-reason" class="cg-reason" role="status" aria-live="polite"${g.reason?'':' hidden'}>${esc(g.reason)}</p>`;
  }
  // 선택 팀 결과: 클리어율·점수(·예상 턴)만. 결과 전에는 칸 자체를 숨김(attrs.result).
  function resultHtml(m){
    const r=m.res(m.active);if(!m.done(m.active))return '';
    const c=r.clear;
    return `<div class="verdict-main"><b class="verdict-number"><small>클리어</small>${c!=null?pct(c)+'%':'—'}</b>${c!=null?`<span class="tag">${c>=.9?'안정적':c>=.7?'깰 수 있음':'아슬아슬'}</span>`:''}</div>`
      +`<div class="verdict-stats"><div><b>${num(r.score)}</b><small>점수</small></div>${r.turn!=null?`<div><b>${esc(r.turn)}</b><small>예상 턴</small></div>`:''}</div>`;
  }
  function model(view,ui){
    const m=read(view);
    if(ui.sel!=null&&ui.team!==m.active)ui.sel=null;
    ui.team=m.active;
    return {m,parts:{hint:view.drag?'끌어서 넣고 바꿈':'칸을 눌러 넣고 바꿈',steps:stepsHtml(m),tabs:tabsHtml(m),total:totalHtml(m,ui),title:titleHtml(m),board:boardHtml(m,ui),selection:selectionHtml(m,ui),tools:toolsHtml(m),
      list:listHtml(m,ui),controls:controlsHtml(m),run:runHtml(m),'result-title':m.done(m.active)?`${esc(m.short(m.active))} 팀 결과`:'',result:resultHtml(m)},
      attrs:{labelledby:'cd-tab-'+m.active,result:m.done(m.active)}};
  }
  const freshUi=()=>({sel:null,team:null,query:'',unowned:false,help:false,picker:false,levelAll:null,focus:null,last:{}});
  // 문서 순서 = 좁은 화면 순서: 카드 → 합계 → 레인 자리 → 보드 → 고르기 → 브레이크·난이도 → 확인 → 결과. 넓은 화면은 CSS 가 뒤쪽 칸을 왼쪽에 붙임.
  function html(view,ui){
    ui=ui||freshUi();const {parts:p,attrs:a}=model(view,ui);
    return `<div class="cd-root" data-cd-root>`
      +`<header class="direct-heading"><h2>직접 편성 · 코스모 게이트</h2><ol class="cg-steps" aria-label="편성 순서" data-cd-part="steps">${p.steps}</ol></header>`
      +`<div class="cg-top"><div class="cg-tabs" role="tablist" aria-label="보스별 팀" data-cd-part="tabs">${p.tabs}</div><aside class="cg-total" aria-label="3팀 합계" data-cd-part="total">${p.total}</aside></div>`
      +`<div class="result-layout" role="tabpanel" id="cd-panel" tabindex="0" aria-labelledby="${esc(a.labelledby)}" data-cd-panel>`
      +`<div class="result-team">`
      +`<div class="gwen-lane cd-lane" aria-label="그웬 길" data-cd-lane-slot></div>`
      +`<div class="cg-board-head"><h3 class="cg-board-title" data-cd-part="title">${p.title}</h3>`
      +`<p class="mut direct-drag-help"><span data-cd-part="hint">${p.hint}</span> · ☆ 리더 · ☐ 육성했다면 <button type="button" class="ux-help" id="cd-grow-help" data-cd-act="help" aria-expanded="${!!ui.help}" aria-controls="cd-grow-help-text" aria-label="«육성했다면» 도움말" title="${GROW_HELP}">?</button></p>`
      +`<p class="cg-help-text" id="cd-grow-help-text" data-cd-help${ui.help?'':' hidden'}>☐ 육성했다면 — ${GROW_HELP}</p></div>`
      +`<div class="cd-board" aria-label="편성판" data-cd-part="board">${p.board}</div>`
      +`<div class="cd-selection" data-cd-part="selection">${p.selection}</div>`
      +`<div class="cg-tools" role="group" aria-label="편성판 도구" data-cd-part="tools">${p.tools}</div>`
      +`<button type="button" class="sec cd-picker-open" data-cd-act="picker" aria-expanded="${!!ui.picker}" aria-controls="cd-picker">＋ 구원자 고르기</button>`
      +`<section id="cd-picker" class="direct-picker cd-picker" aria-label="구원자 고르기" data-cd-picker data-open="${!!ui.picker}">`
      +`<div class="cg-pick-head"><b>구원자 고르기</b><input type="search" placeholder="이름 검색" aria-label="직접 편성 구원자 검색" data-cd-search value="${esc(ui.query)}"><label><input type="checkbox" data-cd-change="unowned"${ui.unowned?' checked':''}> 미보유도 보기</label></div>`
      +`<div class="cd-list" data-cd-part="list">${p.list}</div></section>`
      +`</div>`
      +`<div class="result-summary">`
      +`<div class="cg-controls" data-cd-part="controls">${p.controls}</div>`
      +`<div class="cd-run" data-cd-part="run">${p.run}</div>`
      +`<div class="cg-result" data-cd-result${a.result?'':' hidden'}><p class="cg-result-title" data-cd-part="result-title">${p['result-title']}</p>`
      +`<div class="direct-result-hero"><div class="direct-result-numbers"><div class="mi-verdict cd-result-summary" data-cd-part="result">${p.result}</div></div>`
      +`<div class="direct-gwen"><div class="cg-gwen-slot" data-cd-gwen-slot></div></div></div></div>`
      +`</div></div></div>`;
  }
  const flag=(el,name,on)=>{if(!el)return;if(on)el.setAttribute(name,'');else el.removeAttribute(name);};
  // 다시 그릴 때는 바뀐 조각만 갈아 끼움 — 그웬 자리([data-cd-lane-slot]·[data-cd-gwen-slot])와 검색 칸은 그대로 남음.
  function paint(host){
    const ui=host.__cdui,doc=typeof document!=='undefined'?document:null;
    if(!host.querySelector('[data-cd-root]')){ui.last={};host.innerHTML=html(ui.view,ui);}
    const {parts,attrs}=model(ui.view,ui);
    const active=doc?.activeElement,inside=active&&host.contains(active)&&active!==host;
    const mark=inside?{id:active.id,act:active.getAttribute('data-cd-act'),slot:active.getAttribute('data-slot'),key:active.getAttribute('data-key')}:null;
    for(const [name,value] of Object.entries(parts)){
      if(ui.last[name]===value)continue;
      const el=host.querySelector(`[data-cd-part="${name}"]`);if(el)el.innerHTML=value;ui.last[name]=value;
    }
    host.querySelector('[data-cd-panel]')?.setAttribute('aria-labelledby',attrs.labelledby);
    flag(host.querySelector('[data-cd-result]'),'hidden',!attrs.result);
    flag(host.querySelector('[data-cd-help]'),'hidden',!ui.help);
    host.querySelector('[data-cd-act="help"]')?.setAttribute('aria-expanded',String(!!ui.help));
    host.querySelector('[data-cd-act="picker"]')?.setAttribute('aria-expanded',String(!!ui.picker));
    host.querySelector('[data-cd-picker]')?.setAttribute('data-open',String(!!ui.picker));
    let target=null;
    if(ui.focus){target=host.querySelector('#'+ui.focus);ui.focus=null;}
    else if(mark&&doc.activeElement!==active){
      target=mark.id?host.querySelector('#'+mark.id):mark.act&&mark.slot!=null?host.querySelector(`[data-cd-act="${mark.act}"][data-slot="${mark.slot}"]`)
        :mark.act&&mark.key?host.querySelector(`[data-cd-act="${mark.act}"][data-key="${mark.key}"]`):null;
    }
    if(target&&target.focus)target.focus({preventScroll:true});
  }
  function onClick(host,e){
    const ui=host.__cdui,h=ui.h,m=read(ui.view),boss=m.active;
    const tab=e.target.closest('[role=tab]');
    if(tab){ui.sel=null;ui.focus=tab.id;h.onTeam?.(tab.getAttribute('data-cd-boss'));return;}
    const b=e.target.closest('[data-cd-act]');if(!b||b.disabled||b.hasAttribute('disabled'))return;
    const act=b.getAttribute('data-cd-act'),slot=Number(b.getAttribute('data-slot')),key=b.getAttribute('data-key'),off=b.getAttribute('aria-disabled')==='true';
    const d=m.draft(boss);
    if(act==='jump'){const to=b.getAttribute('data-cd-goto');ui.sel=null;ui.focus='cd-tab-'+to;h.onPickerJump?.(to);return;}
    if(act==='run-one'){if(!off)h.onRunTeam?.(boss);return;}
    if(act==='run-all'){if(!off)h.onRunAll?.();return;}
    if(off)return;
    if(act==='help'){ui.help=!ui.help;paint(host);return;}
    if(act==='picker'){ui.picker=!ui.picker;paint(host);return;}
    if(act==='slot'){
      if(ui.sel!=null&&ui.sel!==slot){const a=ui.sel;ui.sel=null;h.onDraft?.(boss,{type:'swap',a,b:slot});paint(host);return;}
      ui.sel=ui.sel===slot?null:slot;
      if(ui.sel!=null&&!d.slots[slot])ui.picker=true;
      paint(host);return;
    }
    if(act==='deselect'){ui.sel=null;paint(host);return;}
    if(act==='pick'){const at=ui.sel;ui.sel=null;h.onDraft?.(boss,{type:'put',key,slot:at});paint(host);return;}
    if(act==='remove'){ui.sel=null;h.onDraft?.(boss,{type:'remove',slot});paint(host);return;}
    if(act==='leader'){h.onDraft?.(boss,{type:'leader',key});return;}
    if(act==='grown'){h.onDraft?.(boss,{type:'grown',slot,value:!d.slots[slot]?.grown});return;}
    if(act==='clear'){ui.sel=null;h.onDraft?.(boss,{type:'clear'});paint(host);return;}
    if(act==='arrange'){h.onArrange?.(boss);return;}
    if(act==='undo'){ui.sel=null;h.onUndo?.(boss);}
  }
  // 탭 방향키(←→·Home·End): 고른 탭을 바꾸고 초점도 따라감.
  function onKey(host,e){
    const tab=e.target.closest('[role=tab]');if(!tab)return;
    const ui=host.__cdui,m=read(ui.view),n=m.bosses.length,i=m.bosses.findIndex(b=>b.key===m.active);
    const j={ArrowRight:(i+1)%n,ArrowLeft:(i+n-1)%n,Home:0,End:n-1}[e.key];if(j==null)return;
    e.preventDefault();ui.sel=null;ui.focus='cd-tab-'+m.bosses[j].key;ui.h.onTeam?.(m.bosses[j].key);
  }
  function onChange(host,e){
    const el=e.target.closest('[data-cd-change]');if(!el)return;
    const ui=host.__cdui,m=read(ui.view),kind=el.getAttribute('data-cd-change'),v=el.value;
    if(kind==='level')ui.h.onLevel?.(m.active,Number(v));
    if(kind==='unowned'){ui.unowned=!!el.checked;paint(host);}
    if(kind==='brk'){
      const known=(m.view.breaks||[]).find(b=>b.name===v),cur=m.draft(m.active).brk;
      ui.h.onDraft?.(m.active,{type:'brk',value:v==='auto'?'auto':v===''?null:{name:v,level:known?known.level:cur&&cur.name===v?cur.level:1}});
    }
  }
  function onInput(host,e){
    if(!e.target.closest('[data-cd-search]'))return;
    host.__cdui.query=e.target.value||'';paint(host);
  }
  function render(host,view,h){
    if(!host.__cdui){
      host.__cdui=freshUi();
      host.addEventListener('click',e=>onClick(host,e));
      host.addEventListener('keydown',e=>onKey(host,e));
      host.addEventListener('change',e=>onChange(host,e));
      host.addEventListener('input',e=>onInput(host,e));
    }
    const ui=host.__cdui;ui.view=view;ui.h=h||{};
    if(ui.season!==view.season?.id){ui.season=view.season?.id;ui.levelAll=null;ui.sel=null;}
    paint(host);
    return host;
  }
  const api={render,html,summaryHtml,shortOf,SCREEN,LABELS};
  if(node)module.exports=api;else root.CosmoDirectUI=api;
})(typeof window!=='undefined'?window:globalThis);
