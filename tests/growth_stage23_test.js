// Invented teams only. Mutations alter isolated module instances, never source files.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{createRequire}=require('node:module');
const G=require('../growth_guide'),GS=require('../guild_search'),V=require('../guild_view'),CS=require('../cosmo_search'),D=require('../data/guild_defense.json');
const source=fs.readFileSync(require.resolve('../growth_guide'),'utf8');
function load(code){const ctx={module:{exports:{}},require:createRequire(require.resolve('../growth_guide'))};vm.runInNewContext(code,ctx);return ctx.module.exports;}
function signature(g=G){const s={account:'synthetic',options:{growth:true},targets:['x'],content:['guild','EX'],excluded:[],
  equipment:['hash',[]],policy:['v',7200,120000,17011,900001]};
  const sig=g.signature(s),history={a:{signature:sig,content:'guild/EX',rows:[{key:'x',kind:'growth',delta:10,confirmed:true}]}};
  assert.equal(g.priority(history,sig).length,1);
  for(const k of ['equipment','policy'])assert.equal(g.priority(history,g.signature({...s,[k]:'changed'})).length,0,k);
  assert(!g.compatible(JSON.stringify(JSON.parse(sig).slice(0,12)),sig));
  const row=(key,delta)=>({key,delta,kind:'growth',confirmed:true});
  const h={a:{signature:sig,content:'op/a',unit:'%p',rows:[row('a',20),row('b',10)]},
    b:{signature:sig,content:'guild/a',unit:'점',rows:[row('a',1),row('b',100000)]}};
  // Content ID order puts guild first; a huge unrelated op delta must not override it.
  assert.equal(g.priority(h,sig)[0].key,'b');h.a.rows[0].delta=1e12;assert.equal(g.priority(h,sig)[0].key,'b');
  const disjoint={a:{...h.a,rows:[row('a',1)]},b:{...h.b,rows:[row('b',1e12)]}};
  assert.equal(g.priority(disjoint,sig)[0].key,'a','different contents use stable name tie, never raw magnitude');
}
function guild(g=G){const metric=g.guildMetric(GS,V,D,4,[1,0,0,0]);
  const ps=[[0,1,0,1],[.7,.8,.9,1],[.95,.95,.95,.95],[1,1,1,1],[0,0,0,0]];
  const rows=ps.map(progs=>metric.prepare({n:4,clear:progs.filter(x=>x===1).length/4,prog:progs.reduce((a,b)=>a+b)/4,progs,via:{}}));
  for(let i=0;i<rows.length;i++){const r=rows[i],expected=GS.rankStats(V,D,4,[1,0,0,0],r.prog,ps[i],r.clear);
    for(const k of ['top','mean','cap'])assert.equal(r[k],expected[k]);assert.equal(r.scores.length,4);
    assert.equal(JSON.stringify(r.scores),JSON.stringify(ps[i].map(p=>V.scoreFromProg(D,V.extraPct(D,4,[1,0,0,0]),p))));}
  assert.notEqual(rows[0].mean,V.scoreFromProg(D,V.extraPct(D,4,[1,0,0,0]),.5),'per-run scores differ from score(mean progress)');
  for(const a of rows)for(const b of rows)assert.equal(Math.sign(metric.rank(a,b)),Math.sign(b.top-a.top||b.cap-a.cap||b.mean-a.mean));
  const a={mean:4,cap:0},b={mean:3,cap:1};assert(metric.screenRank(a,b,0)<0);assert(metric.screenRank(a,b,1)>0);
  assert.equal(metric.prepare({prog:1,clear:1,n:100}),null,'missing per-run values are not silently replaced');
  const mixed=metric.compare(rows[1],rows[0]);assert.deepEqual(mixed.ci,metric.compare(rows[1],rows[0]).ci);
  assert(metric.compare(rows[3],rows[4]).confirmed);
  const x=Array.from({length:13},(_,i)=>i*i),y=[1,7,13,24,31,82];
  assert.deepEqual(g.bootstrap(x,y,g.topScore,4,123),g.bootstrap(x,y,g.topScore,4,123));
  assert.notDeepEqual(g.bootstrap(x,y,g.topScore,4,123),g.bootstrap(x,y,g.topScore,9,123),'seed controls bootstrap');
}
const keys=[['a','b','c','d'],['e','f','g','h'],['i','j','k','l']];
function triples(g=G,cs=CS){const owned=keys.map((k,i)=>[{keys:k,score:10,bossIndex:i}]),assumed=keys.map((k,i)=>[{keys:['x',...k.slice(1)],score:30+i,bossIndex:i}]);
  const result=g.cosmoTriples(cs,owned,assumed,3);assert.equal(result.length,3);assert.equal(result[0].sum,52);
  for(const t of result){const ks=t.teams.flatMap(x=>x.keys);assert.equal(new Set(ks).size,12);assert.equal(ks.filter(k=>k==='x').length,1);}
  // Relocated owned savior can fill another boss, but cannot occupy two teams.
  owned[1].push({keys:['b','f','g','h'],score:100});
  for(const t of g.cosmoTriples(cs,owned,assumed,3))assert.equal(new Set(t.teams.flatMap(x=>x.keys)).size,12);
}
async function scheduling(g=G){const owned=keys.map((ks,i)=>[{id:'old'+i,keys:ks,bossIndex:i}]),controls=[{id:'new',keys:['a','b','c','m'],bossIndex:0}];
  const targets=[{id:'x',key:'x',kind:'growth',source:'assumed',controls,candidates:keys.map((ks,i)=>({id:'x'+i,keys:['x',...ks.slice(1)],bossIndex:i}))}];
  const calls=[],evaluate=async(jobs,n,seed)=>{calls.push({jobs,n,seed});return Object.fromEntries(jobs.map(j=>[j.id,
    {n,prog:.8,progs:Array(n).fill(.8),via:{},cosmo:{mean:j.id==='new'||j.id==='x0'?90:10,top:j.id==='new'||j.id==='x0'?90:10,n,clear:0,frac:.6}}]));};
  const r=await g.searchCosmo({CS,owned,established:owned.flat(),targets,evaluate});
  assert(r.rows[0].result,'scenario actually evaluated');assert.equal(r.rows[0].delta,0,'new owned team raises baseline too');
  assert.equal(r.baseline.sum,110);assert(r.runs>0&&r.runs<=12000);assert.equal(calls[1].n,100);assert.notEqual(calls[0].seed,calls[1].seed);
  for(const id of ['x0','x1','x2'])assert(calls[0].jobs.some(j=>j.id===id),'all three boss cases must be screened');
  assert.equal(new Set(r.rows[0].team.teams.flatMap(t=>t.keys)).size,12);
  const partial=await g.searchCosmo({CS,owned,established:owned.flat(),targets,evaluate:async(jobs,n,seed)=>{const out=await evaluate(jobs,n,seed);if(n===100)delete out.old0;return out;}});
  assert(partial.baselinePending);assert.equal(partial.rows[0].delta,null);
  assert.equal(await g.searchCosmo({CS,owned,targets,evaluate,alive:()=>false}),null);
  const limited=await g.searchCosmo({CS,owned,targets,evaluate,limits:{maxRuns:150}});assert(limited.runs<=150);assert(limited.rows.every(r=>r.delta==null));
  const before=JSON.stringify({owned,targets});await g.searchCosmo({CS,owned,targets,evaluate});assert.equal(JSON.stringify({owned,targets}),before);
}
async function guildSchedule(g=G){const metric=g.guildMetric(GS,V,D,0,[]),calls=[];
  const evaluate=async(jobs,n,seed)=>{calls.push({jobs,n,seed});return Object.fromEntries(jobs.map(j=>[j.id,metric.prepare({n,clear:0,prog:.8,
    progs:Array.from({length:n},(_,i)=>j.id==='cap'?(i===0?1:.5):j.id==='mean'?.85:.6),via:{}})]));};
  const r=await g.search({metric,owned:[{id:'old',result:metric.prepare({progs:[.6],prog:.6,clear:0,n:1})}],
    targets:[{id:'x',key:'x',candidates:[{id:'mean'},{id:'cap'}]}],evaluate});
  assert(calls[1].jobs.some(j=>j.id==='mean')&&calls[1].jobs.some(j=>j.id==='cap'),'mean and cap diversity survive');
  assert.equal(r.rows[0].team.id,'mean');assert(r.rows[0].result.prog>0&&r.rows[0].ci);assert(r.runs<=7200);
  const dropped=await g.search({metric,owned:[],targets:[{id:'x',candidates:[{id:'mean'},{id:'cap'}]}],limits:{maxRuns:200},
    evaluate:async(jobs,n,seed)=>{const out=await evaluate(jobs,n,seed);if(n===4){delete out.cap;Object.defineProperty(out,'completed',{value:jobs.length});}return out;}});
  assert.equal(dropped.runs,8,'filtered coop runs still consume budget');
}
async function workerContract(){const ui=fs.readFileSync(require.resolve('../growth_ui'),'utf8');let active=0,peak=0;
  const ctx={GuildSearch:GS,GROW:{id:1,versions:{engine:'e'},errors:[]},navigator:{hardwareConcurrency:16},location:{href:'https://example.test/index.html'},
    simOpt:()=>({rule:'test'}),growthPaint(){},setTimeout,clearTimeout,Worker:class {
      constructor(){active++;peak=Math.max(peak,active);}
      postMessage(req){setTimeout(()=>{if(this.dead)return;this.onmessage({data:{type:'team',id:req.id,key:req.teams[0].key,
        result:{ver:'e',n:req.n_runs,prog:.8,progs:Array(req.n_runs).fill(.8),via:{coop:1}}}});
        if(req.teams[0].key!=='slow')this.onmessage({data:{type:'done',id:req.id}});},1);}
      terminate(){if(!this.dead){this.dead=true;active--;}}
    }};
  ctx.MODE='auto';ctx.SIMQ={};ctx.growthMetric=r=>r;
  ctx.scrPool=()=>ctx.SIMQ.pool||(ctx.SIMQ.pool=[ctx.SIMQ.w,new ctx.Worker(),new ctx.Worker()]);
  vm.runInNewContext(ui.slice(ui.indexOf('function growthEvaluate'),ui.indexOf('function growthMaybe')),ctx);
  const jobs=Array.from({length:3},(_,i)=>({id:'j'+i,party:{},options:{}}));
  const r=await ctx.growthEvaluate(jobs,4,17011,{key:'op'},{tab:'a',name:'stage'},1,Date.now()+1000);
  assert.equal(Object.keys(r).length,3);assert.equal(r.j0.progs.length,4);assert.equal(r.j0.via.coop,1);assert.equal(peak,3);
  const partial=await ctx.growthEvaluate([{id:'slow',party:{}}],100,900001,{key:'op'},{tab:'a',name:'b'},1,Date.now()+30);
  assert.equal(partial.slow.n,100);assert(partial.incomplete);assert.equal(active,0,'deadline closes worker, retaining completed teams');
  const cancelled=ctx.growthEvaluate([{id:'slow',party:{}}],100,900001,{key:'op'},{tab:'a',name:'b'},1,Date.now()+1000);
  ctx.GROW.id++;ctx.GROW.stop();const stopped=await cancelled;assert.equal(Object.keys(stopped).length,0);assert.equal(active,0);
}
(async()=>{signature();guild();triples();await scheduling();await guildSchedule();await workerContract();
  for(const [name,from,to,test] of [
    ['history conditions','s.equipment,s.policy','null,null',signature],
    ['content units','.find(c=>c.content===id&&c.metric===x.metric&&c.unit===x.unit)','[0]',signature],
    ['per-run score','V.scoreFromProg(G,V.extraPct(G,level,tiers),p)','V.scoreFromProg(G,V.extraPct(G,level,tiers),r.prog)',guild],
    ['guild rank','b.top-a.top||b.cap-a.cap||b.mean-a.mean','b.mean-a.mean||b.cap-a.cap||b.top-a.top',guild],
    ['guild screening diversity','[t.best,mean,cap,...(t.controls||[])]','[t.best,...(t.controls||[])]',guildSchedule],
    ['filtered run budget','r.completed??Object.keys(r).length','Object.keys(r).length',guildSchedule],
    ['bootstrap seed','let state=seed>>>0','let state=1',guild],
    ['one boss','i===k?assumed[k]:list','assumed[k]',triples],
    ['three boss screening','screenPlan(targets,Math.max(0,...targets.map(t=>t.candidates?.length||0)))','screenPlan(targets)',scheduling],
    ['new owned baseline','const finalOwned=lists(allOwned,fr)','const finalOwned=lists(owned.flat(),fr)',scheduling]
  ]){assert(source.includes(from),name);const mutant=load(source.replace(from,to));let failed=false;try{await test(mutant);}catch{failed=true;}assert(failed,'mutation survived: '+name);console.log('MUTATION caught + restored:',name);}
  const csSource=fs.readFileSync(require.resolve('../cosmo_search'),'utf8'),ctx={module:{exports:{}},require:createRequire(require.resolve('../cosmo_search'))};
  vm.runInNewContext(csSource.replace('if (x[w] & y[w])','if (false)'),ctx);assert.throws(()=>triples(G,ctx.module.exports));console.log('MUTATION caught + restored: savior overlap');
  signature();guild();triples();await scheduling();await guildSchedule();console.log('ALL OK growth stage23');
})().catch(e=>{console.error(e);process.exitCode=1;});
