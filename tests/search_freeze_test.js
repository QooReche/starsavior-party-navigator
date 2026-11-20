// Frozen before executor extraction at 6688d7a. Array order and duplicate jobs are significant.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {createRequire}=require('node:module'),zlib=require('node:zlib');
const ROOT=path.resolve(__dirname,'..'),file=path.join(__dirname,'fixtures/search_execution_6688d7a.json.gz');
const plain=x=>JSON.parse(JSON.stringify(x));
function prelude(name,exports,marker='(async()=>'){
 const filename=path.join(__dirname,name),src=fs.readFileSync(filename,'utf8').split(marker)[0];
 return vm.runInThisContext('(function(require,__dirname){'+src+'\nreturn {'+exports+'};})',{filename})(createRequire(filename),__dirname);
}
function normalize(x){
 if(Array.isArray(x))return x.map(normalize);
 if(x&&typeof x==='object')return Object.fromEntries(Object.keys(x).sort().filter(k=>!['id','requestId','jobId'].includes(k)).map(k=>[k,normalize(x[k])]));
 return x;
}
async function capture(){
 const cosmo=prelude('search_defaults_test.js','check,C'),guild=prelude('guild_defaults_test.js','run');
 // Intercept raw replies too: runPhase intentionally projects only policy fields.
 const GS=require('../guild_search'),phase=GS.runPhase,phases=[];
 GS.runPhase=o=>{const record={jobs:plain(o.jobs),runs:o.runs,seed:o.seed,chunk:o.chunk,results:[],progress:[]};phases.push(record);
  return phase({...o,onResult:(k,r)=>{record.results.push([k,plain(r)]);o.onResult?.(k,r)},onProgress:(d,t)=>{record.progress.push([d,t]);o.onProgress?.(d,t)}});};
 const out={};
 try{
  for(const [name,fn] of [
   ['cosmo-learned-auto-break',()=>cosmo.check(cosmo.C)],
   ['guild-large',()=>guild.run(false,{small:false,banCoop:true,breaks:[],tiers:[0,0,0,0]})],
   ['guild-break',()=>guild.run(false,{small:true,banCoop:true,breaks:[{name:'스타피어서',level:7}],tiers:[1,0,0,0]})],
   ['guild-unfiltered',()=>guild.run(false,{small:true,banCoop:false,breaks:[],tiers:[0,0,0,0]})],
   ['guild-learned',()=>guild.run(false,{small:true,banCoop:true,newSearch:true,breaks:[{name:'스타피어서',level:7}],tiers:[0,0,0,0]})]]){
    phases.length=0;out[name]={result:await fn(),phases:plain(phases)};
  }
 }finally{GS.runPhase=phase;}
 const P=require('../party_placement'),variants=P.variants;
 try{
  const retry=prelude('cosmo_retry_test.js','run,settings','async function main()');
  out.recovery=plain(await retry.run());assert.equal(out.recovery.out.attempts.length,3);
  out.noTriples=plain(await retry.run(retry.settings(),true));assert(out.noTriples.error);
  const learned=prelude('cosmo_learned_test.js','search,settings','async function main()');
  const S=learned.settings();Object.assign(S.learned,{S:40,m:1,K:40,M:1,A:8,epochs:3});S.rerank.keep=20;
  out.ties=plain(await learned.search(S,'ties'));assert(out.ties.out.rows.length);
 }finally{P.variants=variants;}
 out.runtime=await runtime();
 return normalize(out);
}
async function runtime(){
 const html=fs.readFileSync(path.join(ROOT,'party_template.html'),'utf8'),cut=(s,a,b)=>s.slice(s.indexOf(a),s.indexOf(b,s.indexOf(a)));
 const trace=[],responses=[],raw={ver:'synthetic',n:4,prog:.75,clear:.5,t60:.5,ci:[.1,.9],progs:[.2,1,.8,1],via:{coop:.1},raw:[[1,.2],[2,1],[3,.8],[4,1]],unsupported:[{unit:'u0',raw:'synthetic-only'}]};
 const ctx=vm.createContext({console,URL,Date,setTimeout,clearTimeout,SearchExecutor:globalThis.SearchExecutor,
  navigator:{hardwareConcurrency:2},document:{hidden:false},location:{href:'https://synthetic.test/index.html'},
  SIMQ:{LOAD_MS:180000,res:{},scr:{},meta:{}},RECO:{},CFG:{recommendation:{}},LASTQ:{},
  recoIdentity:()=> 'fixed',recoProgressPaint(){},directResultsPaint(){},simTeamLimit:()=>240000,simRateAdd(){},goalVal:r=>r?.t60,
  RecommendPipeline:require('../recommend_pipeline'),
  Worker:class{postMessage(m){trace.push(plain(m));setImmediate(()=>{if(this.dead)return;const send=x=>this.onmessage({data:{...m,...x}});
   send({type:'stage',msg:'준비 끝'});for(const t of m.teams){responses.push([t.key,plain(raw)]);send({type:'team',key:t.key,result:plain(raw)});}send({type:'done'});});}terminate(){this.dead=true;}}
 });
 // Load the real executor in the same realm as its injected fake clock/worker.
 const executor=path.join(ROOT,'search_executor.js');if(fs.existsSync(executor))vm.runInContext(fs.readFileSync(executor,'utf8'),ctx);
 vm.runInContext(cut(html,'const SCR_WMAX=','// 이 기기의 시뮬 속도'),ctx);
 const src=fs.readFileSync(path.join(ROOT,'recommend_runtime.js'),'utf8');
 vm.runInContext(cut(src,'function recoEvaluate(','async function recoEnsure('),ctx);
 const task={owner:'reco',request:0,engine:'synthetic'},snap={key:'fixed',c:{key:'op',parties:2},st:{tab:'a',name:'b'},seed:20261121,n:4,options:{},
  screenKey:p=>'screen'+p,plan:p=>({all:[{key:'team'+p}],rows:[{key:'team'+p}],total:1}),sig:t=>t.key,party:t=>({units:[{key:t.key}]}),breakFor:()=>null,
  result:t=>ctx.SIMQ.res[t.key],meta:{parts:Array.from({length:8},()=>({}))},first:()=>ctx.SIMQ.res.team1};
 ctx.RECO.task=task;await ctx.recoCalculate(snap,task);
 const before=trace.length;await ctx.recoCalculate(snap,task);assert.equal(trace.length,before,'cached recommendation resubmitted');
 const direct=fs.readFileSync(path.join(ROOT,'direct_run.js'),'utf8');
 Object.assign(ctx,{DIRECT:{draft:{},revision:1,requestId:0,rows:{},cache:new Map(),expected:{now:{sig:'now',revision:1,runs:4,seed:20261121,stage:'op/a/b',party:{units:[{key:'u0'}]},options:{},versions:{engine:'synthetic'}}}},
  MI:{},D:{},QK:{},MyInfoReco:{hash:()=> 'synthetic'},DirectParty:{validate:()=>({ok:true})},directContext:()=>({}),directSync(){},directValues:()=>({errors:[]}),directInputKey:()=> 'fixed',directCopy:plain,directManifest:async()=>({ver:'synthetic'})});
 vm.runInContext(cut(direct,'async function directRunRows(','// Only the completed first'),ctx);
 await ctx.directRunRows();while(ctx.DIRECT.active)await new Promise(setImmediate);
 const directCount=trace.length;await ctx.directRunRows();assert.equal(trace.length,directCount,'cached direct resubmitted');
 ctx.simPoolDrop('reco');ctx.simPoolDrop('direct');
 assert(trace.length===3&&responses.length===3);assert(ctx.DIRECT.rows.now.result.prog>0);
 return plain({trace,responses,recommendation:ctx.SIMQ.res,direct:ctx.DIRECT.rows});
}
if(require.main===module)(async()=>{
 const actual=await capture();
 if(process.argv.includes('--capture')){assert.equal(require('node:child_process').execFileSync('git',['diff','6688d7a','--','guild_search.js','guild_planner.js','cosmo_search.js','cosmo_learned.js','party_template.html','recommend_runtime.js','direct_run.js'],{encoding:'utf8'}),'');fs.writeFileSync(file,zlib.gzipSync(JSON.stringify(actual)));}
 else {const expected=JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));assert.deepEqual(actual,expected);
  const mutated=structuredClone(actual);mutated.runtime.responses[0][1].via={};assert.throws(()=>assert.deepEqual(mutated,expected));
  mutated.runtime.responses=actual.runtime.responses.slice().reverse();assert.throws(()=>assert.deepEqual(mutated,expected));}
 console.log('PASS frozen search requests, ordered phases/results, raw/t60/ci/progs/via/unsupported, multi-party recommendation, direct/cache');
})().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={capture,normalize};

