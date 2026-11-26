const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process');
const J=require('../placement_search'),C=require('../cosmo_search');
const plain=x=>JSON.parse(JSON.stringify(x));
function load(source){const ctx={module:{exports:{}},require:n=>require('../'+n)};vm.runInNewContext(source,ctx);return ctx.module.exports;}
const old=load(cp.execFileSync('git',['show','f4afb12:placement_search.js'],{encoding:'utf8'}));
async function check(api=J){
  const a={v:10},b={v:11};
  assert.equal(api.incumbentWithMargin(a,b,x=>x.v,1),a);
  assert.equal(api.incumbentWithMargin(a,b,x=>x.v,.9),b);
  const interleaved=['A1','B1','A2','B2','A3'];
  assert.deepEqual(plain(api.perGroup(interleaved,x=>x[0],2,false)),interleaved.slice(0,4));
  for(const enabled of [false,true])for(const auto of [false,true])for(const mode of ['top','mean']){
    const teams=['x','y'].map((boss,i)=>{const keys=['a','b','c','d'].map(k=>k+i);return {boss,keys,order:keys,leaderKey:keys[0]};});
    const run=async mod=>{
      const trace=[];
      const out=await mod.cosmo({teams,mode,level:2,maxLevel:4,auto,breaks:[{name:'cube',level:2}],runs:4,probeRuns:2,settings:{enabled,keep:2},boundaries:{x:[3],y:[1]},
        makeJob:(t,l,b,p)=>C.bossJobs({topQ:.2},t.boss,l,[t.keys],{}, {},b,p)[0],
        run:async(jobs,n,seed,msg)=>{trace.push(plain({jobs,n,seed,msg}));return Object.fromEntries(jobs.map(j=>{
          const v=seed===8?100+j.level:100-j.level+(j.leaderKey.startsWith('d')?10:0)+(j.boss==='y'?.5:0)+(j.brk?.level||0)/2;
          return [j.key,{prog:.8,progs:Array(n).fill(.8),via:{coop:1},cosmo:{top:v,mean:v/2,clear:.5,n}}];
        }));}
      });
      return plain({out,trace});
    };
    const actual=await run(api);assert.deepEqual(actual,await run(old));
    if(auto)assert(actual.out.moved>0,'must exercise changed-level rerace');
  }
}
(async()=>{
  await check();
  const src=fs.readFileSync(require.resolve('../placement_search'),'utf8');
  for(const [from,to] of [['j.level!==byGroup.get(group(j)).level','false'],['groups.get(k).length<keep','groups.get(k).length<1'],['>margin?candidate', '>=margin?candidate']]){
    assert(src.includes(from));await assert.rejects(()=>check(load(src.replace(from,to))),{code:'ERR_ASSERTION'});
  }
  console.log('PASS joint placement: 8 baseline traces/results, moved rerace, incumbent margin, 3 mutations');
})().catch(e=>{console.error(e);process.exitCode=1;});
