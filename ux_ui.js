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
  function verdict(p){return p>=.9?['safe','안정적']:p>=.7?['ok','깰 수 있음']:p>=.5?['shaky','아슬아슬']:['risk','어려움'];}
  function help(title,text){return `<button type="button" class="ux-help" data-help="${esc(text)}" aria-label="${esc(title)} 설명" aria-expanded="false">ⓘ</button>`;}
  // 공식 SD를 참고한 팬 그림. picture가 동작 줄이기에서는 정지 PNG를 선택함.
  // 탐정 그웬의 한 줄. 첫 줄이 기본이고, 브라우저에서는 방문마다 한 가지를 골라 그 방문 내내 유지함(다시 그려도 글자가 바뀌지 않음).
  const GWEN_LINES={
    inspect:['그웬이 추천 편성 확인 중…','그웬이 단서 모으는 중…','그웬이 사건 파일 펴는 중…'],
    screen:['그웬이 후보 거르는 중…','용의자… 아니 후보 거르는 중…','그웬이 서류 더미 뒤지는 중…'],
    long:['그웬이 끈질기게 검증 중…','그웬이 잠복 수사 중…','그웬이 상위 편성 탐문 중…'],
    report:['조사 끝 · 보고함']};
  const gwenSeed=root.document?Math.floor(Math.random()*6):0;
  const gwenLine=mode=>{const lines=GWEN_LINES[mode];return lines?lines[gwenSeed%lines.length]:'';};
  // 그웬 말풍선 대사 표(친근한 반말·한 줄). 상황별 2~4개 중 방문당 하나로 고정함. 진행률·숫자·보안 안내는 여기 두지 않음.
  const GWEN_SAY={
    inspect:['단서는 끈질기게 모으는 법이지','사건 파일부터 펼쳐 볼게','좋아, 수사를 시작해 볼까?'],
    screen:['후보를 하나씩 탐문 중…','수상한 후보는 내가 걸러 낼게','답은 서류 더미 속에 있어!'],
    long:['잠복은 내 특기야. 조금만 기다려','끝까지 파헤치는 게 탐정이지','진실을 밝히는 빛! …곧 보일 거야'],
    report:['조사 끝! 보고할게','수사 완료, 결과 나왔어!'],
    error:['으… 단서가 부족해','이런, 수사가 막혔어…','음… 이건 예상 밖인데'],
    high:['사건 해결! 이 편성이면 충분해','범인은… 아니, 정답은 바로 이 편성!','이 편성, 내가 보증할게!'],
    shaky:['아슬아슬해… 한 번 더 확인해 봐','반반 승부야. 방심은 금물!'],
    hard:['이대론 벅차. 편성을 손봐야겠어','단서가 더 필요해. 육성도 살펴봐'],
    low:['이 사건은 만만치 않아. 육성부터 하자','지금은 무리야. 힘부터 기르자'],
    welcome:['어서 와, 단장! 어떤 사건이야?','그웬 탐정 사무소에 잘 왔어!','사건이라면 나한테 맡겨!'],
    import:['단장의 정보! 내가 받아 갈게','정보만 주면 수사는 내가 할게'],
    empty:['명단이 비었네. 정보부터 받아 올까?','아직 사건 파일이 텅 비었어']};
  const gwenSayLine=key=>{const lines=Object.hasOwn(GWEN_SAY,key)?GWEN_SAY[key]:null;return lines?lines[gwenSeed%lines.length]:'';};
  // 클리어율 구간(판정 칩과 같은 경계): 70% 이상·50% 이상·5% 이상·그 미만.
  const gwenSayBand=p=>!Number.isFinite(p)?'':p>=.7?'high':p>=.5?'shaky':p>=.05?'hard':'low';
  // 말풍선은 장식(같은 뜻의 안내·판정이 옆에 글로 있음)이라 읽기 도구에는 숨김. tail = 꼬리가 향하는 쪽(down·up·left·right).
  function gwenSay(key,tail='down'){
    const line=gwenSayLine(key);
    return line?`<span class="gwen-bubble" data-gwen-say="${esc(key)}" data-tail="${esc(tail)}" aria-hidden="true">${esc(line)}</span>`:'';
  }
  const GWEN_ART=new Set(['investigate','files','walk','report','surprised','welcome','confident','thoughtful','notes']);
  function gwenImage(art,cls='gwen-worker',size=160){
    if(!GWEN_ART.has(art))return '';
    const base='assets/ui_icons/gwen/'+art;
    // No URL is assigned until the actual visible intersection, including hidden tabs/drawers.
    return `<img class="${cls}" data-gwen-art="${art}" data-gwen-static="${base}.png" data-gwen-motion="${base}.webp" width="${size}" height="${size}" alt="" aria-hidden="true" loading="lazy">`;
  }
  function gwenReaction(p){
    if(!Number.isFinite(p))return '';
    const art=p<.05?'notes':p<.7?'thoughtful':'confident';
    return `<div class="gwen-reaction" data-gwen-reaction="${art}" aria-hidden="true"><div class="gwen-bubble-space">${gwenSay(gwenSayBand(p))}</div>${gwenImage(art,'gwen-reaction-art',240)}</div>`;
  }
  function gwenWork(mode,say=mode){
    const art={inspect:'investigate',screen:'files',long:'walk',error:'surprised',report:'report',welcome:'welcome'}[mode];
    if(!art)return '';
    const label=gwenLine(mode);
    const roam=art==='investigate'||art==='walk';
    return `<span class="gwen-work${roam?' gwen-roam':''}" data-gwen="${mode}">${typeof say==='string'&&gwenSayLine(say)?`<span class="gwen-say-lane">${gwenSay(say)}</span>`:''}<span class="gwen-track"><span class="gwen-traveler"><span class="gwen-scene" aria-hidden="true">${gwenImage(art)}</span></span></span>${label?`<span class="gwen-caption">${label}</span>`:''}</span>`;
  }
  // Each one-shot WebP has loop=1. A new blob URL replays cached bytes without network
  // downloads on every interval. Every pending callback is invalidated on hide/reduce/remove.
  function mountGwen(){
    const doc=root.document,media=root.matchMedia('(prefers-reduced-motion: reduce)');
    const states=new Map(),blobs=new Map();
    const continuous=new Set(['investigate','files','walk']);
    function visible(img){
      if(doc.hidden||!states.get(img)?.intersecting||!img.isConnected||!(img.checkVisibility?.({visibilityProperty:true,opacityProperty:true})??img.getClientRects().length))return false;
      const r=img.getBoundingClientRect();
      return r.bottom>0&&r.right>0&&r.top<root.innerHeight&&r.left<root.innerWidth;
    }
    function still(img,s){
      if(s.loaded&&img.getAttribute('src')!==img.dataset.gwenStatic)img.src=img.dataset.gwenStatic;
      if(s.url){root.URL.revokeObjectURL(s.url);s.url=null;}
      img.dataset.gwenPlaying='false';
    }
    function stop(img,s){
      root.clearTimeout(s.timer);s.timer=null;s.token++;s.active=false;
      still(img,s);
    }
    function play(img,s){
      if(!visible(img)||media.matches){stop(img,s);return;}
      const token=++s.token,path=img.dataset.gwenMotion;
      if(!blobs.has(path))blobs.set(path,root.fetch(path).then(r=>{if(!r.ok)throw Error(r.status);return r.blob();}).catch(e=>{blobs.delete(path);throw e;}));
      blobs.get(path).then(blob=>{
        if(token!==s.token||!visible(img)||media.matches)return;
        s.url=root.URL.createObjectURL(blob);img.src=s.url;img.dataset.gwenPlaying='true';
        // Start the duration after decoding, so a cold load still gets a complete action.
        return img.decode().then(()=>{
          if(token!==s.token)return;
          s.timer=root.setTimeout(()=>{
            still(img,s);
            const delay=4000+Math.floor(Math.random()*4001);
            s.timer=root.setTimeout(()=>play(img,s),delay);
          },1000);
        });
      }).catch(()=>{if(token===s.token)stop(img,s);});
    }
    function update(img,s){
      if(!visible(img)){if(s.active)stop(img,s);return;}
      if(!s.loaded){s.loaded=true;img.src=img.dataset.gwenStatic;}
      if(media.matches){if(s.active)stop(img,s);return;}
      if(s.active)return;
      s.active=true;
      if(continuous.has(img.dataset.gwenArt)){img.src=img.dataset.gwenMotion;img.dataset.gwenPlaying='true';}
      else play(img,s);
    }
    const observer=new root.IntersectionObserver(entries=>{for(const e of entries){const s=states.get(e.target);if(s){s.intersecting=e.isIntersecting&&e.intersectionRect.width>0&&e.intersectionRect.height>0;update(e.target,s);}}},{threshold:[0,.001]});
    function refresh(){
      for(const [img,s] of states)if(!img.isConnected){stop(img,s);observer.unobserve(img);states.delete(img);}
      doc.querySelectorAll('img[data-gwen-art]').forEach(img=>{
        if(!states.has(img)){states.set(img,{token:0,active:false,loaded:false,timer:null,url:null,intersecting:false});observer.observe(img);}
        update(img,states.get(img));
      });
    }
    new root.MutationObserver(refresh).observe(doc.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','hidden','open','style']});
    doc.addEventListener('visibilitychange',()=>{doc.documentElement.classList.toggle('gwen-paused',doc.hidden);refresh();});
    media.addEventListener('change',refresh);
    root.addEventListener('resize',refresh);
    refresh();
  }
  // 같은 결과를 다시 그리거나 접기를 열어도 발표를 반복하지 않음.
  const gwenResults=new WeakMap(),gwenPending=new Map();let gwenSerial=0;
  function gwenReport(result){
    if(!result||typeof result!=='object')return '';
    let state=gwenResults.get(result);
    if(!state){state={id:String(++gwenSerial),remaining:1800,started:0,timer:null,done:false};gwenResults.set(result,state);}
    if(state.done)return '';
    gwenPending.set(state.id,state);
    return gwenWork('report').replace('data-gwen="report"',`data-gwen="report" data-gwen-report="${state.id}"`);
  }
  function gwenStage(message=''){
    return /후보 거르|훑|예선|놓침 감지|1단계|2단계/.test(message)?'screen':/준비|능력치 계산/.test(message)?'inspect':'long';
  }
  // 진행률 갱신 때 단추와 그림 DOM을 보존하고, 단계가 바뀔 때만 연출을 교체함.
  function syncGwen(container,mode){
    const old=container?.querySelector('[data-gwen]');
    if(old&&old.dataset.gwen!==mode)old.outerHTML=gwenWork(mode);
  }
  let grades=null;
  function setGrades(table){grades=table;}
  function grade(value,index,table=grades){const rows=table?.stats?.[index];if(!Number.isFinite(value)||!rows||value>1500)return '';return rows.reduce((g,r)=>value>=r[0]?r[1]:g,'');}
  function archive(value,index,table){const g=grade(value,index,table);return (g?g+' ':'')+num(value);}
  function chip(p){const [state,label]=verdict(p);return `<span class="verdict-chip g-${state}" data-verdict="${state}">${label}</span>`;}
  // 운에 크게 좌우되는 결과 안내: 클리어율 5% 미만이거나, 95% 구간이 1% 밑에서 5% 이상까지 걸쳐 결론이 흔들릴 때만 문구를 낸다.
  // r = 시뮬 요약({clear, ci:[하한,상한], n}). 「30번 도전 시 한 번이라도 깰 확률」 = 1-(1-p)^30(판마다 독립 가정).
  const LUCK={low:.05,ciLo:.01,ciHi:.05,tries:30};
  const pctText=p=>{const v=Math.round(p*1000)/10;return (v>=10?Math.round(v):v)+'%';};
  function luckNote(r){const p=r?.clear;if(!Number.isFinite(p))return '';
    const ci=Array.isArray(r.ci)&&r.ci.every(Number.isFinite)?r.ci:null;
    const low=p<LUCK.low,shaky=!!ci&&ci[0]<LUCK.ciLo&&ci[1]>=LUCK.ciHi;
    if(!low&&!shaky)return '';
    const once=1-Math.pow(1-p,LUCK.tries);
    const head=p===0?`모의 전투 ${num(r.n)}판에서 한 번도 못 깼음.`:low?`클리어 확률 매우 낮음(약 ${pctText(p)}).`:`클리어 확률이 낮고 결과가 흔들림(약 ${pctText(p)}, 범위 ${pctText(ci[0])}~${pctText(ci[1])}).`;
    const tries=p>0?` ${LUCK.tries}번 도전해도 한 번이라도 깰 확률은 약 ${pctText(once)}임.`:'';
    return `<div class="luck-note" data-k="luck-note" role="note"><span class="gwen-memo"><img src="assets/ui_icons/gwen_header_72.png" width="20" height="20" alt="" aria-hidden="true">그웬의 메모</span>${head} 몇십 번 시도해도 못 깰 수 있음 — 파티 변경이나 추가 육성 권장.${tries}</div>`;}
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
        // 기록을 통째로 다시 만드는 추천: 지금 주력 칸 → 바뀌는 주력 칸을 함께 보인다(이미 SG 인 칸을 버리는 추천일 수 있음을 알게)
        const top=x=>x&&x.some(v=>v>0)?x.indexOf(Math.max(...x)):null,mb=top(b),mt=top(t||[]);
        const g=(x,i)=>grade(x[i],i,table)||num(x[i]);
        short=mt==null?'':`(주력 ${mb==null?'없음':names[mb]+' '+g(b,mb)} → ${names[mt]} ${g(t,mt)})`;
        const down=names.filter((n,i)=>(b?.[i]||0)>t[i]);
        detail='한 번의 여정 결과로 기록 전체를 다시 만드는 목표임(칸별로 좋은 값만 섞을 수 없음).'+(down.length?`\n지금보다 내려가는 칸: ${down.join('·')}`:'')+'\n'+
          names.map((n,i)=>`${n} ${archive(b?.[i]||0,i,table)} → ${archive(t[i],i,table)}${t[i]===1250?' (MAX)':''}`).join('\n');
      }
      if(f==='potentials'){
        const changes=(t||[]).filter(p=>!(b||[]).some(q=>q[0]===p[0]&&q[1]>=p[1]));
        short=changes.map(p=>`${view.potentials?.[p[0]]?.name||''} ${(b||[]).find(q=>q[0]===p[0])?.[1]||'미습득'}→${p[1]}`).join(' · ');
        detail=changes.map(p=>`${view.potentials?.[p[0]]?.name||'잠재력 '+p[0]} ${(b||[]).find(q=>q[0]===p[0])?.[1]||'미습득'} → ${p[1]}`).join('\n');
      }
      return {field:f,label:f==='journey'?'스텔라 아카이브 기록 다시 만들기':labels[f],short,detail:detail||short,delta};
    });
    return {before,after,fields,missing:!old};
  }
  function todosHtml(m){return (m?.fields||[]).filter(f=>f.delta!==0).map(f=>`<button type="button" class="growth-todo" data-growth-field="${f.field}" data-power-delta="${f.delta??''}" data-help="${esc(f.detail+'\n전투력 '+signed(f.delta)+' · 이 항목만 목표로 올렸을 때의 증가임.')}" aria-expanded="false">${esc(f.label)} ${esc(f.short)} <small>(${signed(f.delta)})</small></button>`).join('');}
  function memberHtml(m,withTodos=true){if(!m)return '';return `<div class="growth-power" data-k="member-power">전투력 ${num(m.before)} → ${num(m.after)}</div>`+(withTodos?`<div class="growth-todos">${todosHtml(m)}</div>`:'');}
  // 스테이지형 콘텐츠(길방·코스모 밖 전부)는 확률, 시즌 콘텐츠는 점수. goalTurns>0 = 3별 목표: 확률은 «N턴 내 클리어율»(t60)로 보인다
  function resultTabState({enabled,phase,better,baseline,best,kind='op',message='',errors=[],goalTurns=0}){
    const probability=kind!=='guild'&&kind!=='cosmo',field=kind==='guild'?'score':'sum';
    const goal=r=>goalTurns&&r?.t60!=null?r.t60:r?.clear;
    const metric=r=>probability?(Number.isFinite(goal(r))?Math.round(goal(r)*100)+'%':'계산 전'):
      (Number.isFinite(r?.[field])?num(r[field])+'점':'계산 전');
    return {show:!!enabled&&(phase==='running'||phase==='error'||phase==='done'&&!!better),
      now:(probability?(goalTurns?goalTurns+'턴 내 ':'클리어 '):'점수 ')+metric(baseline),
      growth:phase==='running'?'계산 중'+(message?' · '+message:''):phase==='error'?'미완료'+(errors.length?' · 실패':''):'맞추면 '+metric(best)+' ↑',
      recommend:probability&&Number.isFinite(goal(baseline))&&goal(baseline)<.5,phase};
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
    mountGwen();
    // 정적 HTML 에 미리 놓인 빈 말풍선(불러오기 창)은 여기서 한 번만 채움.
    doc.querySelectorAll('.gwen-bubble[data-gwen-say]:empty').forEach(el=>{el.textContent=gwenSayLine(el.dataset.gwenSay);});
    const retireReports=()=>{
      const live=new Map();
      doc.querySelectorAll('[data-gwen="report"]').forEach(el=>{
        const id=el.dataset.gwenReport,r=el.getBoundingClientRect();
        live.set(id,!doc.hidden&&(el.checkVisibility?.({visibilityProperty:true,opacityProperty:true})??el.getClientRects().length)&&r.bottom>0&&r.top<root.innerHeight);
      });
      for(const [id,state] of gwenPending){
        if(!live.get(id)){
          if(state.timer){root.clearTimeout(state.timer);state.timer=null;state.remaining=Math.max(0,state.remaining-(Date.now()-state.started));}
          if(!live.has(id))gwenPending.delete(id);
        }else if(!state.timer){
          state.started=Date.now();
          state.timer=root.setTimeout(()=>{
            state.timer=null;state.done=true;gwenPending.delete(id);
            doc.querySelectorAll(`[data-gwen-report="${id}"]`).forEach(el=>el.remove());
          },state.remaining);
        }
      }
    };
    new root.MutationObserver(retireReports).observe(doc.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','hidden','open','style']});
    retireReports();
    doc.addEventListener('visibilitychange',retireReports);
    root.addEventListener('scroll',retireReports,true);
    root.addEventListener('resize',retireReports);
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
  const api={verdict,help,gwenImage,gwenReaction,gwenWork,GWEN_LINES,GWEN_SAY,gwenSay,gwenSayBand,gwenReport,gwenStage,syncGwen,grade,archive,setGrades,chip,luckNote,LUCK,signed,num,labels,member,todosHtml,memberHtml,resultTabState,createResultTabs,mount};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.Ux=api;
})(typeof globalThis!=='undefined'?globalThis:this);
