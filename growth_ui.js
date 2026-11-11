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
function growthTargets(c,st){const opts=growthOptions(),restrict=(CFG.restrict[c.name]||{})[st.tab],owned=(c.key==='guild'?MyInfoReco.profile(MI.info,R,MI.growth,'op'):miProfile()).units;
  const targets=[];for(const s of R){if(EXCL.has(s.key)||(restrict&&s.el!==restrict))continue;
    if(opts.growth&&(!owned[s.key]||opts.owned)){
      const t={key:s.key,kind:'growth',source:owned[s.key]?'owned':'assumed',id:s.key+'|growth'};targets.push(t);
      if(owned[s.key])for(const [component,fields] of Object.entries(GrowthGuide.COMPONENTS))
        targets.push({...t,id:t.id+'|'+component,parentId:t.id,component,fields});
    }}return targets;}
function growthSig(c,st){return GrowthGuide.signature({account:MI.hash,options:growthOptions(),targets:growthTargets(c,st),
  preset:MI.growth?.assumed?.version,content:[c.key,st.tab,st.name],excluded:[...EXCL],breaks:[breakOwned(),MI.info?.break_skills,BRSEL,SESSION_BR],
  mode:MODE,modifiers:[MM,SCROWN],rules:simOpt(c.key),engine:GROW.versions?.engine,data:GROW.versions?.data,
  ...growthConditions()});}
function growthMetric(r,mode=MODE){if(mode!=='manual'||!r.man)return r;
  return {...r,clear:r.man.c,ttk:r.man.t,n:r.man.n??r.n,ci:r.man.ci,prog:r.man.prog,progs:r.man.progs};}
function growthJob(t,id,c=contents[$('content').value]){const bn=breakChoice(t.combo,c).name||null;
  return {id,t,party:simParty(t),options:{break_skill:bn?{name:bn,level:brkLv(bn)}:null},breakName:bn};}
function growthScoreEnv(env,fn){if(!env)return fn();const saved=[GIMACT,SBACT,DMW];
  try{GIMACT=env.gim;SBACT=env.season;DMW=env.damage;return fn();}
  finally{[GIMACT,SBACT,DMW]=saved;}}
function growthTeam(combo,profile,qi,defPen,env){const keys=combo.map(x=>x.s.key),ek=keys.slice(),[v,got]=growthScoreEnv(env,()=>teamValue(combo,defPen)),
  b={growth:1,power:null,...MyInfoReco.team(keys,profile,k=>k)},q=qi?Quick.evaluate(ek,qi.qs,QK.d.sv,D.pen,qi.prm,1,null,true,b.powers):
    {ok:false,rounds:Object.values(b.powers).reduce((a,v)=>a+v,0),left:0};
  return {combo,v,got,keys,ek,b,q,vd:q.ok?Quick.verdict(q):'hard',base:qi?.qs.bp};}
function growthQuickCmp(a,b){return QO[b.vd]-QO[a.vd]||(a.vd==='hard'?(b.q.rounds??0)-(a.q.rounds??0):(b.q.left??0)-(a.q.left??0))||
  (a.q.rounds??Infinity)-(b.q.rounds??Infinity)||b.v-a.v;}
