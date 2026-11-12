// Real worker-result schema through ranking and all result renderers.
const assert = require('node:assert/strict');
const GS = require('../guild_search.js'), CS = require('../cosmo_search.js');
const V = require('../guild_view.js'), G = require('../data/guild_defense.json');
const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const unsupported = [{unit:'합성 구원자',slot:'잠재력',reason:'data',raw:'재난 대응 프로토콜 <검사>',critical:false}];
const result = {prog:.8,progs:[.6,1],via:{},clear:.5,n:2,
  cosmo:{top:100,mean:80,clear:.5,frac:.8,n:2},unsupported};
const keys = ['a','b','c','d'], job = {key:'j',keys,order:keys,level:0,sup:'none',party:{units:keys}};

function worker() { return {
  postMessage(m) { queueMicrotask(() => {
    this.onmessage({data:{type:'team',id:m.id,key:'j',result}});
    this.onmessage({data:{type:'done',id:m.id}});
  }); }, terminate() {}
}; }

async function main() {
  const res = await GS.runPhase({makeWorker:worker,jobs:[job],workers:1,runs:2,seed:1,stage:'synthetic',base:''}).promise;
  assert.deepEqual(res.j.unsupported, unsupported);
  const ranked = GS.rank(V,G,[job],res,[0,0,0,0],1,{banCoop:false});
  assert.deepEqual(ranked[0].unsupported, unsupported);
  const gh = GS.html({phase:'done',rows:ranked,sig:'',pool:4,combos:1,finalists:1,runs:2},
    {hasInfo:true,hasStats:true,sig:'',esc,label:k=>k});
  assert(gh.includes('지원하지 않음') && gh.includes('재난 대응 프로토콜 &lt;검사&gt;'));
  const bosses=['one','two','three'], teams=bosses.map(b=>({keys,order:keys}));
  const cr=Object.fromEntries(bosses.map(b=>[CS.jobKey(b,keys,1),result]));
  for (const rows of [CS.finalRank([{teams}],bosses,1,cr,'top',1),
      CS.finalRankBrk([{teams}],bosses,()=>1,[null],cr,'top',1)]) {
    assert.equal(rows.length,1);
    assert(rows[0].teams.every(t=>t.unsupported===unsupported));
    for (const team of [null,()=>'<div>team</div>']) {
      const html=CS.table(rows[0],'top',{esc,label:k=>k,bossName:k=>k,team});
      assert(html.includes('지원하지 않음') && html.includes('재난 대응 프로토콜 &lt;검사&gt;'));
      assert(!html.includes('<검사>'));
    }
  }
  assert.equal(GS.unsupportedHtml([{}],esc),'');
  console.log('PASS: unsupported worker payload → guild/cosmo ranking → escaped result names');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
