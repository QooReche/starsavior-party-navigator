// 계정·보스별 즉석 점수 회귀. 전투력 합·quick 분류기는 사용하지 않음.
(function(root) {
  'use strict';
  const GS = typeof module !== 'undefined' && module.exports ? require('./guild_search.js') : root.GuildSearch;
  const id = keys => keys.slice().sort().join('+');
  function random(seed) { let s=seed>>>0; return () => {s=(s+0x6D2B79F5)>>>0;let t=s;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;}; }
  function config(S, units) {
    const c=S.learned;
    for(const k of ['S','m','K','M','A','overlapStarts','overlapKeep','folds','epochs'])
      if(!Number.isInteger(c[k]) || c[k] < (['m','M','overlapStarts','overlapKeep'].includes(k)?0:1)) throw Error('학습 선별 설정 오류: '+k);
    if(c.S < units*c.m || c.folds<2 || !(c.ridge>0) || !(c.minCorrelation>=-1 && c.minCorrelation<=1) || !(c.missThreshold>=0 && c.missThreshold<=1)) throw Error('학습 선별 설정·표본 상한 오류');
    return c;
  }
  // 작은 최솟값 힙. 동점은 키 오름차순으로 결정해서 순회/워커 순서에 독립.
  const better=(a,b)=>a.score-b.score || (a.id<b.id?1:a.id>b.id?-1:0);
  class Heap {
    constructor(n){this.n=n;this.a=[];}
    put(e){const a=this.a;if(!this.n)return;if(a.length<this.n){a.push(e);let i=a.length-1;while(i){const p=(i-1)>>1;if(better(a[i],a[p])>=0)break;[a[i],a[p]]=[a[p],a[i]];i=p;}return;}
      if(better(e,a[0])<=0)return;a[0]=e;let i=0;for(;;){let j=2*i+1;if(j>=a.length)break;if(j+1<a.length&&better(a[j+1],a[j])<0)j++;if(better(a[i],a[j])<=0)break;[a[i],a[j]]=[a[j],a[i]];i=j;}}
    sorted(){return this.a.slice().sort((a,b)=>better(b,a));}
  }
  function reservoir(a,e,n,seen,rng){if(a.length<n)a.push(e);else{const j=Math.floor(rng()*seen);if(j<n)a[j]=e;}}
  const pause=()=>new Promise(r=>setTimeout(r,0));
  async function scan(S,rows,visit,stale){const check=()=>{if(stale())throw Object.assign(Error('취소'),{gwenCause:'cancel'});};check();let n=0;for(const keys of GS.iterateCombos(S,rows)){visit(keys);if(++n%4096===0){await pause();check();}}check();return n;}
  // 균등 reservoir + 구원자별 reservoir. 전원을 m회 포함하는 예약분을 먼저 두고 S까지 균등 표본으로 채움.
  async function sample(S,rows,seed,stale=()=>false){const c=config(S,rows.length),rng=random(seed),a=[],per=new Map(rows.map(r=>[r.key,{a:[],n:0}]));let n=0;
    await scan(S,rows,keys=>{reservoir(a,keys,c.S,++n,rng);for(const k of keys){const p=per.get(k);reservoir(p.a,keys,c.m,++p.n,rng);}},stale);
    const out=new Map();for(const p of per.values())for(const k of p.a)out.set(id(k),k);for(const k of a){if(out.size>=c.S)break;out.set(id(k),k);}return [...out.values()];}
  // Sparse one-hot unit, front/back and leader effects; role/element pair counts.
  function encoder(rows,results,roster){const cls=Object.fromEntries(rows.map(r=>[r.key,r.cls])),meta=new Map(roster.map(r=>[r.key,r])),ix=new Map();
    const index=s=>{if(!ix.has(s))ix.set(s,ix.size);return ix.get(s);};
    for(const r of rows)for(const s of ['unit','front','back','leader'])index(s+':'+r.key);
    const roles=[...new Set(rows.map(r=>r.cls))].sort(), elems=[...new Set(rows.map(r=>meta.get(r.key)?.el||meta.get(r.key)?.elem||meta.get(r.key)?.element||'?'))].sort();
    for(const [name,vs] of [['role',roles],['elem',elems]])for(let i=0;i<vs.length;i++)for(let j=i;j<vs.length;j++)index(name+':'+vs[i]+'/'+vs[j]);
    function encode(keys){const order=keys.slice().sort((x,y)=>(GS.FRONT.includes(cls[x])?0:1)-(GS.FRONT.includes(cls[y])?0:1)||results[y].power-results[x].power||(x<y?-1:1)),v=new Map();
      const add=(s,n=1)=>{const i=ix.get(s);v.set(i,(v.get(i)||0)+n);};
      order.forEach((k,i)=>{add('unit:'+k);add((i<2?'front:':'back:')+k);if(!i)add('leader:'+k);});
      for(let i=0;i<4;i++)for(let j=i+1;j<4;j++){
        add('role:'+ [cls[keys[i]],cls[keys[j]]].sort().join('/'));
        add('elem:'+ [meta.get(keys[i])?.el||meta.get(keys[i])?.elem||meta.get(keys[i])?.element||'?',meta.get(keys[j])?.el||meta.get(keys[j])?.elem||meta.get(keys[j])?.element||'?'].sort().join('/'));}
      return [...v];}
    return {encode,size:ix.size};}
  function ridge(X,y,p,c){const mean=y.reduce((s,v)=>s+v,0)/y.length,scale=Math.max(1,Math.sqrt(y.reduce((s,v)=>s+(v-mean)**2,0)/y.length)),r=Float64Array.from(y,v=>(v-mean)/scale),w=new Float64Array(p),cols=Array.from({length:p},()=>[]);
    X.forEach((x,i)=>x.forEach(([j,v])=>cols[j].push([i,v])));
    for(let e=0;e<c.epochs;e++)for(let j=0;j<p;j++){let den=c.ridge,num=0;for(const [i,v] of cols[j]){den+=v*v;num+=v*(r[i]+w[j]*v);}const next=num/den,d=next-w[j];for(const [i,v] of cols[j])r[i]-=v*d;w[j]=next;}
    return x=>mean+scale*x.reduce((s,[j,v])=>s+w[j]*v,0);}
  function ranks(a){const order=a.map((v,i)=>({v,i})).sort((a,b)=>a.v-b.v),r=[];for(let i=0;i<order.length;){let j=i+1;while(j<order.length&&order[j].v===order[i].v)j++;for(let k=i;k<j;k++)r[order[k].i]=(i+j-1)/2;i=j;}return r;}
  function correlation(a,b){if(a.length<3)return null;const x=ranks(a),y=ranks(b),m=(x.length-1)/2;let xy=0,xx=0,yy=0;for(let i=0;i<x.length;i++){xy+=(x[i]-m)*(y[i]-m);xx+=(x[i]-m)**2;yy+=(y[i]-m)**2;}return xx&&yy?xy/Math.sqrt(xx*yy):null;}
  async function train(enc,teams,values,c,stale=()=>false){const X=teams.map(enc.encode),pred=[];
    for(let f=0;f<c.folds;f++){const xx=[],yy=[];X.forEach((x,i)=>{if(i%c.folds!==f){xx.push(x);yy.push(values[i]);}});const fit=ridge(xx,yy,enc.size,c);X.forEach((x,i)=>{if(i%c.folds===f)pred[i]=fit(x);});await pause();if(stale())throw Error('취소');}
    const rho=correlation(values,pred),fit=ridge(X,values,enc.size,c);return {rho,predict:keys=>fit(enc.encode(keys))};}
  async function select(S,rows,model,stale=()=>false){const c=S.learned,top=new Heap(c.K),per=new Map(rows.map(r=>[r.key,new Heap(c.M)]));
    await scan(S,rows,keys=>{const e={keys,id:id(keys),score:model.predict(keys)};top.put(e);for(const k of keys)per.get(k).put(e);},stale);
    const core=new Map(),guaranteed=new Set();for(const e of top.sorted())core.set(e.id,e);for(const h of per.values())for(const e of h.sorted()){core.set(e.id,e);guaranteed.add(e.id);}return {core,guaranteed,overlap:new Set(),top:top.sorted()};}
  async function overlap(S,rows,models,selections,bestTriples,stale=()=>false){const c=S.learned;
    if(!c.overlapStarts||!c.overlapKeep)return;
    const lists=selections.map(s=>[...s.core.values()].sort((a,b)=>better(b,a)));
    const triples=bestTriples(lists,c.overlapStarts,{remaining:S.retry?.maxTripleChecks||2000000});
    for(let b=0;b<3;b++){
      const others=[0,1,2].filter(i=>i!==b),pairs=triples.map(t=>others.flatMap(i=>t.teams[i].keys));
      // 삼중이 없더라도 두 팀을 피하는 대체 팀을 찾는다. 단순히 하나 찾고 끝내지 않음.
      if(!pairs.length){outer:for(const a of lists[others[0]])for(const d of lists[others[1]])if(!a.keys.some(k=>d.keys.includes(k))){pairs.push([...a.keys,...d.keys]);if(pairs.length>=c.overlapStarts)break outer;}}
      if(!pairs.length){
        const starts=lists[others[0]].slice(0,c.overlapStarts),hs=starts.map(()=>new Heap(1));
        await scan(S,rows,keys=>{let e;starts.forEach((a,i)=>{if(keys.some(k=>a.keys.includes(k)))return;e||={keys,id:id(keys),score:models[others[1]].predict(keys)};hs[i].put(e);});},stale);
        hs.forEach((h,i)=>{for(const e of h.sorted()){pairs.push([...starts[i].keys,...e.keys]);selections[others[1]].core.set(e.id,e);selections[others[1]].overlap.add(e.id);}});
      }
      const constraints=[...new Map(pairs.map(p=>[id(p),new Set(p)])).values()],heaps=constraints.map(()=>new Heap(c.overlapKeep));
      await scan(S,rows,keys=>{let e;constraints.forEach((ban,i)=>{if(keys.some(k=>ban.has(k)))return;e||={keys,id:id(keys),score:models[b].predict(keys)};heaps[i].put(e);});},stale);
      for(const h of heaps)for(const e of h.sorted()){selections[b].core.set(e.id,e);selections[b].overlap.add(e.id);}
    }}
  async function auditSample(S,rows,selection,seed,stale=()=>false){const a=[],rng=random(seed);let n=0;await scan(S,rows,keys=>{if(!selection.core.has(id(keys)))reservoir(a,keys,S.learned.A,++n,rng);},stale);return {teams:a,excluded:n};}
  function audit(c,rho,core,audit,expected,excluded,pass){const scores=core.filter(Number.isFinite).sort((a,b)=>b-a),samples=audit.filter(Number.isFinite),edge=scores[Math.min(pass,scores.length)-1],misses=samples.filter(v=>v>=edge).length,rate=samples.length?misses/samples.length:excluded?1:0;
    return {rho,edge,misses,sampled:samples.length,rate,fallback:rho===null||rho<c.minCorrelation||core.length!==scores.length||samples.length!==expected||rate>c.missThreshold};}
  // MC 통과 후에도 구원자별 상위 M과 겹침 회피 후보를 보존한다.
  function preserve(ranked,initial,M,overlapIds=new Set()){const keep=new Set(initial.map(e=>id(e.keys))),counts=new Map();for(const e of ranked){for(const k of e.keys){const n=counts.get(k)||0;if(n<M){keep.add(id(e.keys));counts.set(k,n+1);}}if(overlapIds.has(id(e.keys)))keep.add(id(e.keys));}return ranked.filter(e=>keep.has(id(e.keys)));}
  const api={Heap,config,random,sample,encoder,train,correlation,select,overlap,auditSample,audit,preserve,scan,id};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.CosmoLearned=api;
})(typeof window!=='undefined'?window:globalThis);