async function growthCandidates(c,st,alive,deadline,config={}){const original=config.original||miProfile(),qi=Object.hasOwn(config,'qi')?config.qi:quickIn(c,st),restrict=(CFG.restrict[c.name]||{})[st.tab],
  defPen=CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty,
  owned=R.filter(s=>original.results[s.key]&&!EXCL.has(s.key)&&!config.banned?.has(s.key)&&(!restrict||s.el===restrict)),
  scored=s=>{const [v,parts]=growthScoreEnv(config.scoring,()=>score(s,st.w,c.main,c.boss));return {s,score:v,parts};},all=owned.map(scored),targets=[];
  for(const target of config.targets||growthTargets(c,st)){
    if(!alive())return [];
    const id=target.id||target.key+'|'+target.kind;
    if(Date.now()>=deadline){targets.push({...target,id,candidates:[],controls:[],limited:true});continue;}
    try{const assumed=config.profile?{changedFields:['level']}:MyInfoReco.assume(target.key,MI.info,MI.growth,{kind:target.kind,fields:target.fields});
      if(!assumed.changedFields.length&&!target.component)continue;
      const profile=config.profile||MyInfoReco.assumedProfile(original,assumed,MI.info,MI.growth,config.ruleContent||c.key),u=scored(BYKEY[target.key]);
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
      const makeJob=config.makeJob||((t,id)=>growthJob(t,id,c));
      const candidates=[...pick].map(([k,t])=>makeJob(t,id+'|'+k)),controls=[];
      for(const job of candidates){if(Date.now()>=deadline)break;const three=job.t.combo.filter(x=>x.s.key!==target.key);
        const choices=all.filter(x=>!three.some(y=>y.s.key===x.s.key)).map(x=>growthTeam([x,...three],original,qi,defPen,config.scoring));
        choices.sort((a,b)=>b.v-a.v);const quick=choices.slice().sort(growthQuickCmp);
        if(config.exactControls&&original.results[target.key])choices.unshift(growthTeam(job.t.combo,original,qi,defPen,config.scoring));
        for(const t of [choices[0],quick[0]])if(t)controls.push(makeJob(t,'owned|'+t.keys.slice().sort().join(',')));}
      targets.push({...target,...assumed,id,candidates,controls});
    }catch(e){targets.push({...target,id,error:String(e.message),errorCode:e.code,candidates:[],controls:[]});}
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
function growthMaybe(c,st){if(growthEnabled()&&growthSeasonContent()){growthPaint();return;}if(!growthEnabled()||!miMode()||!['op','clo'].includes(c.key)||!REQ)return;
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
function growthBadge(r,short=false){const missing=r.source==='assumed';return `<span class="assumed-label ${missing?'assumed-missing':'assumed-owned'}" data-k="assumed-badge"><span aria-hidden="true">${missing?'＋':'↑'}</span><span class="al-long">${esc(growthLabel(r))}</span><span class="al-short">${missing?'미보유':'보정'}</span>${!short&&growthDescription(r)?' · '+esc(growthDescription(r)):''}</span>`;}
function growthCardMeta(r){const before=miProfile().results[r.key],after=r.team?.t.b.finals[r.key];
  if(!after)return '';
  return `<div class="mi-chips"><span class="assumed-mark" title="전투력 ${miNum(before?.power)} → ${miNum(after.power)}">전투력 ${before?`${miNum(before.power)} → `:''}${miNum(after.power)}${before?'':' (가정)'}</span></div><details class="growth-stats"><summary>능력치 변화</summary>${['atk','hp','def','spd'].map((k,i)=>`<div>${['공','생','방','속'][i]} ${before?`${miNum(before.stats[k])} → `:''}${miNum(after.stats[k])}</div>`).join('')}</details>`;}
function growthPaint(){if(!growthEnabled())return;let el=$('growth-result');
  if(growthSeasonContent()){growthSeasonPaint();return;}
  if(!el){if(!['op','clo'].includes(contents[$('content').value]?.key)||!REQ)return;
    el=document.createElement('div');el.id='growth-result';el.className='party';$('out').append(el);}
  if(GROW.phase==='running'){el.innerHTML=`<b>육성 가이드</b><p role="status">${esc(GROW.msg)}</p><button class="sec" data-growth-cancel>가정 중단</button>`;
    el.querySelector('button').onclick=()=>{simInvalidate();GROW.phase='error';GROW.msg='중단함 · 미평가';growthPaint();};return;}
  if(!GROW.result){el.innerHTML=`<b>육성 가이드</b><p>${esc(GROW.msg||'보유 편성 확인 뒤 평가')}</p>`;return;}
  const r=GROW.result,rows=r.rows.filter(x=>!x.component).sort((a,b)=>(b.delta??-Infinity)-(a.delta??-Infinity)),fmt=v=>v==null?'—':(v>0?'+':'')+v.toFixed(1),
    metric=v=>v?`${(v.clear*100).toFixed(1)}% · 진행 ${((v.prog||0)*100).toFixed(1)}% · ${v.ttk==null?'—':v.ttk.toFixed(1)}턴 · ${v.n}판`:r.baselinePending?'기준 재평가 미완료':'기준 편성 없음';
  const status=x=>x.result?metric(x.result):x.errorCode==='level-data'?'자료 없음':x.status==='unsupported'?'자료 미지원':x.status==='screened'?'예선만 · 미평가':'미평가';
  const delta=x=>x.delta==null?'확인 부족':fmt(x.delta)+'%p'+(x.confirmed?' · 개선 확인':' · 확인 부족');
  const best=rows.find(x=>x.result);
  let cards='';if(best?.team){const ar=arrangeOf(best.team.t.combo);LEADKEY=ar.lead;
    cards=`<div data-k="growth-best"><span class="assumed-label">가정 포함</span><div class="rowcards">${ar.order.map((k,i)=>{
      const x=best.team.t.combo.find(x=>x.s.key===k);return card(x,i===0||i===3?'back':'front',null,k===best.key?best:null);
    }).join('')}</div><p class="mut">${esc(growthDescription(best))}</p><p>${best.result.ttk==null?'':best.result.ttk.toFixed(1)+'턴 · '}브레이크 ${esc(best.team.breakName||'없음')}</p></div>`;}
  const contributions=x=>{const parts=r.rows.filter(p=>p.parentId===x.id);return `<details data-k="growth-contributions"><summary>항목별 기여·평가 상세</summary><p class="mut">${status(x)} · 후보 ${x.screened}/2${x.ci?' · 95% 차이 구간 '+x.ci.map(fmt).join(' ~ ')+'%p':''}${x.error?' · '+esc(x.error):''}</p>${parts.length?'<p class="mut">각 항목만 바꾸고 다시 탐색 · 합산하지 않음</p>':''}${parts.map(p=>`<p data-component="${p.component}"><b>${growthParts[p.component]}</b> ${p.errorCode==='level-data'?'자료 없음':delta(p)}<br><span class="mut">${status(p)}${p.error?' · '+esc(p.error):''}${p.ci?' · 차이 구간 '+p.ci.map(fmt).join(' ~ ')+'%p':''}</span></p>`).join('')}</details>`;};
  const table=(list,extra=false)=>`<table data-k="${extra?'growth-more-table':'growth-table'}" class="growth-table"><thead><tr><th>구원자·목표</th><th>클리어 변화</th><th>상태</th></tr></thead><tbody>${list.map(x=>`<tr data-growth-key="${esc(x.id)}"><td><b>${esc(BYKEY[x.key]?.name||x.key)}</b> ${growthBadge(x,true)}${contributions(x)}</td><td>${x.result&&r.baseline?`${(r.baseline.clear*100).toFixed(1)}% → ${(x.result.clear*100).toFixed(1)}%`:'—'}</td><td>${x.errorCode==='level-data'?'자료 없음':delta(x)}</td></tr>`).join('')}</tbody></table>`;
  const top=rows.filter(x=>x.result).slice(0,5),rest=rows.filter(x=>!top.includes(x));
  const headline=best&&r.baseline&&best.delta>0?`${esc(BYKEY[best.key]?.name||best.key)} 키우면 · 클리어 ${(r.baseline.clear*100).toFixed(1)}% → ${(best.result.clear*100).toFixed(1)}%${best.confirmed?'':' · 확인 부족'}`:
    best&&!r.baseline?`${esc(BYKEY[best.key]?.name||best.key)} 육성 가정 · 클리어 ${(best.result.clear*100).toFixed(1)}% · 기준 확인 부족`:'개선이 확인된 육성 후보 없음';
  // Detach the live slot card before replacing the guide body (keep its handlers).
  const slot=$('star-link-result');if(slot?.parentElement===el)slot.remove();
  el.innerHTML=`<b data-k="growth-summary">${headline}</b>${GROW.errors.length?`<p class="bad" title="${esc(GROW.errors.join(' · '))}">일부 평가 실패 · 완료한 결과만 표시</p>`:''}<div data-k="growth-slot-summary"></div>${cards}
    <p class="mut">목표: 스타링크 Lv(상향만) · 장비 +15 · 스킬·공명 최대 · 여정·잠재력</p>${table(top)}${rest.length?`<details data-k="growth-more"><summary>나머지 ${rest.length}명 · 미평가 포함</summary>${table(rest,true)}</details>`:''}
    <details><summary>계산 정보</summary><p class="mut">보유 기준 ${metric(r.baseline)} · 묶음 평가 ${rows.filter(x=>x.result).length}/${rows.length}명 · ${(r.ms/1000).toFixed(1)}초 · 완료 ${r.runs}판</p></details>`;
  if(slot)el.querySelector('[data-k="growth-slot-summary"]').append(slot);
  const version=GROW.versions.engine+'|'+GROW.versions.data,history=MI.shared?GROW.history:LS.get('growth.history')||{},
    matching=Object.fromEntries(Object.entries(history).filter(([,v])=>v.account===MI.hash&&v.version===version)),priority=GrowthGuide.priority(matching,GROW.sig);
  el.insertAdjacentHTML('beforeend',`<details><summary>성능 개선 기준 육성 후보</summary>${priority.slice(0,12).map(x=>`<p>${esc(BYKEY[x.key]?.name||x.key)} · 묶음 · 개선 확인 ${x.count}콘텐츠<br><span class="mut">${x.contents.map(v=>`${esc(v.content)} ${v.delta==null?'미평가':fmt(v.delta)+esc(v.unit)}`).join(' · ')}</span></p>`).join('')}</details>`);
}

// Seasonal guides share the global simulator lock and at most three workers.
function growthSeasonContent(){const c=contents[$('content').value];return c?.key==='cosmo'||(c?.key==='guild'&&parseInt(cur?.[$('stage').value]?.name,10)===D.guild.steps.find(s=>s.ex)?.step)?c:null;}
function growthConditions(){return {
  season:[D.guild?.season,D.cosmoRaid?.season],
  difficulty:[D.guild?GuildView.normSel(D.guild,GS.sel||LS.get('guild.v2')):null,CSR.optLevel],
  support:[GSR.banCoop,CSR.optFast],ranking:['guild-top-cap-mean',CSR.optMode],
  teams:[GSR.rows,CSR.rows].map(rows=>rows.map(r=>r.teams?r.teams.map(t=>[t.keys,t.order,t.level,t.brk,t.brkLv]):[r.keys,r.order,r.sup,r.level])),
  equipment:[MI.hash,[...EXCL].sort()],
  policy:[GrowthGuide.VERSION,GrowthGuide.LIMITS,GrowthGuide.COSMO_LIMITS,17011,900001,27011]};}
function growthSeasonReady(c){return c.key==='guild'?GSR.phase==='done'&&GSR.context===growthOwnedContext('guild'):
  CSR.phase==='done'&&CSR.context===growthOwnedContext('cosmo');}
function growthOwnedContext(kind){return JSON.stringify([MI.hash,[...EXCL].sort(),kind==='guild'?[gsTiers(),GSR.banCoop]:[CSR.optLevel,CSR.optMode,CSR.optFast,csBreaks()],simOpt(kind)]);}
async function growthPhase(jobs,n,seed,c,st,id,deadline,prepare=r=>r){
  const results={};Object.defineProperty(results,'completed',{value:0,writable:true});
  if(!jobs.length||Date.now()>=deadline||GROW.id!==id)return results;
  const handle=GuildSearch.runPhase({makeWorker:()=>new Worker('sim_worker.js'),jobs:jobs.map(j=>({...j,key:j.id})),
    workers:Math.max(1,Math.min(3,(navigator.hardwareConcurrency||4)-1)),runs:n,seed,
    stage:c.key+'/'+st.tab+'/'+st.name,base:location.href.replace(/[?#].*$/,'').replace(/[^/]*$/,''),
    options:{...simOpt(c.key),rng_streams:true},
    onResult:(key,r)=>{if(GROW.id!==id)return;results.completed++;
      if(r.ver!==GROW.versions.engine){GROW.errors.push('엔진 버전 변경');return;}
      const value=prepare(r);if(value)results[key]=value;},
    onProgress:(done,total)=>{if(GROW.id===id){GROW.msg=`${n===100?'재평가':'후보 확인'} ${done}/${total} · ${n}판`;growthPaint();}}});
  const timer=setTimeout(()=>handle.cancel(),Math.max(1,deadline-Date.now()));GROW.stop=()=>handle.cancel();
  try{await handle.promise;}catch(e){if(e.message!=='취소')GROW.errors.push(e.message);}
  finally{clearTimeout(timer);if(GROW.id===id)GROW.stop=null;}
  return results;
}
function growthSeasonJob(t,id,options,bossIndex){
  const p=GuildSearch.party(t.keys,t.b.finals,Object.fromEntries(R.map(s=>[s.key,s.cls])));
  return {id,t,keys:t.keys,order:p.order,party:p.spec,options,bossIndex};
}
async function growthGuild(c,st,id,deadline){
  const alive=()=>GROW.id===id,sel=GuildView.normSel(D.guild,GS.sel||LS.get('guild.v2')),
    S={...D.guild.search,banCoop:GSR.banCoop},profile=MyInfoReco.profile(MI.info,R,MI.growth,'op'),
    cls=Object.fromEntries(R.map(s=>[s.key,s.cls])),metric=GrowthGuide.guildMetric(GuildSearch,GuildView,D.guild,sel.level,sel.tiers),
    prepare=r=>GuildSearch.coopHit(S,r)?null:metric.prepare(r),qi=quickIn(c,st),scoring={gim:gimTop(c,st),season:st.sb||[],damage:[Math.min(1,(st.n-1)/2),CFG.damage.weightBoss]};
  const team=keys=>growthTeam(keys.map(k=>({s:BYKEY[k],score:0})),profile,qi,CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty,scoring);
  const reference=GSR.rows[0];if(!reference)throw Error('보유 기준 편성 없음');
  const options=support=>({guild:{level:sel.level,sets:sel.tiers.slice(),support}});
  const supportJobs=GuildSearch.finalSupports(S,reference.keys,cls).map(sup=>growthSeasonJob(team(reference.keys),'support|'+sup,options(sup)));
  const supportRes=await growthPhase(supportJobs,100,900001,c,st,id,deadline,prepare);
  if(!alive())return null;
  if(supportRes.completed!==supportJobs.length)throw Error('보유 지원 확인 미완료 · 다시 실행');
  const supportJob=supportJobs.filter(j=>supportRes[j.id]).sort((a,b)=>metric.rank(supportRes[a.id],supportRes[b.id]))[0];
  if(!supportJob)throw Error('현재 조건에서 사용 가능한 보유 기준 지원 없음');
  const support=supportJob.options.guild.support;
  const makeJob=(t,key)=>growthSeasonJob(t,key,options(support)),banned=new Set(S.banCoop===false?[]:S.excluded||[]);
  const targets=await growthCandidates(c,st,alive,deadline,{original:profile,qi,scoring,banned,makeJob,ruleContent:'op',
    targets:growthTargets(c,st).filter(t=>!banned.has(t.key))});
  const owned=GSR.rows.map(r=>{const j=makeJob(team(r.keys),'owned|'+r.keys.slice().sort().join(','));
    return {...j,result:r===reference?supportRes[supportJob.id]:null};});
  const result=await GrowthGuide.search({targets,owned,metric,mode:'auto',alive,
    limits:{maxRuns:7200-supportJobs.length*100,maxMs:Math.max(0,deadline-Date.now())},
    evaluate:(jobs,n,seed)=>growthPhase(jobs,n,seed,c,st,id,deadline,prepare)});
  if(result){result.runs+=supportJobs.length*100;result.scope.maxRuns=7200;result.metric='guild-top20';result.unit='점';
    result.conditions={season:D.guild.season,level:sel.level,tiers:sel.tiers,support,ranking:'top20-cap-mean',mode:'auto'};}
  return result;
}
async function growthCosmo(c,st,id,deadline){
  const alive=()=>GROW.id===id,C=D.cosmoRaid,S=C.search,bosses=C.bosses.map(b=>b.key),profile=csProfile(),cls=Object.fromEntries(R.map(s=>[s.key,s.cls])),
    reference=CSR.rows[0];if(!reference)throw Error('보유 3팀 기준 없음');
  const owned=[[],[],[]],established=[],targets=new Map();
  const conditions=reference.teams.map(t=>({boss:t.boss,level:t.level,brk:t.brk?{name:t.brk,level:t.brkLv}:null}));
  for(let i=0;i<3;i++){
    const boss=bosses[i],cond=conditions.find(x=>x.boss===boss),meta=C.bosses[i],existing=c.stages.find(s=>s.tab===meta.name&&s.name.endsWith('3단계')),
      bst=existing||{...st,tab:meta.name,name:meta.name+' 3단계',w:{[Object.keys(EL).find(k=>EL[k]===meta.element)]:2},n:1,sb:[]},
      qi=existing?quickIn(c,bst):null,scoring={gim:existing?gimTop(c,bst):[],season:bst.sb||[],damage:[Math.min(1,(bst.n-1)/2),CFG.damage.weightBoss]};
    const options={cosmo_raid:{boss,step:3,level:cond.level},cosmo_top_q:S.topQ,break_skill:cond.brk};
    const makeJob=(t,key)=>({...growthSeasonJob(t,boss+'|'+key,options,i),boss});
    const rows=(CSR.growthOwned||[]).filter(j=>j.boss===boss),res=Object.fromEntries(rows.map(j=>[j.key,j.result]));
    const diverse=CosmoSearch.pickDiverse(rows,res,CSR.optMode,8);
    const keys=new Map([...CSR.rows.flatMap(r=>r.teams.filter(t=>t.boss===boss)),...diverse].map(t=>[CosmoSearch.idOf(t.keys),t.keys]));
    for(const ks of keys.values()){
      const p=GuildSearch.party(ks,profile.results,cls),job={id:boss+'|owned|'+ks.slice().sort().join(','),keys:ks,order:p.order,party:p.spec,options,boss,bossIndex:i};
      owned[i].push(job);if(CosmoSearch.idOf(ks)===CosmoSearch.idOf(reference.teams.find(t=>t.boss===boss).keys))established.push(job);
    }
    const generated=await growthCandidates(c,bst,alive,deadline,{original:profile,qi,scoring,makeJob,exactControls:true});
    for(const t of generated){if(!targets.has(t.id))targets.set(t.id,{...t,candidates:[],controls:[]});
      const row=targets.get(t.id);row.candidates.push(...t.candidates);row.controls.push(...t.controls);}
  }
  for(const t of targets.values()){const lists=bosses.map((_,i)=>t.candidates.filter(j=>j.bossIndex===i));
    t.candidates=[0,1].flatMap(i=>lists.map(list=>list[i]).filter(Boolean));}
  const result=await GrowthGuide.searchCosmo({CS:CosmoSearch,targets:[...targets.values()],owned,established,mode:CSR.optMode,alive,
    limits:{maxMs:Math.max(0,deadline-Date.now())},evaluate:(jobs,n,seed)=>growthPhase(jobs,n,seed,c,st,id,deadline)});
  if(result)result.conditions={season:C.season,requestedLevel:CSR.optLevel,bosses:conditions,ranking:CSR.optMode,mode:'auto'};
  return result;
}
async function growthSeasonStart(){const c=growthSeasonContent(),st=cur?.[$('stage').value];
  if(!c||!MI.growth||!QK.d||!growthSeasonReady(c)||SIMQ.busy!=null||GSR.phase==='run'||CSR.phase==='run')return;
  growthCancel();const id=++GROW.id;SIMQ.busy='growth';GROW.phase='running';GROW.msg='육성 후보 준비';growthPaint();
  const started=Date.now(),L=c.key==='guild'?GrowthGuide.LIMITS:GrowthGuide.COSMO_LIMITS,deadline=started+L.maxMs;
  try{const manifest=await fetch('sim/manifest.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('엔진 확인 실패');return r.json();});
    if(GROW.id!==id)return;GROW.versions={engine:manifest.ver,data:MyInfoReco.hash([GrowthGuide.VERSION,MI.growth,D,QK.d])};
    GROW.sig=growthSig(c,st);
    const result=await (c.key==='guild'?growthGuild: growthCosmo)(c,st,id,deadline);
    if(GROW.id!==id||!result)return;
    if(GROW.sig!==growthSig(c,st)){growthCancel();return;}
    result.ms=Date.now()-started;result.scope.maxMs=L.maxMs;GROW.result=result;GROW.phase='done';
    const content=c.key+'/'+(c.key==='cosmo'?D.cosmoRaid.season:st.tab+'/'+st.name),entry=GrowthGuide.summary(result,content,GROW.sig,MI.hash,GROW.versions.engine+'|'+GROW.versions.data);
    if(MI.shared)GROW.history[content]=entry;else GrowthGuide.save(LS,false,entry);
  }catch(e){if(GROW.id===id){GROW.phase='error';GROW.msg=e.message;}}
  finally{if(GROW.id===id){SIMQ.busy=null;growthPaint();}}
}
function growthSeasonPaint(){const c=growthSeasonContent();if(!c||!growthEnabled()||!MI.info)return;
  let el=$('growth-result');if(!el){el=document.createElement('div');el.id='growth-result';el.className='party';$('out').append(el);}
  const head=`<b>육성 가이드 · ${c.key==='guild'?'길방':'코스모'}</b>`;
  if(GROW.phase==='running'){el.innerHTML=head+`<p role="status">${esc(GROW.msg)}</p><button data-growth-stop>중단</button>`;
    el.querySelector('button').onclick=()=>{growthCancel();GROW.msg='중단함 · 미평가';growthPaint();};return;}
  if(GROW.sig&&GROW.sig!==growthSig(c,cur[$('stage').value]))growthCancel();
  const ready=growthSeasonReady(c),result=GROW.result,fmt=v=>v==null?'—':Math.round(v).toLocaleString(),num=r=>c.key==='guild'?r?.top:r?.sum;
  const rows=(result?.rows||[]).filter(r=>!r.component).sort((a,b)=>(b.delta??-Infinity)-(a.delta??-Infinity));
  const show=r=>`<article class="growth-score-card" data-k="growth-${c.key}-card"><b>${esc(BYKEY[r.key]?.name||r.key)}</b> ${growthBadge(r,true)}
    <p><span class="tag">${c.key==='guild'?'상위 20%':'3팀 합산'}</span> ${fmt(num(result.baseline))} → ${fmt(num(r.result))}점</p>
    <b>${r.delta==null?'미평가':(r.delta>0?'+':'')+fmt(r.delta)+'점'}${r.confirmed?' · 개선 확인':''}</b>
    ${c.key==='guild'&&r.result?`<p class="mut">상한 ${Math.round(result.baseline?.cap*100||0)}% → ${Math.round(r.result.cap*100)}% · 평균 ${fmt(result.baseline?.mean)} → ${fmt(r.result.mean)}</p>`:''}
    ${r.ci?`<p class="mut">95% 차이 ${r.ci.map(fmt).join(' ~ ')}점</p>`:''}
    <p class="mut">${r.team?(c.key==='guild'?r.team.order.map(k=>esc(BYKEY[k]?.name||k)).join(' · '):r.team.teams.map(t=>esc(csBoss(t.boss))+': '+t.order.map(k=>esc(BYKEY[k]?.name||k)).join(' · ')).join('<br>')):esc(r.error||'확인 부족')}</p></article>`;
  const conditions=result?.conditions;
  el.innerHTML=head+` <button data-growth-start ${ready&&SIMQ.busy==null?'':'disabled'}>육성 비교</button>`+
    `<p>${result?'현재 조건에서의 개선':esc(GROW.msg||(ready?'보유 기준 준비됨':'먼저 보유 최고 편성 찾기'))}</p>`+
    (conditions?`<p class="mut">${c.key==='guild'?conditions.level+'단계 · '+esc(GuildSearch.SUP_NAME[conditions.support]||conditions.support):conditions.bosses.map(b=>esc(csBoss(b.boss))+' '+b.level+'단계').join(' · ')} · 오토</p>`:'')+
    rows.filter(r=>r.result).slice(0,5).map(show).join('')+
    `<details data-k="growth-score-details"><summary>평가 상세</summary><p class="mut">${c.key==='guild'?'보유 기준팀의 최선 지원 고정 · 평균·상한 예선 후 별도 시드 100판 · 부트스트랩 차이 구간':'가정자 한 보스씩 · 보유 중복 없이 재결합 · 보유 최선 3팀과 비교 · 기준팀 난이도·브레이크 고정'}. 제한 탐색 · 오토 기준 · 전역 최적 보장 없음.</p>`+
    (result?`<p class="mut">완료 ${result.runs}판 · ${(result.ms/1000).toFixed(1)}초${result.baselinePending?' · 기준 재평가 미완료':''}${GROW.errors.length?' · 일부 평가 실패':''}</p>`:'')+
    rows.filter(r=>!rows.filter(x=>x.result).slice(0,5).includes(r)).map(show).join('')+
    (result?.rows||[]).filter(r=>r.component).map(r=>`<p>${esc(BYKEY[r.key]?.name||r.key)} · ${growthParts[r.component]} ${r.delta==null?'미평가':fmt(r.delta)+'점'}</p>`).join('')+'</details>';
  el.querySelector('[data-growth-start]').onclick=growthSeasonStart;
}
