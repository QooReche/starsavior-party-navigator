const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const Share=require('../share_state'),Search=require('../guild_search'),View=require('../guild_view');
const G=require('./guild_fixture')(30101);
const current=require('./guild_fixture')(30112);
current.title='길드방어전(시즌5 11/26~12/03)';
const released=[{key:'guild',seasonId:current.season.id,stages:[]}];
assert.equal(Share.parse(Share.stringify({c:'guild',gs:30112}),released,[]).guildExpired,false);
assert.equal(Share.parse('?c=guild&gs=30111',released,[]).guildExpired,true);
assert.equal(Share.parse('?c=guild',released,[]).guildExpired,true);
const escape=s=>String(s);
const play=View.panelHtml(current,null,7,Date.parse('2026-12-03T03:59:59+09:00'),escape);
const settled=View.panelHtml(current,null,7,Date.parse('2026-12-03T04:00:00+09:00'),escape);
assert.match(play,/진행 중/);assert.doesNotMatch(play,/gd-stale/);
assert.match(settled,/결산 중/);assert.match(settled,/gd-stale/);
assert.match(play,/카본펑크 칸/);
assert.doesNotMatch(play,/undefined/);
const contents=[{key:'guild',seasonId:30101,stages:[{tab:'S1',name:'6단계'}]}];
const old=Share.parse('?c=guild&s=old',contents,[]);
assert.equal(old.gs,30111);assert.equal(old.guildExpired,true);assert.equal(old.s,'old');
const now=Share.parse(Share.stringify({c:'guild',gs:30101,s:'S1|6단계'}),contents,[]);
assert.equal(now.gs,30101);assert.equal(now.guildExpired,false);
assert.equal(Share.parse('?c=guild&gs=invalid',contents,[]).guildExpired,true);
const keys=['a','b','c','d'],changed={...G,dataVersion:'different'};
assert.notEqual(Search.jobKey(keys,0,'none',[],null,null,G),Search.jobKey(keys,0,'none',[],null,null,changed));
const cls=Object.fromEntries(keys.map(k=>[k,'캐스터'])),results=Object.fromEntries(keys.map(k=>[k,{power:1,stats:{},combat:{}}]));
const job=Search.screenJobs(G.search,G,View,[keys],results,cls,[0,0,0,0])[0];
assert.equal(job.options.guild.seasonId,30101);assert.equal(job.options.guild.dataVersion,G.dataVersion);
assert.throws(()=>Search.rankStats(View,G,0,[],.5,[.5],0),/점수 자료/);
assert.throws(()=>Search.rankStats(View,G,0,[],.5,[.5,.5],0,{base_scores:[1]}),/점수 자료/);
// 실제 판별 기본 점수와 .5 반올림. 진행도 평균으로 점수를 다시 만들면 실패함.
const rank=Search.rankStats(View,G,0,[1,0,0,0],.5,[.2,.8],0,{base_scores:[1,11]});
const pct=View.extraPct(G,0,[1,0,0,0]);
const scores=[1,11].map(n=>Math.floor((n*(100+pct)+50)/100));
assert.equal(rank.top,scores[1]);assert.equal(rank.mean,Math.round((scores[0]+scores[1])/2));
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
// All editors share stage/support normalization, and links preserve only validated options.
{
  const current=require('../data/guild_defense.json'),sup=String(current.supports[0].id);
  const selection={level:3,tiers:[1,0,0,0],support:sup};
  const opts=View.battleOptions(current,selection,current.defaultStep);
  assert.equal(opts.seasonId,current.season.id);assert.equal(opts.level,3);assert.equal(opts.support,sup);
  assert.deepEqual(opts.sets,[0,0,0,0]);
  const lower=View.battleOptions(current,selection,current.steps[0].step);
  assert.equal(lower.level,0);assert.deepEqual(lower.sets,[0,0,0,0]);assert.equal(lower.support,sup);
  assert.equal(View.normSel(current,{support:'stale'}).support,'none');
  const ss=require('../share_state'),contents=[{key:'guild',seasonId:current.season.id,stages:[]}];
  const round=ss.parse(ss.stringify({c:'guild',gs:current.season.id,go:selection}),contents,[]);
  assert.deepEqual(round.go,selection);assert.equal(round.guildExpired,false);
  // The page normalizes parsed links with the active season before storage/run/share.
  const normalized=View.normSel(current,round.go);
  assert.deepEqual(normalized,{...selection,tiers:[0,0,0,0]});
  assert.deepEqual(ss.parse(ss.stringify({c:'guild',gs:current.season.id,go:normalized}),contents,[]).go,normalized);
  assert(ss.parse('?c=guild',contents,[]).guildExpired);
}
const sigCode=html.slice(html.indexOf('function simSignature('),html.indexOf('const simSig=('));
const c={};vm.createContext(c);vm.runInContext(sigCode,c);
const sig=guild=>c.simSignature({ck:'guild',guild,party:()=>({units:keys})},{tab:'same',name:'same'},null,null,100);
assert.notEqual(sig({seasonId:30101,dataVersion:'a'}),sig({seasonId:30102,dataVersion:'a'}));
assert.notEqual(sig({seasonId:30101,dataVersion:'a'}),sig({seasonId:30101,dataVersion:'b'}));
const mutant={};vm.createContext(mutant);vm.runInContext(sigCode.replace('x.guild?[x.guild]:[]','[]'),mutant);
assert.equal(mutant.simSignature({ck:'guild',guild:{seasonId:1},party:()=>keys},{tab:'a',name:'b'},null,null,100),
             mutant.simSignature({ck:'guild',guild:{seasonId:2},party:()=>keys},{tab:'a',name:'b'},null,null,100));
(async()=>{
  const guild={seasonId:30101,base_scores:[1,11]};
  const phase=Search.runPhase({jobs:[job],runs:2,seed:1,workers:1,stage:'guild/S1/6단계',base:'',
    makeWorker:()=>({terminate(){},postMessage(m){setImmediate(()=>{
      this.onmessage({data:{type:'team',id:m.id,key:job.key,result:{prog:.5,progs:[.2,.8],n:2,via:{},guild}}});
      this.onmessage({data:{type:'done',id:m.id}});
    });}})});
  const received=(await phase.promise)[job.key];
  assert.deepEqual(received.guild,guild);
  assert.deepEqual(Search.rankStats(View,G,0,[1,0,0,0],received.prog,received.progs,0,received.guild),rank);
  console.log('PASS guild season share, worker identity/score transport, scores, precise cache and mutation');
})().catch(e=>{console.error(e);process.exitCode=1;});
