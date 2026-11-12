// Browser policy only: simulation/search libraries remain usable in offline tests.
(function(root){
  function time(value){
    if(typeof value!=='string'||!value)return NaN;
    return Date.parse(/^\d{4}-\d{2}-\d{2}$/.test(value)?value+'T00:00:00+09:00':value);
  }
  function state(season,now=Date.now(),query=''){
    const start=time(season?.start),end=time(season?.end),q=new URLSearchParams(query);
    const bypass=q.get('dev')==='1'||q.get('season')==='force';
    const known=Number.isFinite(start)&&Number.isFinite(end)&&start<end;
    const phase=!known?'unknown':now<start?'upcoming':now>=end?'ended':'active';
    const closed=phase==='upcoming'||phase==='ended';
    return {phase,blocked:closed&&!bypass,bypass,label:closed?'미오픈':!known?'기간 미확인':'',
      message:phase==='ended'?'시즌 종료 — 새 시즌 자료 반영 전':phase==='upcoming'?'시즌 시작 전':!known?'기간 미확인 — 탐색 가능':''};
  }
  const api={time,state};if(typeof module!=='undefined')module.exports=api;else root.SeasonGate=api;
})(typeof window!=='undefined'?window:globalThis);
