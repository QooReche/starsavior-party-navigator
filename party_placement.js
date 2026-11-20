// Candidate generation only: tactics are hypotheses; simulation chooses the winner.
(function(root){
  'use strict';
  const VERSION='placement-ehp-joint-v1';
  const id=keys=>keys.slice().sort().join('+');
  const stats=(results,k)=>results[k]?.stats||{};
  const ehp=s=>(s.hp||0)*(1+(s.def||0)/3000);
  function baseline(keys,results){
    const order=keys.slice().sort((a,b)=>ehp(stats(results,b))-ehp(stats(results,a))||a.localeCompare(b));
    const leaderKey=keys.slice().sort((a,b)=>(stats(results,b).spd||0)-(stats(results,a).spd||0)||a.localeCompare(b))[0];
    return {order,leaderKey};
  }
  function validate(keys,p){
    if(keys.length!==4||new Set(keys).size!==4||p.order?.length!==4||new Set(p.order).size!==4||!p.order.every(k=>keys.includes(k))||!keys.includes(p.leaderKey))throw Error('배치에는 같은 4명과 리더가 필요함');
    return p;
  }
  function party(keys,results,placement=baseline(keys,results)){
    const {order,leaderKey}=validate(keys,placement);
    return {keys:keys.slice(),order:order.slice(),leaderKey,spec:{units:order.map(key=>{
      const r=results[key];return r?{key,build:'none',stats_override:r.stats,stats_final:true,power:r.power,myinfo_combat:r.combat}:{key,build:'standard'};
    }),leader:order.indexOf(leaderKey)}};
  }
  function variants(keys,results,traits={}){
    const base=baseline(keys,results),out=[base,{order:base.order.slice().reverse(),leaderKey:base.leaderKey}];
    for(const trait of ['stealth','taunt']){
      const order=base.order.slice().sort((a,b)=>Number(!!traits[b]?.includes(trait))-Number(!!traits[a]?.includes(trait)));
      out.push({order,leaderKey:base.leaderKey});
    }
    return [...new Map(out.map(p=>[p.order.join('|')+'|'+p.leaderKey,p])).values()];
  }
  function all(keys,full=false){
    const k=keys.slice().sort(),orders=[];
    if(full){const perm=(rest,out)=>{if(!rest.length){orders.push(out);return;}rest.forEach((x,i)=>perm(rest.filter((_,j)=>i!==j),[...out,x]));};perm(k,[]);}
    else for(let a=0;a<4;a++)for(let b=a+1;b<4;b++)orders.push([k[a],k[b],...k.filter((_,i)=>i!==a&&i!==b)]);
    return orders.flatMap(order=>k.map(leaderKey=>({order:order.slice(),leaderKey})));
  }
  const executionKey=(keys,p)=>JSON.stringify([VERSION,id(keys),p.order,p.leaderKey]);
  const boundaries=levels=>levels.filter((l,i)=>JSON.stringify(l.effects||[])!==JSON.stringify(levels[i-1]?.effects||[])).map(l=>l.level);
  function reorder(spec,p){const byKey=new Map(spec.units.map(u=>[u.key,u]));validate([...byKey.keys()],p);return {units:p.order.map(k=>byKey.get(k)),leader:p.order.indexOf(p.leaderKey)};}
  function best(jobs,res,compare,valid=Boolean){
    const rows=jobs.filter(j=>valid(res[j.key])).map(j=>({...j,result:res[j.key]}));
    if(rows.length!==jobs.length)throw Error('배치 비교 결과가 누락됨');
    return rows.sort((a,b)=>compare(a.result,b.result)||(a.level-b.level)||a.key.localeCompare(b.key));
  }
  // Every arrangement gets a short run. Only complete results may enter later rounds.
  async function race({jobs,run,compare,valid,runs=40,screenRuns=2,keep=2,seed=2}){
    const first=await run(jobs,Math.min(runs,screenRuns),seed);
    let ranked=best(jobs,first,compare,valid);
    if(runs<=screenRuns)return {ranked,results:first};
    const finalists=ranked.slice(0,keep),last=await run(finalists,runs,seed+1);
    ranked=best(finalists,last,compare,valid);
    return {ranked,results:last};
  }
  // Probe leaders/rows and both sides of each newly enabled effect, plus best levels.
  function levels(probes,max,boundaries=[],top=2){
    const ranked=probes.slice().sort((a,b)=>b.score-a.score||a.level-b.level);
    const chosen=new Set([...new Set(ranked.map(x=>x.level))].slice(0,top));
    for(const l of boundaries)for(const x of [l-1,l])if(x>=0&&x<=max)chosen.add(x);
    return [...chosen].sort((a,b)=>a-b);
  }
  const api={VERSION,id,ehp,baseline,validate,party,variants,all,executionKey,reorder,best,race,levels,boundaries};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PartyPlacement=api;
})(typeof window!=='undefined'?window:globalThis);
