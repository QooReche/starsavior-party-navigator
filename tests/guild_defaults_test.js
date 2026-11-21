// 200c2d3's actual page function and module are the oracle, not a rewritten pipeline.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process');
const GS=require('../guild_search'),Planner=require('../guild_planner'),V=require('../guild_view'),G=require('../data/guild_defense.json');
const old=p=>cp.execFileSync('git',['show','200c2d3:'+p],{cwd:require('node:path').resolve(__dirname,'..'),encoding:'utf8'});
const oldG=JSON.parse(old('data/guild_defense.json')),plain=x=>JSON.parse(JSON.stringify(x));
const mod={exports:{}};
vm.runInThisContext('(function(module,require){'+old('guild_search.js')+'\n})')(mod,n=>require('../'+n.slice(2)));
const oldGS=mod.exports,html=old('party_template.html');
const start=html.indexOf('async function guildSearchStart('),end=html.indexOf('$("guild-search").addEventListener',start);
const source=html.slice(start,end),currentHtml=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const currentStart=currentHtml.indexOf('async function guildSearchStart(');
const currentSource=currentHtml.slice(currentStart,currentHtml.indexOf('$("guild-search").addEventListener',currentStart));
const roster=Array.from({length:13},(_,i)=>({key:i===0?'professor-m':'u'+String(i).padStart(2,'0'),cls:i<7?'캐스터':i<10?'서포터':'디펜더'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:i<7?1000-i*30:400-i,stats:{hp:1000+i*100,atk:100+i,def:i*10,spd:100+i},combat:{}}]));
const excluded=['professor-m'];
// Freeze the archived dispatch policy too; current chunking is compared separately.
function settings(base,small){const s=structuredClone(base);s.execution={chunk:8};s.excluded=excluded;if(small)s.poolSize=5;s.screen2={keep:8,runs:3};s.finalists=3;s.final={...s.final,runs:4,levels:[2,4,6]};return s;}
function fakeWorker(trace,life){return class {
 constructor(){life.active++;life.max=Math.max(life.max,life.active);}
 terminate(){life.active--;this.dead=true;}
 postMessage(m){trace.push(plain(m));setImmediate(()=>{if(this.dead)return;
  for(const t of m.teams){const ks=t.party.units.map(u=>u.key),g=t.options.guild,b=t.options.break_skill;
   const mix=ks.reduce((n,k,i)=>n+(roster.findIndex(r=>r.key===k)+1)*(i+3),0);
   const v=Math.min(1,.52+(mix%17)/50+(g.support==='gust'?.12:0)+(b?.level===7?.1:0)-Math.abs(g.level-4)*.02);
   const progs=Array.from({length:m.n_runs},(_,i)=>i%4===0?.2:i%4===1?1:v);
   this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{prog:progs.reduce((a,b)=>a+b,0)/progs.length,progs,clear:progs.filter(x=>x===1).length/progs.length,n:m.n_runs,via:ks.includes('u01')?{forced_coop:.2}:{trigger:1}}}});
  }this.onmessage({data:{type:'done',id:m.id}});
 });}
};}
const fields=x=>Object.fromEntries(['rows','dropped','pool','combos','finalists','runs'].map(k=>[k,x[k]]));
async function run(legacy,{small,banCoop,breaks,tiers,newSearch=false}){
 const trace=[],life={active:0,max:0},Worker=fakeWorker(trace,life),S=settings(legacy?oldG.search:G.search,small);S.banCoop=banCoop;
 if(newSearch){S.newSearch=true;Object.assign(S.learned,{S:20,m:1,K:20,M:1,A:4,epochs:3,minCorrelation:-1,missThreshold:1});S.screen2.keep=4;S.finalists=1;}
 // Only worker concurrency is capped in the old page; its search policy stays intact.
 const ctx={GSR:{banCoop,phase:'idle',id:0},D:{guild:{...(legacy?oldG:G),search:S}},GuildSearch:legacy?{...oldGS,runPhase:o=>oldGS.runPhase({...o,workers:1})}:GS,GuildPlanner:Planner,GuildView:V,
   MI:{info:{synthetic:true},profiles:{op:{results}}},SIMQ:{busy:null},CSR:{phase:'idle'},R:roster,EXCL:new Set(),
   contents:[{key:'guild'}],cur:[{tab:'EX',name:'7'}],$:()=>({value:0}),seasonBlocked:()=>false,growthCancel(){},guildGwenClaim(){},
   renderGuildSearch(){},miGrowth:async()=>({}),gsTiers:()=>tiers,ownedSimBreaks:()=>breaks,gsSig:()=>'',growthOwnedContext:()=>'',
   navigator:{hardwareConcurrency:2},location:{href:'http://example.test/index.html'},Worker,SearchExecutor:{...require('../search_executor'),createWorker:()=>new Worker()},growthEnabled:()=>false};
 const out=await vm.runInNewContext((legacy?source:currentSource)+';guildSearchStart()',ctx);
 assert.equal(ctx.GSR.phase,'done',ctx.GSR.msg);
 assert.equal(life.active,0);assert.equal(life.max,1);assert(out.rows.length&&out.rows.every(r=>r.prog>0&&r.score>0));
 assert(trace.every(m=>m.teams.length));
 return plain({out:fields(out),trace});
}
(async()=>{
 for(const k of ['poolSize','minPowerRatio','minRole','minFront','minDealer','screen2','finalists','final','supportRole','excludeText','excludeKeys'])assert.deepEqual(G.search[k],oldG.search[k],k);
 for(const [k,v] of Object.entries(oldG.search.screen))assert.deepEqual(G.search.screen[k],v,k);
 assert.equal(G.search.newSearch,false);
 const cases=[{small:false,banCoop:true,breaks:[],tiers:[0,0,0,0]},{small:true,banCoop:true,breaks:[{name:'스타피어서',level:7}],tiers:[1,0,0,0]},{small:true,banCoop:false,breaks:[{name:'스타피어서',level:7}],tiers:[0,0,0,0]}];
 for(const c of cases){const expected=await run(true,c),actual=await run(false,c);assert.deepEqual(actual,expected);if(c.banCoop)assert(actual.out.dropped>0);else assert.equal(actual.out.dropped,0);}
 const S={...settings(G.search,true),newSearch:true,banCoop:true};
 assert.equal(GS.pool(S,results,roster).length,roster.length);
 assert.equal(GS.combos({...S,minFront:4,minDealer:4},roster.slice(0,4)).length,1);
 assert(!GS.coopHit(S,{via:{forced_coop:1}}));assert.equal(GS.screenSupport(S,['u07'],{'u07':'서포터'}),'none');
 const enabled=await run(false,{...cases[1],newSearch:true});
 assert.equal(enabled.out.pool,roster.length);assert.equal(enabled.out.dropped,0);
 assert(enabled.trace.some(m=>m.seed===9),'single switch reaches joint search through the page');
 assert(enabled.trace.filter(m=>m.seed===1).every(m=>m.teams.every(t=>t.options.guild.support==='none')));
 const notes=[{key:'professor-m',kind:'exclude',basis:'client',why:'test'}],cx={esc:String,label:String,excluded,notes,hasInfo:true};
 assert(GS.html({phase:'idle'},cx).includes('data-gs="coop"'));
 assert(!GS.html({phase:'idle'},{...cx,newSearch:true}).includes('data-gs="coop"'));
 const sigSource=currentHtml.slice(currentHtml.indexOf('function searchPlacementTag('),currentHtml.indexOf('const gsLabel='));
 const sigContext={D:{guild:{search:structuredClone(G.search)}},MI:{hash:'synthetic'},EXCL:new Set(),gsTiers:()=>[],GSR:{banCoop:true},GuildSearch:GS,ownedSimBreaks:()=>[]};
 vm.runInNewContext(sigSource+';globalThis.signature=gsSig',sigContext);
 const offSig=sigContext.signature();sigContext.D.guild.search.newSearch=true;assert.notEqual(sigContext.signature(),offSig);
 sigContext.D.guild.search.newSearch=false;assert.equal(sigContext.signature(),offSig);
 // Mutation: dropping the legacy role/power pool must make the exact comparison fail.
 const pool=GS.pool;try{GS.pool=(s,...args)=>pool({...s,newSearch:true},...args);await assert.rejects(async()=>assert.deepEqual(await run(false,cases[0]),await run(true,cases[0])));}finally{GS.pool=pool;}
 console.log('PASS guild defaults: 200c2d3/current page complete requests/results, synthetic roster, power/roles/coop/support, breaks on/off, new switch/UI/signature, mutation; max 1 worker');
})().catch(e=>{console.error(e);process.exitCode=1;});
