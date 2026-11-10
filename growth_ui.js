// Page integration. Uses the existing SIMQ workers, never a second worker budget.
const GROW={id:0,phase:'idle',result:null,sig:null,msg:'',stop:null,versions:null,history:{},errors:[]};
function growthOptions(){return {growth:!!document.getElementById('assume-growth')?.checked,
  owned:document.getElementById('assume-owned')?.value!=='missing'};}
function growthCacheTag(){return JSON.stringify([GrowthGuide.VERSION,growthOptions(),MI.growth?.assumed?.version]);}
function growthEnabled(){const o=growthOptions();return o.growth;}
function growthCancel(){if(typeof slotCancel==='function')slotCancel();GROW.id++;if(GROW.stop)GROW.stop();GROW.stop=null;
  if(typeof SIMQ!=='undefined'&&SIMQ.busy==='growth')SIMQ.busy=null;
  GROW.phase='idle';GROW.result=null;GROW.sig=null;GROW.msg='';GROW.errors=[];}
function growthInit(){const o=GrowthGuide.options(LS.get('growth.options')||{},SHARE);
  $('assume-growth').checked=o.growth;$('assume-owned').value=o.owned?'all':'missing';
  for(const id of ['assume-growth','assume-owned'])$(id).onchange=()=>{
    if(!MI.shared)LS.set('growth.options',growthOptions());condChanged();};}
function growthTargets(c,st){const opts=growthOptions(),restrict=(CFG.restrict[c.name]||{})[st.tab],owned=miProfile().units;
  const targets=[];for(const s of R){if(EXCL.has(s.key)||(restrict&&s.el!==restrict))continue;
    if(opts.growth&&(!owned[s.key]||opts.owned)){
      const t={key:s.key,kind:'growth',source:owned[s.key]?'owned':'assumed',id:s.key+'|growth'};targets.push(t);
      if(owned[s.key])for(const [component,fields] of Object.entries(GrowthGuide.COMPONENTS))
        targets.push({...t,id:t.id+'|'+component,parentId:t.id,component,fields});
    }}return targets;}
function growthSig(c,st){return GrowthGuide.signature({account:MI.hash,options:growthOptions(),targets:growthTargets(c,st),
  preset:MI.growth?.assumed?.version,content:[c.key,st.tab,st.name],excluded:[...EXCL],breaks:[breakOwned(),MI.info?.break_skills,BRSEL,SESSION_BR],
  mode:MODE,rules:simOpt(c.key),engine:GROW.versions?.engine,data:GROW.versions?.data});}
function growthMetric(r,mode=MODE){if(mode!=='manual'||!r.man)return r;
  return {...r,clear:r.man.c,ttk:r.man.t,n:r.man.n??r.n,ci:r.man.ci,prog:r.man.prog,progs:r.man.progs};}
function growthJob(t,id,c=contents[$('content').value]){const bn=breakChoice(t.combo,c).name||null;
  return {id,t,party:simParty(t),options:{break_skill:bn?{name:bn,level:brkLv(bn)}:null},breakName:bn};}
function growthScoreEnv(env,fn){if(!env)return fn();const saved=[GIMACT,SBACT,DMW];
  try{GIMACT=env.gim;SBACT=env.season;DMW=env.damage;return fn();}
  finally{[GIMACT,SBACT,DMW]=saved;}}
function growthTeam(combo,profile,qi,defPen,env){const keys=combo.map(x=>x.s.key),ek=keys.slice(),[v,got]=growthScoreEnv(env,()=>teamValue(combo,defPen)),
  b={growth:1,power:null,...MyInfoReco.team(keys,profile,k=>k)},q=Quick.evaluate(ek,qi.qs,QK.d.sv,D.pen,qi.prm,1,null,true,b.powers);
  return {combo,v,got,keys,ek,b,q,vd:q.ok?Quick.verdict(q):'hard',base:qi.qs.bp};}
