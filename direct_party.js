// Pure DIRECT contracts. Slots are always engine order: front 1/2, rear 1/2.
(function(root){
  'use strict';
  const node=typeof module!=='undefined'&&module.exports;
  const M=node?require('./myinfo_reco'):root.MyInfoReco;
  const S=node?require('./star_link'):root.StarLink;
  const VERSION=1;
  const key=v=>typeof v==='string'&&/^[a-z][a-z0-9_-]{0,63}$/.test(v)?v:null;
  const empty=()=>({v:VERSION,slots:[null,null,null,null],leader:null,starLink:false,brk:'auto'});
  const toEngine=xs=>[xs[1],xs[2],xs[0],xs[3]];
  const toScreen=xs=>[xs[2],xs[0],xs[1],xs[3]];
  function draft(raw){
    const out=empty();if(!raw||raw.v!==VERSION)return out;
    out.slots=out.slots.map((_,i)=>key(raw.slots?.[i]?.key)?{key:key(raw.slots[i].key),grown:raw.slots[i].grown===true}:null);
    out.leader=key(raw.leader);out.starLink=raw.starLink===true;
    if(raw.brk===null)out.brk=null;
    else if(raw.brk&&typeof raw.brk.name==='string'&&raw.brk.name.length<=40&&Number.isInteger(raw.brk.level)&&raw.brk.level>=1&&raw.brk.level<=10)
      out.brk={name:raw.brk.name,level:raw.brk.level};
    return out;
  }
  // The same allowlist is used for local drafts and public links; no results/profile/account.
  const share=d=>({...draft(d),entry:'direct'});
  function restore(local,received){return {draft:draft(received||local),shared:!!received};}
  function storage(state){return state.shared?null:draft(state.draft);}
  function validate(d,{roster=[],info=null,restrict=null,content='op'}={}){
    const errors=[],members=d.slots.filter(Boolean),byKey=new Map(roster.map(s=>[s.key,s]));
    if(['guild','cosmo'].includes(content))errors.push({code:'unsupported',message:'아직 안 됨 · 이 콘텐츠의 직접 편성은 준비 중'});
    if(members.length!==4)errors.push({code:'count',message:`4명 미만 · ${members.length}/4명 편성 중`});
    const seen=new Set();
    d.slots.forEach((m,i)=>{if(!m)return;const s=byKey.get(m.key);
      if(!s){errors.push({code:'unknown',slot:i,message:'알 수 없는 구원자'});return;}
      if(seen.has(s.uid??s.key))errors.push({code:'duplicate',slot:i,message:'중복 구원자'});seen.add(s.uid??s.key);
      if(info&&!info.units.some(u=>u.id===s.uid))errors.push({code:'unowned',slot:i,message:'미보유'});
      if(restrict&&s.el!==restrict)errors.push({code:'element',slot:i,message:'속성 제한'});
    });
    if(!d.leader||!members.some(s=>s.key===d.leader))errors.push({code:'leader',message:'리더를 골라야 함'});
    return {ok:!errors.length,errors};
  }
  function edit(input,action){
    const d=draft(input),slots=d.slots;
    if(action.type==='put'&&key(action.key)){
      if(slots.some(s=>s?.key===action.key))return d;
      const i=Number.isInteger(action.slot)&&action.slot>=0&&action.slot<4?action.slot:toScreen([0,1,2,3]).find(i=>!slots[i]);
      if(i==null)return d;const old=slots[i];slots[i]={key:action.key,grown:false};
      if(!d.leader||d.leader===old?.key)d.leader=action.key;
    }
    if(action.type==='swap'&&[action.a,action.b].every(i=>Number.isInteger(i)&&i>=0&&i<4))
      [slots[action.a],slots[action.b]]=[slots[action.b],slots[action.a]];
    if(action.type==='remove'&&slots[action.slot]){const old=slots[action.slot];slots[action.slot]=null;if(d.leader===old.key)d.leader=slots.find(Boolean)?.key||null;}
    if(action.type==='leader'&&slots.some(s=>s?.key===action.key))d.leader=action.key;
    if(action.type==='grown'&&slots[action.slot])slots[action.slot].grown=!!action.value;
    if(action.type==='starLink')d.starLink=!!action.value;
    if(action.type==='brk')return draft({...d,brk:action.value});
    if(action.type==='clear')return empty();
    // Explicit automatic placement changes positions only; leader/growth follow their savior.
    if(action.type==='arrange'&&action.order?.length===4&&new Set(action.order).size===4&&action.order.every(k=>slots.some(s=>s?.key===k)))
      d.slots=action.order.map(k=>slots.find(s=>s.key===k));
    return d;
  }
  function serialize(d,finals={},engineKey=k=>k){
    if(d.slots.filter(Boolean).length!==4||new Set(d.slots.map(s=>s.key)).size!==4||!d.slots.some(s=>s.key===d.leader))throw Error('유효한 4명과 리더 필요');
    const units=d.slots.map(s=>{const r=finals[s.key],k=engineKey(s.key);
      return r?{key:k,build:'none',stats_override:{...r.stats},stats_final:true,power:r.power,myinfo_combat:JSON.parse(JSON.stringify(r.combat||{}))}:{key:k,build:'standard'};});
    return {units,leader:d.slots.findIndex(s=>s.key===d.leader)};
  }
  function powers(d,{info,roster,growth,content,slots,priority,standard={}}){
    if(!info){const values=d.slots.map(s=>s?standard[s.key]||null:null);return {values,before:values,total:values.reduce((n,r)=>n+(r?.power||0),0),profile:null,changes:{},errors:[],warnings:['내 정보 없음 · 표준 육성 기준']};}
    if(!growth)throw Error('성장표를 불러오는 중');
    const selected=new Set(d.slots.filter(s=>s?.grown).map(s=>s.key));
    const original=M.profile(info,roster,growth,content);
    const snapshot=M.overwrite(info,roster,growth,content,{excluded:roster.filter(s=>!selected.has(s.key)).map(s=>s.key),slots,priority});
    let profile=snapshot.profile,account=snapshot.info;const warnings=[];
    if(d.starLink){
      const unavailable=S.availability(info);
      if(unavailable)warnings.push(unavailable);
      else if(original.rule==='fixed200')warnings.push('고정 레벨 콘텐츠 · 스타링크 추가 적용 없음');
      else{
        const ids=account.star_link.slots.map(s=>s.id),byKey=new Map(roster.map(s=>[s.key,s.uid]));let extra=0;
        for(const m of d.slots.filter(Boolean)){const id=byKey.get(m.key);
          if(!account.units.some(u=>u.id===id)||account.star_link.source.includes(id)||ids.includes(id))continue;
          const free=ids.indexOf(0);if(free>=0)ids[free]=id;else{ids.push(id);extra++;}
        }
        if(extra)warnings.push(`가상 등록 ${extra}명 · 실제 빈 슬롯/교체 확인 필요`);
        account=S.withSlots(account,ids);profile=M.profile(account,roster,growth,content);
      }
    }
    const values=d.slots.map(s=>s?profile.results[s.key]||null:null),before=d.slots.map(s=>s?original.results[s.key]||null:null);
    return {values,before,total:values.reduce((n,r)=>n+(r?.power||0),0),profile,changes:snapshot.changes,errors:snapshot.errors,warnings};
  }
  function stable(v){if(Array.isArray(v))return v.map(stable);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])]));return v;}
  function signature({party,stage,brk,seed,runs,options,versions}){
    return JSON.stringify(stable({v:VERSION,units:party.units,leader:party.leader,stage,brk,seed,runs,options,versions}));
  }
  const api={VERSION,empty,draft,share,restore,storage,toEngine,toScreen,validate,edit,serialize,powers,signature};
  if(node)module.exports=api;else root.DirectParty=api;
})(typeof window!=='undefined'?window:globalThis);
