const assert=require('node:assert/strict'),fs=require('node:fs');
const harness=require('./helpers/gwen_dom');
const read=p=>fs.readFileSync(require.resolve('../'+p),'utf8').replace(/\r\n/g,'\n');
const lane=read('gwen_lane.js'),policy=read('gwen_policy.js'),ux=read('ux_ui.js'),html=read('party_template.html'),direct=read('direct_run.js');
const section=(s,a,b)=>s.slice(s.indexOf(a),s.indexOf(b,s.indexOf(a)));
// Retain the physical result-stage contracts (used by direct mode).
// Automatic summary placement and resultExternal are checked by test_gwen_auto.py.
function setup(code=lane,template=html.replace('resultExternal:true,','')){
  template=template.replace("$('reco-result-lane').hidden=true","$('reco-result-lane').hidden=phase!=='result'");
  const h=harness();h.load(policy);h.load(ux);h.load(code);
  const {c}=h;h.host=h.add('reco-gwen-stage');h.add('mi-panel').hidden=true;
  for(const mode of ['direct','reco']){
    const parent=mode==='reco'?h.host:h.doc.body;
    h.add(mode+'-board-lane',parent);h.add(mode+'-result-lane',parent);
    const banner=h.add(mode+'-lane-banner',h.doc.getElementById(mode+'-board-lane'));
    banner.innerHTML=c.GwenPolicy.bannerMarkup();
  }
  c.$=id=>h.doc.getElementById(id);c.DIRECT={mode:'reco'};
  // Exercise production registration and result writer, including their DOM wiring.
  h.load(template.match(/GwenLane.registerStage\('direct'.*\n/)[0]+template.match(/GwenLane.registerStage\('reco'.*\n/)[0]);
  h.load(section(template,'function recoGwenVisibility()','function simProgress('));
  c.GwenLane.activate('reco');h.g=c.GwenLane;h.actor=()=>h.doc.querySelector('[data-gwen=lane]');
  return h;
}
async function remount(code=lane){
  const h=setup(code),g=h.g;
  h.c.recoGwenShow(false,null,{clear:.8});await h.flush();
  const actor=h.actor(),old=h.c.$('reco-result-lane'),report=actor.dataset.announcements,speech=actor.querySelector('.gwen-lane-speech').textContent;
  const state={...g.mount().policy.state},phrase=h.c.$('reco-lane-banner').dataset.phrase;
  old.remove();const replacement=h.add('reco-result-lane',h.host);replacement.clientWidth=140;
  const banner=h.add('new-banner',h.c.$('reco-board-lane'));banner.innerHTML=h.c.GwenPolicy.bannerMarkup();
  g.registerStage('reco',{board:h.c.$('reco-board-lane'),result:replacement,banner});await h.flush();
  assert.equal(actor.parentElement,replacement,'same phase must attach actor to the replacement lane');
  assert.equal(actor.dataset.announcements,report,'host replacement replayed report');
  assert.equal(actor.querySelector('.gwen-lane-speech').textContent,speech);
  assert.equal(g.mount().policy.state.lastSpeech,state.lastSpeech);
  assert.equal(banner.hidden,false);assert.equal(banner.dataset.state,'result');assert.equal(banner.dataset.phrase,phrase);
  assert(g.mount().state.x>=0&&g.mount().state.x<=60,'position exceeds replacement lane');
  // Pending old decode must not commit, even if it completes before the new request.
  h.c.recoGwenShow(true,.9);await h.tick(300);assert(g.mount().state.moving);
  h.holdDecode(true);const board=h.c.$('reco-board-lane');board.remove();
  const board2=h.add('reco-board-lane',h.host);board2.clientWidth=100;
  g.registerStage('reco',{board:board2,result:replacement,banner});
  assert(!g.mount().state.moving,'host replacement must cancel movement');
  const pendingOld=h.decodes.at(-1);board2.remove();const board3=h.add('reco-board-lane',h.host);board3.clientWidth=90;
  g.registerStage('reco',{board:board3,result:replacement,banner});
  pendingOld.resolve();await h.flush();
  assert.notEqual(actor.querySelector('button').firstElementChild,pendingOld.el,'old decode committed after replacement');
  h.decodes.at(-1).resolve();await h.flush();assert.equal(actor.parentElement,board3);
}
function directPaintSync(h,src=direct){
  // Execute the real producer's sync expression, with directResultsPaint's local values.
  Object.assign(h.c,{phase:'idle',bundling:false,validNow:false,bundle:null,finalReport:false,compatible:false,now:null,metric:'clear',
    running:null,RECO:{},past:()=>false});h.c.DIRECT.draft={slots:[]};
  h.load(section(src,'  GwenLane.sync(', '\n\n  const detail='));
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
async function lateResponse(template=html){
  const h=setup(lane,template),c=h.c;
  c.SIMQ={};c.navigator={hardwareConcurrency:2,deviceMemory:8};const workers=[];
  c.Worker=class{constructor(){workers.push(this)}postMessage(m){this.req=m}terminate(){this.dead=true}};
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
async function persistent(template=html.replace('resultExternal:true,',''),code=lane){
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
async function reactionOnce(code=ux){
  const h=setup(lane);h.load(code);h.c.recoGwenShow(false,null,{clear:.8});await h.flush();h.c.Ux.mount();await h.flush();
  assert.equal(h.actor().querySelector('img').dataset.gwenPlaying,'true','initial result action was not reached');
  await h.tick(1900);
  h.g.activate('direct');await h.flush();h.refresh();await h.flush();
  h.g.activate('reco');await h.flush();h.refresh();await h.flush();
  assert.equal(h.actor().querySelector('img').dataset.gwenPlaying,'false','return to a result replayed its action');
  assert.equal(h.actor().dataset.announcements,'1');
}
async function mutation(name,source,from,to,check){assert(source.includes(from),name+' target');
  await check(source);
  await assert.rejects(()=>check(source.replace(from,to)),{code:'ERR_ASSERTION'},name);console.log('MUTATION caught + restored (isolated VM):',name);}
(async()=>{
  await remount();await ownership();await lateResponse();await persistent();await inlineReport();await reactionOnce();
  await mutation('same-phase host reattachment',lane,'controller?.rebind(key);','',remount);
  await mutation('stale image decode',lane,'if(request!==imageRequest)return;','',remount);
  await mutation('movement cancellation',lane,"actor?.removeAttribute('data-moving');",'',async code=>{
    // This mutation deliberately leaves the DOM moving marker behind.
    const h=setup(code);h.c.recoGwenShow(true,.9);await h.tick(300);const actor=h.actor();
    const replacement=h.add('new-board');h.g.registerStage('reco',{board:replacement});
    assert.equal(actor.dataset.moving,undefined,'moving marker survived reattachment');
  });
  await mutation('direct writer ownership',direct,"GwenLane.sync({mode:'direct'",'GwenLane.sync({mode:DIRECT.mode',src=>ownership(lane,src));
  await mutation('inactive stage isolation',lane,'if(next.mode===activeMode)render(next);','render(next);',ownership);
  await mutation('late request validation',html,
    'if(!boot&&(m.id!==o.id||(m.requestId!=null&&m.requestId!==o.id)))return;',
    'm.owner=b.owner;m.revision=o.revision||0;m.jobId=lease.token;',lateResponse);
  await mutation('internal result host hidden',html.replace('resultExternal:true,',''),"host.hidden=DIRECT.mode!=='reco'", "host.hidden=host.dataset.phase==='result'||DIRECT.mode!=='reco'",persistent);
  await mutation('result lane registration',html.replace('resultExternal:true,',''),"result:document.getElementById('reco-result-lane'),",'',persistent);
  await mutation('score policy bypass',lane,'candidates=P.resultCandidates(current.clear,current.better,current.recoHigher)','candidates=CHOICES.low',code=>persistent(html.replace('resultExternal:true,',''),code));
  await mutation('result idle expiration',lane,"if(!['work','error','result'].includes(current.phase)&&!quiet)","if(!['work','error'].includes(current.phase)&&!quiet)",code=>persistent(html.replace('resultExternal:true,',''),code));
  await mutation('inline result removal',ux,'report.done=true;invalidate();','report.done=true;scene.remove();invalidate();',inlineReport);
  await mutation('completed report rerender removal',ux,'gwenPending.set(state.id,new WeakRef(state));',"if(state.done)return '';gwenPending.set(state.id,new WeakRef(state));",inlineReport);
  await mutation('result action replay',ux,'||img.dataset.gwenOnce&&playedReports.has(img.dataset.gwenOnce)','',reactionOnce);
  console.log('PASS 6 DOM scenarios / 13 mutations');
})().catch(e=>{console.error(e);process.exitCode=1});
