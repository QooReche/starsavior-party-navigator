// 실제 페이지의 3+1단계 실행·작업자 메시지·기록 서명. 가짜 결과에도 판별 진행도와 via를 유지한다.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const GS=require('../guild_search'),V=require('../guild_view'),GG=require('../growth_guide');
const source=fs.readFileSync(require.resolve('../guild_search'),'utf8');
const page=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const ui=fs.readFileSync(require.resolve('../growth_ui'),'utf8');
const data=require('../data/guild_defense.json');
const section=(s,a,b)=>{const start=s.indexOf(a);assert(start>=0,a);const end=s.indexOf(b,start);assert(end>start,b);return s.slice(start,end);};
const plain=x=>JSON.parse(JSON.stringify(x));
const skill={name:'스타피어서',level:7};
function load(code){const ctx={module:{exports:{}}};vm.runInNewContext(code,ctx);return ctx.module.exports;}
function context(gs=GS,html=page){
  const G=structuredClone(data),S=G.search;
  Object.assign(S,{poolSize:6,minPowerRatio:0,minRole:{},minFront:0,minDealer:0,excluded:[],screen2:{keep:12,runs:3},finalists:10});
  S.screen.runs=2;S.final={runs:4,levels:[4,6],supports:['fire','gust']};
  const R=Array.from({length:6},(_,i)=>({key:'u'+i,cls:i<2?'서포터':'스트라이커'}));
  const results=Object.fromEntries(R.map((r,i)=>[r.key,{power:100-i,stats:{atk:10},combat:{}}]));
  const combos=gs.combos(S,R),ids=combos.map(k=>k.join('+'));
  const state={phase:'idle',id:0,rows:[],banCoop:true},reqs=[],workers=[],handlers={},phases=[];
  const ctx={GuildSearch:gs,GuildView:V,GrowthGuide:GG,MI:{hash:'synthetic',info:{},brkLv:{[skill.name]:skill.level},profiles:{op:{results}}},
    CFG:{breakSupported:[skill.name,'큐브 과부하'],restrict:{}},EXCL:new Set(),R,D:{guild:G},GSR:state,CSR:{phase:'idle'},SIMQ:{busy:null},
    GS:{sel:null},LS:{get:()=>null},contents:[{key:'guild'}],cur:[{tab:'시즌4',name:'EX'}],navigator:{hardwareConcurrency:2},
    location:{href:'http://example.test/index.html'},seasonBlocked:()=>false,miGrowth:async()=>({}),MyInfoReco:{},
    growthCancel(){},growthPaint(){},growthEnabled:()=>false,renderGuildSearch(){if(!phases.includes(state.msg))phases.push(state.msg);},
    gsTiers:()=>[0,0,0,0],breakOwned:()=>[],simOpt:()=>({}),setTimeout,clearTimeout,
    $:id=>({value:0,addEventListener:(e,fn)=>handlers[id+':'+e]=fn}),
    Worker:class {
      constructor(){workers.push(this);}
      terminate(){this.dead=true;}
      postMessage(req){
        reqs.push(req);
        if(req.n_runs===40&&ctx.beforeBreak){ctx.beforeBreak();ctx.beforeBreak=null;}
        if(ctx.hold&&req.n_runs===40){ctx.started?.();return;}
        setTimeout(()=>{
          if(this.dead)return;
          for(const t of req.teams){
            const ix=ids.indexOf(t.key.split('|')[0]),g=t.options.guild,b=t.options.break_skill;
            // 본선은 u0... 순. 8등 팀은 브레이크 장착 때 상위20%만 클리어(평균은 여전히 낮음).
            const win=req.n_runs===40&&ix===7&&b?.name===skill.name&&b.level===skill.level&&g.level===5;
            const p=g.level===4&&g.support==='gust'?.94-ix*.015:.5;
            const progs=win?[...Array(8).fill(1),...Array(32).fill(0)]:Array(req.n_runs).fill(p);
            const result={n:req.n_runs,clear:win?.2:0,prog:progs.reduce((a,b)=>a+b,0)/progs.length,progs,
              via:ctx.coop&&win?{forced_coop:1}:{trigger:1}};
            this.onmessage({data:{id:req.id,type:'team',key:t.key,result}});
          }
          this.onmessage({data:{id:req.id,type:'done'}});
        },0);
      }
    }};
  ctx.growthWorker=()=>new ctx.Worker();
  vm.createContext(ctx);
  vm.runInContext(section(html,'function brkLv(','function syncBrk('),ctx);
  vm.runInContext(section(html,'function ownedSimBreaks(','const csBoss='),ctx);
  vm.runInContext(section(html,'const gsSig=','const gsLabel='),ctx);
  vm.runInContext(section(ui,'function growthConditions(','function growthPriority('),ctx);
  vm.runInContext(section(ui,'function growthOwnedContext(','// Whole-account'),ctx);
  vm.runInContext(section(html,'async function guildSearchStart(','// ── 코스모 게이트'),ctx);
  return {ctx,state,reqs,workers,handlers,phases,results,ids,run:()=>ctx.guildSearchStart(),sig:()=>vm.runInContext('gsSig()',ctx)};
}
async function search(gs=GS,html=page){
  const t=context(gs,html);await t.run();
  assert.equal(t.state.phase,'done',t.state.msg);
  assert.equal(t.state.rows.length,5);
  const jobs=t.reqs.filter(r=>r.n_runs===40).flatMap(r=>r.teams);
  assert.equal(jobs.length,8*3*2);
  assert.equal(new Set(jobs.map(j=>j.key)).size,jobs.length);
  assert(t.reqs.filter(r=>r.n_runs===40).every(r=>r.seed===2));
  assert(jobs.every(j=>j.options.guild.support==='gust'&&[3,4,5].includes(j.options.guild.level)));
  assert.deepEqual([...new Set(jobs.map(j=>j.key.split('|')[0]))].sort(),t.ids.slice(0,8).sort());
  assert(jobs.some(j=>j.options.break_skill===null));
  assert.deepEqual(plain(jobs.find(j=>j.options.break_skill)?.options.break_skill),skill);
  assert.equal(t.state.rows[0].keys.join('+'),t.ids[7],'브레이크로 8등→1등 재정렬');
  assert.equal(t.state.rows[0].level,5);
  assert.equal(t.state.rows[0].brk,skill.name);assert.equal(t.state.rows[0].brkLv,7);
  assert(t.state.rows[0].mean<t.state.rows[1].mean,'평균 대신 상위20% 기준');
  assert(t.phases.some(s=>s.startsWith('4단계')));assert(t.workers.every(w=>w.dead));
  const rendered=gs.html({...t.state,sig:t.sig()},{hasInfo:true,sig:t.sig(),esc:String,label:k=>k});
  assert(rendered.includes('브레이크 스킬: 스타피어서 Lv.7'));
  return t;
}
async function skipAndFilter(){
  for(const owned of [{},{'미지원':9}]){
    const t=context();t.ctx.MI.brkLv=owned;await t.run();
    assert.equal(t.state.phase,'done');assert(t.reqs.every(r=>r.n_runs!==40));
    assert.equal(t.state.rows[0].keys.join('+'),t.ids[0]);
  }
  const t=context();t.ctx.coop=true;await t.run();
  assert.equal(t.state.rows[0].keys.join('+'),t.ids[0],'4단계도 via 협공 결과 제외');
  assert.equal(t.state.dropped,1);
  const grown=context();await grown.ctx.guildSearchStart(grown.state,{results:grown.results});
  assert.equal(grown.state.rows[0].brk,skill.name,'육성 추천도 동일 단계');
}
function jobsAndSignatures(){
  const visible=(old,current)=>{
    const signature=GG.signature({account:'synthetic',content:['guild','시즌4','EX',old],excluded:[]});
    const record=GG.grownSummary({content:'guild/시즌4/EX',signature,account:'synthetic',version:'test',
      members:[{key:'u0',source:'owned',changedFields:['skills']}],delta:100,metric:'guild-top',unit:'점'});
    return GG.grownPriority({record},signature,{guild:current}).length;
  };
  const t=context(),ctx=t.ctx;
  const sig=t.sig(),oldContext=ctx.growthOwnedContext('guild'),conditions=plain(ctx.growthConditions({key:'guild'}));
  ctx.MI.brkLv[skill.name]=8;
  assert.notEqual(t.sig(),sig);assert.notEqual(ctx.growthOwnedContext('guild'),oldContext);
  assert.equal(visible(conditions,conditions),1);
  assert.equal(visible(conditions,plain(ctx.growthConditions({key:'guild'}))),0);
  ctx.MI.brkLv={[skill.name]:7,'큐브 과부하':2};assert.notEqual(t.sig(),sig);
  const one=t.sig();ctx.MI.brkLv={'큐브 과부하':2,[skill.name]:7};assert.equal(t.sig(),one,'보유 목록 순서 무관');
  assert.deepEqual(plain(ctx.csBreaks()),plain(ctx.ownedSimBreaks()));
  const old={...conditions};delete old.breakCheck;
  assert.equal(visible(old,conditions),0,'옛 기록 무효화');
  ctx.MI.brkLv=null;ctx.breakOwned=()=>[skill.name,'미지원'];
  assert.deepEqual(plain(ctx.ownedSimBreaks()),[{name:skill.name,level:5}]);
  const keys=t.ids[0].split('+'),cls=Object.fromEntries(ctx.R.map(r=>[r.key,r.cls]));
  for(const level of [0,12]){
    const jobs=GS.breakJobs([{keys,level,sup:'fire'}],[skill,{...skill,level:8}],t.results,cls,[]);
    assert.equal(jobs.length,6);assert.equal(new Set(jobs.map(j=>j.key)).size,6);
    assert(jobs.every(j=>j.level>=0&&j.level<=12));
  }
  assert.notEqual(GS.jobKey(keys,4,'fire',[],skill),GS.jobKey(keys,4,'fire',[],{...skill,level:8}));
  assert.notEqual(GS.jobKey(keys,4,'fire',[],skill),GS.jobKey(keys,4,'fire',[],{...skill,name:'큐브 과부하'}));
}
async function cancellation(){
  const t=context();t.ctx.hold=true;
  const started=new Promise(resolve=>t.ctx.started=resolve),running=t.run();await started;
  const pending=t.workers.filter(w=>!w.dead);
  t.handlers['guild-search:click']({target:{closest:()=>({dataset:{gs:'cancel'}})}});
  await running;assert.equal(t.state.phase,'idle');assert.equal(t.state.rows.length,0);
  assert(pending.length>0&&t.workers.every(w=>w.dead));
  pending.forEach(w=>w.onmessage({data:{type:'done'}}));assert.equal(t.state.phase,'idle');
}
async function changedDuringSearch(){
  const t=context(),sig=t.sig(),before=t.ctx.growthOwnedContext('guild');
  t.ctx.beforeBreak=()=>t.ctx.MI.brkLv[skill.name]=8;
  await t.run();
  assert.equal(t.state.sig,sig);assert.equal(t.state.context,before);
  assert.notEqual(t.state.sig,t.sig());assert.notEqual(t.state.context,t.ctx.growthOwnedContext('guild'));
}
async function mutation(label,code,from,to,check){
  assert(code.includes(from),label+' anchor');let caught=false;
  try{await check(code.replace(from,to));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'mutation survived: '+label);console.log('MUTATION caught:',label);
}
(async()=>{
  await search();await skipAndFilter();jobsAndSignatures();await cancellation();await changedDuringSearch();
  await mutation('break_skill 옵션 누락',source,'break_skill: brk','break_skill: null',s=>search(load(s)));
  await mutation('4단계 순위 재정렬 누락',page,'ranked=GuildSearch.rank(V,G,jobsC,resC,tiers,5,S)','ranked=ranked',s=>search(GS,s));
  console.log('PASS guild break: 8 teams, support/levels, 40 runs/seed, rankStats, skip, keys, display, history, cancel');
})().catch(e=>{console.error(e);process.exitCode=1;});
