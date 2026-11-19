// 그웬 그림·배너 선택 규칙. DOM 의존 없음.
// GwenLane(레인 컨트롤러)과 Ux(화면 도우미) 양쪽이 참조함.
(function(root){
  'use strict';

  // --- 결과 등신대/SD 후보 ---

  // 레인·초상(portrait) 문맥: st_* 우선. 좁은 화면에서도 st_*를 쓰고 CSS 가 크기를 줄임.
  function resultCandidates(clear,better,recoHigher){
    if(recoHigher)return ['st_point','thoughtful'];
    if(better)return ['st_wink','st_reach'];
    if(!Number.isFinite(clear))return ['st_point','thoughtful'];
    if(clear>=.7)return ['st_verdict','st_cheer','st_ok','st_reach'];
    if(clear>=.05)return ['st_point','thoughtful'];
    return ['st_cry','notes'];
  }

  // 작은 인라인 문맥(코스모·길드 탐색 한 줄 등): SD 유지.
  function resultCandidatesSD(clear,better,recoHigher){
    if(recoHigher)return ['report','think'];
    if(better)return ['verdict','cheer','report'];
    if(!Number.isFinite(clear))return ['report','verdict'];
    if(clear>=.7)return ['verdict','cheer','report'];
    if(clear>=.05)return ['report','verdict'];
    return ['cry'];
  }

  // Ux.gwenReport/gwenReaction 용: 결과 그림 한 장 선택. portrait=true 면 st_*.
  function resultArt(clear,{kind,seed=.5,portrait=true}={}){
    if(kind==='score'||!Number.isFinite(clear))return portrait?'st_point':'report';
    if(!portrait)return clear<.05?'cry':clear>=.7?(seed<.5?'verdict':'cheer'):'report';
    if(clear<.05)return 'st_cry';
    if(clear>=.7){const pool=['st_verdict','st_cheer','st_ok','st_reach'];return pool[Math.floor(seed*pool.length)];}
    return seed<.5?'st_point':'thoughtful';
  }

  // --- 배너 ---

  function bannerState(state,onBoard){
    if(!['direct','cdirect','reco'].includes(state.mode)||onBoard)return '';
    if(state.bundleRunning||state.phase==='work')return '';
    if(state.phase==='result'&&!state.stale)return 'result';
    return state.phase==='error'?'error':'';
  }

  const BANNER_COPY={investigation:'조사 완료!',inquiry:'수사 완료!',calculation:'계산 완료!',error:'수사 난항…'};

  function bannerPicker(random=Math.random){
    let previous='';const reports=new Map();
    return (state,id)=>{
      if(state==='result'){
        if(!reports.has(id)){
          const pool=['investigation','inquiry','calculation'].filter(x=>x!==previous);
          previous=pool[Math.floor(random()*pool.length)];reports.set(id,previous);
          if(reports.size>128)reports.delete(reports.keys().next().value);
        }
        return reports.get(id);
      }
      return state==='error'?'error':'';
    };
  }

  // 배너 마크업(수동·자동 무대 공용). 호출처가 감싸는 div 에 넣음.
  function bannerMarkup(){
    return ['investigation','inquiry','calculation','error'].map(key=>
      `<span class="gwen-banner-title" data-phrase="${key}" hidden><span class="gwen-banner-fallback">${BANNER_COPY[key]}</span><img src="assets/ui_icons/case_banner_${key}.webp" width="640" height="160" alt="" decoding="async"></span>`
    ).join('');
  }

  const api={resultCandidates,resultCandidatesSD,resultArt,bannerState,BANNER_COPY,bannerPicker,bannerMarkup};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GwenPolicy=api;
})(typeof window!=='undefined'?window:globalThis);
