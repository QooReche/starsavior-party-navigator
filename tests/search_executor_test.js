const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../search_executor.js'),'utf8');
function clockReplacement(src=source){
 const early=[],late=[],cleared=[];
 const c=vm.createContext({setTimeout:()=>early.push('set'),clearTimeout:()=>early.push('clear'),Date:{now:()=>100}});
 vm.runInContext(src,c);
 const executor=c.SearchExecutor.shared({capacity:()=>1,priority:()=>0,loadMs:()=>1000});
 // Browser clock installation can happen after the page/executor has loaded.
 c.setTimeout=(fn,ms)=>{late.push({fn,ms});return 'late'};c.clearTimeout=id=>cleared.push(id);
 const arm=executor.watch([{_job:0,_last:100,_ready:true}],()=>240000,()=>true,()=>{});
 arm();assert.equal(late.length,1);assert.equal(late[0].ms,240000);arm.cancel();
 assert.equal(early.length,0);assert.equal(cleared.at(-1),'late');
}
clockReplacement();
assert.throws(()=>clockReplacement(source.replace('((...args)=>setTimeout(...args))','setTimeout')),assert.AssertionError);
assert.throws(()=>clockReplacement(source.replace('((...args)=>clearTimeout(...args))','clearTimeout')),assert.AssertionError);
const E=require('../search_executor'),made=[];
const pool=E.workerPool(()=>{const w={terminate(){this.ended=(this.ended||0)+1}};made.push(w);return w;});
assert.equal(pool.get(0),pool.get(0));pool.get(1);pool.drop(made[0]);pool.drop(made[0]);pool.close();pool.close();
assert.deepEqual(made.map(w=>w.ended),[1,1]);assert.throws(()=>pool.get(0),/닫힌/);
console.log('PASS late clock installation (2 mutations), common pool reuse/drop/close lifecycle');
