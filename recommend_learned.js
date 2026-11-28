// General-stage U360 policy. Matches tools/learned_reco_measure.js without its transport.
(function(root){
'use strict';
const node=typeof module!=='undefined'&&module.exports;
const L=node?require('./cosmo_learned.js'):root.CosmoLearned;
const U=node?require('./ui_shared.js'):root.UiShared,id=U.teamKey;
const count=n=>n<4?0:n*(n-1)*(n-2)*(n-3)/24;
function encoder(rows,ctx){
 const ix=new Map(),meta=new Map(rows.map(x=>[x.key,x])),index=k=>{if(!ix.has(k))ix.set(k,ix.size);return ix.get(k);};
 for(const x of rows)for(const kind of ['unit','front','back','leader'])index(kind+':'+x.key);
 for(const field of ['cls','el']){const vs=[...new Set(rows.map(x=>x[field]))].sort();for(let a=0;a<vs.length;a++)for(let b=a;b<vs.length;b++)index(field+':'+vs[a]+'/'+vs[b]);}
 for(const b of ctx.breaks)index('break:'+b);index('break:');
 function encode(keys){const t=ctx.team(keys),p=ctx.party(t),out=new Map(),add=k=>{const i=ix.get(k);if(i===undefined)throw Error('Unknown feature '+k);out.set(i,(out.get(i)||0)+1);};
  p.units.forEach((u,i)=>{const k=t.keys.find(k=>ctx.engineKey(k)===u.key);add('unit:'+k);add((i<2?'front:':'back:')+k);if(i===p.leader)add('leader:'+k);});
  for(let a=0;a<4;a++)for(let b=a+1;b<4;b++)for(const f of ['cls','el'])add(f+':'+[meta.get(keys[a])[f],meta.get(keys[b])[f]].sort().join('/'));
  add('break:'+(ctx.breakFor(t)?.name||''));return [...out];
 }
 return {encode,size:ix.size};
}
function init(sc,settings,rows,pool){
 if(!sc.full||sc.fullDone||!settings?.value||sc.union)return;
 const learned={...settings,K:sc.fullN};L.config({learned},rows.length);
 sc.union={settings:{learned},rows,pool:[...pool],base:sc.full.slice(),sample:null,observed:{},outside:null,teams:{},
  total:sc.full.length+Math.min(learned.S,count(rows.length))+Math.min(learned.outside,count(rows.length)-count(pool.size))};
}
const destination=(sc,i)=>i===-2?sc.union.observed:i<0?sc.res0:i?sc.res2:sc.res;
function progress(sc){const u=sc.union;return u?{got:Object.keys(u.observed).length+Object.keys(sc.res0).length,all:u.total}:{got:sc.got||0,all:sc.left||0};}
function partial(sc){return sc.union?{...sc.union.observed,...sc.res0}:sc.res0;}
function restore(sc,all){
 const u=sc?.union;if(!u)return all;const seen=new Set(all.map(t=>id(t.keys)));
 const keys=sc.done&&!sc.fullDone?Object.keys(partial(sc)):u.outside||[];
 for(const k of keys)if(!seen.has(k)&&u.teams[k]){all.push(u.teams[k]);seen.add(k);}return all;
}
// leg returns a promise only after all its worker results have been stored. Samples are
// training observations, never promotion candidates after a completed sweep.
async function prepare(sc,ctx,leg,stale=()=>false){
 const u=sc.union;if(!u||sc.fullDone)return;
 const check=()=>{if(stale())throw Error('취소');},remember=keys=>{const k=id(keys),t=ctx.add(keys);u.teams[k]=t;return k;};
 const run=async(i,keys)=>{check();if(keys.length)await leg(i,keys);check();};
 check();
 if(!u.sample)u.sample=await L.sample(u.settings,u.rows,ctx.seed,stale);
 u.total=u.base.length+u.sample.length+Math.min(u.settings.learned.outside,count(u.rows.length)-count(u.pool.length));
 await run(-2,u.sample.map(remember).filter(k=>!u.observed[k]));
 if(!u.outside){
  const model=await L.train(encoder(u.rows,ctx),u.sample,u.sample.map(k=>u.observed[id(k)].prog),u.settings.learned,stale);
  const pool=new Set(u.pool),top=new L.Heap(u.settings.learned.outside);
  await L.scan(u.settings,u.rows,keys=>{if(keys.some(k=>!pool.has(k)))top.put({keys,id:L.id(keys),score:model.predict(keys)});},stale);
  check();u.rho=model.rho;u.outside=top.sorted().map(x=>remember(x.keys));
  // F wins ties, irrespective of which phase/worker finishes first.
  sc.full=u.base.concat(u.outside);u.total=u.base.length+u.sample.length+u.outside.length;
 }
 for(const k of u.outside)ctx.add(u.teams[k].keys);
 await run(-3,u.outside.filter(k=>!sc.res0[k]));
}
const api={encoder,init,destination,progress,partial,restore,prepare};
if(node)module.exports=api;else root.RecommendLearned=api;
})(typeof window!=='undefined'?window:globalThis);
