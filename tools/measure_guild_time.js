// Full guild policy on the shared executor, native engine, <=2 workers.
// Usage: node tools/measure_guild_time.js ACCOUNT PRIVATE_DIR old|new [SETTINGS_JSON]
// Each reply is journaled. A resumed run is useful for quality, not a fresh timing.
'use strict';
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),readline=require('node:readline'),crypto=require('node:crypto');
const ROOT=path.resolve(__dirname,'..'),GS=require('../guild_search'),Planner=require('../guild_planner'),V=require('../guild_view');
const read=f=>JSON.parse(fs.readFileSync(f,'utf8').replace(/^\uFEFF/,''));
const hash=x=>crypto.createHash('sha256').update(typeof x==='string'||Buffer.isBuffer(x)?x:JSON.stringify(x)).digest('hex');
function privateDir(dir){fs.mkdirSync(dir,{recursive:true});const real=fs.realpathSync(dir),rel=path.relative(fs.realpathSync(ROOT),real);if(!rel||(!rel.startsWith('..'+path.sep)&&!path.isAbsolute(rel)))throw Error('output must be outside repository');return real;}
function save(file,value){fs.writeFileSync(file+'.tmp',JSON.stringify(value,null,2)+'\n');fs.renameSync(file+'.tmp',file);}
function context(input){
 const D=JSON.parse(fs.readFileSync(path.join(ROOT,'index.html'),'utf8').match(/const D=(\{[^\n]+\});/)[1]),info=read(input);
 const profile=require('../myinfo_reco').profile(info,D.roster,require('../data/growth.json'),'op');
 const breaks=Object.entries(require('../myinfo_import').mapBreak(info)||{}).filter(([n])=>D.cfg.breakSupported.includes(n)).map(([name,level])=>({name,level}));
 const G=D.guild,c=D.contents.find(c=>c.key==='guild'),st=c.stages.find(s=>parseInt(s.name,10)===G.steps.find(s=>s.ex).step);
 return {G,S:structuredClone(G.search),V,results:profile.results,roster:D.roster,tiers:[0,0,0,0],breaks,stage:'guild/'+st.tab+'/'+st.name,base:'',workers:2};
}
function instrument(dir,pins){
 const pinFile=path.join(dir,'pins.json'),journal=path.join(dir,'events.jsonl');
 if(fs.existsSync(pinFile)&&JSON.stringify(read(pinFile))!==JSON.stringify(pins))throw Error('checkpoint input/source mismatch: use a new directory');
 save(pinFile,pins);
 const previous=new Map();let resumed=false;
 if(fs.existsSync(journal))for(const line of fs.readFileSync(journal,'utf8').split('\n')){if(!line)continue;let e;try{e=JSON.parse(line);}catch{continue;}if(e.type==='result'){previous.set(e.id,e.result);resumed=true;}}
 const fd=fs.openSync(journal,'a'),emit=e=>fs.writeSync(fd,JSON.stringify(e)+'\n'),children=new Set(),phaseOriginal=GS.runPhase;
 let phase=null,phaseIndex=0,active,submitted=0,phaseName='',lastProgress=0;
 const phases=[],start=performance.now();
 function makeWorker(){
  if(children.size>=2)throw Error('worker limit exceeded');
  const child=cp.spawn('python',['-X','utf8','-I',path.join(__dirname,'bench_cosmo_search.py'),'--worker'],{stdio:['pipe','pipe','inherit']});children.add(child);
  let busy=null,assignedPhase=null;
  const w={postMessage(m){busy=performance.now();assignedPhase=phase;child.stdin.write(JSON.stringify(m)+'\n');},terminate(){children.delete(child);child.kill();}};
  readline.createInterface({input:child.stdout}).on('line',line=>{try{const m=JSON.parse(line);if(m.type==='done'&&busy!==null){assignedPhase.busyMs+=performance.now()-busy;busy=null;}w.onmessage?.({data:m});}catch(e){w.onerror?.(e);}});
  child.on('error',e=>w.onerror?.(e));child.on('exit',code=>{if(children.has(child))w.onerror?.(Error('worker exited '+code));});return w;
 }
 GS.runPhase=o=>{
  const index=phaseIndex++,ids=new Map(o.jobs.map(j=>[j.key,hash({job:j,runs:o.runs,seed:o.seed,stage:o.stage,options:o.options})]));
  const cached=Object.fromEntries(o.jobs.filter(j=>previous.has(ids.get(j.key))).map(j=>[j.key,previous.get(ids.get(j.key))]));
  const missing=o.jobs.filter(j=>!cached[j.key]),begin=performance.now();
  phase={index,name:phaseName,jobs:o.jobs.length,runs:o.runs,seed:o.seed,cached:Object.keys(cached).length,busyMs:0,gapMs:begin-(phases.at(-1)?.endMs??start)};const record=phase;phases.push(record);
  submitted+=missing.length*o.runs;emit({type:'phase',...record});
  const h=phaseOriginal({...o,jobs:missing,workers:2,onResult:(key,result)=>{const value={prog:result.prog??0,clear:result.clear,n:result.n,via:result.via||{},progs:result.progs||null,cosmo:result.cosmo||null,...GS.unsupportedFields(result)};cached[key]=value;emit({type:'result',phase:index,id:ids.get(key),key,result:value});o.onResult?.(key,result);},onProgress:(done,total)=>{o.onProgress?.(done+record.cached,o.jobs.length);if(Date.now()-lastProgress>60000){lastProgress=Date.now();console.error('progress',index,done,'/',total);}}});
  active=h;
  return {cancel:()=>h.cancel(),promise:h.promise.then(res=>{record.endMs=performance.now();record.elapsedMs=record.endMs-begin;record.idleMs=Math.max(0,2*record.elapsedMs-record.busyMs);emit({type:'phaseDone',...record});save(path.join(dir,'progress.json'),{phases,submitted,resumed,seconds:(performance.now()-start)/1000});return {...cached,...res};})};
 };
 return {makeWorker,onPhase(name,jobs){phaseName=name;console.error(name,jobs);},summary:()=>({phases,submitted,resumed,seconds:(performance.now()-start)/1000}),close(){active?.cancel();for(const c of children)c.kill();GS.runPhase=phaseOriginal;fs.closeSync(fd);}};
}
async function main(){
 const [input,output,variant,settings]=process.argv.slice(2);if(!input||!output||!['old','new'].includes(variant))throw Error('ACCOUNT PRIVATE_DIR old|new [SETTINGS_JSON]');
 const dir=privateDir(output),cx=context(input);cx.S.newSearch=variant==='new';if(settings)Object.assign(cx.S,read(settings));
 const files=['guild_planner.js','guild_search.js','search_executor.js','cosmo_learned.js','party_placement.js','sim/manifest.json','data/growth.json','tools/bench_cosmo_search.py'];
 const pins={variant,transport:'native Python / shared JS executor',workers:2,accountHash:hash(fs.readFileSync(input)),settings:cx.S,season:cx.G.season,stage:cx.stage,tiers:cx.tiers,breaks:cx.breaks,profileHash:hash(cx.results),sources:Object.fromEntries(files.map(f=>[f,hash(fs.readFileSync(path.join(ROOT,f)))]))};
 const T=instrument(dir,pins);
 try{const result=await Planner.search({...cx,makeWorker:T.makeWorker,onPhase:T.onPhase});delete result.growthOwned;save(path.join(dir,'result.json'),{...T.summary(),pins,result});console.error('complete',variant);}
 finally{T.close();}
}
module.exports={context,instrument,privateDir,save,hash};
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
