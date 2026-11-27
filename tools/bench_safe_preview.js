const cp=require('node:child_process'),fs=require('node:fs'),assert=require('node:assert/strict');
const {performance}=require('node:perf_hooks');
const {harness}=require('../tests/safe_preview_test');
const ref=process.argv[process.argv.indexOf('--compare')+1]||'HEAD';
const before=cp.execFileSync('git',['show',ref+':guild_daily_page.js'],{encoding:'utf8'});
const after=fs.readFileSync(require.resolve('../guild_daily_page'),'utf8');
function sample(src){const {c}=harness(src);c.guildDailyPreview();const start=performance.now();
  for(let i=0;i<100;i++)c.guildDailyPreview();return {ms:(performance.now()-start)/100,plan:JSON.parse(JSON.stringify(c.guildDailyPreview()))};}
const xs=[],ys=[];
for(let i=0;i<6;i++){
  let x,y;if(i%2){y=sample(after);x=sample(before);}else{x=sample(before);y=sample(after);}
  assert.deepEqual(y.plan,x.plan);if(i){xs.push(x.ms);ys.push(y.ms);}
}
console.log(JSON.stringify({before_ms:xs.sort((a,b)=>a-b)[2],after_ms:ys.sort((a,b)=>a-b)[2],metric:'ms per repeated preview, 40 synthetic units'}));
