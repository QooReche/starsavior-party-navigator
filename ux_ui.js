// Presentation only: probability labels, accessible help, and isolated power comparisons.
(function(root){
  'use strict';
  const U=typeof module!=='undefined'&&module.exports?require('./ui_shared'):root.UiShared;
  const S=typeof module!=='undefined'&&module.exports?require('./myinfo_stats'):root.MyInfoStats;
  const esc=U.esc, num=v=>Number.isFinite(v)?Math.round(v).toLocaleString('ko-KR'):'—';
  const labels={level:'스타링크',equip:'장비',skills:'스킬',resonance:'공명',journey:'스텔라 아카이브',potentials:'잠재력',favor:'호감도'};
  const names=['힘','체력','인내','집중','보호'];
  const skillNames={basic:'기본',special:'특수',ultimate:'궁'};
  const clone=x=>JSON.parse(JSON.stringify(x));
  function verdict(p){return p>=.9?['safe','안정적']:p>=.7?['ok','깰 수 있음']:p>=.5?['shaky','아슬아슬']:['risk','어려움'];}
  function help(title,text){return `<button type="button" class="ux-help" data-help="${esc(text)}" aria-label="${esc(title)} 설명" aria-expanded="false">ⓘ</button>`;}
  // 공식 SD를 참고한 팬 그림. 동작 줄이기에서는 정지 PNG만 사용함.
  // 방문별 초기 대사는 전체 후보 중 선택하며 재렌더해도 같은 줄에서 시작함.
  const GWEN_LINES={
    inspect:['그웬이 추천 편성 확인 중…','그웬이 단서 모으는 중…','그웬이 사건 파일 펴는 중…'],
    screen:['그웬이 후보 거르는 중…','용의자… 아니 후보 거르는 중…','그웬이 서류 더미 뒤지는 중…'],
    long:['그웬이 끈질기게 검증 중…','그웬이 잠복 수사 중…','그웬이 상위 편성 탐문 중…'],
    report:['조사 끝 · 보고함']};
  const gwenSeed=root.document?Math.random():0;
  const gwenLine=mode=>{const lines=GWEN_LINES[mode];return lines?lines[Math.floor(gwenSeed*lines.length)]:'';};
  // 그웬 대사는 상황별 6개. 보이는 동안 12초마다 다음 줄, 읽기 도구는 클릭 반응만 알림.
  const GWEN_SAY={
    inspect:["단서는 끈질기게 모으는 법이지","사건 파일부터 펼쳐 볼게","좋아, 수사를 시작해 볼까?","단서가 슬슬 모이는걸","한눈에 간파해 줄게… 조금만!","천재 조사관에게 맡겨"],
    screen:["후보를 하나씩 탐문 중…","수상한 후보는 내가 걸러 낼게","답은 서류 더미 속에 있어!","후후후, 실마리가 보여","단장님, 꼼꼼히 볼게","한 장도 놓칠 수 없지"],
    long:["잠복은 내 특기야","끝까지 파헤치는 게 탐정이지","진실을 밝히는 빛! …지지직","조금만 더, 거의 다 왔어","단장님, 나만 믿어","흥, 쉽게 포기할 줄 알아?"],
    report:["조사 끝! 보고할게","수사 완료, 결과 나왔어!","흠, 한 끗이 아쉬운데","단장님, 파일을 확인해 봐","여기까지가 내 추리야","후후후, 단서를 정리했어"],
    error:["으… 단서가 부족해","이런, 수사가 막혔어…","음… 이건 예상 밖인데","잠깐! 다시 확인할게","단장님, 조금만 기다려","이 파일은 더 살펴봐야겠어"],
    high:["사건 해결! 이 편성이면 충분해","범인은… 아니, 정답은 바로 이 편성!","이 편성, 내가 보증할게!","역시 천재 조사관이지!","후후후, 한눈에 간파했지","단장님, 내 추리 어때?"],
    shaky:["아슬아슬해… 한 번 더 확인해 봐","반반 승부야. 방심은 금물!","흠, 한 끗이 아쉬운데","단장님, 꼼꼼히 살펴봐","아직 변수는 남아 있어","한 번 더 단서를 모아 보자"],
    hard:["이대론 벅차. 편성을 손봐야겠어","단서가 더 필요해. 육성도 살펴봐","흥, 제법 어려운 사건이네","단장님, 다른 조합도 볼까?","실마리를 더 찾아야겠어","천재 조사관도 준비는 필요해"],
    low:["이 사건은 만만치 않아. 육성부터 하자","지금은 무리야. 힘부터 기르자","으으… 이번 사건은 어렵네","단장님, 준비부터 다시 해 볼까?","단서를 차근차근 모아 보자","다음 수사엔 더 잘할 거야"],
    best:["더 키울 필요 없어. 이대로 충분해!","이미 최선의 편성이야, 단장님","후후후, 준비가 완벽한걸","단장님, 지금도 든든해","내가 봐도 잘 갖췄네","이 사건은 준비 끝이야"],
    welcome:["어서 와, 단장님! 어떤 사건이야?","그웬 탐정 사무소에 잘 왔어!","사건이라면 나한테 맡겨!","후후후, 오늘도 나만 믿어","천재 조사관 그웬, 대기 중!","단장님, 무슨 단서를 가져왔어?"],
    import:["단장님의 정보! 내가 받아 갈게","정보만 주면 수사는 내가 할게","사건 파일은 여기로 줘","후후후, 단서가 늘겠는걸","단장님, 준비되면 불러","차근차근 살펴볼게"],
    empty:["명단이 비었네. 정보부터 받아 올까?","아직 사건 파일이 텅 비었어","단장님, 명단부터 보여 줘","수사엔 단서가 필요하지","파일이 오면 바로 볼게","흥, 빈 서류로는 추리 못 해"],
    idle:["단장님, 사건 파일 골랐어?","조사야? 사건이야? 나에게 맡겨","후후후, 오늘도 나만 믿어","천재 조사관은 준비 끝이야","단장님, 어떤 사건부터 볼까?","한눈에 간파할 준비 됐어"],
    verdict:["범인은 바로… 이 편성이야!","후후후, 한눈에 간파했지","단장님, 답을 찾았어!","천재 조사관의 추리 완료!","내가 말했지? 나만 믿으라고","바로 이 조합이었어!"],
    cheer:["역시 천재 조사관이지!","해냈어, 단장님!","후후후, 멋진 수사였어","좋아! 실마리가 풀렸어","단장님, 내 솜씨 봤어?","이 정도는 맡겨 두라고!"],
    cry:["으아앙, 잠깐! 다시 볼게!","아냐, 내 실수 아니야!","으으… 이번 사건은 어렵네","단장님, 조금만 도와줘","잠깐! 파일이 꼬였어","다시 보면 풀 수 있을 거야"],
    sulk:["흥, 단서가 하나도 없잖아","자꾸 누르면 삐질 거야","흥, 천재 조사관도 쉬어야지","단장님, 너무하는 거 아냐?","나 지금 생각 중이거든!","단서를 더 가져와 줘"],
    shy:["왜, 왜 불러?","간지러워, 단장님!","잠깐! 깜짝 놀랐잖아","나 찾았어, 단장님?","흥, 부르면 대답은 해 줄게","그렇게 보면 쑥스럽잖아"],
    doze:["…졸면 안 돼… 쿨","안 잤어! 진짜야!","잠복 중이야… 잠복…","단장님… 파일은 거기에…","눈만 잠깐 감은 거야","천재 조사관도… 쉬어야…"],
    think:["흠, 이 단서는 말이지…","한눈에 간파해 줄게… 조금만!","잠깐! 뭔가 떠올랐어","후후후, 연결이 보이는걸","천재 조사관의 생각 시간!","단장님, 퍼즐이 맞아 가"],
    magnify:["작은 단서도 놓칠 수 없지","여기, 뭔가 있어!","단장님, 조금만 가까이 볼게","돋보기로 보면 다 보여","후후후, 찾았다!","바닥부터 꼼꼼히 살펴볼게"],
    stamp:["이 파일은 확인 끝!","도장 하나, 단서 하나","단장님, 차근차근 정리 중이야","후후후, 서류도 완벽하지","검토한 건 표시해 둬야지","천재 조사관의 확인 도장!"],
    board:["단서들이 이어지고 있어","이쪽과 저쪽이 연결되네","단장님, 큰 그림이 보여","후후후, 사건의 흐름이야","한 장씩 붙여 보면 알 수 있지","빠진 조각을 찾아볼게"],
    coffee:["커피 한 모금, 추리 한 번","단장님, 잠깐 숨 돌릴게","후후후, 정신이 번쩍 드네","서류는 끝까지 읽어야지","차근차근 마저 살펴볼게","아직 식기 전에 끝내 볼까?"],
    stakeout:["잠복은 내 특기야","쉿, 단서를 기다리는 중이야","단장님, 여기서 지켜볼게","흥, 끈기라면 자신 있어","신문 뒤에서도 다 보여","곧 실마리가 나타날 거야"],
    zap:["진실을 밝히는 빛! …지지직","잠깐! 너무 반짝였나?","후후후, 번뜩이는 추리야","단장님, 놀라진 않았지?","천재 조사관의 반짝이는 생각!","실마리가 번쩍 떠올랐어"],
    poke:["왜, 왜 불러?","간지러워, 단장님!","자꾸 누르면 삐질 거야","잠깐! 깜짝 놀랐잖아","단장님, 나 여기 있어","흥, 수사에 집중해야지"]};
  const gwenSayLine=key=>{const lines=Object.hasOwn(GWEN_SAY,key)?GWEN_SAY[key]:null;return lines?lines[Math.floor(gwenSeed*lines.length)]:'';};
  // 클리어율 구간(판정 칩과 같은 경계): 70% 이상·50% 이상·5% 이상·그 미만.
  const gwenSayBand=p=>!Number.isFinite(p)?'':p>=.7?'high':p>=.5?'shaky':p>=.05?'hard':'low';
  // 말풍선은 장식(같은 뜻의 안내·판정이 옆에 글로 있음)이라 읽기 도구에는 숨김. tail = 꼬리가 향하는 쪽(down·up·left·right).
  function gwenSay(key,tail='down'){
    const line=gwenSayLine(key);
    return line?`<span class="gwen-bubble" data-gwen-say="${esc(key)}" data-tail="${esc(tail)}" aria-hidden="true">${esc(line)}</span>`:'';
  }
  // file/blink를 채우면 새 그림이 연결됨. 미연결 그림은 fallback을 사용함.
  const GWEN_SCENES={
    investigate:{file:'investigate'},files:{file:'files'},walk:{file:'walk',loop:true},
    report:{file:'report'},surprised:{file:'surprised'},welcome:{file:'welcome'},
    confident:{file:'confident'},thoughtful:{file:'thoughtful'},notes:{file:'notes'},ready:{file:'ready'},
    cry:{file:null,fallback:'surprised'},verdict:{file:null,fallback:'report'},cheer:{file:null,fallback:'report'},
    sulk:{file:null,fallback:'surprised'},shy:{file:null,fallback:'ready'},doze:{file:null,fallback:'ready'},
    think:{file:null,fallback:'report'},magnify:{file:null,fallback:'files'},
    stamp:{file:null,fallback:'report'},board:{file:null,fallback:'investigate'},coffee:{file:null,fallback:'files'},
    stakeout:{file:null,fallback:'investigate'},zap:{file:null,fallback:'surprised'}
  };
  const GWEN_CYCLES={inspect:['investigate','think','magnify'],screen:['files','stamp','board'],long:['walk','stakeout','zap','coffee']};
  function gwenAsset(key){
    if(!Object.hasOwn(GWEN_SCENES,key))return null;
    const scene=GWEN_SCENES[key];
    const actual=scene.file?key:scene.fallback,entry=GWEN_SCENES[actual],base='assets/ui_icons/gwen/'+entry.file;
    return {art:actual,still:base+'.png',motion:entry.motion===false?'':base+'.webp',blink:entry.blink?'assets/ui_icons/gwen/'+entry.blink:'',loop:!!entry.loop};
  }
  function gwenImage(art,cls='gwen-worker',size=160){
    const a=gwenAsset(art);if(!a)return '';
    return `<img class="${cls}" data-gwen-expression="${art}" data-gwen-art="${a.art}" data-gwen-static="${a.still}" data-gwen-motion="${a.motion}" width="${size}" height="${size}" alt="" aria-hidden="true" loading="lazy">`;
  }
  function gwenReaction(p){
    if(!Number.isFinite(p))return '';
    const art=p<.05?'notes':p<.7?'thoughtful':'confident';
    return `<div class="gwen-reaction" data-gwen-reaction="${art}" aria-hidden="true"><div class="gwen-bubble-space">${gwenSay(gwenSayBand(p))}</div>${gwenImage(art,'gwen-reaction-art',240)}</div>`;
  }
  // 대기 칸: 그림만 버튼으로 감싸고 자동 말풍선은 읽기 도구에 숨김.
  function gwenIdle(){
    return `<span class="idle-gwen" data-gwen-idle>${gwenSay('idle','left')}<button type="button" class="gwen-poke" aria-label="그웬 부르기">${gwenImage('ready','idle-gwen-art',112)}</button><span class="gwen-announcement" role="status" aria-live="polite" aria-atomic="true"></span></span>`;
  }
  // 「지금 편성이 이미 최선」 안내(클리어 추천 육성 탭): 작은 그림 + 말풍선. 실패 그림(surprised)·실패 대사를 쓰지 않음.
  function gwenBest(){
    return `<span class="gwen-best" data-gwen-best aria-hidden="true">${gwenImage('confident','gwen-best-art',72)}${gwenSay('best','left')}</span>`;
  }
  function gwenWork(mode,say=mode,expression=null){
    const art=expression||({inspect:'investigate',screen:'files',long:'walk',error:'surprised',report:'report',welcome:'welcome'}[mode]);
    if(!art)return '';
    const label=gwenLine(mode);
    const roam=art==='walk';
    return `<span class="gwen-work${roam?' gwen-roam':''}" data-gwen="${mode}" data-gwen-expression="${art}">${typeof say==='string'&&gwenSayLine(say)?`<span class="gwen-say-lane">${gwenSay(say)}</span>`:''}<span class="gwen-track"><span class="gwen-traveler"><span class="gwen-scene" aria-hidden="true">${gwenImage(art)}</span></span></span>${label?`<span class="gwen-caption">${label}</span>`:''}</span>`;
  }
  // 발표 객체의 선택은 재렌더해도 고정. 확률이 없는 결과/점수형/배열은 중립임.
  const gwenResults=new WeakMap(),gwenPending=new Map();let gwenSerial=0;
  function gwenReport(result,context={}){
    if(!result||typeof result!=='object')return '';
    let state=gwenResults.get(result);
    if(!state){
      const p=context.kind==='score'||Array.isArray(result)?undefined:context.clear;
      const art=!Number.isFinite(p)?'report':p<.05?'cry':p>=.7?(gwenSeed<.5?'verdict':'cheer'):'report';
      state={id:String(++gwenSerial),remaining:1800,done:false,art};gwenResults.set(result,state);
    }
    if(state.done)return '';
    gwenPending.set(state.id,new WeakRef(state));
    return gwenWork('report',state.art,state.art).replace('data-gwen="report"',`data-gwen="report" data-gwen-report="${state.id}"`);
  }
  function gwenError(cause){
    if(['cancel','uncalculated','best'].includes(cause))return '';
    const art=cause==='calculation'?'cry':['few','empty'].includes(cause)?'sulk':'surprised';
    return gwenWork('error',art==='surprised'?'error':art,art);
  }
  // 최초 로딩의 opacity:0은 가시성 판정에서 제외하되, 조상 숨김·잘림은 검사함.
  function gwenVisible(img){
    const doc=root.document;
    if(doc.hidden||!img.isConnected||!img.getClientRects().length)return false;
    let r=img.getBoundingClientRect(),left=Math.max(0,r.left),right=Math.min(root.innerWidth,r.right),top=Math.max(0,r.top),bottom=Math.min(root.innerHeight,r.bottom);
    for(let el=img;el;el=el.parentElement){
      const c=root.getComputedStyle(el);
      if(c.visibility==='hidden'||c.visibility==='collapse'||c.display==='none'||(el!==img&&Number(c.opacity)===0))return false;
      if(el!==img){
        r=el.getBoundingClientRect();
        if(/hidden|clip|scroll|auto/.test(c.overflowX)){left=Math.max(left,r.left);right=Math.min(right,r.right);}
        if(/hidden|clip|scroll|auto/.test(c.overflowY)){top=Math.max(top,r.top);bottom=Math.min(bottom,r.bottom);}
      }
    }
    return right>left&&bottom>top;
  }
  // 장면 컨트롤러 한 개 = 마감 시각 표 한 개 + 다음 이벤트 timeout 한 개.
  // clock은 보이는 시간만 소비함. fetch/decode는 토큰을 확인한 뒤에만 그림을 교체함.
  function mountGwen(){
    const doc=root.document,media=root.matchMedia('(prefers-reduced-motion: reduce)');
    const states=new Map(),decoded=new Map(),blobs=new Map();
    const rand=(lo,span)=>lo+Math.floor(Math.random()*span);
    function decode(path){
      if(!decoded.has(path)){
        const image=new root.Image();image.src=path;
        decoded.set(path,image.decode().then(()=>image));
      }
      return decoded.get(path);
    }
    function bytes(path){
      if(!blobs.has(path))blobs.set(path,root.fetch(path).then(r=>{if(!r.ok)throw Error(r.status);return r.blob();}));
      return blobs.get(path);
    }
    function create(img){
      const scene=img.closest('[data-gwen], [data-gwen-idle], .gwen-reaction, .gwen-best, .gwen-greet, .gwen-guide-footer')||img;
      const bubble=scene.querySelector?.('.gwen-bubble'),idle=scene.hasAttribute('data-gwen-idle');
      const report=gwenPending.get(scene.dataset.gwenReport)?.deref();
      const s={img,scene,bubble,idle,report,token:0,timer:null,url:null,pendingURL:null,active:false,intersecting:false,
        clock:0,last:0,due:{},expression:img.dataset.gwenExpression||img.dataset.gwenArt,asset:null,still:null,phase:'rest',line:0,
        baseSay:bubble?.dataset.gwenSay,clicks:[],reduced:media.matches};
      function account(){
        if(!s.active)return;
        const now=Date.now(),delta=Math.max(0,now-s.last);s.last=now;s.clock+=delta;
        if(report&&!report.done&&s.still)report.remaining=Math.max(0,report.remaining-delta);
      }
      function release(){
        for(const key of ['url','pendingURL'])if(s[key]){root.URL.revokeObjectURL(s[key]);s[key]=null;}
      }
      function rest(){
        if(s.still){img.src=s.still;img.dataset.gwenLoaded='true';}
        img.dataset.gwenPlaying='false';s.phase='rest';
        release();
      }
      function invalidate(){
        s.token++;root.clearTimeout(s.timer);s.timer=null;
        rest();
      }
      function breathing(){
        img.dataset.gwenRest=String(s.active&&!media.matches&&s.phase==='rest'&&s.expression!=='walk');
        scene.dataset.gwenPaused=String(!s.active||media.matches);
      }
      function schedule(){
        root.clearTimeout(s.timer);s.timer=null;
        if(!s.active)return;
        let next=Math.min(...Object.values(s.due));
        if(report&&!report.done&&s.still)next=Math.min(next,s.clock+report.remaining);
        if(Number.isFinite(next))s.timer=root.setTimeout(tick,Math.max(1,next-s.clock));
      }
      function valid(token){return token===s.token&&s.active&&gwenVisible(img);}
      function say(key){
        if(!bubble||!GWEN_SAY[key])return;
        bubble.dataset.gwenSay=key;
        const lines=GWEN_SAY[key];bubble.textContent=lines[(Math.floor(gwenSeed*lines.length)+s.line)%lines.length];
      }
      async function show(path,phase,blob=false){
        const token=s.token;let url=null;s.phase='loading';breathing();
        try{
          let next=path;
          if(blob){
            const data=await bytes(path);if(!valid(token))return;
            next=url=root.URL.createObjectURL(data);s.pendingURL=url;
            const probe=new root.Image();probe.src=next;await probe.decode();
          }else await decode(path);
          if(!valid(token)){if(url&&s.pendingURL===url){root.URL.revokeObjectURL(url);s.pendingURL=null;}return;}
          account();const previous=s.url;img.src=next;img.dataset.gwenLoaded='true';
          s.url=url;s.pendingURL=null;if(previous)root.URL.revokeObjectURL(previous);
          s.phase=phase;img.dataset.gwenPlaying=String(phase==='action');
          if(phase==='action'&&!s.asset.loop)s.due.action=s.clock+1000;
          if(phase==='blink')s.due.open=s.clock+rand(120,41);
          breathing();schedule();
        }catch{
          if(url&&s.pendingURL===url){root.URL.revokeObjectURL(url);s.pendingURL=null;}
          if(valid(token)){rest();breathing();schedule();}
        }
      }
      function action(){
        delete s.due.action;
        if(!s.asset.motion||media.matches)return;
        show(s.asset.motion,'action',!s.asset.loop);
      }
      function resetDeadlines(){
        s.due={};
        if(!media.matches){
          s.due.line=s.clock+12000;
          if(GWEN_CYCLES[scene.dataset.gwen]&&s.baseSay!=='empty')s.due.cycle=s.clock+rand(8000,2001);
          if(idle&&s.expression==='ready')s.due.doze=s.clock+60000;
          if(s.asset.blink&&s.expression!=='walk')s.due.blink=s.clock+rand(3000,3001);
        }
        if(s.restoreAt!=null)s.due.restore=s.restoreAt;
      }
      function select(expression,key){
        account();invalidate();s.waiting=false;s.expression=expression;s.asset=gwenAsset(expression);s.line=0;
        scene.dataset.gwenExpression=expression;img.dataset.gwenExpression=expression;
        img.dataset.gwenArt=s.asset.art;img.dataset.gwenStatic=s.asset.still;img.dataset.gwenMotion=s.asset.motion;
        scene.classList.toggle('gwen-roam',scene.hasAttribute('data-gwen')&&expression==='walk');
        if(key)say(key);
        resetDeadlines();breathing();
        if(!s.active||!gwenVisible(img)){s.update();return;}
        const token=s.token;
        decode(s.asset.still).then(()=>{
          if(!valid(token))return;
          account();s.still=s.asset.still;img.src=s.still;img.dataset.gwenLoaded='true';
          breathing();action();schedule();
        }).catch(()=>{if(valid(token)){breathing();schedule();}});
        schedule();
      }
      function tick(){
        s.timer=null;if(!gwenVisible(img)){s.update();return;}account();
        if(report&&!report.done&&report.remaining<=0){report.done=true;gwenPending.delete(report.id);scene.remove();s.stop();return;}
        const due=key=>s.due[key]!=null&&s.due[key]<=s.clock;
        if(due('restore')){s.restoreAt=null;s.clicks=[];select('ready','idle');return;}
        if(due('doze')){select('doze','doze');return;}
        if(due('cycle')){
          const cycle=GWEN_CYCLES[scene.dataset.gwen],next=cycle[(cycle.indexOf(s.expression)+1)%cycle.length];
          select(next,GWEN_SAY[next]?next:scene.dataset.gwen);return;
        }
        if(due('line')){s.line++;say(bubble?.dataset.gwenSay);s.due.line=s.clock+12000;}
        if(due('action')){
          if(s.waiting){
            if(s.phase==='rest'){s.waiting=false;action();}
            else s.due.action=s.clock+200;
          }else{rest();s.due.action=s.clock+rand(4000,4001);s.waiting=true;}
        }
        else if(due('open')){
          delete s.due.open;rest();
          s.due.blink=s.clock+(s.doubleBlink?180:rand(3000,3001));s.doubleBlink=false;
        }
        else if(due('blink')){
          s.due.blink=s.clock+rand(3000,3001);
          if(s.phase==='rest'){
            s.doubleBlink=!s.secondBlink&&Math.random()<.15;s.secondBlink=s.doubleBlink;show(s.asset.blink,'blink');
          }
        }
        breathing();schedule();
      }
      s.stop=()=>{account();s.active=false;invalidate();breathing();};
      s.update=()=>{
        const on=gwenVisible(img);
        if(!on){if(s.active)s.stop();return;}
        if(s.active&&s.reduced===media.matches)return;
        if(s.active)s.stop();
        s.active=true;s.last=Date.now();s.reduced=media.matches;s.waiting=false;
        // 자동 대사/순환의 남은 시간은 숨김 동안 보존함.
        const deadlines={...s.due},line=s.line;select(s.expression,bubble?.dataset.gwenSay||s.baseSay);s.line=line;say(bubble?.dataset.gwenSay);
        if(!media.matches){for(const key of ['line','cycle','doze','restore'])if(deadlines[key]!=null)s.due[key]=deadlines[key];}
        schedule();
      };
      s.input=()=>{
        if(!idle||!s.active)return;account();
        if(s.expression==='doze'){s.restoreAt=null;select('ready','idle');}
        if(s.expression==='ready'&&!media.matches)s.due.doze=s.clock+60000;
        schedule();
      };
      s.poke=()=>{
        if(!s.active)return;account();const now=Date.now();
        s.clicks=s.clicks.filter(t=>now-t<=2000);s.clicks.push(now);
        const art=s.clicks.length>=5?'cry':s.clicks.length>=3?'sulk':'shy';
        s.restoreAt=s.clock+3000;select(art,art);
        const status=scene.querySelector('.gwen-announcement');if(status)status.textContent=gwenSayLine(art);
      };
      s.external=()=>{if(Object.hasOwn(GWEN_SCENES,img.dataset.gwenExpression)&&img.dataset.gwenExpression!==s.expression)select(img.dataset.gwenExpression);};
      return s;
    }
    const observer=new root.IntersectionObserver(entries=>{for(const e of entries){const s=states.get(e.target);if(s){s.intersecting=e.isIntersecting&&e.intersectionRect.width>0&&e.intersectionRect.height>0;s.update();}}},{threshold:[0,.001]});
    function refresh(){
      for(const [img,s] of states)if(!img.isConnected){s.stop();observer.unobserve(img);states.delete(img);}
      doc.querySelectorAll('img[data-gwen-art]').forEach(img=>{
        if(!states.has(img)){states.set(img,create(img));observer.observe(img);}
        const s=states.get(img);s.external();s.update();
      });
      for(const [id,ref] of gwenPending)if(!ref.deref())gwenPending.delete(id);
    }
    new root.MutationObserver(refresh).observe(doc.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','hidden','open','style','data-gwen-expression']});
    doc.addEventListener('visibilitychange',()=>{doc.documentElement.classList.toggle('gwen-paused',doc.hidden);refresh();});
    media.addEventListener('change',refresh);root.addEventListener('resize',refresh);root.addEventListener('scroll',refresh,true);
    for(const type of ['pointerdown','pointermove','keydown','input'])doc.addEventListener(type,()=>{for(const s of states.values())s.input();},{passive:true});
    doc.addEventListener('keydown',e=>{if(e.repeat&&['Enter',' '].includes(e.key)&&e.target.closest('.gwen-poke'))e.preventDefault();});
    doc.addEventListener('click',e=>{const b=e.target.closest('.gwen-poke');if(b)states.get(b.querySelector('img'))?.poke();});
    refresh();
  }
  // 헤더·메모·구원자 얼굴도 decode가 끝난 뒤 보임. 교체/제거된 노드에는 완료 표시를 쓰지 않음.
  function mountDecodedImages(){
    const doc=root.document,seen=new WeakMap();
    function refresh(){doc.querySelectorAll('img.gwen-head,.gwen-memo img,img.face,img.art').forEach(img=>{
      const path=img.getAttribute('src');if(!path||seen.get(img)===path)return;seen.set(img,path);delete img.dataset.imageLoaded;
      const finish=()=>img.decode().then(()=>{if(img.isConnected&&img.getAttribute('src')===path)img.dataset.imageLoaded='true';}).catch(()=>{});
      if(img.complete)finish();else img.addEventListener('load',finish,{once:true});
    });}
    new root.MutationObserver(refresh).observe(doc.body,{childList:true,subtree:true,attributes:true,attributeFilter:['src']});refresh();
  }

  function gwenStage(message=''){
    return /후보 거르|훑|예선|놓침 감지|1단계|2단계/.test(message)?'screen':/준비|능력치 계산/.test(message)?'inspect':'long';
  }
  // 진행률 갱신 때 단추와 그림 DOM을 보존하고, 단계가 바뀔 때만 연출을 교체함.
  function syncGwen(container,mode){
    const old=container?.querySelector('[data-gwen]');
    if(old&&old.dataset.gwen!==mode)old.outerHTML=gwenWork(mode);
  }
  let grades=null;
  function setGrades(table){grades=table;}
  function grade(value,index,table=grades){const rows=table?.stats?.[index];if(!Number.isFinite(value)||!rows||value>1500)return '';return rows.reduce((g,r)=>value>=r[0]?r[1]:g,'');}
  function archive(value,index,table){const g=grade(value,index,table);return (g?g+' ':'')+num(value);}
  function chip(p){const [state,label]=verdict(p);return `<span class="verdict-chip g-${state}" data-verdict="${state}">${label}</span>`;}
  // 운에 크게 좌우되는 결과 안내: 클리어율 5% 미만이거나, 95% 구간이 1% 밑에서 5% 이상까지 걸쳐 결론이 흔들릴 때만 문구를 낸다.
  // r = 시뮬 요약({clear, ci:[하한,상한], n}). 「30번 도전 시 한 번이라도 깰 확률」 = 1-(1-p)^30(판마다 독립 가정).
  const LUCK={low:.05,ciLo:.01,ciHi:.05,tries:30};
  const pctText=p=>{const v=Math.round(p*1000)/10;return (v>=10?Math.round(v):v)+'%';};
  function luckNote(r){const p=r?.clear;if(!Number.isFinite(p))return '';
    const ci=Array.isArray(r.ci)&&r.ci.every(Number.isFinite)?r.ci:null;
    const low=p<LUCK.low,shaky=!!ci&&ci[0]<LUCK.ciLo&&ci[1]>=LUCK.ciHi;
    if(!low&&!shaky)return '';
    const once=1-Math.pow(1-p,LUCK.tries);
    const head=p===0?`모의 전투 ${num(r.n)}판에서 한 번도 못 깼음.`:low?`클리어 확률 매우 낮음(약 ${pctText(p)}).`:`클리어 확률이 낮고 결과가 흔들림(약 ${pctText(p)}, 범위 ${pctText(ci[0])}~${pctText(ci[1])}).`;
    const tries=p>0?` ${LUCK.tries}번 도전해도 한 번이라도 깰 확률은 약 ${pctText(once)}임.`:'';
    return `<div class="luck-note" data-k="luck-note" role="note"><span class="gwen-memo"><img src="assets/ui_icons/gwen_header_72.png" width="20" height="20" alt="" aria-hidden="true">그웬의 메모</span>${head} 몇십 번 시도해도 못 깰 수 있음 — 파티 변경이나 추가 육성 권장.${tries}</div>`;}
  const signed=v=>v==null?'자료 없음':(v>=0?'+':'−')+num(Math.abs(v));
  function member(a,info,growth,content,table,view={}){
    const old=info.units.find(u=>u.id===a.unit.id),rule=S.rule_for_content(content),before=old?S.final_stats(old,info,growth,rule).power:0;
    if(!old)return null;
    const after=S.final_stats(a.unit,a.targetInfo||info,growth,rule).power;
    const fields=a.changedFields.filter(f=>rule!=='fixed200'||!['level','resonance'].includes(f)).map(f=>{
      // A missing unit has no account baseline. Do not invent its starting power.
      let delta=null;
      if(old){const unit=clone(old);let account=info;
        if(f==='level')account=a.targetInfo||info;
        else if(f==='journey'||f==='potentials'){unit.gauntlet||={};unit.gauntlet[f]=clone(a.unit.gauntlet[f]);}
        else unit[f]=clone(a.unit[f]);
        delta=S.final_stats(unit,account,growth,rule).power-before;
      }
      const c=a.changes[f]||{},b=c.before,t=c.after;let short='',detail='';
      if(f==='level')short=`Lv ${num(b)}→${num(t)}`;
      if(f==='resonance'||f==='favor')short=`${num(b??0)}→${num(t)}`;
      if(f==='skills'){
        const changed=Object.keys(skillNames).filter(k=>t?.[k]>(b?.[k]||0));
        const line=k=>`${skillNames[k]||k} ${b?.[k]||0}→${t?.[k]??b?.[k]??0}`;
        detail=Object.keys(skillNames).map(line).join('\n');
        short=changed.length<=2?changed.map(line).join(' · '):`${changed.length}종`;
      }
      if(f==='equip'){
        const levels=(b||[]).map(e=>e.enhance||0);short=(levels.length?'+'+Math.min(...levels):'없음')+'→+15';
        short+=' · '+[...new Set((t||[]).map(e=>view.sets?.[growth.item_sets?.[e.item_id]]).filter(Boolean))].join('·');
        detail='세트: '+[...new Set((t||[]).map(e=>view.sets?.[growth.item_sets?.[e.item_id]]).filter(Boolean))].join('·')+'\n'+(t||[]).map(e=>{const slot=view.itemSlots?.[e.item_id],prev=(b||[]).find(x=>view.itemSlots?.[x.item_id]===slot);
          return `${['무기','장갑','갑옷','신발','목걸이','반지'][slot]||'장비'} ${prev?'+'+(prev.enhance||0):'없음'}→+${e.enhance} · ${view.sets?.[growth.item_sets?.[e.item_id]]||'세트 정보 없음'}`;}).join('\n');
      }
      if(f==='journey'){
        // 기록을 통째로 다시 만드는 추천: 지금 주력 칸 → 바뀌는 주력 칸을 함께 보인다(이미 SG 인 칸을 버리는 추천일 수 있음을 알게)
        const top=x=>x&&x.some(v=>v>0)?x.indexOf(Math.max(...x)):null,mb=top(b),mt=top(t||[]);
        const g=(x,i)=>grade(x[i],i,table)||num(x[i]);
        short=mt==null?'':`(주력 ${mb==null?'없음':names[mb]+' '+g(b,mb)} → ${names[mt]} ${g(t,mt)})`;
        const down=names.filter((n,i)=>(b?.[i]||0)>t[i]);
        detail='한 번의 여정 결과로 기록 전체를 다시 만드는 목표임(칸별로 좋은 값만 섞을 수 없음).'+(down.length?`\n지금보다 내려가는 칸: ${down.join('·')}`:'')+'\n'+
          names.map((n,i)=>`${n} ${archive(b?.[i]||0,i,table)} → ${archive(t[i],i,table)}${t[i]===1250?' (MAX)':''}`).join('\n');
      }
      if(f==='potentials'){
        const changes=(t||[]).filter(p=>!(b||[]).some(q=>q[0]===p[0]&&q[1]>=p[1]));
        short=changes.map(p=>`${view.potentials?.[p[0]]?.name||''} ${(b||[]).find(q=>q[0]===p[0])?.[1]||'미습득'}→${p[1]}`).join(' · ');
        detail=changes.map(p=>`${view.potentials?.[p[0]]?.name||'잠재력 '+p[0]} ${(b||[]).find(q=>q[0]===p[0])?.[1]||'미습득'} → ${p[1]}`).join('\n');
      }
      return {field:f,label:f==='journey'?'스텔라 아카이브 기록 다시 만들기':labels[f],short,detail:detail||short,delta};
    });
    return {before,after,fields,missing:!old};
  }
  function todosHtml(m){return (m?.fields||[]).filter(f=>f.delta!==0).map(f=>`<button type="button" class="growth-todo" data-growth-field="${f.field}" data-power-delta="${f.delta??''}" data-help="${esc(f.detail+'\n전투력 '+signed(f.delta)+' · 이 항목만 목표로 올렸을 때의 증가임.')}" aria-expanded="false">${esc(f.label)} ${esc(f.short)} <small>(${signed(f.delta)})</small></button>`).join('');}
  function memberHtml(m,withTodos=true){if(!m)return '';return `<div class="growth-power" data-k="member-power">전투력 ${num(m.before)} → ${num(m.after)}</div>`+(withTodos?`<div class="growth-todos">${todosHtml(m)}</div>`:'');}
  // 스테이지형 콘텐츠(길방·코스모 밖 전부)는 확률, 시즌 콘텐츠는 점수. goalTurns>0 = 3별 목표: 확률은 «N턴 내 클리어율»(t60)로 보인다
  function resultTabState({enabled,phase,better,baseline,best,kind='op',message='',errors=[],goalTurns=0,none=''}){
    const probability=kind!=='guild'&&kind!=='cosmo',field=kind==='guild'?'score':'sum';
    const goal=r=>goalTurns&&r?.t60!=null?r.t60:r?.clear;
    const metric=r=>probability?(Number.isFinite(goal(r))?Math.round(goal(r)*100)+'%':'계산 전'):
      (Number.isFinite(r?.[field])?num(r[field])+'점':'계산 전');
    // 탐색이 끝났으면 더 나은 편성이 없어도 탭을 유지함(육성 탭 = 안내). none = 그때 탭 제목 옆 문구.
    const found=phase==='done'&&!!better;
    return {show:!!enabled&&(phase==='running'||phase==='error'||phase==='done'),
      now:(probability?(goalTurns?goalTurns+'턴 내 ':'클리어 '):'점수 ')+metric(baseline),
      growth:phase==='running'?'계산 중'+(message?' · '+message:''):phase==='error'?'미완료'+(errors.length?' · 실패':''):found?'맞추면 '+metric(best)+' ↑':none||'더 나은 편성 없음',
      recommend:(phase!=='done'||found)&&probability&&Number.isFinite(goal(baseline))&&goal(baseline)<.5,phase};
  }
  // The choice lives only in this controller. Never persist it or add it to share state.
  function createResultTabs(){
    const doc=root.document;
    let selected='now',nav=null,panels=[];
    function release(){for(const p of panels){p.classList.remove('ux-tab-hidden');p.removeAttribute('role');p.removeAttribute('aria-labelledby');p.removeAttribute('tabindex');}panels=[];}
    function reset(){release();nav?.remove();nav=null;selected='now';}
    function select(key){selected=key;
      panels.forEach((p,i)=>p.classList.toggle('ux-tab-hidden',(i===0?'now':'growth')!==selected));
      nav.querySelectorAll('[role=tab]').forEach(b=>{const active=b.dataset.resultTab===selected;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
    }
    function update(now,growth,state){
      if(!state.show||!now||!growth){reset();return;}
      if(!nav){nav=doc.createElement('div');nav.id='result-tabs';nav.className='result-tabs';nav.setAttribute('role','tablist');nav.setAttribute('aria-label','추천 결과');
        nav.innerHTML=['now','growth'].map((key,i)=>`<button type="button" role="tab" id="result-tab-${key}" data-result-tab="${key}"><span class="result-tab-title">${i?'클리어 추천 육성':'지금 내 구원자로'}</span><span class="result-tab-sep"> · </span><span data-tab-metric></span>${i?'<span class="result-recommend" hidden>추천</span>':''}</button>`).join('');
        nav.addEventListener('click',e=>{const b=e.target.closest('[role=tab]');if(b)select(b.dataset.resultTab);});
        nav.addEventListener('keydown',e=>{const b=e.target.closest('[role=tab]');if(!b||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
          e.preventDefault();const buttons=[...nav.querySelectorAll('[role=tab]')],next=e.key==='Home'?buttons[0]:e.key==='End'?buttons[1]:buttons[1-buttons.indexOf(b)];
          buttons.forEach(x=>x.tabIndex=x===next?0:-1);next.focus();});
      }
      release();panels=[now,growth];now.id||='result-now';if(nav.nextSibling!==now)now.before(nav);
      panels.forEach((p,i)=>{const key=i?'growth':'now',b=nav.querySelector(`[data-result-tab=${key}]`);
        p.setAttribute('role','tabpanel');p.setAttribute('aria-labelledby',b.id);p.tabIndex=0;b.setAttribute('aria-controls',p.id);
        b.querySelector('[data-tab-metric]').textContent=state[key];});
      nav.querySelector('.result-recommend').hidden=!state.recommend;
      const b=nav.querySelector('[data-result-tab=growth]');b.dataset.state=state.phase;
      b.querySelector('[data-tab-metric]').setAttribute('role','status');
      select(selected);
    }
    return {update,reset};
  }
  function mount(){
    const doc=root.document;if(!doc)return;
    mountGwen();mountDecodedImages();
    // 정적 HTML 에 미리 놓인 빈 말풍선(불러오기 창)은 여기서 한 번만 채움.
    doc.querySelectorAll('.gwen-bubble[data-gwen-say]:empty').forEach(el=>{el.textContent=gwenSayLine(el.dataset.gwenSay);});
    const pop=doc.createElement('div');pop.id='ux-popover';pop.className='ux-popover';pop.role='tooltip';pop.hidden=true;doc.body.append(pop);
    let owner=null,pinned=false,timer;
    function close(){clearTimeout(timer);if(owner){owner.setAttribute('aria-expanded','false');owner.removeAttribute('aria-describedby');}owner=null;pinned=false;pop.hidden=true;}
    function place(){if(!owner?.isConnected){close();return;}const r=owner.getBoundingClientRect(),vw=doc.documentElement.clientWidth,vh=root.innerHeight;
      pop.style.left=Math.max(8,Math.min(r.left,vw-pop.offsetWidth-8))+'px';
      pop.style.top=Math.max(8,Math.min(r.bottom+8,vh-pop.offsetHeight-8))+'px';}
    function show(b,pin=false){clearTimeout(timer);if(owner!==b)close();owner=b;pinned=pin;pop.textContent=b.dataset.help;pop.hidden=false;b.setAttribute('aria-expanded','true');b.setAttribute('aria-describedby',pop.id);place();}
    doc.addEventListener('click',e=>{const b=e.target.closest('[data-help]');if(b){e.preventDefault();e.stopPropagation();if(owner===b&&pinned)close();else show(b,true);}else if(!pop.contains(e.target))close();});
    doc.addEventListener('pointerover',e=>{const b=e.target.closest('[data-help]');if(e.pointerType==='mouse'&&b&&!pinned)show(b);if(pop.contains(e.target))clearTimeout(timer);});
    doc.addEventListener('pointerout',e=>{if(!pinned&&(e.target.closest('[data-help]')||pop.contains(e.target)))timer=setTimeout(close,150);});
    doc.addEventListener('keydown',e=>{if(e.key==='Escape'){const b=owner;close();b?.focus();doc.querySelectorAll('.ux-menu[open]').forEach(d=>d.open=false);}});
    doc.addEventListener('focusout',e=>{if(owner===e.target&&!pinned)close();});
    root.addEventListener('resize',()=>{if(owner)place();});root.addEventListener('scroll',()=>{if(owner)place();},true);
  }
  const api={verdict,help,gwenImage,gwenReaction,gwenIdle,gwenBest,gwenWork,gwenError,GWEN_SCENES,GWEN_CYCLES,GWEN_LINES,GWEN_SAY,gwenSay,gwenSayBand,gwenReport,gwenStage,syncGwen,grade,archive,setGrades,chip,luckNote,LUCK,signed,num,labels,member,todosHtml,memberHtml,resultTabState,createResultTabs,mount};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.Ux=api;
})(typeof globalThis!=='undefined'?globalThis:this);
