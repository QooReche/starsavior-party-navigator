// Independent holdout: selected rows are fixed before any evaluation is observed.
// node tools/evaluate_guild_time.js ACCOUNT PRIVATE_DIR SEARCH_DIR [SEARCH_DIR ...]
'use strict';
const fs=require('node:fs'),path=require('node:path'),GS=require('../guild_search'),Planner=require('../guild_planner'),V=require('../guild_view');
const {context,instrument,privateDir,save,hash}=require('./measure_guild_time');
const read=f=>JSON.parse(fs.readFileSync(f,'utf8'));
function stats(scores,clears,caps){const sorted=scores.slice().sort((a,b)=>b-a),n=scores.length,k=Math.ceil(n*.2-1e-9);return {top:sorted.slice(0,k).reduce((a,b)=>a+b,0)/k,mean:scores.reduce((a,b)=>a+b,0)/n,clear:clears.reduce((a,b)=>a+b,0)/n,...(caps?{cap:caps.reduce((a,b)=>a+b,0)/n}:{}),n};}
function wilson(p,n){const z=1.959963984540054,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [Math.max(0,c-h),Math.min(1,c+h)];}
function comparison(a,b,draws=4000){
 if(a.scores.length!==b.scores.length||!a.scores.length)throw Error('paired holdout lengths differ');
 let seed=20261121;const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
 const n=a.scores.length,boot={topRatio:[],meanRatio:[],clearDifference:[]};
 const delta=(x,y)=>({topRatio:y.top/x.top,meanRatio:y.mean/x.mean,clearDifference:y.clear-x.clear});
 for(let i=0;i<draws;i++){const ids=Array.from({length:n},()=>Math.floor(rand()*n)),sample=r=>stats(ids.map(j=>r.scores[j]),ids.map(j=>r.clears[j])),d=delta(sample(a),sample(b));for(const k of Object.keys(boot))boot[k].push(d[k]);}
 const point=delta(a.summary,b.summary),ci95=Object.fromEntries(Object.entries(boot).map(([k,values])=>{values.sort((x,y)=>x-y);return [k,[values[Math.floor(draws*.025)],values[Math.ceil(draws*.975)-1]]];}));
 return {point,ci95,method:'paired percentile bootstrap over independent battle seeds; top 20% recalculated per draw',draws};
}
async function main(){
 const args=process.argv.slice(2);let batches=50,startBatch=0;
 for(const [flag,set] of [['--batches',v=>batches=v],['--start-batch',v=>startBatch=v]]){const i=args.indexOf(flag);if(i>=0){const v=Number(args[i+1]);if(!Number.isSafeInteger(v)||v<(flag==='--batches'?1:0))throw Error('invalid '+flag);set(v);args.splice(i,2);}}
 const [input,output,...searchDirs]=args;if(!input||!output||!searchDirs.length)throw Error('ACCOUNT PRIVATE_DIR SEARCH_DIR ... [--batches N] [--start-batch N]');
 const dir=privateDir(output),selections=searchDirs.map(d=>({name:path.basename(d),search:read(path.join(d,'result.json'))})),cx=context(input,selections[0].search.pins.season.id);
 for(const s of selections){if(s.search.pins.accountHash!==hash(fs.readFileSync(input))||s.search.pins.profileHash!==hash(cx.results)||JSON.stringify(s.search.pins.tiers)!==JSON.stringify(cx.tiers)||s.search.pins.stage!==cx.stage||s.search.pins.seasonHash!==hash(cx.G)||s.search.pins.seedOffset!==selections[0].search.pins.seedOffset||s.search.pins.sources['sim/manifest.json']!==hash(fs.readFileSync(path.join(__dirname,'../sim/manifest.json'))))throw Error('holdout account/conditions/engine mismatch');}
 const cls=Object.fromEntries(cx.roster.map(r=>[r.key,r.cls]));
 const jobs=selections.map(({name,search})=>{const t=search.result.rows[0],j=Planner.job(cx.S,t.keys,cx.results,cls,cx.tiers,t.level,t.sup,t.brk?{name:t.brk,level:t.brkLv}:null,{order:t.order,leaderKey:t.leaderKey||t.order[0]});return {...j,key:name};});
 const pins={accountHash:hash(fs.readFileSync(input)),profileHash:hash(cx.results),seasonHash:hash(cx.G),jobs,engine:hash(fs.readFileSync(path.join(__dirname,'../sim/manifest.json'))),tool:hash(fs.readFileSync(__filename)),seedStart:20270101+(selections[0].search.pins.seedOffset||0)+startBatch,batches,runsPerBatch:20};
 if(fs.existsSync(path.join(dir,'result.json'))){if(JSON.stringify(read(path.join(dir,'result.json')).pins)!==JSON.stringify(pins))throw Error('completed holdout input/source mismatch');console.error('existing complete holdout');return;}
 const T=instrument(dir,pins),pool=GS.workerPool(T.makeWorker),evaluated=Object.fromEntries(jobs.map(j=>[j.key,{scores:[],clears:[],caps:[],selected:selections.find(s=>s.name===j.key).search.result.rows[0]}]));
 try{
  for(let batch=0;batch<pins.batches;batch++){
   T.onPhase('independent '+batch,jobs.length);
   const r=await GS.runPhase({jobs,pool,makeWorker:T.makeWorker,workers:2,chunk:1,runs:pins.runsPerBatch,seed:pins.seedStart+batch,stage:cx.stage,base:''}).promise;
   for(const j of jobs){const progs=r[j.key]?.progs;if(progs?.length!==pins.runsPerBatch||progs.some(p=>!Number.isFinite(p)))throw Error('missing independent per-run progress');const v=evaluated[j.key],scores=battleScores(cx.G,j,cx.tiers,r[j.key]),cap=V.scoreAt(cx.G,V.extraPct(cx.G,j.level,cx.tiers),1);v.scores.push(...scores);v.clears.push(...progs.map(p=>Number(p>=1-1e-9)));v.caps.push(...scores.map(s=>Number(s>=cap)));}
   save(path.join(dir,'holdout-progress.json'),{batch:batch+1,evaluated});
  }
  for(const v of Object.values(evaluated)){v.summary=stats(v.scores,v.clears,v.caps);v.clearCI95=wilson(v.summary.clear,v.summary.n);}
  const comparisons={};for(let i=0;i<jobs.length;i++)for(let j=i+1;j<jobs.length;j++)comparisons[jobs[i].key+' -> '+jobs[j].key]=comparison(evaluated[jobs[i].key],evaluated[jobs[j].key]);
  save(path.join(dir,'result.json'),{pins,evaluated,comparisons,...T.summary()});console.error('holdout complete');
 }finally{pool.close();T.close();}
}
function battleScores(G,j,tiers,r){
 const pct=V.extraPct(G,j.level,tiers);
 if(G.season.boss.engine==='client'){
  if(r.guild?.base_scores?.length!==r.progs.length||r.guild.base_scores.some(x=>!Number.isFinite(x)))throw Error('missing independent client scores');
  return r.guild.base_scores.map(n=>Math.floor((n*(100+pct)+50)/100));
 }
 return r.progs.map(p=>V.scoreFromProg(G,pct,p));
}
module.exports={stats,wilson,comparison,battleScores};
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
