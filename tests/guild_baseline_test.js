'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const GS=require('../guild_search'),P=require('../party_placement'),V=require('../guild_view');
const G=require('./guild_fixture')(30111),S=structuredClone(G.search),keys=['a','b','c','d'];
const results=Object.fromEntries(keys.map((k,i)=>[k,{power:100-i,stats:{hp:100+i*100,def:i*100,spd:100+i},combat:{}}]));
const cls={a:'디펜더',b:'서포터',c:'캐스터',d:'레인저'},tiers=[0,0,0,0];
assert.equal(require('../data/guild_defaults.json').search.legacyBaseline,false);
const check=()=>{
 const off=GS.screenJobs(S,G,V,[keys],results,cls,tiers);
 assert.equal(JSON.stringify(GS.screenJobs({...S,legacyBaseline:false},G,V,[keys],results,cls,tiers)),JSON.stringify(off));
 assert.equal(JSON.stringify(GS.finalJobs({...S,legacyBaseline:false},G,V,[keys],results,cls,tiers)),JSON.stringify(GS.finalJobs(S,G,V,[keys],results,cls,tiers)));
 const on={...S,legacyBaseline:true},expected=P.baseline(keys,results);
 const first=GS.screenJobs(on,G,V,[keys],results,cls,tiers);
 assert.notDeepEqual(first[0].party,off[0].party);
 const finals=GS.finalJobs(on,G,V,[keys],results,cls,tiers);
 assert.equal(finals.length,GS.finalJobs(S,G,V,[keys],results,cls,tiers).length);
 for(const j of [...first,...finals]){
  assert.deepEqual(j.order,expected.order);assert.equal(j.leaderKey,expected.leaderKey);
  assert.equal(j.party.units[j.party.leader].key,expected.leaderKey);
 }
 const breaks=GS.breakJobs([first[0]],[{name:'스타피어서',level:1}],results,cls,tiers,G);
 assert(breaks.length>0);for(const j of breaks){assert.deepEqual(j.order,expected.order);assert.equal(j.leaderKey,expected.leaderKey);}
};
check();
// Turning off the new branch must break these assertions.
const original=GS.screenJobs;
try{GS.screenJobs=(s,...args)=>original({...s,legacyBaseline:false},...args);assert.throws(check);}finally{GS.screenJobs=original;}
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const src=html.slice(html.indexOf('function searchPlacementTag('),html.indexOf('const gsLabel='));
const cx={D:{guild:{search:structuredClone(S)}},guildIdentity:()=>({}),MI:{hash:'test'},EXCL:new Set(),gsTiers:()=>[],GSR:{banCoop:false},GuildSearch:GS,ownedSimBreaks:()=>[]};
vm.runInNewContext(src+';globalThis.sig=gsSig',cx);
const before=cx.sig();cx.D.guild.search.legacyBaseline=true;assert.notEqual(cx.sig(),before);cx.D.guild.search.legacyBaseline=false;assert.equal(cx.sig(),before);
const {battleScores}=require('../tools/evaluate_guild_time');
const client={...G,season:{boss:{engine:'client'}}},j={level:0};
assert.deepEqual(battleScores(client,j,tiers,{progs:[1,.2],guild:{base_scores:[101,203]}}),[101,203]);
assert.throws(()=>battleScores(client,j,tiers,{progs:[1],guild:{base_scores:[]}}));
console.log('PASS legacy baseline: off bytes, on placement/leader, breaks, signature, mutation, client holdout scores');
