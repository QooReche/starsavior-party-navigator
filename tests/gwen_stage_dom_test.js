const assert=require('node:assert/strict'),fs=require('node:fs');
const harness=require('./helpers/gwen_dom');
const read=p=>fs.readFileSync(require.resolve('../'+p),'utf8').replace(/\r\n/g,'\n');
const lane=read('gwen_lane.js'),policy=read('gwen_policy.js'),ux=read('ux_ui.js'),html=read('party_template.html'),direct=read('direct_run.js');
const section=(s,a,b)=>s.slice(s.indexOf(a),s.indexOf(b,s.indexOf(a)));
// Production component + producers. Layout supplies empty slots, never hand-built lanes.
function setup(code=lane,template=html){
  const h=harness();h.load(policy);h.load(ux);h.load(code);
  const {c}=h;h.host=h.add('reco-gwen-stage');h.add('mi-panel').hidden=true;
  h.slot=(mode,part,parent=mode==='reco'?h.host:h.doc.body)=>{const e=h.add(mode+'-'+part+'-slot',parent);e.dataset.gwenSlot=mode+'-'+part;return e;};
  for(const mode of ['direct','reco'])for(const part of ['board','result'])h.slot(mode,part);
  c.$=id=>h.doc.getElementById(id);c.DIRECT={mode:'reco'};
  h.load(template.match(/const DIRECT_GWEN=GwenStage.mount.*\n/)[0]+template.match(/const RECO_GWEN=GwenStage.mount.*\n/)[0]);
  c.contents=[{key:'op'}];h.add('content').value=0;
  h.load(section(template,'function guildGwenMode()','function simProgress('));
  c.GwenStage.activate('reco');h.g=c.GwenLane;h.actor=()=>h.doc.querySelector('[data-gwen=lane]');
  h.bind=mode=>c.GwenStage.mount(h.doc,{mode});return h;
}
async function remount(code=lane){
  const h=setup(code),g=h.g;
  h.c.recoGwenShow(false,null,{clear:.8});await h.flush();
  const actor=h.actor(),old=h.c.$('reco-result-lane'),report=actor.dataset.announcements,speech=actor.querySelector('.gwen-lane-speech').textContent;
  const state={...g.mount().policy.state},phrase=h.c.$('reco-lane-banner').dataset.phrase;
  const create=h.doc.createElement;h.doc.createElement=tag=>{const el=create(tag);el.clientWidth=140;return el;};
  old.remove();h.slot('reco','result');h.bind('reco');const replacement=h.c.$('reco-result-lane');h.doc.createElement=create;
  const banner=h.c.$('reco-lane-banner');h.bind('reco');await h.flush();
  assert.equal(actor.parentElement,replacement,'same phase must attach actor to the replacement lane');
  assert.equal(actor.dataset.announcements,report,'host replacement replayed report');
  assert.equal(actor.querySelector('.gwen-lane-speech').textContent,speech);
  assert.equal(g.mount().policy.state.lastSpeech,state.lastSpeech);
  assert.equal(banner.hidden,false);assert.equal(banner.dataset.state,'result');assert.equal(banner.dataset.phrase,phrase);
  assert(g.mount().state.x>=0&&g.mount().state.x<=60,'position exceeds replacement lane');
  // Pending old decode must not commit, even if it completes before the new request.
  h.c.recoGwenShow(true,.9);await h.tick(300);assert(g.mount().state.moving);
  h.holdDecode(true);const board=h.c.$('reco-board-lane');board.remove();
  h.slot('reco','board');h.bind('reco');const board2=h.c.$('reco-board-lane');board2.clientWidth=100;
  assert(!g.mount().state.moving,'host replacement must cancel movement');
  const pendingOld=h.decodes.at(-1);board2.remove();h.slot('reco','board');h.bind('reco');const board3=h.c.$('reco-board-lane');board3.clientWidth=90;
  pendingOld.resolve();await h.flush();
  assert.notEqual(actor.querySelector('button').firstElementChild,pendingOld.el,'old decode committed after replacement');
  h.decodes.at(-1).resolve();await h.flush();assert.equal(actor.parentElement,board3);
}
function directPaintSync(h,src=direct){
  // Execute the real producer's sync expression, with directResultsPaint's local values.
  Object.assign(h.c,{phase:'idle',bundling:false,validNow:false,bundle:null,finalReport:false,compatible:false,now:null,metric:'clear',
    running:null,RECO:{},past:()=>false});h.c.DIRECT.draft={slots:[]};
  h.load(src.match(/  \w+_GWEN\.update\([\s\S]*?\);\n/)[0]);
}
async function ownership(code=lane,src=direct){
  const h=setup(code);h.c.recoGwenShow(true,.8);await h.tick(300);
  assert(h.g.mount().state.moving,'test did not reach work movement');
  directPaintSync(h,src);
  assert.equal(h.g.mount().state.phase,'work','direct repaint overwrote reco work');
  assert(h.g.mount().state.moving,'direct repaint stopped reco walking');
  h.c.DIRECT.mode='direct';h.g.activate('direct');
  assert.equal(h.g.mount().state.phase,'idle');assert.equal(h.actor().parentElement,h.c.$('direct-board-lane'));
  h.c.recoGwenShow(false,null,{clear:.9});
  assert.equal(h.g.mount().state.phase,'idle','background reco stole the direct stage');
  h.c.DIRECT.mode='reco';h.g.activate('reco');h.c.recoGwenVisibility();await h.flush();
  assert.equal(h.g.mount().state.phase,'result');assert.equal(h.actor().parentElement,h.c.$('reco-result-lane'));
  h.g.activate('direct');assert.equal(h.g.mount().state.phase,'idle');
  h.g.activate('reco');assert.equal(h.actor().dataset.announcements,'1');
}
async function lateResponse(template=html,executor=read('search_executor.js')){
  const h=setup(lane,template),c=h.c;
  c.SIMQ={};c.navigator={hardwareConcurrency:2,deviceMemory:8};const workers=[];
  c.Worker=class{constructor(){workers.push(this)}postMessage(m){this.req=m}terminate(){this.dead=true}};
  h.load(executor);
  h.load(section(template,'const SCR_WMAX=','// 이 기기의 시뮬 속도'));
  const start=(owner,id)=>{const ws=c.scrPool(1);c.simDispatch(ws,['team'],{owner,id,revision:0,live:()=>true,
    msg:()=>({type:'run',teams:[{key:'team'}]}),stage:(w,m)=>c.GwenLane.sync({mode:owner,phase:'work',progress:m.completed,count:4}),
    team:(j,m)=>c.GwenLane.sync({mode:owner,phase:'result',result:id,clear:m.result.clear,count:4}),done(){},error(){}});return ws;};
  start('direct',1);const worker=workers[0],old={...worker.req};
  // Returning a worker without terminating it lets a cancelled request arrive on a new lease.
  c.simRelease(worker);start('reco',2);c.simPoolDrop('direct',1);
  assert.equal(workers.length,1,'test must exercise a reused worker');
  h.c.recoGwenShow(true,.4);await h.tick(300);
  const before=h.g.mount().state;
  const send=(req,type,extra={})=>worker.onmessage({data:{...req,type,key:'team',result:{clear:0,n:100,progs:[0],via:{}},...extra}});
  send(old,'stage',{completed:.99});send(old,'team');send(old,'done');
  assert.equal(h.g.mount().state.phase,before.phase,'cancelled result changed the active stage');
  assert.equal(h.actor().parentElement,c.$('reco-board-lane'));assert.equal(h.actor().dataset.announcements,undefined);
  send(worker.req,'team');assert.equal(h.g.mount().state.phase,'result','current response must reach the DOM');
}
async function persistent(template=html,code=lane){
  const h=setup(code,template),result={score:100};h.c.recoGwenShow(false,null,result);await h.flush();
  const actor=h.actor();assert.equal(actor.parentElement,h.c.$('reco-result-lane'));
  assert.equal(h.host.hidden,false);assert.equal(h.c.$('reco-lane-banner').hidden,false);
  assert(['st_point','thoughtful'].includes(actor.dataset.gwenExpression),'score-only result must be neutral');
  await h.tick(1900);h.c.recoGwenShow(false,null,result);await h.tick(61000);
  assert.equal(actor.parentElement,h.c.$('reco-result-lane'),'result must remain beyond report and idle timers');
  assert(actor.isConnected&&!h.host.hidden&&!actor.hidden);assert.equal(actor.dataset.announcements,'1');
  assert(['st_point','thoughtful'].includes(actor.dataset.gwenExpression));
}
async function inlineReport(code=ux){
  const h=harness();h.load(policy);h.load(code);const result={clear:.8},host=h.add('report');
  host.innerHTML=h.c.Ux.gwenReport(result,{clear:.8});h.c.Ux.mount();await h.flush();
  assert(host.querySelector('img').dataset.gwenLoaded==='true','decode path not reached');
  await h.tick(1900);
  assert(host.querySelector('[data-gwen-report]')?.isConnected,'report image removed after 1.8 seconds');
  const output=h.c.Ux.gwenReport(result,{clear:0});assert(output.includes('data-gwen-report'),'completed report disappeared on rerender');
  assert.equal(host.querySelector('img').dataset.gwenPlaying,'false');
  host.innerHTML=output;h.refresh();await h.flush();
  assert.equal(host.querySelector('img').dataset.gwenPlaying,'false','completed report reaction replayed');
}
// 감시 범위: 진행 글자(텍스트 노드)·그웬과 무관한 요소의 속성 변화로는 새 그웬을 등록하지 않고, 그웬 그림이 들어오면 등록함.
async function refreshFilter(code=ux){
  const h=harness();h.load(policy);h.load(code);const host=h.add('work'),other=h.add('other');h.c.Ux.mount();await h.flush();
  host.innerHTML=h.c.Ux.gwenWork('long');const img=host.querySelector('img');
  h.refresh([{type:'childList',target:other,addedNodes:[{nodeType:3}],removedNodes:[{nodeType:3}]}]);await h.flush();
  h.refresh([{type:'attributes',attributeName:'style',target:other}]);await h.flush();
  assert.equal(img.dataset.gwenLoaded,undefined,'progress text or unrelated style refreshed Gwen');
  h.refresh([{type:'childList',target:host,addedNodes:[host.firstElementChild],removedNodes:[]}]);await h.flush();
  assert.equal(img.dataset.gwenLoaded,'true','added Gwen image not registered');
}
async function reactionOnce(code=ux){
  const h=setup(lane);h.load(code);h.c.recoGwenShow(false,null,{clear:.8});await h.flush();h.c.Ux.mount();await h.flush();
  assert.equal(h.actor().querySelector('img').dataset.gwenPlaying,'true','initial result action was not reached');
  await h.tick(1900);
  h.g.activate('direct');await h.flush();h.refresh();await h.flush();
  h.g.activate('reco');await h.flush();h.refresh();await h.flush();
  assert.equal(h.actor().querySelector('img').dataset.gwenPlaying,'false','return to a result replayed its action');
  assert.equal(h.actor().dataset.announcements,'1');
}
async function bundlePhases(source=read('direct_bundle.js')){
  const h=setup(),c=h.c;h.add('out');c.scrAlertSync=()=>'';c.scrAlertLane=al=>al;   // 관측 경보(훑기)·빠른 관측은 fullscreen_test.js 가 봄
  h.load(section(source,'function recoProgressPaint(','async function directAwait('));
  const task={owner:'reco-bundle',request:1,progress:.7,message:'예선'};
  c.recoProgressPaint(task);
  const animate=h.actor().animate;
  h.actor().animate=function(frames,opts){const a=animate.call(this,frames,opts);a.playState='finished';a.currentTime=opts.duration;return a;};
  await h.tick(3000);assert(h.g.mount().state.x>0,'bundle test never walked');
  const before=h.g.mount().state.x;
  task.request++;task.progress=0;c.recoProgressPaint(task);
  assert.equal(h.g.mount().state.x,before,'next bundle request teleported instead of turning');
  assert.equal(h.g.mount().state.dir,-1,'next bundle request did not reverse direction');
  task.progress=.7;c.recoProgressPaint(task);await h.tick(3000);assert(h.g.mount().state.x<before,'reversed phase did not walk back');
  const back=h.g.mount().state.x;c.recoProgressPaint({...task,progress:0});
  assert.equal(h.g.mount().state.x,back,'different bundle task teleported');
  assert.equal(h.g.mount().state.dir,1,'different bundle task did not reverse direction');
}
// 단계 전환은 순간이동 없이 왕복: 방향 반전·그림 반전·위치 연속·새 계산은 왼쪽에서 시작.
async function pingpong(code=lane){
  const h=setup(code),c=h.c,g=()=>h.g.mount().state;
  c.recoGwenShow(true,0,null,'a');await h.flush();const actor=h.actor();
  const animate=actor.animate;
  actor.animate=function(frames,opts){const a=animate.call(this,frames,opts);a.playState='finished';a.currentTime=opts.duration;return a;};
  const face=()=>actor.querySelector('button').style.transform;
  // 50ms 마다 위치를 재서 한 번에 한 걸음(최대 36px)보다 크게 뛰면 순간이동으로 봄.
  const walk=async(ms=3000)=>{let last=g().x;for(let t=0;t<ms;t+=50){await h.tick(50);const now=g().x;assert(Math.abs(now-last)<=36.5,`position jumped ${last}->${now}`);last=now;}};
  const show=async(p,step)=>{const was=g().x;c.recoGwenShow(true,p,null,step);assert.equal(g().x,was,`step ${step} teleported`);await walk();};
  assert.equal(g().x,0,'new run must start at the left');assert.equal(g().dir,1);
  await show(.5,'a');assert(Math.abs(g().x-260)<1,'forward phase position '+g().x);
  await show(1,'a');assert(Math.abs(g().x-520)<1);assert.notEqual(face(),'scaleX(-1)');
  await show(0,'b');assert.equal(g().dir,-1,'phase change did not reverse');assert(Math.abs(g().x-520)<1,'reverse phase must start at the end');
  assert.equal(face(),'scaleX(-1)','reverse phase must mirror Gwen');assert.equal(actor.dataset.direction,'back');
  assert.notEqual(actor.querySelector('.gwen-lane-speech').style.transform,'scaleX(-1)','speech bubble mirrored');
  await show(.5,'b');assert(Math.abs(g().x-260)<1,'reverse phase position '+g().x);
  // 진행도 1 전에 끝난 단계: 새 시작점(왼쪽)까지 걸어간 뒤 →로 진행.
  await show(0,'c');assert.equal(g().dir,1);assert(g().x<1,'unfinished phase did not walk to the new start '+g().x);
  assert.notEqual(face(),'scaleX(-1)');
  await show(.5,'c');assert(Math.abs(g().x-260)<1);
  await show(0,'d');assert.equal(g().dir,-1);assert(Math.abs(g().x-520)<1,'did not walk to the right start');assert.equal(face(),'scaleX(-1)');
  c.recoGwenShow(false,null,{clear:.8});await h.flush();
  assert.equal(face(),'none','result must restore the original direction');assert.equal(actor.dataset.direction,'forward');
  c.recoGwenShow(true,0,null,'e');await h.flush();
  assert.equal(g().x,0,'new run after result must start at the left');assert.equal(g().dir,1);
}
async function mutation(name,source,from,to,check){assert(source.includes(from),name+' target');
  await check(source);
  await assert.rejects(()=>check(source.replace(from,to)),{code:'ERR_ASSERTION'},name);console.log('MUTATION caught + restored (isolated VM):',name);}
