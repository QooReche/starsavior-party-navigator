// Headless stage search. Inputs/jobs are snapshots; UI, stores and leases are adapters.
(function(root){
  'use strict';
  const alive=env=>{if(!env.live())throw Error('취소');};
  async function recommendation(env){
    for(let p=1;p<=env.parties;p++){
      alive(env);let box=env.plan(p);
      if(!box?.all?.length)throw Error(`파티 ${p}: 후보가 4명 미만임`);
      if(env.screened&&!env.screenState(p)?.done){await env.screen(p,box);alive(env);box=env.plan(p);}
      while(true){
        alive(env);await env.final(p,box);alive(env);box=env.plan(p);
        if(!box.rows.every(t=>env.goal(env.result(t))<.5)||box.rows.length>=9||box.rows.length>=box.total)break;
        env.more(p,box.rows.length+3);box=env.plan(p);
      }
    }
    return env.first();
  }
  const api={recommendation};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.RecommendPipeline=api;
})(typeof window!=='undefined'?window:globalThis);
