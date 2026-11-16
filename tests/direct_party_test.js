const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const P=require('../direct_party'),M=require('../myinfo_reco'),S=require('../star_link'),Share=require('../share_state');
const growth=require('../data/growth.json'),slots=require('../data/myinfo_slots.json'),priority=require('../data/journey_priority.json');
const raw=require('./fixtures/myinfo_synthetic.json');
const roster=Object.entries(growth.assumed.units).map(([key,s],i)=>({key,uid:s.uid,el:i%2?'sun':'moon'}));
const owned=roster.filter(s=>raw.units.some(u=>u.id===s.uid)),keys=owned.slice(0,4).map(s=>s.key);
let checks=0;function test(name,fn){fn();checks++;console.log('PASS '+name);}
function full(p=P){let d=p.empty();keys.forEach((key,slot)=>d=p.edit(d,{type:'put',key,slot}));return d;}
function permutations(xs){return xs.length?xs.flatMap((x,i)=>permutations(xs.filter((_,j)=>i!==j)).map(t=>[x,...t])):[[]];}
function context(){const info=structuredClone(raw);for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};return {info,roster,growth,content:'op',slots,priority};}
const request=(p,party)=>p.signature({party,stage:{content:'op',tab:'1',name:'1-1'},brk:{name:'큐브 과부하',level:3},seed:1024,runs:100,options:{build:'standard',rules_override:{power_penalty:'model'}},versions:{engine:'x',data:'y',policy:M.OVERWRITE_VERSION,preset:growth.assumed.version}});
function payloads(p=P){const signatures=new Set();for(const order of permutations(keys))for(const leader of keys){
  const d={...full(),slots:order.map(key=>({key,grown:false})),leader};
  const party=p.serialize(d);
  assert.deepEqual(JSON.parse(JSON.stringify(party.units.map(u=>u.key))),order);
  assert.equal(party.leader,order.indexOf(leader));signatures.add(request(p,party));
}assert.equal(signatures.size,96);}
test('24 arrangements × 4 leaders: exact payload, distinct signatures',()=>payloads());
test('screen/engine inverse and recommendation legacy order',()=>{
  for(const order of permutations(keys)){assert.deepEqual(P.toScreen(P.toEngine(order)),order);assert.deepEqual(P.toEngine(order),[order[1],order[2],order[0],order[3]]);}
  const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
  const start=html.indexOf('function simParty('),end=html.indexOf('const simSigB=',start),code=html.slice(start,end);
  for(const order of permutations(keys))for(const leader of keys){
    const c={DirectParty:P,arrangeOf:()=>({order,lead:leader}),QK:{d:{sv:Object.fromEntries(keys.map(k=>[k,[0,150,200,30,0,10]]))}},Quick:{MUL:1},ekey:k=>k};
    vm.createContext(c);vm.runInContext(code,c);const next=c.simParty({combo:[],ek:keys,b:{}});
    vm.runInContext(code.replace('DirectParty.toEngine(ar.order)','[ar.order[1],ar.order[2],ar.order[0],ar.order[3]]'),c);
    assert.equal(JSON.stringify(next),JSON.stringify(c.simParty({combo:[],ek:keys,b:{}})));
  }
});
test('validation: count, duplicate uid, owned, element, leader, unsupported',()=>{
  assert(P.validate(full(),{roster,info:raw}).ok);
  assert(P.validate(P.empty(),{roster}).errors.some(e=>e.code==='count'));
  assert(P.validate({...full(),leader:'missing'},{roster}).errors.some(e=>e.code==='leader'));
  const d=full();d.slots[1]=d.slots[0];assert(P.validate(d,{roster}).errors.some(e=>e.code==='duplicate'));
  const alias={...roster.find(s=>s.key===keys[0]),key:'alias'};d.slots[1]={key:'alias'};
  assert(P.validate(d,{roster:roster.concat(alias)}).errors.some(e=>e.code==='duplicate'));
  const missing=roster.find(s=>!raw.units.some(u=>u.id===s.uid));d.slots[1]={key:missing.key};
  assert(P.validate(d,{roster,info:raw}).errors.some(e=>e.code==='unowned'));
  assert(P.validate(full(),{roster,restrict:'chaos'}).errors.some(e=>e.code==='element'));
  for(const content of ['guild','cosmo'])assert(P.validate(full(),{roster,content}).errors.some(e=>e.code==='unsupported'));
  assert.throws(()=>P.serialize(P.empty()));assert.throws(()=>P.serialize(draftDuplicate()));
  function draftDuplicate(){const d=full();d.slots[1]=d.slots[0];return d;}
});
test('slot priority, swapping, leader/growth identity, explicit arrange, remove',()=>{
  assert.equal(P.edit(P.empty(),{type:'put',key:keys[0]}).slots[2].key,keys[0],'first empty follows screen order');
  const d=P.edit(full(),{type:'grown',slot:0,value:true}),frozen=JSON.stringify(d);
  let next=P.edit(d,{type:'swap',a:0,b:3});assert.equal(next.slots[3].key,keys[0]);assert(next.slots[3].grown);assert.equal(next.leader,keys[0]);assert.equal(JSON.stringify(d),frozen);
  next=P.edit(next,{type:'arrange',order:keys});assert(next.slots[0].grown);assert.equal(next.leader,keys[0]);
  assert.deepEqual(P.edit(next,{type:'put',key:keys[0],slot:1}),next);
  next=P.edit(next,{type:'remove',slot:0});assert.equal(next.leader,keys[1]);
  next=P.edit(next,{type:'put',key:keys[0],slot:2});assert.equal(next.slots[2].key,keys[0]);assert.equal(next.slots[0],null);
  assert.deepEqual(P.edit(next,{type:'clear'}),P.empty());
});
function overwriteParity(p=P){
  const cx=context(),before=JSON.stringify(cx.info),base=M.profile(cx.info,roster,growth,'op');let changed=0;
  for(let mask=0;mask<16;mask++){
    const d=full();d.slots.forEach((s,i)=>s.grown=!!(mask&(1<<i)));
    const expected=M.overwrite(cx.info,roster,growth,'op',{excluded:roster.filter(s=>!d.slots.some(m=>m.key===s.key&&m.grown)).map(s=>s.key),slots,priority});
    const actual=p.powers(d,cx);assert.equal(actual.errors.length,0);
    d.slots.forEach((s,i)=>{assert.deepEqual(JSON.parse(JSON.stringify(actual.values[i])),expected.profile.results[s.key]);
      if(!s.grown)assert.deepEqual(actual.values[i],base.results[s.key]);else if(actual.values[i].power!==base.results[s.key].power)changed++;
    });assert.equal(actual.total,actual.values.reduce((a,r)=>a+r.power,0));
  }assert(changed>0,'fixture must exercise growth');assert.equal(JSON.stringify(cx.info),before);
}
test('all 16 per-slot overwrite combinations equal recommendation power/combat, input immutable',()=>overwriteParity());
test('StarLink copied-account recalculation, capacity warning, overwrite registration survives off',()=>{
  const cx=context();cx.info.units.forEach(u=>u.level=100);cx.info.star_link={level:200,source:[],slots:[{index:0,id:cx.info.units.at(-1).id}]};
  const before=JSON.stringify(cx.info),d=full();d.slots[0].grown=true;
  const off=P.powers(d,cx),on=P.powers({...d,starLink:true},cx),offAgain=P.powers(d,cx);
  assert.deepEqual(off.values,offAgain.values);assert(on.warnings.some(s=>s.includes('실제 빈 슬롯')));
  assert(off.changes[keys[0]].changedFields.includes('level'),'must exercise overwrite link registration');
  const expected=M.overwrite(cx.info,roster,growth,'op',{excluded:roster.filter(s=>s.key!==keys[0]).map(s=>s.key),slots,priority});
  const ids=[...new Set([...expected.info.star_link.slots.map(s=>s.id),...keys.map(k=>roster.find(s=>s.key===k).uid)])];
  const profile=M.profile(S.withSlots(expected.info,ids),roster,growth,'op');
  on.values.forEach((v,i)=>assert.deepEqual(v,profile.results[keys[i]]));
  assert.equal(JSON.stringify(cx.info),before);assert(on.values.some((v,i)=>v.power!==off.values[i].power));
  const fixed=P.powers({...d,starLink:true},{...cx,content:'cosmo'});assert(fixed.warnings.some(s=>s.includes('고정 레벨')));
});
test('signature includes final stats, stage, break level, seed, runs, all options/versions',()=>{
  const input={party:P.serialize(full()),stage:{content:'op',name:'one'},brk:{name:'큐브 과부하',level:1},seed:1,runs:100,options:{rng_streams:true,build:'standard'},versions:{engine:'e',data:'d',policy:'p'}};
  const baseline=P.signature(input);
  for(const f of [v=>v.party.units.reverse(),v=>v.party.leader=2,v=>v.stage.name='two',v=>v.brk.level=2,v=>v.seed++,v=>v.runs++,v=>v.options.rng_streams=false,v=>v.versions.engine='f',v=>v.versions.data='f',v=>v.versions.policy='f',v=>v.party.units[0].power=123]){
    const next=structuredClone(input);f(next);assert.notEqual(P.signature(next),baseline);
  }
  assert.equal(P.signature({...input,options:{build:'standard',rng_streams:true}}),baseline);
});
function isolation(p=P){const local=full(),remote=p.edit(local,{type:'swap',a:0,b:1}),state=p.restore(local,remote);assert.equal(p.storage(state),null);state.draft=p.edit(state.draft,{type:'grown',slot:0,value:true});assert.equal(p.storage(state),null);assert.deepEqual(local,full());}
test('local/share allowlist, received session edits never replace local',()=>{
  const dirty={...full(),account:raw,result:{secret:99},power:123,profile:{stats:123}};dirty.slots[0].power=999;
  assert.deepEqual(P.draft(dirty),full());assert.deepEqual(P.storage(P.restore(dirty,null)),full());isolation();
  const q=Share.stringify({pm:'direct',dp:dirty,account:raw}),out=Share.parse('?'+q,[],[]);
  assert.deepEqual(out.dp,P.share(full()));assert(!q.includes('power'));assert(!q.includes('profile'));assert(!q.includes('account'));assert.equal(out.pm,'direct');
  assert.equal(Share.parse('?'+q.replace('pm=direct','pm=reco'),[],[]).pm,'reco');
  assert.equal(Share.parse('?pm=manual&dp=bad',[],[]).dp,undefined);
  assert.deepEqual(P.draft({v:99}),P.empty());assert.equal(P.draft({v:1,brk:{name:'x',level:100}}).brk,'auto');
});
// Execute mutated production modules in an isolated VM; each protected behavior must fail.
const source=fs.readFileSync(require.resolve('../direct_party'),'utf8');
function mutant(change,M2=M){const code=change(source);assert.notEqual(code,source);const c={MyInfoReco:M2,StarLink:S};vm.createContext(c);vm.runInContext(code,c);return c.DirectParty;}
test('mutation harness control: unchanged VM passes protected behavior',()=>{const p=mutant(s=>s.replace('// Pure DIRECT','// Control Pure DIRECT'));payloads(p);overwriteParity(p);isolation(p);});
test('mutation detected: silently restore automatic rearrangement',()=>assert.throws(()=>payloads(mutant(s=>s.replace('const units=d.slots.map','const units=[...d.slots].sort((a,b)=>a.key.localeCompare(b.key)).map')))));
test('mutation detected: remove leader from signature',()=>assert.throws(()=>payloads(mutant(s=>s.replace('leader:party.leader,stage','stage')))));
test('mutation detected: overwrite → legacy assume',()=>{
  const old={...M,overwrite(info,roster,growth,content,{excluded}){let profile=M.profile(info,roster,growth,content);const changes={};
    for(const s of roster)if(!excluded.includes(s.key)&&profile.units[s.key]){const a=M.assume(s.key,info,growth);changes[s.key]=a;profile=M.assumedProfile(profile,a,info,growth,content);}
    return {info,profile,changes,errors:[]};}};
  assert.throws(()=>overwriteParity(mutant(s=>s.replace('// Pure DIRECT','// legacy Pure DIRECT'),old)));
});
test('mutation detected: received draft overwrites local',()=>assert.throws(()=>isolation(mutant(s=>s.replace('state.shared?null:draft(state.draft)','draft(state.draft)')))));
console.log(`${checks} direct contract groups passed (96 payloads/signatures, 96 recommendation parity cases, 16 growth combinations, 4 mutations)`);
