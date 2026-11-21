// Casebook search check driver: production JS search policy (cosmo_search / guild_planner) with native
// Python workers (tools/casebook_search_check.py --worker). Public standard builds, whole roster, no account.
// node tools/casebook_search_check.js <cosmo|guild> <out.json> <catalog.json> <workers> <python> [seasonData] [level] [breaksJSON]
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib'),{spawn}=require('node:child_process'),readline=require('node:readline');
const root=path.resolve(__dirname,'..');
const GS=require('../guild_search.js'),C=require('../cosmo_search.js'),P=require('../party_placement.js');
const [kind,out,catalogFile,workersText,python,seasonData='',levelText='18',breaksText='[]']=process.argv.slice(2);
const workers=+workersText;
const D=JSON.parse(fs.readFileSync(path.join(root,'index.html'),'utf8').match(/const D=(\{[^\n]+\});/)[1]);
const catalog=JSON.parse(fs.readFileSync(catalogFile,'utf8'));
const results=Object.fromEntries(catalog.map(r=>[r.key,r]));
const breaks=JSON.parse(breaksText);
// Standard builds: same transport rewrite as tools/run_cosmo_search_cli.js --standard.
const oldParty=GS.party;
GS.party=(...args)=>{const p=oldParty(...args);p.spec={units:p.order.map(key=>({key,build:'standard'})),leader:p.spec.leader};return p;};
const children=new Set();
function makeWorker(){
 const args=['-X','utf8','-I',path.join(__dirname,'casebook_search_check.py'),'worker'];if(seasonData)args.push('--data',seasonData);
 const child=spawn(python,args,{stdio:['pipe','pipe','inherit'],cwd:root});children.add(child);
 const w={onmessage:null,onerror:null,postMessage:m=>child.stdin.write(JSON.stringify(m)+'\n'),terminate(){children.delete(child);child.kill();}};
 readline.createInterface({input:child.stdout}).on('line',line=>{try{w.onmessage?.({data:JSON.parse(line)});}catch(e){w.onerror?.(e);}});
 child.on('error',e=>w.onerror?.(e));child.on('exit',code=>{if(children.has(child))w.onerror?.(Error('worker exit '+code));});
 return w;
}
// Trace every phase: which teams were evaluated, with how many runs and what summary.
const phases=[],oldRun=GS.runPhase,start=performance.now();let games=0;
GS.runPhase=o=>{const i=phases.length,began=performance.now();games+=o.jobs.length*o.runs;
 const h=oldRun({...o,workers:kind==='guild'?o.workers:workers});
 return {...h,promise:h.promise.then(res=>{
  phases.push({i,runs:o.runs,seed:o.seed,teams:o.jobs.length,seconds:(performance.now()-began)/1000,
   jobs:o.jobs.map(j=>{const r=res[j.key]||{};return {boss:j.boss||null,keys:j.keys,order:j.order,leaderKey:j.leaderKey||j.order?.[0],level:j.level,
    brk:(j.brk||j.options?.break_skill)?.name||null,sup:j.sup||j.options?.guild?.support||null,cosmo:r.cosmo||null,prog:r.prog,clear:r.clear,n:r.n};})});
  console.error(`phase ${i}: ${o.jobs.length} teams x ${o.runs} runs, ${((performance.now()-began)/1000).toFixed(0)}s`);
  return res;})};};
const onPhase=(m,t)=>console.error(m,t);
async function main(){
 let result,meta;
 if(kind==='cosmo'){
  const G=seasonData?JSON.parse(fs.readFileSync(seasonData,'utf8')):require('../data/cosmo_raid.json');
  const S=structuredClone(require('../data/cosmo_raid.json').search);   // current production search settings
  S.combine.show=10;
  const level=+levelText;
  result=await C.search({S,bosses:G.season.bossOrder,bossName:k=>k,results,roster:D.roster,level,levelMax:Math.min(...G.bosses.map(b=>b.levels.length)),mode:S.defaultMode||'top',
   workers,makeWorker,stage:'코스모 게이트',base:'',breaks,boundaries:Object.fromEntries(G.bosses.map(b=>[b.key,P.boundaries(b.levels)])),sampleSeed:20261119,onPhase});
  meta={season:G.season.id,bosses:G.season.bossOrder,level,settings:S};
 }else{
  const G=D.guild,S={...G.search,banCoop:true},V=require('../guild_view.js');
  const tiers=V.normSel(G,null).tiers;
  result=await require('../guild_planner.js').search({S,G,V,results,roster:D.roster,tiers,breaks,stage:'guild/BFB/길드 방어전 EX스테이지',base:'',workers:2,makeWorker,onPhase});
  meta={season:G.season.id,tiers,settings:S,pool:result.pool,combos:result.combos};
 }
 delete result.growthOwned;
 fs.writeFileSync(out,zlib.gzipSync(JSON.stringify({kind,meta,games,seconds:(performance.now()-start)/1000,result,phases})));
 console.error('done',kind,'games',games,'seconds',((performance.now()-start)/1000).toFixed(0));
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>{GS.runPhase=oldRun;for(const c of children)c.kill();});
