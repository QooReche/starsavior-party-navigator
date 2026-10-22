// 공개 화면 공용 표·문자열 처리. 능력치 합산 순서는 계산 모듈에서 유지함.
(function(root){
  'use strict';
  const keys=['atk','hp','def','spd','cr','cd','eh','er','atkP','hpP','defP'];
  const NST=Object.fromEntries(['NST_ATK','NST_HP','NST_DEF','NST_TURN_SPEED','NST_RATE_CRITICAL','NST_RATE_CRITICAL_DAMAGE','NST_RATE_EFFECT_HIT','NST_RATE_EFFECT_EVADE','NST_NV_RATE_ATK','NST_NV_RATE_HP','NST_NV_RATE_DEF'].map((k,i)=>[k,keys[i]]));
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  // 선 아이콘(Lucide, ISC 라이선스 https://lucide.dev — 모양만 옮김). currentColor 로 그린다
  const SH='<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/>',SW='<polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/><line x1="13" x2="19" y1="19" y2="13"/><line x1="16" x2="20" y1="16" y2="20"/><line x1="19" x2="21" y1="21" y2="19"/>';
  const ICON={atk:SW,hp:'<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',def:SH,
    spd:'<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',cr:'<circle cx="12" cy="12" r="9"/><line x1="22" x2="17" y1="12" y2="12"/><line x1="7" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="7" y2="2"/><line x1="12" x2="12" y1="22" y2="17"/>',
    cd:'<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    eh:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',er:SH+'<path d="m9 12 2 2 4-4"/>',
    power:SW+'<polyline points="14.5 6.5 18 3 21 3 21 6 17.5 9.5"/><line x1="5" x2="9" y1="14" y2="18"/><line x1="7" x2="4" y1="17" y2="20"/><line x1="3" x2="5" y1="19" y2="21"/>',
    endure:'<path d="M5 22h14M5 2h14M17 22v-4.17a2 2 0 0 0-.59-1.42L12 12l-4.41 4.41A2 2 0 0 0 7 17.83V22M7 2v4.17a2 2 0 0 0 .59 1.42L12 12l4.41-4.41A2 2 0 0 0 17 6.17V2"/>',
    focus:'<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    basic:SW,special:'<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    ultimate:'<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',passive:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>',
    gear:'<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/>',
    gem:'<path d="M6 3h12l4 6-10 13L2 9Z"/><path d="M11 3 8 9l4 13 4-13-3-6M2 9h20"/>',tough:SH+'<path d="M12 2v20"/>',
    reso:'<path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5M19.1 4.9C23 8.8 23 15.1 19.1 19"/><circle cx="12" cy="12" r="2"/>',
    sigil:'<path d="M5 22h14M19.27 13.73A2.5 2.5 0 0 0 17.5 13h-11A2.5 2.5 0 0 0 4 15.5V17a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-1.5c0-.66-.26-1.3-.73-1.77ZM14 13V8.5C14 7 15 7 15 5a3 3 0 0 0-6 0c0 2 1 2 1 3.5V13"/>',
    tactics:'<path d="M3 3v18h18"/><path d="M18 17V9M13 17V5M8 17v-3"/>',journey:'<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>'};
  const icon=(k,cls='ic')=>ICON[k]?`<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k]}</svg>`:'';
  const api={NST,esc,ICON,icon};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.UiShared=api;
})(typeof globalThis!=='undefined'?globalThis:this);
