// 코스모 직접 편성 화면 부품(cosmo_direct_ui.js) — 브라우저 없이 render 결과 DOM 을 검사한다. node tests/cosmo_direct_ui_test.js
// 로직 모듈(cosmo_direct.js)은 쓰지 않고 계약(view·콜백) 모양의 가짜 view 를 직접 만든다.
// 끝에 변이 검사: 부품 코드를 한 군데씩 망가뜨린 사본으로 같은 시험을 돌려 전부 실패하는지 본다(--no-mutations 로 생략).
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const SRC=fs.readFileSync(path.join(__dirname,'..','cosmo_direct_ui.js'),'utf8');

// ── 시험용 작은 DOM: 부품이 쓰는 것(innerHTML·querySelector·closest·속성·이벤트 등록)만 흉내 ──
const VOID=new Set(['img','input','br','hr','path','rect']);
const decode=s=>s.replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
class El{
  constructor(tag,attrs={}){this.tag=tag;this.attrs=attrs;this.children=[];this.parent=null;this.text='';this.handlers={};this.focused=0;}
  getAttribute(n){return n in this.attrs?this.attrs[n]:null;}
  setAttribute(n,v){this.attrs[n]=String(v);}
  removeAttribute(n){delete this.attrs[n];}
  hasAttribute(n){return n in this.attrs;}
  get id(){return this.attrs.id||'';}
  get disabled(){return 'disabled' in this.attrs;}
  get hidden(){return 'hidden' in this.attrs;}
  get className(){return this.attrs.class||'';}
  get textContent(){return this.children.map(c=>typeof c==='string'?c:c.textContent).join('');}
  set innerHTML(html){this.children=[];parse(html,this);}
  addEventListener(type,fn){(this.handlers[type]=this.handlers[type]||[]).push(fn);}
  focus(){this.focused++;El.lastFocus=this;}
  contains(x){for(let n=x;n;n=n.parent)if(n===this)return true;return false;}
  closest(sel){for(let n=this;n;n=n.parent)if(n instanceof El&&matches(n,sel))return n;return null;}
  all(){const out=[];(function walk(n){for(const c of n.children)if(c instanceof El){out.push(c);walk(c);}})(this);return out;}
  querySelectorAll(sel){return this.all().filter(n=>matches(n,sel));}
  querySelector(sel){return this.querySelectorAll(sel)[0]||null;}
}
function parse(html,into){
  const re=/<!--[\s\S]*?-->|<\/([a-zA-Z0-9]+)>|<([a-zA-Z0-9]+)((?:\s+[^\s=>\/]+(?:="[^"]*")?)*)\s*\/?>|([^<]+)/g;let cur=into,m;
  while((m=re.exec(html))){
    if(m[1]){assert.equal(cur.tag,m[1],`닫는 태그 짝이 안 맞음: </${m[1]}> (열린 것 <${cur.tag}>)`);cur=cur.parent;}
    else if(m[2]){const attrs={};for(const a of m[3].matchAll(/([^\s=]+)(?:="([^"]*)")?/g))attrs[a[1]]=decode(a[2]??'');
      const el=new El(m[2],attrs);el.parent=cur;cur.children.push(el);if(!VOID.has(m[2])&&!m[0].endsWith('/>'))cur=el;}
    else if(m[4])cur.children.push(decode(m[4]));
  }
  assert.equal(cur,into,'안 닫힌 태그가 남음');
}
// 선택자: 태그·.class·#id·[속성]·[속성=값] 을 붙여 쓴 것과 자손(빈칸) 결합
function simple(n,sel){
  const parts=sel.match(/^[a-zA-Z0-9]+|#[\w-]+|\.[\w-]+|\[[^\]]+\]/g);assert(parts&&parts.join('')===sel,'시험 DOM 이 모르는 선택자: '+sel);
  return parts.every(p=>p[0]==='#'?n.id===p.slice(1):p[0]==='.'?n.className.split(/\s+/).includes(p.slice(1))
    :p[0]==='['?(([,k,v])=>v===undefined?n.hasAttribute(k):n.getAttribute(k)===v.replace(/^"|"$/g,''))(/^\[([^=\]]+)(?:=(.*))?\]$/.exec(p)):n.tag===p);
}
function matches(n,sel){
  const chain=sel.trim().split(/\s+/);if(!simple(n,chain[chain.length-1]))return false;
  let i=chain.length-2;for(let p=n.parent;p&&i>=0;p=p.parent)if(p instanceof El&&simple(p,chain[i]))i--;
  return i<0;
}
const fire=(host,type,target,extra={})=>{const e={target,prevented:false,preventDefault(){this.prevented=true;},...extra};for(const fn of host.handlers[type]||[])fn(e);return e;};

// ── 계약 모양의 가짜 view ──
const season={id:23,levelMax:18,bosses:[{key:'mogulus',name:'불사왕 모굴루스',element:'chaos',sim:true},{key:'baskerville',name:'바스커빌의 괴수',element:'order',sim:true},{key:'disparity',name:'괴리의 표상',element:'order',sim:true}]};
const names={asherah:'아세라',smile:'스마일',luna:'루나',carnelia:'카넬리아',cristelle:'크리스텔',carmen:'카르멘',emily:'에밀리',frey:'프레이',lugh:'루그',hilde:'힐데'};
const roster=Object.entries(names).map(([key,name],i)=>({key,name,el:['moon','star','order','chaos','sun'][i%5],cls:['스트라이커','레인저','캐스터','디펜더'][i%4],img:`assets/savior/${key}_face.webp`}));
const draft=(keys,leader,brk=null)=>({v:1,slots:keys.map(k=>k?{key:k,grown:false}:null),leader,brk});   // 엔진 순서(전열1·전열2·후열1·후열2)
function fixture(over={}){
  const state={v:1,seasonId:23,active:'baskerville',teams:{
    mogulus:{level:12,draft:draft(['smile','luna','asherah','carnelia'],'asherah',{name:'스타피어서',level:10})},
    baskerville:{level:10,draft:draft(['carmen','emily','cristelle','frey'],'carmen')},
    disparity:{level:9,draft:draft([null,null,null,null],null)}},...over.state};
  const usedBy=new Map();for(const [b,t] of Object.entries(state.teams))for(const s of t.draft.slots)if(s)usedBy.set(s.key,b);
  const count=k=>state.teams[k].draft.slots.filter(Boolean).length;
  const teams=Object.fromEntries(season.bosses.map(b=>[b.key,count(b.key)===4?{ok:true,errors:[]}:{ok:false,errors:[{code:'count',message:`4명 미만 · ${count(b.key)}/4명 편성 중`}]}]));
  return {state,season,roster,usedBy,running:false,step:2,validation:{ok:Object.values(teams).every(t=>t.ok),teams,errors:[]},
    summary:{teams:{mogulus:{status:'done',score:1182400,clear:.82},baskerville:{status:'ready'},disparity:{status:'empty'}},total:null,done:1,need:2},
    breaks:[{name:'스타피어서',level:10},{name:'차원 강습',level:8}],...over.view};
}
function mount(U,view){
  const host=new El('section'),calls=[];
  const h={onTeam:b=>calls.push(['team',b]),onLevel:(b,l)=>calls.push(['level',b,l]),onLevelAll:l=>calls.push(['levelAll',l]),onDraft:(b,a)=>calls.push(['draft',b,a]),
    onRunTeam:b=>calls.push(['runTeam',b]),onRunAll:()=>calls.push(['runAll']),onPickerJump:b=>calls.push(['jump',b]),onArrange:b=>calls.push(['arrange',b]),onUndo:b=>calls.push(['undo',b])};
  U.render(host,view,h);
  return {host,calls,h,q:s=>host.querySelector(s),qa:s=>host.querySelectorAll(s),click:s=>{const el=typeof s==='string'?host.querySelector(s):s;assert(el,'누를 것이 없음: '+s);return fire(host,'click',el);}};
}
const cand=(t,key)=>t.qa('.direct-candidate').find(b=>b.getAttribute('data-key')===key);

function suite(U){
  // 1. 빈 팀 안내: 카드에 «비어 있음 · 눌러서 편성»·«4명 필요», 보드 네 칸에 «구원자 넣기», 결과 칸은 숨김
  {
    const t=mount(U,fixture({state:{active:'disparity'}}));
    const tab=t.q('#cd-tab-disparity');
    assert.match(tab.textContent,/비어 있음 · 눌러서 편성/);assert.match(tab.textContent,/0\/4 · 4명 필요/);
    assert(tab.querySelector('.cg-face .vacant'),'빈 팀 카드에는 초상 대신 빈 자리');
    assert.match(tab.getAttribute('aria-label'),/괴리의 표상 팀 · 편성 0\/4 · 4명 필요/);
    const vac=t.qa('.cd-board .direct-vacant');assert.equal(vac.length,4);
    for(const b of vac){assert.match(b.textContent,/구원자 넣기/);assert.match(b.getAttribute('aria-label'),/빈 칸 · 구원자 넣기/);}
    assert.equal(t.qa('.cd-board .direct-grow').filter(b=>b.disabled).length,4,'빈 칸의 «육성했다면» 은 못 누름');
    assert(t.q('[data-cd-result]').hidden,'결과 전에는 결과 칸을 숨김');
    const str=new El('div');str.innerHTML=U.html(fixture({state:{active:'disparity'}}));
    assert(str.querySelector('[data-cd-result]').hidden,'문자열만 쓸 때(html)도 결과 칸은 숨김');
    assert(t.q('[data-cd-lane-slot]')&&t.q('[data-cd-gwen-slot]'),'그웬 자리 두 곳');
    assert.equal(t.q('[data-cd-lane-slot]').children.length,0,'레인 자리는 빈 자리만');
    assert.match(t.q('.cg-total-num').textContent,/미완료 · 1\/3/);
  }
  // 2. 중복: 다른 팀 구원자는 «○○ 팀 사용 중» + aria-disabled, 누르면 넣지 않고 그 팀 탭으로. 이 팀 구원자는 «편성됨»(disabled)
  {
    const t=mount(U,fixture({state:{active:'disparity'}}));
    const used=cand(t,'carmen');
    assert.match(used.textContent,/바스커빌 팀 사용 중/);assert.equal(used.getAttribute('aria-disabled'),'true');
    assert(!used.disabled,'누르면 그 팀으로 가야 하므로 disabled 가 아니라 aria-disabled');
    assert.match(used.getAttribute('aria-label'),/카르멘 · 바스커빌 팀 사용 중이라 넣을 수 없음/);
    assert.equal(t.qa('.direct-candidate.cg-used').length,8);
    t.click(used);assert.deepEqual(t.calls,[['jump','baskerville']],'사용 중 구원자를 누르면 put 없이 onPickerJump 만');
    const free=cand(t,'lugh');assert.equal(free.getAttribute('aria-disabled'),null);
    t.calls.length=0;t.click(free);assert.deepEqual(t.calls,[['draft','disparity',{type:'put',key:'lugh',slot:null}]]);
    const mine=mount(U,fixture());const inTeam=cand(mine,'carmen');
    assert.match(inTeam.textContent,/편성됨/);assert(inTeam.disabled);
    mine.click(inTeam);assert.deepEqual(mine.calls,[]);
    // 목록 순서: 이 팀 → 다른 팀 → 나머지
    const order=mine.qa('.direct-candidate').map(b=>b.className.includes('cg-in')?0:b.className.includes('cg-used')?1:2);
    assert.deepEqual(order,[...order].sort(),'편성된 구원자가 먼저');
    // usedBy 를 객체로 줘도 같음
    const v=fixture({state:{active:'disparity'}});v.usedBy=Object.fromEntries(v.usedBy);
    assert.match(cand(mount(U,v),'asherah').textContent,/모굴루스 팀 사용 중/);
  }
  // 3. 비활성 확인 단추 + 이유(aria-describedby)
  {
    const t=mount(U,fixture());const one=t.q('#cd-run-one'),all=t.q('#cd-run-all'),reason=t.q('#cd-reason');
    assert.equal(one.getAttribute('aria-disabled'),'false');assert.equal(all.getAttribute('aria-disabled'),'true');
    assert(!all.disabled,'흐리게만 하고 초점은 받음');
    for(const b of [one,all])assert.equal(b.getAttribute('aria-describedby'),'cd-reason');
    assert.equal(reason.id,'cd-reason');assert(!reason.hidden);assert.equal(reason.getAttribute('role'),'status');
    assert.equal(reason.textContent,'«3팀 모두 확인»은 괴리 팀 4명을 채운 뒤 가능');
    t.click(all);assert.deepEqual(t.calls,[],'비활성 단추는 콜백을 부르지 않음');
    t.click(one);assert.deepEqual(t.calls,[['runTeam','baskerville']]);
    // 검증 결과(validation)가 아직 없어도 인원만으로 막음
    const nv=mount(U,{...fixture(),validation:undefined});
    assert.equal(nv.q('#cd-run-all').getAttribute('aria-disabled'),'true');assert.equal(nv.q('#cd-run-one').getAttribute('aria-disabled'),'false');
    nv.click('#cd-run-all');assert.deepEqual(nv.calls,[]);
    const e=mount(U,fixture({state:{active:'disparity'}}));
    assert.equal(e.q('#cd-run-one').getAttribute('aria-disabled'),'true');
    assert.equal(e.q('#cd-reason').textContent,'이 팀에 4명을 더 넣으면 확인 가능');
    e.click('#cd-run-one');e.click('#cd-run-all');assert.deepEqual(e.calls,[]);
    // 4명이어도 검증 실패(팀 간 중복 등)면 그 메시지가 이유
    const bad=fixture({state:{teams:{mogulus:{level:12,draft:draft(['smile','luna','asherah','carnelia'],'asherah')},baskerville:{level:10,draft:draft(['carmen','emily','cristelle','frey'],'carmen')},
      disparity:{level:9,draft:draft(['lugh','hilde','smile','luna'],'lugh')}},active:'disparity'}});
    bad.validation.teams.disparity={ok:false,errors:[{code:'cross_dup',slot:2,message:'다른 팀에서 사용 중'}]};bad.validation.ok=false;
    const b=mount(U,bad);
    assert.equal(b.q('#cd-run-one').getAttribute('aria-disabled'),'true');assert.match(b.q('#cd-reason').textContent,/다른 팀에서 사용 중/);
    assert.match(b.q('.cd-board [data-cd-slot="2"]').textContent,/다른 팀에서 사용 중/,'칸에도 같은 이유');
    assert.match(b.q('#cd-tab-disparity').textContent,/고칠 곳 있음/);
    // 3팀 다 되면 이유 없음, 둘 다 누를 수 있음. 돌리는 중이면 둘 다 막음
    const full=fixture({state:{teams:{mogulus:{level:12,draft:draft(['smile','luna','asherah','carnelia'],'asherah')},baskerville:{level:10,draft:draft(['carmen','emily','cristelle','frey'],'carmen')},
      disparity:{level:9,draft:draft(['lugh','hilde',null,null],'lugh')}}}});
    full.state.teams.disparity.draft=draft(['lugh','hilde','x1','x2'],'lugh');full.validation={ok:true,teams:{},errors:[]};
    const f=mount(U,full);assert(f.q('#cd-reason').hidden);f.click('#cd-run-all');assert.deepEqual(f.calls,[['runAll']]);
    const r=mount(U,{...full,running:true});assert.equal(r.q('#cd-run-all').getAttribute('aria-disabled'),'true');assert(!r.q('#cd-reason').hidden);
    r.click('#cd-run-all');r.click('#cd-run-one');assert.deepEqual(r.calls,[]);
  }
  // 4. 탭: role·aria-selected·roving tabindex·panel 연결, 누르기·방향키(←→·Home·End) → onTeam
  {
    const t=mount(U,fixture());const list=t.q('[role=tablist]'),tabs=t.qa('[role=tab]'),panel=t.q('[role=tabpanel]');
    assert(list);assert.equal(tabs.length,3);assert(tabs.every(x=>x.parent===list&&x.tag==='button'));
    assert.deepEqual(tabs.map(x=>x.getAttribute('aria-selected')),['false','true','false']);
    assert.deepEqual(tabs.map(x=>x.getAttribute('tabindex')),['-1','0','-1']);
    assert(tabs.every(x=>x.getAttribute('aria-controls')===panel.id));assert.equal(panel.getAttribute('aria-labelledby'),'cd-tab-baskerville');
    assert(t.host.handlers.keydown?.length===1&&t.host.handlers.click?.length===1,'핸들러 연결');
    const key=(k,from=tabs[1])=>{t.calls.length=0;const e=fire(t.host,'keydown',from,{key:k});return [t.calls.slice(),e.prevented];};
    assert.deepEqual(key('ArrowRight'),[[['team','disparity']],true]);
    assert.deepEqual(key('ArrowLeft'),[[['team','mogulus']],true]);
    assert.deepEqual(key('Home'),[[['team','mogulus']],true]);assert.deepEqual(key('End'),[[['team','disparity']],true]);
    assert.deepEqual(key('a'),[[],false],'다른 글쇠는 건드리지 않음');
    assert.deepEqual(key('ArrowRight',t.q('#cd-level')),[[],false],'탭 밖에서 누른 방향키는 탭을 바꾸지 않음');
    t.calls.length=0;t.click(tabs[2].querySelector('.cg-count'));assert.deepEqual(t.calls,[['team','disparity']],'카드 안 어디를 눌러도');
    // 고른 팀이 바뀐 view 로 다시 그리면 탭·패널·보드가 따라가고 초점이 새 탭으로
    const v=fixture({state:{active:'disparity'}});U.render(t.host,v,t.h);
    assert.equal(t.q('#cd-tab-disparity').getAttribute('aria-selected'),'true');assert.equal(panel.getAttribute('aria-labelledby'),'cd-tab-disparity');
    assert.equal(El.lastFocus?.id,'cd-tab-disparity');assert.equal(t.qa('.cd-board .direct-vacant').length,4);
    // 순환: 마지막에서 → 는 처음
    t.calls.length=0;fire(t.host,'keydown',t.q('#cd-tab-disparity'),{key:'ArrowRight'});assert.deepEqual(t.calls,[['team','mogulus']]);
  }
  // 5. 문서 순서(= 좁은 화면 순서): 카드 → 합계(말풍선 → 그웬 결과 자리) → 레인 자리 → 보드 → 고르기 → 브레이크·난이도 → 확인 → 결과
  {
    const t=mount(U,fixture()),all=t.host.all(),at=s=>{const el=t.q(s);assert(el,s);return all.indexOf(el);};
    const seq=['[role=tablist]','.cg-total','.cg-say-bubble','[data-cd-gwen-slot]','[data-cd-lane-slot]','.cd-board','.cg-tools','[data-cd-picker]','.cg-controls','#cd-break','#cd-level','.cg-actions','#cd-reason','[data-cd-result]'].map(at);
    assert.deepEqual(seq,[...seq].sort((a,b)=>a-b),'좁은 화면 순서가 DOM 순서와 같아야 함');
    assert(t.q('.result-team').contains(t.q('[data-cd-picker]'))&&t.q('.result-summary').contains(t.q('.cg-controls')));
    // 그웬 결과 자리는 결과 칸이 아니라 4번째 칸(합계) 안 — 자동 찾기 결과 요약과 같은 모양
    const say=t.q('.cg-total');assert(say.contains(t.q('[data-cd-gwen-slot]'))&&!t.q('[data-cd-result]').contains(t.q('[data-cd-gwen-slot]')));
    assert(!t.q('[data-cd-part=total]').contains(t.q('[data-cd-gwen-slot]')),'다시 그리는 말풍선 조각 안에 그웬 자리가 있으면 안 됨');
    const sum=new El('div');sum.innerHTML=U.summaryHtml(fixture(),{gwen:'<div data-gwen-slot="cosmoSearch-result"></div>'});
    assert(sum.querySelector('.cg-total').contains(sum.querySelector('[data-gwen-slot="cosmoSearch-result"]')),'찾기 결과도 그웬은 4번째 칸');
    sum.innerHTML=U.summaryHtml(fixture());assert(!sum.querySelector('[data-gwen-slot]')&&sum.querySelector('.cg-say-bubble [data-k=cs-sum]'),'2위 이하: 말풍선만');
    assert.equal(U.html(fixture()).indexOf('data-direct-'),-1,'기존 직접 편성의 문서 전체 핸들러에 걸리는 속성을 쓰지 않음');
    for(const id of ['direct-panel','direct-board','direct-break','direct-picker-open'])assert(!t.q('#'+id),'기존 화면과 id 가 겹치면 안 됨: '+id);
  }
  // 6. 보드: 화면 순서 후열1·전열1·전열2·후열2, 리더, 콜백 인자(draft 의 칸 번호 = 엔진 순서)
  {
    const t=mount(U,fixture()),slots=t.qa('.cd-board .direct-slot');
    assert.deepEqual(slots.map(s=>s.querySelector('.direct-position').textContent),['후열1','전열1','전열2','후열2']);
    assert.deepEqual(slots.map(s=>s.getAttribute('data-cd-slot')),['2','0','1','3']);
    assert.deepEqual(slots.map(s=>s.getAttribute('data-pos')),['back','front','front','back']);
    assert.deepEqual(slots.map(s=>s.querySelector('.direct-name').textContent),['크리스텔','카르멘','에밀리','프레이']);
    assert.deepEqual(slots.map(s=>s.className.includes('direct-leader')),[false,true,false,false]);
    assert.equal(slots[1].querySelector('.direct-leader-toggle').getAttribute('aria-pressed'),'true');
    t.click(slots[0].querySelector('.direct-leader-toggle'));t.click(slots[3].querySelector('.direct-grow'));
    assert.deepEqual(t.calls,[['draft','baskerville',{type:'leader',key:'cristelle'}],['draft','baskerville',{type:'grown',slot:3,value:true}]]);
    // 칸 고르기 → 다른 칸 = 맞바꾸기, 고른 칸에 후보 넣기 = 그 칸으로 put, 빼기
    t.calls.length=0;t.click('[data-cd-act="slot"][data-slot="2"]');assert.deepEqual(t.calls,[],'칸 고르기는 화면 안 일');
    assert(t.q('[data-cd-slot="2"]').className.includes('selected'));assert.match(t.q('.cd-selection').textContent,/고른 칸: 후열1 크리스텔/);
    t.click('[data-cd-act="slot"][data-slot="1"]');assert.deepEqual(t.calls,[['draft','baskerville',{type:'swap',a:2,b:1}]]);
    assert(!t.q('.cd-board .selected'));
    t.calls.length=0;t.click('[data-cd-act="slot"][data-slot="3"]');t.click(cand(t,'lugh'));
    assert.deepEqual(t.calls,[['draft','baskerville',{type:'put',key:'lugh',slot:3}]]);
    t.calls.length=0;t.click('.cd-board [data-cd-act="remove"][data-slot="0"]');assert.deepEqual(t.calls,[['draft','baskerville',{type:'remove',slot:0}]]);
    // 도구: 4명이면 자동 배치 가능, 되돌리기는 canUndo 일 때만
    t.calls.length=0;t.click('[data-cd-act="arrange"]');t.click('[data-cd-act="clear"]');t.click('[data-cd-act="undo"]');
    assert.deepEqual(t.calls,[['arrange','baskerville'],['draft','baskerville',{type:'clear'}]]);
    assert(t.q('[data-cd-act="undo"]').disabled);
    U.render(t.host,{...fixture(),canUndo:true},t.h);t.calls.length=0;t.click('[data-cd-act="undo"]');assert.deepEqual(t.calls,[['undo','baskerville']]);
    const e=mount(U,fixture({state:{active:'disparity'}}));assert(e.q('[data-cd-act="arrange"]').disabled&&e.q('[data-cd-act="clear"]').disabled);
    // 육성 체크는 팀 draft 값을 그대로 보임
    const g=fixture();g.state.teams.baskerville.draft.slots[3].grown=true;const gm=mount(U,g),gb=gm.q('.direct-grow[data-slot="3"]');
    assert.equal(gb.getAttribute('aria-pressed'),'true');assert.match(gb.textContent,/☑ 육성했다면/);gm.click(gb);
    assert.deepEqual(gm.calls,[['draft','baskerville',{type:'grown',slot:3,value:false}]]);
  }
  // 7. 브레이크(선택)·난이도·3팀 같은 난이도
  {
    const t=mount(U,fixture()),brk=t.q('#cd-break'),lv=t.q('#cd-level');
    const opts=brk.querySelectorAll('option');assert.deepEqual(opts.map(o=>o.textContent),['자동 선택','장착 안 함','스타피어서 Lv.10','차원 강습 Lv.8']);
    assert(opts[1].hasAttribute('selected'));assert.match(brk.parent.textContent,/브레이크 스킬 \(선택\)/);
    assert.equal(lv.querySelectorAll('option').length,19);assert.equal(lv.querySelector('option[selected]').getAttribute('value'),'10');
    assert.equal(lv.querySelector('option').textContent,'레벨 0(없음)');
    const change=(el,value)=>{el.value=value;fire(t.host,'change',el);};
    change(brk,'차원 강습');change(brk,'');change(brk,'auto');change(lv,'14');
    assert.deepEqual(t.calls,[['draft','baskerville',{type:'brk',value:{name:'차원 강습',level:8}}],['draft','baskerville',{type:'brk',value:null}],['draft','baskerville',{type:'brk',value:'auto'}],['level','baskerville',14]]);
    assert.equal(t.q('#cd-level-all'),null,'3팀 일괄 난이도 줄 없음 — 난이도는 팀별로만');assert.equal(t.q('[data-cd-act="level-all"]'),null);
    const m=mount(U,fixture({state:{active:'mogulus'}}));assert.equal(m.q('#cd-break option[selected]').textContent,'스타피어서 Lv.10');
    const a=fixture();a.state.teams.baskerville.draft.brk='auto';assert.equal(mount(U,a).q('#cd-break option[selected]').textContent,'자동 선택');
  }
  // 8. 결과·합계·단계 안내
  {
    const t=mount(U,fixture({state:{active:'mogulus'}})),box=t.q('[data-cd-result]');
    assert(!box.hidden);assert.equal(t.q('.cg-result-title').textContent,'모굴루스 팀 결과');
    assert.match(box.textContent,/클리어82%/);assert.match(box.textContent,/깰 수 있음/);assert.match(box.textContent,/1,182,400점수/);
    assert.match(t.q('#cd-tab-mogulus').textContent,/1,182,400클리어 82%/);assert(t.q('#cd-tab-mogulus .cg-face img.lead'));
    assert.equal(t.q('.cg-steps [aria-current=step]').textContent.replace(/\s+/g,' ').trim(),'② 구원자 4명 넣기구원자 4명');
    const lane=t.q('[data-cd-lane-slot]'),gwen=t.q('[data-cd-gwen-slot]');gwen.innerHTML='<img src="x.png" alt="">';
    const v=fixture();v.summary={teams:{mogulus:{status:'done',score:1182400,clear:.82},baskerville:{status:'done',score:968300,clear:.74,turn:38},disparity:{status:'done',score:901750,clear:.68}},total:3052450,done:3,need:0};
    U.render(t.host,v,t.h);
    assert.equal(t.q('.cg-total-num').textContent,'3,052,450');assert(!t.q('.cg-total-num').className.includes('pending'));
    assert.equal(t.q('.cg-say-bubble').textContent,'클리어는 운이 좀 필요해합계 3,052,450!');
    assert.equal(t.q('.cg-say-line').textContent,'클리어는 운이 좀 필요해');
    // 클리어율이 LOW_CLEAR 미만인 팀만 ⚠ 경고색
    assert.equal(U.LOW_CLEAR,.5);assert(!t.q('#cd-tab-disparity .cg-clear-low'));
    v.summary.teams.disparity.clear=.49;U.render(t.host,v,t.h);
    assert.equal(t.q('#cd-tab-disparity .cg-clear-low')?.textContent,'⚠ 클리어 49%');assert.equal(t.qa('.cg-clear-low').length,1);
    assert.match(t.q('#cd-tab-disparity').getAttribute('aria-label'),/클리어 49%\(낮음\)/);
    assert.match(t.q('.cg-say-line').textContent,/^괴리.* 쪽이 아슬아슬해!$/,'가장 약한 팀을 그웬이 짚음');
    v.summary.teams.disparity.clear=.5;U.render(t.host,v,t.h);assert.equal(t.qa('.cg-clear-low').length,0,'기준값과 같으면 경고 아님');
    for(const k of ['mogulus','baskerville','disparity'])v.summary.teams[k].clear=.9;U.render(t.host,v,t.h);
    assert.equal(t.q('.cg-say-line').textContent,'다 해볼 만해, 자신 있어!');
    assert.match(t.q('[data-cd-result]').textContent,/38예상 턴/);assert.equal(t.qa('.cg-steps li.done').length,4);assert(!t.q('.cg-steps [aria-current=step]'));
    assert(t.q('[data-cd-lane-slot]')===lane&&t.q('[data-cd-gwen-slot]')===gwen&&gwen.children.length===1,'다시 그려도 그웬 자리(와 그 안에 붙인 것)는 그대로');
    // 보스 카드 보강 줄: 난이도 태그+반대 점수 / 보스 깎음 / 브레이크. 값이 없으면 그 줄만 생략, 결과 전 카드엔 없음.
    assert(!t.q('#cd-tab-mogulus .cg-more'),'보강 값이 하나도 없으면 줄 없음');
    Object.assign(v.summary.teams.mogulus,{mode:'top',level:7,other:1100000,frac:.913,brk:{name:'특이점 <관측>',level:4}});
    Object.assign(v.summary.teams.baskerville,{mode:'mean',level:3,brk:'auto'});
    Object.assign(v.summary.teams.disparity,{frac:.5,brk:{name:'스타피어서',level:null}});
    U.render(t.host,v,t.h);
    const more=k=>t.qa(`#cd-tab-${k} [data-cg-more]`).map(e=>e.getAttribute('data-cg-more')+':'+e.textContent);
    assert.deepEqual(more('mogulus'),['level:난이도 7평균 1,100,000','frac:보스 깎음 91%','brk:브레이크 특이점 <관측> Lv.4']);
    assert.equal(t.q('#cd-tab-mogulus .cg-lv')?.textContent,'난이도 7','난이도는 태그');
    assert.deepEqual(more('baskerville'),['level:난이도 3','brk:브레이크 자동 선택'],'점수·깎음 없으면 그 줄(조각) 생략');
    assert.deepEqual(more('disparity'),['frac:보스 깎음 50%','brk:브레이크 스타피어서'],'난이도·반대 점수 없으면 첫 줄 생략, 레벨 없으면 Lv 생략');
    v.summary.teams.disparity.other=5;U.render(t.host,v,t.h);assert.deepEqual(more('disparity')[0],'level:상위 5','순위 기준이 평균이면 반대 점수는 상위');
    assert.match(t.q('#cd-tab-mogulus').getAttribute('aria-label'),/난이도 7 · 평균 1,100,000점 · 보스 깎음 91% · 브레이크 특이점 <관측> 레벨 4$/);
    assert.match(t.q('#cd-tab-mogulus').textContent,/1,182,400클리어 90%난이도 7/,'기존 점수·클리어율은 그대로, 보강 줄은 그 아래');
    assert(t.q('#cd-tab-mogulus .cg-face img.lead')&&t.q('#cd-tab-mogulus .cg-count'),'리더 초상·편성 유지');
    v.summary.teams.disparity={status:'ready',level:9,frac:.9,brk:{name:'x',level:1}};U.render(t.host,v,t.h);
    assert(!t.q('#cd-tab-disparity .cg-more'),'결과 없는 카드엔 보강 줄 없음');
  }
  // 8-2. 4번째 칸 말풍선은 그웬 머리 위(꼬리 아래) — 다른 결과 화면과 같은 규칙, 찾기 결과·직접 편성 공통 부품
  {
    const t=mount(U,fixture()),bub=t.q('.cg-say-bubble'),all=t.host.all();
    assert.equal(bub.getAttribute('data-tail'),'down');assert(all.indexOf(bub)<all.indexOf(t.q('[data-cd-gwen-slot]')),'말풍선이 그웬보다 먼저(위)');
    const sum=new El('div');sum.innerHTML=U.summaryHtml(fixture(),{gwen:'<div data-gwen-slot="cosmoSearch-result"></div>'});
    const sb=sum.querySelector('.cg-say-bubble'),sall=sum.all();
    assert.equal(sb.getAttribute('data-tail'),'down');assert(sall.indexOf(sb)<sall.indexOf(sum.querySelector('[data-gwen-slot="cosmoSearch-result"]')));
    const css=fs.readFileSync(path.join(__dirname,'..','cosmo_direct.css'),'utf8').replace(/\/\*[\s\S]*?\*\//g,'');
    const rule=sel=>[...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].filter(m=>m[1].trim()===sel).map(m=>m[2]).join(';');
    assert.match(rule('.cg-say'),/flex-direction:column(;|$)/,'세로: 말풍선 위·그웬 아래(모든 폭)');
    assert.doesNotMatch(css,/\.cg-say\{[^}]*flex-direction:row/,'어느 폭에서도 옆 배치로 돌아가지 않음');
    assert.match(rule('.cg-say-bubble'),/--ty:calc\(100% \+ \.5px\);--tr:45deg/,'꼬리는 아래(그웬 쪽)');
    assert.doesNotMatch(css,/--tr:135deg/,'옆(왼쪽) 꼬리 없음');
    assert.doesNotMatch(css,/calc\(100% - 108px\)/,'그웬 옆 자리만큼 말풍선을 줄이던 규칙 없음');
  }
  // 9. 화면 안 상태: 도움말 펼침, 검색, 고르기 펼침(좁은 화면)
  {
    const t=mount(U,fixture()),help=t.q('#cd-grow-help'),text=t.q('#cd-grow-help-text');
    assert.equal(help.getAttribute('aria-expanded'),'false');assert(text.hidden);assert.equal(help.getAttribute('aria-controls'),text.id);
    t.click(help);assert.equal(help.getAttribute('aria-expanded'),'true');assert(!text.hidden);assert.match(text.textContent,/더 키웠다고 치고 계산/);
    const search=t.q('[data-cd-search]');search.value='루';fire(t.host,'input',search);
    assert.deepEqual(t.qa('.direct-candidate').map(b=>b.getAttribute('data-key')).sort(),['lugh','luna']);assert(t.q('[data-cd-search]')===search,'검색 칸은 다시 만들지 않음');
    const open=t.q('[data-cd-act="picker"]');assert.equal(open.getAttribute('aria-expanded'),'false');
    t.click(open);assert.equal(open.getAttribute('aria-expanded'),'true');assert.equal(t.q('[data-cd-picker]').getAttribute('data-open'),'true');
    assert.deepEqual(t.calls,[]);
    const x=fixture();x.roster=[...roster,{key:'evil',name:'<b>"악"</b>',el:'sun',cls:'캐스터',img:'a.webp'}];
    assert.equal(cand(mount(U,x),'evil').querySelector('span').textContent.replace('태양 · 캐스터',''),'<b>"악"</b>','이름은 글자 그대로');
  }
}

suite(require('../cosmo_direct_ui'));
console.log('cosmo_direct_ui: 기본 시험 통과');

// ── 변이 검사: 한 군데씩 망가뜨린 부품으로 같은 시험을 돌려 반드시 실패해야 함 ──
const MUTATIONS=[
  ['빈 팀 안내 문구 없앰',"n===0?'비어 있음 · 눌러서 편성':","n===0?'':"],
  ['다른 팀 사용 중 표시를 끔',"if(u&&u!==m.active){","if(false){"],
  ['사용 중 구원자의 aria-disabled 뺌',' aria-disabled="true" aria-label="${name} · ${t} 팀 사용 중',' aria-label="${name} · ${t} 팀 사용 중'],
  ['사용 중 구원자를 눌러도 팀 이동 안 함',"h.onPickerJump?.(to);return;","return;"],
  ['비활성 확인 단추가 콜백을 부름',"if(act==='run-all'){if(!off)h.onRunAll?.();return;}","if(act==='run-all'){h.onRunAll?.();return;}"],
  ['이 팀 확인이 인원 부족을 무시',"const one=!!m.view.running||own.length>0;","const one=!!m.view.running;"],
  ['3팀 확인이 다른 팀 부족을 무시',"||lack.length>0||bad.length>0||m.view.validation?.ok===false;","||bad.length>0||m.view.validation?.ok===false;"],
  ['이유 연결(aria-describedby) 뺌','data-cd-act="run-all" aria-disabled="${g.all}" aria-describedby="cd-reason"','data-cd-act="run-all" aria-disabled="${g.all}"'],
  ['이유 문구를 항상 숨김',"${g.reason?'':' hidden'}","hidden"],
  ['탭 role 뺌','<button type="button" role="tab" class="cg-tab"','<button type="button" class="cg-tab"'],
  ['방향키 핸들러 연결 안 함',"host.addEventListener('keydown',e=>onKey(host,e));",""],
  ['왼쪽·오른쪽 방향 뒤바뀜',"{ArrowRight:(i+1)%n,ArrowLeft:(i+n-1)%n,","{ArrowLeft:(i+1)%n,ArrowRight:(i+n-1)%n,"],
  ['roving tabindex 깨짐','tabindex="${sel?0:-1}"','tabindex="0"'],
  ['브레이크·난이도가 보드보다 앞(좁은 화면 순서 깨짐)',null,src=>{const a=src.indexOf("+`<div class=\"cg-controls\""),b=src.indexOf("+`<div class=\"cd-run\"");const piece=src.slice(a,b),at=src.indexOf("+`<div class=\"cd-board\"");
    assert(a>0&&b>a&&at>0);return src.slice(0,at)+piece+src.slice(at,a)+src.slice(b);}],
  ['확인 단추가 고르기보다 앞',null,src=>{const a=src.indexOf("+`<div class=\"cd-run\""),b=src.indexOf("+`<div class=\"cg-result\"");const piece=src.slice(a,b),at=src.indexOf("+`<button type=\"button\" class=\"sec cd-picker-open\"");
    assert(a>0&&b>a&&at>0);return src.slice(0,at)+piece+src.slice(at,a)+src.slice(b);}],
  ['칸 순서를 엔진 순서 그대로 놓음',"const SCREEN=[2,0,1,3]","const SCREEN=[0,1,2,3]"],
  ['맞바꾸기 인자 틀림',"{type:'swap',a,b:slot}","{type:'swap',a:slot,b:slot}"],
  ['고른 칸을 무시하고 넣음',"{type:'put',key,slot:at}","{type:'put',key,slot:null}"],
  ['육성 체크 값이 뒤집히지 않음',"value:!d.slots[slot]?.grown","value:!!d.slots[slot]?.grown"],
  ['난이도 콜백에 팀을 안 넘김',"ui.h.onLevel?.(m.active,Number(v));","ui.h.onLevel?.(Number(v));"],
  ['브레이크 «장착 안 함» 이 null 이 아님',"v===''?null:","v===''?'auto':"],
  ['다시 그릴 때 그웬 자리까지 갈아엎음',"if(!host.querySelector('[data-cd-root]')){","if(true){"],
  ['결과 칸을 결과 전에도 보임',"data-cd-result${a.result?'':' hidden'}","data-cd-result"],
  ['보강 줄을 카드에 안 붙임',"`<b>${wait}</b>`}</span>${moreHtml(r)}","`<b>${wait}</b>`}</span>"],
  ['보강 줄을 결과 전 카드에도 붙임',"if(r.status!=='done')return '';","if(false)return '';"],
  ['보강: 브레이크 레벨 안 보임',"${r.brk.level!=null?` Lv.${esc(r.brk.level)}`:''}",""],
  ['보강: 반대 점수 이름 뒤바뀜',"`<span>${r.mode==='top'?'평균':'상위'}","`<span>${r.mode==='top'?'상위':'평균'}"],
  ['보강: 깎음 줄 없을 때도 빈 줄',"r.frac!=null?`<span class=\"cg-more-line\" data-cg-more=\"frac\">보스 깎음 ${pct(r.frac)}%</span>`:''","`<span class=\"cg-more-line\" data-cg-more=\"frac\">보스 깎음 ${r.frac!=null?pct(r.frac):''}%</span>`"],
  ['말풍선 꼬리 표시 뺌','cg-say-bubble" data-tail="down"','cg-say-bubble"'],
  ['말풍선이 그웬 아래',null,src=>{const a='<p class="gwen-bubble cg-say-bubble" data-tail="down"${say}</p>',b='<div class="cg-say-gwen">${gwen}</div>';assert(src.includes(a+b));return src.replace(a+b,b+a);}],
  ['이름을 HTML 로 그대로 넣음',"const esc=s=>String(s??'').replace(","const esc=s=>String(s??'');const esc0=s=>String(s??'').replace("],
];
if(!process.argv.includes('--no-mutations')){
  let caught=0;
  for(const [name,from,to] of MUTATIONS){
    const src=from===null?to(SRC):SRC.split(from).join(to);
    assert.notEqual(src,SRC,`변이가 적용되지 않음(코드가 바뀌었는지 확인): ${name}`);
    const mod={exports:{}};new Function('module','require',src)(mod,require);
    let failed=false;try{suite(mod.exports);}catch(e){failed=true;}
    assert(failed,`변이를 못 잡음: ${name}`);caught++;
  }
  console.log(`cosmo_direct_ui: 변이 ${caught}/${MUTATIONS.length}개 잡음`);
}
