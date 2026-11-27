// Page lifecycle/import contracts without a browser, engine, or account files.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const UI=require('../guild_daily_ui'),Direct=require('../direct_party');
const source=fs.readFileSync(require.resolve('../guild_daily_page'),'utf8');
const plain=x=>JSON.parse(JSON.stringify(x));
function harness(src=source){
  const calls=[],writes=[],sessions=[],elements={content:{value:0},stage:{value:0},q:{value:''}};
  const G={season:{id:30112},search:{daily:{seals:{max:3}}}},rows=[{key:'a'},{key:'b'}];
  const c={console,Date,JSON,Set,Map,Promise,Error,GuildDailyUI:UI,DirectParty:Direct,
    D:{guild:G},GSR:{id:0,phase:'idle',banCoop:true,rows:[]},R:rows,EXCL:new Set(),
    MI:{hash:'account',info:{},growth:{},profiles:{op:{results:{}}}},SIMQ:{busy:null},CSR:{phase:'idle'},
    GuildView:{gameDay:()=>({date:'2026-11-26'}),normSel:(g,s)=>s},
    guildIdentity:()=>['30112','data'],gsTiers:()=>[],ownedSimBreaks:()=>[],growthOptions:()=>({}),growthEnabled:()=>false,
    seasonBlocked:()=>false,growthCancel(){},guildGwenClaim(){},miGrowth:async()=>({}),
    renderGuildSearch(){},csMobile:()=>false,navigator:{hardwareConcurrency:2},location:{href:'https://example.test/index.html'},
    document:{hidden:false},LS:{get:()=>null,set:(k,v)=>writes.push([k,plain(v)])},
    SearchExecutor:{PAINT_MS:0,throttle:()=>Object.assign(()=>{},{cancel(){}})},
    GuildDaily:{createSession(){const session={closed:false,resets:0,reset(){this.resets++;},close(){this.closed=true;}};sessions.push(session);return session;}},
    GuildPlanner:{async search(cx){calls.push(cx);if(c.failure)throw Error(c.failure);
      const i=cx.previous?.teams.length||0,t={keys:['a','b','c','d'].map(k=>k+i),order:['c','a','b','d'].map(k=>k+i),leaderKey:'d'+i,
        kind:i?'normal':'ex',step:i?6:7,level:i?0:3,tiers:i?[0]:[2],sup:'s'+i,brk:'break'+i,brkLv:2,
        score:100,signature:'team'+i,date:'2026-11-26',evaluation:{partial:!!c.stopTeam,placementComplete:!c.stopTeam,stageSupportComplete:true}};
      const teams=[...(cx.previous?.teams||[]),t];return {teams,rows:teams,sum:teams.length*100,partial:!!c.stopTeam,
        plan:{day:{date:'2026-11-26'}},seals:{used:teams.length+1,remaining:2-teams.length}};}},
    $:id=>elements[id],contents:[{key:'guild',stages:[{name:'7단계'},{name:'6단계'}]}],cur:[{name:'7단계'},{name:'6단계'}],
    DIRECT:{draft:Direct.draft(),revision:0},GS:{},guildStoreKey:()=> 'guild.v3.30112',directCancel(){},
    directSave(){writes.push(['direct.v1',plain(Direct.storage(c.DIRECT))]);},saveSel(){},showInfo(){},showPow(){},condChanged(){},directNavigate(){},
  };
  vm.createContext(c);vm.runInContext(src,c);c.guildDailySourcePaint=()=>{};
  return {c,calls,writes,sessions,elements};
}
async function checks(src=source){
  const {c,calls,writes,sessions,elements}=harness(src);
  await c.guildDailyStart();assert.equal(c.GSR.teams.length,1);assert.equal(sessions.length,1);assert(!sessions[0].closed);
  const first=plain(c.GSR.teams[0]);c.stopTeam=true;
  await c.guildDailyStart(c.GSR,null,true);assert.equal(c.GSR.teams.length,2);assert.deepEqual(plain(c.GSR.teams[0]),first);
  assert.equal(calls[0].session,calls[1].session);assert.equal(calls[1].previous.teams.length,1);assert(!sessions[0].closed);
  assert.equal(writes.length,0,'search adds no persistent keys');
  await c.guildDailyStart(c.GSR,null,true);assert.equal(calls.length,2,'cap blocks extra click');
  for(const i of [0,1]){
    c.guildDailyFromSearch(i);const t=c.GSR.teams[i];
    assert.deepEqual(plain(c.DIRECT.draft.slots.map(s=>s.key)),t.order);assert.equal(c.DIRECT.draft.leader,t.leaderKey);
    assert.equal(c.DIRECT.draft.brk.name,t.brk);assert.deepEqual(plain(c.GS.sel),{level:t.level,tiers:t.tiers,support:t.sup});
    assert.equal(Number(elements.stage.value),i);assert.equal(c.DIRECT.guildSearchSource.partial,i===1);
    assert.equal(c.DIRECT.guildSearchSource.signature,t.signature);assert.equal(c.DIRECT.guildSearchSource.team,i+1);
  }
  assert(writes.every(([k])=>['guild.v3.30112','direct.v1'].includes(k)));
  assert(!('signature' in writes.find(([k])=>k==='direct.v1')[1]),'session metadata does not leak to stored/shared draft');
  await c.guildDailyStart();assert.equal(sessions.length,1);assert.equal(sessions[0].resets,1);
  assert.equal(calls.at(-1).previous,null,'restart clears previous teams, keeps workers');
  const bad=harness(src);await bad.c.guildDailyStart();bad.c.failure='남은 구원자 부족';const saved=plain(bad.c.GSR.teams);
  await bad.c.guildDailyStart(bad.c.GSR,null,true);assert.equal(bad.c.GSR.phase,'done');assert.deepEqual(plain(bad.c.GSR.teams),saved);
  assert.equal(bad.c.GSR.seals.used,2);assert.match(bad.c.GSR.followError,/구원자 부족/);
  assert(!bad.sessions[0].closed,'failed follow retains reusable session');
  bad.c.MI.hash='changed';await bad.c.guildDailyStart(bad.c.GSR,null,true);assert.equal(bad.calls.length,2);
  bad.c.guildDailyInput();assert(bad.sessions[0].closed);
  await bad.c.guildDailyStart();assert.equal(bad.sessions.length,2);assert(bad.sessions[1].closed,'failed restart closes session');
  const stop=harness(src);await stop.c.guildDailyStart();
  stop.c.miGrowth=async()=>{stop.c.GSR.stopRequested=true;return {};};
  await stop.c.guildDailyStart(stop.c.GSR,null,true);
  assert.equal(stop.c.GSR.phase,'done');assert(!stop.sessions[0].closed,'early stop retains reusable session');
  assert.equal(stop.c.GSR.id,2);assert.equal(stop.c.GSR.teams.length,1);
  const race=harness(src);let release;race.c.miGrowth=()=>new Promise(r=>{release=r;});
  const pending=race.c.guildDailyStart();race.c.GSR.id++;const newer=race.c.GuildDaily.createSession();race.c.GSR.session=newer;
  release({});await pending;assert(race.sessions[0].closed);assert(!newer.closed,'old completion cannot close newer search');
}
(async()=>{
  await checks();
  for(const [from,to] of [["partial:!!t.evaluation?.partial","partial:source.partial"],["session.close();if(target.session===session)target.session=null;","guildDailyRelease(target);"],["target.seals.remaining<1","false"],["{id,following:false,handle:null}","{following:false,handle:null}"],["{id,following:false,handle:null,followError:","{following:false,handle:null,followError:"]]){
    assert(source.includes(from));await assert.rejects(()=>checks(source.replace(from,to)),undefined,from);
  }
  console.log('PASS daily page: follow/session/cap/error/stale/import/storage/race contracts, 5 killed mutations');
})().catch(e=>{console.error(e);process.exitCode=1;});
