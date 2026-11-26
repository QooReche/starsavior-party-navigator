// Exercise the opt-in guild placement/audit path, which the default freeze leaves off.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process');
const current=require('../guild_planner'),G=require('./guild_fixture')(30111),V=require('../guild_view');
const plain=x=>JSON.parse(JSON.stringify(x)),ctx={module:{exports:{}},require:n=>require('../'+n)};
vm.runInNewContext(cp.execFileSync('git',['show','f4afb12:guild_planner.js'],{encoding:'utf8'}),ctx);
const old=ctx.module.exports;
const roster=Array.from({length:9},(_,i)=>({key:'u'+i,cls:['캐스터','디펜더','서포터'][i%3],placementTraits:[]}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:100-i,stats:{hp:100+i,def:i,spd:10-i},combat:{}}]));
async function run(planner,enabled){
  const S=structuredClone(G.search),trace=[];S.newSearch=true;S.execution={chunk:8};S.placement={...S.placement,enabled,baseline:true,auditTeams:4};
  Object.assign(S.learned,{S:20,m:1,K:12,M:1,A:6,epochs:3,minCorrelation:-1,missThreshold:0});
  S.screen2={keep:4,runs:3};S.finalists=1;S.final={...S.final,runs:4,levels:[2,4,6]};
  const out=await planner.search({S,G,V,results,roster,tiers:[0,0,0,0],breaks:[{name:'cube',level:2}],workers:1,stage:'synthetic',base:'',
    makeWorker:()=>({terminate(){},postMessage(m){trace.push(plain(m));setImmediate(()=>{
      for(const t of m.teams){const keys=t.party.units.map(u=>u.key),g=t.options.guild,b=t.options.break_skill;
        const bonus=keys[t.party.leader]===keys.slice().sort().at(-1)?.3:0;
        const score=Math.max(.05,Math.min(.99,.45+keys.reduce((n,k)=>n+Number(k[1]),0)%13/100+bonus+(g.support==='gust'?.08:0)+(b?.level===2?.04:0)-Math.abs(g.level-(m.seed===7?0:4))*.1));
        const progs=Array.from({length:m.n_runs},(_,i)=>score+.01*(i%2));
        this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{prog:progs.reduce((a,b)=>a+b)/progs.length,progs,clear:progs.filter(p=>p>=1).length/progs.length,n:m.n_runs,via:{coop:.2}}}});
      }this.onmessage({data:{type:'done',id:m.id}});
    });}})});
  for(const m of trace){delete m.id;delete m.requestId;delete m.jobId;}
  return plain({trace,out});
}
(async()=>{
  for(const enabled of [false,true]){const actual=await run(current,enabled);assert.deepEqual(actual,await run(old,enabled));
    assert(actual.out.rows[0].prog>0);if(enabled){assert(actual.out.representative.sampled>0);assert(actual.out.representative.misses>0);assert(actual.out.placement.moved>0);}}
  console.log('PASS guild opt-in baseline trace: placement off/on, audit rescue/expansion, changed-level rerace, results/seeds/runs/order');
})().catch(e=>{console.error(e);process.exitCode=1;});
