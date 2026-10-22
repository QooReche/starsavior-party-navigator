const assert=require('node:assert/strict'),Share=require('../share_state.js');
const contents=[{key:'op',stages:[{tab:'1',name:'1-1'},{tab:'37',name:'37-3'}]},
  {key:'cosmo',stages:[{tab:'a',name:'길레 2단계'}]}],breaks=['특이점 관측','스타피어서'];
const parse=q=>Share.parse(q,contents,breaks);
for(const g of ['1','0.8','1.25','manual','myinfo']){
  const state={c:'cosmo',s:'a|길레 2단계',g,m:'manual',rk:5,b:'특이점 관측',b2:''};
  if(g==='manual')state.p=123456;
  assert.deepEqual(parse(Share.stringify(state)),state);
}
assert.deepEqual(parse('?c=bad&s=bad&g=no&m=bad&rk=6&b=bad'),{c:'op',s:'1|1-1',g:'1',m:'auto',rk:0,b:null});
assert.deepEqual(parse('?c=cosmo&s=37%7C37-3'),{c:'cosmo',s:'a|길레 2단계'});
for(const p of ['-1','0','NaN','Infinity','1e5','1.5','9999999999999999',''])assert.equal(parse('?g=manual&p='+p).p,0);
for(const rk of ['-1','5.1','Infinity','01',''])assert.equal(parse('?rk='+rk).rk,0);
assert.deepEqual(parse('?mode=manual&pick=abc&grow=0.8'),{m:'manual',g:'0.8'});
assert.equal(parse('?m=auto&mode=manual').m,'auto');
assert.deepEqual(parse(''),{});
const url=new URL(Share.url('https://example.test/index.html?owned=secret&pick=secret#myinfo=secret',
  {c:'op',s:'37|37-3',g:'myinfo',m:'auto',rk:0,owned:['secret'],myinfo:{units:['secret']},pw:{secret:99},p:99}));
assert.equal(url.hash,'');assert(!url.href.includes('secret'));assert(!url.searchParams.has('p'));
assert.deepEqual([...url.searchParams.keys()],['c','s','g','m','rk']);
console.log('PASS query round trips, validation, legacy aliases, public allowlist');

// Execute the actual page restore/mode functions against stored view values.
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const section=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
function restore(query,info=null){
  const els={content:{value:'0'},tab:{value:''},stage:{value:'0'},grow:{value:'0.8'},mypow:{value:'77777'},rk:{value:'5'},'m-auto':{},'m-manual':{}};
  const owned=breaks.map(b=>({dataset:{b},checked:false}));
  const ctx=vm.createContext({SHARE:parse(query),contents,MI:{info},MODE:'auto',$:id=>els[id],
    document:{querySelectorAll:()=>owned},showInfo(){},showPow(){},
    LS:{set(){throw Error('URL restore must not write preferences')}},
    refreshTabs(){els.tab.value='';ctx.cur=contents[+els.content.value].stages},
    refreshStages(){ctx.cur=contents[+els.content.value].stages.filter(s=>s.tab===els.tab.value)}});
  vm.runInContext(section('function setMode(', 'document.querySelectorAll(\'input[name="mode"]\')'),ctx);
  vm.runInContext(section('function applyShare(){','setMode(LS.get("mode")'),ctx);
  vm.runInContext('applyShare()',ctx);
  return {els,ctx,owned};
}
const restored=restore('?c=cosmo&s=a%7C길레+2단계&g=manual&p=123456&m=manual&rk=3&b=스타피어서');
assert.equal(restored.els.content.value,'1');assert.equal(restored.ctx.cur[+restored.els.stage.value].name,'길레 2단계');
// 추천은 내 정보로만: 옛 링크의 육성(g)·전투력(p)은 적용하지 않고 표시만 남긴다
assert.equal(restored.els.grow.value,'0.8');assert.equal(restored.els.mypow.value,'77777');assert.equal(restored.ctx.SHARE.oldGrow,true);
assert.equal(restored.ctx.MODE,'manual');assert.equal(restored.els.rk.value,'3');assert(restored.owned[1].checked);
assert.equal(restore('?g=myinfo').els.grow.value,'0.8');assert.equal(restore('?g=myinfo').ctx.SHARE.oldGrow,undefined);
assert.equal(restore('?g=bad&m=bad&rk=bad').els.grow.value,'0.8');
assert.equal(restore('?mode=manual&pick=old').ctx.MODE,'manual');
console.log('PASS actual page restore, no storage writes, old growth ignored, legacy mode');
