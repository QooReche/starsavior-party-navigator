// Public view state only. Never serialize account data or owned saviors.
(function(root){
  "use strict";
  const growths=["1","0.8","1.25","manual","myinfo"];
  function parse(search,contents,breakKeys){
    const q=new URLSearchParams(search),out={};
    if(q.has("c")||q.has("s")){
      const c=contents.find(c=>c.key===q.get("c"))||contents[0];
      out.c=c.key;
      const s=c.stages.find(s=>s.tab+"|"+s.name===q.get("s"))||c.stages[0];
      if(s)out.s=s.tab+"|"+s.name;
    }
    if(q.has("g")||q.has("grow")){
      const g=q.get("g")??q.get("grow");out.g=growths.includes(g)?g:"1";
      if(out.g==="manual"){
        const p=q.get("p");out.p=/^[1-9]\d{0,11}$/.test(p||"")?Number(p):0;
      }
    }
    if(q.has("m")||q.has("mode"))out.m=(q.get("m")??q.get("mode"))==="manual"?"manual":"auto";
    if(q.has("rk"))out.rk=/^[0-5]$/.test(q.get("rk"))?Number(q.get("rk")):0;
    for(const key of ["b","b2"])if(q.has(key))out[key]=q.get(key)===""||breakKeys.includes(q.get(key))?q.get(key):null;
    return out;
  }
  function stringify(state){
    const q=new URLSearchParams();
    for(const key of ["c","s","g","m","rk"])if(state[key]!=null)q.set(key,String(state[key]));
    if(state.g==="manual"&&Number.isSafeInteger(state.p)&&state.p>0&&state.p<1e12)q.set("p",String(state.p));
    for(const key of ["b","b2"])if(typeof state[key]==="string")q.set(key,state[key]);
    return q.toString();
  }
  function url(base,state){const u=new URL(base);u.search=stringify(state);u.hash="";return u.href}
  const api={parse,stringify,url};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.ShareState=api;
})(typeof window!=="undefined"?window:globalThis);
