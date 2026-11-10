// Gold comparison using production bestTriples; summaries only, raw data stays local.
const fs=require('node:fs'),zlib=require('node:zlib'),path=require('node:path');
const assert=require('node:assert/strict');
const C=require('../cosmo_search.js'),G=require('../data/cosmo_raid.json');
const [out,goldFile='gold.json.gz']=process.argv.slice(2);
const read=p=>JSON.parse(p.endsWith('.gz')?zlib.gunzipSync(fs.readFileSync(p)):fs.readFileSync(p,'utf8'));
const gold=read(path.join(out,goldFile)),catalog=read(path.join(out,'catalog.json'));
const tid=t=>t.teams.map(e=>C.idOf(e.keys)).join('/');
const jobkey=t=>C.jobKey(t.boss,t.keys,6);
const mean=a=>a.reduce((s,v)=>s+v,0)/a.length;
const sd=a=>a.length<2?0:Math.sqrt(a.reduce((s,v)=>s+(v-mean(a))**2,0)/(a.length-1));
const jac=(a,b)=>{const x=new Set(a),y=new Set(b);return [...x].filter(v=>y.has(v)).length/new Set([...x,...y]).size;};
const dirs=fs.readdirSync(out).filter(d=>fs.existsSync(path.join(out,d,'result.json')));
const unique=new Map();
for(const d of dirs){
 const r={...read(path.join(out,d,'result.json')),dir:d},key=[r.size,r.mode,r.variant,r.repeat].join('|'),old=unique.get(key);
 if(old && JSON.stringify(old.result)!==JSON.stringify(r.result))throw Error('same-seed replay differs: '+key);
 if(!old || (old.replay&&!r.replay) || (old.wallSeconds==null&&r.wallSeconds!=null))unique.set(key,r);
}
const reports=[...unique.values()].filter(r=>r.mode==='top');
const output={goldFile,goldSignature:gold.signature??null,goldTeams:gold.rows.length,goldRuns:gold.rows[0].scores.length,goldSeconds:gold.seconds,pools:{}};
for(const size of [...new Set(reports.map(r=>r.size))]){
 const keys=new Set(catalog.slice(0,size).map(r=>r.key)),valid=gold.rows.filter(g=>g.keys.every(k=>keys.has(k)));
 const gm=new Map(valid.map(g=>[g.key,g]));
 const lists=G.season.bossOrder.map(b=>valid.filter(g=>g.boss===b).map(g=>({...g,score:g.summary.top})).sort((a,b)=>b.score-a.score||(a.key<b.key?-1:1)));
 const best=C.bestTriples(lists,5),opt=best[0].sum;
 const bestUnits=new Set(best[0].teams.flatMap(t=>t.keys));
 const pool={candidateUnion:lists.map(l=>l.length),goldBest:best[0],goldBestKeys:best[0].teams.map(t=>t.key),methods:{}};
 const runs=reports.filter(r=>r.size===size);
 for(const variant of [...new Set(runs.map(r=>r.variant))]){
  const group=runs.filter(r=>r.variant===variant).sort((a,b)=>a.repeat-b.repeat),measure=[];
  for(const r of group){
   const phases=fs.readdirSync(path.join(out,r.dir)).filter(n=>/^phase-.*gz$/.test(n)).map(n=>read(path.join(out,r.dir,n)));
   const rerank=phases.find(p=>p.seed%100===3),passed=phases.find(p=>p.seed%100===4),initial=phases.find(p=>p.seed%100===1);
   const initialSets=G.season.bossOrder.map(b=>new Set(initial.jobs.filter(j=>j.boss===b).map(j=>j.key)));
   const passSets=G.season.bossOrder.map(b=>new Set((passed||rerank).jobs.filter(j=>j.boss===b).map(j=>j.key)));
   const rerankSets=G.season.bossOrder.map(b=>new Set(rerank.jobs.filter(j=>j.boss===b).map(j=>j.key)));
   const picked=r.result.rows[0],goldValue=picked.teams.reduce((v,t)=>{const g=gm.get(jobkey(t));if(!g)throw Error('missing gold '+jobkey(t));return v+g.summary.top;},0);
   const recall=sets=>lists.map((l,i)=>Object.fromEntries([50,100,300].map(k=>[k,l.slice(0,k).filter(g=>sets[i].has(g.key)).length/Math.min(k,l.length)])));
   const represented=new Set((passed||rerank).jobs.flatMap(j=>j.keys));
   const baseline=runs.find(x=>x.variant==='baseline'&&x.repeat===r.repeat);
   let monitor=null;
   if(r.result.fast && r.search && baseline){
    const full=read(path.join(out,baseline.dir,'phase-0.json.gz'));
    const results=Object.fromEntries(catalog.slice(0,size).map(x=>[x.key,x]));
    const pl=C.plan(r.search,catalog.slice(0,size));
    monitor=G.season.bossOrder.map((b,i)=>{
     const jobs=full.jobs.filter(j=>j.boss===b),sel=C.surrogateSelect(r.search,jobs,results,20261110+i);
     const core=new Set(sel.core.map(j=>j.key));
     // Exhaustive baseline gives the true FIRST-RUN miss fraction, independently of the audit sample.
     const actual=C.surrogateAudit(r.search,{...sel,audit:jobs.filter(j=>!core.has(j.key))},full.res,r.mode,pl.pass);
     const sampled=C.surrogateAudit(r.search,sel,full.res,r.mode,pl.pass);
     const recorded=r.result.audit.find(a=>a.boss===b);
     for(const field of ['rate','misses','sampled','fallback'])assert.equal(sampled[field],recorded[field],'recorded audit differs: '+b+' '+field);
     return {boss:b,sampledRate:sampled.rate,populationFirstRunRate:actual.rate,
      sampledFallback:sampled.fallback,populationFallback:actual.fallback,
      goldTop50InitialOmission:1-recall(initialSets)[i][50]};
    });
   }
   measure.push({repeat:r.repeat,regret:opt-goldValue,selectedGold:goldValue,selectedKeys:picked.teams.map(jobkey),
    top1:tid(picked),top5:r.result.rows.slice(0,5).map(tid),top1Match:baseline?tid(picked)===tid(baseline.result.rows[0]):null,
    top5Jaccard:baseline?jac(r.result.rows.slice(0,5).map(tid),baseline.result.rows.slice(0,5).map(tid)):null,
    initialRecall:recall(initialSets),passRecall:recall(passSets),rerankRecall:recall(rerankSets),missedSaviors:[...bestUnits].filter(k=>!represented.has(k)),
    phaseSeconds:r.phases.map(p=>p.seconds),phaseGames:r.phases.map(p=>p.teams*p.runs),seconds:r.replay?null:r.seconds,wallSeconds:r.replay?null:(r.wallSeconds??null),audit:r.result.audit||null,monitor});
  }
  const regrets=measure.map(r=>r.regret);
  pool.methods[variant]={runs:measure,regretMean:mean(regrets),regretSD:sd(regrets),regretSE:sd(regrets)/Math.sqrt(regrets.length),
    meanPhaseSeconds:mean(measure.filter(r=>r.seconds!=null).map(r=>r.seconds)),
    timedRuns:measure.filter(r=>r.wallSeconds!=null).length,
    meanSeconds:mean(measure.filter(r=>r.wallSeconds!=null).map(r=>r.wallSeconds)),
    top1Match:mean(measure.map(r=>+r.top1Match)),top5Jaccard:mean(measure.map(r=>r.top5Jaccard))};
 }
 const baseline=pool.methods.baseline;
 const pairs=[];
 for(let i=0;i<baseline.runs.length;i++)for(let j=i+1;j<baseline.runs.length;j++)pairs.push({same:baseline.runs[i].top1===baseline.runs[j].top1,jaccard:jac(baseline.runs[i].top5,baseline.runs[j].top5)});
 pool.baselineBetween={top1Match:mean(pairs.map(p=>+p.same)),top5Jaccard:mean(pairs.map(p=>p.jaccard))};
 pool.regretThreshold=baseline.regretMean+baseline.regretSD;
 for(const [name,m] of Object.entries(pool.methods)){
  const recallOK=G.season.bossOrder.every((_,b)=>mean(m.runs.map(r=>r.passRecall[b][50]))>=mean(baseline.runs.map(r=>r.passRecall[b][50])));
  m.gate={regret:m.regretMean<=pool.regretThreshold,top50:recallOK,noSaviorLoss:m.runs.every(r=>r.missedSaviors.length===0),faster:m.meanSeconds<baseline.meanSeconds};
 }
 output.pools[size]=pool;
}
fs.writeFileSync(path.join(out,'quality-summary.json'),JSON.stringify(output,null,2));
console.log(JSON.stringify(output,null,2));
