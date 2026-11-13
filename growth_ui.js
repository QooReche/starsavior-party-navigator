// Page integration. Uses the existing SIMQ workers, never a second worker budget.
const GROW={id:0,phase:'idle',result:null,sig:null,msg:'',stop:null,versions:null,history:{},errors:[]};
let growthTabs=null;
function growthOptions(){return {growth:!!document.getElementById('assume-growth')?.checked,
  owned:false};}
function growthCacheTag(){return JSON.stringify(['current-account',MyInfoReco.OVERWRITE_VERSION,MyInfoReco.THRESHOLD_POLICY,growthOptions(),MI.growth?.assumed?.version]);}
function growthEnabled(){const o=growthOptions();return o.growth;}
// Keep one live checkbox while the recommendation body is replaced.
function growthControlPlace(home=false){const seasonal=['guild','cosmo'].includes(contents[$('content').value]?.key);
  const target=!home&&!seasonal&&!$('out').hidden&&$('reco-actions');
  (target||$('growth-control-home')).append($('growth-control'));}
function growthControls(){const enabled=!!MI.info&&growthEnabled(),details=$('growth-settings');
  $('assume-growth').disabled=!MI.info;$('growth-requires-info').hidden=!!MI.info;
  if(!enabled)details.open=false;
  details.dataset.enabled=String(enabled);
  $('growth-settings-summary').textContent='육성 설정 · '+(!MI.info?'내 정보 필요':!enabled?'꺼짐':'보유만');
  growthRankPaint();}
function growthCancel(){growthTabs?.reset();if(typeof slotCancel==='function')slotCancel();GROW.id++;if(GROW.stop)GROW.stop();GROW.stop=null;
  document.getElementById('growth-result')?.remove();
  if(typeof SIMQ!=='undefined'&&SIMQ.busy==='growth')SIMQ.busy=null;
  GROW.phase='idle';GROW.result=null;GROW.sig=null;GROW.msg='';GROW.errors=[];GROW.recordTag=null;}
function growthInit(){const o=GrowthGuide.options(LS.get('growth.options')||{},SHARE);
  $('assume-growth').checked=o.growth;
  $('assume-growth').setAttribute('aria-describedby','growth-hint');
  growthControls();
  $('assume-growth').onchange=()=>{
    if(!MI.shared)LS.set('growth.options',growthOptions());condChanged();};}
function growthTargets(c,st){const opts=growthOptions(),restrict=(CFG.restrict[c.name]||{})[st.tab],owned=(c.key==='guild'?MyInfoReco.profile(MI.info,R,MI.growth,'op'):miProfile()).units;
  const targets=[];for(const s of R){if(EXCL.has(s.key)||(restrict&&s.el!==restrict))continue;
    if(opts.growth&&owned[s.key]){
      const t={key:s.key,kind:'growth',source:'owned',id:s.key+'|growth'};targets.push(t);
    }}return targets;}
function growthSig(c,st,versions=GROW.versions){return GrowthGuide.signature({account:MI.hash,options:growthOptions(),targets:growthTargets(c,st),
  preset:MI.growth?.assumed?.version,content:[c.key,...(c.key==='cosmo'?[]:[st.tab,st.name]),growthConditions(c)],excluded:[...EXCL],breaks:[breakOwned(),MI.info?.break_skills],
  modifiers:[MM,SCROWN],rules:SIMOPT,engine:versions?.engine,data:versions?.data,
  equipment:[MI.hash,[...EXCL].sort()],
  policy:[MyInfoReco.OVERWRITE_VERSION,MyInfoReco.THRESHOLD_POLICY,GrowthGuide.VERSION,GrowthGuide.LIMITS,GrowthGuide.COSMO_LIMITS,17011,900001,27011]});}
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
      const candidates=[...pick].map(([k,t])=>makeJob(t,id+'|'+k)),controls=[];let controlsComplete=true;
      for(const job of candidates){if(Date.now()>=deadline){controlsComplete=false;break;}const three=job.t.combo.filter(x=>x.s.key!==target.key);
        const choices=all.filter(x=>!three.some(y=>y.s.key===x.s.key)).map(x=>growthTeam([x,...three],original,qi,defPen,config.scoring));
        choices.sort((a,b)=>b.v-a.v);const quick=choices.slice().sort(growthQuickCmp);
        if(config.exactControls&&original.results[target.key])choices.unshift(growthTeam(job.t.combo,original,qi,defPen,config.scoring));
        if(!choices.length)controlsComplete=false;
        for(const t of [choices[0],quick[0]])if(t)controls.push(makeJob(t,'owned|'+t.keys.slice().sort().join(',')));}
      targets.push({...target,...assumed,id,candidates,controls,controlsComplete});
    }catch(e){targets.push({...target,id,error:String(e.message),errorCode:e.code,candidates:[],controls:[]});}
    if(!config.profile){GROW.msg=`육성 후보 준비 ${targets.length}건`;growthPaint();}await new Promise(ok=>setTimeout(ok,0));
  }return targets;}
