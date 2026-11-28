// node tests/fullscreen_test.js
// 후보 전체 훑기(항상 켬, 스위치 없음 — docs/fullscreen_measure_1121.md)
//  깰 수 있는 팀 있음(쉬운 스테이지): 훑기 없이 예선만(8판 → 32판), 예선 상태에 훑기 필드도 안 붙음.
//  전원 «못 깸»: 후보 전체 1판 → 상위 «예선 후보 수» → 예선 8판(훑기 1판에 7판 이어 돌리기) → 32판(24판 이어 돌리기). 화면 경로(simScreen)·직접 편성 묶음 경로(recoCalculate) 둘 다.
//  빠른 관측(11/22): 훑기 진입 직후 0.8초는 경보 대신 «[SCAN] 빠른 관측 — 후보 N개 판정 중…» → «[RESULT] 돌파 가능 0개», 그 뒤 경보. 쉬운 스테이지엔 없음, 그 사이 멈춤·취소 정상(가짜 시계).
//  관측 경보(SCR_ALERT, 11/22): 훑기 진입 시 켜짐 · 쉬운 스테이지는 꺼짐 · 끝나거나 멈추면 꺼짐(화면·직접 편성 묶음 둘 다).
//  강제 탐색: 훑는 동안 진행 칸에 시스템 메시지 줄(글만 — 그웬 그림 없음), 끝·멈춤·쉬운 스테이지엔 없음. 판정 «관리 실패»(0%) / «루트 확보»(0 초과) / 훑기 없음 = 표시 없음.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(ROOT,'party_template.html'),'utf8'),rt=fs.readFileSync(path.join(ROOT,'recommend_runtime.js'),'utf8');
const section=(s,a,b)=>{const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i,'구간 없음: '+a);return s.slice(i,j)};
const CFG0=require('../party_contents.json');
// F 동결 계약은 학습 합집합만 끈다. 기존 훑기 자체는 항상 켬.
CFG0.recommendation={...CFG0.recommendation,learnedUnion:{...CFG0.recommendation?.learnedUnion,value:false}};
const plain=x=>JSON.parse(JSON.stringify(x));
const mk=(keys,vd,v)=>({keys,combo:keys.map(key=>({s:{key}})),vd,v,q:{rounds:1,left:0}});
const NAMES=Array.from({length:200},(_,i)=>'t'+String(i).padStart(3,'0'));
const keyOf=k=>['a','b','c',k].sort().join(',');
// 진행도: 빠른 계산 뒤쪽(t150~)이 실제로는 강함 — 훑기가 없으면 예선 후보(80)에 못 듦
const progOf=key=>{const m=key.match(/t(\d{3})/),i=+m[1];return i>=150?0.5+i/1000:0.1+i/10000};
function teamsOf(vds){return NAMES.map((k,i)=>mk(['a','b','c',k],vds(i),200-i))}

