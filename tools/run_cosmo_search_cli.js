// Actual browser search policy with native Python worker transport. Account input is never copied.
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process'),readline=require('node:readline');
const C=require('../cosmo_search.js'),GS=require('../guild_search.js'),G=require('../data/cosmo_raid.json');
async function run({roster,results,mode='learned',metric='top',level=-1,workers=2,python='python',seed=0,breaks=[],standard=false,onPhase=()=>{},onLists,settings=null,forbidFallback=false}){
 if(!Number.isInteger(workers)||workers<1||workers>4)throw Error('workers must be 1..4');
 const S=structuredClone(settings||G.search);S.learned.value=mode==='learned';S.combine.show=10;
 const children=new Set(),phases=[],start=performance.now();let games=0,active=null;
 const oldRun=GS.runPhase,oldParty=GS.party;
 if(standard)GS.party=(...args)=>{const p=oldParty(...args);p.spec={units:p.order.map(key=>({key,build:'standard',...(results[key].override?{stats_override:results[key].override,stats_final:true,power:results[key].power}:{})})),leader:p.spec.leader};return p;};
 GS.runPhase=o=>{const began=performance.now();games+=o.jobs.length*o.runs;const h=oldRun({...o,seed:seed*100+o.seed});active=h;return {...h,promise:h.promise.then(r=>{phases.push({teams:o.jobs.length,runs:o.runs,seconds:(performance.now()-began)/1000});return r;})};};
 function makeWorker(){const child=spawn(python,['-X','utf8','-I',path.join(__dirname,'bench_cosmo_search.py'),'--worker'],{stdio:['pipe','pipe','inherit']});children.add(child);
  const w={onmessage:null,onerror:null,postMessage:m=>child.stdin.write(JSON.stringify(m)+'\n'),terminate(){children.delete(child);child.kill();}};
  readline.createInterface({input:child.stdout}).on('line',line=>{try{w.onmessage?.({data:JSON.parse(line)});}catch(e){w.onerror?.(e);}});
  child.on('error',e=>w.onerror?.(e));child.on('exit',code=>{if(children.has(child))w.onerror?.(Error('worker exit '+code));});return w;}
 try{const result=await C.search({S,bosses:G.season.bossOrder,bossName:key=>G.bosses.find(b=>b.key===key)?.name||key,results,roster,level,levelMax:Math.min(...G.bosses.map(b=>b.levels.length)),mode:metric,workers,makeWorker,stage:'코스모 게이트',base:'',breaks,boundaries:Object.fromEntries(G.bosses.map(b=>[b.key,require('../party_placement.js').boundaries(b.levels)])),sampleSeed:20261119+seed*100,
   onLists,onPhase:(msg,total,info)=>{if(forbidFallback&&msg.includes('전수 확인'))throw Error('59명 전수 금지: 감사 복귀가 필요함');onPhase(msg,total,info);}});
  return {mode,metric,seed,pool:result.pool,season:G.season.id,games,seconds:(performance.now()-start)/1000,phases,result};
 }catch(e){e.games=games;e.seconds=(performance.now()-start)/1000;throw e;}
 finally{active?.cancel();for(const p of children)p.kill();GS.runPhase=oldRun;GS.party=oldParty;}
}
async function main(){const args=process.argv.slice(2),get=(k,f)=>{const i=args.indexOf('--'+k);return i<0?f:args[i+1];};
 if(args.includes('--help')){console.log('node tools/run_cosmo_search_cli.js --myinfo <JSON> --output <private JSON> [--lists-output <private JSON>] --mode learned|legacy --metric top|mean --level auto|N --workers 1..4 --python python');return;}
 const input=get('myinfo'),output=get('output');if(!input||!output)throw Error('--myinfo and --output required');
 const mode=get('mode','learned'),metric=get('metric','top'),lv=get('level','auto');if(!['learned','legacy'].includes(mode)||!['top','mean'].includes(metric)||!(lv==='auto'||/^\d+$/.test(lv)))throw Error('invalid mode/metric/level');
 // Use the same published roster/uid mapping as the page (including name aliases).
 const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8'),match=html.match(/const D=(\{[^\n]+\});/);if(!match)throw Error('build index.html first');const D=JSON.parse(match[1]);
 const info=JSON.parse(fs.readFileSync(path.resolve(input),'utf8').replace(/^\uFEFF/,'')),growth=require('../data/growth.json'),profile=require('../myinfo_reco.js').profile(info,D.roster,growth,'cosmo');
 const outputPath=path.resolve(output),root=fs.realpathSync(path.resolve(__dirname,'..')).toLowerCase();
 const canonical=(fs.existsSync(outputPath)?fs.realpathSync(outputPath):path.join(fs.realpathSync(path.dirname(outputPath)),path.basename(outputPath))).toLowerCase();
 if(canonical===fs.realpathSync(path.resolve(input)).toLowerCase()||canonical===root||canonical.startsWith(root+path.sep))throw Error('계정 결과는 입력과 다른 저장소 밖 경로에 저장해야 함');
 const listsOutput=get('lists-output');
 if(listsOutput){const dest=path.resolve(listsOutput),real=(fs.existsSync(dest)?fs.realpathSync(dest):path.join(fs.realpathSync(path.dirname(dest)),path.basename(dest))).toLowerCase();
  if(real===fs.realpathSync(path.resolve(input)).toLowerCase()||real===canonical||real===root||real.startsWith(root+path.sep))throw Error('후보 목록은 입력·결과와 다른 저장소 밖 경로에 저장해야 함');}
 const levels=require('../myinfo_import.js').mapBreak(info)||{},owned=Object.entries(levels).filter(([name])=>D.cfg.breakSupported.includes(name)).map(([name,level])=>({name,level}));
 if(lv!=='auto'&&+lv>D.cosmoRaid.levelMax)throw Error('난이도 범위를 벗어남');
 const report=await run({roster:D.roster,results:profile.results,mode,metric,level:lv==='auto'?-1:+lv,workers:+get('workers','2'),python:get('python','python'),seed:+get('seed','0'),breaks:JSON.parse(get('breaks',JSON.stringify(owned))),onLists:listsOutput?(lists=>fs.writeFileSync(path.resolve(listsOutput),JSON.stringify(lists))):undefined,onPhase:(m,t)=>console.error(m,t)});
 const candidates=report.result.rows.map(r=>({...r,teams:r.teams.map(t=>({...t,leader:t.leaderKey||t.order[0],front:t.order.slice(0,2),back:t.order.slice(2)}))}));
 delete report.result.growthOwned;fs.writeFileSync(outputPath,JSON.stringify({...report,best:candidates[0],candidates},null,2));console.log(JSON.stringify({output:outputPath,games:report.games,seconds:report.seconds,sum:candidates[0]?.sum}));
}
module.exports={run};if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
