// Candidate generation only: tactics are hypotheses; simulation chooses the winner.
(function(root){
  'use strict';
  const VERSION='placement-ehp-joint-v1';
  const {teamId:id}=typeof module!=='undefined'&&module.exports?require('./ui_shared.js'):root.UiShared;
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
  // incumbent(선택) = 지금 쓰는 자리 job. 예선 순위와 무관하게 결선에 항상 넣는다(같은 판 수·시드로 맞대기 위해).
  // decide(선택) = (결선 jobs, 결선 결과) → 고른 job. 없으면 결선 1등. 반환 pick = 최종 선택.
  // raceMany = 여러 팀(groups: [{jobs, incumbent?}])을 단계마다 한 번에 run 에 넘긴다(작업자를 놀리지 않게). job.key 는 팀끼리 겹치면 안 됨.
  // checkRuns·stop(선택) = 결선 2단계: 먼저 checkRuns 판을 돌려 stop(결선 jobs, 결과)이 참인 팀은 거기서 끝내고(바꿀 근거 없음),
  //   나머지만 runs 판까지 «이어» 돌린다 — run(jobs, n, seed, prior) 의 prior = 앞 단계 결과(같은 시드로 이어 붙여 runs 판 한 번과 같게). 판정(decide)은 runs 판 결과로만.
  async function raceMany({groups,run,compare,valid,runs=40,screenRuns=2,keep=2,seed=2,decide=null,checkRuns=0,stop=null}){
    const all=groups.flatMap(g=>g.jobs);
    if(new Set(all.map(j=>j.key)).size!==all.length)throw Error('배치 비교 job 키가 겹침');
    const first=await run(all,Math.min(runs,screenRuns),seed);
    const screened=groups.map(g=>best(g.jobs,first,compare,valid));
    if(runs<=screenRuns)return screened.map(ranked=>({ranked,results:first,pick:ranked[0]}));
    const finals=groups.map((g,i)=>{const f=screened[i].filter(j=>!g.incumbent||j.key!==g.incumbent.key).slice(0,keep);if(g.incumbent)f.push(g.incumbent);return f;});
    let last,stopped=finals.map(()=>false);
    if(checkRuns>0&&checkRuns<runs&&stop){
      const mid=await run(finals.flat(),checkRuns,seed+1);
      stopped=finals.map(f=>!!stop(f,mid));
      const more=finals.filter((f,i)=>!stopped[i]).flat();
      last={...mid,...(more.length?await run(more,runs-checkRuns,seed+1,mid):{})};
    }else last=await run(finals.flat(),runs,seed+1);
    return finals.map((f,i)=>{const ranked=best(f,last,compare,valid);
      return {ranked,results:last,stopped:stopped[i],pick:stopped[i]?(f.find(j=>j===groups[i].incumbent)||ranked[0]):decide?decide(f,last):ranked[0]};});
  }
  async function race({jobs,incumbent=null,...rest}){return (await raceMany({groups:[{jobs,incumbent}],...rest}))[0];}
  // Probe leaders/rows and both sides of each newly enabled effect, plus best levels.
  function levels(probes,max,boundaries=[],top=2){
    const ranked=probes.slice().sort((a,b)=>b.score-a.score||a.level-b.level);
    const chosen=new Set([...new Set(ranked.map(x=>x.level))].slice(0,top));
    for(const l of boundaries)for(const x of [l-1,l])if(x>=0&&x<=max)chosen.add(x);
    return [...chosen].sort((a,b)=>a-b);
  }
  // 일반 자동 추천 끝의 자리·리더 비교(11/23). 결과 r = 웹 요약({t60?,clear,prog,progs}).
  // 24개 중 최대값을 고르면 운으로 부푼다(승자의 저주) → 규칙 자리와 같은 판 수·시드로 비교해 «여유폭»을 넘을 때만 바꾼다.
  // 여유폭 = max(1%p, z × 표준오차), z=2.4(대안 최대 3개의 다중 비교 보정 근사). 목표 지표가 조금이라도 나빠지면 바꾸지 않는다.
  const goalOf=r=>r.t60??r.clear;
  function recoCompare(a,b){return goalOf(b)-goalOf(a)||b.clear-a.clear||(b.prog||0)-(a.prog||0);}
  // 같은 시드로 돌린 두 결과는 판끼리 짝지어 비교한다(짝 차이의 표준오차가 독립 표본식보다 작다 — 같은 판 수로 더 작은 이득도 잡음).
  //   판별 클리어 = progs 가 1(모든 웨이브 처치). N턴 내 클리어(t60)는 판별 값이 없어 독립 표본식을 쓴다(보수적).
  const pairOk=(a,b)=>Array.isArray(a.progs)&&Array.isArray(b.progs)&&a.progs.length===b.progs.length&&a.progs.length>0;
  function pairedGain(xs,ys,z){const d=xs.map((x,i)=>x-ys[i]),n=d.length,m=d.reduce((s,x)=>s+x,0)/n;
    const sd=Math.sqrt(d.reduce((s,x)=>s+(x-m)*(x-m),0)/Math.max(1,n-1));return {m,thr:Math.max(0.01,z*sd/Math.sqrt(n))};}
  function recoBetter(a,b,z=2.4){
    const n=Math.min(a.n||0,b.n||0)||(a.progs?.length||0);if(!n)return false;
    const indep=(p,q)=>({m:p-q,thr:Math.max(0.01,z*Math.sqrt((p*(1-p)+q*(1-q))/n))});
    const paired=pairOk(a,b),won=x=>x.progs.map(v=>v>=0.99995?1:0);
    const clearGain=paired?pairedGain(won(a),won(b),z):indep(a.clear,b.clear);
    const steps=[a.t60!=null&&b.t60!=null?indep(a.t60,b.t60):clearGain,...(a.t60!=null&&b.t60!=null?[clearGain]:[])];
    for(const g of steps){if(g.m>g.thr)return true;if(g.m<0)return false;}
    if(!paired)return false;
    const g=pairedGain(a.progs,b.progs,z);return g.m>g.thr;
  }
  // 결선 1단계에서 멈출지: 1등이 규칙 자리이거나, 약한 기준(zStop)으로도 규칙 자리보다 낫다는 근거가 없으면 멈춘다(교체 판정은 하지 않음 — 2단계에서만)
  function recoStop(finals,res,zStop=1.0){
    const rule=finals.find(j=>j.rule);if(!rule||!res[rule.key])return false;
    const rows=finals.filter(j=>res[j.key]&&Number.isFinite(res[j.key].clear)).sort((a,b)=>recoCompare(res[a.key],res[b.key])||Number(!!b.rule)-Number(!!a.rule));
    return rows[0].rule||!recoBetter(res[rows[0].key],res[rule.key],zStop);
  }
  // finals = [{key,p,rule?}], res[key] = 결과. 규칙 자리(rule:true)가 반드시 있어야 한다. 반환 = 고른 job(바꿀 근거가 없으면 규칙 자리)
  function recoDecide(finals,res,z=2.4){
    const rule=finals.find(j=>j.rule);if(!rule||!res[rule.key])throw Error('규칙 자리 결과가 없음');
    const rows=finals.filter(j=>res[j.key]&&Number.isFinite(res[j.key].clear));
    rows.sort((a,b)=>recoCompare(res[a.key],res[b.key])||Number(!!b.rule)-Number(!!a.rule)||a.key.localeCompare(b.key));
    const top=rows[0];return top.rule||!recoBetter(res[top.key],res[rule.key],z)?rule:top;
  }
  const api={VERSION,id,ehp,baseline,validate,party,variants,all,executionKey,reorder,best,race,raceMany,levels,boundaries,recoCompare,recoBetter,recoDecide,recoStop};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PartyPlacement=api;
})(typeof window!=='undefined'?window:globalThis);
