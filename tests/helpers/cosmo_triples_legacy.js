// Frozen 3697359 algorithm for exact regression and local measurements.
// Only instrumentation added: zero-based budget exhaustion position.
const BOSSES=3, idOf=keys=>keys.slice().sort().join("+");
  function bestTriples(lists, n, budget) {
    if (lists.length !== BOSSES || lists.some(l => !l.length)) return [];
    const index = new Map();
    lists.forEach(l => l.forEach(e => e.keys.forEach(k => { if (!index.has(k)) index.set(k, index.size); })));
    const W = Math.max(1, Math.ceil(index.size / 30));
    const mk = e => { const m = new Array(W).fill(0); e.keys.forEach(k => { const i = index.get(k); m[(i / 30) | 0] |= 1 << (i % 30); }); return m; };
    const L = lists.map(l => l.map(e => ({e, m: mk(e), id: idOf(e.keys)})));
    const top = [], idOfT = t => t.map(x => x.id).join("/");
    const better = (a, b) => { const ia = idOfT(a.t), ib = idOfT(b.t); return a.sum - b.sum || (ia < ib ? 1 : ia > ib ? -1 : 0); };   // >0 이면 a 가 더 좋음(합이 크거나, 같으면 id 가 작음)
    const floor = () => top.length < n ? -Infinity : top[top.length - 1].sum;
    const hit = (x, y) => { for (let w = 0; w < W; w++) if (x[w] & y[w]) return true; return false; };
    const or = (x, y) => x.map((v, w) => v | y[w]);
    function put(sum, t) {
      const c = {sum, t};
      let i = top.length;
      while (i > 0 && better(c, top[i - 1]) > 0) i--;
      top.splice(i, 0, c);
      if (top.length > n) top.pop();
    }
    const c0 = L[2][0].e.score, b0 = L[1][0].e.score;
    const visit = () => !budget || (budget.remaining-- > 0 || (budget.exhausted = true, false));
    search: for (const a of L[0]) {
      if (a.e.score + b0 + c0 < floor()) break;
      for (const b of L[1]) {
        if (!visit()) { budget.position = {a:L[0].indexOf(a), b:L[1].indexOf(b), c:null}; break search; }
        if (a.e.score + b.e.score + c0 < floor()) break;
        if (hit(a.m, b.m)) continue;
        const ab = or(a.m, b.m), base = a.e.score + b.e.score;
        for (const c of L[2]) {
          if (!visit()) { budget.position = {a:L[0].indexOf(a), b:L[1].indexOf(b), c:L[2].indexOf(c)}; break search; }
          if (base + c.e.score < floor()) break;
          if (hit(ab, c.m)) continue;
          put(base + c.e.score, [a, b, c].map(x => ({id: x.id, e: x.e})));
        }
      }
    }
    return top.map(x => ({sum: x.sum, teams: x.t.map(y => y.e)}));
  }

module.exports=bestTriples;
