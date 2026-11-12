// Session-only content snapshots: never persist simulated accounts or slot proposals.
const SLOT={scope:null,contexts:new Map(),result:null,phase:'idle',msg:'',errors:[],excluded:[],stop:null};
function slotScope(){return MyInfoReco.hash([MI.hash,MODE,MM,SCROWN,[...EXCL].sort(),breakOwned(),BRSEL,SESSION_BR,SHARE.b,SHARE.b2,
  MI.growth,QK.d,['op','oph','clo','daily','equip','cube','rush','clash'].map(k=>simOpt(k))]);}
function slotCancel(){if(SLOT.stop)SLOT.stop();SLOT.stop=null;SLOT.phase='idle';SLOT.result=null;SLOT.msg='';SLOT.errors=[];
  SLOT.excluded=[];if(SIMQ.busy==='slots')SIMQ.busy=null;}
function slotSync(){const scope=slotScope();if(SLOT.scope!==scope){slotCancel();SLOT.scope=scope;SLOT.contexts.clear();}}
function slotRemember(c,st){if(!miMode()||!MI.growth||StarLink.availability(MI.info))return;
  slotSync();if(!MyInfoStats.rule_for_content(c.key)||SIMQ.busy!=null)return;
  const jobs=(LASTQ[1]?.all||[]).filter(t=>{const r=SIMQ.res[simSig(st,t)];return r&&growthMetric(r).n>=100;})
    .map(t=>({...growthJob(t,'owned|'+t.keys.slice().sort().join(','),c),result:growthMetric(SIMQ.res[simSig(st,t)])}));
  if(!jobs.length)return;
  const id=c.key+'/'+st.tab+'/'+st.name;
  const version=jobs[0].result.ver;
  for(const [k,v] of SLOT.contexts)if(v.version!==version)SLOT.contexts.delete(k);
  SLOT.contexts.set(id,{id,c,st,qi:quickIn(c,st),jobs,mode:MODE,options:structuredClone(simOpt(c.key)),version,
    scoring:structuredClone({gim:GIMACT,season:SBACT,damage:DMW})});
}
async function slotEvaluateState({info,referenceInfo=info,context,focus,remaining,deadline},id){
  const {c,st,qi}=context,cost=GrowthGuide.finalCost(100,context.mode),alive=()=>GROW.id===id;
  if(remaining<cost||Date.now()>=deadline)return {runs:0,paired:true};
  const profiles=[info,referenceInfo].map(i=>MyInfoReco.profile(i,R,MI.growth,c.key)),restrict=(CFG.restrict[c.name]||{})[st.tab];
  const keys=focus.map(uid=>R.find(s=>s.uid===uid)).filter(s=>s&&!EXCL.has(s.key)&&(!restrict||restrict===s.el)).map(s=>s.key);
  const combos=new Map(context.jobs.map(j=>[j.t.keys.slice().sort().join(','),j.t.combo]));
  for(const profile of profiles){
    const targets=await growthCandidates(c,st,alive,deadline,{original:profile,profile,qi,scoring:context.scoring,
      targets:keys.map(key=>({key,kind:'slot',id:key+'|slot'}))});
    for(const t of targets)for(const j of [...t.candidates,...t.controls])combos.set(j.t.keys.slice().sort().join(','),j.t.combo);
  }
  if(!alive())return {runs:0,paired:true};
  const defPen=CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty;
  const pairs=[...combos].filter(([,combo])=>profiles.every(p=>combo.every(x=>p.results[x.s.key]&&!p.results[x.s.key].missing.length)))
    .map(([key,combo])=>({key,jobs:profiles.map((p,i)=>growthJob(growthTeam(combo,p,qi,defPen,context.scoring),i+'|'+key,c))}));
  if(!pairs.length)return {runs:0,paired:true};
  const env={state:SLOT,mode:context.mode,options:context.options,paint:slotPaint};
  // Same party/options on fixed200 has exactly zero level effect; share that run.
  const unique=jobs=>{const seen=new Map(),aliases={};for(const j of jobs){const sig=JSON.stringify([j.party,j.options]);
    if(seen.has(sig))aliases[j.id]=seen.get(sig).id;else seen.set(sig,j);}return {jobs:[...seen.values()],aliases};};
  const expand=(results,aliases)=>{for(const [k,v] of Object.entries(aliases))if(results[v])results[k]=results[v];return results;};
  const screenPairs=pairs.slice(0,Math.max(0,Math.floor((remaining-2*cost)/8)));
  const screen=unique(screenPairs.flatMap(p=>p.jobs));
  const sr=await growthEvaluate(screen.jobs,4,17011,c,st,id,deadline,env);let runs=Object.keys(sr).length*4;expand(sr,screen.aliases);
  const established=context.jobs.slice().sort((a,b)=>GrowthGuide.cmp(a.result,b.result))[0];
  const keep=pairs.find(p=>p.key===established?.t.keys.slice().sort().join(','));
  const ranked=[0,1].map(i=>screenPairs.filter(p=>p.jobs.every(j=>sr[j.id])).sort((a,b)=>GrowthGuide.cmp(sr[a.jobs[i].id],sr[b.jobs[i].id])));
  const chosen=[...new Map([keep,ranked[0][0],ranked[1][0]].filter(Boolean).map(p=>[p.key,p])).values()]
    .slice(0,Math.floor((remaining-runs)/(2*cost)));
  const finals=unique(chosen.flatMap(p=>p.jobs));
  const fr=await growthEvaluate(finals.jobs,100,900001,c,st,id,deadline,env);runs+=Object.keys(fr).length*cost;expand(fr,finals.aliases);
  if(!chosen.length||chosen.some(p=>p.jobs.some(j=>!fr[j.id])))return {runs,paired:true};
  return {runs,paired:true,metric:chosen.map(p=>fr[p.jobs[0].id]).sort(GrowthGuide.cmp)[0],
    controlMetric:chosen.map(p=>fr[p.jobs[1].id]).sort(GrowthGuide.cmp)[0]};
}
async function slotStart(){if(SIMQ.busy!=null||StarLink.availability(MI.info))return;slotSync();
  const contexts=[...SLOT.contexts.values()];if(!contexts.length)return;
  const id=++GROW.id,alive=()=>GROW.id===id;
  SLOT.phase='running';SLOT.result=null;SLOT.errors=[];SLOT.msg='슬롯 후보 준비';SIMQ.busy='slots';slotPaint();
  try{
    const manifest=await fetch('sim/manifest.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('엔진 버전 확인 실패');return r.json();});
    if(!alive())return;
    if(contexts.some(c=>c.version!==manifest.ver))throw Error('엔진이 바뀜 · 콘텐츠를 다시 실행');
    GROW.versions={engine:manifest.ver,data:MyInfoReco.hash([GrowthGuide.VERSION,MI.growth,D,QK.d])};
    const original=MyInfoReco.profile(MI.info,R,MI.growth,'op'),link=MI.info.star_link;
    const gains=[];SLOT.excluded=[];
    for(const s of R.filter(s=>original.units[s.key]&&!link.source.includes(s.uid)&&
      !link.slots.some(slot=>slot.id===s.uid)&&!EXCL.has(s.key))){
      try{const a=MyInfoReco.assume(s.key,MI.info,MI.growth,{fields:['level']}),p=MyInfoReco.assumedProfile(original,a,MI.info,MI.growth,'op');
        const gain=p.results[s.key].power-original.results[s.key].power;if(gain>0)gains.push({id:s.uid,gain});
      }catch(e){SLOT.excluded.push({id:s.uid,reason:String(e.message)});}
    }
    const candidates=gains.sort((a,b)=>b.gain-a.gain||a.id-b.id).map(x=>x.id);
    SLOT.result=await StarLink.search({info:MI.info,contexts,candidates,alive,
      evaluate:request=>slotEvaluateState(request,id),progress:p=>{SLOT.msg=`완료 ${p.runs}판 · 교환 검증 ${p.pairs}쌍`;slotPaint();}});
    if(alive())SLOT.phase='done';
  }catch(e){if(alive()){SLOT.phase='error';SLOT.msg=e.message;}}
  finally{if(alive()){SIMQ.busy=null;if(SIMQ.pool){SIMQ.pool.slice(1).forEach(w=>w?.terminate());SIMQ.pool=null;}slotPaint();}}
}
function slotPaint(){if(!miMode()||!MI.info||!REQ)return;
  let el=$('star-link-result');if(!el){el=document.createElement('details');el.id='star-link-result';el.className='party slot-details';$('out').append(el);}
  const summary=document.querySelector('[data-k="growth-slot-summary"]');if(summary)summary.append(el);
  else if($('growth-result'))$('growth-result').after(el);
  const unavailable=StarLink.availability(MI.info);
  if(unavailable){el.innerHTML=`<summary>스타링크 슬롯 추천 <span class="tag" data-k="slot-unavailable">${esc(unavailable)}</span></summary>`;return;}
  const name=id=>id?(R.find(s=>s.uid===id)?.name||String(id)):'빈 슬롯',fmt=v=>v==null?'확인 부족':`${v>0?'+':''}${v.toFixed(1)}%p`;
  const content=id=>{const [k,tab,st]=id.split('/');return `${contents.find(c=>c.key===k)?.name||k} · ${tab} ${st}`;};
  const reason=rows=>rows.map(r=>`<span class="tag slot-${r.confirmed?'good':r.ci?.[1]<0?'bad':'pending'}" title="${esc(r.ci?'95% 차이 구간 '+r.ci.map(fmt).join(' ~ '):'미평가')}">${r.confirmed?'✓':r.ci?.[1]<0?'▼':'?'} ${esc(content(r.content))} ${fmt(r.delta)}${r.confirmed?'':r.ci?.[1]<0?' · 손해 확인':' · 확인 부족'}</span>`).join('');
  const face=id=>{const s=R.find(s=>s.uid===id);return s?`<span class="slot-face">${art(s)}</span>`:'';};
  const r=SLOT.result;
  el.innerHTML=`<summary>스타링크 슬롯 추천${SLOT.phase==='running'?' · 계산 중':SLOT.phase==='error'?' · 확인 부족':''}</summary><div data-k="slot-panel"><span class="tag" data-k="slot-cooldown">교체 쿨다운 있음</span>
    ${!r?'':r.swaps.map(s=>`<div class="slot-swap" data-k="slot-swap"><span class="slot-in">▲ 넣기: ${face(s.in)}<b>${esc(name(s.in))}</b> <small>Lv ${MI.info.units.find(u=>u.id===s.in).level}→링크</small></span><span class="slot-out">▼ 빼기: ${face(s.out)}<b>${esc(name(s.out))}</b></span><div>${reason(s.rows)}</div></div>`).join('')||'<p>확인 부족 · 개선이 확인된 교환 없음</p>'}
    ${SLOT.phase==='running'?`<p role="status">${esc(SLOT.msg)}</p><button class="sec" data-slot-stop>중단</button>`:
      `<button class="sec" data-slot-start ${SIMQ.busy!=null||!SLOT.contexts.size?'disabled':''}>슬롯 추천 계산</button>`}
    ${SLOT.phase==='error'?`<p>${esc(SLOT.msg)} · 확인 부족</p>`:''}
    <details><summary>슬롯 평가 상세${SLOT.excluded.length?` · 제외 ${SLOT.excluded.length}명`:''}</summary><p class="mut">직접 실행한 ${SLOT.contexts.size}개 스테이지 기준 · 현재 ${MI.info.star_link.slots.length}칸 · 소스 ${MI.info.star_link.source.length}명 별도</p>
    ${SLOT.excluded.map(x=>`<p data-k="slot-excluded">${esc(name(x.id))} 제외 · ${esc(x.reason)}</p>`).join('')}
    ${!r?'':`<p>지금 슬롯: ${r.initial.map(id=>esc(name(id))).join(' · ')}<br>추천 슬롯: ${r.slots.map(id=>esc(name(id))).join(' · ')}</p>
      <p class="mut">${(r.ms/1000).toFixed(1)}초 · 완료 ${r.runs}판 · ${r.pairs}쌍 검증${r.limited?' · 상한 내 부분 탐색 · 확인 부족':''}</p>
      <details><summary>슬롯에 넣으면 / 슬롯에서 빼면</summary>${r.diagnostics.map(d=>`<p>${d.step+1}차 ${d.kind==='in'?'넣기':'빼기'}: ${esc(name(d.id))}<br>${d.note?esc(d.note):reason(d.rows)}</p>`).join('')}</details>`}</details>
    ${SLOT.errors.length?'<p>일부 평가 실패 · 확인 부족</p>':''}</div>`;
  el.querySelector('[data-slot-start]')?.addEventListener('click',slotStart);
  el.querySelector('[data-slot-stop]')?.addEventListener('click',()=>{simInvalidate();SLOT.phase='error';SLOT.msg='중단함';slotPaint();});
}
