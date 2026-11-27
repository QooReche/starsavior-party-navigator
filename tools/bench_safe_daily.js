// Synthetic daily search comparison against the pinned deployment, never account data.
const assert=require('node:assert/strict'),cp=require('node:child_process'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {performance}=require('node:perf_hooks');
const ROOT=path.resolve(__dirname,'..'),{scenario}=require('../tests/guild_daily_test');
function baseline(ref='1197383',transform=x=>x){
  const modules=new Map();
  function load(file){
    file=file.replace(/^\.\//,'').replace(/\.js$/,'')+'.js';
    if(!['guild_daily.js','guild_search.js'].includes(file))return require(path.join(ROOT,file));
    if(modules.has(file))return modules.get(file);
    const source=transform(cp.execFileSync('git',['-c','safe.directory='+ROOT.replaceAll('\\','/'),'show',ref+':'+file],{cwd:ROOT,encoding:'utf8'}),file);
    const c={module:{exports:{}},require:load,setTimeout,clearTimeout,console};
    vm.runInNewContext(source,c,{filename:'1197383/'+file});modules.set(file,c.module.exports);return c.module.exports;
  }
  return load('guild_daily');
}
const plain=x=>JSON.parse(JSON.stringify(x));
function teamResults(out){return plain({teams:out.teams,sum:out.sum,mean:out.mean,seals:out.seals,growth:out.growth&&teamResults(out.growth)});}
function variant(daily,changed){return {...daily,search(cx){
  if(changed&&cx.growthResults){cx={...cx,growthResults:structuredClone(cx.growthResults)};cx.growthResults.u00.stats.atk+=17;}
  return daily.search(cx);
}};}
async function sample(daily,changed=false){
  const start=performance.now();
  const r=await scenario({daily:variant(daily,changed),count:8,growth:true,
    scoreFn:t=>1000+t.party.units.reduce((s,u)=>s+u.stats_override.atk,0)+(t.options.guild.level===1?20:0),
    viaFn:t=>({trigger:t.party.units[0].stats_override.atk/100,coop:0})});
  return {ms:performance.now()-start,games:r.trace.reduce((s,m)=>s+m.teams.length*m.n_runs,0),out:teamResults(r.out)};
}
async function main(){
  const ref=process.argv.includes('--compare')?process.argv[process.argv.indexOf('--compare')+1]:'1197383';
  const before=baseline(ref),after=require('../guild_daily'),reports=[];
  for(const changed of [false,true]){
    const a=[],b=[];let counts;
    for(let i=0;i<4;i++){
      let x,y;
      if(i%2){y=await sample(after,changed);x=await sample(before,changed);}
      else{x=await sample(before,changed);y=await sample(after,changed);}
      assert.deepEqual(y.out,x.out,'complete selected team results, including SE/via filtering and signatures');
      if(i){a.push(x.ms);b.push(y.ms);}counts=[x.games,y.games];
    }
    reports.push({changed,baseline_ms:a.sort((a,b)=>a-b)[1],current_ms:b.sort((a,b)=>a-b)[1],games:counts});
  }
  console.log(JSON.stringify(reports,null,2));
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={baseline,teamResults,sample};
