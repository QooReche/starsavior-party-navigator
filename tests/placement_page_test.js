const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const P=require('../party_placement'),J=require('../placement_search');
const src=fs.readFileSync(require.resolve('../placement_page'),'utf8');
const party={units:['a','b','c','d'].map(key=>({key,stats_final:true,stats_override:{hp:123}})),leader:0};
async function check(source=src){
 let sent,dropped=0,live=true,cancel;
 const c={PartyPlacement:P,PlacementSearch:J,Map,URL,Number,setInterval,clearInterval,location:{href:'http://localhost/'},
  scrPool:n=>{assert.equal(n,2);return [];},simPoolDrop:()=>dropped++,simWatch:()=>()=>{},simTeamLimit:()=>100,
  simDispatch:(ws,jobs,o)=>sent={jobs,o}};
 vm.createContext(c);vm.runInContext(source,c);
 const start=()=>c.placementRun({party,stage:'cosmo',options:{cosmo_raid:{level:3}},brk:{name:'cube',level:7},live:()=>live,register:f=>cancel=f});
 const pending=start();assert.equal(sent.jobs.length,24);const first=sent;
 for(const j of sent.jobs){const m=sent.o.msg(j);assert.equal(m.teams[0].options.break_skill.level,7);assert.equal(m.stage,'cosmo');assert(m.teams[0].party.units.every(u=>u.stats_override.hp===123));
  const score=j.p.leaderKey==='d'&&j.p.order[0]==='a'?100:1;sent.o.team(j,{result:{clear:.8,prog:.8,progs:[.8],via:{},cosmo:{mean:score,top:score}}});}
 sent.o.done();const winner=await pending;assert.equal(winner.p.leaderKey,'d');assert.equal(winner.p.order[0],'a');
 const missing=start();sent.o.done();await assert.rejects(missing,/누락/);
 const cancelled=start();assert.notEqual(first.o.id,sent.o.id);cancel();await assert.rejects(cancelled,/취소/);assert(!sent.o.live());assert.equal(dropped,1);
 const changed=start();live=false;await assert.rejects(changed,/입력/);assert.equal(dropped,2);
 // Cosmo adapter must preserve break skill, level, and the rear-row leader.
 live=true;c.CDIRECT={jobs:{x:{party,stage:'cosmo',options:{cosmo_raid:{level:3},break_skill:{name:'cube',level:7}}}}};
 c.cdSync=()=>{};c.cdInput=()=>1;c.$=()=>({querySelector:()=>({})});c.cdPaint=()=>{};
 let edit;c.cdChange=a=>edit=a;
 const arrange=c.cdArrangeSim('x'),actualBreak=sent.o.msg(sent.jobs[0]).teams[0].options.break_skill;
 for(const j of sent.jobs)sent.o.team(j,{result:{clear:1,prog:1,cosmo:{mean:j.p.leaderKey==='d'?9:1,top:j.p.leaderKey==='d'?9:1}}});
 sent.o.done();await arrange;assert.equal(actualBreak?.level,7);assert.equal(edit.action.leaderKey,'d');assert.equal(edit.type,'draft');
 // Loading account stats must not silently launch a standard-build comparison.
 c.contents=[{key:'op'}];c.cur=[{tab:'x',name:'y'}];c.DIRECT={draft:{}};c.MI={};
 c.$=()=>({value:0});c.DirectParty={validate:()=>({ok:true}),serialize:()=>assert.fail('must wait for account stats')};
 c.directContext=()=>({});c.directInputKey=()=>1;c.directValues=()=>null;c.directResultsPaint=()=>{};
 await c.directArrangeSim();assert.match(c.DIRECT.runError,/능력치/);assert.equal(c.DIRECT.placement,null);
}
(async()=>{await check();const from='brk:job.options.break_skill';assert(src.includes(from));await assert.rejects(()=>check(src.replace(from,'brk:null')));console.log('PASS placement page: 24 conditions, options/stats, leader, cancel, stale/missing, break mutation');})().catch(e=>{console.error(e);process.exitCode=1;});
