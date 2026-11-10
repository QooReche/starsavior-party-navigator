// Exercise the benchmark entry point with an in-memory filesystem and battle adapter.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../tools/bench_cosmo_search.js'),'utf8');
const reportPath=path.join('bench-output','12-top-baseline-0','result.json');
async function run(files,code=source,result={rows:[{sum:123}]}){
 const writes=[],errors=[],proc={argv:['node','bench','bench-output','12','0','1','python','baseline','top']};
 const GS={party(){},runPhase:()=>({promise:Promise.resolve({team:{cosmo:{mean:123,top:123,n:1}}}),cancel(){}})};
 const fakeFs={mkdirSync(){},existsSync:p=>files.has(p),readFileSync:p=>{
  if(!files.has(p))throw Error('unexpected read '+p);return files.get(p);
 },writeFileSync:(p,v)=>{writes.push(p);files.set(p,v);}};
 const mocks={'node:fs':fakeFs,'../guild_search.js':GS,'../cosmo_search.js':{
  search:async()=>{await GS.runPhase({jobs:[],seed:1,runs:1}).promise;return result;}
 },'node:child_process':{spawn(){throw Error('unexpected native worker');}}};
 await vm.runInNewContext(code,{require:n=>mocks[n]||require(n.startsWith('../')?path.join(__dirname,'../tools',n):n),
  __dirname:path.join(__dirname,'../tools'),process:proc,performance,console:{log(){},error:e=>errors.push(String(e))}});
 return {writes,errors,exitCode:proc.exitCode};
}
async function check(code=source){
 const files=new Map([[path.join('bench-output','catalog.json'),'[]']]);
 assert.equal((await run(files,code)).exitCode,undefined);
 const first=files.get(reportPath),report=JSON.parse(first);
 assert(report.wallSeconds>0&&!report.resumed,'fresh run records real timing');
 const again=await run(files,code);
 assert.equal(again.exitCode,undefined);
 assert(!again.writes.includes(reportPath),'cache verification must not overwrite completed report');
 assert.equal(files.get(reportPath),first,'all original timing fields remain byte-identical');
 const changed=await run(files,code,{rows:[{sum:456}]});
 assert.equal(changed.exitCode,1,'same signature with a different result must fail');
 assert(changed.errors.some(e=>e.includes('completed result mismatch')));
 assert.equal(files.get(reportPath),first,'mismatch preserves original evidence');
 files.delete(reportPath);
 await run(files,code);
 const partial=JSON.parse(files.get(reportPath));
 assert(partial.resumed&&partial.wallSeconds===null,'partial resume is not a full timing sample');
}
(async()=>{
 await check();
 if(process.argv.includes('--mutations')){
  const old='if(previous && previous.signature===signature){';
  assert.equal(source.split(old).length,2);
  await assert.rejects(check(source.replace(old,'if(false){')),assert.AssertionError);
  console.log('detected: completed benchmark timing overwrite');
 }
 console.log('PASS cosmo_bench_resume_test');
})().catch(e=>{console.error(e);process.exitCode=1;});