function growthQuickCmp(a,b){return QO[b.vd]-QO[a.vd]||(a.vd==='hard'?(b.q.rounds??0)-(a.q.rounds??0):(b.q.left??0)-(a.q.left??0))||
  (a.q.rounds??Infinity)-(b.q.rounds??Infinity)||b.v-a.v;}
async function growthCandidates(c,st,alive,deadline,config={}){const original=config.original||miProfile(),qi=config.qi||quickIn(c,st),restrict=(CFG.restrict[c.name]||{})[st.tab],
  defPen=CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty,
  owned=R.filter(s=>original.results[s.key]&&!EXCL.has(s.key)&&(!restrict||s.el===restrict)),
  scored=s=>{const [v,parts]=growthScoreEnv(config.scoring,()=>score(s,st.w,c.main,c.boss));return {s,score:v,parts};},all=owned.map(scored),targets=[];
  for(const target of config.targets||growthTargets(c,st)){
    if(!alive())return [];
    const id=target.id||target.key+'|'+target.kind;
    if(Date.now()>=deadline){targets.push({...target,id,candidates:[],controls:[],limited:true});continue;}
    try{const assumed=config.profile?{changedFields:['level']}:MyInfoReco.assume(target.key,MI.info,MI.growth,{kind:target.kind,fields:target.fields});
      if(!assumed.changedFields.length&&!target.component)continue;
      const profile=config.profile||MyInfoReco.assumedProfile(original,assumed,MI.info,MI.growth,c.key),u=scored(BYKEY[target.key]);
      // Favor companions synergistic with the fixed target, plus role-diverse existing pool members.
      const rest=all.filter(x=>x.s.key!==target.key),base=partyPool(rest),pool=[],add=x=>{if(pool.length<GrowthGuide.LIMITS.companions&&!pool.includes(x))pool.push(x)};
      rest.slice().sort((a,b)=>(b.score+partySyn([b.s.key,target.key]).reduce((v,h)=>v+h.pts,0))-(a.score+partySyn([a.s.key,target.key]).reduce((v,h)=>v+h.pts,0))).slice(0,6).forEach(add);
      for(const role of [...new Set(rest.map(x=>x.s.cls))])base.filter(x=>x.s.cls===role).slice(0,2).forEach(add);
      base.forEach(add);let aq=[],qq=[];
      let steps=0;
      combinations:for(let a=0;a<pool.length;a++)for(let b=a+1;b<pool.length;b++)for(let d=b+1;d<pool.length;d++){
        if(Date.now()>=deadline||!alive())break combinations;
        if(++steps%64===0){await new Promise(ok=>setTimeout(ok,0));if(!alive())return [];}
        const t=growthTeam([u,pool[a],pool[b],pool[d]],profile,qi,defPen,config.scoring);aq.push(t);qq.push(t);}
      aq.sort((a,b)=>b.v-a.v);qq.sort(growthQuickCmp);
      const pick=new Map();for(const t of [qq[0],aq[0],qq[1],aq[1]])if(t&&pick.size<2)pick.set(t.keys.slice().sort().join(','),t);
      const candidates=[...pick].map(([k,t])=>growthJob(t,id+'|'+k,c)),controls=[];
      for(const job of candidates){if(Date.now()>=deadline)break;const three=job.t.combo.filter(x=>x.s.key!==target.key);
        const choices=all.filter(x=>!three.some(y=>y.s.key===x.s.key)).map(x=>growthTeam([x,...three],original,qi,defPen,config.scoring));
        choices.sort((a,b)=>b.v-a.v);const quick=choices.slice().sort(growthQuickCmp);
        for(const t of [choices[0],quick[0]])if(t)controls.push(growthJob(t,'owned|'+t.keys.slice().sort().join(','),c));}
      targets.push({...target,...assumed,id,candidates,controls});
    }catch(e){targets.push({...target,id,error:String(e.message),candidates:[],controls:[]});}
    if(!config.profile){GROW.msg=`육성 후보 준비 ${targets.length}건`;growthPaint();}await new Promise(ok=>setTimeout(ok,0));
  }return targets;}
