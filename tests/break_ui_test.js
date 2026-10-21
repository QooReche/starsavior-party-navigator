// 브라우저 없이 실제 선택/요청/Worker 코드를 실행한다. node tests/break_ui_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'party_template.html'),'utf8');
const section=(start,end)=>html.slice(html.indexOf(start),html.indexOf(end,html.indexOf(start)));
let owned=['특이점 관측','스타피어서','큐브 과부하'],saved={},handlers={},workers=[];
const rules=JSON.parse(fs.readFileSync(path.join(root,'battlesim/rules/default.json'),'utf8'));
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
ctx.CFG.breakSupported=['큐브 과부하',...Object.keys(rules.mc.break_skills)];
vm.runInContext(section('function pickBreak(', 'const KT='),ctx);
vm.runInContext(section('function breakCard(', '// ---------------- 표시 모드'),ctx);
vm.runInContext(section('const simCls=', 'function quickRows('),ctx);
vm.runInContext(section('const simSigB=', 'function simCell('),ctx);
vm.runInContext(section('function simInvalidate(', '// 자동 확인'),ctx);
vm.runInContext(section('function simStart(', 'const LASTQ='),ctx);
vm.runInContext(section('$("out").addEventListener("click",e=>{const b=e.target.closest("button[data-sim]")', '$("out").addEventListener("change"'),ctx);
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

// 이전 서명 식을 독립적으로 유지: 문자열/UTF-8 바이트가 그대로여야 기존 캐시를 쓴다.
const legacy='JSON.stringify([contents[$("content").value].key,cur[0].tab,cur[0].name,simParty(a),SIMQ.n,MODE,teamBreak(a)?.name||null].concat(rkOf()? [rkOf()]:[]))';
for(const mode of ['auto','manual'])for(const rk of [0,3])for(const name of ['',...owned]){
 ctx.MODE=mode;ctx.rkOf=()=>rk;ctx.name=name;ev('BRSEL["op|a,b"]=name');
 assert.deepEqual(Buffer.from(ev('simSig(cur[0],a)')),Buffer.from(ev(legacy)));
 assert.equal(ev('simSigB(cur[0],a,name||null)'),ev(legacy));
}
ctx.MODE='auto';ctx.rkOf=()=>0;
console.log('PASS simSig 기존 키 바이트 동일성(auto/manual·재점화·미장착/장착)');

owned=['특이점 관측','스타피어서','큐브 과부하','차원 강습','행성 정화'];
const targets=plain(ev('breakTargets()')),jobs=plain(ev('breakJobs(cur[0],a)'));
assert.equal(targets.length,owned.length+1);
assert.deepEqual(targets.filter(x=>!x.supported).map(x=>x.name),['행성 정화']);
assert.deepEqual(jobs.map(x=>x.bname),[null,...owned.slice(0,-1)]);
assert.equal(new Set(jobs.map(j=>j.key)).size,jobs.length);
assert(!ev('breakCard(breakChoice(a.combo,contents[0]),null,1,null,cur[0])').includes('data-bcompare'));
assert(ev('breakCard(breakChoice(a.combo,contents[0]),null,1,a,cur[0])').includes('data-bcompare'));
assert(!ev('breakCard(breakChoice(a.combo,contents[0],[]),null,1,a,cur[0])').includes('data-bcompare'));
console.log('PASS 비교 대상(장착 안 함·rules 지원 스킬만 실행)·팀 없으면 버튼 숨김');

const best=rows=>{ctx.testRows=rows;return ev('breakBest(testRows)')};
const row=(name,clear,ttk,supported=true)=>({name,supported,result:{clear,ttk}});
assert.equal(best([row(null,0.8,2),row('A',0.9,8)]),'A');
assert.equal(best([row('A',0.9,8),row('B',0.9,3)]),'B');
assert.equal(best([row('A',0.9,null),row(null,0.9,0)]),null);
assert.equal(best([row('A',0,null),row('B',0,1)]),undefined);
assert.equal(best([row('A',1,1,false)]),undefined);
assert.equal(best([]),undefined);
ctx.MODE='manual';
assert.equal(best([{...row('A',1,1),result:{clear:1,ttk:1,man:{c:0.5,t:2}}},
 {...row('B',0,8),result:{clear:0,ttk:8,man:{c:0.5,t:1}}}]),'B');
