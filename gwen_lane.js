// Presentation only. One movable actor, registered stages, and a visible-time clock.
(function(root){
  'use strict';
  const P=typeof module!=='undefined'&&module.exports?require('./gwen_policy'):root.GwenPolicy;
  const PRIORITY={idle:0,edit:1,work:2,result:3,error:4};
  const CHOICES={home:['guide2','st_welcome','welcome'],empty:['ready','present'],
    ready:['ready'],vacant:['think','sulk','peek'],put:['present','shy'],remove:['surprised','sulk'],
    swap:['think'],leader:['verdict'],complete:['jump'],grown:['train'],
    withReco:['files','board'],withGrowth:['train'],reco:['stakeout','magnify','files'],growth:['train','walk'],skip:['surprised'],recoHigher:['st_point','thoughtful'],brk:['charge'],work:['investigate','magnify','think','board','coffee','stakeout','stamp','files'],
    high:['st_verdict','st_cheer','st_ok','st_reach'],medium:['st_point','thoughtful'],low:['st_cry','notes'],
    better:['st_wink','st_reach'],past:['think'],error:['cry','surprised','sulk'],wait:['wait'],doze:['doze'],wake:['wake']};
  const SAY={home:['단장님, 어떤 방법으로 골라 볼까?','후후후, 두 방법 다 나만 믿어!','천재 조사관은 준비 끝이야!'],
    empty:['단장님, 구원자부터 골라 봐!','후후후, 어떤 조합이 될까?'],vacant:['빈 칸이 남았네, 단장님.','천천히 골라도 돼. 내가 기다릴게!'],
    put:['좋아, 이쪽으로 모실게!','후후후, 한 명 더 모였어!','단장님, 자리 확인해 봐!'],remove:['잠깐! 다른 조합도 볼까?','단장님, 다음 구원자는 누구야?'],
    swap:['이쪽 자리로 바꿔 볼까?','후후후, 배치도 중요하지!'],leader:['단장님, 이번 리더는 정했네!','앞장설 구원자, 확인했어!'],
    complete:['네 명 다 모였어, 단장님!','후후후, 준비됐으면 나만 믿어!'],grown:['이만큼 키웠다고 치고 볼게!','단장님, 달라진 능력치도 확인해 봐!','스타링크까지 더해서 볼게!'],
    withReco:['후후후, 내 추천이랑 겨뤄 보자는 거지?','좋아, 내 추천도 같이 꺼내 올게!'],withGrowth:['키웠을 때 편성도 찾아볼게!'],reco:['이번엔 내 추천 차례야, 단장님!','후보를 하나씩 살펴볼게.'],growth:['키우면 누가 좋을지 보고 있어!'],skip:['알았어, 그건 넘어갈게!'],recoHigher:['내 추천 쪽이 조금 더 높네. 비교해 봐, 단장님!'],
    brk:['브레이크 준비, 확인했어!','단장님, 이 스킬로 볼게!'],
    work:['하나씩 꼼꼼히 살펴볼게.','단장님, 조금만 기다려!','끝까지 확인할 테니 나만 믿어!'],
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
    function event(kind,now,{level='edit',candidates=CHOICES[kind],duration=1500,quiet=false,silent=false,id=null}={}){
      const priority=PRIORITY[level];
      if(priority<s.priority&&now<s.until)return null;
      if(quiet&&!['work','result','error'].includes(level))return null;
      if(level==='result'&&id!=null&&s.reports.has(id))return null;
      const cooled=level==='edit'&&now-s.lastReaction<4000;
      const speech=!silent&&!cooled&&now-s.lastSpeech>=6000;
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
  function playground(random=Math.random){
    const choices=policy(random);
    return {delay:()=>3000+random()*4000,pose:()=>random()<.15?'jump':choices.pick(['magnify','think','coffee','stamp']),next:(x,max)=>({
      target:x<max/2?max:0,run:random()<.25,
      duration:2000+random()*1000
    })};
  }

  // --- 무대 등록(register) ---
  // 각 무대(stage)는 mode 이름에 대응하며 {board, result, banner} DOM 요소를 가짐.
  // GwenLane.sync({mode}) 가 해당 무대를 사용함.
  const stages=new Map();
  function initBannerImages(bannerEl){
    for(const img of bannerEl?.querySelectorAll('img')||[]){
      const title=img.parentElement;
      const decoded=()=>img.decode().then(()=>{title.dataset.imageReady='true';},()=>{delete title.dataset.imageReady;});
      img.addEventListener('load',decoded);img.addEventListener('error',()=>{delete title.dataset.imageReady;});
      if(img.complete&&img.naturalWidth)decoded();
    }
  }
  function registerStage(key,elements){
    const previous=stages.get(key);
    if(previous?.banner&&previous.banner!==elements.banner)previous.banner.hidden=true;
    stages.set(key,elements);
    if(elements.banner&&previous?.banner!==elements.banner)initBannerImages(elements.banner);
    controller?.rebind(key);
  }

  let controller,serial=0;const resultIds=new WeakMap();
  function resultId(result){if(!resultIds.has(result))resultIds.set(result,++serial);return resultIds.get(result);}
  function mount(){
    if(controller||!root.document)return controller;
    const doc=root.document,mq=root.matchMedia('(prefers-reduced-motion: reduce)'),p=policy(),play=playground(),resultArts=new Map();
    let actor=null,lane=null,current={},clock=0,last=performance.now(),idleAt=0,vacant=false,phaseKey='',cycleAt=0,
      restoreAt=0,bubbleUntil=0,speechShownAt=-Infinity,move=null,landing=0,pending=null,x=0,quiet=false,art='',lastEvent='',sleeping=false,workRestAt=0;
    let playAt=play.delay(),playing=null,imageRequest=0;
    const stageStates=new Map();let activeMode=null;
    function resetPlay(){playing=null;playAt=clock+play.delay();}
    try{quiet=JSON.parse(localStorage.getItem('pn.gwen.quiet')||'false')===true;}catch{}
    doc.documentElement.dataset.gwenQuiet=String(quiet);
    const pickBanner=P.bannerPicker();
    let bannerKey='';
    function currentBanner(){return stages.get(current.mode)?.banner||null;}
    function syncBanner(){const banner=currentBanner();
      // 비활성 무대의 배너는 숨김
      for(const [,s] of stages)if(s.banner&&s.banner!==banner)s.banner.hidden=true;
      if(!banner)return;
      const stage=stages.get(current.mode);
      const onBoard=!!stage?.board&&actor?.parentElement===stage.board;
      const state=P.bannerState(current,onBoard);
      banner.hidden=!state;
      if(state!==bannerKey||banner.dataset.state!==state){banner.dataset.state=state;bannerKey=state;}
      const phrase=pickBanner(state,current.result);
      banner.dataset.phrase=phrase;
      for(const title of banner.querySelectorAll('[data-phrase]'))title.hidden=title.dataset.phrase!==phrase;
    }
    function ensure(){if(actor)return;actor=doc.createElement('div');actor.className='gwen-lane-actor';actor.dataset.gwen='lane';
      actor.innerHTML='<span class="gwen-lane-speech" aria-hidden="true"></span><button type="button" class="gwen-lane-poke" aria-label="그웬 부르기"></button><span class="gwen-announcement" role="status" aria-live="polite"></span>';
      actor.querySelector('button').addEventListener('click',()=>{
        const e=p.poke(clock,lane?.dataset.portrait==='true',quiet);if(e){resetPlay();cancelMove();display(e);restoreAt=clock+1500;}
      });
    }
    function visible(){if(!actor||!lane||doc.hidden||!actor.isConnected)return false;
      const r=actor.getBoundingClientRect();return lane.getClientRects().length>0&&r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth&&!lane.closest('[hidden]');}
    function cancelMove(){if(move){const pos=move.animation.currentTime||0;const ratio=Math.min(1,pos/Math.max(1,move.ms));x=move.from+(move.to-move.from)*ratio;move.animation.cancel();move=null;}
      if(actor)actor.style.transform=`translateX(${x}px)`;landing=0;pending=null;actor?.removeAttribute('data-moving');}
    function setLane(el){ensure();if(!el)return false;
      if(lane!==el||actor.parentElement!==el){cancelMove();lane=el;lane.append(actor);x=Math.max(0,(lane.clientWidth-actor.offsetWidth)/2);actor.style.transform=`translateX(${x}px)`;}
      syncBanner();
      return true;}
    function image(key){if(key===art)return;art=key;const request=++imageRequest;
      const holder=doc.createElement('div');holder.innerHTML=root.Ux.gwenImage(key,'gwen-lane-image',80);
      const next=holder.firstElementChild;if(!next)return;
      next.dataset.gwenManaged='true';next.loading='eager';next.src=new URL(next.dataset.gwenStatic,doc.baseURI).href;
      if(current.phase==='result')next.dataset.gwenOnce=String(current.result);
      next.decode().then(()=>{if(request!==imageRequest)return;
        next.dataset.gwenLoaded='true';actor.querySelector('button').replaceChildren(next);
        actor.dataset.gwenExpression=key;
      }).catch(()=>{});
      actor.dataset.event=lastEvent;}
    function positionSpeech(){const bubble=actor.querySelector('.gwen-lane-speech');
      if(!bubble.hidden){const half=bubble.offsetWidth/2;
        bubble.style.left=Math.max(half-x,Math.min(actor.offsetWidth/2,lane.clientWidth-half-x))+'px';}}
    function display(e){if(!e)return;lastEvent=e.kind;image(e.art);actor.dataset.event=e.kind;actor.dataset.priority=String(e.priority);
      const bubble=actor.querySelector('.gwen-lane-speech');
      if(e.speech&&!quiet&&clock-speechShownAt>=6000){const lines=SAY[e.kind]||SAY.work;bubble.textContent=lines[Math.floor(Math.random()*lines.length)];bubbleUntil=clock+2500;speechShownAt=clock;p.state.lastSpeech=clock;}
      else bubbleUntil=0;
      bubble.hidden=clock>=bubbleUntil;positionSpeech();}
    function moveTo(target,{run=false,reaction=null,adjust=true}={}){
      cancelMove();const mobile=innerWidth<=400,size=actor.offsetWidth,max=Math.max(0,lane.clientWidth-size);
      target=Math.max(0,Math.min(max,target));
      if(mobile&&adjust)target=x+(target-x)*.5;
      const stage=stages.get(current.mode);
      const isHome=stage?.board===lane&&current.mode==='home';
      const step=travel(x,target,lane.clientWidth,size,{run,mobile,reduced:mq.matches,quiet,home:isHome});
      if(!step.ms){if(reaction)display(mq.matches&&reaction.art==='jump'?{...reaction,art:'ready'}:reaction);return;}
      actor.querySelector('.gwen-lane-speech').hidden=true;image(run?'run':'walk');actor.dataset.moving='true';
      actor.querySelector('button').style.transform=target<x?'scaleX(-1)':'none';
      pending=reaction;const from=x;
      const animation=actor.animate([{transform:`translateX(${from}px)`},{transform:`translateX(${step.x}px)`}],{duration:step.ms,easing:'linear',fill:'forwards'});
      move={animation,from,to:step.x,ms:step.ms,target,run};
    }
    function request(kind,opts={}){const e=p.event(kind,clock,{quiet,...opts});if(!e)return false;
      resetPlay();
      if(opts.target!=null)moveTo(opts.target,{run:opts.run,reaction:e});else{cancelMove();display(e);}
      if(opts.level==='edit'||!opts.level)restoreAt=clock+1500+(move?move.ms+150:0);return true;}
    function base(){
      const stage=stages.get(current.mode);if(!stage)return [null,null];
      if(current.mode==='home')return ['home',stage.board];
      if(current.phase==='work')return ['work',stage.board];
      if(current.phase==='error')return ['error',stage.result||stage.board];
      if(current.phase==='result')return [current.recoHigher?'recoHigher':current.better?'better':!Number.isFinite(current.clear)?'medium':current.clear>=.7?'high':current.clear>=.05?'medium':'low',stage.result||stage.board];
      if(current.stale)return ['past',stage.board];
      if(current.count>0&&current.count<4)return ['wait',stage.result||stage.board];
      return [current.count===0?'empty':'ready',stage.board];
    }
    function settle(){
      if(stages.get(current.mode)?.resultExternal&&current.phase==='result'){render(current);return;}
      const [kind,el]=base();if(!setLane(el))return;
      const stage=stages.get(current.mode);
      // 결과는 항상 등신대(st_*). 좁은 화면에서도 CSS 가 크기를 줄여 표시함.
      const portrait=!!stage?.result&&lane===stage.result;
      lane.dataset.portrait=String(portrait);
      let candidates=CHOICES[kind];
      if(current.phase==='result')candidates=P.resultCandidates(current.clear,current.better,current.recoHigher);
      if(kind==='home')candidates=innerWidth>=1200?CHOICES.home:['guide2','welcome','present'];
      const level=current.phase==='error'?'error':current.phase==='result'?'result':current.phase==='work'?'work':'idle';
      p.state.until=clock;const idKey=level==='result'?current.result:null;
      const e=p.event(kind,clock,{level,candidates,duration:level==='work'||level==='error'?Infinity:level==='result'?1800:0,id:idKey});
      actor.hidden=false;
      if(e){display(e);if(level==='result'){actor.dataset.gwenReport=String(current.result);actor.dataset.announcements=String((Number(actor.dataset.announcements)||0)+1);}}
      if(level==='result'){
        const artKey=JSON.stringify([idKey,kind,portrait]);
        if(!resultArts.has(artKey))resultArts.set(artKey,e?.art||p.pick(candidates));
        if(resultArts.size>256)resultArts.delete(resultArts.keys().next().value);
        if(!e){display({kind,art:resultArts.get(artKey),speech:false,priority:PRIORITY.result});p.state.priority=PRIORITY.result;}
      }
      if(level!=='result')delete actor.dataset.gwenReport;
      cycleAt=clock+(mq.matches?20000:9000);restoreAt=0;resetPlay();
    }
    function progressMove(){
      if(current.phase!=='work'||!visible()||quiet||mq.matches||move||landing||restoreAt||clock<workRestAt)return;
      if(!Number.isFinite(current.progress))return;
      const target=Math.max(0,Math.min(1,current.progress))*Math.max(0,lane.clientWidth-actor.offsetWidth);
      if(target>x+.5)moveTo(target,{reaction:{kind:'work',art:p.pick(CHOICES.work),speech:false,priority:PRIORITY.work},adjust:false});
    }
    // State writers own one stage; only navigation chooses the visible stage.
    function sync(next){stageStates.set(next.mode,{...next});if(next.mode===activeMode)render(next);}
    function activate(mode){activeMode=mode;render(stageStates.get(mode)||{mode,phase:'idle',count:0});}
    function rebind(mode){
      if(mode!==current.mode)return;
      if(stages.get(mode)?.resultExternal&&current.phase==='result'){render(current);return;}
      const [,el]=base();
      if(!el||lane===el&&actor?.parentElement===el){syncBanner();return;}
      // A replaced host invalidates decode and movement, but not report/speech history.
      ++imageRequest;const previousArt=art;art='';
      cancelMove();resetPlay();setLane(el);
      lane.dataset.portrait=String(el===stages.get(mode)?.result);
      if(previousArt)image(previousArt);
      positionSpeech();
    }
    function render(next){current={...next};
      if(current.bundleRunning&&current.phase==='result')current.phase='work';
      syncBanner();
      if(!stages.has(current.mode)){if(actor){cancelMove();actor.remove();}phaseKey='';return;}
      // Automatic results own a portrait inside their summary; the lane keeps only its banner.
      if(stages.get(current.mode).resultExternal&&current.phase==='result'){
        ++imageRequest;cancelMove();resetPlay();actor?.remove();lane=null;art='';phaseKey='';syncBanner();return;
      }
      const key=JSON.stringify(current.phase==='work'?[current.mode,'work',current.step]:[current.mode,current.phase,current.result,current.stale,current.better,current.recoHigher,current.step,innerWidth>=1200]);
      if(key!==phaseKey){resetPlay();cancelMove();phaseKey=key;settle();
        if(current.phase==='work'){x=0;actor.style.transform='translateX(0px)';positionSpeech();workRestAt=clock+250;}
      }
      else rebind(current.mode);
      progressMove();
    }
    function edit(action,slot){idleAt=clock;vacant=false;sleeping=false;
      if(playing){cancelMove();resetPlay();}
      const stage=stages.get(current.mode);
      if(current.mode==='direct'&&current.phase==='work'&&action==='skip'&&!quiet){
        if(stage?.board&&setLane(stage.board)){request('skip',{level:'work',duration:1500});restoreAt=clock+1500;}return;
      }
      if(current.mode!=='direct'||current.phase==='work'||current.phase==='error'||quiet)return;
      if(p.state.priority>=PRIORITY.result&&clock<p.state.until)return;
      if(!stage?.board||!setLane(stage.board))return;lane.dataset.portrait='false';
      const kind=action==='put'&&current.count===4?'complete':({put:'put',remove:'remove',swap:'swap',leader:'leader',grown:'grown',withReco:'withReco',withGrowth:'withGrowth',skip:'skip',brk:'brk',arrange:'swap',clear:'empty',undo:'swap',focus:'point'}[action]||'empty');
      const cell=doc.querySelector(`[data-direct-slot="${slot}"]`),r=cell?.getBoundingClientRect(),l=lane.getBoundingClientRect();
      const target=kind==='complete'?(lane.clientWidth-actor.offsetWidth)/2:r?r.x+r.width/2-l.x-actor.offsetWidth/2:null;
      request(kind,{level:'edit',candidates:kind==='point'?['point']:undefined,target,run:action==='put'});
    }
    function input(e){if(!visible())return;idleAt=clock;vacant=false;
      if(playing){cancelMove();playing=null;image('ready');}resetPlay();
      if(sleeping){sleeping=false;request('wake',{level:'idle'});restoreAt=clock+1500;}
      const choice=e.target?.closest?.('[data-pn-choice]');if(current.mode==='home'&&choice&&!quiet){
        const direction=choice.dataset.pnChoice==='direct';actor.querySelector('button').style.transform=direction?'none':'scaleX(-1)';request('point',{candidates:['point']});}
    }
    function tick(){const now=performance.now(),on=visible(),delta=Math.max(0,now-last);last=now;
      if(!on){move?.animation.pause();if(actor)actor.dataset.lanePaused='true';return;}
      clock+=Math.min(delta,1000);actor.dataset.lanePaused=String(mq.matches);if(move?.animation.playState==='paused')move.animation.play();
      if(move&&move.animation.playState==='finished'){
        const m=move,reaction=pending;x=m.to;m.animation.cancel();move=null;actor.style.transform=`translateX(${x}px)`;
        if(Math.abs(m.target-x)>.5){moveTo(m.target,{run:m.run,reaction,adjust:false});}
        else{landing=clock+150;pending=reaction;actor.removeAttribute('data-moving');workRestAt=landing+900;}
      }
      if(!move&&landing&&clock>=landing){landing=0;if(pending){if(playing)pending={...pending,art:play.pose()};display(pending);restoreAt=pending.priority===PRIORITY.edit?clock+1500:0;pending=null;
        if(playing){playing.until=clock+playing.duration;actor.querySelector('button').style.transform='none';}}}
      const bubble=actor.querySelector('.gwen-lane-speech');bubble.hidden=!!move||clock>=bubbleUntil;
      positionSpeech();
      if(restoreAt&&clock>=restoreAt&&!move&&!landing){restoreAt=0;settle();}
      if(current.phase==='work'&&clock>=cycleAt&&!move&&!landing&&!restoreAt){
        request(base()[0],{level:'work',duration:Infinity});cycleAt=clock+(mq.matches?20000:9000);
      }
      progressMove();
      const stage=stages.get(current.mode);
      if(!['work','error','result'].includes(current.phase)&&!quiet){
        if(!sleeping&&clock-idleAt>=60000){sleeping=true;if(stage?.board){setLane(stage.board);lane.dataset.portrait='false';}request('doze',{level:'idle',target:0});}
        else if(!vacant&&!sleeping&&current.mode==='direct'&&current.count<4&&clock-idleAt>=20000){vacant=true;request('vacant',{level:'idle'});}
      }
      if(current.mode==='direct'&&!['work','error','result'].includes(current.phase)&&!mq.matches&&!quiet&&!sleeping){
        if(playing?.until&&clock>=playing.until){playing=null;image('ready');playAt=clock+play.delay();}
        if(!playing&&!move&&!landing&&!restoreAt&&clock>=playAt&&clock>=p.state.until){
          if(stage?.board)setLane(stage.board);lane.dataset.portrait='false';
          const plan=play.next(x,Math.max(0,lane.clientWidth-actor.offsetWidth));
          const e=p.event('play',clock,{level:'idle',candidates:['ready'],duration:0,silent:true});
          if(e){playing=plan;moveTo(plan.target,{run:plan.run,reaction:{...e,speech:false},adjust:false});
            if(!move){display({...e,art:play.pose(),speech:false});playing.until=clock+plan.duration;}}
        }
      }
    }
    for(const type of ['pointerdown','pointermove','keydown','input'])doc.addEventListener(type,input,{passive:true});
    doc.addEventListener('focusin',input);
    doc.addEventListener('visibilitychange',()=>{last=performance.now();if(doc.hidden)move?.animation.pause();syncBanner();});
    root.addEventListener('scroll',()=>{if(!visible())move?.animation.pause();},{passive:true,capture:true});
    root.addEventListener('resize',()=>{cancelMove();resetPlay();if(lane){x=Math.min(x,Math.max(0,lane.clientWidth-actor.offsetWidth));actor.style.transform=`translateX(${x}px)`;}sync(current);});
    mq.addEventListener('change',()=>{cancelMove();resetPlay();cycleAt=clock+(mq.matches?20000:9000);syncBanner();});
    const toggle=doc.getElementById('gwen-quiet');if(toggle){toggle.checked=quiet;toggle.addEventListener('change',()=>{
      quiet=toggle.checked;try{localStorage.setItem('pn.gwen.quiet',JSON.stringify(quiet));}catch{}
      doc.documentElement.dataset.gwenQuiet=String(quiet);cancelMove();bubbleUntil=0;settle();doc.dispatchEvent(new Event('gwenquietchange'));
    });}
    root.setInterval(tick,50);
    controller={sync,activate,rebind,edit,policy:p,get state(){return {clock,x,moving:!!move,art,quiet,mode:current.mode,phase:current.phase,lane:lane?.id,playing:!!playing,playAt};}};return controller;
  }
  // 하위 호환: bannerState·bannerPicker·BANNER_COPY 는 gwen_policy 에서 재내보냄
  const api={PRIORITY,CHOICES,SAY,policy,travel,playground,bannerState:P.bannerState,bannerPicker:P.bannerPicker,BANNER_COPY:P.BANNER_COPY,registerStage,mount,resultId,sync:s=>mount()?.sync(s),activate:mode=>mount()?.activate(mode),edit:(a,i)=>mount()?.edit(a,i)};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GwenLane=api;
})(typeof window!=='undefined'?window:globalThis);
