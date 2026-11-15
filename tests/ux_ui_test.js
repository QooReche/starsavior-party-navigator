const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const U=require('../ux_ui'),M=require('../myinfo_reco'),S=require('../myinfo_stats');
const growth=require('../data/growth.json'),grades=require('../data/archive_grades.json');
const view={...require('../data/myinfo_view.json'),itemSlots:require('../data/myinfo_slots.json')};
const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
function checkVerdict(u=U){for(const [p,expected] of [[0,'risk'],[.49999,'risk'],[.5,'shaky'],[.69999,'shaky'],[.7,'ok'],[.89999,'ok'],[.9,'safe'],[1,'safe']])assert.equal(u.verdict(p)[0],expected);}
function checkGrades(u=U){for(const [n,label] of [[1250,'SG'],[1150,''],[497,'A+'],[465,'A+'],[435,'A'],[373,'B+'],[367,'B+'],[181,'D+'],[148,'E+'],[66,'F']]){
  for(let i=0;i<5;i++)assert.equal(u.grade(n,i,grades),label,`grade ${n}/${i}`);
}assert.equal(u.archive(1250,0,grades),'SG 1,250','1,250(MAX) is shown as SG (user decision 11/13)');assert.equal(u.archive(1150,0,grades),'1,150','other upper glyphs stay numeric');
assert.equal(u.grade(1501,0,grades),'');}
function checkPower(u=U){const info=structuredClone(require('./fixtures/myinfo_synthetic.json'));
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  info.star_link={level:240,source:[],slots:[]};info.star_link_level=240;
  for(const x of info.units){x.level=80;x.resonance=0;x.equip=[];x.skills={basic:1,special:1,ultimate:1,passive:1};x.gauntlet.journey=[66,148,373,181,435];x.gauntlet.potentials=[];}
  const original=JSON.stringify(info),snapshot=M.overwrite(info,roster,growth,'op',{includeMissing:false});
  assert.equal(snapshot.errors.length,0);const counts={};
  for(const a of Object.values(snapshot.changes)){
    const display=u.member(a,info,growth,'op',grades,view),old=info.units.find(x=>x.id===a.unit.id);
    assert(display.after>display.before);assert.equal(display.fields.length,a.changedFields.length);
    for(const f of display.fields){counts[f.field]=(counts[f.field]||0)+1;
      const unit=structuredClone(old);let account=info;
      if(f.field==='level')account=a.targetInfo;
      else if(['journey','potentials'].includes(f.field))unit.gauntlet[f.field]=structuredClone(a.unit.gauntlet[f.field]);
      else unit[f.field]=structuredClone(a.unit[f.field]);
      const expected=S.final_stats(unit,account,growth,'normal').power-S.final_stats(old,info,growth,'normal').power;
      assert.equal(f.delta,expected,f.field);assert(f.field==='skills'?f.short==='3종':f.short.includes('→'),f.field);assert(f.detail.length>0);
      assert.equal(u.memberHtml(display).includes(`data-growth-field="${f.field}"`),f.delta!==0);
    }
  }
  for(const f of Object.keys(U.labels))assert(counts[f]>0,`path not exercised: ${f}`);
  assert.equal(JSON.stringify(info),original);
  // Fixed-level content must not report a fictitious benefit for registration.
  const a=Object.values(snapshot.changes).find(a=>a.changedFields.includes('level'));
  const fixed=u.member(a,info,growth,'cosmo',grades,view);
  assert(!fixed.fields.some(f=>['level','resonance'].includes(f.field)));
  assert(!u.memberHtml(fixed).includes('data-growth-field="level"'));
  const missing=M.overwrite(info,roster,growth,'op',{includeMissing:true});
  assert(!Object.values(missing.changes).some(a=>a.source==='assumed'));
  const ma=M.assume('hilde',{...info,units:[]},growth),md=u.member(ma,{...info,units:[]},growth,'op',grades,view);
  assert.equal(md,null);assert.equal(u.memberHtml(md),'');assert.equal(u.todosHtml(md),'');
}
function checkChips(u=U){
  const fields=Object.entries(u.labels).map(([field,label],i)=>({field,label,short:'길고 복잡한 상세 → 목표',detail:'상세 정보',delta:i===3?0:100+i}));
  const m={before:100,after:200,fields,missing:false},html=u.todosHtml(m);
  assert.equal((html.match(/<button /g)||[]).length,6);
  assert(!html.includes('data-growth-field="resonance"'));
  assert.equal((html.match(/길고 복잡한/g)||[]).length,6,'every changed target belongs in compact chips');
  assert(html.includes('스타링크 길고 복잡한 상세 → 목표 <small>(+100)</small>'));
  assert(html.includes('장비 길고 복잡한 상세 → 목표 <small>(+101)</small>'));
  assert(!u.memberHtml(m,false).includes('<button'));
  assert.equal(u.todosHtml({...m,fields:[{...fields[0],delta:0}]}),'');
  assert.match(u.todosHtml({...m,fields:[{...fields[0],delta:null}],missing:true}),/자료 없음/);
  assert.match(u.todosHtml({...m,fields:[{...fields[0],delta:-20}]}),/−20/);
}
function checkSkills(u=U){
  const info=structuredClone(require('./fixtures/myinfo_synthetic.json'));
  const old=info.units[0];old.skills={basic:6,special:10,ultimate:1,passive:10};
  const target=structuredClone(old);target.skills={basic:10,special:10,ultimate:10,passive:10};
  function inspect(expected){
    const a={unit:target,changedFields:['skills'],changes:{skills:{before:old.skills,after:target.skills}}};
    const m=u.member(a,info,growth,'op',grades,view),f=m.fields[0];
    assert.equal(f.short,expected);assert(f.delta>0);
    assert.equal(f.detail.split('\n').length,3);
    for(const [key,label] of Object.entries({basic:'기본',special:'특수',ultimate:'궁'}))assert(f.detail.includes(`${label} ${old.skills[key]}→10`));
    assert(!f.detail.includes('패시브'));
    assert(u.todosHtml(m).includes(`>스킬 ${expected} <small>(+${u.num(f.delta)})</small>`));
  }
  inspect('기본 6→10 · 궁 1→10');
  old.skills.ultimate=10;inspect('기본 6→10');
  old.skills.special=1;old.skills.ultimate=1;inspect('3종');
  old.skills.passive=1;target.skills.passive=1;inspect('3종');
}
function checkTabState(u=U){
  const base={enabled:true,phase:'done',better:true,baseline:{clear:.4},best:{clear:.8}};
  const s=u.resultTabState(base);assert(s.show&&s.recommend);assert.equal(s.now,'클리어 40%');assert.equal(s.growth,'맞추면 80% ↑');
  for(const clear of [0,.4999,.5,1])assert.equal(u.resultTabState({...base,baseline:{clear}}).recommend,clear<.5);
  assert(!u.resultTabState({...base,baseline:null}).recommend);
  for(const changes of [{enabled:false},{better:false},{phase:'idle'}])assert(!u.resultTabState({...base,...changes}).show);
  const running=u.resultTabState({...base,phase:'running',better:false,message:'후보 확인 2/10'});
  assert(running.show);assert.equal(running.growth,'계산 중 · 후보 확인 2/10');
  const error=u.resultTabState({...base,phase:'error',better:false,errors:['worker failed']});
  assert(error.show);assert.equal(error.growth,'미완료 · 실패');
  for(const kind of ['guild','cosmo']){const state=u.resultTabState({...base,kind,baseline:{score:100,sum:100},best:{score:200,sum:200}});
    assert.equal(state.now,'점수 100점');assert.equal(state.growth,'맞추면 200점 ↑');assert(!state.recommend);}
}
// 운에 크게 좌우되는 결과 안내(luckNote): 성간 회랑 485 사례(0.5%, 구간 0.2~1.2%)는 뜨고, 보통 결과·정보 없는 결과는 안 뜬다
function checkLuck(u=U){
  const on=r=>u.luckNote(r).includes('data-k="luck-note"'),text=r=>u.luckNote(r).replace(/<[^>]*>/g,'');
  const case485={clear:.005,ci:[.002,.012],n:2000};
  assert(on(case485));assert.match(text(case485),/약 0\.5%/);assert.match(text(case485),/30번 도전해도 한 번이라도 깰 확률은 약 14%/);
  assert.match(text(case485),/파티 변경이나 추가 육성 권장/);
  assert.equal(Math.round((1-Math.pow(1-.005,30))*1000)/10,14,'1-(1-p)^30');
  // 기준 경계: 5% 미만만 «낮음», 구간은 하한 1% 미만 + 상한 5% 이상일 때만 «흔들림»
  assert(on({clear:.0499,ci:[.04,.06],n:2000}));assert(!on({clear:.05,ci:[.04,.06],n:2000}));
  assert(on({clear:.05,ci:[.009,.236],n:20}));assert.match(text({clear:.05,ci:[.009,.236],n:20}),/결과가 흔들림\(약 5%, 범위 0\.9%~24%\)/);
  assert(!on({clear:.05,ci:[.01,.236],n:20}));assert(!on({clear:.05,ci:[.009,.0499],n:20}));
  assert(!on({clear:.125,ci:[.022,.47],n:8}),'하한 1% 이상이면 표본이 적어도 안 띄움');
  // 0판 클리어: 확률 대신 «한 번도 못 깼음», 30번 문구 없음
  const zero={clear:0,ci:[0,.037],n:100};assert(on(zero));assert.match(text(zero),/모의 전투 100판에서 한 번도 못 깼음/);assert.doesNotMatch(text(zero),/30번/);
  for(const r of [{clear:.96,ci:[.91,.99],n:100},{clear:.5,ci:[.4,.6],n:100},{clear:.2,n:8},null,undefined,{},{clear:null}])assert.equal(u.luckNote(r),'',JSON.stringify(r));
  assert(on({clear:.03}),'구간이 없어도 클리어율로 판단');
}
function load(code){const c={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,c);return c.module.exports;}
function checkGwenWork(u=U){
  for(const mode of ['inspect','screen','long','error','report','welcome']){
    const html=u.gwenWork(mode);assert.match(html,new RegExp(`data-gwen="${mode}"`));
    assert.match(html,/width="160" height="160" alt=""/);assert.match(html,/aria-hidden="true"/);
    const art={inspect:'investigate',screen:'files',long:'walk',error:'surprised',report:'report',welcome:'welcome'}[mode];
    assert(html.includes(`assets/ui_icons/gwen/${art}.png`));
    assert(html.includes(`${art}.webp`));assert.match(html,/loading="lazy"/);assert.doesNotMatch(html,/\ssrc=/);
  }
  assert.match(u.gwenWork('inspect'),/그웬이 추천 편성 확인 중…/);
  assert.match(u.gwenWork('screen'),/그웬이 후보 거르는 중…/);
  // 탐정 말투 한 줄: 단계마다 3종, 짧은 체(「…중…」), 휴대폰 한 줄에 들어갈 길이. 오류에는 문구를 붙이지 않음(오류 글이 주인공).
  for(const mode of ['inspect','screen','long']){assert.equal(u.GWEN_LINES[mode].length,3,mode);
    for(const line of u.GWEN_LINES[mode]){assert.match(line,/중…$/,line);assert(line.length<=18,line);}
    assert(u.gwenWork(mode).includes(`<span class="gwen-caption">${u.GWEN_LINES[mode][0]}</span>`),mode);}
  assert.match(u.gwenWork('report'),/<span class="gwen-caption">조사 끝 · 보고함<\/span>/);
  assert.doesNotMatch(u.gwenWork('error'),/gwen-caption/);
  // 낮은 클리어율 안내 머리: 그웬 얼굴(장식) + 「그웬의 메모」, 본문 뜻은 그대로.
  {const note=u.luckNote({clear:.005,n:1000,ci:[.002,.012]});
   assert.match(note,/^<div class="luck-note" data-k="luck-note" role="note"><span class="gwen-memo"><img src="assets\/ui_icons\/gwen_header_72\.png" width="20" height="20" alt="" aria-hidden="true">그웬의 메모<\/span>클리어 확률 매우 낮음/);
   assert.equal((note.match(/<img/g)||[]).length,1);}
  for(const mode of ['idle','done','cancelled',''])assert.equal(u.gwenWork(mode),'');
  for(const msg of ['후보 거르는 중 3/80','1단계: 조합 훑어보는 중','2단계: 상위 팀 확인 중'])assert.equal(u.gwenStage(msg),'screen');
  for(const msg of ['작업 준비 중','내 구원자 능력치 계산 중'])assert.equal(u.gwenStage(msg),'inspect');
  for(const msg of ['3단계: 상위 팀 확인 중','육성 계획 탐색','난이도 비교'])assert.equal(u.gwenStage(msg),'long');
  const old={dataset:{gwen:'screen'},outerHTML:'unchanged'},parent={querySelector:()=>old};
  u.syncGwen(parent,'screen');assert.equal(old.outerHTML,'unchanged');
  u.syncGwen(parent,'long');assert.match(old.outerHTML,/data-gwen="long"/);
  u.syncGwen(parent,'done');assert.equal(old.outerHTML,'');
}
// 그웬 말풍선: 대사 표 한곳, 상황별 2~4개·한 줄(30자 이내)·반말, 방문당 하나 고정, 장식이라 aria-hidden.
function checkGwenSay(u=U){
  const keys=['inspect','screen','long','report','error','high','shaky','hard','low','welcome','import','empty'];
  assert.deepEqual(Object.keys(u.GWEN_SAY),keys);
  for(const key of keys){const lines=u.GWEN_SAY[key];
    assert(lines.length>=2&&lines.length<=4,key);assert.equal(new Set(lines).size,lines.length,key);
    for(const line of lines){assert([...line].length<=30,line);assert.doesNotMatch(line,/\n|[<>&"]/,line);
      assert.doesNotMatch(line,/(음|함|됨|임|니다|세요|어요|아요|해요)[.!?…]*$/,`안내 문구체·존댓말 아님: ${line}`);
      assert.doesNotMatch(line,/\d|%/,`숫자·진행률은 말풍선에 넣지 않음: ${line}`);}
    const html=u.gwenSay(key);
    assert.equal(html,`<span class="gwen-bubble" data-gwen-say="${key}" data-tail="down" aria-hidden="true">${lines[0]}</span>`);
    assert.equal(u.gwenSay(key),html,'다시 그려도 같은 대사');}
  assert.match(u.gwenSay('welcome','right'),/data-tail="right"/);
  for(const key of ['','none','toString','constructor',undefined])assert.equal(u.gwenSay(key),'',String(key));
  assert.equal(u.GWEN_SAY.error[0],'으… 단서가 부족해');assert.equal(u.GWEN_SAY.welcome[0],'어서 와, 단장! 어떤 사건이야?');
  assert.equal(u.GWEN_SAY.import[0],'단장 정보, 내가 받아 갈게');
  // 진행·실패·보고 연출: 그림 트랙 앞에 말풍선 한 개, 기존 안내 문구(caption)는 그대로.
  for(const mode of ['inspect','screen','long','error','report','welcome']){const html=u.gwenWork(mode);
    assert.equal((html.match(/class="gwen-bubble"/g)||[]).length,1,mode);
    assert(html.includes(`<span class="gwen-say-lane">${u.gwenSay(mode)}</span><span class="gwen-track">`),mode);}
  assert.match(u.gwenWork('inspect'),/<span class="gwen-caption">그웬이 추천 편성 확인 중…<\/span>/);
  assert(u.gwenWork('screen','empty').includes(u.gwenSay('empty')));assert.match(u.gwenWork('screen','empty'),/data-gwen="screen"/);
  assert.doesNotMatch(u.gwenWork('screen',null),/gwen-bubble/);
  // Array.map 같은 호출로 숫자가 둘째 인자로 와도 엉뚱한 대사를 내지 않음.
  assert.doesNotMatch(['screen'].map(u.gwenWork)[0],/gwen-bubble/);
  // 결과 발표: 판정 칩과 같은 경계(70%·50%)와 매우 낮음(5% 미만).
  for(const [p,band] of [[1,'high'],[.7,'high'],[.6999,'shaky'],[.5,'shaky'],[.4999,'hard'],[.05,'hard'],[.0499,'low'],[0,'low']]){
    assert.equal(u.gwenSayBand(p),band,String(p));
    assert(u.gwenReaction(p).includes(`<div class="gwen-bubble-space">${u.gwenSay(band)}</div>`),String(p));}
  for(const p of [NaN,undefined,null])assert.equal(u.gwenSayBand(p),'');
  assert.match(u.gwenReaction(.95),/^<div class="gwen-reaction" data-gwen-reaction="confident" aria-hidden="true">/);
  assert.match(u.GWEN_SAY.high[0],/사건 해결/);assert.match(u.GWEN_SAY.shaky[0],/아슬아슬/);assert.match(u.GWEN_SAY.low[0],/육성부터/);
}
// 방문당 하나 고정: 브라우저에서는 처음 한 번만 고르고, 불러오기 창의 빈 말풍선은 mount 가 한 번 채움.
function checkGwenSayVisit(code=source){
  const filled=[],randoms=[.25,.9,.1,.7];let calls=0;
  const el={dataset:{gwenSay:'import'},textContent:''};
  const doc={hidden:false,body:{append(){}},documentElement:{classList:{toggle(){}},clientWidth:1280},addEventListener(){},
    createElement:()=>({}),querySelectorAll:q=>q==='.gwen-bubble[data-gwen-say]:empty'?(filled.push(q),[el]):[]};
  const c={module:undefined,document:doc,UiShared:require('../ui_shared'),MyInfoStats:S,innerHeight:900,innerWidth:1280,
    Math:Object.assign(Object.create(Math),{random:()=>{calls++;return randoms[(calls-1)%randoms.length];}}),
    matchMedia:()=>({matches:false,addEventListener(){}}),addEventListener(){},setTimeout,clearTimeout,
    IntersectionObserver:class{observe(){}unobserve(){}},MutationObserver:class{observe(){}}};
  c.globalThis=c;vm.runInNewContext(code,c);const u=c.Ux;
  const first=u.gwenSay('inspect');assert(u.GWEN_SAY.inspect.some(line=>first.includes('>'+line+'<')));
  assert.notEqual(first,U.gwenSay('inspect'),'방문마다 고른 대사(시험용 난수 .25 → 둘째 대사)');
  for(let i=0;i<5;i++){assert.equal(u.gwenSay('inspect'),first,'다시 그려도 대사 유지');assert.equal(u.gwenWork('long'),u.gwenWork('long'));}
  assert.equal(calls,1,'난수는 방문당 한 번');
  u.mount();assert.equal(filled.length,1);assert(u.GWEN_SAY.import.includes(el.textContent),'불러오기 창 말풍선 채움');
}
const source=fs.readFileSync(require.resolve('../ux_ui'),'utf8');
function mutation(from,to,check){assert(source.includes(from));let caught=false;try{check(load(source.replace(from,to)));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}assert(caught,`mutation survived: ${from}`);check(U);}
checkVerdict();checkGrades();checkPower();checkChips();checkSkills();checkTabState();checkLuck();
checkGwenWork();
checkGwenSay();checkGwenSayVisit();
{const r={},first=U.gwenReport(r);assert.match(first,/data-gwen="report"/);assert.equal(U.gwenReport(r),first,'not consumed before visible mount');assert.equal(U.gwenReport(null),'');}
mutation("if(!art)return '';","return '';",checkGwenWork);
mutation("error:'surprised'","error:'welcome'",checkGwenWork);
mutation("?'screen':/준비|능력치 계산/","?'long':/준비|능력치 계산/",checkGwenWork);
mutation("old.outerHTML=gwenWork(mode)","old.outerHTML=old.outerHTML",checkGwenWork);
mutation("p>=.7?'high'","p>.7?'high'",checkGwenSay);
mutation("p>=.5?'shaky'","p>=.4?'shaky'",checkGwenSay);
mutation("p>=.05?'hard':'low'","p>=.05?'hard':'hard'",checkGwenSay);
mutation('<div class="gwen-bubble-space">${gwenSay(gwenSayBand(p))}</div>','<div class="gwen-bubble-space"></div>',checkGwenSay);
mutation('<span class="gwen-say-lane">${gwenSay(say)}</span>','',checkGwenSay);
mutation('data-tail="${esc(tail)}" aria-hidden="true">','data-tail="${esc(tail)}">',checkGwenSay);
mutation("function gwenWork(mode,say=mode){","function gwenWork(mode,say='inspect'){",checkGwenSay);
mutation("'으… 단서가 부족해'","'단서가 부족함'",checkGwenSay);
mutation("'어서 와, 단장! 어떤 사건이야?'","'어서 오세요, 단장! 오늘은 어떤 사건을 맡기러 오셨나요?'",checkGwenSay);
{const visit=(from,to)=>{assert(source.includes(from));assert.throws(()=>checkGwenSayVisit(source.replace(from,to)),{code:'ERR_ASSERTION'},`mutation survived: ${from}`);};
 visit("return lines?lines[gwenSeed%lines.length]:'';};\n  // 클리어율","return lines?lines[Math.floor(Math.random()*lines.length)]:'';};\n  // 클리어율");
 visit("el.textContent=gwenSayLine(el.dataset.gwenSay);","");}
mutation('p>=.9','p>.9',checkVerdict);
mutation('value>=r[0]','value>r[0]+50',checkGrades);
mutation('delta=S.final_stats(unit,account,growth,rule).power-before;','delta=after-before;',checkPower);
mutation('a.changedFields.filter(f=>','a.changedFields.filter(f=>f!=="equip").filter(f=>',checkPower);
mutation('f.delta!==0','true',checkChips);
mutation("${esc(f.short)}", "", checkChips);
mutation("changed.length<=2","changed.length<2",checkSkills);
mutation("changed.map(line).join(' · ')","changed.slice(-1).map(line).join(' · ')",checkSkills);
mutation("Object.keys(skillNames).map(line)","changed.map(line)",checkSkills);
mutation("goal(baseline)<.5","goal(baseline)<=.5",checkTabState);
mutation("&&!!better","",checkTabState);
mutation("!!enabled&&","",checkTabState);
mutation("phase==='running'||phase==='error'||","",checkTabState);
mutation("const low=p<LUCK.low","const low=p<=LUCK.low",checkLuck);
mutation("ci[0]<LUCK.ciLo&&ci[1]>=LUCK.ciHi","ci[0]<LUCK.ciLo",checkLuck);
mutation("if(!low&&!shaky)return '';","",checkLuck);
mutation("1-Math.pow(1-p,LUCK.tries)","p*LUCK.tries",checkLuck);
console.log('PASS probability, grades, power, skill targets, tab states, luck note, Gwen modes and transitions, Gwen speech bubbles; 32 mutations caught');
