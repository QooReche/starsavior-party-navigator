const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process');
const source=fs.readFileSync(require.resolve('../party_template.html'),'utf8'),old=cp.execFileSync('git',['show','f4afb12:party_template.html'],{encoding:'utf8'});
function render(src,t,fn){const ctx=vm.createContext({BYKEY:Object.fromEntries(t.order.map(key=>[key,{key}])),LEADKEY:null,seasonBreakBar:(t,compact=false)=>'break:'+compact});
  vm.runInContext("function card(x,role){return x.s.key+':'+role+':'+LEADKEY;}",ctx);
  vm.runInContext(src.match(/function gsTeam\(t\)\{[^\n]+/)[0],ctx);
  const start=src.indexOf('function csTeam('),end=src.indexOf('function seasonBreakBar(',start);
  vm.runInContext(src.slice(start,end),ctx);
  return ctx[fn](t);
}
function check(src){for(const fn of ['gsTeam','csTeam'])for(const leaderKey of [undefined,'d']){
  const t={order:['a','b','c','d'],leaderKey};assert.equal(render(src,t,fn),render(old,t,fn));
}}
check(source);
for(const [from,to] of [['[2,0,1,3]','[0,1,2,3]'],['const before=LEADKEY;LEADKEY=t.leaderKey||t.order[0];','const before=LEADKEY;LEADKEY=t.order[0];']]){
  assert(source.includes(from));assert.throws(()=>check(source.replace(from,to)),{code:'ERR_ASSERTION'});
}
console.log('PASS guild/cosmo team-card bytes, leader/slot order, 2 mutations');
