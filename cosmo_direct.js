// Pure Cosmo drafts. No DOM, storage writes, account retention or result cache.
(function(root){
  'use strict';
  const node=typeof module!=='undefined'&&module.exports;
  const P=node?require('./direct_party'):root.DirectParty;
  const VERSION=1, STORAGE_KEY='direct.cosmo.v1', SHARE_PARAM='cd';
  const key=v=>typeof v==='string'&&/^[a-z][a-z0-9_-]{0,63}$/.test(v)&&!['constructor','prototype','__proto__'].includes(v);
  const own=(o,k)=>Object.prototype.hasOwnProperty.call(o||{},k);
  const copy=v=>JSON.parse(JSON.stringify(v));
  // Keep the contract's enumerable state shape. JSON/cloned drafts must go through
  // restore(raw, season); metadata is per state, never a global "current season".
  const seasons=new WeakMap();
  function spec(season){
    return {id:season?.id,levelMax:Number.isInteger(season?.levelMax)&&season.levelMax>=0?season.levelMax:6,
      bosses:(Array.isArray(season?.bosses)?season.bosses:[]).filter((b,i,all)=>key(b?.key)&&all.findIndex(x=>x?.key===b.key)===i)
        .map(b=>({key:b.key,sim:b.sim!==false}))};
  }
  function bind(state,season){seasons.set(state,season);return state;}
  function create(season){
    const s=spec(season);
    return bind({v:VERSION,seasonId:s.id,active:s.bosses[0]?.key||null,
      teams:Object.fromEntries(s.bosses.map(b=>[b.key,{level:Math.min(6,s.levelMax),draft:P.draft(null)}]))},s);
  }
  function restore(raw,season){
    const out=create(season),s=seasons.get(out);
    if(typeof raw==='string')try{raw=JSON.parse(raw);}catch(_){return out;}
    if(!raw||raw.v!==VERSION||raw.seasonId!==s.id)return out;
    if(own(out.teams,raw.active))out.active=raw.active;
    const seen=new Set();
    for(const b of s.bosses){
      const input=own(raw.teams,b.key)?raw.teams[b.key]:null;if(!input)continue;
      const team=out.teams[b.key];
      if(Number.isInteger(input.level)&&input.level>=0&&input.level<=s.levelMax)team.level=input.level;
      team.draft=P.draft(input.draft);
      // Season order wins, then slot order. Drop only invalid/duplicate members.
      team.draft.slots=team.draft.slots.map(m=>{if(!m||seen.has(m.key))return null;seen.add(m.key);return m;});
      if(!team.draft.slots.some(m=>m?.key===team.draft.leader))team.draft.leader=team.draft.slots.find(Boolean)?.key||null;
    }
    return out;
  }
  function usedBy(state){
    const used=new Map();
    for(const [boss,t] of Object.entries(state.teams))for(const m of t.draft.slots)
      if(m&&!used.has(m.key))used.set(m.key,boss);
    return used;
  }
  function edit(state,action){
    const s=seasons.get(state);
    if(!s)throw Error('restore(raw, season) 필요');
    const out=bind({...state,teams:Object.fromEntries(Object.entries(state.teams).map(([b,t])=>[b,{level:t.level,draft:P.draft(t.draft)}]))},s);
    if(!action)return out;
    const has=own(out.teams,action.boss);
    if(action.type==='team'&&has)out.active=action.boss;
    if(['level','levelAll'].includes(action.type)&&Number.isInteger(action.level)){
      const level=Math.max(0,Math.min(s.levelMax,action.level));
      for(const [b,t] of Object.entries(out.teams))if(action.type==='levelAll'||b===action.boss)t.level=level;
    }
    if(action.type==='draft'&&has&&action.action){
      const a=action.action;
      if(a.type==='put'&&Object.entries(out.teams).some(([b,t])=>b!==action.boss&&t.draft.slots.some(m=>m?.key===a.key)))return out;
      out.teams[action.boss].draft=P.edit(out.teams[action.boss].draft,a);
    }
    return out;
  }
  function validate(state,ctx={}){
    const teams={},errors=[],s=seasons.get(state),owners=new Map();
    const roster=ctx.roster||[],byKey=new Map(roster.map(r=>[r.key,r]));
    for(const [boss,t] of Object.entries(state.teams)){
      const v=P.validate(t.draft,{roster,info:ctx.info||null,content:'op'});
      teams[boss]=v;
      const b=s?.bosses.find(b=>b.key===boss);
      if(!b||state.seasonId!==s.id)v.errors.push({code:'season',message:'시즌 자료로 복원 필요'});
      else if(!b.sim)v.errors.push({code:'unsupported_boss',message:'아직 계산할 수 없는 보스'});
      if(!Number.isInteger(t.level)||t.level<0||(s&&t.level>s.levelMax))v.errors.push({code:'level',message:'난이도 확인 필요'});
      for(const [slot,m] of t.draft.slots.entries())if(m){
        const id=byKey.get(m.key)?.uid??m.key;
        if(!owners.has(id))owners.set(id,[]);owners.get(id).push({boss,slot,key:m.key});
      }
    }
    for(const entries of owners.values())if(new Set(entries.map(e=>e.boss)).size>1)
      for(const e of entries)teams[e.boss].errors.push({code:'cross_dup',slot:e.slot,key:e.key,
        other:entries.find(x=>x.boss!==e.boss).boss,message:'다른 팀에서 사용 중인 구원자'});
    for(const [boss,v] of Object.entries(teams)){v.ok=!v.errors.length;errors.push(...v.errors.map(e=>({...e,boss})));}
    return {ok:Object.keys(teams).length>0&&!errors.length,teams,errors};
  }
  // ctx: validate context + DirectParty.powers inputs (growth/slots/priority),
  // options (common sim options), optional engineKey and resolveBreak(draft,boss).
  // Resolve auto with the host's pickBreak/ownedSimBreaks adapter; absent adapter
  // means no automatic break. breaks, when supplied, validates ownership/level.
  // Actual direct_run wire format: leader is party.leader, growth is final stats
  // in party.units, NOT inert options.leader/options.growth fields.
  // Invalid teams are omitted so a supported, complete team can run on its own.
  function jobs(state,ctx={}){
    const check=validate(state,ctx),out=[];
    for(const [boss,t] of Object.entries(state.teams)){
      if(ctx.boss&&ctx.boss!==boss)continue;
      if(!check.teams[boss].ok)continue;
      const d=P.draft(t.draft);
      const brk=d.brk==='auto'?(ctx.resolveBreak?ctx.resolveBreak(P.draft(d),boss):null):d.brk;
      if(brk&&(!Number.isInteger(brk.level)||brk.level<1||brk.level>10||typeof brk.name!=='string'))throw Error('브레이크 스킬 확인 필요');
      if(brk&&ctx.breaks&&!ctx.breaks.some(b=>b.name===brk.name&&b.level===brk.level))throw Error('브레이크 보유 레벨 확인 필요');
      const values=P.powers(d,{...ctx,roster:ctx.roster||[],content:'cosmo'});
      if(values.errors.length||(ctx.info&&d.slots.some(m=>!values.profile?.results[m.key])))throw Error('내 정보 계산 자료 확인 필요');
      const party=P.serialize(d,values.profile?.results||{},ctx.engineKey);
      out.push({boss,party,options:{...copy(ctx.options||{}),cosmo_raid:{boss,step:3,level:t.level},
        break_skill:brk?{name:brk.name,level:brk.level}:null}});
    }
    return out;
  }
  // Caller supplies results for the CURRENT jobs only (signatures/cancellation
  // belong to the runner). need is the total team count, not remaining count.
  function summary(state,results={},mode='mean'){
    const teams={};let total=0,done=0;
    for(const [boss,t] of Object.entries(state.teams)){
      const st=results?.[boss]?.cosmo,score=st?.[mode==='top'?'top':'mean'];
      const members=t.draft.slots.filter(Boolean),full=members.length===4&&new Set(members.map(m=>m.key)).size===4&&members.some(m=>m.key===t.draft.leader);
      const complete=full&&Number.isFinite(score);
      teams[boss]={status:complete?'done':members.length?'ready':'empty',score:complete?score:null,
        clear:complete&&Number.isFinite(st.clear??results[boss].clear)?(st.clear??results[boss].clear):null};
      if(complete){total+=score;done++;}
    }
    const need=Object.keys(teams).length;
    return {teams,total:need>0&&done===need?total:null,done,need};
  }
  function fromSearch(row,season){
    const raw=create(season),seen=new Set();
    for(const t of Array.isArray(row?.teams)?row.teams:[]){
      if(!t||!own(raw.teams,t.boss)||seen.has(t.boss))continue;seen.add(t.boss);
      // CosmoSearch.finalRankBrk: order is ENGINE order; leader = order[0].
      // keys is the unordered combination, used only when no order was supplied.
      const order=Array.isArray(t.order)?t.order:t.keys;
      if(!Array.isArray(order)||order.length!==4||!order.every(key)||new Set(order).size!==4)continue;
      raw.teams[t.boss]={level:t.level??raw.teams[t.boss].level,draft:{v:VERSION,
        slots:order.map(key=>({key,grown:false})),leader:order[0],brk:t.brk?{name:t.brk,level:t.brkLv}:null}};
    }
    return restore(raw,season);
  }
  function storage(state){
    // Explicit allowlist at every layer; never spread a draft into a public link.
    return {v:VERSION,seasonId:typeof state.seasonId==='string'||Number.isFinite(state.seasonId)?state.seasonId:null,
      active:key(state.active)?state.active:null,teams:Object.fromEntries(Object.entries(state.teams)
        .filter(([b])=>key(b)).map(([b,t])=>[b,{level:Number.isInteger(t.level)?t.level:6,draft:P.draft(t.draft)}]))};
  }
  const share=state=>storage(state);
  const api={VERSION,STORAGE_KEY,SHARE_PARAM,create,restore,edit,usedBy,validate,jobs,summary,fromSearch,storage,share};
  if(node)module.exports=api;else root.CosmoDirect=api;
})(typeof window!=='undefined'?window:globalThis);