(async()=>{
  await remount();await ownership();await lateResponse();await persistent();await inlineReport();await refreshFilter();await reactionOnce();await bundlePhases();await pingpong();
  await mutation('bundle request phase',read('direct_bundle.js'),"GwenLane.resultId(task)+':'+task.request","GwenLane.resultId(task)",bundlePhases);
  await mutation('bundle task identity',read('direct_bundle.js'),"GwenLane.resultId(task)+':'+task.request","task.request",bundlePhases);
  await mutation('same-phase host reattachment',lane,'function rebind(mode){','function rebind(mode){return;',remount);
  await mutation('stale image decode',lane,'if(request!==imageRequest)return;','',remount);
  await mutation('movement cancellation',lane,"actor?.removeAttribute('data-moving');",'',async code=>{
    // This mutation deliberately leaves the DOM moving marker behind.
    const h=setup(code);h.c.recoGwenShow(true,.9);await h.tick(300);const actor=h.actor();
    h.c.$('reco-board-lane').remove();h.slot('reco','board');h.bind('reco');
    assert.equal(actor.dataset.moving,undefined,'moving marker survived reattachment');
  });
  await mutation('direct writer ownership',direct,"DIRECT_GWEN.update({mode:'direct'",'RECO_GWEN.update({mode:DIRECT.mode' ,src=>ownership(lane,src));
  await mutation('inactive stage isolation',lane,'if(next.mode===activeMode)render(next);','render(next);',ownership);
  await mutation('late request validation',read('search_executor.js'),
    'if(!boot&&(m.id!==o.id||(m.requestId!=null&&m.requestId!==o.id)))return;',
    'm.owner=b.owner;m.revision=o.revision||0;m.jobId=lease.token;',src=>lateResponse(html,src));
  await mutation('internal result host hidden',html,"host.hidden=DIRECT.mode!=='reco'", "host.hidden=host.dataset.phase==='result'||DIRECT.mode!=='reco'",persistent);
  await mutation('result lane registration',html,"host.dataset.phase=phase;GwenStage.mount(document,{mode:'reco'});",'host.dataset.phase=phase;',async template=>{const h=setup(lane,template);h.c.$('reco-result-lane').remove();h.slot('reco','result');h.c.recoGwenShow(false,null,{clear:.8});await h.flush();assert(h.actor()?.isConnected);});
  await mutation('score policy bypass',lane,'candidates=Array.isArray(current.arts)&&current.arts.length?current.arts:P.resultCandidates(current.clear,current.better,current.recoHigher)','candidates=CHOICES.low',code=>persistent(html,code));
  await mutation('result idle expiration',lane,"if(!['work','error','result'].includes(current.phase))","if(!['work','error'].includes(current.phase))",code=>persistent(html,code));
  await mutation('inline result removal',ux,'report.done=true;invalidate();','report.done=true;scene.remove();invalidate();',inlineReport);
  await mutation('completed report rerender removal',ux,'gwenPending.set(state.id,new WeakRef(state));',"if(state.done)return '';gwenPending.set(state.id,new WeakRef(state));",inlineReport);
  await mutation('result action replay',ux,'||img.dataset.gwenOnce&&playedReports.has(img.dataset.gwenOnce)','',reactionOnce);
  await mutation('phase teleport to start',lane,"actor.style.transform=`translateX(${x}px)`;positionSpeech();workRestAt=clock+250;}","x=0;actor.style.transform=`translateX(${x}px)`;positionSpeech();workRestAt=clock+250;}",pingpong);
  await mutation('direction reversal',lane,'run.dir=-run.dir;','',pingpong);
  await mutation('mirror on reverse',lane,"run?.dir<0?'scaleX(-1)':'none';}","'none';}",pingpong);
  await mutation('walk to new start',lane,'run.seek=true;','run.seek=false;',pingpong);
  await mutation('result restores direction',lane,"current.phase==='result'||",'',pingpong);
  await mutation('refresh on any change',ux,'function relevant(records){','function relevant(records){return true;',refreshFilter);
  await mutation('ignore added Gwen',ux,'for(const n of list)if(gwenNode(n))return true;','for(const n of list)if(false)return true;',refreshFilter);
  console.log('PASS 9 DOM scenarios / 22 mutations');
})().catch(e=>{console.error(e);process.exitCode=1});
