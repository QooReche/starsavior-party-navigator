// Content/DOM-free worker execution. Callers own candidate, score, seed and ordering policies.
(function(root){
 'use strict';
 function createWorker(){return new root.Worker('sim_worker.js')}
 // RecoPlan input + score-search aliases. upper means jobs/games is a ceiling;
 // p is occurrence probability (unknown conditional work conservatively uses 1).
 // This only describes work: it never schedules, filters or reorders it.
 function planStages(stages){return stages.map((s,i)=>{
  const jobs=s.jobs??s.teams??0,runs=s.runs??0;
  return {...s,id:s.id??i+1,step:s.step??s.name??String(s.id??i+1),name:s.name??s.step??String(s.id??i+1),
   jobs,teams:jobs,runs,games:jobs*runs,done:s.done??0,chunk:s.chunk??1,kind:s.kind??'run',p:s.p??1,upper:!!s.upper};
 })}
function shared(env){
 const now=env.now||(()=>Date.now()),setTimer=env.setTimer||((...args)=>setTimeout(...args)),clearTimer=env.clearTimer||((...args)=>clearTimeout(...args));
 // Same resource owner as phase execution; scheduling/retention remain caller contracts.
 const resources=workerPool(()=>{
  const w=(env.makeWorker||createWorker)();w.onmessage=e=>simReceive(w,e.data);
  w.onerror=e=>{const b=w._lease?.batch;if(b&&!b.closed&&b.o.live())b.o.error(e.message||'알 수 없음',w,true)};
  return w;
 });
const SIMPOOL={get workers(){return resources.workers},batches:[],serial:0,pumping:false};
function scrPool(want){const ws=[];ws.capacity=Math.max(1,Math.min(env.capacity(),want||Infinity));return ws}
function simPoolSync(){env.sync?.(SIMPOOL.workers)}
function simRelease(w,kill=false){const lease=w._lease;if(lease){const ws=lease.batch.ws,i=ws.indexOf(w);if(i>=0)ws.splice(i,1);w._lease=null;w._job=null;lease.batch.o.arm?.()}
 if(kill)resources.drop(w);simPoolSync()}
// 취소: 그 owner·요청의 묶음을 닫고, 그 묶음을 «지금 돌리는» 작업자만 끈다(파이썬 중단은 terminate 뿐).
//  놀고 있는 작업자는 owner 와 무관하게 살려 둔다 — 다음 계산이 엔진 부팅(약 1.4초)·자료 파싱을 다시 하지 않게(HANDOFF 27②).
//  늦은 응답은 simReceive 의 lease·id·owner·revision·token·job 검사가 막는다(놀고 있는 작업자는 lease 가 없어 받을 답이 없음)
function simPoolDrop(owner='reco',requestId=null,group=null){
 const matches=b=>b.owner===owner&&(requestId==null||b.o.id===requestId)&&(group==null||b.o.group===group);
 for(const b of SIMPOOL.batches.filter(matches)){b.closed=true;b.o.arm?.cancel?.()}
 for(const w of SIMPOOL.workers.slice())if(w._lease&&matches(w._lease.batch))simRelease(w,true);
 SIMPOOL.batches=SIMPOOL.batches.filter(b=>!b.closed);simPump()}
// 놀고 있는 작업자 정리: 자기 풀을 따로 띄우는 탐색(코스모 3보스·길드 찾기) 직전에 불러 두 풀이 함께 상주하지 않게 함(메모리 예산은 풀 하나 기준)
function simPoolTrimIdle(){for(const w of SIMPOOL.workers.slice())if(!w._lease)simRelease(w,true)}
function simReceive(w,m){
 const lease=w._lease;if(w._dead||!lease)return;
 const b=lease.batch,o=b.o;
 if(b.closed||!o.live())return;
 // Only legacy boot notifications may omit id. Calculation replies must match the lease.
 const boot=m.type==='stage'&&m.id==null&&m.requestId==null;
 if(!boot&&(m.id!==o.id||(m.requestId!=null&&m.requestId!==o.id)))return;
 if(m.owner!=null&&m.owner!==b.owner||m.revision!=null&&m.revision!==(o.revision||0)||m.jobId!=null&&m.jobId!==lease.token)return;
 if(m.job!=null&&m.job!==lease.index)return;
 if(m.type==='stage'){if(m.msg==='준비 끝')w._ready=true;w._last=now();o.stage?.(w,m);if(!b.closed)o.arm?.();return}
 if(m.type==='error'){o.error(m.msg,w,false);return}
 // 묶음(lease.keys = 팀 key → 작업 번호): 묶음 안의 key 이고 아직 안 받은 것만 받는다. done 은 전부 받았을 때만 인정
 if(m.type==='team'){const j=lease.keys.get(m.key);if(j==null||lease.got.has(m.key))return;lease.got.add(m.key);w._last=now();o.team(b.jobs[j],m,w);if(!b.closed)o.arm?.();return}
 if(m.type==='done'){
  if(lease.got.size<lease.keys.size){o.error('결과 없이 끝난 작업',w,false);return}
  simRelease(w);b.left-=lease.keys.size;
  if(!b.left){b.closed=true;o.arm?.cancel?.();SIMPOOL.batches=SIMPOOL.batches.filter(x=>x!==b);o.done()}
  simPump()}}
// 다음 작업 묶음: o.chunk(기본 1)개까지, 팀 key 가 겹치지 않고 팀 말고는 요청이 같은(판 수·옵션·시드…) 이어진 작업만 한 메시지로.
//  작업 하나 = 팀 하나(msg 의 teams 가 1개)일 때만 묶는다. 다음 묶음 첫 작업의 msg 는 b.peek 에 두어 두 번 만들지 않음
function take(b){const size=Math.max(1,Math.floor(b.o.chunk||1)),keys=new Map(),teams=[];let head=null,m0=null;
 while(b.next<b.jobs.length&&keys.size<size){const j=b.next,m=b.peek?.j===j?b.peek.m:b.o.msg(b.jobs[j],j);b.peek=null;
  const solo=m.teams.length===1,k=m.teams[0].key;
  if(m0){const h=JSON.stringify({...m,teams:null});if(!solo||keys.has(k)||h!==head){b.peek={j,m};break}}
  else{m0=m;if(size>1&&solo)head=JSON.stringify({...m,teams:null})}
  b.next++;if(!solo||size===1){keys.set(k,j);return {m,keys}}      // 지금과 같음: 받는 것은 첫 팀 key 하나
  keys.set(k,j);teams.push(m.teams[0])}
 return {m:{...m0,teams},keys}}
function simPump(){if(SIMPOOL.pumping)return;SIMPOOL.pumping=true;
 try{
  for(const b of SIMPOOL.batches.slice())if(!b.o.live()){b.closed=true;b.o.arm?.cancel?.();for(const w of b.ws.slice())simRelease(w,true)}
  SIMPOOL.batches=SIMPOOL.batches.filter(b=>!b.closed);
  for(;;){
   const pending=SIMPOOL.batches.filter(b=>!b.closed&&b.next<b.jobs.length).sort((a,b)=>(env.priority(b.owner))-(env.priority(a.owner))||a.serial-b.serial);
   const priority=pending.some(b=>env.priority(b.owner));
   const b=pending.find(b=>(!priority||env.priority(b.owner))&&b.ws.length<b.ws.capacity);if(!b)break;
   let w=SIMPOOL.workers.find(w=>!w._lease&&!w._dead);
   if(!w){if(SIMPOOL.workers.length>=env.capacity())break;
    w=resources.get(SIMPOOL.workers.length)}
   const j=b.next,{m,keys}=take(b),token=++SIMPOOL.serial;
   w._owner=b.owner;w._lastBatch={owner:b.owner,o:{id:b.o.id,group:b.o.group}};w._lease={batch:b,index:j,token,keys,got:new Set()};w._job=j;w._key=m.teams[0].key;w._n=m.n_runs;w._t=0;w._last=now();b.ws.push(w);simPoolSync();
   for(const i of keys.values())b.o.assigned?.(w,b.jobs[i]);
   w.postMessage({...m,id:b.o.id,requestId:b.o.id,owner:b.owner,revision:b.o.revision||0,job:j,jobId:token});b.o.arm?.();
  }
 }finally{SIMPOOL.pumping=false}}
// 대기열: 작업(팀 하나)을 순서대로 하나씩 맡기고, 작업자가 그 작업의 done 을 보내면 다음 작업을 준다(고정 분배가 아니라 먼저 끝난 작업자가 더 가져간다).
//  작업마다 번호(job)를 달아 보내고 작업자가 되돌려 준다 — 지금 맡긴 작업(번호·팀 key 가 같은 것)의 답만 받고, 같은 작업의 결과는 한 번만 받는다. 결과 없이 done 이 오면 오류.
//  결과는 어느 작업자가 언제 돌렸는지와 무관하다(팀마다 같은 시드·판 번호). 순위 동률도 끝난 순서가 아니라 후보 순서로 가른다(scrOrder).
//  o = {owner='reco', id, revision, group?, chunk?, live(), msg(작업, 번호), assigned?, stage?, team, done, error, arm?}
//  chunk>1 이면 작업 여러 개(팀 여러 개)를 한 메시지로 맡긴다(take). 받기·무진행 감시·속도 표본은 그대로 팀 단위, 취소는 terminate(이미 온 팀 결과는 남음)
//  물리 작업자의 핸들러는 생성 때 한 번만 설치함. 대기 시간에는 무진행 시계를 돌리지 않음.
function simDispatch(ws,jobs,o){const b={ws,jobs,o,owner:o.owner||'reco',next:0,left:jobs.length,serial:++SIMPOOL.serial,closed:false};
 SIMPOOL.batches.push(b);simPump();return b}
// 무진행 감시(작업자별): 일하는 작업자마다 «마지막 소식(w._last) + 상한»을 넘기면 stop(그 작업자가 엔진을 준비했는가). 상한 = 엔진 준비 전 LOAD_MS, 준비 뒤 limit().
//  가려진 탭이거나 타이머가 예정보다 크게 늦게 돌았으면(탭 동결·절전 복귀 — 그동안 계산도 멈춤) 끝내지 않고 다시 잰다. 늦게 돈 경우 그동안 잰 팀 시간(w._t)은 속도 표본에서 버린다
function simWatch(ws,limit,live,stop){return watchWorkers(ws,limit,live,stop,{...env,now,setTimer,clearTimer})}
return {state:SIMPOOL,reserve:scrPool,drop:simPoolDrop,trimIdle:simPoolTrimIdle,dispatch:simDispatch,watch:simWatch,release:simRelease,chunkSize};
}
function watchWorkers(ws,limit,live,stop,env={}){
 const now=env.now||(()=>Date.now()),setTimer=env.setTimer||((...args)=>setTimeout(...args)),clearTimer=env.clearTimer||((...args)=>clearTimeout(...args));
 let timer;const lim=w=>w._ready?limit():env.loadMs();
 const arm=()=>{clearTimer(timer);const busy=ws.filter(w=>w._job!=null);if(!busy.length)return;
  const wait=Math.max(1,Math.min(...busy.map(w=>w._last+lim(w)))-now()),due=now()+wait;
  timer=setTimer(()=>{if(!live())return;const late=now()-due>5000;
   if(late||env.hidden?.()){for(const w of ws){w._last=now();if(late)w._t=0}arm();return}
   const dead=ws.find(w=>w._job!=null&&now()-w._last>=lim(w));if(!dead){arm();return}
   stop(!!dead._ready)},wait)};
 arm.cancel=()=>clearTimer(timer);return arm}
  function split(jobs, n) {
    const out = Array.from({length: Math.max(1, Math.min(n, jobs.length))}, () => []);
    jobs.forEach((j, i) => out[i % out.length].push(j));
    return out;
  }
  function workerPool(makeWorker=createWorker) {
    const ws = []; let closed = false, serial = 0;
    return {
      get workers() { return ws; },
      get(i) { if (closed) throw new Error("닫힌 작업자 풀"); return ws[i] || (ws[i] = makeWorker()); },
      nextId() { return ++serial; },
      drop(w) { const i=ws.indexOf(w);if(i<0)return;w._dead=true;w.terminate();ws.splice(i,1); },
      close() { if (closed) return; closed = true; ws.forEach(w => { w.onmessage = () => {}; w.onerror = () => {}; w.terminate(); }); }
    };
  }
  function runPhase({makeWorker, pool, jobs, workers, runs, seed, stage, base, onProgress, chunk, options, onResult, project=x=>x, watch={}}) {
    const resources=pool||workerPool(makeWorker);
    const dyn = chunk > 0;
    const parts = dyn ? Array.from({length: Math.max(1, Math.min(workers, Math.ceil(jobs.length / chunk)))}, () => []) : split(jobs, workers), res = {}, ws = [];
    let done = 0, finished = 0, dead = false, rejectFn, next = 0, seq = 0;
    const now=watch.now||(()=>Date.now());
    const arm=watchWorkers(ws,()=>watch.limit?watch.limit(runs):240000,()=>!dead,
      ready=>fail(Object.assign(new Error(ready?'모의 전투 무진행 시간 초과':'계산 엔진 준비 시간 초과'),{gwenCause:'timeout'})),
      {...watch,loadMs:watch.loadMs||(()=>180000)});
    const clean = fatal => {
      arm.cancel();ws.forEach(w=>w._job=null);
      if (!pool || fatal) resources.close();
      else ws.forEach(w => { w.onmessage = () => {}; w.onerror = () => {}; });
    };
    const fail = err => { err.gwenCause ||= "calculation"; if (dead) return; dead = true; clean(true); rejectFn(err); };
    const p = new Promise((resolve, reject) => {
      rejectFn = reject;
      if (!jobs.length) { dead = true; resolve(res); return; }
      try { parts.forEach((part, wi) => {
        if (dead) return;
        const w = resources.get(wi); ws.push(w);
        let requestId,pending=new Map(),left=0,active=false;
        const send = list => {
          requestId = pool ? pool.nextId() : ++seq;
          pending=new Map();for(const j of list)pending.set(j.key,(pending.get(j.key)||0)+1);
          left=list.length;active=true;w._job=requestId;w._last=now();arm();
          try { w.postMessage({type: "run", id: requestId, base, stage, n_runs: runs, seed, options: options || {build: "standard", rules_override: {power_penalty: "model"}},
            teams: list.map(j => ({key: j.key, party: j.party, options: j.options}))}); }
          catch (e) { fail(e); }
        };
        w.onmessage = e => {
          const m = e.data; if (dead || !active || (m.id != null && m.id !== requestId) || (m.requestId!=null&&m.requestId!==requestId)) return;
          try{
            if((m.type==='team'||m.type==='done')&&m.id!==requestId)throw new Error('요청 id가 없는 계산 응답');
            if(m.type==='stage'){if(m.msg==='준비 끝')w._ready=true;w._last=now();arm();}
            else if (m.type === "team") {
              if(!(pending.get(m.key)>0)||!m.result||typeof m.result!=='object')throw new Error('누락·중복 또는 요청 밖 계산 결과');
              pending.set(m.key,pending.get(m.key)-1);left--;
              res[m.key] = project(m.result);w._ready=true;w._last=now();arm();
              if(onResult)onResult(m.key,m.result); done++; if (onProgress) onProgress(done, jobs.length);
            }
            else if (m.type === "done") {
              if(left)throw new Error('계산 결과가 누락된 채 작업이 끝남');
              active=false;w._job=null;arm();
              if(dyn&&next<jobs.length){const l=jobs.slice(next,next+chunk);next+=l.length;send(l);}
              else if(++finished===parts.length){dead=true;clean(false);resolve(res);}
            }
            else if (m.type === "error") fail(new Error(m.msg || "작업자 오류"));
          }catch(err){fail(err);}
        };
        w.onerror = ev => fail(new Error("작업자 오류: " + (ev && ev.message || "알 수 없음")));
        if (dyn) { const l = jobs.slice(next, next + chunk); next += l.length; send(l); return; }
        send(part);
      }); } catch (e) { fail(e); }
    });
    return {promise: p, snapshot:()=>({...res}), cancel() { if (dead) { if (pool) pool.close(); return; } fail(Object.assign(new Error("취소"),{gwenCause:"cancel"})); }};
  }
  function etaNew(o) {
    const W = o.weights.slice(), warm = o.warmup == null ? 3 : o.warmup, win = o.window == null ? 20 : o.window, prior = o.prior || null, GAP = 0.25, blend = o.blend == null ? 0 : o.blend, frac = o.winFrac == null ? 0 : o.winFrac;
    const st = o.stages.map(s => ({games: s.games, done: 0, samples: [], cur: null, first: null, c: null, cAvg: null, lat: null, startT: null}));
    let cur = -1;
    const obs = s => s.cAvg != null && s.done >= s.games ? s.cAvg : s.c;      // 끝난 단계는 구간 전체 평균(더 안정적), 진행 중이면 최근 구간
    function begin(i, games, t) {
      if(i==null||!st[i]){cur=-1;return;}
      if (i === cur && st[i].done > 0) { if (games != null) st[i].games = games; return; }
      cur = i; const s = st[i];
      if (games != null) s.games = games;
      s.startT = t; s.done = 0; s.samples = []; s.cur = null; s.first = null;
    }
    function update(done, t) {
      const s = st[cur]; if (!s) return;
      s.done = done;
      if (s.first == null) { if (done > 0) { s.first = {t, g: done}; s.lat = t - s.startT; s.samples = [{t, g: done}]; s.cur = {t, g: done}; } return; }
      s.cur = {t, g: done};
      const last = s.samples[s.samples.length - 1], el = t - s.first.t, span = Math.max(win, frac * el);
      if (t - last.t >= Math.max(GAP, 0.02 * el)) s.samples.push({t, g: done});          // 오래 갈수록 표본 간격을 늘려 개수를 제한
      while (s.samples.length > 2 && s.samples[1].t < t - 2 * span) s.samples.shift();
      if (done > s.first.g && t > s.first.t) s.cAvg = (t - s.first.t) / (done - s.first.g);
      if (el >= warm) {
        let ref = s.samples[0];
        for (const x of s.samples) { if (x.t >= t - span) { ref = x; break; } ref = x; }
        if (ref.t >= t) ref = s.first;
        if (done > ref.g && t > ref.t) s.c = (t - ref.t) / (done - ref.g);
      }
    }
    // 단계 s 의 한 판 비용(초). 기준 = 자기 실측 > 가장 가까운 이전 단계 실측 × 가중치 비 > 저장된 prior > 없음
    function cost(s) {
      if (s <= cur && obs(st[s]) != null) {
        const m = obs(st[s]);
        // 저장된 속도가 있으면 측정 초반(blend 초)에는 둘을 섞는다: 초반 속도는 엔진 데워지는 중이라 낮게 나옴
        if (prior && prior[s] > 0 && s === cur && st[s].cur && blend > 0) { const a = Math.min(1, (st[s].cur.t - st[s].first.t) / blend); return a * m + (1 - a) * prior[s]; }
        return m;
      }
      for (let r = Math.min(cur, st.length - 1); r >= 0; r--) { const c = obs(st[r]); if (c != null) return c * W[s] / W[r]; }
      return prior && prior[s] > 0 ? prior[s] : null;
    }
    function estimate(t) {
      if (cur < 0) return {ready: false};
      let lat = 0;
      for (let i = st.length - 1; i >= 1; i--) if (st[i].lat != null) { lat = st[i].lat; break; }
      let rem = 0;
      for (let s = cur; s < st.length; s++) {
        const c = cost(s); if (c == null) return {ready: false};
        const left = s === cur ? Math.max(0, st[s].games - st[s].done) : st[s].games;
        rem += left * c + (s > cur ? lat : 0);
      }
      return {ready: true, remainSec: rem, finishAt: t + rem, stage: cur, cost: st.map((_, s) => cost(s))};
    }
    // 저장용: 단계별 초/판(실측 없는 단계는 실측 있는 단계 × 가중치 비). 실측이 하나도 없으면 null
    function summary() {
      let ref = -1;
      st.forEach((s, i) => { if (s.cAvg != null) ref = i; });      // 가장 나중에 실측한 단계를 기준으로 비어 있는 단계를 채운다
      if (ref < 0) return null;
      return st.map((s, i) => s.cAvg != null ? s.cAvg : st[ref].cAvg * W[i] / W[ref]);
    }
    return {begin, update, estimate, summary, state: () => ({cur, st})};
  }
// 화면 갱신 간격 제한(11/22, 훑기 A-1): 첫 호출은 바로, 그 뒤 ms 안의 호출은 끝에 한 번만(live() 가 거짓이면 버림).
//  대기는 최대 ms — 시계가 뒤로 가도(last 가 미래) 진행 표시가 멈추지 않음.
//  표시만 늦을 뿐 결과·순위·배차는 그대로. flush = 밀린 것 바로 실행, cancel = 버림. env.trailing=false 면 끝 호출을 버림(타이머 없음 — 다른 갱신이 곧 덮어쓸 때)
function throttle(fn,ms=200,live=()=>true,env={}){const now=env.now||(()=>Date.now()),setTimer=env.setTimer||((...a)=>setTimeout(...a)),clearTimer=env.clearTimer||((...a)=>clearTimeout(...a)),trailing=env.trailing!==false;
 let last=-Infinity,timer=null;
 const run=()=>{timer=null;last=now();if(live())fn()};
 const f=()=>{if(timer!=null)return;const wait=last+ms-now();if(wait<=0){run();return}if(trailing)timer=setTimer(run,Math.min(ms,wait))};
 f.flush=()=>{if(timer!=null){clearTimer(timer);run()}};f.cancel=()=>{if(timer!=null)clearTimer(timer);timer=null};return f}
function timedWorker(env){
  const raw=createWorker();let timer=null,ready=false,runs=1;
  const wrapper={onmessage:null,onerror:null,postMessage(message){runs=message.n_runs;arm();raw.postMessage(message);},
    terminate(){clearTimeout(timer);raw.terminate();}};
  function arm(){clearTimeout(timer);timer=setTimeout(()=>wrapper.onerror?.({message:'시간 초과'}),ready?env.limit(runs):env.loadMs());}
  raw.onmessage=e=>{if(e.data.type==='done'||e.data.type==='error')clearTimeout(timer);
    else {if(e.data.msg==='준비 끝'||e.data.type==='team')ready=true;arm();}wrapper.onmessage?.(e);};
  raw.onerror=e=>{clearTimeout(timer);wrapper.onerror?.(e);};return wrapper;
}

 // 묶음 크기(훑기·예선): 코스모 식 min(50, ceil(팀 수/(작업자×40))) — 작업자마다 40묶음 이상 남겨 끝이 고르게. 8개·10,626팀이면 34팀, 120팀이면 1팀(지금과 같음)
 const chunkSize=(teams,workers)=>Math.max(1,Math.min(50,Math.ceil(teams/(Math.max(1,workers)*40))));
 const PAINT_MS=200;      // 훑기·예선 진행 표시 갱신 간격(ms, throttle)
 const api={createWorker,planStages,shared,split,workerPool,runPhase,etaNew,timedWorker,throttle,chunkSize,PAINT_MS};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.SearchExecutor=api;
})(typeof window!=='undefined'?window:globalThis);
