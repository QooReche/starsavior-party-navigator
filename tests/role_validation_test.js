const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {runValidation,interval}=require('../tools/validate_role_search');
function options(missing=false){return {jobs:[{key:'cosmo',party:{}},{key:'guild',party:{}}],runs:2,seed:1,workers:2,stage:'validation',base:'',makeWorker:()=>({terminate(){},postMessage(m){setImmediate(()=>{for(const t of m.teams)this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{prog:.5,progs:[.4,.6],n:2,...(t.key==='cosmo'?{cosmo:{top:17,mean:14},...(!missing?{scores:[11,17]}:{})}:{})}}});this.onmessage({data:{type:'done',id:m.id}});});}})};}
(async()=>{
 const r=await runValidation(options());assert.deepEqual(r.cosmo.scores,[11,17]);assert.deepEqual(r.guild.progs,[.4,.6]);
 await assert.rejects(()=>runValidation(options(true)),/per-run scores missing/);
 // Opposite boss outcomes must share the same resampled battle indices.
 const a=[Array.from({length:200},(_,i)=>i+1),Array.from({length:200},(_,i)=>400-i*2)],b=a.map((r,t)=>r.map((x,i)=>x+(t?i%13:-i%7)));
 const ci=interval(a,b),source=fs.readFileSync(require.resolve('../tools/validate_role_search'),'utf8');
 const anchor='for(let t=0;t<a.length;t++){x+=top';assert(source.includes(anchor));
 const ctx={module:{exports:{}},require:n=>n.startsWith('.')?require(require('node:path').resolve(__dirname,'../tools',n)):require(n),__dirname:require('node:path').resolve(__dirname,'../tools')};
 vm.runInNewContext(source.replace(anchor,'for(let t=0;t<a.length;t++){const ids=Array.from({length:200},()=>Math.floor(random()*200));x+=top'),ctx);
 assert.notDeepEqual(Array.from(ctx.module.exports.interval(a,b)),ci,'independent boss resampling must change the interval');
 console.log('PASS private validation: raw scores, missing result, paired battle-index bootstrap');
})().catch(e=>{console.error(e);process.exitCode=1;});
