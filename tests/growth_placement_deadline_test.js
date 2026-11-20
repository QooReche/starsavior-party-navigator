const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../growth_ui'),'utf8');
const start=source.indexOf('async function growthEvaluate('),end=source.indexOf('function growthMaybe',start),code=source.slice(start,end);
async function check(src=code){let now=0,dispatched=0;
 const c={Date:{now:()=>now},Number,Promise,PLACEMENT_CACHE:new Map(),GROW:{},growthPaint:()=>{},simOpt:()=>({}),
  placementRun:async()=>{now=101;return {party:{units:[]}};},scrPool:()=>{dispatched++;throw Error('final dispatch');}};
 vm.createContext(c);vm.runInContext(src,c);
 const state={errors:[],versions:{engine:'v'}},jobs=[{id:'x',party:{units:[]},options:{}}],env={final:true,live:()=>true,state,version:'v'};
 await assert.rejects(()=>c.growthEvaluate(jobs,40,1,{key:'op'},{tab:'x',name:'y'},1,100,env),/final dispatch/);assert.equal(dispatched,1);
 const expired=await c.growthEvaluate(jobs,40,1,{key:'op'},{tab:'x',name:'y'},1,0,{...env,final:false});assert.equal(Object.keys(expired).length,0);assert.equal(dispatched,1);
}
(async()=>{await check();const line='if(env.final&&Number.isFinite(deadline))deadline+=Date.now()-placementStarted;';assert(code.includes(line));await assert.rejects(()=>check(code.replace(line,'')));console.log('PASS growth placement elapsed time preserves final budget; mutation caught');})().catch(e=>{console.error(e);process.exitCode=1;});
