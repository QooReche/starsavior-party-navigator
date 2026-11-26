// Page regressions: synthetic results only; no browser, workers, or simulations.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {test}=require('node:test');
const read=f=>fs.readFileSync(require('node:path').join(__dirname,'..',f),'utf8');
const page=read('party_template.html'),growth=read('growth_ui.js');
const UI=require('../guild_daily_ui'),V=require('../guild_view'),U=require('../ui_shared');
const G=require('./guild_fixture')(30112),nowMs=Date.parse('2026-11-26T12:00:00+09:00');
G.search.preset='daily';
const team={kind:'ex',step:7,level:1,order:['a','b','c','d'],leaderKey:'c',sup:'none',score:100,mean:90,clear:.5};
const done=()=>({phase:'done',teams:[team],rows:[team],sum:100,split:{ex:1,normal:0},seals:{used:2,remaining:1},plan:{day:V.gameDay(G,nowMs),reductions:[]}});
const cx={G,nowMs,esc:U.esc,hasInfo:true,cards:()=>'',breakBar:()=>'',label:k=>k,say:()=>'',work:()=>'',report:()=>'',error:()=>''};
function fn(src,name,next){const start=src.indexOf('function '+name),end=next?src.indexOf(next,start):-1;assert(start>=0);return src.slice(start,end<0?src.length:end);}
function dailyContext(){
  const c={D:{guild:G},GSR:{id:0,phase:'idle',banCoop:true},MI:{info:{},growth:{},hash:'synthetic',profiles:{op:{results:{}}}},
    R:[],EXCL:new Set(),GuildView:V,GuildDailyUI:UI,Date:class extends Date{static now(){return nowMs;}},
    guildIdentity:()=>['30112','data'],gsTiers:()=>[],ownedSimBreaks:()=>[],growthOptions:()=>({growth:false}),growthEnabled:()=>false,
    GuildDaily:{plan:x=>({estimatedSec:x.growthResults?20:10,withinCap:true,warnings:[]})}};
  vm.createContext(c);vm.runInContext(read('guild_daily_page.js'),c);return c;
}
test('recommendation entry preserves daily Gwen owner and queues no work',()=>{
  const calls=[],c={seasonBlocked:()=>false,contents:[{key:'guild'}],$:()=>({value:0,scrollIntoView(){}}),MI:{info:{}},REQ:false,
    SIMQ:{busy:null},GSR:{phase:'run'},CSR:{phase:'idle'},guildGwenClaim:x=>calls.push(x),recoClearTimer(){},setDrawer(){},run:()=>calls.push('work')};
  vm.runInNewContext(fn(page,'showReco','function run('),c);
  c.showReco();assert.deepEqual(calls,[]);assert.equal(c.REQ,false);
  c.GSR.phase='idle';c.showReco();assert.deepEqual(calls,['reco','work']);
});
test('daily EX and normal stages remove the legacy growth panel',()=>{
  for(const step of [7,6]){
    let removed=0,resets=0;
    const el={dataset:{},remove(){removed++;}},elements={content:{value:0},stage:{value:0},'growth-result':el,out:{append(){}}};
    const c={D:{guild:G},MI:{info:{}},contents:[{key:'guild'}],cur:[{name:step+'단계'}],GROW:{phase:'idle',result:null},SIMQ:{busy:null},
      growthTabs:{reset(){resets++;}},growthRankPaint(){},growthEnabled:()=>true,growthStageKind:()=>false,seasonBlocked:()=>false,
      growthSeasonContent:()=>false,growthIdleText:()=> 'EX 단계에서만 계산함',esc:U.esc,$:id=>elements[id],document:{querySelector:()=>null}};
    vm.runInNewContext(fn(growth,'growthPaint'),c);
    c.growthPaint();assert.equal(removed,1);assert.equal(resets,1);assert(!el.innerHTML);
  }
});
test('growth checkbox invalidates session and immediately refreshes follow, warning and estimate',()=>{
  const c=dailyContext(),box={checked:false,setAttribute(){}},elements={content:{value:0},'assume-growth':box};let closed=0,painted='';
  Object.assign(c,{GrowthGuide:{options:()=>({growth:false})},LS:{get:()=>null,set(){}},SHARE:{},growthControls(){},condChanged(){},
    contents:[{key:'guild'}],$:id=>elements[id],document:{getElementById:id=>elements[id]},
    renderGuildSearch(){c.guildDailyInput();painted=UI.html(c.GSR,{...cx,sig:c.guildDailySig(),plan:c.guildDailyPreview()});}});
  vm.runInContext(fn(growth,'growthOptions','function growthCacheTag'),c);
  c.growthEnabled=()=>box.checked;
  Object.assign(c.GSR,done(),{sig:c.guildDailySig(),session:{close(){closed++;}}});
  c.renderGuildSearch();assert(painted.includes('data-gs="follow"'));assert(painted.includes('약 10초'));
  vm.runInContext(fn(growth,'growthInit','function growthTargets'),c);c.growthInit();box.checked=true;box.onchange();
  assert.equal(closed,1);assert.equal(c.GSR.session,null);assert(!painted.includes('data-gs="follow"'));
  assert(painted.includes('다시 찾기 필요'));assert(painted.includes('약 20초'));
});
test('grown search retains snapshot and passes changed cards, final powers and tasks through UI',async()=>{
  const c=dailyContext(),marks={a:{key:'a',source:'owned',overwrite:true,changedFields:['skills']}};
  const snapshot={profile:{results:Object.fromEntries(team.order.map(k=>[k,{power:200}]))},changes:marks,errors:[]};
  Object.assign(c,{SIMQ:{busy:null},CSR:{phase:'idle'},seasonBlocked:()=>false,growthCancel(){},guildGwenClaim(){},miGrowth:async()=>({}),
    renderGuildSearch(){},growthEnabled:()=>true,fetch:async()=>({ok:true,json:async()=>({})}),MyInfoReco:{overwrite:()=>snapshot},
    SearchExecutor:{PAINT_MS:0,throttle:()=>Object.assign(()=>{},{cancel(){}})},
    GuildDaily:{...c.GuildDaily,createSession:()=>({close(){}})},GuildPlanner:{search:async x=>{assert.equal(x.growthResults,snapshot.profile.results);return {...done(),growth:done()};}},
    LS:{get:()=>null},location:{href:'https://example.test/'},navigator:{hardwareConcurrency:2},csMobile:()=>false,document:{hidden:false},
    LEADKEY:'before',BYKEY:Object.fromEntries(team.order.map(key=>[key,{key,name:key}])),
    card:(x,pos,r,a,manual)=>{if(a)assert.equal(a,marks[x.s.key]);return `${x.s.key}:${a?'grown':'current'}:${a?200:manual?.final?.power||100}`;},
    growthTodoRow:(a,name)=>`task:${name}:${a.changedFields.join(',')}`});
  await c.guildDailyStart();assert.equal(c.GSR.growth.snapshot,snapshot);
  const out=UI.html(c.GSR,{...cx,cards:c.guildDailyCards});
  assert(out.includes('a:grown:200'));assert(out.includes('b:current:200'));assert(out.includes('task:a:skills'));
  assert(out.includes('a:current:100'));assert.equal(c.LEADKEY,'before');
});
test('each daily team reuses escaped unsupported-effect warnings',()=>{
  const unsupported=[{unit:'a',raw:'<effect>'}],out=UI.result({...done(),teams:[{...team,unsupported},team]},cx);
  const sections=out.split('<section').slice(1);
  assert(sections[0].includes('data-k="potential-unsupported"'));assert(sections[0].includes('&lt;effect&gt;'));
  assert(!sections[1].includes('data-k="potential-unsupported"'));
});
test('daily normal-stage guidance never requires selecting EX',()=>{
  for(const id of [30111,30112]){
    const g=require('./guild_fixture')(id);g.search.preset='daily';
    const out=V.panelHtml(g,null,6,nowMs,U.esc);
    assert(out.includes('스테이지 6단계'));assert(!out.includes('EX를 선택해야'));assert(!out.includes('를 선택해야 함'));
  }
});
