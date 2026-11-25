// Public view state only. Never serialize account data or owned saviors.
(function(root){
  "use strict";
  const Direct=typeof module!=="undefined"&&module.exports?require('./direct_party'):root.DirectParty;
  const Cosmo=typeof module!=="undefined"&&module.exports?require('./cosmo_direct'):root.CosmoDirect;
  const growths=["1","0.8","1.25","manual","myinfo"];
  function parse(search,contents,breakKeys){
    const q=new URLSearchParams(search),out={};
    if(['home','reco','direct'].includes(q.get('pm')))out.pm=q.get('pm');
    if(q.has('dp')&&q.get('dp').length<4096){try{const d=JSON.parse(q.get('dp'));if(d?.v===Direct.VERSION){out.dp=Direct.share(d);out.pm||='direct';}}catch(e){}}
    if(q.has('cd')&&q.get('cd').length<16384){try{const d=JSON.parse(q.get('cd'));if(d?.v===Cosmo.VERSION&&d.teams&&typeof d.teams==='object'){out.cd=Cosmo.share(d);out.pm||='direct';}}catch(e){}}
    if(q.has("c")||q.has("s")){
      const c=contents.find(c=>c.key===q.get("c"))||contents[0];
      out.c=c.key;
      if(c.key==='guild'){
        out.gs=q.has('gs')?(/^\d+$/.test(q.get('gs'))?Number(q.get('gs')):0):30111;
        out.guildExpired=out.gs!==(c.seasonId??30111);
      }
      const s=c.stages.find(s=>s.tab+"|"+s.name===q.get("s"))||c.stages[0];
      if(out.guildExpired)out.s=q.get('s')||'';else if(s)out.s=s.tab+"|"+s.name;
    }
    if(q.has("g")||q.has("grow")){
      const g=q.get("g")??q.get("grow");out.g=growths.includes(g)?g:"1";
      if(out.g==="manual"){
        const p=q.get("p");out.p=/^[1-9]\d{0,11}$/.test(p||"")?Number(p):0;
      }
    }
    // 옛 링크의 m·mode(오토/수동)는 읽지 않는다 — 오토 기준만(11/14 수동 모드 제거)
    if(q.has("rk"))out.rk=/^[0-5]$/.test(q.get("rk"))?Number(q.get("rk")):0;
    for(const key of ['ag','ao'])if(q.has(key))out[key]=q.get(key)==='1';
    for(const key of ["b","b2"])if(q.has(key))out[key]=q.get(key)===""||breakKeys.includes(q.get(key))?q.get(key):null;
    return out;
  }
  function stringify(state){
    const q=new URLSearchParams();
    if(['home','reco','direct'].includes(state.pm))q.set('pm',state.pm);
    if(state.cd)q.set('cd',JSON.stringify(Cosmo.share(state.cd)));
    if(state.dp)q.set('dp',JSON.stringify(Direct.share(state.dp)));
    for(const key of ["c","s","g","rk"])if(state[key]!=null)q.set(key,String(state[key]));
    if(state.c==='guild')q.set('gs',String(state.gs??30111));
    for(const key of ['ag','ao'])if(typeof state[key]==='boolean')q.set(key,state[key]?'1':'0');
    if(state.g==="manual"&&Number.isSafeInteger(state.p)&&state.p>0&&state.p<1e12)q.set("p",String(state.p));
    for(const key of ["b","b2"])if(typeof state[key]==="string")q.set(key,state[key]);
    return q.toString();
  }
  function url(base,state){const u=new URL(base);u.search=stringify(state);u.hash="";return u.href}
  const api={parse,stringify,url};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.ShareState=api;
})(typeof window!=="undefined"?window:globalThis);
