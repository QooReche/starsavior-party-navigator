// 공개 화면 공용 표·문자열 처리. 능력치 합산 순서는 계산 모듈에서 유지함.
(function(root){
  'use strict';
  const keys=['atk','hp','def','spd','cr','cd','eh','er','atkP','hpP','defP'];
  const NST=Object.fromEntries(['NST_ATK','NST_HP','NST_DEF','NST_TURN_SPEED','NST_RATE_CRITICAL','NST_RATE_CRITICAL_DAMAGE','NST_RATE_EFFECT_HIT','NST_RATE_EFFECT_EVADE','NST_NV_RATE_ATK','NST_NV_RATE_HP','NST_NV_RATE_DEF'].map((k,i)=>[k,keys[i]]));
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const api={NST,esc};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.UiShared=api;
})(typeof globalThis!=='undefined'?globalThis:this);
