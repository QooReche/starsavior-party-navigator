'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {report}=require('../tools/report_guild_attr'),{stats,wilson}=require('../tools/evaluate_guild_time');
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'guild-attr-'));
const save=(p,x)=>fs.writeFileSync(p,JSON.stringify(x));
try{
 for(const n of ['A','B','C','D']){
  fs.mkdirSync(path.join(dir,n));fs.mkdirSync(path.join(dir,n+'-holdout'));
  const newSearch=['C','D'].includes(n),placement=['B','D'].includes(n);
  const scores=Array.from({length:1000},(_,i)=>(1+i%10)*(newSearch?2:1)),clears=scores.map(s=>Number(s>=8));
  const summary=stats(scores,clears);
  save(path.join(dir,n,'result.json'),{seconds:newSearch?2:1,resumed:false,pins:{accountHash:'synthetic',sources:{engine:'same'},
   settings:{newSearch,placement:{baseline:placement,enabled:placement,keep:2}}}});
  fs.writeFileSync(path.join(dir,n,'events.jsonl'),JSON.stringify({type:'result',id:'job',result:{prog:1,progs:[1],via:{coop:1}}})+'\n');
  save(path.join(dir,n+'-holdout','result.json'),{pins:{seedStart:20270101,batches:50,runsPerBatch:20},evaluated:{[n]:{scores,clears,summary,clearCI95:wilson(summary.clear,1000)}}});
 }
 const r=report(dir,100);assert(r.legacyPlacementIgnored);assert.equal(r.rows[1].comparisonToA.point.clearDifference,0);
 assert.equal(r.rows[2].timeRatio,2);assert.equal(r.rows[2].comparisonToA.point.meanRatio,2);
 assert.deepEqual(r.rows[2].comparisonToA.ci95.meanRatio,[2,2]);
 // Mutations: changing one engine pin or an actual legacy request must be rejected.
 const bfile=path.join(dir,'B','result.json'),b=JSON.parse(fs.readFileSync(bfile,'utf8'));
 b.pins.sources.engine='different';save(bfile,b);assert.throws(()=>report(dir,100),/search sources/);
 b.pins.sources.engine='same';b.resumed=true;save(bfile,b);assert(!report(dir,100).rows[1].timingValid);
 fs.writeFileSync(path.join(dir,'B','events.jsonl'),JSON.stringify({type:'result',id:'changed',result:{prog:1}})+'\n');
 assert.throws(()=>report(dir,100),/legacy placement changed/);
 console.log('PASS guild attribution ratios, paired intervals, inactive B, source/request mutations, resumed timing');
}finally{fs.rmSync(dir,{recursive:true,force:true});}
