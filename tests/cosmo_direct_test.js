const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const C=require('../cosmo_direct'),P=require('../direct_party'),Search=require('../cosmo_search');
const growth=require('../data/growth.json'),slots=require('../data/myinfo_slots.json'),priority=require('../data/journey_priority.json');
const fixture=require('./fixtures/myinfo_synthetic.json');
const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid,el:'sun',cls:'캐스터'}));
const owned=roster.filter(s=>fixture.units.some(u=>u.id===s.uid)).map(s=>s.key);
const keys=[...owned,...roster.filter(r=>!owned.includes(r.key)).map(r=>r.key)].slice(0,12);
const season={id:23,levelMax:18,bosses:['alpha','beta','gamma'].map(key=>({key,name:key,element:'moon',sim:true}))};
const clean=x=>JSON.parse(JSON.stringify(x));
let checks=0;
function test(name,fn){fn();checks++;console.log('PASS '+name);}
function full(c=C){let s=c.create(season);season.bosses.forEach((b,i)=>keys.slice(i*4,i*4+4).forEach((key,slot)=>{
  s=c.edit(s,{type:'draft',boss:b.key,action:{type:'put',key,slot}});
}));return s;}
const change=(c,s,boss,action)=>c.edit(s,{type:'draft',boss,action});
function context(){
  const info=structuredClone(fixture);
  // Extend the public synthetic fixture to three owned teams; no private input.
  for(const key of keys){const uid=roster.find(r=>r.key===key).uid;if(!info.units.some(u=>u.id===uid))info.units.push({...structuredClone(fixture.units[0]),id:uid});}
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  return {info,roster,growth,slots,priority};
}
function defaults(c=C){
  const s=c.create(season);assert.deepEqual(Object.keys(s),['v','seasonId','active','teams']);
  assert.equal(s.active,'alpha');assert.equal(s.seasonId,23);
  for(const t of Object.values(s.teams)){assert.equal(t.level,6);assert.deepEqual(clean(t.draft),P.empty());}
  assert.equal(c.create({...season,levelMax:3}).teams.alpha.level,3);
  assert.equal(c.create({...season,levelMax:0}).teams.alpha.level,0);
  assert.deepEqual(clean(c.restore('{broken',season)),clean(s));
  assert.deepEqual(clean(c.restore({v:2,seasonId:23},season)),clean(s));
  const changed=c.edit(s,{type:'team',boss:'beta'});assert.equal(changed.active,'beta');assert.equal(s.active,'alpha');
  assert.notStrictEqual(changed,s);assert.notStrictEqual(changed.teams,s.teams);
}
test('create/defaults, cap, state shape, invalid restore, immutable tab',()=>defaults());
function duplicates(c=C){
  let s=c.create(season);s=change(c,s,'alpha',{type:'put',key:keys[0],slot:0});
  const before=JSON.stringify(s),next=change(c,s,'beta',{type:'put',key:keys[0],slot:1});
  assert.equal(JSON.stringify(next),before);assert.equal(JSON.stringify(s),before);
  s=change(c,s,'beta',{type:'put',key:keys[4],slot:1});
  assert.deepEqual(clean(change(c,s,'beta',{type:'put',key:keys[0],slot:1})),clean(s),'cannot replace another member with a duplicate');
  assert.equal(c.usedBy(s).get(keys[0]),'alpha');assert.equal(c.usedBy(s).get(keys[4]),'beta');assert.equal(c.usedBy(s).size,2);
  const malformed=full(c);malformed.teams.beta.draft.slots[2]={key:keys[0],grown:true};
  const v=c.validate(malformed,{roster,content:'cosmo'});
  assert(!v.ok);for(const boss of ['alpha','beta'])assert(v.teams[boss].errors.some(e=>e.code==='cross_dup'));
  assert(v.teams.gamma.ok);assert.equal(v.errors.filter(e=>e.code==='cross_dup').length,2);
  assert.deepEqual(Array.from(c.jobs(malformed,{roster}),j=>j.boss),['gamma'],'neither duplicate owner may run');
  const alias={...roster.find(r=>r.key===keys[0]),key:'alias'};malformed.teams.beta.draft.slots[2].key='alias';
  assert(c.validate(malformed,{roster:roster.concat(alias)}).teams.alpha.errors.some(e=>e.code==='cross_dup'),'uid aliases also conflict');
}
test('cross-team put ignored, usedBy, cross_dup on both teams, uid aliases',()=>duplicates());
function restoration(c=C){
  const raw=clean(full(c));raw.active='beta';raw.teams.beta.draft.slots[0]={key:keys[0],grown:true};raw.teams.beta.draft.leader=keys[0];
  raw.teams.alpha.draft.slots[1].grown=true;raw.teams.alpha.draft.slots[2]={key:keys[0],grown:false};
  raw.teams.gamma.draft.slots[1]={key:'<bad>',grown:true};raw.teams.gamma.level=99;
  raw.teams.unknown=raw.teams.alpha;const before=JSON.stringify(raw),s=c.restore(JSON.stringify(raw),season);
  assert.equal(s.active,'beta');assert.equal(s.teams.beta.draft.slots[0],null);assert.equal(s.teams.beta.draft.leader,keys[5]);
  assert.equal(s.teams.alpha.draft.slots[2],null);assert(s.teams.alpha.draft.slots[1].grown);
  assert.equal(s.teams.gamma.draft.slots[1],null);assert.equal(s.teams.gamma.level,6);assert(!s.teams.unknown);
  assert.equal(JSON.stringify(raw),before);
  assert.deepEqual(clean(c.restore(raw,{...season,id:24})),clean(c.create({...season,id:24})),'same bosses do not carry into new season');
  assert.deepEqual(clean(c.restore({...raw,seasonId:'23'},season)),clean(c.create(season)));
  const reordered=c.restore(raw,{...season,bosses:[season.bosses[1],season.bosses[0],season.bosses[2]]});
  assert.equal(reordered.teams.beta.draft.slots[0].key,keys[0]);assert.equal(reordered.teams.alpha.draft.slots[0],null);
}
test('restore drops duplicates/invalid entries, repairs leaders, rejects season mismatch',()=>restoration());
function levels(c=C){
  const s=full(c),before=JSON.stringify(s),all=c.edit(s,{type:'levelAll',level:12});
  assert.deepEqual(Object.values(all.teams).map(t=>t.level),[12,12,12]);
  const one=c.edit(all,{type:'level',boss:'beta',level:9});assert.deepEqual(Object.values(one.teams).map(t=>t.level),[12,9,12]);
  assert.equal(c.edit(s,{type:'level',boss:'alpha',level:99}).teams.alpha.level,18);
  assert.equal(c.edit(s,{type:'level',boss:'alpha',level:-1}).teams.alpha.level,0);
  for(const level of [NaN,Infinity,'8',1.5])assert.deepEqual(clean(c.edit(s,{type:'levelAll',level})),clean(s));
  assert.equal(JSON.stringify(s),before);
  for(const boss of ['missing','constructor','__proto__']){
    assert.deepEqual(clean(c.edit(s,{type:'team',boss})),clean(s));
    assert.deepEqual(clean(change(c,s,boss,{type:'clear'})),clean(s));
  }
  const limited=c.create({...season,levelMax:2});c.create(season);
  assert.equal(c.edit(limited,{type:'levelAll',level:10}).teams.alpha.level,2,'metadata does not follow most recently created state');
}
test('levelAll, independent levels, bounds, bad actions, independent season metadata',()=>levels());
test('validation delegates to DirectParty with op and blocks unsupported bosses',()=>{
  const s=full(),cx={roster,content:'cosmo',restrict:'moon'};
  assert(C.validate(s,cx).ok,'boss element is not a roster restriction');
  const stopped=C.restore(s,{...season,bosses:season.bosses.map(b=>({...b,sim:b.key!=='beta'}))});
  assert(C.validate(stopped,cx).teams.beta.errors.some(e=>e.code==='unsupported_boss'));
  assert.deepEqual(C.jobs(stopped,cx).map(j=>j.boss),['alpha','gamma']);
  assert(C.validate(s,{roster,info:fixture}).teams.gamma.errors.some(e=>e.code==='unowned'));
  assert(C.validate(C.create(season),{roster}).teams.alpha.errors.some(e=>e.code==='count'));
  s.teams.alpha.draft.leader='missing';assert(C.validate(s,cx).teams.alpha.errors.some(e=>e.code==='leader'));
  s.teams.alpha.draft.slots[0].key='unknown';assert(C.validate(s,cx).teams.alpha.errors.some(e=>e.code==='unknown'));
  assert(!C.validate(clean(s),cx).ok,'serialized state must restore season metadata');
});
function growthJobs(c=C){
  const cx=context(),account=JSON.stringify(cx.info),s=full(c),before=JSON.stringify(s);
  const base=c.jobs(s,cx);assert.deepEqual(Array.from(base,j=>j.boss),['alpha','beta','gamma']);
  const led=change(c,s,'alpha',{type:'leader',key:keys[2]}),leaders=c.jobs(led,cx);
  assert.equal(leaders[0].party.leader,2);assert.deepEqual(clean(leaders.slice(1)),clean(base.slice(1)));
  assert.deepEqual(clean(leaders[0].party.units),clean(base[0].party.units));
  const grown=change(c,led,'alpha',{type:'grown',slot:0,value:true}),jobs=c.jobs(grown,cx);
  assert.notDeepEqual(clean(jobs[0].party.units[0]),clean(leaders[0].party.units[0]),'fixture must actually improve growth stats');
  assert.deepEqual(clean(jobs[0].party.units.slice(1)),clean(leaders[0].party.units.slice(1)));
  assert.deepEqual(clean(jobs.slice(1)),clean(leaders.slice(1)),'A growth must not change B/C');
  const expected=P.powers(grown.teams.alpha.draft,{...cx,content:'cosmo'});
  assert.deepEqual(clean(jobs[0].party),P.serialize(grown.teams.alpha.draft,expected.profile.results));
  assert(jobs[0].party.units[0].stats_final);assert.equal(jobs[0].party.units[0].build,'none');
  assert.deepEqual(clean(jobs[0].options.cosmo_raid),{boss:'alpha',step:3,level:6});
  assert.equal(jobs[0].party.leader,2);
  const saved=c.restore(c.share(grown),season);assert(saved.teams.alpha.draft.slots[0].grown);assert.equal(saved.teams.alpha.draft.leader,keys[2]);
  assert.deepEqual(clean(c.jobs(saved,cx)),clean(jobs));
  const moved=change(c,grown,'alpha',{type:'swap',a:0,b:3});assert(moved.teams.alpha.draft.slots[3].grown);assert.equal(moved.teams.alpha.draft.leader,keys[2]);
  assert.equal(JSON.stringify(s),before);assert.equal(JSON.stringify(cx.info),account);
  jobs[0].party.units[0].stats_override.atk=-1;assert(c.jobs(grown,cx)[0].party.units[0].stats_override.atk>0);
}
test('team leaders, grown persists, actual final stats, only A job changes, immutable account',()=>growthJobs());
test('job options, explicit/auto/none break, ownership, growth data errors, standard',()=>{
  let s=full();const brk={name:'큐브 과부하',level:3};
  for(const b of ['alpha','beta'])s=change(C,s,b,{type:'brk',value:brk});
  s=change(C,s,'gamma',{type:'brk',value:null});
  const cx={roster,options:{rng_streams:true,cosmo_raid:{boss:'wrong'},break_skill:{name:'wrong'}},breaks:[brk]};
  const jobs=C.jobs(s,cx);for(const j of jobs){assert(j.options.rng_streams);assert.equal(j.options.cosmo_raid.boss,j.boss);assert.equal(j.party.leader,0);assert(j.party.units.every(u=>u.build==='standard'));}
  assert.deepEqual(jobs.map(j=>j.options.break_skill),[brk,brk,null]);
  assert.throws(()=>C.jobs(s,{...cx,breaks:[]}),/브레이크/);
  const auto=C.jobs(full(),{roster,resolveBreak:(d,b)=>b==='alpha'?brk:null});assert.deepEqual(auto[0].options.break_skill,brk);assert.equal(auto[1].options.break_skill,null);
  assert.throws(()=>C.jobs(full(),{roster,info:fixture}),/성장표/);
  const mapped=C.jobs(full(),{roster,engineKey:k=>'engine-'+k});assert.equal(mapped[0].party.units[0].key,'engine-'+keys[0]);
});
function summaries(c=C){
  const s=full(c),rs={alpha:{cosmo:{mean:10.5,top:20.25,clear:0.4}},beta:{cosmo:{mean:0,top:2,clear:0}},gamma:{cosmo:{mean:25.25,top:40.75,clear:1}}};
  assert.deepEqual(clean(c.summary(c.create(season),rs)),{teams:Object.fromEntries(season.bosses.map(b=>[b.key,{status:'empty',score:null,clear:null}])),total:null,done:0,need:3});
  let sum=c.summary(s,{});assert.equal(sum.done,0);assert.equal(sum.need,3);assert.equal(sum.total,null);assert.equal(sum.teams.alpha.status,'ready');
  sum=c.summary(s,{alpha:rs.alpha,beta:rs.beta});assert.equal(sum.done,2);assert.equal(sum.total,null);assert.equal(sum.teams.beta.score,0);assert.equal(sum.teams.beta.clear,0);
  sum=c.summary(s,rs);assert.equal(sum.done,3);assert.equal(sum.total,35.75);assert.equal(sum.teams.alpha.clear,0.4);
  assert.equal(c.summary(s,rs,'top').total,63);
  for(const mean of [null,undefined,NaN,Infinity,'20']){sum=c.summary(s,{...rs,gamma:{cosmo:{mean}}});assert.equal(sum.done,2);assert.equal(sum.total,null);}
  const partial=change(c,s,'alpha',{type:'remove',slot:0});assert.equal(c.summary(partial,rs).done,2);
}
test('summary mean/top, raw sums, zero, partial/null/nonfinite results, done/need',()=>summaries());
function imported(c=C){
  // Generate a real finalRankBrk row, not an invented approximation of it.
  const finals=Object.fromEntries(keys.map((k,i)=>[k,{stats:{atk:100+i},power:100+i,combat:{}}]));
  const bosses=season.bosses.map(b=>b.key),brk={name:'큐브 과부하',level:3};
  const teams=bosses.map((boss,i)=>Search.bossJobs({topQ:0.2},boss,6,[keys.slice(i*4,i*4+4)],finals,{})[0]);
  assert.notDeepEqual(teams[0].order,teams[0].keys,'fixture must expose accidental keys/order confusion');
  teams.forEach(t=>{t.leaderKey=t.order[3];t.party.leader=3;});
  const triple={teams},res={},levelOf=boss=>bosses.indexOf(boss)+4;
  for(const [i,t] of teams.entries())for(const b of [null,brk])res[Search.jobKey(t.boss,t.keys,i+4,b,t)]={cosmo:{mean:b?20+i:10+i,top:b?30+i:20+i,clear:0.5,frac:0.7,n:40},via:{},progs:[0.5,1],bs:b};
  const row=Search.finalRankBrk([triple],bosses,levelOf,[null,brk],res,'mean',1)[0],before=JSON.stringify(row);
  const state=c.fromSearch(row,season),jobs=c.jobs(state,{roster});assert.equal(jobs.length,3);
  row.teams.forEach((t,i)=>{assert.deepEqual(Array.from(state.teams[t.boss].draft.slots,m=>m.key),t.order);assert.equal(state.teams[t.boss].draft.leader,t.leaderKey);
    assert.equal(state.teams[t.boss].level,i+4);assert.deepEqual(clean(state.teams[t.boss].draft.brk),brk);
    assert.deepEqual(clean(jobs[i].party),P.serialize(state.teams[t.boss].draft));assert.equal(jobs[i].party.leader,3);
  });assert.equal(JSON.stringify(row),before);assert(!JSON.stringify(c.share(state)).includes('mean'));
  const fallback={teams:[{boss:'alpha',keys:keys.slice(0,4),level:0,brk:null,brkLv:null}]};
  const simple=c.fromSearch(fallback,season);assert.equal(simple.teams.alpha.level,0);assert.equal(simple.teams.alpha.draft.brk,null);
  assert.deepEqual(Array.from(simple.teams.alpha.draft.slots,m=>m.key),keys.slice(0,4));
  assert.deepEqual(clean(c.fromSearch({teams:[{boss:'alpha',order:['invalid']},null]},season)),clean(c.create(season)));
}
test('fromSearch actual finalRankBrk result: engine order/leader/level/brk, keys fallback',()=>imported());
function privacy(c=C){
  const s=full(c),expected=clean(s);s.info=fixture;s.results={alpha:{cosmo:{mean:123}}};s.account=fixture;s.profile={secret:123};
  for(const t of Object.values(s.teams)){t.result={secret:123};t.account=fixture;t.draft.info=fixture;t.draft.result={secret:123};t.draft.slots[0].stats={secret:123};}
  for(const save of [c.storage,c.share]){const out=save(s);assert.deepEqual(clean(out),expected);assert.notStrictEqual(out.teams.alpha.draft,s.teams.alpha.draft);assert(!/secret|stats|account|result|info|profile/.test(JSON.stringify(out)));}
  assert.equal(c.STORAGE_KEY,'direct.cosmo.v1');assert.equal(c.SHARE_PARAM,'cd');
  assert.deepEqual(clean(c.restore(c.storage(s),season)),expected);
}
test('storage/share recursive allowlist excludes results/account/final stats',()=>privacy());
// Browser UMD and in-memory mutation checks: never change the working module.
const source=fs.readFileSync(require.resolve('../cosmo_direct'),'utf8');
function load(code){const box={DirectParty:P};vm.createContext(box);vm.runInContext(code,box);return box.CosmoDirect;}
test('browser UMD control passes all mutation-protected behaviors',()=>{
  const c=load(source);for(const check of [defaults,duplicates,restoration,levels,growthJobs,summaries,imported,privacy])check(c);
});
const mutations=[
  ['allow duplicate put',"if(a.type==='put'&&Object.entries",'if(false&&Object.entries',duplicates],
  ['drop cross_dup detection','new Set(entries.map(e=>e.boss)).size>1','false',duplicates],
  ['ignore season mismatch','raw.seasonId!==s.id','false',restoration],
  ['restore duplicate members','!m||seen.has(m.key)','!m',restoration],
  ['ignore levelAll',"action.type==='levelAll'||b===action.boss","b===action.boss",levels],
  ['remove leader','const party=P.serialize(d,','d.leader=d.slots[0].key;const party=P.serialize(d,',growthJobs],
  ['ignore grown','const values=P.powers(d,','d.slots.forEach(m=>m.grown=false);const values=P.powers(d,',growthJobs],
  ['publish partial total','need>0&&done===need?total:null','total',summaries],
  ['wrong done count','total+=score;done++','total+=score;done+=0',summaries],
  ['discard search order','Array.isArray(t.order)?t.order:t.keys','t.keys',imported],
  ['leak state through storage','return {v:VERSION,seasonId:typeof','return {...state,v:VERSION,seasonId:typeof',privacy],
];
for(const [name,from,to,check] of mutations)test('mutation detected: '+name,()=>{
  assert(source.includes(from),name+' anchor');const mutant=load(source.replace(from,to));
  assert.throws(()=>check(mutant),assert.AssertionError,name+' must fail an assertion, not crash');
});
console.log(`${checks} cosmo direct groups passed (${mutations.length} mutations)`);
