const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const G=require('../growth_guide'),Gate=require('../season_gate');
const read=p=>fs.readFileSync(p,'utf8'),ui=read('growth_ui.js'),season=read('season_gate_ui.js'),page=read('party_template.html');
function ranking(code=ui){
  const cond={mode:'auto',rules:{},breaks:[{},{}]},sig=kind=>G.signature({account:'synthetic',options:{growth:true},targets:[],preset:'test',content:[kind,'tab','stage',cond],excluded:[],engine:'e',data:'d'});
  const history=Object.fromEntries(['op','clo','guild','cosmo'].map(kind=>[kind,G.grownSummary({content:kind+'/test',signature:sig(kind),account:'synthetic',version:'test',members:[{key:'a',source:'owned',changedFields:['skills']}],delta:1,metric:'test',unit:'test'})]));
  const saved=JSON.stringify(history),el={hidden:true,innerHTML:''},period={start:'2026-11-01',end:'2026-11-05'},ctx={GrowthGuide:G,MI:{info:{},growth:{},shared:false},QK:{d:{}},D:{},
    contents:[{key:'op'},{key:'guild'},{key:'cosmo'},{key:'clo'}],cur:[{}],BYKEY:{a:{name:'synthetic'}},esc:String,
    $:id=>id==='growth-priority'?el:{value:0},LS:{get:()=>history},MyInfoReco:{hash:()=>''},now:Date.parse('2026-11-02'),query:''};
  ctx.seasonBlocked=key=>['guild','cosmo'].includes(key)&&Gate.state(period,ctx.now,ctx.query).blocked;
  vm.createContext(ctx);vm.runInContext(code,ctx);Object.assign(ctx,{growthEnabled:()=>true,growthSig:()=>sig('op'),growthConditions:()=>cond});
  ctx.history=history;vm.runInContext("GROW.historyEngine='e';GROW.history=history",ctx);
  for(const shared of [false,true]){
    ctx.MI.shared=shared;
    for(const [date,query,count] of [['2026-11-02','',4],['2026-11-05','',2],['2026-10-31','',2],['2026-11-05','?dev=1',4]]){
      ctx.now=Date.parse(date);ctx.query=query;ctx.growthRankPaint();assert(!el.hidden);assert(el.innerHTML.includes(count+'개 콘텐츠'));
      assert.equal(JSON.stringify(history),saved,'closed records stay in persistent and shared history');
    }
  }
}
function rollover(seasonCode=season,pageCode=page,growthCode=ui){
  for(const key of ['guild','cosmo']){
    let stopped=0;
    const ctx={contents:[{key}],$:()=>({value:0}),closed:false,clearTimeout,REQ:true,SIMQ:{busy:'growth',scr:{},kick:true},
      GSR:{id:0,phase:'done'},CSR:{id:0,phase:'done'},renderGuild(){},renderCosmoSearch(){},run(){},stop:()=>stopped++};
    vm.createContext(ctx);vm.runInContext(growthCode,ctx);vm.runInContext(seasonCode,ctx);
    const invalidate=pageCode.match(/^function simInvalidate\(\)\{[^\r\n]*\}/m);
    assert(invalidate,'simInvalidate 를 찾지 못함');
    vm.runInContext(invalidate[0],ctx);
    Object.assign(ctx,{seasonStatus:()=>({blocked:ctx.closed}),seasonBlocked:()=>ctx.closed,seasonPaint(){}});
    vm.runInContext("GROW.phase='running';GROW.stop=stop;GROW.id=3",ctx);
    ctx.seasonRefresh();assert.equal(stopped,0);ctx.closed=true;ctx.seasonRefresh();
    assert.equal(stopped,1,'season refresh must reach the copied search stop handle exactly once');
    assert.equal(vm.runInContext('GROW.id',ctx),4);assert.equal(vm.runInContext('GROW.phase',ctx),'idle');
    assert.equal(vm.runInContext('GROW.stop',ctx),null);assert.equal(ctx.SIMQ.busy,null);
    ctx.seasonRefresh();assert.equal(stopped,1,'same closed state does not cancel twice');
  }
}
function mutate(name,code,from,to,test){assert(code.includes(from),name);assert.throws(()=>test(code.replace(from,to)),{code:'ERR_ASSERTION'},name);console.log('MUTATION caught:',name);}
ranking();
for(const newline of ['\n','\r\n'])rollover(season,page.replace(/\r?\n/g,newline));
mutate('closed history exclusion',ui,"!seasonBlocked(h.content?.split('/')[0])",'true',ranking);
mutate('season cancel chain',season,'simInvalidate();','',s=>rollover(s));
mutate('growth cancel chain',page,'function simInvalidate(){if(typeof growthCancel==="function")growthCancel();','function simInvalidate(){',s=>rollover(season,s));
mutate('copied search stop',ui,'if(GROW.stop)GROW.stop();','',s=>rollover(season,page,s));
console.log('ALL OK small fixes; LF/CRLF; 4 mutations');
