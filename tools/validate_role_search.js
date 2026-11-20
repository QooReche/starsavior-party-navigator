// Private results only. Fixed-condition 96-layout reference and independent 200-run evaluation.
const fs=require('node:fs'),path=require('node:path'),P=require('../party_placement'),C=require('../cosmo_search'),GS=require('../guild_search'),V=require('../guild_view');
const {transport}=require('./measure_role_search'),root=path.resolve(__dirname,'..');
const read=f=>JSON.parse(fs.readFileSync(f,'utf8').replace(/^\uFEFF/,''));
const top=a=>{const b=a.slice().sort((x,y)=>y-x);return b.slice(0,Math.ceil(b.length*.2)).reduce((s,x)=>s+x,0)/Math.ceil(b.length*.2);};
function interval(a,b){let seed=20261125;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;},draws=[];
 for(let k=0;k<2000;k++){let x=0,y=0;const ids=Array.from({length:200},()=>Math.floor(random()*200));for(let t=0;t<a.length;t++){x+=top(ids.map(i=>a[t][i]));y+=top(ids.map(i=>b[t][i]));}draws.push((y/x-1)*100);}
 draws.sort((x,y)=>x-y);return [draws[50],draws[1949]];}
async function main(){const [input,dir,mode='independent']=process.argv.slice(2),dest=fs.realpathSync(dir);
 if(dest.toLowerCase().startsWith(root.toLowerCase()))throw Error('private output must be outside repository');
 const D=JSON.parse(fs.readFileSync(path.join(root,'index.html'),'utf8').match(/const D=(\{[^\n]+\});/)[1]),info=read(input),growth=require('../data/growth.json'),G=require('../data/cosmo_raid.json'),GG=require('../data/guild_defense.json');
 const profiles={cosmo:require('../myinfo_reco').profile(info,D.roster,growth,'cosmo'),guild:require('../myinfo_reco').profile(info,D.roster,growth,'op')};
 const T=transport(GS,'role_validation_worker.py'),pool=GS.workerPool(T.makeWorker),start=performance.now();
 const run=(jobs,runs,seed)=>runValidation({jobs,runs,seed,workers:2,makeWorker:T.makeWorker,pool,stage:'validation',base:''});
 const save=(name,value)=>fs.writeFileSync(path.join(dest,name+'.json'),JSON.stringify(value,null,2));
 const job=(t,guild=false)=>{const results=profiles[guild?'guild':'cosmo'].results,layout={order:t.order,leaderKey:t.leaderKey||t.order[0]};
  if(!guild)return C.bossJobs(G.search,t.boss,t.level,[t.keys||t.order],results,{},t.brk?{name:t.brk,level:t.brkLv}:null,layout)[0];
  return {key:P.executionKey(t.keys,layout),party:P.party(t.keys,results,layout).spec,options:{guild:{level:t.level,sets:[0,0,0,0],support:t.sup},break_skill:t.brk?{name:t.brk,level:t.brkLv}:null}};};
 try{
  if(mode==='independent'){
   const evaluated={};
   for(const name of ['rules','free','B','A','guild-old','guild-new']){const selected=read(path.join(dest,name+'.json')).result.rows[0],guild=name.startsWith('guild'),teams=guild?[selected]:selected.teams,jobs=teams.map(t=>job(t,guild));
    const res=await run(jobs,200,20261121);evaluated[name]={teams:teams.map((t,i)=>({...t,evaluation:res[jobs[i].key],scores:guild?res[jobs[i].key].progs.map(p=>V.scoreFromProg(GG,V.extraPct(GG,t.level,[0,0,0,0]),p)):res[jobs[i].key].scores}))};
    evaluated[name].sum=evaluated[name].teams.reduce((s,t)=>s+top(t.scores),0);save('independent-progress',evaluated);console.error('independent complete',name);
   }
   // Paired bootstrap across independent battle seeds; selection seeds are disjoint.
   const comparisons={};for(const [a,b] of [['rules','free'],['rules','B'],['rules','A'],['guild-old','guild-new']]){
    comparisons[a+'→'+b]={differencePct:(evaluated[b].sum/evaluated[a].sum-1)*100,ci95:interval(evaluated[a].teams.map(t=>t.scores),evaluated[b].teams.map(t=>t.scores))};
   }save('independent',{evaluated,comparisons,seconds:(performance.now()-start)/1000,games:T.games});
  }else if(mode==='small'){
   const results=profiles.cosmo.results,eligible=D.roster.filter(r=>results[r.key]?.power>0).sort((a,b)=>results[b.key].power-results[a.key].power);
   const tactical=eligible.filter(r=>r.placementTraits?.length||r.cls==='서포터').slice(0,3),roster=[...new Map([...tactical,...eligible].map(r=>[r.key,r])).values()].slice(0,12),keys=roster.map(r=>r.key);
   const combos=GS.combos({},roster),bosses=G.season.bossOrder,checkpoint=path.join(dest,'small-progress.json');
   const state=fs.existsSync(checkpoint)?read(checkpoint):{keys,done:0,full:bosses.map(()=>[]),reduced:bosses.map(()=>[]),conditions:0};
   if(JSON.stringify(state.keys)!==JSON.stringify(keys))throw Error('small checkpoint pool mismatch');
   for(let i=state.done;i<combos.length;i+=8){const batch=combos.slice(i,i+8),jobs=batch.flatMap(k=>bosses.flatMap(b=>P.all(k,true).flatMap(p=>C.bossJobs(G.search,b,6,[k],results,{},null,p)))),res=await run(jobs,1,20261123);
    for(const k of batch){const reduced=new Set(P.all(k).map(p=>P.executionKey(k,p)));for(let b=0;b<bosses.length;b++){
     const selected=jobs.filter(j=>j.boss===bosses[b]&&P.id(j.keys)===P.id(k));
     for(const type of ['full','reduced']){const ranked=P.best(selected.filter(j=>type==='full'||reduced.has(P.executionKey(k,j))),res,(a,b)=>b.cosmo.top-a.cosmo.top,r=>Number.isFinite(r?.cosmo?.top)),j=ranked[0];state[type][b].push({keys:k,order:j.order,leaderKey:j.leaderKey,level:6,boss:bosses[b],score:j.result.cosmo.top,st:j.result.cosmo});}
    }}state.done=i+batch.length;state.conditions+=jobs.length;save('small-progress',state);console.error('small',state.done,'/',combos.length);
   }
   const best=type=>C.bestTriples(state[type].map(l=>l.sort((a,b)=>b.score-a.score)),1)[0];
   const full=best('full'),reduced=best('reduced');
   const S=structuredClone(G.search);S.learned.value=false;S.speed.surrogate.value=false;S.maxPool=0;
   const search=await C.search({S,bosses,results,roster,level:6,levelMax:18,mode:'top',breaks:[],workers:2,makeWorker:T.makeWorker,stage:'cosmo',base:'',onPhase:(m,n)=>console.error(m,n)});
   const chosen=search.rows[0],selectedJobs=chosen.teams.map(t=>job(t)),one=await run(selectedJobs,1,20261123);
   const selectedScore=selectedJobs.reduce((s,j)=>s+one[j.key].cosmo.top,0),independent={};
   for(const [name,row] of Object.entries({full,reduced,search:chosen})){const jobs=row.teams.map(t=>job(t)),r=await run(jobs,200,20261124);independent[name]={teams:jobs.map(j=>r[j.key]),sum:jobs.reduce((s,j)=>s+r[j.key].cosmo.top,0)};}
   const comparisons=Object.fromEntries(['reduced','search'].map(name=>[name,{differencePct:(independent[name].sum/independent.full.sum-1)*100,ci95:interval(independent.full.teams.map(r=>r.scores),independent[name].teams.map(r=>r.scores))}]));
   save('small',{keys,conditions:state.conditions,full,reduced,selected:chosen,structuralLossPct:(1-reduced.sum/full.sum)*100,searchLossPct:(1-selectedScore/full.sum)*100,independent,comparisons,seconds:(performance.now()-start)/1000,games:T.games,audit:search.representative});
  }else throw Error('unknown validation mode');
 }finally{pool.close();T.close();}
}
async function runValidation(options){
 const raw={};await GS.runPhase({...options,onResult:(key,result)=>{raw[key]=result;}}).promise;
 for(const j of options.jobs){const r=raw[j.key],values=r?.cosmo?r.scores:r?.progs;if(!Array.isArray(values)||values.length!==options.runs||values.some(x=>!Number.isFinite(x)))throw Error('independent per-run scores missing: '+j.key);}
 return raw;
}
module.exports={runValidation,interval};
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
