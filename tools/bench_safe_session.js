// Real Node worker startup only; this does not model Pyodide boot time.
const {Worker}=require('node:worker_threads');
const {performance}=require('node:perf_hooks');
const {baseline}=require('./bench_safe_daily');
async function sample(daily){
  const workers=[];
  const make=()=>{const w=new Worker('setInterval(()=>{},1000)',{eval:true});
    w.ready=new Promise(resolve=>w.once('online',resolve));workers.push(w);return w;};
  let s=daily.createSession(make);await s.pool.get(0).ready;
  const start=performance.now();
  if(s.reset)s.reset();else{s.close();s=daily.createSession(make);}
  await s.pool.get(0).ready;const ms=performance.now()-start;
  s.close();await Promise.all(workers.map(w=>w.terminate()));return ms;
}
async function main(){
  const ref=process.argv[process.argv.indexOf('--compare')+1]||'HEAD';
  const before=baseline(ref),after=require('../guild_daily'),xs=[],ys=[];
  for(let i=0;i<6;i++){
    let x,y;if(i%2){y=await sample(after);x=await sample(before);}else{x=await sample(before);y=await sample(after);}
    if(i){xs.push(x);ys.push(y);}
  }
  console.log(JSON.stringify({before_ms:xs.sort((a,b)=>a-b)[2],after_ms:ys.sort((a,b)=>a-b)[2],metric:'Node worker restart, not Pyodide'}));
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
