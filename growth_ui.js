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
// 스테이지형 콘텐츠(작전·작전 어려움·일일·장비 탐사·큐브·플래시 포인트·성간 회랑·격전 의뢰 …) = 길방·코스모(시즌 탐색) 밖 전부. 같은 탐색(growthStageSearch)을 쓴다
function growthStageKind(kind){return !['guild','cosmo'].includes(kind);}
// 그 콘텐츠의 목표: 3별 목표(starOf — 장비 탐사·격전 의뢰, 옵션 «클리어만»이면 0)면 N턴, 아니면 0(클리어율)
function growthGoalTurns(kind){return typeof starOf==='function'&&growthStageKind(kind)?starOf(kind)||0:0;}
// 목표 지표 값: 3별 목표 결과(t60 있음)면 N턴 내 클리어율, 아니면 클리어율 — 예선 순위(scrCmp)의 첫 기준과 같다
function growthGoal(r){return r?(r.t60??r.clear):null;}
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
function growthEvaluate(jobs,n,seed,c,st,id,deadline,env={}){const state=env.state||GROW,paint=env.paint||growthPaint;return new Promise(resolve=>{
  const results={};if(!jobs.length||Date.now()>=deadline||GROW.id!==id||state.errors.length){resolve(results);return;}
  // 작업자 풀·대기열은 추천 예선·본선과 같은 것(scrPool·simDispatch): 정상으로 끝나면 작업자를 살려 두고, 끊길 때(중단·시간 초과·오류)만 풀을 끈다
  const workers=scrPool(jobs.length),request=SIMQ.requestId=(SIMQ.requestId||0)+1;let done=false;
  const finish=cut=>{if(done)return;done=true;clearTimeout(timer);state.stop=null;
    if(cut)Object.defineProperty(results,'incomplete',{value:true});
    if(cut)simPoolDrop();
    resolve(results);};
  let timer;
  // 예선(env.screenClock)은 전체 시간 상한이 없다: 엔진 준비는 LOAD_MS, 준비된 뒤에는 팀 결과가 올 때마다 다시 재는 무진행 상한뿐(추천 예선과 같음).
  // 타이머가 예정보다 크게 늦게 돌았으면(절전·탭 동결 복귀 — 그동안 계산도 멈춤) 끝내지 않고 다시 잰다. 가려진 탭도 끊지 않는다
  const stall=env.screenClock,arm=()=>{clearTimeout(timer);
    const due=stall?Date.now()+(stall.ready?simTeamLimit(n,'auto'):SIMQ.LOAD_MS):deadline;
    timer=setTimeout(()=>{if(stall&&(Date.now()-due>5000||(typeof document!=='undefined'&&document.hidden))){arm();return;}finish(true);},Math.max(1,due-Date.now()));};
  const ready=()=>{if(stall&&!stall.ready&&workers.every(w=>w._ready)){stall.ready=true;arm();}};
  arm();ready();state.stop=()=>finish(true);
  // 작업마다 판 수를 따로 줄 수 있다(j.runs — 앞 단계 판을 다시 쓰는 예선 2차: growthStageSearch). 결과의 n 은 합친 판 수(n)
  const base=location.href.replace(/[?#].*$/,'').replace(/[^/]*$/,''),options={...(env.options||simOpt(c.key)),rng_streams:true};
  simDispatch(workers,jobs,{id:request,live:()=>!done&&GROW.id===id&&SIMQ.requestId===request,
    msg:j=>({type:'run',base,stage:c.key+'/'+st.tab+'/'+st.name,n_runs:j.runs||n,seed,options,
      teams:[{key:j.id,party:j.party,options:j.options}]}),
    stage(w,m){if(m.msg==='준비 끝'){SIMQ.loaded=true;ready();}},
    team(j,m){if(stall)arm();
      if(m.result.ver!==GROW.versions.engine){state.errors.push('엔진 버전이 바뀜 · 다시 실행');finish(true);return;}
      results[j.id]={...m.result,n};state.msg=`${seed===900001?'재평가':'후보 확인'} ${Object.keys(results).length}/${jobs.length} · ${n}판`;paint();},
    done(){finish(false);},
    error(msg,w,crash){state.errors.push((crash?'가정 작업자 오류: ':'육성 모의 전투 오류: ')+msg);finish(true);}});
});}
// 스테이지형 콘텐츠는 모두 탐색한다(11/14: 작전·성간 회랑만 하던 것). 못 하는 경우(내 정보 기준 아님·길방 EX 밖)는 growthPaint 가 이유를 남긴다 — 켰는데 조용히 사라지지 않게
function growthMaybe(c,st){if(growthEnabled()&&growthSeasonContent()){growthPaint();return;}if(!growthEnabled()||!REQ)return;
  if(!miMode()||!growthStageKind(c.key)){growthPaint();return;}
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
  return {rules,mode:'auto',breaks:[breaks,{}],...(shared?{breakDefault:SHARE.b}:{}),...(teams?.length?{breakTeams:teams}:{})};}
function growthPriority(history){return GrowthGuide.priority(history,GROW.sig,
  Object.fromEntries(contents.map(c=>[c.key,growthConditions(c,false)])));}
function growthMembers(r){const keys=r.kind==='cosmo'?r.best?.teams.flatMap(t=>t.keys||t.order):r.kind==='guild'?r.best?.keys||r.best?.order:r.team?.t.keys;
  return [...new Set(keys||[])].map(key=>r.snapshot.changes[key]).filter(a=>a?.changedFields.length);}
function growthRecord(c,st,r,show){if(!r?.snapshot||r.kind!==c.key||!GROW.sig)return;
  // 스테이지형은 목표 지표의 차이(3별 목표면 N턴 내 클리어율 — metric 이름도 따로)
  const stage=growthStageKind(c.key),turns=stage&&r.best?.t60!=null?growthGoalTurns(c.key):0,field=c.key==='guild'?'score':c.key==='cosmo'?'sum':'clear',scale=field==='clear'?100:1;
  const members=show?growthMembers(r):[],delta=!show?0:stage?scale*(growthGoal(r.best)-(growthGoal(r.baseline)||0)):scale*(r.best[field]-(r.baseline?.[field]||0));
  const entry=GrowthGuide.grownSummary({content:c.key==='cosmo'?'cosmo/'+D.cosmoRaid.season:c.key+'/'+st.tab+'/'+st.name,
    signature:GROW.sig,account:MI.hash,version:MyInfoReco.OVERWRITE_VERSION,members,delta,
    metric:c.key==='guild'?'guild-top':c.key==='cosmo'?'cosmo-'+CSR.optMode:turns?'clear-in-'+turns:'clear',unit:field==='clear'?'%p':'점'});
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
// 스테이지형: 목표 지표(3별 목표면 N턴 내 클리어율, 아니면 클리어율)가 올라야 «더 나음». 목표 지표가 같으면 3별 목표일 때만 클리어율이 오른 경우를 인정한다
//  (N턴 내 확률은 그대로여도 깨는 확률이 오른 것). 진척도·처치 턴만 나아진 것은 «더 잘 깸»이 아니다 — 표시하지 않는다
function growthBetter(kind,baseline,result){
  if(growthStageKind(kind)){const a=growthGoal(result),b=growthGoal(baseline)??0;
    return Number.isFinite(a)&&(a>b||(a===b&&result.t60!=null&&result.clear>(baseline?.clear??0)));}
  const metric=r=>kind==='guild'?r?.score:r?.sum;
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
  if(!qi)return {best:null,runs:0,reason:'quick'};
  const candidates=R.filter(s=>profile.results[s.key]&&!EXCL.has(s.key)&&(!restrict||s.el===restrict))
    .map(s=>{const [scoreValue,parts]=score(s,st.w,c.main,c.boss);return {s,score:scoreValue,parts};});
  if(candidates.length<4)return {best:null,runs:0,reason:'few'};
  const defPen=CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty;
  const all=quickRank(rankAll(candidates,defPen),qi,profile),key=t=>t.keys.slice().sort().join(','),by=new Map(all.map(t=>[key(t),t]));
  // 후보 순서는 추천 예선(simScreen)과 같은 규칙(scrPick, 재점화 풀 포함). 전체 시간 상한 없이 끝까지 돌고, 멈추는 것은 「중단」(전체 취소)뿐
  let keys=scrPick(all,SCR_RK&&rkOf(c.key)?rkQuickTop(c,st,all,SCR_RK,qi):null),runs=0;
  // 예선 2차는 1차 판을 다시 돌리지 않는다(추천 예선과 같음): prev = 앞 단계 {n, r}. 앞 결과의 raw 를 되돌려 보내 뒤쪽 판(run_offset)만 돌리고 작업자가 합친다
  const evaluate=async(list,n,deadline,final=false,prev=null)=>{
    if(GROW.id!==id)throw Error('취소');
    const jobs=list.map(k=>{const j=growthJob(by.get(k),k,c);if(final)return j;
      const raw=prev&&prev.n<n?prev.r[k]?.raw:null;
      return raw?{...j,runs:n-prev.n,options:{...j.options,run_offset:prev.n,merge_raw:raw}}:{...j,options:{...j.options,raw_runs:true}};});
    const r=await growthEvaluate(jobs,n,SIMQ.seed,c,st,id,deadline,{final,...(!final?{screenClock:{}}:{})});
    runs+=final?Object.keys(r).length*GrowthGuide.finalCost(n):jobs.reduce((a,j)=>a+(r[j.id]?j.runs||n:0),0);
    if(GROW.id!==id||r.incomplete||Object.keys(r).length!==jobs.length)throw Error('미완료');
    return r;
  };
  if(keys.length>3){
    const deadline=Infinity; // 예선은 growthEvaluate 의 내려받기·무진행 상한만 쓴다
    let prev=null;
    for(const round of SCR_ROUNDS){
      if(round.top)keys=keys.slice(0,round.top);
      const r=await evaluate(keys,round.n,deadline,false,prev);prev={n:round.n,r};
      keys.sort((a,b)=>scrCmp(r[a],r[b]));
      if(keys.length<=3)break;
    }
  }
  // The same 3-at-a-time, at most 9, >=50% stop rule as simAutoKick — 목표 지표 기준(3별 목표면 N턴 내 클리어율).
  let best=null,bestJob=null;
  for(let i=0;i<Math.min(9,keys.length);i+=3){
    const batch=keys.slice(i,i+3),r=await evaluate(batch,SIMQ.n,
      Date.now()+Math.max(SIMQ.LOAD_MS,batch.length*simTeamLimit(SIMQ.n)),true);
    for(const k of batch)if(!best||scrCmp(r[k],best)<0){best=r[k];bestJob=growthJob(by.get(k),k,c);}
    if(growthGoal(best)>=.5)break;
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
      {excluded:[...EXCL],slots,priority:D.journeyPriority});   // 아카이브 주력 판단 = 공략 DB 여정 스탯 우선순위
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
  finally{if(GROW.id===id){GROW.stop=null;SIMQ.busy=null;   // 작업자 풀은 끄지 않는다(다음 계산이 다시 씀 — scrPool 주석). 끊긴 경우는 growthEvaluate 가 이미 껐다
    growthPaint();}}
}
function growthBaseline(c,st){
  const q=LASTQ[1],selected=PICK[c.key+'|'+st.tab+'|'+st.name+'|1'];
  const current=selected&&(q?.all||q?.rows||[]).find(t=>t.keys.slice().sort().join(',')===selected)||q?.rows[0];
  return current?(SIMQ.res[simSig(st,current)]||{clear:0}):null;
}
function growthTabsPaint(c,el,show){
  const seasonal=c.key==='guild'||c.key==='cosmo',r=GROW.result;
  const baseline=seasonal?(c.key==='guild'?GSR:CSR).rows[0]:growthBaseline(c,cur[$('stage').value]);
  const now=seasonal?$(c.key+'-search'):document.querySelector('#out > [data-party="1"]');
  if(now&&now.nextElementSibling!==el)now.after(el);
  growthTabs||=Ux.createResultTabs();
  growthTabs.update(now,el,Ux.resultTabState({enabled:growthEnabled(),phase:GROW.phase,better:show,
    kind:c.key,baseline,best:r?.best,message:GROW.msg,errors:GROW.errors,goalTurns:growthGoalTurns(c.key)}));
  if($('result-tabs'))$('result-tabs').hidden=$('out').hidden;
}
// 켰는데 탐색을 시작하지 않은 이유(결과 화면이 떠 있을 때만). 빈 글 = 안내할 화면이 아님
function growthIdleText(c){
  if(!REQ||!document.querySelector('#out > [data-party]'))return '';
  if(c.key==='guild')return '길드 방어전은 EX 단계에서만 계산해요';
  if(!miMode())return '내 정보 기준으로 추천할 때만 계산해요 · 육성 기준을 «내 구원자»로 바꿔 주세요';
  if(SIMQ.err)return '모의 전투가 끝나지 않아 계산하지 못했어요 · 모의 전투를 다시 실행하면 이어서 계산해요';
  if(!simAutoOn())return '모의 전투를 실행하면 이어서 계산해요';
  if(SIMQ.busy!=null)return '다른 계산이 끝나면 이어서 계산해요';
  return '계산 준비 중';}
// 공략 DB 는 늦게 갱신될 수 있다: DB 에 아직 없는 구원자(data/journey_priority.json 의 fallback)는 직업 기본 우선순위로 아카이브를 판단했다 — 그 사실을 보인다(조용히 대체하지 않음)
function growthArchiveNote(keys){const fb=D.journeyPriority?.fallback||{},names=[...new Set(keys||[])].filter(k=>fb[k]).map(k=>BYKEY[k]?.name||k);
  return names.length?`<p class="mut" data-k="growth-archive-fallback">스텔라 아카이브 우선순위: ${names.map(esc).join('·')} — 공략 DB 미반영 · 직업 기본값으로 판단했어요</p>`:'';}
// 탐색이 끝났는데 더 나은 육성 편성이 없을 때: 탭 없이 같은 자리에 한 줄 안내(조용히 사라지면 켰는데 안 나온 것처럼 보임)
//  3별 목표(turns>0)면 «N턴 안에» 기준으로 말한다. 계산하지 못한 경우(r.reason)는 이유를 그대로 적는다
function growthNoneText(kind,r,turns=growthGoalTurns(kind)){const prob=growthStageKind(kind),b=r?.baseline,star=prob&&turns>0&&(b?.t60!=null||r?.best?.t60!=null);
  if(r?.reason==='few')return '이 스테이지에 편성할 수 있는 보유 구원자가 4명 미만이라 계산하지 못했어요';
  if(r?.reason==='quick')return '이 스테이지는 빠른 계산 자료가 없어서 계산하지 못했어요';
  const v=prob?(star?b?.t60:b?.clear):kind==='guild'?b?.score:b?.sum;
  const noItems=!!r?.snapshot&&!Object.values(r.snapshot.changes||{}).some(a=>a?.changedFields?.length);
  if(prob&&Number.isFinite(v)&&v>=1)return star?`추가 육성 없이도 ${turns}턴 내 클리어율 100%예요`:'추가 육성 없이도 모의 전투 클리어율 100%예요';
  if(noItems)return '이미 추천 기준까지 다 키워서 더 올릴 항목이 없어요';
  const has=Number.isFinite(v),now=has?(prob?Math.round(v*100)+'%':miNum(v)+'점'):'';
  if(star)return has&&v>0?`추천 기준까지 키워도 지금(${turns}턴 내 ${now})보다 ${turns}턴 안에 잘 깨는 편성은 찾지 못했어요`:
    `추천 기준까지 키워도 ${turns}턴 안에 깨는 편성은 찾지 못했어요${has?` (지금 ${turns}턴 내 ${now}${Number.isFinite(b?.clear)?' · 클리어 '+Math.round(b.clear*100)+'%':''})`:''}`;
  if(prob&&has&&v<=0)return `추천 기준까지 키워도 이 스테이지는 모의 전투에서 깨지 못했어요 (지금 ${now})`;
  return `추천 기준까지 키워도 지금${has?'('+now+')':''}보다 ${prob?'잘 깨는':'점수가 높은'} 편성은 찾지 못했어요`;}
// 결과 없음 아래 도움말(11/13 제보: «아무것도 안 나오면 스타링크를 올려야 하나?» 오해) — [제목, 내용] 줄 목록. 무엇을 올려 봤는지와 참고 한 줄
function growthNoneHint(kind,r,turns=growthGoalTurns(kind)){const prob=growthStageKind(kind),b=r?.baseline,star=prob&&turns>0&&(b?.t60!=null||r?.best?.t60!=null),v=prob?(star?b?.t60:b?.clear):null;
  if(r?.reason)return [];
  if(prob&&Number.isFinite(v)&&v>=1)return [];
  const noItems=!!r?.snapshot&&!Object.values(r.snapshot.changes||{}).some(a=>a?.changedFields?.length);
  const rows=noItems?[]:[['추천 기준까지 올려 본 항목','스킬 · 장비 · 스텔라 아카이브 · 잠재력 · 호감도 · 공명 · 스타링크(레벨) (보유 구원자만)']];
  if(star&&(!Number.isFinite(v)||v<=0)&&b?.clear>0)rows.push(['참고',`클리어는 되지만 ${turns}턴 안에 끝내기는 아직 어려울 수 있어요. 클리어만 필요하면 ⋯ 메뉴의 3별 목표를 «클리어만»으로 바꿔 보세요.`]);
  else if(prob&&(!Number.isFinite(v)||v<=0))rows.push(['참고','지금 보유한 구원자로는 아직 어려운 스테이지일 수 있어요.']);
  else rows.push(['결론','지금 추천 편성이 가장 나은 선택이에요.']);
  return rows;}
function growthNonePaint(c,r){growthTabs?.reset();let el=$('growth-result');
  if(!el){el=document.createElement('div');el.id='growth-result';el.className='party';$('out').append(el);}
  el.dataset.state='none';const errs=r?.snapshot?.errors||[],hint=growthNoneHint(c.key,r);
  el.innerHTML=`<h3 class="growth-none-title">클리어 추천 육성</h3><p class="growth-none" data-k="growth-none" role="status">${esc(growthNoneText(c.key,r))}</p>`+
    (hint.length?`<dl class="growth-none-hint" data-k="growth-none-hint">${hint.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>`:'')+
    growthArchiveNote(Object.keys(r?.snapshot?.profile?.units||{}))+
    (errs.length?`<details><summary>계산에서 제외된 구원자 ${errs.length}명</summary>${errs.map(x=>`<p class="mut">${esc(BYKEY[x.key]?.name||x.key)} · ${esc(x.reason)}</p>`).join('')}</details>`:'');
  const now=['guild','cosmo'].includes(c.key)?$(c.key+'-search'):document.querySelector('#out > [data-party="1"]');
  if(now&&now.nextElementSibling!==el)now.after(el);}
function growthPaint(){
  growthRankPaint();
  let el=$('growth-result');
  if(!growthEnabled()||!MI.info){growthTabs?.reset();el?.remove();return;}
  const c=contents[$('content').value],r=GROW.result,stage=growthStageKind(c.key);
  if(seasonBlocked(c.key)){growthTabs?.reset();el?.remove();return;}   // 기간이 끝난 시즌 콘텐츠는 화면 자체가 «기간 종료» 안내(결과·켜짐 표시 없음)
  if(r&&stage)r.baseline=growthBaseline(c,cur[$('stage').value]);
  const show=r&&growthBetter(c.key,r.baseline,r.best);
  if(GROW.phase==='done')growthRecord(c,cur[$('stage').value],r,show);
  if(GROW.phase==='done'&&!show){growthNonePaint(c,r);return;}
  if(GROW.phase==='idle'&&growthSeasonContent()&&growthSeasonReady(c)&&SIMQ.busy==null)
    setTimeout(()=>{if(GROW.phase==='idle')growthStart(c,cur[$('stage').value]);},0);
  // 탐색을 시작하지 않은 채 결과 화면이 떠 있으면 이유를 남긴다(11/14 제보: «켜짐» 표시만 있고 아무 안내가 없었음). 결과 화면이 없으면(「추천 편성 보기」 전·진행 화면) 지운다
  if(GROW.phase==='idle'&&!growthSeasonContent()){growthTabs?.reset();const why=growthIdleText(c);
    if(!why){el?.remove();return;}
    if(!el){el=document.createElement('div');el.id='growth-result';el.className='party';$('out').append(el);}
    el.dataset.state='idle';el.dataset.shape='';
    el.innerHTML=`<h3 class="growth-none-title">클리어 추천 육성</h3><p class="growth-none" data-k="growth-wait" role="status">${esc(why)}</p>`;
    const now=document.querySelector('#out > [data-party="1"]');if(now&&now.nextElementSibling!==el)now.after(el);return;}
  if(!el){el=document.createElement('div');el.id='growth-result';el.className='party';$('out').append(el);}
  el.dataset.state=GROW.phase;
  const turns=growthGoalTurns(c.key),star=stage&&turns>0&&r?.best?.t60!=null;
  const head='<h3 class="growth-heading" data-k="growth-summary">클리어 추천 육성 <span>· '+(!stage?'맞추면 기대 점수가 올라가요':star?`맞추면 ${turns}턴 안에 깰 확률이 올라가요`:'이것만 맞추면 깰 수 있어요')+'</span></h3>';
  if(GROW.phase!=='done'){
    const running=GROW.phase==='running',shape=GROW.phase+'|'+GROW.errors.length,msg=el.querySelector('[data-k="growth-msg"]');
    // 탐색 중 팀 결과마다 불린다: 모양이 같으면 진행 글자만 바꾼다(통째로 다시 그리면 누르는 중인 「중단」 단추가 사라져 클릭이 안 먹음)
    if(running&&el.dataset.shape===shape&&msg){const t=' '+GROW.msg;if(msg.textContent!==t)msg.textContent=t;growthTabsPaint(c,el,show);return;}
    el.dataset.shape=shape;
    el.innerHTML='<b data-k="growth-summary">클리어 추천 육성</b><span class="tag growth-on">클리어 추천 육성 켜짐</span>'+` <span role="status">${running?'탐색 중':GROW.phase==='error'?'계산을 끝내지 못했어요 · 다시 실행해 주세요':'지금 계정 탐색 후'}</span>`+
      // 단추를 진행 글자 앞에 둔다(글자 길이가 바뀌어도 단추 자리가 안 밀리게)
      (running?`<button class="sec" data-growth-cancel>중단</button><span class="mut" data-k="growth-msg"> ${esc(GROW.msg)}</span>`:'')+
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
  // 요약의 큰 숫자는 목표 지표(3별 목표면 N턴 내 클리어율), 3별 목표면 클리어율을 아래 줄에 함께 적는다
  const st=cur[$('stage').value],prob=stage,pct=v=>Number.isFinite(v)?Math.round(v*100)+'%':'자료 없음';
  const summary=prob?`<div class="mi-verdict" data-k="growth-goal" data-goal="${star?turns:0}"><div class="verdict-main"><b class="verdict-number"><small>${star?turns+'턴 내 · ':''}지금</small>${r.baseline?pct(growthGoal(r.baseline)):'자료 없음'} → <small>맞추면</small>${pct(growthGoal(r.best))}</b>${Ux.chip(growthGoal(r.best))}</div>${star?`<div class="verdict-meta" data-k="growth-clear">클리어 ${r.baseline?pct(r.baseline.clear):'자료 없음'} → ${pct(r.best.clear)}</div>`:''}<div class="verdict-stats"><div><b>${miNum(r.best.ta??r.best.ttk)}턴</b><small>예상 턴</small></div><div><b>${miNum(grown)}</b><small>전투력</small></div><div><b>${st.rp?miNum(st.rp):'자료 없음'}</b><small>권장 전투력</small></div></div></div>`:`<div class="season-score" data-k="growth-season-score"><span>지금 ${r.baseline?miNum(c.key==='guild'?r.baseline.score:r.baseline.sum)+'점':'자료 없음'} → 맞추면</span><b>${miNum(c.key==='guild'?r.best.score:r.best.sum)}</b><small>${c.key==='guild'?'상위 20% 점수':'3팀 합산 점수'}</small></div>`;
  el.innerHTML=head+summary+`<p class="growth-total" data-k="growth-power-total">기존 대비 전투력 ${Ux.signed(delta)}(${now?Ux.signed(delta/now*100)+'%':'비교 자료 없음'})으로 계산했어요 ${Ux.help('전투력 변화','위의 현재 편성과 육성 후 편성의 팀 전투력을 비교해요. 구성원이 바뀌면 편성 교체에 따른 차이도 포함해요. 항목별 값은 같은 구원자에서 그 항목만 목표로 올렸을 때의 전투력 증가예요. 곱셈·반올림·편성 변경 때문에 항목별 합계와 전체 증가가 다를 수 있어요. 추가 모의 전투는 하지 않아요.')}</p>`+
    `<p class="growth-components" data-k="growth-components">${['팀 항목별 전투력',...Object.entries(totals).filter(([,v])=>v!==0).map(([f,v])=>`${growthShortFields[f]} ${Ux.signed(v)}`),...(missing?['일부 항목 비교 자료 없음']:[])].join(' · ')}</p>${growthArchiveNote(keys)}<div data-k="growth-${c.key}-card">${body}</div>`+
    Ux.help('육성 기준',`이 육성 계획을 따랐을 때 예상. 보유 구원자의 기준선 미달 항목만 프리셋 목표로 계산해요. 패시브는 현재 값을 유지해요. 최소 육성치는 아니에요. ${D.archiveGrades?.unverified||''}`)+
    (r.snapshot.errors.length?`<details><summary>계산에서 제외된 구원자 ${r.snapshot.errors.length}명</summary>${r.snapshot.errors.map(x=>`<p class="mut">${esc(BYKEY[x.key]?.name||x.key)} · ${esc(x.reason)}</p>`).join('')}</details>`:'');
  growthTabsPaint(c,el,show);
}
