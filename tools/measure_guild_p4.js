// P4 reduced scope: daily 2 seals, then fixed 30 x 20 independent evaluations.
// node tools/measure_guild_p4.js ACCOUNT PRIVATE_DIR P0_DIR BROWSER_ENV_JSON [0|100]
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {context,instrument,privateDir,save,hash}=require('./measure_guild_time');
const {stats,battleScores}=require('./evaluate_guild_time'),{compare}=require('./report_guild_p0');
const Daily=require('../guild_daily'),GS=require('../guild_search'),V=require('../guild_view');
const ROOT=path.resolve(__dirname,'..'),read=f=>JSON.parse(fs.readFileSync(f,'utf8'));
function constraints(r){
 assert(!r.partial&&!r.timeCapped,'incomplete search');assert(r.teams.length>0);
 assert.equal(new Set(r.teams.flatMap(t=>t.keys)).size,r.teams.length*4);
 assert.equal(new Set(r.teams.map(t=>t.sup)).size,r.teams.length);
 assert(r.teams.every(t=>t.sup&&t.sup!=='none'));assert.equal(r.seals.remaining,0);
}
async function main(){
 const [account,output,p0dir,envfile,only]=process.argv.slice(2),dir=privateDir(output),environment=read(envfile);
 assert(only===undefined||['0','100'].includes(only),'optional offset must be 0 or 100');
 const original=read(path.join(p0dir,'experiment-pins.json'));
 assert.equal(hash(fs.readFileSync(account)),original.accountHash);
 for(const [f,h] of Object.entries(original.sources))if(f.startsWith('battlesim/')||(f.startsWith('data/')&&!['data/guild_defaults.json','data/guild_defense.json','data/guild_seasons/30112.json'].includes(f)))assert.equal(hash(fs.readFileSync(path.join(ROOT,f))),h,'P0 engine/data changed: '+f);
 const reference={A:[],E:[]};
 for(const offset of [0,100]){
  const cx=context(account,30112),base=read(path.join(p0dir,'30112',String(offset),'A/result.json'));
  const oldSeason=structuredClone(cx.G);oldSeason.search=base.pins.settings;
  assert.equal(hash(oldSeason),base.pins.seasonHash,'P0 season changed outside search settings');
  for(const name of ['A','E']){
   const folder=path.join(p0dir,'30112',String(offset),name),s=read(path.join(folder,'result.json')),h=read(path.join(folder,'holdout/result.json'));
   for(const k of ['accountHash','profileHash','seasonHash','tiers','breaks','stage'])assert.deepEqual(s.pins[k],base.pins[k]);
   assert.equal(s.pins.accountHash,original.accountHash);assert.equal(s.pins.profileHash,hash(cx.results));
   assert.deepEqual(s.pins.tiers,cx.tiers);assert.deepEqual(s.pins.breaks,cx.breaks);assert.equal(s.pins.stage,cx.stage);
   for(const k of ['accountHash','profileHash','seasonHash'])assert.equal(h.pins[k],s.pins[k]);
   assert.equal(h.pins.engine,original.sources['sim/manifest.json']);
   assert.equal(h.pins.seedStart,20270101+offset);assert.equal(h.pins.batches,30);assert.equal(h.pins.runsPerBatch,20);
   const v=h.evaluated[name];assert.deepEqual(v.selected,s.result.rows[0]);
   for(const k of ['scores','clears','caps'])assert.equal(v[k].length,600);
   reference[name].push(v);
  }
 }
 const all={};
 for(const offset of [0,100])for(const seals of [2]){
  const cx=context(account,30112);cx.S.preset='daily';cx.seals=seals;cx.split={ex:1,normal:0};cx.nowMs=Date.parse('2026-11-26T12:00:00+09:00');
  cx.secondsPerGame=environment.secondsPerGame;cx.env=environment.env;cx.workers=environment.workers;
  const runDir=privateDir(path.join(dir,String(offset),String(seals))),p0=read(path.join(p0dir,'30112',String(offset),'A/result.json'));
  assert.equal(hash(cx.results),p0.pins.profileHash);
  const strip=g=>{g=structuredClone(g);delete g.search;return g;};
  const pins={accountHash:original.accountHash,profileHash:hash(cx.results),seasonHash:hash(strip(cx.G)),seedOffset:offset,seals,split:cx.split,settings:cx.S,environment,
   sources:Object.fromEntries(['guild_daily.js','guild_search.js','party_placement.js','sim/manifest.json','tools/measure_guild_p4.js','tools/measure_guild_time.js','tools/bench_cosmo_search.py'].map(f=>[f,hash(fs.readFileSync(path.join(ROOT,f)))]))};
  if(only!==undefined&&offset!==Number(only)&&!fs.existsSync(path.join(runDir,'holdout/result.json')))continue;
  let measured;
  if(fs.existsSync(path.join(runDir,'result.json'))){measured=read(path.join(runDir,'result.json'));assert.deepEqual(measured.pins,pins);}
  else{
   // instrument reuses completed replies; resumed time is advisory only.
   const t=instrument(runDir,pins,offset,environment.workers);
   try{const result=await Daily.search({...cx,makeWorker:t.makeWorker,onPhase:t.onPhase});constraints(result);measured={pins,result,...t.summary()};save(path.join(runDir,'result.json'),measured);}
   finally{t.close();}
  }
  constraints(measured.result);assert.equal(measured.result.teams.length,1);assert.equal(measured.result.teams[0].kind,'ex');
  const holdDir=privateDir(path.join(runDir,'holdout')),hp={pins,selected:measured.result.teams,seedStart:20270101+offset,batches:30,runs:20};
  let evaluated;
  if(fs.existsSync(path.join(holdDir,'result.json'))){const h=read(path.join(holdDir,'result.json'));assert.deepEqual(h.pins,hp);evaluated=h.evaluated;}
  else{
   const t=instrument(holdDir,hp,0,environment.workers),pool=GS.workerPool(t.makeWorker),jobs=measured.result.teams.map((x,i)=>({...x,key:'team'+i}));
   evaluated=jobs.map(j=>({selected:j,scores:[],clears:[],caps:[]}));
   try{
    for(let b=0;b<30;b++){
     t.onPhase('independent '+b,jobs.length);
     const r=await GS.runPhase({jobs,pool,makeWorker:t.makeWorker,workers:environment.workers,chunk:1,runs:20,seed:hp.seedStart+b,stage:cx.stage,base:''}).promise;
     jobs.forEach((j,i)=>{const v=r[j.key];assert.equal(v.progs.length,20);const g=j.kind==='ex'?cx.G:{...cx.G,defaultStep:j.step};
      const scores=battleScores(g,j,j.options.guild.sets,v),cap=V.scoreAt(g,V.extraPct(g,j.level,j.options.guild.sets),1);
      evaluated[i].scores.push(...scores);evaluated[i].clears.push(...v.progs.map(x=>Number(x>=1-1e-9)));evaluated[i].caps.push(...scores.map(x=>Number(x>=cap)));
     });
    }
    for(const v of evaluated)v.summary=stats(v.scores,v.clears,v.caps);
    save(path.join(holdDir,'result.json'),{pins:hp,evaluated,...t.summary()});
   }finally{pool.close();t.close();}
  }
  all[offset+'-'+seals]={measured,evaluated};
 }
 if(Object.keys(all).length!==2){console.log(JSON.stringify({completed:Object.keys(all),pending:true}));return;}
 const a=reference.A,e=reference.E;
 const ex=n=>[0,100].map(o=>{const t=all[o+'-'+n].evaluated.find(x=>x.selected.kind==='ex');assert(t,'EX team required');return t;});
 const two=ex(2),vsA=compare(a,two),vsE=compare(e,two);
 const quality=vsA.point.topRatio>=1&&vsA.ci95.meanRatio[0]>=.98&&(vsA.ci95.capDifference[0]>0||vsA.ci95.meanRatio[0]>1);
 const report={vsA,vsE,quality,constraints:true,
  runs:Object.entries(all).map(([id,{measured:m,evaluated:v}])=>({id,seconds:m.seconds,resumed:m.resumed,split:m.result.split,reason:m.result.reason,searchSum:m.result.sum,holdoutTopSum:v.reduce((s,t)=>s+t.summary.top,0),holdoutMeanSum:v.reduce((s,t)=>s+t.summary.mean,0),teams:v.map(t=>({kind:t.selected.kind,summary:t.summary})),reductions:m.result.plan.reductions}))};
 save(path.join(dir,'report.json'),report);console.log(JSON.stringify({quality,constraints:true}));
}
module.exports={constraints};if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
