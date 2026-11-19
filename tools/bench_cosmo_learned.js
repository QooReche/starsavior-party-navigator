const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {run}=require('./run_cosmo_search_cli.js'),G=require('../data/cosmo_raid.json');
const [out,w,python,sizes='20,26,32,59',seeds='0,1']=process.argv.slice(2);
const D=JSON.parse(fs.readFileSync(path.join(__dirname,'../index.html'),'utf8').match(/const D=(\{[^\n]+\});/)[1]);
const catalog=JSON.parse(fs.readFileSync(path.join(out,'catalog.json'),'utf8'));
const usable=new Map(D.roster.map(r=>[r.key,r]));
const roster=catalog.filter(r=>usable.has(r.key)).map(r=>({...r,...usable.get(r.key)})).sort((a,b)=>a.key.localeCompare(b.key));
const id=r=>r.teams.map(t=>t.boss+':'+t.keys.slice().sort().join('+')).join('/');
async function main(){const reports=[];
 for(const size of sizes.split(',').map(Number))for(const seed of (size===59?[0]:seeds.split(',').map(Number))){
  if(roster.length<size)throw Error('roster too small: '+roster.length);
  const rr=structuredClone(roster.slice(0,size));
  // Elisa keeps her support skills with 35% HP/ATK/DEF and power. No real-account data.
  const support=rr.find(r=>r.key==='elisa');if(!support||support.cls!=='서포터')throw Error('support required');
  support.override=Object.fromEntries(Object.entries(support.stats).map(([k,v])=>[k,['atk','def','hp'].includes(k)?Math.round(v*.35):v]));support.power=Math.round(support.power*.35);
  const results=Object.fromEntries(rr.map(r=>[r.key,r]));
  const pair={size,seed,support:support.key,lowSupportPower:support.power};
  for(const mode of size===59?['learned']:['legacy','learned']){
   const file=path.join(out,`${size}-${seed}-${mode}.json`),signature=crypto.createHash('sha256').update(JSON.stringify({rr,G:G.search,source:['cosmo_search.js','cosmo_learned.js','guild_search.js'].map(f=>fs.readFileSync(path.join(__dirname,'..',f),'utf8'))})).digest('hex');
   if(fs.existsSync(file)){const old=JSON.parse(fs.readFileSync(file,'utf8'));if(old.signature!==signature)throw Error('changed benchmark inputs: use new output directory');pair[mode]=old;continue;}
   const start=Date.now();console.log(JSON.stringify({size,seed,mode,start:true}));
   try{const report=await run({roster:rr,results,workers:+w,python,seed,mode,standard:true,level:6,metric:'top',forbidFallback:size===59,onPhase:(msg,total)=>console.log(JSON.stringify({size,seed,mode,msg,total}))});
    report.signature=signature;delete report.result.growthOwned;fs.writeFileSync(file,JSON.stringify(report));pair[mode]=report;
   }catch(e){if(size!==59)throw e;pair[mode]={error:e.message,games:e.games,seconds:e.seconds||(Date.now()-start)/1000};fs.writeFileSync(file,JSON.stringify({...pair[mode],signature}));}
  }
  if(pair.legacy&&pair.learned.result){pair.loss=(pair.legacy.result.rows[0].sum-pair.learned.result.rows[0].sum)/pair.legacy.result.rows[0].sum;pair.match=id(pair.legacy.result.rows[0])===id(pair.learned.result.rows[0]);pair.supportUsed=Object.fromEntries(['legacy','learned'].map(m=>[m,pair[m].result.rows[0].teams.some(t=>t.keys.includes(support.key))]));}
  reports.push(pair);fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(reports,null,2));
  console.log(JSON.stringify({size,seed,loss:pair.loss,match:pair.match,legacy:pair.legacy&&{games:pair.legacy.games,seconds:pair.legacy.seconds},learned:{games:pair.learned.games,seconds:pair.learned.seconds,error:pair.learned.error},audit:pair.learned.result?.audit}));
 }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