function growthEvaluate(jobs,n,seed,c,st,id,deadline,env={}){const state=env.state||GROW,mode=env.mode||MODE,paint=env.paint||growthPaint;return new Promise(resolve=>{
  const results={};if(!jobs.length||Date.now()>=deadline||GROW.id!==id||state.errors.length){resolve(results);return;}
  if(!SIMQ.w){SIMQ.w=new Worker('sim_worker.js');SIMQ.loaded=false;}
  const workers=scrPool(),parts=workers.map(()=>[]),request=SIMQ.requestId=(SIMQ.requestId||0)+1;
  jobs.forEach((j,i)=>parts[i%workers.length].push(j));let open=parts.filter(p=>p.length).length,done=false;
  const finish=cut=>{if(done)return;done=true;clearTimeout(timer);state.stop=null;
    if(cut)Object.defineProperty(results,'incomplete',{value:true});
    if(cut){for(const w of workers)w?.terminate();SIMQ.w=null;SIMQ.loaded=false;SIMQ.pool=null;}
    resolve(results);};
  let timer;
  const arm=()=>{clearTimeout(timer);const due=env.screenClock?(env.screenClock.deadline??Date.now()+SIMQ.LOAD_MS):deadline;
    timer=setTimeout(()=>finish(true),Math.max(1,due-Date.now()));};
  const ready=()=>{if(env.screenClock&&!env.screenClock.deadline&&workers.every((w,i)=>!parts[i].length||w._ready)){
    env.screenClock.deadline=Date.now()+SCR_MS;arm();}};
  arm();ready();state.stop=()=>finish(true);
  for(const [i,w] of workers.entries()){
    if(!parts[i].length)continue;
    w.onmessage=e=>{const m=e.data;if(GROW.id!==id||SIMQ.requestId!==request||(m.id!=null&&m.id!==request))return;
      if(m.type==='stage'){if(m.msg==='준비 끝'){SIMQ.loaded=true;w._ready=true;ready();}return;}
      if(m.type==='team'){if(m.result.ver!==GROW.versions.engine){state.errors.push('엔진 버전이 바뀜 · 다시 실행');finish(true);return;}
        results[m.key]=growthMetric({...m.result,n},mode);state.msg=`${seed===900001?'재평가':'후보 확인'} ${Object.keys(results).length}/${jobs.length} · ${n}판`;paint();}
      if(m.type==='done'&&--open===0)finish(false);
      if(m.type==='error'){state.errors.push('육성 모의 전투 오류: '+m.msg);finish(true);}};
    w.onerror=e=>{state.errors.push('가정 작업자 오류: '+e.message);finish(true);};
    w.postMessage({type:'run',id:request,base:location.href.replace(/[?#].*$/,'').replace(/[^/]*$/,''),
      stage:c.key+'/'+st.tab+'/'+st.name,n_runs:n,seed,mode:env.final||seed===900001?mode:'auto',options:{...(env.options||simOpt(c.key)),rng_streams:true},
      teams:parts[i].map(j=>({key:j.id,party:j.party,options:j.options}))});
  }
});}
function growthMaybe(c,st){if(growthEnabled()&&growthSeasonContent()){growthPaint();return;}if(!growthEnabled()||!miMode()||!['op','clo'].includes(c.key)||!REQ)return;
  if(GROW.sig&&GROW.sig!==growthSig(c,st))growthCancel();
  if(GROW.phase==='idle'&&SIMQ.busy==null&&!SIMQ.err&&simAutoOn()){const id=GROW.id;
    setTimeout(()=>{if(GROW.id===id&&REQ&&GROW.phase==='idle')growthStart(c,st);},0);}
  growthPaint();}
const growthLabel=r=>'키워야 함';
const growthFields={level:'레벨→스타링크',resonance:'공명 최대',skills:'스킬 최대',journey:'목표 스텔라 아카이브',potentials:'목표 잠재력',equip:'장비 +15',favor:'호감도'};
const growthShortFields={level:'스타링크',equip:'장비',skills:'스킬',resonance:'공명',journey:'스텔라 아카이브',potentials:'잠재력',favor:'호감도'};
function growthDescription(r){if(r.source==='assumed')return '';return (r.changedFields||[]).map(f=>{
  const c=r.changes?.[f];if(f==='level'&&c)return `${c.before==null?'Lv ':('Lv '+c.before+'→')}스타링크`;
  if(f==='resonance'&&c)return `공명 ${c.before??0}→${c.after}`;
  return growthFields[f];}).join(' · ');}
function growthBadge(r,short=false){if(r.source!=='owned')return '';return `<span class="assumed-label assumed-owned" data-k="assumed-badge"><span aria-hidden="true">↑</span><span class="al-long">${esc(growthLabel(r))}</span><span class="al-short">키워야 함</span>${!short&&growthDescription(r)?' · '+esc(growthDescription(r)):''}</span>`;}
function growthCardMeta(r){if(r.source!=='owned')return '';if(r.overwrite)return Ux.memberHtml(growthDisplay(r),false);const before=miProfile().results[r.key],after=r.team?.t.b.finals[r.key];
  if(!after)return '';
  return `<div class="mi-chips"><span class="assumed-mark" title="전투력 ${miNum(before?.power)} → ${miNum(after.power)}">전투력 ${before?`${miNum(before.power)} → `:''}${miNum(after.power)}${before?'':' (가정)'}</span></div><details class="growth-stats"><summary>능력치 변화</summary>${['atk','hp','def','spd'].map((k,i)=>`<div>${['공','생','방','속'][i]} ${before?`${miNum(before.stats[k])} → `:''}${miNum(after.stats[k])}</div>`).join('')}</details>`;}
const growthDisplays=new WeakMap();
function growthTodoRow(r,name){if(r.source!=='owned')return '';const chips=Ux.todosHtml(growthDisplay(r));return chips?`<div class="growth-task-row" data-key="${esc(r.key)}"><b>${esc(name)}</b><div class="growth-todos">${chips}</div></div>`:'';}
function growthDisplay(a){const c=contents[$('content').value].key,content=c==='guild'?'op':c;
  let cached=growthDisplays.get(a);if(!cached||cached.content!==content||cached.info!==MI.info){cached={content,info:MI.info,value:Ux.member(a,MI.info,MI.growth,content,D.archiveGrades,D.growthView)};growthDisplays.set(a,cached);}return cached.value;}
// Seasonal passes share the lock and each content's existing worker budget.
function growthSeasonContent(){const c=contents[$('content').value];return c?.key==='cosmo'||(c?.key==='guild'&&parseInt(cur?.[$('stage').value]?.name,10)===D.guild.steps.find(s=>s.ex)?.step)?c:null;}
function growthConditions(c,trackTeams=true){const rules=simOpt(c.key);
  if(c.key==='guild')return {rules,season:D.guild?.season,
    difficulty:GuildView.normSel(D.guild,GS.sel||LS.get('guild.v2')),banCoop:GSR.banCoop,ranking:'guild-top-cap-mean',breakCheck:GuildSearch.breakSignature(ownedSimBreaks()),
    teams:GSR.rows.map(r=>[r.keys,r.order,r.sup,r.level,r.brk,r.brkLv])};
  if(c.key==='cosmo')return {rules,season:D.cosmoRaid?.season,
    difficulty:CSR.optLevel,fast:CSR.optFast,ranking:CSR.optMode,
    teams:CSR.rows.map(r=>Array.isArray(r?.teams)?r.teams.map(t=>[t?.boss,t?.keys,t?.order,t?.level,t?.brk,t?.brkLv]):[])};
  const prefix=c.key+'|',shared=typeof SHARE!=='undefined'&&Object.hasOwn(SHARE,'b');
  const selected=shared?SESSION_BR:BRSEL;
  const teams=!trackTeams||typeof LASTQ==='undefined'?null:(LASTQ[1]?.rows||[]).map(t=>prefix+t.keys.slice().sort().join(','));
  const breaks=Object.fromEntries(Object.entries(selected).filter(([k])=>k.startsWith(prefix)&&(!teams?.length||teams.includes(k))).sort(([a],[b])=>a.localeCompare(b)));
  if(shared&&teams)for(const k of teams)breaks[k]??=SHARE.b;
  return {rules,mode:MODE,breaks:[breaks,{}],...(shared?{breakDefault:SHARE.b}:{}),...(teams?.length?{breakTeams:teams}:{})};}
function growthPriority(history){return GrowthGuide.priority(history,GROW.sig,
  Object.fromEntries(contents.map(c=>[c.key,growthConditions(c,false)])));}
function growthMembers(r){const keys=r.kind==='cosmo'?r.best?.teams.flatMap(t=>t.keys||t.order):r.kind==='guild'?r.best?.keys||r.best?.order:r.team?.t.keys;
  return [...new Set(keys||[])].map(key=>r.snapshot.changes[key]).filter(a=>a?.changedFields.length);}
function growthRecord(c,st,r,show){if(!r?.snapshot||r.kind!==c.key||!GROW.sig)return;
  const field=c.key==='guild'?'score':c.key==='cosmo'?'sum':'clear',scale=field==='clear'?100:1;
  const members=show?growthMembers(r):[],delta=show?scale*(r.best[field]-(r.baseline?.[field]||0)):0;
  const entry=GrowthGuide.grownSummary({content:c.key==='cosmo'?'cosmo/'+D.cosmoRaid.season:c.key+'/'+st.tab+'/'+st.name,
    signature:GROW.sig,account:MI.hash,version:MyInfoReco.OVERWRITE_VERSION,members,delta,
    metric:c.key==='guild'?'guild-top':c.key==='cosmo'?'cosmo-'+CSR.optMode:'clear',unit:field==='clear'?'%p':'점'});
  const tag=JSON.stringify({...entry,at:0});if(GROW.recordTag===tag)return;GROW.recordTag=tag;
  const key=JSON.stringify([entry.historyVersion,entry.content,entry.signature]);GROW.history[key]=entry;
  GrowthGuide.save(LS,MI.shared,entry);growthRankPaint();
}
function growthRankPaint(){const el=$('growth-priority');if(!el)return;
  el.hidden=true;
  if(!MI.info||!MI.growth||!QK.d||!growthEnabled())return;
  const history=MI.shared?GROW.history:{...(LS.get('growth.history')||{}),...GROW.history};
  if(!Object.values(history).some(h=>h.historyVersion===GrowthGuide.HISTORY_VERSION))return;
  // Reload must check the current engine, rather than trust the engine saved in a summary.
  if(!GROW.historyEngine){if(!GROW.historyLoading){GROW.historyLoading=true;
    fetch('sim/manifest.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('engine');return r.json();})
      .then(m=>{GROW.historyEngine=m.ver;growthRankPaint();}).catch(()=>{}).finally(()=>{GROW.historyLoading=false;});}return;}
  const c=contents[$('content').value],st=cur[$('stage').value];if(!c||!st)return;
  const versions={engine:GROW.historyEngine,data:MyInfoReco.hash([GrowthGuide.VERSION,MI.growth,D,QK.d])};
  const activeHistory=Object.fromEntries(Object.entries(history).filter(([,h])=>!seasonBlocked(h.content?.split('/')[0])));
  const rows=GrowthGuide.grownPriority(activeHistory,growthSig(c,st,versions),
    Object.fromEntries(contents.map(c=>[c.key,growthConditions(c,false)])));
  if(!rows.length)return;
  const row=r=>`<div class="growth-rank-row" data-k="growth-rank-row"><b>${esc(BYKEY[r.key]?.name||r.key)}</b> `+
    `<span class="tag">${r.count}개 콘텐츠</span>`+
    `<div class="mi-chips">${r.changedFields.map(f=>`<span class="tag">${esc(growthShortFields[f]||f)}</span>`).join('')}</div></div>`;
  const ordered=rows.filter(r=>r.source==='owned');
  el.hidden=false;el.innerHTML='<b>키울 만한 구원자</b>'+ordered.slice(0,5).map(row).join('')+
    `<details><summary>${ordered.length>5?'나머지 '+(ordered.length-5)+'명 · ':''}상세</summary>`+
    ordered.slice(5).map(row).join('')+'<p class="mut">보조 추천에 나온 콘텐츠 종류 수 · 함께 키운 팀 기준</p></details>';
}
function growthSeasonReady(c){return c.key==='guild'?GSR.phase==='done'&&GSR.context===growthOwnedContext('guild'):
  CSR.phase==='done'&&CSR.context===growthOwnedContext('cosmo');}
function growthOwnedContext(kind){return JSON.stringify([MI.hash,[...EXCL].sort(),kind==='guild'?[gsTiers(),GSR.banCoop,GuildSearch.breakSignature(ownedSimBreaks())]:[CSR.optLevel,CSR.optMode,CSR.optFast,csBreaks()],simOpt(kind)]);}
// Whole-account pass: the owned recommendation and its caches remain untouched.
function growthBetter(kind,baseline,result){
  const metric=r=>kind==='guild'?r?.score:kind==='cosmo'?r?.sum:r?.clear;
  return Number.isFinite(metric(result))&&metric(result)>(metric(baseline)??0);
}
// Same load/idle limits as the normal stage simulator, per seasonal worker.
function growthWorker(){
  const raw=new Worker('sim_worker.js');let timer=null,ready=false,runs=1;
  const wrapper={onmessage:null,onerror:null,postMessage(message){runs=message.n_runs;arm();raw.postMessage(message);},
    terminate(){clearTimeout(timer);raw.terminate();}};
  function arm(){clearTimeout(timer);timer=setTimeout(()=>wrapper.onerror?.({message:'시간 초과'}),ready?simTeamLimit(runs,'auto'):SIMQ.LOAD_MS);}
  raw.onmessage=e=>{if(e.data.type==='done'||e.data.type==='error')clearTimeout(timer);
    else {if(e.data.msg==='준비 끝'||e.data.type==='team')ready=true;arm();}wrapper.onmessage?.(e);};
  raw.onerror=e=>{clearTimeout(timer);wrapper.onerror?.(e);};return wrapper;
}
async function growthStageSearch(c,st,profile,id){
  const restrict=(CFG.restrict[c.name]||{})[st.tab],qi=quickIn(c,st);
  if(!qi)throw Error('빠른 계산 자료 없음');
  const candidates=R.filter(s=>profile.results[s.key]&&!EXCL.has(s.key)&&(!restrict||s.el===restrict))
    .map(s=>{const [scoreValue,parts]=score(s,st.w,c.main,c.boss);return {s,score:scoreValue,parts};});
  if(candidates.length<4)return {best:null,runs:0};
  const defPen=CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty;
  const all=quickRank(rankAll(candidates,defPen),qi,profile),key=t=>t.keys.slice().sort().join(','),by=new Map(all.map(t=>[key(t),t]));
  const selected=new Map(),first=SCR_ROUNDS[0];
  all.slice(0,first.q).forEach(t=>selected.set(key(t),t));
  all.slice().sort((a,b)=>b.v-a.v).slice(0,first.v).forEach(t=>selected.set(key(t),t));
  let keys=[...selected.keys()],runs=0;const screenClock={deadline:null};
  const evaluate=async(list,n,deadline,final=false)=>{
    if(GROW.id!==id)throw Error('취소');
    const jobs=list.map(k=>growthJob(by.get(k),k,c));
    const r=await growthEvaluate(jobs,n,SIMQ.seed,c,st,id,deadline,{final,mode:final?MODE:'auto',...(!final?{screenClock}:{})});
    runs+=Object.keys(r).length*(final?GrowthGuide.finalCost(n,MODE):n);
    if(GROW.id!==id||r.incomplete||Object.keys(r).length!==jobs.length)throw Error('미완료');
    return r;
  };
  if(keys.length>3){
    const deadline=Infinity; // Preparation has its own LOAD_MS; screening starts when workers are ready.
    for(const round of SCR_ROUNDS){
      if(round.top)keys=keys.slice(0,round.top);
      const r=await evaluate(keys,round.n,deadline);
      keys.sort((a,b)=>scrCmp(r[a],r[b]));
      if(keys.length<=3)break;
    }
  }
  // The same 3-at-a-time, at most 9, >=50% stop rule as simAutoKick.
  let best=null,bestJob=null;
  for(let i=0;i<Math.min(9,keys.length);i+=3){
    const batch=keys.slice(i,i+3),r=await evaluate(batch,SIMQ.n,
      Date.now()+Math.max(SIMQ.LOAD_MS,batch.length*simTeamLimit(SIMQ.n,MODE)),true);
    for(const k of batch)if(!best||scrCmp(r[k],best)<0){best=r[k];bestJob=growthJob(by.get(k),k,c);}
    if(best?.clear>=.5)break;
  }
  return {best,team:bestJob,runs};
}
async function growthStart(c,st){
  if(seasonBlocked(c.key))return;
  if(!growthEnabled()||GROW.phase==='running'||SIMQ.busy!=null||GSR.phase==='run'||CSR.phase==='run'||!MI.growth||!QK.d)return;
  const seasonal=['guild','cosmo'].includes(c.key);
  if(seasonal&&!growthSeasonReady(c))return;
  const id=++GROW.id;GROW.phase='running';GROW.msg='육성 계획 탐색';GROW.errors=[];SIMQ.busy='growth';growthPaint();
  try{
    const manifest=await fetch('sim/manifest.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('엔진 확인 실패');return r.json();});
    if(GROW.id!==id)return;
    GROW.versions={engine:manifest.ver,data:MyInfoReco.hash([GrowthGuide.VERSION,MI.growth,D,QK.d])};GROW.historyEngine=manifest.ver;GROW.sig=growthSig(c,st);
    const slots=await fetch('data/myinfo_slots.json').then(r=>{if(!r.ok)throw Error('장비 부위 확인 실패');return r.json();});
    if(GROW.id!==id)return;
    const snapshot=MyInfoReco.overwrite(MI.info,R,MI.growth,c.key==='guild'?'op':c.key,
      {excluded:[...EXCL],slots});
    const started=Date.now();let result,baseline;
    if(seasonal){
      const owned=c.key==='guild'?GSR:CSR;
      baseline=owned.rows[0]||null;
      const state={...owned,id:0,phase:'idle',rows:[],handle:null};
      GROW.stop=()=>{state.id++;state.handle?.cancel();};
      // Existing search functions own their phase deadlines and worker-count policy.
      const out=await (c.key==='guild'?guildSearchStart:cosmoSearchStart)(state,snapshot.profile);
      if(!out||out.phase!=='done')throw Error('미완료');
      result={best:out.rows[0]||null,runs:out.runs};
    }else{
      baseline=growthBaseline(c,st);
      result=await growthStageSearch(c,st,snapshot.profile,id);
    }
    if(GROW.id!==id)return;
    if(GROW.sig!==growthSig(c,st)){growthCancel();return;}
    GROW.result={...result,baseline,snapshot,kind:c.key,ms:Date.now()-started,
      signature:JSON.stringify(['grown-account',MyInfoReco.OVERWRITE_VERSION,snapshot.preset,GROW.sig])};
    GROW.phase='done';
  }catch(e){if(GROW.id===id){GROW.phase='error';GROW.msg='미완료';GROW.errors.push(e.message);}}
  finally{if(GROW.id===id){GROW.stop=null;SIMQ.busy=null;
    if(SIMQ.pool){SIMQ.pool.slice(1).forEach(w=>w?.terminate());SIMQ.pool=null;}
    growthPaint();}}
}
function growthBaseline(c,st){
  const q=LASTQ[1],selected=PICK[c.key+'|'+st.tab+'|'+st.name+'|1'];
  const current=selected&&(q?.all||q?.rows||[]).find(t=>t.keys.slice().sort().join(',')===selected)||q?.rows[0];
  return current?growthMetric(SIMQ.res[simSig(st,current)]||{clear:0}):null;
}
function growthTabsPaint(c,el,show){
  const seasonal=c.key==='guild'||c.key==='cosmo',r=GROW.result;
  const baseline=seasonal?(c.key==='guild'?GSR:CSR).rows[0]:growthBaseline(c,cur[$('stage').value]);
  const now=seasonal?$(c.key+'-search'):document.querySelector('#out > [data-party="1"]');
  if(now&&now.nextElementSibling!==el)now.after(el);
  growthTabs||=Ux.createResultTabs();
  growthTabs.update(now,el,Ux.resultTabState({enabled:growthEnabled(),phase:GROW.phase,better:show,
    kind:c.key,baseline,best:r?.best,message:GROW.msg,errors:GROW.errors}));
  if($('result-tabs'))$('result-tabs').hidden=$('out').hidden;
}
// 탐색이 끝났는데 더 나은 육성 편성이 없을 때: 탭 없이 같은 자리에 한 줄 안내(조용히 사라지면 켰는데 안 나온 것처럼 보임)
function growthNoneText(kind,r){const prob=['op','clo'].includes(kind),b=r?.baseline,v=prob?b?.clear:kind==='guild'?b?.score:b?.sum;
  const noItems=!!r?.snapshot&&!Object.values(r.snapshot.changes||{}).some(a=>a?.changedFields?.length);
  if(prob&&Number.isFinite(v)&&v>=1)return '추가 육성 없이도 모의 전투 클리어율 100%예요';
  if(noItems)return '이미 추천 기준까지 다 키워서 더 올릴 항목이 없어요';
  const has=Number.isFinite(v),now=has?(prob?Math.round(v*100)+'%':miNum(v)+'점'):'';
  if(prob&&has&&v<=0)return `추천 기준까지 키워도 이 스테이지는 모의 전투에서 깨지 못했어요 (지금 ${now})`;
  return `추천 기준까지 키워도 지금${has?'('+now+')':''}보다 ${prob?'잘 깨는':'점수가 높은'} 편성은 찾지 못했어요`;}
// 결과 없음 아래 한 줄 도움말(11/13 제보: «아무것도 안 나오면 스타링크를 올려야 하나?» 오해) — 무엇을 올려 봤는지와 다음에 할 일
function growthNoneHint(kind,r){const prob=['op','clo'].includes(kind),b=r?.baseline,v=prob?b?.clear:null;
  if(prob&&Number.isFinite(v)&&v>=1)return '';
  const tried='보유 구원자의 스킬·장비·스텔라 아카이브·잠재력·호감도·공명·스타링크(레벨)를 추천 기준까지 올려서 계산했어요.';
  if(prob&&(!Number.isFinite(v)||v<=0))return tried+' 지금 보유한 구원자로는 아직 어려운 스테이지일 수 있어요. 새 구원자를 얻거나 앞 스테이지부터 도전해 보세요.';
  return tried+' 지금 추천 편성이 가장 나은 선택이에요.';}
function growthNonePaint(c,r){growthTabs?.reset();let el=$('growth-result');
  if(!el){el=document.createElement('div');el.id='growth-result';el.className='party';$('out').append(el);}
  el.dataset.state='none';const errs=r?.snapshot?.errors||[];
  el.innerHTML=`<p class="growth-none" data-k="growth-none" role="status"><b>클리어 추천 육성</b> · ${esc(growthNoneText(c.key,r))}</p>`+((h=>h?`<p class="mut growth-none-hint" data-k="growth-none-hint">${esc(h)}</p>`:'')(growthNoneHint(c.key,r)))+
    (errs.length?`<details><summary>계산에서 제외된 구원자 ${errs.length}명</summary>${errs.map(x=>`<p class="mut">${esc(BYKEY[x.key]?.name||x.key)} · ${esc(x.reason)}</p>`).join('')}</details>`:'');
  const now=['guild','cosmo'].includes(c.key)?$(c.key+'-search'):document.querySelector('#out > [data-party="1"]');
  if(now&&now.nextElementSibling!==el)now.after(el);}
function growthPaint(){
  growthRankPaint();
  let el=$('growth-result');
  if(!growthEnabled()||!MI.info){growthTabs?.reset();el?.remove();return;}
  const c=contents[$('content').value],r=GROW.result;
  if(seasonBlocked(c.key)||!['op','clo','guild','cosmo'].includes(c.key)){growthTabs?.reset();el?.remove();return;}
  if(r&&['op','clo'].includes(c.key))r.baseline=growthBaseline(c,cur[$('stage').value]);
  const show=r&&growthBetter(c.key,r.baseline,r.best);
  if(GROW.phase==='done')growthRecord(c,cur[$('stage').value],r,show);
  if(GROW.phase==='done'&&!show){growthNonePaint(c,r);return;}
  if(GROW.phase==='idle'&&growthSeasonContent()&&growthSeasonReady(c)&&SIMQ.busy==null)
    setTimeout(()=>{if(GROW.phase==='idle')growthStart(c,cur[$('stage').value]);},0);
  if(GROW.phase==='idle'&&!growthSeasonContent()){growthTabs?.reset();el?.remove();return;}
  if(!el){el=document.createElement('div');el.id='growth-result';el.className='party';$('out').append(el);}
  el.dataset.state=GROW.phase;
  const head='<h3 class="growth-heading" data-k="growth-summary">클리어 추천 육성 <span>· '+(['guild','cosmo'].includes(c.key)?'맞추면 기대 점수가 올라가요':'이것만 맞추면 깰 수 있어요')+'</span></h3>';
  if(GROW.phase!=='done'){
    const running=GROW.phase==='running';
    el.innerHTML='<b data-k="growth-summary">클리어 추천 육성</b><span class="tag growth-on">클리어 추천 육성 켜짐</span>'+` <span role="status">${running?'탐색 중':GROW.phase==='error'?'미완료 · 다시 실행해 주세요':'지금 계정 탐색 후'}</span>`+
      (running?`<span class="mut"> ${esc(GROW.msg)}</span><button class="sec" data-growth-cancel>중단</button>`:'')+
      (GROW.errors.length?`<details><summary>상세</summary>${GROW.errors.map(esc).join(' · ')}</details>`:'');
    el.querySelector('[data-growth-cancel]')?.addEventListener('click',()=>{
      const stop=GROW.stop;GROW.id++;stop?.();GROW.stop=null;SIMQ.busy=null;GROW.phase='error';GROW.msg='미완료';growthPaint();});growthTabsPaint(c,el,show);return;
  }
  const marks=r.snapshot.changes;
  const cards=(order,lead)=>{LEADKEY=lead;return `<div class="rowcards">${order.map((k,i)=>card({s:BYKEY[k]},i===0||i===3?'back':'front',null,marks[k]||null)).join('')}</div><div class="growth-tasks">${order.map(k=>marks[k]?growthTodoRow(marks[k],BYKEY[k].name):'').join('')}</div>`;};
  let body='';
  if(c.key==='cosmo')body=r.best.teams.map(t=>`<div class="growth-score-card"><div class="season-chips"><b>${esc(csBoss(t.boss))}</b><span class="tag">난이도 ${t.level}</span><span class="tag">${esc(t.brk||'브레이크 없음')}${t.brkLv?' · Lv.'+t.brkLv:''}</span></div>${cards([t.order[2],t.order[0],t.order[1],t.order[3]],t.order[0])}</div>`).join('');
  else if(c.key==='guild'){const t=r.best;body=`<div class="season-chips"><span class="tag">${t.level}단계</span><span class="tag">${esc(GuildSearch.SUP_NAME[t.sup]||t.sup)}</span></div>`+cards([t.order[2],t.order[0],t.order[1],t.order[3]],t.order[0]);}
  else if(r.team){const ar=arrangeOf(r.team.t.combo);body=cards(ar.order,ar.lead)+`<p class="mut">${esc(r.team.breakName||'브레이크 없음')}</p>`;}
  const keys=c.key==='cosmo'?r.best.teams.flatMap(t=>t.keys||t.order):c.key==='guild'?(r.best.keys||r.best.order):r.team?.t.keys||[];
  const grown=keys.reduce((sum,k)=>sum+(r.snapshot.profile.results[k]?.power||0),0);
  const currentKeys=c.key==='cosmo'?r.baseline?.teams?.flatMap(t=>t.keys||t.order):c.key==='guild'?(r.baseline?.keys||r.baseline?.order):[...document.querySelectorAll('.party[data-party="1"] .gc')].map(e=>e.dataset.key);
  const current=MyInfoReco.profile(MI.info,R,MI.growth,c.key==='guild'?'op':c.key);
  const now=(currentKeys||keys).reduce((sum,k)=>sum+(current.results[k]?.power||0),0),delta=grown-now;
  const totals={};let missing=false;
  for(const k of keys){if(!marks[k])continue;for(const f of growthDisplay(marks[k]).fields){if(f.delta==null){missing=true;continue;}totals[f.field]=(totals[f.field]||0)+f.delta;}}
  const st=cur[$('stage').value],prob=['op','clo'].includes(c.key);
  const summary=prob?`<div class="mi-verdict"><div class="verdict-main"><b class="verdict-number"><small>지금</small>${r.baseline?Math.round(r.baseline.clear*100)+'%':'자료 없음'} → <small>맞추면</small>${Math.round(r.best.clear*100)}%</b>${Ux.chip(r.best.clear)}</div><div class="verdict-stats"><div><b>${miNum(MODE==='manual'?r.best.ttk:(r.best.ta??r.best.ttk))}턴</b><small>예상 턴</small></div><div><b>${miNum(grown)}</b><small>전투력</small></div><div><b>${st.rp?miNum(st.rp):'자료 없음'}</b><small>권장 전투력</small></div></div></div>`:`<div class="season-score" data-k="growth-season-score"><span>지금 ${r.baseline?miNum(c.key==='guild'?r.baseline.score:r.baseline.sum)+'점':'자료 없음'} → 맞추면</span><b>${miNum(c.key==='guild'?r.best.score:r.best.sum)}</b><small>${c.key==='guild'?'상위 20% 점수':'3팀 합산 점수'}</small></div>`;
  el.innerHTML=head+summary+`<p class="growth-total" data-k="growth-power-total">기존 대비 전투력 ${Ux.signed(delta)}(${now?Ux.signed(delta/now*100)+'%':'비교 자료 없음'})으로 계산했어요 ${Ux.help('전투력 변화','위의 현재 편성과 육성 후 편성의 팀 전투력을 비교해요. 구성원이 바뀌면 편성 교체에 따른 차이도 포함해요. 항목별 값은 같은 구원자에서 그 항목만 목표로 올렸을 때의 전투력 증가예요. 곱셈·반올림·편성 변경 때문에 항목별 합계와 전체 증가가 다를 수 있어요. 추가 모의 전투는 하지 않아요.')}</p>`+
    `<p class="growth-components" data-k="growth-components">${['팀 항목별 전투력',...Object.entries(totals).filter(([,v])=>v!==0).map(([f,v])=>`${growthShortFields[f]} ${Ux.signed(v)}`),...(missing?['일부 항목 비교 자료 없음']:[])].join(' · ')}</p><div data-k="growth-${c.key}-card">${body}</div>`+
    Ux.help('육성 기준',`이 육성 계획을 따랐을 때 예상. 보유 구원자의 기준선 미달 항목만 프리셋 목표로 계산해요. 패시브는 현재 값을 유지해요. 최소 육성치는 아니에요. ${D.archiveGrades?.unverified||''}`)+
    (r.snapshot.errors.length?`<details><summary>계산에서 제외된 구원자 ${r.snapshot.errors.length}명</summary>${r.snapshot.errors.map(x=>`<p class="mut">${esc(BYKEY[x.key]?.name||x.key)} · ${esc(x.reason)}</p>`).join('')}</details>`:'');
  growthTabsPaint(c,el,show);
}