// ── 화면 경로(simScreen) ── 가짜 작업자는 요청마다 바로 결과·done 을 돌려줌
function screenRun(vds,{stopAfter=null,clock=null}={}){
 // clock = 가짜 시계({t}) — 빠른 관측처럼 시간으로 넘어가는 단계를 시험이 직접 넘김. timers = 걸린 setTimeout(ms) 기록
 const FakeDate=clock?class extends Date{static now(){return clock.t}}:Date,timers=[],dom={n:0};
 const posts=[],teams=teamsOf(vds),CFG=plain(CFG0);
 const c=vm.createContext({UiShared:require('../ui_shared'),PartyPlacement:require('../party_placement'),GwenLane:require('../gwen_lane'),CFG,recommendationPolicyTag:()=>[],PLACEMENT_CACHE:{has:()=>true},console,MODE:'auto',MM:'',MI:{pending:null},miMode:()=>false,
  SIMQ:{n:100,seed:1,busy:null,res:{},scr:{},LOAD_MS:180000,RUN_MS:240000},LASTQ:{1:{rows:teams.slice(0,3),all:teams,total:teams.length}},cur:[{tab:'a',name:'b'}],
  contents:[{key:'op'}],$:()=>({value:'0'}),rkOf:()=>0,starOf:()=>0,simParty:t=>({units:t.keys}),teamBreak:()=>null,brkLv:()=>1,
  simMain:r=>r,simCls:()=>'',esc:String,simOpt:()=>({}),document:{querySelector:()=>{dom.n++;return null},hidden:false},
  navigator:{hardwareConcurrency:3,deviceMemory:8},location:{href:'https://test/index.html'},Date:FakeDate,performance:{now:()=>0},
  setTimeout:(f,ms)=>{timers.push({f,ms});return 0},clearTimeout(){},run(){},
  Worker:class{postMessage(req){posts.push({req,msg:c.SIMQ.msg});const send=m=>this.onmessage({data:{id:req.id,job:req.job,...m}});
   if(stopAfter!=null&&posts.length>stopAfter){this.parked=req;return}
   send({type:'stage',id:undefined,msg:'준비 끝'});
   for(const [i,t] of req.teams.entries()){const k=t.key,n=req.n_runs+(t.options.run_offset||0),p=progOf(k);send({type:'stage',msg:`시뮬 ${i+1}/${req.teams.length}팀`});
    send({type:'team',key:k,result:{n,clear:0,prog:p,progs:[p],via:{coop:0},ttk:20,...(t.options.raw_runs||t.options.merge_raw?{raw:'[raw'+n+']'}:{})}})}send({type:'done'})}
   terminate(){this.stopped=true}}});
 vm.runInContext(fs.readFileSync(require.resolve('../search_executor.js'),'utf8'),c);
 for(const [a,b] of [['const simSigB=','// 표시 상태는'],['function simInvalidate()','// 자동 확인'],
  ['function simStart(',"document.querySelectorAll('input[name=\"runs\"]')"],['const SCR_ROUNDS=','function simWaiting(']])vm.runInContext(section(html,a,b),c);
 // 진행 칸(simProgress)도 실제 코드로 그림 — 그웬 호출(recoGwenShow)은 받은 경보 값만 적어 둠
 Object.assign(c,{gwen:[],recoGwenShow:(...a)=>c.gwen.push(a[4]||''),growthEnabled:()=>false,Ux:{help:()=>''},simEtaText:()=>'',simSig:(st,t)=>t.keys.join(),SCR_N:8});
 vm.runInContext(section(html,'function simProgress(st)','function buildCands('),c);
 assert.equal(vm.runInContext('simScreen(1)',c),true);
 return {c,posts,timers,dom,card:()=>vm.runInContext('simProgress(cur[0])',c),alert:now=>vm.runInContext(`scrAlertOf(Object.values(SIMQ.scr)[0]${now?','+now:''})`,c),sc:()=>plain(Object.values(c.SIMQ.scr)[0]),ev:s=>vm.runInContext(s,c)};
}
// 요청 하나에 팀 여럿(묶음, A-2)일 수 있음 → 팀 단위로 펼쳐 비교
const legs=posts=>{const out=[];for(const p of posts){const n=p.req.n_runs,last=out[out.length-1],ks=p.req.teams.map(t=>t.key);if(last&&last.n===n)last.keys.push(...ks);else out.push({n,keys:[...ks]})}return out};
const sizes=(posts,n)=>posts.filter(p=>p.req.n_runs===n).map(p=>p.req.teams.length);
const PRE_TIMERS=[450+16,800+16];   // 빠른 관측 두 전환 시각(SCR_ALERT.preStepMs·preMs + 16)
const hard=()=>'hard',easy=i=>i===5?'tight':'hard';

