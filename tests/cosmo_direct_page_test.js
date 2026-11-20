const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const C=require('../cosmo_direct'),P=require('../direct_party'),M=require('../myinfo_reco'),Share=require('../share_state'),UI=require('../cosmo_direct_ui');
const growth=require('../data/growth.json'),fixture=require('./fixtures/myinfo_synthetic.json');
const source=fs.readFileSync(require.resolve('../cosmo_direct_page'),'utf8');
const clean=x=>JSON.parse(JSON.stringify(x));
const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid,name:key,el:'sun',cls:'캐스터',img:key+'.png'}));
const keys=[...roster.filter(r=>fixture.units.some(u=>u.id===r.uid)),...roster.filter(r=>!fixture.units.some(u=>u.id===r.uid))].slice(0,12).map(r=>r.key);
const season={season:1023,levelMax:18,bosses:['mogulus','baskerville','disparity'].map(key=>({key,name:key,element:'질서',sim:true}))};
const bosses=season.bosses.map(b=>b.key);
async function check(code=source){
  const info=clean(fixture),saved={},sent=[],dropped=[];
  for(const key of keys){const uid=roster.find(r=>r.key===key).uid;if(!info.units.some(u=>u.id===uid))info.units.push({...clean(fixture.units[0]),id:uid});}
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  const c={CosmoDirect:C,DirectParty:P,MyInfoReco:M,CosmoDirectUI:UI,Map,Set,URL,JSON,Number,
    D:{cosmoRaid:clean(season),growthView:{itemSlots:require('../data/myinfo_slots.json')},journeyPriority:require('../data/journey_priority.json')},QK:{d:{}},
    MI:{info,growth,hash:'account-a'},R:roster,BYKEY:Object.fromEntries(roster.map(s=>[s.key,s])),SHARE:{},DIRECT:{mode:'direct'},
    SIMQ:{seed:42,n:100},LS:{get:k=>saved[k],set:(k,v)=>{saved[k]=clean(v);return true;}},
    contents:[{key:'cosmo',stages:[{name:'boss'}]}],$:()=>({value:0}),simOpt:()=>({test:'common'}),
    ownedSimBreaks:()=>[{name:'스타피어스',level:3}],pickBreak:()=>[1,'스타피어스'],brkLv:()=>3,
    score:()=>[0,{}],arrangeOf:combo=>({order:combo.map(x=>x.s.key).reverse()}),
    csBoss:b=>b,simPoolDrop:(...a)=>dropped.push(a),directCopy:clean,directManifest:async()=>({ver:'engine-a'}),
    scrPool:()=>[],simWatch:()=>()=>{},simTeamLimit:()=>100,simDispatch:(ws,jobs,o)=>sent.push({jobs,o}),
    cdArrangeSim:boss=>c.cdChange({type:'draft',boss,action:{type:'arrange',order:c.cd.state.teams[boss].draft.slots.map(m=>m.key).reverse(),leaderKey:keys[2]}}),
    location:{href:'http://localhost/index.html'},directNavigate:m=>{c.DIRECT.mode=m;},GwenLane:{},GwenStage:{destroy:()=>{}}};
  vm.createContext(c);vm.runInContext(code+'\nglobalThis.paintOriginal=cdPaint;cdPaint=()=>cdSync();globalThis.cd=CDIRECT;',c);
  c.cdInit();assert.equal(c.cd.state.seasonId,1023);
  const lookup=c.$;let cleared=0;
  c.$=()=>({hidden:true,replaceChildren:()=>cleared++});
  const render=c.CosmoDirectUI;c.CosmoDirectUI={render:()=>assert.fail('hidden panel must not render')};
  c.paintOriginal();assert.equal(cleared,1,'hidden panel releases duplicate slots');
  c.$=lookup;c.CosmoDirectUI=render;
  const draft=(boss,action)=>c.cdChange({type:'draft',boss,action});
  bosses.forEach((boss,i)=>keys.slice(i*4,i*4+4).forEach((key,slot)=>draft(boss,{type:'put',key,slot})));
  const original=clean(c.cd.state),jobs=clean(c.cd.jobs),account=JSON.stringify(info);
  assert.equal(Object.keys(jobs).length,3);assert.equal(jobs.mogulus.options.break_skill?.name,'스타피어스');
  assert(jobs.mogulus.party.units.every(u=>u.stats_final));
  const savedBefore=JSON.stringify(saved);draft('baskerville',{type:'put',key:keys[0],slot:0});
  assert.equal(JSON.stringify(saved),savedBefore,'duplicate put must not save or reset undo');
  await c.cdRun();assert.equal(sent.length,3);
  const first=sent.slice();c.cdChange({type:'team',boss:'baskerville'});
  assert(c.cd.active,'tabs must not cancel');assert(first.every(s=>s.o.live()));
  for(const [i,s] of first.entries()){
    assert.equal(s.o.owner,'cdirect');const m=s.o.msg();assert.equal(m.stage,'코스모 게이트');assert(m.progress);
    assert.deepEqual(clean(m.teams[0].options.cosmo_raid),{boss:bosses[i],step:3,level:6});
    s.o.team(s.jobs[0],{result:{ver:'engine-a',cosmo:{mean:100+i,top:200+i,clear:.8},clear:.8,progs:[1],via:{}}});s.o.done();
  }
  assert.equal(c.cd.active,null);assert.equal(C.summary(c.cd.state,c.cdResults()).total,303);
  const now=clean(c.cd.jobs);c.cdChange({type:'team',boss:'mogulus'});assert.deepEqual(clean(c.cd.jobs),now);
  draft('mogulus',{type:'leader',key:keys[2]});assert.equal(c.cd.jobs.mogulus.party.leader,2);
  assert.notEqual(c.cd.jobs.mogulus.sig,now.mogulus.sig);assert.equal(c.cd.jobs.baskerville.sig,now.baskerville.sig);
  assert.equal(C.summary(c.cd.state,c.cdResults()).total,null);assert.equal(C.summary(c.cd.state,c.cdResults()).done,2);
  c.cdUndo('mogulus');assert.equal(c.cd.jobs.mogulus.sig,now.mogulus.sig);assert.equal(C.summary(c.cd.state,c.cdResults()).total,303);
  draft('mogulus',{type:'grown',slot:0,value:true});
  assert.notDeepEqual(clean(c.cd.jobs.mogulus.party.units[0]),now.mogulus.party.units[0]);assert.equal(c.cd.jobs.disparity.sig,now.disparity.sig);
  assert.equal(JSON.stringify(info),account);c.cdUndo('mogulus');
  c.cdChange({type:'levelAll',level:12});assert(Object.values(c.cd.jobs).every(j=>j.options.cosmo_raid.level===12));
  assert.equal(C.summary(c.cd.state,c.cdResults()).done,0);
  c.cdUndo('baskerville');assert.equal(c.cd.state.teams.baskerville.level,6);assert.equal(c.cd.state.teams.mogulus.level,12);
  c.cdArrange('mogulus');assert.equal(c.cd.state.teams.mogulus.draft.leader,keys[2]);assert.notDeepEqual(clean(c.cd.state.teams.mogulus.draft.slots),original.teams.mogulus.draft.slots);
  await c.cdRun('mogulus');assert.equal(sent.length,4);const old=sent.at(-1);
  c.cdChange({type:'level',boss:'mogulus',level:11});assert(!old.o.live());assert.equal(dropped.at(-1)[0],'cdirect');
  assert.equal(C.summary(c.cd.state,c.cdResults()).done,1);
  const row={teams:bosses.map((boss,i)=>({boss,order:keys.slice(i*4,i*4+4).reverse(),level:i+2,brk:'스타피어스',brkLv:3,st:{mean:10+i,top:20+i,clear:.9}}))};
  c.cdFromSearch(row);assert.deepEqual(clean(c.cd.state),clean(C.fromSearch(row,c.cdSeason())));
  assert.deepEqual(saved[C.STORAGE_KEY],clean(C.storage(c.cd.state)));assert.equal(c.DIRECT.mode,'direct');assert.equal(saved['direct.v1'],undefined);
  const html=c.cdSearchSummary(row,'top');assert.equal((html.match(/class="cg-tab"/g)||[]).length,3);assert(html.includes('63'));assert(!html.includes('role="tab"'));
  const share=Share.parse('?'+Share.stringify({c:'cosmo',pm:'direct',cd:c.cd.state}),[{key:'cosmo',stages:[]}],[]);
  assert.deepEqual(share.cd,clean(C.share(c.cd.state)));assert.equal(share.dp,undefined);
  // A malformed break in one complete team must not block another team's run.
  draft('mogulus',{type:'brk',value:{name:'unowned',level:3}});
  assert(!c.cd.jobs.mogulus);assert(c.cd.jobs.baskerville&&c.cd.jobs.disparity);c.cdUndo('mogulus');
  const save=c.LS.set;c.LS.set=()=>false;c.cdChange({type:'level',boss:'mogulus',level:13});
  assert(c.cd.saveError.includes('저장 실패'),'sync must retain failed-save warning');
  c.LS.set=save;c.cdChange({type:'level',boss:'mogulus',level:12});assert.equal(c.cd.saveError,'');
  c.MI.growth=null;c.miGrowth=async()=>{c.MI.error='network';throw Error('offline');};
  c.cdRefresh();await c.cd.loading;assert(c.cd.loadError);assert.equal(Object.keys(c.cd.jobs).length,0);
  c.MI.error='';c.miGrowth=async()=>c.MI.growth=growth;
  c.cdRefresh();await c.cd.loading;assert.equal(c.cd.loadError,'');assert.equal(Object.keys(c.cd.jobs).length,3);
  // Recovery through the ordinary account loader also clears the old error.
  c.cd.loadError='old failure';c.cdRefresh();assert.equal(c.cd.loadError,'');assert.equal(Object.keys(c.cd.jobs).length,3);
  const local=JSON.stringify(saved);c.SHARE.cd=C.share(c.cd.state);c.cd.state=null;c.cdInit();c.cdChange({type:'level',boss:'mogulus',level:14});
  assert.equal(JSON.stringify(saved),local,'shared draft edits stay session-only');
  c.D.cosmoRaid.season=1024;c.SHARE.cd=null;c.cdInit();assert.equal(c.cd.state.seasonId,1024);assert.equal(C.usedBy(c.cd.state).size,0);
}
(async()=>{
  await check();
  const mutations=[
    ["action.type!=='team'","true"],
    ['CDIRECT.undo[boss]=previous.teams[boss]','CDIRECT.undo[boss]=next.teams[boss]'],
    ["simPoolDrop('cdirect',a.id)","simPoolDrop('direct',a.id)"],
    ['CosmoDirect.jobs(CDIRECT.state,{...ctx,boss})','CosmoDirect.jobs(CDIRECT.state,{...ctx,boss,resolveBreak:null})'],
    ['return entry?[[boss,entry.result]]:[]','return []'],
    ["owner:'cdirect'","owner:'direct'"],
    ['if(!CDIRECT.shared)CDIRECT.saveError','if(true)CDIRECT.saveError'],
    ['CDIRECT.state=CosmoDirect.fromSearch(row,cdSeason())','CDIRECT.state=CosmoDirect.create(cdSeason())'],
    ["if(MI.growth||!MI.info)CDIRECT.loadError='';",''],
    ["CDIRECT.input=input;CDIRECT.error='';","CDIRECT.input=input;CDIRECT.error='';CDIRECT.saveError='';"],
    ["if(host.hidden){GwenStage.destroy('cdirect');host.replaceChildren();return;}",''],
  ];
  for(const [a,b] of mutations){assert(source.includes(a),a);await assert.rejects(()=>check(source.replace(a,b)),{code:'ERR_ASSERTION'},a);}
  console.log(`PASS cosmo page: state/jobs/undo/ownership/signatures/summary/search/share; ${mutations.length}/${mutations.length} mutations caught`);
})().catch(e=>{console.error(e);process.exitCode=1;});
