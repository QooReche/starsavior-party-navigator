// Non-overlapping N-team combinations; sorted candidate lists and additive scores.
(function(root){
  'use strict';
  function* steps(lists, n, budget, {id=e=>e.keys.slice().sort().join('+'),resources=e=>({units:e.keys})}={}) {
    if (!lists.length || n<=0 || lists.some(l => !l.length)) return [];
    const index=new Map();
    const tokens=lists.map(l=>l.map(e=>({e,id:id(e),tokens:Object.entries(resources(e)).flatMap(([kind,values])=>values.map(value=>JSON.stringify([kind,value])))})));
    for(const list of tokens)for(const row of list)for(const k of row.tokens)if(!index.has(k))index.set(k,index.size);
    const W=Math.max(1,Math.ceil(index.size/30));
    const L=tokens.map(l=>l.map(({e,id,tokens})=>{const m=new Array(W).fill(0);for(const k of tokens){const i=index.get(k);m[(i/30)|0]|=1<<(i%30);}return {e,id,m};}));
    const top = [], idOfT = t => t.map(x => x.id).join("/");
    const better = (a, b) => { const ia = idOfT(a.t), ib = idOfT(b.t); return a.sum - b.sum || (ia < ib ? 1 : ia > ib ? -1 : 0); };   // >0 이면 a 가 더 좋음(합이 크거나, 같으면 id 가 작음)
    const floor = () => top.length < n ? -Infinity : top[top.length - 1].sum;
    const hit = (x, y) => { for (let w = 0; w < W; w++) if (x[w] & y[w]) return true; return false; };
    function put(sum, t) {
      const c = {sum, t};
      let i = top.length;
      while (i > 0 && better(c, top[i - 1]) > 0) i--;
      top.splice(i, 0, c);
      if (top.length > n) top.pop();
    }
    const visit = () => !budget || (budget.remaining-- > 0 || (budget.exhausted = true, false));
    let checks = 0;
    if(L.length!==3){
      // The three-list traversal below retains its historic visit/budget contract.
      // Other team counts use the same masks and ranking with a depth-first bound.
      const suffix=new Array(L.length+1).fill(0);
      for(let d=L.length-1;d>=0;d--)suffix[d]=L[d][0].e.score+suffix[d+1];
      function* walk(depth,sum,mask,chosen,indices){
        for(let i=0;i<L[depth].length;i++){
          if(depth===0||++checks%4096===0)yield;
          const row=L[depth][i];
          if(sum+row.e.score+suffix[depth+1]<floor())break;
          if(!visit()){
            budget.upperBound=suffix[0]; // Conservative whole-search certificate.
            budget.position={depth,indices:[...indices,i]};return;
          }
          if(hit(mask,row.m))continue;
          const next=[...chosen,{id:row.id,e:row.e}];
          if(depth===L.length-1)put(sum+row.e.score,next);
          else yield* walk(depth+1,sum+row.e.score,mask.map((v,w)=>v|row.m[w]),next,[...indices,i]);
          if(budget?.exhausted)return;
        }
      }
      yield* walk(0,0,new Array(W).fill(0),[],[]);
      return top.map(x=>({sum:x.sum,teams:x.t.map(y=>y.e)}));
    }
    const c0 = L[2][0].e.score, b0 = L[1][0].e.score;
    search: for (let ai = 0; ai < L[0].length; ai++) {
      yield; // 호환 목록 구성도 a마다 화면에 제어를 돌려줄 수 있게 함.
      const a = L[0][ai];
      if (a.e.score + b0 + c0 < floor()) break;
      const Ba = L[1].filter(b => !hit(a.m, b.m)), Ca = L[2].filter(c => !hit(a.m, c.m));
      // 이 경계는 a에 종속됨. 다음 a의 호환 최고점은 더 높을 수 있으므로 break 금지.
      if (!Ba.length || !Ca.length || a.e.score + Ba[0].e.score + Ca[0].e.score < floor()) continue;
      const ca0 = Ca[0].e.score;
      const stop = (bi, ci) => {
        // 현재 c 꼬리 / 다음 b / 다음 a. 다음 a는 아직 거르지 않았으므로 전역 최고점 사용.
        const tail = a.e.score + Ba[bi].e.score + Ca[ci == null ? 0 : ci].e.score;
        const nextB = bi + 1 < Ba.length ? a.e.score + Ba[bi + 1].e.score + ca0 : -Infinity;
        const nextA = ai + 1 < L[0].length ? L[0][ai + 1].e.score + b0 + c0 : -Infinity;
        budget.upperBound = Math.max(tail, nextB, nextA);
        budget.position = {a: ai, b: bi, c: ci}; // b·c는 호환 목록 안의 0부터 세는 위치.
      };
      for (let bi = 0; bi < Ba.length; bi++) {
        if (++checks % 4096 === 0) yield;
        const b = Ba[bi];
        if (!visit()) { stop(bi, null); break search; }
        if (a.e.score + b.e.score + ca0 < floor()) break;
        const base = a.e.score + b.e.score;
        for (let ci = 0; ci < Ca.length; ci++) {
          if (++checks % 4096 === 0) yield;
          const c = Ca[ci];
          if (!visit()) { stop(bi, ci); break search; }
          if (base + c.e.score < floor()) break;
          if (hit(b.m, c.m)) continue; // a와의 겹침은 Ca에서 이미 제거했음.
          put(base + c.e.score, [a, b, c].map(x => ({id: x.id, e: x.e})));
        }
      }
    }
    return top.map(x => ({sum: x.sum, teams: x.t.map(y => y.e)}));
  }
  function bestSets(lists,n,budget,options){
    const it=steps(lists,n,budget,options);let next;do{next=it.next();}while(!next.done);return next.value;
  }
  const api={steps,bestSets};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ScoreCombinations=api;
})(typeof window!=='undefined'?window:globalThis);