{
 // 쉬운 스테이지(깰 수 있는 팀 있음) = 훑기 없이 예선만, 상태에 훑기 필드 없음
 const onE=screenRun(easy),L=legs(onE.posts);
 assert.deepEqual(L.map(x=>[x.n,x.keys.length]),[[8,80],[24,20]],'쉬운 스테이지: 예선만(8판 80팀 → 24판 20팀)');
 assert(!('full' in onE.sc())&&!('res0' in onE.sc()),'쉬운 스테이지: 예선 상태에 훑기 필드 없음');
 assert(!L[0].keys.includes(keyOf('t199')),'쉬운 스테이지: 뒤쪽 팀은 예선 후보 밖(빠른 계산 순 그대로)');
 assert(sizes(onE.posts,8).every(x=>x===1),'쉬운 스테이지: 묶음 없음');
 // 전원 못 깸 = 훑기 단계 추가
 const on=screenRun(hard),M=legs(on.posts),sc=on.sc();
 assert.deepEqual(M.map(x=>[x.n,x.keys.length]),[[1,200],[7,80],[24,20]],'켬: 1판 200팀 → 7판 80팀(훑기 1판에 이어) → 24판 20팀');
 // 묶음(A-2): 작업자 2개(코어 3) → 훑기 200팀은 ceil(200/80)=3팀씩, 예선 80팀·20팀은 1팀씩(지금과 같음)
 assert.deepEqual([...new Set(sizes(on.posts,1).slice(0,-1))],[3],'훑기는 3팀 묶음');assert.equal(sizes(on.posts,1).reduce((a,b)=>a+b),200);
 assert(sizes(on.posts,7).every(x=>x===1)&&sizes(on.posts,24).every(x=>x===1),'예선은 묶음 1(지금과 같음)');
 assert.deepEqual(M[0].keys,teamsOf(hard).map(t=>keyOf(t.keys[3])),'훑기는 빠른 계산 순서 그대로 전부');
 assert(on.posts.filter(p=>p.req.n_runs===1).every(p=>p.req.teams.every(t=>t.options.raw_runs===true&&!t.options.run_offset&&!t.options.merge_raw)),'훑기는 raw 를 받음(1차가 이어 씀)');
 // 1차는 훑기 1판을 0번째 판으로 다시 씀: 그 팀의 훑기 raw 를 되돌려 보내고 run_offset 1 부터 7판(합친 값 = 8판 한 번, tests/screen_merge_test.py test_scan_reuse)
 assert(on.posts.filter(p=>p.req.n_runs===7).every(p=>p.req.teams[0].options.run_offset===1&&p.req.teams[0].options.merge_raw==='[raw1]'&&!p.req.teams[0].options.raw_runs),'1차는 훑기 1판에 이어 돌림');
 assert(onE.posts.filter(p=>p.req.n_runs===8).every(p=>p.req.teams[0].options.raw_runs===true&&!p.req.teams[0].options.run_offset),'쉬운 스테이지 1차는 지금처럼 8판 처음부터');
 assert(Object.values(sc.res).every(r=>r.n===8),'1차 결과는 8판짜리');
 assert(on.posts.filter(p=>p.req.n_runs===24).every(p=>p.req.teams[0].options.run_offset===8&&p.req.teams[0].options.merge_raw),'2차는 1차 8판에 이어 돌림');
 assert.equal(sc.fullDone,true);assert.equal(sc.fullN,80);assert.equal(sc.pool.length,80);assert.equal(sc.total,80);
 const want=NAMES.slice(150).map(keyOf).reverse();
 assert.deepEqual(sc.pool.slice(0,50),want,'예선 후보 = 1판 결과 순(진행도 높은 뒤쪽 팀부터)');
 assert.equal(sc.order[0],keyOf('t199'),'최종 예선 1위 = 진행도 최고');
 assert.equal(sc.done,true);assert.equal(sc.short,false);
 const of=n=>on.posts.filter(p=>p.req.n_runs===n);
 assert(of(1).slice(1).every(p=>/^세계선 [\d,]+ \/ 200$/.test(p.msg)),'훑는 동안 진행 문구');
 // 관측 경보: 다 끝나면 꺼짐(쉬운 스테이지는 처음부터 끝까지 꺼짐)
 assert.equal(on.alert(),'','끝나면 경보 꺼짐');assert.equal(onE.alert(),'');
 // 판정 표시(결과 위 한 줄): 훑기를 끝까지 한 스테이지만 — 1안 0% = 관리 실패, 0 초과 = 루트 확보. 쉬운 스테이지·결과 없음 = 표시 없음
 const verdict=(r,x)=>r.ev(`scrVerdict(Object.values(SIMQ.scr)[0],${x})`);
 assert.match(verdict(on,'{clear:0}'),/^<div class="scr-verdict" data-k="scr-verdict" data-verdict="fail" role="status"><b>관리 실패<\/b><span>현 전력으로 돌파 불가 — 성장 후 재관측 권장<\/span><\/div>$/);
 assert.match(verdict(on,'{clear:.01}'),/data-verdict="ok" role="status"><b>루트 확보<\/b>/);assert(!/관리 실패/.test(verdict(on,'{clear:.01}')));
 for(const x of ['{clear:0}','{clear:1}'])assert.equal(verdict(onE,x),'','훑기 없음: 판정 표시 없음');
 assert.equal(verdict(on,'undefined'),'','본선 결과가 아직 없으면 표시 없음');
 assert.match(html,/\$\{miVerdict\(shown,st\)\}\$\{scrVerdict\(SIMQ\.scr\[scrKey\(st,p\)\],SIMQ\.res\[simSig\(st,rows\[0\]\)\]\)\}\$\{scrNote\(p,st\)\}/,'결과 요약(1안 기준)에 판정 줄');
 assert(of(7).slice(1).every(p=>/^후보 거르는 중/.test(p.msg)),'예선 진행 문구');
}
// 관측 경보 — 쉬운 스테이지: 계산 도중에도 꺼져 있고 진행 칸에 경보 흔적이 없음
{
 const onE=screenRun(easy,{stopAfter:30});assert.equal(onE.alert(),'','쉬운 스테이지: 경보 꺼짐');const h=onE.card();
 assert(!/data-alert|scr-alert|al-deco|세계선|경보|fx-|forced|SYSTEM|SCAN|RESULT|빠른 관측/.test(h),'쉬운 스테이지: 진행 칸에 경보 흔적 없음');assert.match(h,/<b class="case-title">추천 편성 확인 중<\/b>/);assert.match(h,/후보 거르는 중 \d+\/80/);
 assert.deepEqual([...new Set(onE.c.gwen)],[''],'그웬 길에도 경보 안 넘김');
 assert(!onE.timers.some(t=>PRE_TIMERS.includes(t.ms)),'쉬운 스테이지: 빠른 관측 단계도 없음(전환 예약 없음)');
}
// 관측 경보 — 훑기 진입: 켜짐(진행 칸·그웬 길), 숫자는 «세계선 n / N»
{
 const T={t:1e12},on=screenRun(hard,{stopAfter:30,clock:T});
 assert.match(on.c.SIMQ.msg,/^세계선 \d+ \/ 200$/);assert.equal(on.sc().round,-1);
 // 빠른 관측(가짜 시계): 진입 직후 preMs(0.8초) 동안은 경보 대신 평소 진행 칸 + 기록 줄 «[SCAN] …» → 0.45초 뒤 «[RESULT] 돌파 가능 0개» → 0.8초에 경보.
 //  훑기 배차는 이 표시와 동시에 이미 시작(시간 손실 0), 그웬 길엔 안 넘김(평소 SD 그웬)
 {assert.deepEqual([on.ev('SCR_ALERT.preMs'),on.ev('SCR_ALERT.preStepMs')],[800,450]);
  assert.equal(on.alert(),'pre','훑기 진입 직후: 빠른 관측');assert.equal(on.sc().alertAt,T.t+800);
  assert(on.posts.length>30&&on.posts.every(p=>p.req.n_runs===1),'빠른 관측 동안 훑기 배차는 이미 시작');
  const p1=on.card();assert.match(p1,/data-k="progress" data-state="running" data-alert="pre"><b class="case-title">추천 편성 확인 중<\/b><div class="fx-log" data-k="fx-log" data-line="p1" aria-hidden="true"><code>\[SCAN\] 빠른 관측 — 후보 200개 판정 중…<\/code><\/div>/,'1단계: 평소 제목 + [SCAN] 줄');
  assert(!/scr-alert|al-deco|data-alert-enter|RESULT|승리 좌표/.test(p1),'1단계: 경보 흔적 없음');assert.equal(on.c.gwen.at(-1),'','빠른 관측 동안 그웬 길은 평소');
  assert.match(p1,/data-scrstop="1">지금까지 결과로 보기<\/button> <button type="button" class="sec" data-simcancel="1">취소</,'빠른 관측 동안에도 멈춤·취소 단추');
  assert.equal(on.ev('SCR_ALERT.pre[0](UiShared.numText(10626))'),'[SCAN] 빠른 관측 — 후보 10,626개 판정 중…');
  T.t+=449;assert.match(on.card(),/data-line="p1"/);T.t+=1;
  const p2=on.card();assert.match(p2,/data-alert="pre">.*data-line="p2" aria-hidden="true"><code>\[SCAN\] 빠른 관측 — 후보 200개 판정 중…<br><b>\[RESULT\] 돌파 가능 0개<\/b><\/code>/,'2단계: [RESULT] 줄이 붙음');
  assert(!/scr-alert|al-deco|승리 좌표/.test(p2));assert.equal(on.c.gwen.at(-1),'');
  assert.deepEqual(on.timers.map(t=>t.ms).filter(ms=>PRE_TIMERS.includes(ms)),PRE_TIMERS,'두 전환 시각에 진행 칸 갱신 예약(작업자 소식이 없어도 넘어감)');
  {const n=on.dom.n;for(const t of on.timers.filter(t=>PRE_TIMERS.includes(t.ms)))t.f();assert.equal(on.dom.n,n+2,'예약된 갱신이 진행 칸을 찾음');}
  T.t+=349;assert.equal(on.alert(),'pre');T.t+=1;}
 assert.equal(on.alert(),'scan','빠른 관측 뒤: 경보 켜짐');
 const h=on.card();
 assert.match(h,/data-k="progress" data-state="running" data-alert="scan" data-alert-enter>/,'진입 직후: 경보 + 깜빡임 표시');
 assert.match(h,/<b class="case-title">⚠ 승리 좌표 미검출<\/b><p class="scr-alert" data-k="scr-alert">강제 탐색 프로토콜 — 다른 세계선을 뒤지는 중<small>/);
 assert.match(h,/<span data-k="simstate"[^>]*>세계선 \d+ \/ 200<\/span>/);
 assert.match(h,/data-scrstop="1">지금까지 결과로 보기<\/button> <button type="button" class="sec" data-simcancel="1">취소</,'멈춤·취소 단추 그대로');
 assert.equal(on.c.gwen.at(-1),'scan','그웬 길에 경보 넘김');
 // 강제 탐색: 진행 칸의 기록 줄 = 시스템 메시지만(그웬 그림 없음 — 그웬은 화면에 한 곳). 줄은 진행률 순서, 숫자는 그 줄이 뜰 때 값
 {const log=h.match(/<div class="fx-log" data-k="fx-log" data-line="(\d)" aria-hidden="true"><code>(\[[A-Z]+\] [^<]+)<\/code><\/div>/);
  assert(log,'훑기 진입: 시스템 메시지 줄');assert(!/<img|url\(|assets\//.test(h),'진행 칸에 그림 없음');const sc=on.sc(),line=on.c.GwenLane.forcedLine(sc.got,sc.left);assert.equal(+log[1],line.i);assert.equal(log[2],line.text);
  assert.equal(on.c.GwenLane.forcedLine(3412,10626).text,'[WARN] 관측 범위 외 기억 참조 중');assert.equal(on.c.GwenLane.forcedLine(4000,10626).text,'[ROUTE] 루트 강제 개방… 10,626개 중 4,000개 검증');
  const seen=[];for(let g=0;g<=200;g++){const l=on.c.GwenLane.forcedLine(g,200);if(seen.at(-1)!==l.i)seen.push(l.i);assert.match(l.text,/^\[(SYSTEM|ACK|WARN|ROUTE|LOG)\] /);assert(!/[{}]/.test(l.text));}
  assert.deepEqual(seen,[0,1,2,3,4,5,6,7],'진행률에 따라 한 줄씩 순서대로');
  // 줄 번호가 같으면 그대로, 바뀌면 그 줄만 바꿈(단추 DOM 은 안 건드림)
  const node={dataset:{line:'2'},outerHTML:''},cardEl={querySelector:q=>q==='[data-k="fx-log"]'?node:null};on.c.cardEl=cardEl;
  on.ev(`scrLogSync(cardEl,'<div data-line="2">같은 줄</div>')`);assert.equal(node.outerHTML,'');on.ev(`scrLogSync(cardEl,'<div data-line="3">다음 줄</div>')`);assert.match(node.outerHTML,/다음 줄/);}
 // 들어온 지 오래면 깜빡임 표시는 안 붙음(다시 그려도 반복 안 함)
 on.ev('Object.values(SIMQ.scr)[0].alertAt-=5000');assert(!/data-alert-enter/.test(on.card()));assert.match(on.card(),/data-alert="scan"/);
 assert.equal(on.ev('scrMsg(-1,3412,10626)'),'세계선 3,412 / 10,626');assert.equal(on.ev('scrMsg(0,3,80)'),'후보 거르는 중 3/80');
 // 「지금까지 결과로 보기」: 1판 결과 순으로 닫고 short, 안내 문구
 on.ev('scrStop()');const sc=on.sc();
 assert.equal(sc.done,true);assert.equal(sc.short,true);assert.equal(sc.fullDone,false);
 assert.equal(on.alert(),'','멈추면 경보 꺼짐');assert.equal(sc.round,-1);
 assert.equal(on.ev('scrAlertHtml(scrAlertOf(Object.values(SIMQ.scr)[0]),Object.values(SIMQ.scr)[0])'),'','멈추면 기록 줄 없음(원래 경로)');
 assert.equal(on.ev('scrVerdict(Object.values(SIMQ.scr)[0],{clear:0})'),'','중간에 멈춘 훑기: 판정 표시 없음');
 assert(sc.order.length>0&&sc.order.length<200);
 const got=Object.keys(sc.res0);assert.deepEqual(sc.order,got.slice().sort((a,b)=>progOf(b)-progOf(a)));
 assert.match(on.ev('scrNote(1,cur[0])'),/후보 전체 200팀 중 \d+팀만 훑었음/);
 // 「끝까지 확인」: 남은 훑기만 이어서
 const before=on.posts.length,seen=new Set(got);
 assert.equal(on.ev('simScreen(1,true)'),true);
 const first=on.posts.slice(before).map(p=>p.req);assert(first.length>0);
 assert(first.every(r=>r.n_runs===1&&!seen.has(r.teams[0].key)),'이미 훑은 팀은 다시 안 돎');
 assert.equal(on.alert(),'scan','이어서 훑으면 경보 다시 켜짐');
}
// 관측 경보 — 훑기가 끝나 예선으로: 잠깐 «기억 N개 회수», 그 뒤 원래대로
{
 const on=screenRun(hard,{stopAfter:80});   // 훑기 67요청(3팀 묶음) 뒤 예선 도중에 멈춘 상태
 const sc=on.sc();assert.equal(sc.fullDone,true);assert.equal(sc.round,0);assert.equal(sc.done,false);
 assert.equal(on.alert(sc.foundAt+100),'found');assert.equal(on.alert(sc.foundAt+on.ev('SCR_ALERT.foundMs')+1),'','전환 문구 시간이 지나면 꺼짐');
 const h=on.card();assert.match(h,/data-alert="found"/);assert.match(h,/<b class="case-title">추천 편성 확인 중<\/b><p class="scr-alert" data-k="scr-alert" aria-live="polite">✦ 돌파 가능성 있는 기억 80개 회수 — 구원자 편성 다시 정렬<\/p>/);
 assert(!/al-deco|data-alert-enter|fx-log/.test(h),'훑기가 끝나면 기록 줄 없음');assert.match(h,/후보 거르는 중 \d+\/80/);
 on.ev('Object.values(SIMQ.scr)[0].foundAt-=60000');assert(!/data-alert|scr-alert/.test(on.card()),'시간이 지나면 원래 진행 칸');
 // 이미 그려진 칸에 켜고 끄기(직접 편성 묶음 경로 scrAlertSync): 상태가 같으면 DOM 을 안 건드림
 const title={textContent:'추천 편성 확인 중',after:'',insertAdjacentHTML(_,x){this.after=x}};let writes=0;const logEl={dataset:{line:'0'},outerHTML:''};
 const card={dataset:{},attrs:{},head:'',querySelectorAll:()=>[{remove(){writes++}}],toggleAttribute(k,v){this.attrs[k]=v},querySelector:q=>q==='.case-title'?title:q==='[data-k="fx-log"]'?logEl:null,insertAdjacentHTML(_,x){this.head=x}};
 on.c.card=card;const sync=s=>on.ev(`scrAlertSync(card,${s})`);
 assert.equal(sync('{full:[1],round:-1,alertAt:Date.now(),pool:[]}'),'scan');assert.equal(card.dataset.alert,'scan');assert.equal(card.attrs['data-alert-enter'],true);
 assert.match(title.textContent,/^⚠ 승리 좌표 미검출/);assert.match(title.after,/scr-alert/);assert.match(title.after,/data-k="fx-log" data-line="0"/,'묶음 진행 칸에도 기록 줄');assert.match(card.head,/al-deco/);
 const w=writes;sync('{full:[1],round:-1,alertAt:Date.now(),pool:[]}');assert.equal(writes,w,'같은 상태면 그대로 둠');assert.equal(logEl.outerHTML,'','같은 줄이면 기록 줄도 그대로');
 sync('{full:[1],round:-1,alertAt:Date.now(),pool:[],got:150,left:200}');assert.equal(writes,w);assert.match(logEl.outerHTML,/data-line="6".*\[ROUTE\] 잔여 세계선 50개/,'진행률이 넘어가면 기록 줄만 바뀜');
 // 빠른 관측(묶음 진행 칸): 평소 제목 + [SCAN] 줄 → 같은 상태에서 단계가 넘어가면 줄만 바뀜 → 시간이 되면 경보로
 {sync('undefined');card.head='';logEl.dataset.line='p1';logEl.outerHTML='';const w0=writes,sc=n=>`{full:[1,2,3],round:-1,alertAt:Date.now()+${n},pool:[]}`;
  assert.equal(sync(sc(800)),'pre');assert.equal(card.dataset.alert,'pre');assert.equal(card.attrs['data-alert-enter'],false);assert.equal(title.textContent,'추천 편성 확인 중');
  assert.match(title.after,/^<div class="fx-log" data-k="fx-log" data-line="p1" aria-hidden="true"><code>\[SCAN\] 빠른 관측 — 후보 3개 판정 중…<\/code><\/div>$/);assert.equal(card.head,'','빠른 관측엔 경보 장식 없음');
  const w1=writes;assert(w1>w0);assert.equal(sync(sc(700)),'pre');assert.equal(logEl.outerHTML,'');assert.equal(sync(sc(200)),'pre');assert.equal(writes,w1);assert.match(logEl.outerHTML,/data-line="p2".*<b>\[RESULT\] 돌파 가능 0개<\/b>/,'단계가 넘어가면 기록 줄만 바뀜');
  assert.equal(sync(sc(0)),'scan');assert.equal(card.attrs['data-alert-enter'],true,'경보로 넘어갈 때 진입 깜빡임 그대로');assert.match(title.textContent,/^⚠ 승리 좌표 미검출/);assert.match(card.head,/al-deco/);
  assert.equal(on.ev('scrAlertLane("pre")'),'');assert.equal(on.ev('scrAlertLane("scan")'),'scan');assert.equal(on.ev('scrAlertLane("found")'),'found');}
 assert.equal(sync('{full:[1],round:-1,done:true,pool:[]}'),'');assert(!('alert' in card.dataset));assert.equal(title.textContent,'추천 편성 확인 중');assert.equal(title.after,'');assert.equal(card.attrs['data-alert-enter'],false);
 assert.equal(sync('undefined'),'');assert.equal(sync('{round:0,pool:[]}'),'','쉬운 스테이지(훑기 필드 없음)');
}
// 빠른 관측 도중(0.8초 안)에 「지금까지 결과로 보기」: 평소 멈춤 처리 그대로, 예약된 갱신은 아무것도 안 함. 이어 훑을 때는 빠른 관측 없이 바로 경보
{
 const T={t:1e12},on=screenRun(hard,{stopAfter:30,clock:T});T.t+=300;assert.equal(on.alert(),'pre');
 on.ev('scrStop()');const sc=on.sc();assert.equal(sc.done,true);assert.equal(sc.short,true);assert.equal(sc.fullDone,false);assert(sc.order.length>0&&sc.order.length<200);
 assert.equal(on.alert(),'','빠른 관측 중 멈춤: 표시 꺼짐');assert.equal(on.ev('scrAlertHtml(scrAlertOf(Object.values(SIMQ.scr)[0]),Object.values(SIMQ.scr)[0])'),'');
 {const n=on.dom.n;for(const t of on.timers.filter(t=>PRE_TIMERS.includes(t.ms)))t.f();assert.equal(on.dom.n,n,'멈춘 뒤 예약된 갱신은 화면을 안 건드림');}
 T.t+=5000;const before=on.timers.length;assert.equal(on.ev('simScreen(1,true)'),true);
 assert.equal(on.alert(),'scan','이어 훑기: 빠른 관측 없이 바로 경보');assert(!on.timers.slice(before).some(t=>PRE_TIMERS.includes(t.ms)));assert.match(on.card(),/data-alert="scan" data-alert-enter>/);
 // 취소(simInvalidate): 빠른 관측 중에도 예선 상태가 지워지고 예약된 갱신은 아무것도 안 함
 const T2={t:1e12},on2=screenRun(hard,{stopAfter:30,clock:T2});assert.equal(on2.alert(),'pre');on2.ev('simInvalidate()');
 {const n=on2.dom.n;for(const t of on2.timers.filter(t=>PRE_TIMERS.includes(t.ms)))t.f();assert.equal(on2.dom.n,n,'취소 뒤 예약된 갱신은 화면을 안 건드림');}
}
// 훑기 중 1판 결과가 하나도 없을 때 「지금까지 결과로 보기」 = 취소
{
 const on=screenRun(hard,{stopAfter:0});on.ev('scrStop()');
 assert.equal(Object.keys(on.c.SIMQ.scr).length,0,'결과 없음 → 예선 상태 지움(지금과 같음)');
}
// 순수 함수: 조건
{
 const c=vm.createContext({UiShared:require('../ui_shared'),CFG:plain(CFG0)});vm.runInContext(section(html,'const SCR_ROUNDS=','const scrKey='),c);
 const all=[mk(['a','b','c','d'],'hard',1),mk(['a','b','c','e'],'hard',1),mk(['a','b','c','f'],'hard',1)];
 c.all=all;assert.deepEqual(plain(vm.runInContext('scrFullKeys(all,["x"])',c)),['a,b,c,d','a,b,c,e','a,b,c,f']);
 assert.equal(vm.runInContext('scrFullKeys(all,["x","y","z"])',c),null,'후보 전체가 예선 후보보다 많지 않으면 훑지 않음');
 all[2].vd='tight';assert.equal(vm.runInContext('scrFullKeys(all,["x"])',c),null,'깰 수 있는 팀 있음');
 assert.equal(vm.runInContext('scrFullKeys([],[])',c),null);
}

// ── 직접 편성 묶음 경로(recoCalculate → recoScreenCalculate → recoEvaluate, 실제 공통 실행기) ──
async function bundleRun(vds){
 const trace=[],CFG=plain(CFG0);
 const ctx=vm.createContext({UiShared:require('../ui_shared'),console,URL,Date,setTimeout,clearTimeout,CFG,navigator:{hardwareConcurrency:3},document:{hidden:false},location:{href:'https://synthetic.test/index.html'},
  SIMQ:{LOAD_MS:180000,res:{},scr:{},meta:{}},RECO:{},LASTQ:{},recoIdentity:()=> 'fixed',recoProgressPaint(){},directResultsPaint(){},simTeamLimit:()=>240000,simRateAdd(){},goalVal:r=>r?.clear,
  RecommendPipeline:require('../recommend_pipeline'),SCR_RK:0,rkQuickTop:()=>[],messages:[],
  Worker:class{postMessage(m){trace.push(plain(m));setImmediate(()=>{if(this.dead)return;const send=x=>this.onmessage({data:{...m,...x}});
   send({type:'stage',msg:'준비 끝'});for(const t of m.teams){const n=m.n_runs+(t.options?.run_offset||0),p=progOf(t.key)||0.5;
   send({type:'team',key:t.key,result:{ver:'synthetic',n,clear:0,prog:p,progs:[p],...(t.options?.raw_runs||t.options?.merge_raw?{raw:'[raw]'}:{})}})}send({type:'done'});});}terminate(){this.dead=true;}}});
 vm.runInContext(fs.readFileSync(path.join(ROOT,'search_executor.js'),'utf8'),ctx);
 vm.runInContext(section(html,'const SCR_WMAX=','// 이 기기의 시뮬 속도'),ctx);
 for(const [a,b] of [['const SCR_ROUNDS=','const scrKey='],['const scrCmp=','function scrNote('],['function recoScreenSequence(','function simWaiting(']])vm.runInContext(section(html,a,b),ctx);
 vm.runInContext(section(rt,'function recoEvaluate(','async function recoEnsure('),ctx);
 ctx.ckey=combo=>combo.map(x=>x.s.key).sort().join(',');
 let rowsN=3;const all=teamsOf(vds),task={owner:'reco',request:0,engine:'synthetic'};
 const alerts=[],laterAlert=[];
 const origEval=ctx.recoEvaluate;ctx.recoEvaluate=(s,t,jobs,n,o)=>{ctx.messages.push(o.label||(o.screen?'예선':'본선'));alerts.push(vm.runInContext('scrAlertOf',ctx)(t.sc));if(o.label)laterAlert.push(vm.runInContext('scrAlertOf',ctx)(t.sc,t.sc.alertAt));return origEval(s,t,jobs,n,o).then(()=>{texts.push(t.message)})};
 const texts=[];
 const snap={key:'fixed',c:{key:'op',parties:1},st:{tab:'a',name:'b'},seed:1,n:4,options:{},screenKey:()=> 'scr',
  plan:()=>({all,rows:all.slice(0,rowsN),total:all.length}),sig:t=>ckeyOf(t),party:t=>({units:t.keys}),breakFor:()=>null,result:t=>ctx.SIMQ.res[ckeyOf(t)],
  more(p,n){rowsN=n},meta:{parts:Array.from({length:8},()=>({}))},first:()=>null};
 const ckeyOf=t=>t.keys.slice().sort().join(',');
 ctx.RECO.task=task;await ctx.recoCalculate(snap,task);ctx.simPoolDrop('reco');
 alerts.push(vm.runInContext('scrAlertOf',ctx)(task.sc));   // 끝난 뒤
 return {trace,sc:plain(ctx.SIMQ.scr.scr),messages:ctx.messages,alerts,laterAlert,texts};
}
(async()=>{
 const on=await bundleRun(hard),onE=await bundleRun(easy);
 assert.deepEqual(legs(onE.trace.map(req=>({req}))).map(x=>[x.n,x.keys.length]),[[8,80],[24,20],[4,9]],'묶음 쉬운 스테이지: 예선 → 본선(훑기 없음)');
 assert.deepEqual(legs(on.trace.map(req=>({req}))).map(x=>[x.n,x.keys.length]),[[1,200],[7,80],[24,20],[4,9]],'묶음 전원 못 깸: 훑기 추가(1차는 훑기 1판에 이어 7판)');
 assert(on.trace.filter(m=>m.n_runs===7).every(m=>m.teams[0].options.run_offset===1&&m.teams[0].options.merge_raw==='[raw]'),'묶음 1차도 훑기 1판에 이어 돌림');
 assert.deepEqual(on.messages.slice(0,3),['세계선','예선','예선'],'진행 문구');
 assert.equal(on.texts[0],'세계선 200 / 200');assert.match(on.texts[1],/^예선 80\/80팀$/);
 // 관측 경보(묶음 경로): 훑기 시작 = scan, 예선 시작 = found(전환 문구), 끝난 뒤 = 꺼짐. 쉬운 스테이지·끔 = 늘 꺼짐
 assert.deepEqual([on.alerts[0],on.laterAlert[0],on.alerts[1],on.alerts.at(-1)],['pre','scan','found',''],'묶음 전원 못 깸: 훑기 진입 = 빠른 관측 → (0.8초 뒤) 경보 → 끝나면 꺼짐');
 assert.deepEqual([...new Set(onE.alerts)],[''],'묶음 쉬운 스테이지: 경보 꺼짐');
 {const src=f=>fs.readFileSync(path.join(ROOT,f),'utf8');
  assert.match(src('direct_bundle.js'),/const alert=scrAlertSync\(el,task\.sc\);/,'묶음 진행 칸이 경보를 맞춤');
  // 그웬 길·단계 줄에는 scrAlertLane 을 거친 값만(빠른 관측 동안은 평소 SD 그웬 — 그웬은 화면에 한 곳), 두 경로 모두 scrLegEnter 하나로
  assert.match(src('direct_bundle.js'),/recoGwenShow\([^;]*scrAlertLane\(alert\)\);/);assert.match(src('direct_bundle.js'),/scrAlertLane\(scrAlertOf\(active\.sc\)\)/);
  assert.match(src('direct_run.js'),/alert:[^,]*scrAlertLane\(scrAlertOf\(RECO\.task\.sc\)\)/);assert.match(html,/recoGwenShow\([^;]*scrAlertLane\(al\)\);/);
  assert.match(rt,/scrLegEnter\(sc,i,keys\.length,\(\)=>\{if\(RECO\.task===task\)/,'묶음 경로도 같은 함수로 전환 예약');}
 console.log('PASS fullScreen(항상 켬): 쉬운 스테이지=훑기 없음(필드 없음), 전원 못 깸=1판 전체→8→32(화면·묶음), 멈춤·이어 하기, 조건, 빠른 관측(진입 0.8초: [SCAN]→[RESULT]→경보, 쉬움 없음, 그 사이 멈춤·취소), 관측 경보(진입 켜짐·쉬움 꺼짐·끝/멈춤 꺼짐), 강제 탐색(기록 줄·판정 3경우)');
})().catch(e=>{console.error(e);process.exitCode=1;});
