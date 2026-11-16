// Presentation only. One movable actor, reserved lanes, and a visible-time clock.
(function(root){
  'use strict';
  const PRIORITY={idle:0,edit:1,work:2,result:3,error:4};
  const CHOICES={home:['guide2','st_welcome','welcome'],empty:['ready','present'],
    ready:['ready'],vacant:['think','sulk','peek'],put:['present','shy'],remove:['surprised','sulk'],
    swap:['think'],leader:['verdict'],complete:['jump'],grown:['train'],
    withReco:['files','board'],withGrowth:['train'],reco:['stakeout','magnify','files'],growth:['train','walk'],skip:['surprised'],recoHigher:['st_point','thoughtful'],brk:['charge'],start:['zap'],work:['magnify','stamp','stakeout','walk','files'],
    high:['st_verdict','st_cheer','st_ok'],medium:['st_point','thoughtful'],low:['st_cry','notes'],
    highSD:['verdict','cheer','report'],mediumSD:['report','verdict'],lowSD:['cry'],
    better:['st_wink'],past:['think'],error:['cry','surprised','sulk'],wait:['wait'],doze:['doze'],wake:['wake']};
  const SAY={home:['단장님, 어떤 방법으로 골라 볼까?','후후후, 두 방법 다 나만 믿어!','천재 조사관은 준비 끝이야!'],
    empty:['단장님, 구원자부터 골라 봐!','후후후, 어떤 조합이 될까?'],vacant:['빈 칸이 남았네, 단장님.','천천히 골라도 돼. 내가 기다릴게!'],
    put:['좋아, 이쪽으로 모실게!','후후후, 한 명 더 모였어!','단장님, 자리 확인해 봐!'],remove:['잠깐! 다른 조합도 볼까?','단장님, 다음 구원자는 누구야?'],
    swap:['이쪽 자리로 바꿔 볼까?','후후후, 배치도 중요하지!'],leader:['단장님, 이번 리더는 정했네!','앞장설 구원자, 확인했어!'],
    complete:['네 명 다 모였어, 단장님!','후후후, 준비됐으면 나만 믿어!'],grown:['이만큼 키웠다고 치고 볼게!','단장님, 달라진 능력치도 확인해 봐!','스타링크까지 더해서 볼게!'],
    withReco:['후후후, 내 추천이랑 겨뤄 보자는 거지?','좋아, 내 추천도 같이 꺼내 올게!'],withGrowth:['키웠을 때 편성도 찾아볼게!'],reco:['이번엔 내 추천 차례야, 단장님!','후보를 하나씩 살펴볼게.'],growth:['키우면 누가 좋을지 보고 있어!'],skip:['알았어, 그건 넘어갈게!'],recoHigher:['내 추천 쪽이 조금 더 높네. 비교해 봐, 단장님!'],
    brk:['브레이크 준비, 확인했어!','단장님, 이 스킬로 볼게!'],
    start:['천재 조사관에게 맡겨!','후후후, 지금부터 확인할게!'],work:['하나씩 꼼꼼히 살펴볼게.','단장님, 조금만 기다려!','끝까지 확인할 테니 나만 믿어!'],
    high:['후후후, 든든한 편성이네!','잘 골랐어, 단장님!','천재 조사관의 확인도 끝!'],medium:['아슬아슬하네. 숫자도 살펴봐!','단장님, 한 번 더 비교해 볼까?'],
    low:['으아앙, 쉽지 않겠는걸!','단장님, 육성도 같이 살펴보자.'],better:['후후후, 추천보다 높게 나왔어!','단장님, 멋진 선택이야!'],past:['편성이 바뀌었네. 지난 결과야!','지금 편성으로 다시 확인해 봐!'],
    error:['으아앙, 잠깐! 다시 확인해 줘!','단장님, 안내문부터 살펴봐!'],wait:['편성을 짜고 실행하면 내가 봐줄게!','단장님, 준비되면 불러!'],
    doze:['눈만 잠깐… 감을게…','단장님… 나 여기 있어…'],wake:['잠깐! 안 잤어, 단장님!','으앗! 준비됐어?'],
    shy:['왜, 왜 불러, 단장님?','그렇게 보면 쑥스럽잖아!'],sulk:['자꾸 누르면 삐질 거야!','흥, 나도 생각할 시간이 필요해!'],cry:['으아앙, 잠깐만!','단장님, 조금만 쉬게 해 줘!']};
  function policy(random=Math.random){
    const s={history:[],priority:0,until:0,lastReaction:-Infinity,lastSpeech:-Infinity,lastClick:-Infinity,clicks:0,locked:0,reports:new Map()};
    const pick=candidates=>{let pool=candidates.filter(x=>!s.history.slice(-2).includes(x));
      if(!pool.length)pool=candidates.filter(x=>x!==s.history.at(-1));if(!pool.length)pool=candidates;
      const art=pool[Math.floor(random()*pool.length)];s.history.push(art);s.history=s.history.slice(-2);return art;};
    function event(kind,now,{level='edit',candidates=CHOICES[kind],duration=1500,quiet=false,id=null}={}){
      const priority=PRIORITY[level];
      if(priority<s.priority&&now<s.until)return null;
      if(quiet&&!['work','result','error'].includes(level))return null;
      if(level==='result'&&id!=null&&s.reports.has(id))return null;
      const cooled=level==='edit'&&now-s.lastReaction<4000;
      const speech=!cooled&&now-s.lastSpeech>=6000;
      if(level==='edit')s.lastReaction=now;if(speech)s.lastSpeech=now;
      const art=pick(candidates||[kind]);s.priority=priority;s.until=now+duration;
      if(level==='result'&&id!=null){s.reports.set(id,art);if(s.reports.size>128)s.reports.delete(s.reports.keys().next().value);}
      return {kind,art,speech,priority};
    }
    function poke(now,portrait=false,quiet=false){
      if(now<s.locked||quiet||s.priority>=PRIORITY.work&&now<s.until)return null;
      if(now-s.lastClick>=10000)s.clicks=0;s.lastClick=now;
      const kind=['shy','sulk','cry'][s.clicks++];
      if(s.clicks===3){s.locked=now+10000;s.clicks=0;}
      return event(kind,now,{candidates:[(portrait?'st_':'')+kind],duration:1500});
    }
    return {state:s,pick,event,poke};
  }
  function travel(from,target,width,size,{run=false,mobile=false,reduced=false,quiet=false,home=false}={}){
    const max=Math.max(0,width-size),end=Math.max(0,Math.min(max,target));
    if(reduced||quiet||home&&mobile)return {x:Math.min(max,Math.max(0,from)),ms:0};
    const speed=(run?240:60)*(mobile?.5:1),distance=Math.min(Math.abs(end-from),speed*.6);
    return {x:Math.max(0,Math.min(max,from+Math.sign(end-from)*distance)),ms:distance/speed*1000};
  }
  let controller,serial=0;const resultIds=new WeakMap();
  function resultId(result){if(!resultIds.has(result))resultIds.set(result,++serial);return resultIds.get(result);}
  function mount(){
    if(controller||!root.document)return controller;
    const doc=root.document,mq=root.matchMedia('(prefers-reduced-motion: reduce)'),p=policy(),resultArts=new Map();
    let actor=null,lane=null,current={},clock=0,last=performance.now(),idleAt=0,vacant=false,phaseKey='',cycleAt=0,
      restoreAt=0,bubbleUntil=0,speechShownAt=-Infinity,move=null,landing=0,pending=null,x=0,quiet=false,art='',lastEvent='',sleeping=false,exit=null,startAt=0,startAction=null;
    try{quiet=JSON.parse(localStorage.getItem('pn.gwen.quiet')||'false')===true;}catch{}
    doc.documentElement.dataset.gwenQuiet=String(quiet);
    function ensure(){if(actor)return;actor=doc.createElement('div');actor.className='gwen-lane-actor';actor.dataset.gwen='lane';
      actor.innerHTML='<span class="gwen-lane-speech" aria-hidden="true"></span><button type="button" class="gwen-lane-poke" aria-label="그웬 부르기"></button><span class="gwen-announcement" role="status" aria-live="polite"></span>';
      actor.querySelector('button').addEventListener('click',()=>{
        const e=p.poke(clock,lane?.dataset.portrait==='true',quiet);if(e){cancelMove();display(e);restoreAt=clock+1500;}
      });
    }
    function visible(){if(!actor||!lane||doc.hidden||!actor.isConnected)return false;
      const r=lane.getBoundingClientRect();return lane.getClientRects().length>0&&r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth&&!lane.closest('[hidden]');}
    function cancelMove(){if(move){const pos=move.animation.currentTime||0;const ratio=Math.min(1,pos/Math.max(1,move.ms));x=move.from+(move.to-move.from)*ratio;move.animation.cancel();move=null;}
      if(actor)actor.style.transform=`translateX(${x}px)`;landing=0;pending=null;actor?.removeAttribute('data-moving');}
    function setLane(id){ensure();const target=doc.getElementById(id);if(!target)return false;
      if(lane!==target||actor.parentElement!==target){cancelMove();lane=target;lane.append(actor);x=id==='direct-progress-lane'?0:Math.max(0,(lane.clientWidth-actor.offsetWidth)/2);actor.style.transform=`translateX(${x}px)`;}
      return true;}
    function image(key){if(key===art)return;art=key;actor.querySelector('button').innerHTML=root.Ux.gwenImage(key,'gwen-lane-image',80).replace('data-gwen-art=', 'data-gwen-managed="true" data-gwen-art=');
      actor.dataset.gwenExpression=key;actor.dataset.event=lastEvent;}
    function display(e){if(!e)return;lastEvent=e.kind;image(e.art);actor.dataset.event=e.kind;actor.dataset.priority=String(e.priority);
      const bubble=actor.querySelector('.gwen-lane-speech');
      if(e.speech&&clock-speechShownAt>=6000){const lines=SAY[e.kind]||SAY.work;bubble.textContent=lines[Math.floor(Math.random()*lines.length)];bubbleUntil=clock+2500;speechShownAt=clock;p.state.lastSpeech=clock;}
      else bubbleUntil=0;
      bubble.hidden=clock>=bubbleUntil;}
    function moveTo(target,{run=false,reaction=null,leave=false,adjust=true}={}){
      cancelMove();const mobile=innerWidth<=400,size=actor.offsetWidth,max=Math.max(0,lane.clientWidth-size);
      target=Math.max(0,Math.min(max,target));
      if(mobile&&!leave&&adjust)target=x+(target-x)*.5;
      const step=travel(x,target,lane.clientWidth,size,{run,mobile,reduced:mq.matches,quiet,home:lane.id==='home-gwen-lane'});
      if(!step.ms){if(reaction)display(mq.matches&&reaction.art==='jump'?{...reaction,art:'ready'}:reaction);if(leave)exit=clock;return;}
      actor.querySelector('.gwen-lane-speech').hidden=true;image(run?'run':'walk');actor.dataset.moving='true';
      actor.querySelector('button').style.transform=target<x?'scaleX(-1)':'none';
      pending=reaction;const from=x;
      const animation=actor.animate([{transform:`translateX(${from}px)`},{transform:`translateX(${step.x}px)`}],{duration:step.ms,easing:'linear',fill:'forwards'});
      move={animation,from,to:step.x,ms:step.ms,target,run,leave};
    }
    function request(kind,opts={}){const e=p.event(kind,clock,{quiet,...opts});if(!e)return false;
      if(opts.target!=null)moveTo(opts.target,{run:opts.run,reaction:e});else{cancelMove();display(e);}
      if(opts.level==='edit'||!opts.level)restoreAt=clock+1500+(move?move.ms+150:0);return true;}
    function base(){if(current.mode==='home')return ['home','home-gwen-lane'];
      if(current.phase==='work')return [current.step==='reco'?'reco':current.step==='growth'?'growth':'work','direct-progress-lane'];
      if(current.phase==='error')return ['error','direct-result-lane'];
      if(current.phase==='result')return [current.recoHigher?'recoHigher':current.better?'better':current.clear>=.7?'high':current.clear>=.05?'medium':'low','direct-result-lane'];
      if(current.stale)return ['past','direct-board-lane'];
      if(current.count>0&&current.count<4)return ['wait','direct-result-lane'];
      return [current.count===0?'empty':'ready','direct-board-lane'];}
    function settle(){const [kind,id]=base();if(!setLane(id))return;
      const portrait=id==='direct-result-lane'&&innerWidth>=1200;lane.dataset.portrait=String(portrait);
      let candidates=CHOICES[kind];if(['high','medium','low'].includes(kind)&&!portrait)candidates=CHOICES[kind+'SD'];
      if(kind==='recoHigher'&&!portrait)candidates=['report','think'];
      if(kind==='better'&&!portrait)candidates=['verdict','cheer','report'];
      if(kind==='home')candidates=innerWidth>=1200?CHOICES.home:['guide2','welcome','present'];
      const level=current.phase==='error'?'error':current.phase==='result'?'result':current.phase==='work'?'work':'idle';
      p.state.until=clock;const idKey=level==='result'?current.result:null;
      const e=p.event(kind,clock,{level,candidates,duration:level==='work'||level==='error'?Infinity:level==='result'?1800:0,quiet,id:idKey});
      actor.hidden=quiet&&!['work','result','error'].includes(level);
      if(e){display(e);if(level==='result'){actor.dataset.gwenReport=String(current.result);actor.dataset.announcements=String((Number(actor.dataset.announcements)||0)+1);}}
      if(level==='result'){
        const artKey=JSON.stringify([idKey,kind,portrait]);
        if(!resultArts.has(artKey))resultArts.set(artKey,e?.art||p.pick(candidates));
        if(resultArts.size>256)resultArts.delete(resultArts.keys().next().value);
        if(!e){display({kind,art:resultArts.get(artKey),speech:false,priority:PRIORITY.result});p.state.priority=PRIORITY.result;}
      }
      if(level!=='result')delete actor.dataset.gwenReport;
      cycleAt=clock+(mq.matches?20000:9000);restoreAt=0;
    }
    function sync(next){current={...next};if(!['home','direct'].includes(current.mode)){if(actor){cancelMove();actor.remove();}phaseKey='';return;}
      const key=JSON.stringify([current.mode,current.phase,current.result,current.stale,current.better,current.recoHigher,current.step,innerWidth>=1200]);
      if(key!==phaseKey){const stepChanged=current.phase==='work'&&lane?.id==='direct-progress-lane';phaseKey=key;if(stepChanged){cancelMove();x=0;if(actor)actor.style.transform='translateX(0px)';}
        startAt=0;startAction=null;
        if(current.phase==='work'&&visible()&&lane?.id==='direct-board-lane'&&!quiet&&!mq.matches){
          const e=p.event('start',clock,{level:'work',duration:Infinity});display(e);exit=Infinity;startAt=clock+250;startAction='exit';
        }else{exit=null;settle();if(current.phase==='work'&&!quiet){display(p.event('start',clock,{level:'work',duration:Infinity}));startAt=clock+250;startAction='cycle';}}
      }
      if(current.phase==='work'&&exit==null&&!startAt&&!move&&clock>=landing&&lane){
        if(Number.isFinite(current.progress)){const reaction={kind:'work',art,speech:false,priority:PRIORITY.work};moveTo(current.progress*(lane.clientWidth-actor.offsetWidth),{reaction});}
      }
    }
    function edit(action,slot){idleAt=clock;vacant=false;sleeping=false;
      if(current.mode==='direct'&&current.phase==='work'&&action==='skip'&&!quiet){
        if(setLane('direct-progress-lane')){request('skip',{level:'work',duration:1500});restoreAt=clock+1500;}return;
      }
      if(current.mode!=='direct'||current.phase==='work'||current.phase==='error'||quiet)return;
      if(p.state.priority>=PRIORITY.result&&clock<p.state.until)return;
      if(!setLane('direct-board-lane'))return;lane.dataset.portrait='false';
      const kind=action==='put'&&current.count===4?'complete':({put:'put',remove:'remove',swap:'swap',leader:'leader',grown:'grown',withReco:'withReco',withGrowth:'withGrowth',skip:'skip',brk:'brk',arrange:'swap',clear:'empty',undo:'swap',focus:'point'}[action]||'empty');
      const cell=doc.querySelector(`[data-direct-slot="${slot}"]`),r=cell?.getBoundingClientRect(),l=lane.getBoundingClientRect();
      const target=kind==='complete'?(lane.clientWidth-actor.offsetWidth)/2:r?r.x+r.width/2-l.x-actor.offsetWidth/2:null;
      request(kind,{level:'edit',candidates:kind==='point'?['point']:undefined,target,run:action==='put'});
    }
    function input(e){if(!visible())return;idleAt=clock;vacant=false;
      if(sleeping){sleeping=false;request('wake',{level:'idle'});restoreAt=clock+1500;}
      const choice=e.target?.closest?.('[data-pn-choice]');if(current.mode==='home'&&choice&&!quiet){
        const direction=choice.dataset.pnChoice==='direct';actor.querySelector('button').style.transform=direction?'none':'scaleX(-1)';request('point',{candidates:['point']});}
    }
    function tick(){const now=performance.now(),on=visible(),delta=Math.max(0,now-last);last=now;
      if(!on){move?.animation.pause();if(actor)actor.dataset.lanePaused='true';return;}
      clock+=Math.min(delta,1000);actor.dataset.lanePaused=String(mq.matches);if(move?.animation.playState==='paused')move.animation.play();
      if(startAt&&clock>=startAt){startAt=0;if(startAction==='exit')moveTo(lane.clientWidth-actor.offsetWidth,{run:true,leave:true});else request(base()[0],{level:'work',duration:Infinity});startAction=null;}
      if(move&&move.animation.playState==='finished'){
        const m=move,reaction=pending;x=m.to;m.animation.cancel();move=null;actor.style.transform=`translateX(${x}px)`;
        // A long lane is crossed in bounded segments, never by a cross-column absolute jump.
        if(Math.abs(m.target-x)>.5){moveTo(m.target,{run:m.run,reaction,leave:m.leave,adjust:false});}
        else{landing=clock+150;pending=reaction;actor.removeAttribute('data-moving');if(m.leave)exit=landing;}
      }
      if(!move&&landing&&clock>=landing){landing=0;if(pending){display(pending);restoreAt=pending.priority===PRIORITY.edit?clock+1500:0;pending=null;}}
      if(exit!=null&&clock>=exit){exit=null;settle();}
      const bubble=actor.querySelector('.gwen-lane-speech');bubble.hidden=!!move||clock>=bubbleUntil;
      if(!bubble.hidden){const half=bubble.offsetWidth/2;
        bubble.style.left=Math.max(half-x,Math.min(actor.offsetWidth/2,lane.clientWidth-half-x))+'px';}
      if(restoreAt&&clock>=restoreAt&&!move&&!landing){restoreAt=0;settle();}
      if(current.phase==='work'&&exit==null&&clock>=cycleAt&&!move){
        request(base()[0],{level:'work',duration:Infinity});cycleAt=clock+(mq.matches?20000:9000);
        if(!Number.isFinite(current.progress))moveTo(Math.random()*(lane.clientWidth-actor.offsetWidth));
      }
      if(!['work','error'].includes(current.phase)&&!quiet){
        if(!sleeping&&clock-idleAt>=60000){sleeping=true;if(current.mode==='direct'){setLane('direct-board-lane');lane.dataset.portrait='false';}request('doze',{level:'idle',target:0});}
        else if(!vacant&&!sleeping&&current.mode==='direct'&&current.count<4&&clock-idleAt>=20000){vacant=true;request('vacant',{level:'idle'});}
      }
    }
    for(const type of ['pointerdown','keydown','input'])doc.addEventListener(type,input,{passive:true});
    doc.addEventListener('focusin',input);
    doc.addEventListener('visibilitychange',()=>{last=performance.now();if(doc.hidden)move?.animation.pause();});
    root.addEventListener('scroll',()=>{if(!visible())move?.animation.pause();},{passive:true,capture:true});
    root.addEventListener('resize',()=>{cancelMove();if(lane){x=Math.min(x,Math.max(0,lane.clientWidth-actor.offsetWidth));actor.style.transform=`translateX(${x}px)`;}sync(current);});
    mq.addEventListener('change',()=>{cancelMove();cycleAt=clock+(mq.matches?20000:9000);});
    const toggle=doc.getElementById('gwen-quiet');if(toggle){toggle.checked=quiet;toggle.addEventListener('change',()=>{
      quiet=toggle.checked;try{localStorage.setItem('pn.gwen.quiet',JSON.stringify(quiet));}catch{}
      doc.documentElement.dataset.gwenQuiet=String(quiet);cancelMove();bubbleUntil=0;settle();
    });}
    root.setInterval(tick,50);
    controller={sync,edit,policy:p,get state(){return {clock,x,moving:!!move,art,quiet,phase:current.phase,lane:lane?.id};}};return controller;
  }
  const api={PRIORITY,CHOICES,SAY,policy,travel,mount,resultId,sync:s=>mount()?.sync(s),edit:(a,i)=>mount()?.edit(a,i)};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GwenLane=api;
})(typeof window!=='undefined'?window:globalThis);
