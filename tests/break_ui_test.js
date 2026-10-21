// 브라우저 없이 실제 선택/요청/Worker 코드를 실행한다. node tests/break_ui_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'party_template.html'),'utf8');
const section=(start,end)=>html.slice(html.indexOf(start),html.indexOf(end,html.indexOf(start)));
let owned=['특이점 관측','스타피어서','큐브 과부하'],saved={},handlers={},workers=[];
const ctx=vm.createContext({console,URL,JSON,Number,Promise,
 localStorage:{getItem:k=>saved[k]??null,setItem:(k,v)=>{saved[k]=v}},
 document:{querySelectorAll:()=>owned.map(b=>({dataset:{b}})),querySelector:()=>null},
 $:id=>id==='out'?{addEventListener:(ev,fn)=>{handlers[ev]=fn}}:{value:'0'},
 setTimeout:()=>1,clearTimeout:()=>{},location:{href:'https://example.test/index.html'},
 Worker:class{constructor(){workers.push(this)} postMessage(req){this.req=req} terminate(){this.stopped=true}},
 CFG:{breakSkills:{'특이점 관측':{bonusRoles:[],text:'공·방'},'스타피어서':{bonusRoles:['스트라이커','레인저'],text:'치명'},'큐브 과부하':{bonusRoles:['서포터','디펜더'],text:'속도'}}},
 D:{bicons:{}},BG:{},esc:s=>String(s??''),MODE:'auto',
 contents:[{key:'op',name:'작전 (일반)'}],ckey:party=>party.map(x=>x.s.key).sort().join(','),
 simParty:t=>({units:t.keys}),rkOf:()=>0,simOpt:()=>({build:'standard'}),run:()=>{},
 SIMQ:{n:100,seed:1,res:{},busy:null,LOAD_MS:100,RUN_MS:100},cur:[{tab:'tab',name:'stage'}],LASTQ:{}});
vm.runInContext('const bkeys=Object.keys(CFG.breakSkills);',ctx);
vm.runInContext(section('function pickBreak(', 'const KT='),ctx);
vm.runInContext(section('function breakCard(', '// ---------------- 표시 모드'),ctx);
vm.runInContext(section('const simSig=', 'function simCell('),ctx);
vm.runInContext(section('function simInvalidate(', '// 자동 확인'),ctx);
vm.runInContext(section('function simStart(', 'const LASTQ='),ctx);
vm.runInContext(section('$("out").addEventListener("change"', 'function buildCands('),ctx);
const ev=src=>vm.runInContext(src,ctx),plain=x=>JSON.parse(JSON.stringify(x));
ctx.a={keys:['a','b'],combo:[{s:{key:'b',cls:'스트라이커'}},{s:{key:'a',cls:'레인저'}}]};
ctx.b={keys:['c','d'],combo:[{s:{key:'c',cls:'서포터'}},{s:{key:'d',cls:'디펜더'}}]};
assert.equal(ev('breakChoice(a.combo,contents[0]).name'),'스타피어서');
assert.equal(ev('breakChoice(b.combo,contents[0]).name'),'큐브 과부하');
const initial=ev('simSig(cur[0],a)');
ev('BRSEL["op|a,b"]="특이점 관측";saveBreakSel()');
assert.equal(JSON.parse(saved['pn.brksel.v1'])['op|a,b'],'특이점 관측');
assert.notEqual(ev('simSig(cur[0],a)'),initial);
assert.equal(ev('breakChoice(a.combo,{key:"cosmo",name:"코스모 게이트"}).name'),'스타피어서');
assert.match(ev('breakCard(breakChoice(a.combo,contents[0]),{bs:{supported:true,uses:1.25}})'),/평균 1.25회 발동/);
assert.match(ev('breakCard(breakChoice(a.combo,contents[0]),{bs:{supported:false}})'),/시뮬 미반영/);
console.log('PASS 선택 기본값·팀/콘텐츠 분리·저장·서명·결과 칩');
ctx.LASTQ[1]={rows:[ctx.a,ctx.b]};ev('simStart(1)');
const old=workers[0],req=old.req;
assert.deepEqual(plain(req.teams.map(t=>t.options.break_skill)),[{name:'특이점 관측',level:5},{name:'큐브 과부하',level:5}]);
handlers.change({target:{closest:()=>({dataset:{bkey:'op|a,b'},value:''})}});
assert(old.stopped);
old.onmessage({data:{type:'team',id:req.id,key:'a,b',result:{clear:1}}});
assert.equal(Object.keys(ctx.SIMQ.res).length,0);
ev('simStart(1)');assert.equal(workers[1].req.teams[0].options.break_skill,null);
workers[1].onmessage({data:{type:'team',id:req.id,key:'a,b',result:{clear:1}}});
assert.equal(Object.keys(ctx.SIMQ.res).length,0);
console.log('PASS 팀별 요청·미장착 null·선택 변경 이전 요청 무시');
ev('BRSEL["op|a,b"]="특이점 관측"');owned=owned.filter(n=>n!=='특이점 관측');ev('pruneBreakSel()');
assert.equal(ev('breakChoice(a.combo,contents[0]).name'),'스타피어서');
assert(!('op|a,b' in JSON.parse(saved['pn.brksel.v1'])));
ctx.localStorage.setItem=()=>{throw Error('storage unavailable')};ev('saveBreakSel()');
console.log('PASS 보유 해제 무효화·저장 실패 허용');

(async()=>{
 const sent=[],calls=[];
 const worker=vm.createContext({URL,self:{location:{href:'https://example.test/sim_worker.js'}},postMessage:m=>sent.push(m)});
 vm.runInContext(fs.readFileSync(path.join(root,'sim_worker.js'),'utf8'),worker);
 worker.fake={toPy:x=>x,globals:{get:fn=>(stage,party,n,seed,extra)=>{const opts=JSON.parse(extra);calls.push({fn,opts});return JSON.stringify({bs:{name:opts.break_skill?.name??null}})}}};
 vm.runInContext('ready=Promise.resolve({p:fake,ver:"test"})',worker);
 await worker.onmessage({data:{...plain(req),mode:'manual',options:{build:'standard',rules_override:{power_penalty:'model',basic_tough:1}},
  teams:[{key:'a',party:{},options:{break_skill:{name:'차원 강습',level:5},rules_override:{basic_tough:0}}},{key:'b',party:{},options:{break_skill:null}}]}});
 assert.equal(calls.length,4);
 assert.deepEqual(calls.map(c=>c.opts.break_skill),[{name:'차원 강습',level:5},{name:'차원 강습',level:5},null,null]);
 assert.deepEqual(calls[0].opts.rules_override,{power_penalty:'model',basic_tough:0});
 assert.deepEqual(calls[2].opts.rules_override,{power_penalty:'model',basic_tough:1});
 assert(calls.every(c=>c.opts.build==='standard'));
 assert.equal(sent.filter(m=>m.type==='team').length,2);
 assert(sent.every(m=>m.id===req.id));
 console.log('PASS 실제 Worker auto/manual 팀별 options 병합·요청 ID');
})().catch(e=>{console.error(e);process.exitCode=1});
