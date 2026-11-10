// Native Worker adapter. Ranking/selection is the production JS implementation.
const fs = require('node:fs'), path = require('node:path'), zlib = require('node:zlib');
const {spawn} = require('node:child_process'), readline = require('node:readline');
const crypto = require('node:crypto');
const GS = require('../guild_search.js'), C = require('../cosmo_search.js');
const G = require('../data/cosmo_raid.json');
const [out, sizeText, repeatText, workersText, python, variant='baseline', mode='top'] = process.argv.slice(2);
const size=+sizeText, repeat=+repeatText, workers=+workersText;
const dir=path.join(out, `${size}-${mode}-${variant}-${repeat}`);
fs.mkdirSync(dir,{recursive:true});
const catalog=JSON.parse(fs.readFileSync(path.join(out,'catalog.json'),'utf8'));
// Alphabetical prefix: fixed before observing scores; both pools include supports.
const roster=catalog.slice(0,size), results=Object.fromEntries(roster.map(r=>[r.key,r]));
const originalParty=GS.party;
GS.party=(...args)=>{const p=originalParty(...args);p.spec={units:p.order.map(key=>({key,build:'standard'})),leader:0};return p;};
let children=new Set();
function makeWorker(){
 const child=spawn(python,['-X','utf8','-I',path.join(__dirname,'bench_cosmo_search.py'),'--worker'],{stdio:['pipe','pipe','inherit']});
 children.add(child);
 const w={onmessage:null,onerror:null,postMessage:m=>child.stdin.write(JSON.stringify(m)+'\n'),terminate:()=>{children.delete(child);child.kill();}};
 readline.createInterface({input:child.stdout}).on('line',line=>{try{w.onmessage?.({data:JSON.parse(line)});}catch(e){w.onerror?.(e);}});
 child.on('error',e=>w.onerror?.(e));
 child.on('exit',code=>{if(children.has(child)){children.delete(child);w.onerror?.(new Error('native worker exit '+code));}});
 return w;
}
const S=JSON.parse(JSON.stringify(G.search));
// Baseline explicitly preserves the original policy when switches are introduced.
if(variant==='baseline') delete S.speed;
else if(variant==='fast'||variant==='fast-replay') S.speed.surrogate.value=true;
else if(variant==='crn') S.speed.rngStreams.value=true;
else if(variant!=='reuse') throw new Error('unknown variant '+variant);
if(variant!=='baseline')S.speed.workerReuse.value=true;
const signature=crypto.createHash('sha256').update(JSON.stringify({roster,S,repeat,variant,mode})).digest('hex');
const originalRun=GS.runPhase, phases=[];
let instrumentationSeconds=0,resumed=false;
const replay=variant.endsWith('-replay'), baseCache=new Map();
let phase=0, active=null;
GS.runPhase=o=>{
 const i=phase++, file=path.join(dir,`phase-${i}.json.gz`), started=performance.now();
 const seed=repeat*100+o.seed;
 if(fs.existsSync(file)){
  resumed=true;
  const saved=JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  if(saved.signature!==signature)throw new Error('cache input mismatch: '+file);
  phases.push(saved.timing);console.log(JSON.stringify({size,repeat,variant,phase:i,resumed:true,...saved.timing}));
  return {promise:Promise.resolve(saved.res),cancel(){}};
 }
 let cached={},todo=o.jobs;
 if(replay){
  const baseIndex={1:0,4:1,3:2,2:3}[o.seed];
  if(!baseCache.has(baseIndex))baseCache.set(baseIndex,JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(out,`${size}-${mode}-baseline-${repeat}`,`phase-${baseIndex}.json.gz`)))));
  const old=baseCache.get(baseIndex);
  if(old.seed!==seed||old.timing.runs!==o.runs)throw Error('replay seed/runs mismatch');
  cached=Object.fromEntries(o.jobs.filter(j=>old.res[j.key]).map(j=>[j.key,old.res[j.key]]));
  todo=o.jobs.filter(j=>!cached[j.key]);
 }
 const h=originalRun({...o,jobs:todo,seed,chunk:100});active=h;
 return {cancel:()=>h.cancel(),promise:h.promise.then(res=>{
  Object.assign(res,cached);
  const timing={phase:i,teams:o.jobs.length,runs:o.runs,seconds:(performance.now()-started)/1000,...(replay?{replayed:Object.keys(cached).length,native:todo.length}: {})};
  phases.push(timing);
  const saveStart=performance.now();
  fs.writeFileSync(file,zlib.gzipSync(JSON.stringify({signature,timing,seed,jobs:o.jobs.map(j=>({key:j.key,keys:j.keys,order:j.order,boss:j.boss})),res})));
  instrumentationSeconds+=(performance.now()-saveStart)/1000;
  console.log(JSON.stringify({size,repeat,variant,...timing}));return res;
 })};
};
const started=performance.now();
C.search({S,bosses:G.season.bossOrder,mode,level:6,results,roster,workers,makeWorker,stage:'cosmo',base:'',
 onPlan:pl=>console.log(JSON.stringify({size,repeat,variant,plan:pl})),
 onPhase:(msg,total,info)=>console.log(JSON.stringify({size,repeat,variant,msg,total,info})),
 onProgress:(d,t)=>{if(d%10000===0)console.log(JSON.stringify({progress:d,total:t,phase:phase-1,seconds:(performance.now()-started)/1000}));}
}).then(result=>{
 const report={signature,size,repeat,variant:variant.replace('-replay',''),replay,resumed,mode,workers,search:S,phases,seconds:phases.reduce((s,p)=>s+p.seconds,0),
  wallSeconds:replay||resumed?null:(performance.now()-started)/1000-instrumentationSeconds,instrumentationSeconds,result};
 report.resultHash=crypto.createHash('sha256').update(JSON.stringify(result)).digest('hex');
 const reportFile=path.join(dir,'result.json');
 const previous=fs.existsSync(reportFile)?JSON.parse(fs.readFileSync(reportFile,'utf8')):null;
 // 완료한 같은 실행을 캐시로 검증해도 원래 시간 표본은 그대로 둔다.
 if(previous && previous.signature===signature){
  if(previous.resultHash!==report.resultHash)throw new Error('completed result mismatch: '+reportFile);
  console.log(JSON.stringify({size,repeat,variant,preserved:true,resultHash:report.resultHash}));
 }else fs.writeFileSync(reportFile,JSON.stringify(report));
 console.log(JSON.stringify({size,repeat,variant,seconds:report.seconds,resultHash:report.resultHash}));
}).catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>{for(const p of children)p.kill();children.clear();});