function growthEvaluate(jobs,n,seed,c,st,id,deadline,env={}){const state=env.state||GROW,mode=env.mode||MODE,paint=env.paint||growthPaint;return new Promise(resolve=>{
  const results={};if(!jobs.length||Date.now()>=deadline||GROW.id!==id||state.errors.length){resolve(results);return;}
  if(!SIMQ.w){SIMQ.w=new Worker('sim_worker.js');SIMQ.loaded=false;}
  const workers=scrPool(),parts=workers.map(()=>[]),request=SIMQ.requestId=(SIMQ.requestId||0)+1;
  jobs.forEach((j,i)=>parts[i%workers.length].push(j));let open=parts.filter(p=>p.length).length,done=false;
  const finish=cut=>{if(done)return;done=true;clearTimeout(timer);state.stop=null;
    if(cut){for(const w of workers)w?.terminate();SIMQ.w=null;SIMQ.loaded=false;SIMQ.pool=null;}
    resolve(results);};
  const timer=setTimeout(()=>finish(true),Math.max(1,deadline-Date.now()));state.stop=()=>finish(true);
  for(const [i,w] of workers.entries()){
    if(!parts[i].length)continue;
    w.onmessage=e=>{const m=e.data;if(GROW.id!==id||SIMQ.requestId!==request||(m.id!=null&&m.id!==request))return;
      if(m.type==='stage'){if(m.msg==='준비 끝'){SIMQ.loaded=true;w._ready=true;}return;}
      if(m.type==='team'){if(m.result.ver!==GROW.versions.engine){state.errors.push('엔진 버전이 바뀜 · 다시 실행');finish(true);return;}
        results[m.key]=growthMetric({...m.result,n},mode);state.msg=`${seed===900001?'재평가':'후보 확인'} ${Object.keys(results).length}/${jobs.length} · ${n}판`;paint();}
      if(m.type==='done'&&--open===0)finish(false);
      if(m.type==='error'){state.errors.push('가정 시뮬 오류: '+m.msg);finish(true);}};
    w.onerror=e=>{state.errors.push('가정 작업자 오류: '+e.message);finish(true);};
    w.postMessage({type:'run',id:request,base:location.href.replace(/[?#].*$/,'').replace(/[^/]*$/,''),
      stage:c.key+'/'+st.tab+'/'+st.name,n_runs:n,seed,mode:seed===900001?mode:'auto',options:{...(env.options||simOpt(c.key)),rng_streams:true},
      teams:parts[i].map(j=>({key:j.id,party:j.party,options:j.options}))});
  }
});}
async function growthStart(c,st){if(GROW.phase==='running'||SIMQ.busy!=null||!MI.growth||!QK.d)return;
  const id=++GROW.id,alive=()=>GROW.id===id;GROW.phase='running';GROW.msg='육성 가이드 준비';SIMQ.busy='growth';growthPaint();
  try{
    const manifest=await fetch('sim/manifest.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('엔진 버전 확인 실패');return r.json();});
    if(!alive())return;GROW.versions={engine:manifest.ver,data:MyInfoReco.hash([GrowthGuide.VERSION,MI.growth,D,QK.d])};
    GROW.sig=growthSig(c,st);const started=Date.now(),deadline=started+GrowthGuide.LIMITS.maxMs;
    const targets=await growthCandidates(c,st,alive,deadline);if(!alive())return;
    const owned=(LASTQ[1]?.all||[]).filter(t=>SIMQ.res[simSig(st,t)]).map(t=>({...growthJob(t,'owned|'+t.keys.slice().sort().join(','),c),result:growthMetric(SIMQ.res[simSig(st,t)])}));
    const result=await GrowthGuide.search({targets,owned,alive,mode:MODE,
      limits:{maxMs:Math.max(0,deadline-Date.now())},
      evaluate:(jobs,n,seed)=>growthEvaluate(jobs,n,seed,c,st,id,deadline),
      progress:m=>{GROW.msg=m;growthPaint();}});
    if(!alive()||!result)return;
    result.ms=Date.now()-started;result.scope.maxMs=GrowthGuide.LIMITS.maxMs;GROW.result=result;GROW.phase='done';
    const content=c.key+'/'+st.tab+'/'+st.name,version=GROW.versions.engine+'|'+GROW.versions.data;
    const entry=GrowthGuide.summary(result,content,GROW.sig,MI.hash,version);
    if(MI.shared)GROW.history[content]=entry;else GrowthGuide.save(LS,false,entry);
  }catch(e){if(alive()){GROW.phase='error';GROW.msg=e.message;}}
  finally{if(alive()){SIMQ.busy=null;if(SIMQ.pool){SIMQ.pool.slice(1).forEach(w=>w?.terminate());SIMQ.pool=null;}growthPaint();if(typeof slotPaint==='function')slotPaint();}}
}
function growthMaybe(c,st){if(!growthEnabled()||!miMode()||!['op','clo'].includes(c.key)||!REQ)return;
  if(GROW.sig&&GROW.sig!==growthSig(c,st))growthCancel();
  if(GROW.phase==='idle'&&SIMQ.busy==null&&!SIMQ.err&&simAutoOn())setTimeout(()=>{if(REQ&&GROW.phase==='idle')growthStart(c,st);},0);
  growthPaint();}
const growthLabel=r=>r.source==='assumed'?'미보유 가정':'임시 보정';
const growthFields={level:'레벨→스타링크',resonance:'공명 최대',skills:'스킬 최대',journey:'목표 여정',potentials:'목표 잠재력',equip:'장비 +15'};
const growthParts={level:'레벨만',equipment:'장비만',skills:'스킬만',potential:'공명·잠재력만'};
function growthDescription(r){return (r.changedFields||[]).map(f=>{
  const c=r.changes?.[f];if(f==='level'&&c)return `${c.before==null?'Lv ':('Lv '+c.before+'→')}스타링크`;
  if(f==='resonance'&&c)return `공명 ${c.before??0}→${c.after}`;
  return growthFields[f];}).join(' · ');}
function growthBadge(r){return `<span class="assumed-label" data-k="assumed-badge">${esc(growthLabel(r))}${growthDescription(r)?' · '+esc(growthDescription(r)):''}</span>`;}
function growthCardMeta(r){const before=miProfile().results[r.key],after=r.team?.t.b.finals[r.key];
  if(!after)return '';
  const number=(label,a,b)=>`<span class="tag">${label} ${miNum(b)}${a!==b?`<small class="assumed-mark" title="${label} ${miNum(a)} → ${miNum(b)}" aria-label="${label} 임시 보정">*</small>`:''}</span>`;
  return `<div class="mi-chips">${number('전투력',before?.power,after.power)}${['atk','hp','def','spd'].map((k,i)=>number(['공','생','방','속'][i],before?.stats[k],after.stats[k])).join('')}</div>`;}
function growthPaint(){if(!growthEnabled())return;let el=$('growth-result');
  if(!el){if(!['op','clo'].includes(contents[$('content').value]?.key)||!REQ)return;
    el=document.createElement('div');el.id='growth-result';el.className='party';$('out').append(el);}
  if(GROW.phase==='running'){el.innerHTML=`<b>육성 가이드</b><p role="status">${esc(GROW.msg)}</p><button class="sec" data-growth-cancel>가정 중단</button>`;
    el.querySelector('button').onclick=()=>{simInvalidate();GROW.phase='error';GROW.msg='중단함 · 미평가';growthPaint();};return;}
  if(!GROW.result){el.innerHTML=`<b>육성 가이드</b><p>${esc(GROW.msg||'보유 편성 확인 뒤 평가')}</p>`;return;}
  const r=GROW.result,rows=r.rows.filter(x=>!x.component).sort((a,b)=>(b.delta??-Infinity)-(a.delta??-Infinity)),fmt=v=>v==null?'—':(v>0?'+':'')+v.toFixed(1),
    metric=v=>v?`${(v.clear*100).toFixed(1)}% · 진행 ${((v.prog||0)*100).toFixed(1)}% · ${v.ttk==null?'—':v.ttk.toFixed(1)}턴 · ${v.n}판`:r.baselinePending?'기준 재평가 미완료':'기준 편성 없음';
  const status=x=>x.result?metric(x.result):x.status==='unsupported'?'자료 미지원':x.status==='screened'?'예선만 · 미평가':'미평가';
  const delta=x=>x.delta==null?'확인 부족':fmt(x.delta)+'%p'+(x.confirmed?' · 개선 확인':' · 확인 부족');
  const best=rows.find(x=>x.result);
  let cards='';if(best?.team){const ar=arrangeOf(best.team.t.combo);LEADKEY=ar.lead;
    cards=`<div data-k="growth-best"><b><span class="tag assumed-label">가정 포함</span> ${esc(BYKEY[best.key]?.name||best.key)}</b><div class="rowcards">${ar.order.map((k,i)=>{
      const x=best.team.t.combo.find(x=>x.s.key===k);return card(x,i===0||i===3?'back':'front',null,k===best.key?best:null);
    }).join('')}</div><p>${metric(best.result)} · 브레이크 ${esc(best.team.breakName||'없음')}</p></div>`;}
  const contributions=x=>{const parts=r.rows.filter(p=>p.parentId===x.id);return parts.length?`<details data-k="growth-contributions"><summary>항목별 기여</summary><p class="mut">각 항목만 바꾸고 다시 탐색 · 합산하지 않음</p>${parts.map(p=>`<p data-component="${p.component}"><b>${growthParts[p.component]}</b> ${delta(p)}<br>${growthBadge(p)}<br><span class="mut" title="${esc(p.error||'')}">${status(p)}${p.ci?' · 차이 구간 '+p.ci.map(fmt).join(' ~ ')+'%p':''}</span></p>`).join('')}</details>`:'';};
  el.innerHTML=`<b>이 구원자를 키우면</b>${GROW.errors.length?`<p class="bad" title="${esc(GROW.errors.join(' · '))}">일부 평가 실패 · 완료한 결과만 표시</p>`:''}<p class="mut">보유 기준 ${metric(r.baseline)} · 묶음 평가 ${rows.filter(x=>x.result).length}/${rows.length}명 · ${(r.ms/1000).toFixed(1)}초 · 완료 ${r.runs}판</p>${cards}
    <div style="overflow-x:auto"><table data-k="growth-table"><thead><tr><th>구원자</th><th>목표 육성 묶음</th><th>묶음 전체 개선</th><th>95% 차이 구간</th><th>평가 범위</th></tr></thead><tbody>${rows.map(x=>`<tr data-growth-key="${esc(x.id)}"><td>${esc(BYKEY[x.key]?.name||x.key)}</td><td>${growthBadge(x)}${contributions(x)}</td><td>${delta(x)}</td><td>${x.ci?x.ci.map(fmt).join(' ~ ')+'%p':'—'}</td><td title="${esc(x.error||'')}">${status(x)} · 후보 ${x.screened}/2</td></tr>`).join('')}</tbody></table></div>`;
  const version=GROW.versions.engine+'|'+GROW.versions.data,history=MI.shared?GROW.history:LS.get('growth.history')||{},
    matching=Object.fromEntries(Object.entries(history).filter(([,v])=>v.account===MI.hash&&v.version===version)),priority=GrowthGuide.priority(matching);
  el.innerHTML+=`<details><summary>성능 개선 기준 육성 후보</summary>${priority.slice(0,12).map(x=>`<p>${esc(BYKEY[x.key]?.name||x.key)} · 묶음 · 개선 확인 ${x.count}콘텐츠<br><span class="mut">${x.contents.map(v=>`${esc(v.content)} ${v.delta==null?'미평가':fmt(v.delta)+'%p'}`).join(' · ')}</span></p>`).join('')}</details>`;
}