assert.deepEqual(plain(ev('breakMetric({clear:1,ttk:1,man:{c:0.5,t:2}})')),{clear:0.5,turn:2});
ctx.MODE='auto';
console.log('PASS 최고 규칙(클리어·턴·0% 우열 없음·미지원 제외·수동 값)');

ev('simInvalidate();SIMQ.res={};BRSEL["op|a,b"]="스타피어서"');
ctx.SIMQ.res[ev('simSigB(cur[0],a,null)')]={clear:0.4,ttk:5};
ev('breakCompareStart(1,"a,b")');
const cw=workers.at(-1),cr=cw.req,expected=jobs.filter(j=>j.bname!==null);
assert.equal(cr.teams.length,expected.length); // 미장착 캐시는 건너뛴다.
assert.deepEqual(plain(cr.teams.map(t=>t.options.break_skill.name)),expected.map(j=>j.bname));
assert(cr.teams.every(t=>JSON.stringify(t.party)===JSON.stringify(plain(ev('simParty(a)')))));
const count=workers.length;ev('breakCompareStart(1,"c,d");simStart(1)');assert.equal(workers.length,count);
const view=()=>ev('breakCompareView(breakChoice(a.combo,contents[0]),1,a,cur[0])');
assert.match(view(),/data-k="breakstate"/);assert.match(view(),/취소/);
assert.equal((view().match(/class="bcrow"/g)||[]).length,targets.length);
assert.match(view(),/행성 정화 · 미지원/);
cw.onmessage({data:{type:'team',id:cr.id,key:'not-a-job',result:{clear:1}}});
assert.equal(Object.keys(ctx.SIMQ.res).length,1);
for(const t of cr.teams)cw.onmessage({data:{type:'team',id:cr.id,key:t.key,result:{clear:0.8,ttk:2}}});
cw.onmessage({data:{type:'done',id:cr.id}});
assert.equal(ctx.SIMQ.busy,null);
assert.equal(Object.keys(ctx.SIMQ.res).length,jobs.length);
assert.match(view(),/최고/);
const requestId=ctx.SIMQ.requestId;
let skippedAuto;
ctx.run=skip=>{skippedAuto=skip};
ctx.localStorage.setItem=(k,v)=>{saved[k]=v};
handlers.click({target:{closest:s=>s==='button[data-bequip]'?{dataset:{bequip:'차원 강습',bkey:'op|a,b'}}:null}});
assert.equal(ev('teamBreak(a).name'),'차원 강습');
assert.equal(ev('SIMQ.res[simSig(cur[0],a)].clear'),0.8);
assert.equal(JSON.parse(saved['pn.brksel.v1'])['op|a,b'],'차원 강습');
assert.equal(skippedAuto,true);
handlers.change({target:{closest:()=>({dataset:{bkey:'op|a,b'},value:'특이점 관측'})}});
assert.equal(skippedAuto,true); // 선택칸에서도 캐시가 있으면 자동 작업을 새로 만들지 않는다.
ev('breakCompareStart(1,"a,b")');assert.equal(ctx.SIMQ.requestId,requestId);
console.log('PASS 비교 작업·진행/취소·중복 실행 차단·공유 캐시·캐시 장착');

// 비교를 눌렀던 팀만, 이동 후에는 완료된 캐시만 복원한다.
assert.equal(ev('breakCompareView(breakChoice(b.combo,contents[0]),2,b,cur[0])'),'');
assert.equal(ev('breakCompareView(breakChoice(a.combo,contents[0]),1,a,{tab:"other",name:"other"})'),'');
assert.match(view(),/bcrow/);
ev('delete SIMQ.res[simSigB(cur[0],a,null)]');assert.equal(view(),'');
ev('breakCompareStart(1,"a,b")');const cancelled=workers.at(-1),cancelReq=cancelled.req;
handlers.change({target:{closest:()=>({dataset:{bkey:'op|a,b'},value:''})}});
assert(cancelled.stopped);assert.equal(ctx.SIMQ.busy,null);
const cached=Object.keys(ctx.SIMQ.res).length;
cancelled.onmessage({data:{type:'team',id:cancelReq.id,key:cancelReq.teams[0].key,result:{clear:1}}});
assert.equal(Object.keys(ctx.SIMQ.res).length,cached);
ev('breakCompareStart(1,"a,b");simStop("취소함")');assert.match(view(),/취소함/);
assert.equal(ctx.SIMQ.busy,null);
console.log('PASS 비교 재표시 범위·부분 캐시 숨김·선택 변경/취소 후 늦은 결과 무시');

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
