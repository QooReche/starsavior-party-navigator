// Public synthetic fixtures only. Run the real calculators and UI entry points.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),Stats=require('../myinfo_stats'),growth=require('../data/growth.json');
const slots=require('../data/myinfo_slots.json'),raw=require('./fixtures/myinfo_synthetic.json');
const source=fs.readFileSync(require.resolve('../myinfo_reco'),'utf8');
const ui=fs.readFileSync(require.resolve('../growth_ui'),'utf8'),page=fs.readFileSync('party_template.html','utf8');
const roster=[{key:'luna',uid:growth.assumed.units.luna.uid}],preset=growth.assumed.units.luna.equip;
function account(){const info=structuredClone(raw);info.units=[];
  info.star_link={level:120,source:[],slots:[]};
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  const a=M.assume('luna',info,growth);a.unit.favor=30;return {...a.targetInfo,units:[a.unit]};
}
function load(code){const ctx={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,ctx);
  return (...args)=>JSON.parse(JSON.stringify(ctx.module.exports.overwrite(...args)));
}
function equipment(overwrite=M.overwrite){
  const info=account(),u=info.units[0];
  // Six pieces of another four-piece set, exactly three already at +15.
  u.equip.forEach((e,i)=>{e.item_id=Number(Object.keys(slots).find(k=>slots[k]===i&&growth.item_sets[k]===8));e.enhance=i<3?15:12;});
  const original=structuredClone(u.equip),before=JSON.stringify(info);
  for(const content of ['op','clo','cosmo']){
    const r=overwrite(info,roster,growth,content,{includeMissing:false,slots});assert.deepEqual(r.errors,[]);
    const result=r.info.units[0],rule=Stats.rule_for_content(content);
    const oldPower=Stats.final_stats({...result,equip:original},r.info,growth,rule).power;
    const presetPower=Stats.final_stats({...result,equip:preset},r.info,growth,rule).power;
    const mixed=original.map((e,i)=>i<3?e:preset[i]);
    assert(Stats.final_stats({...result,equip:mixed},r.info,growth,rule).power<oldPower,'fixture must expose loss from mixing sets');
    assert(r.profile.results.luna.power>=oldPower,'grown equipment cannot reduce power');
    assert.deepEqual(result.equip,presetPower>oldPower?preset:original,'select exactly one complete bundle');
    assert.equal(!!r.changes.luna?.changedFields.includes('equip'),presetPower>oldPower);
  }
  assert.equal(JSON.stringify(info),before);
  // Better imported equipment stays intact even below +15, in shuffled slot order.
  u.equip.forEach(e=>{e.enhance=12;e.main.value*=10;});u.equip.reverse();
  u.skills=Object.fromEntries(Object.entries(u.skills).reverse());
  const high=overwrite(info,roster,growth,'op',{includeMissing:false,slots});
  assert.deepEqual(high.info,info);assert.deepEqual(high.changes,{},'no equipment/skill chip for reordered fields');
  // Ties retain the imported objects and order, including harmless item metadata.
  u.equip=structuredClone(preset).reverse();u.equip.forEach(e=>{e.importTag='kept';e.enhance=12;});
  const tie=overwrite(info,roster,growth,'op',{includeMissing:false,slots});
  assert.deepEqual(tie.info,info);assert.deepEqual(tie.changes,{});
  // Weak four-substat equipment must not donate extra options to the preset.
  u.equip.forEach(e=>{e.enhance=1;e.main.value=1;
    e.subs=[{stat:'NST_HP',value:1},{stat:'NST_DEF',value:1},{stat:'NST_RATE_EFFECT_HIT',value:1},{stat:'NST_RATE_EFFECT_EVADE',value:1}];});
  assert.deepEqual(Stats.final_stats(u,info,growth,'normal').missing,[],'fixture must use supported stats');
  const low=overwrite(info,roster,growth,'op',{includeMissing:false,slots});assert.deepEqual(low.errors,[]);
  assert.deepEqual(low.info.units[0].equip,preset);
  assert(low.changes.luna.changedFields.includes('equip'));
  assert(low.info.units[0].equip.every((e,i)=>e.subs.length===preset[i].subs.length&&e.subs.length<=4));
  // Shuffling the import and preset independently must not change the decision.
  const shuffled=structuredClone(growth);shuffled.assumed.units.luna.equip.reverse();
  const again=overwrite(info,roster,shuffled,'op',{includeMissing:false,slots});
  const byPart=items=>Object.fromEntries(items.map(e=>[slots[e.item_id],e]));
  assert.deepEqual(byPart(again.info.units[0].equip),byPart(low.info.units[0].equip));
  assert.deepEqual(again.changes.luna.changedFields,low.changes.luna.changedFields);
}
function baseline(code=ui){
  const first={keys:['a','b','c','d']},picked={keys:['e','f','g','h']};
  const ctx={PICK:{},LASTQ:{1:{rows:[first],all:[first,picked]}},SIMQ:{res:{a:{clear:.9,man:{c:.8}},e:{clear:.3,man:{c:.2}}}},MODE:'auto',simSig:(st,t)=>t.keys[0]};
  vm.createContext(ctx);vm.runInContext(code,ctx);
  const c={key:'op'},st={tab:'sector',name:'stage'};
  assert.equal(ctx.growthBaseline(c,st).clear,.9);
  ctx.PICK['op|sector|stage|1']='e,f,g,h';assert.equal(ctx.growthBaseline(c,st).clear,.3);
  ctx.MODE='manual';assert.equal(ctx.growthBaseline(c,st).clear,.2);
  ctx.PICK['op|sector|stage|1']='obsolete';assert.equal(ctx.growthBaseline(c,st).clear,.8);
  // Repainting after a user selection must refresh an already-finished comparison.
  ctx.PICK['op|sector|stage|1']='e,f,g,h';
  Object.assign(ctx,{seasonBlocked:()=>false,growthEnabled:()=>true,MI:{info:{}},contents:[c],cur:[st],$:(id)=>id==='growth-result'?{remove(){ctx.removed=true;}}:{value:0}});
  ctx.growthNonePaint=()=>{ctx.none=true;};ctx.miNum=n=>String(n);
  vm.runInContext("GROW.phase='done';GROW.result={baseline:{clear:.9},best:{clear:.1}};growthPaint()",ctx);
  assert.equal(vm.runInContext('GROW.result.baseline.clear',ctx),.2);assert(ctx.none);
  // 더 나은 육성 편성이 없을 때 안내 문구(조용히 사라지지 않음)
  const grown={snapshot:{changes:{a:{changedFields:['skills']}}}},flat={snapshot:{changes:{a:{changedFields:[]}}}};
  assert.equal(ctx.growthNoneText('op',{...grown,baseline:{clear:1}}),'추가 육성 없이도 모의 전투 클리어율 100%예요');
  assert.equal(ctx.growthNoneText('op',{...flat,baseline:{clear:.4}}),'이미 추천 기준까지 다 키워서 더 올릴 항목이 없어요');
  assert.equal(ctx.growthNoneText('op',{...grown,baseline:{clear:.996}}),'추천 기준까지 키워도 지금(100%)보다 잘 깨는 편성은 찾지 못했어요');
  // 0% 는 «못 깼다»를 분명히 + 도움말에 무엇을 올려 봤는지(스타링크 포함)와 다음 할 일(11/13 제보 오해)
  assert.equal(ctx.growthNoneText('op',{...grown,baseline:{clear:0}}),'추천 기준까지 키워도 이 스테이지는 모의 전투에서 깨지 못했어요 (지금 0%)');
  assert.match(ctx.growthNoneHint('op',{...grown,baseline:{clear:0}}).flat().join('|'),/올려 본 항목\|[^|]*스타링크.*\|다음 할 일\|[^|]*앞 스테이지/);
  assert.match(ctx.growthNoneHint('op',{...grown,baseline:{clear:.4}}).flat().join('|'),/결론\|[^|]*가장 나은 선택/);
  assert.equal(ctx.growthNoneHint('op',{...grown,baseline:{clear:1}}).length,0);
  assert.ok(!ctx.growthNoneHint('op',{...flat,baseline:{clear:0}}).some(([k])=>k.includes('올려 본 항목')));   // 이미 다 키웠으면 «올려 본 항목» 없이 다음 할 일만
  assert.equal(ctx.growthNoneText('clo',{...grown}),'추천 기준까지 키워도 지금보다 잘 깨는 편성은 찾지 못했어요');
  assert.equal(ctx.growthNoneText('guild',{...grown,baseline:{score:1200}}),'추천 기준까지 키워도 지금(1200점)보다 점수가 높은 편성은 찾지 못했어요');
  assert.equal(ctx.growthNoneText('cosmo',{...grown,baseline:{sum:1}}),'추천 기준까지 키워도 지금(1점)보다 점수가 높은 편성은 찾지 못했어요');
}
async function speed(code=page){
  const fn=code.slice(code.indexOf('async function cosmoSearchStart('),code.indexOf('$("cosmo-search").addEventListener("change"'));
  for(const finalPhase of [false,true])for(const grown of [false,true]){
    const writes=[],state={id:0,phase:'idle',optLevel:0,optMode:'mean'};
    const ctx={seasonBlocked:()=>false,CSR:state,MI:{info:{},profiles:{}},SIMQ:{busy:null},GSR:{phase:'idle'},D:{cosmoRaid:{search:{},bosses:[],levelMax:18}},R:[],EXCL:new Set(),
      location:{href:'http://example.test/'},LS:{get:()=>({sec:{old:1}}),set:(k,v)=>writes.push([k,v])},
      csSig:()=>'',csWorkers:()=>2,csBreaks:()=>[],csNow:()=>1,csTick(){},growthCancel(){},growthPaint(){},renderCosmoSearch(){},growthEnabled:()=>false,growthOwnedContext:()=>'',
      miGrowth:async()=>growth,MyInfoReco:{profile:()=>({results:{}})},
      CosmoSearch:{searchSettings:s=>s,priorFrom:v=>v,etaNew:()=>({summary:()=>({new:2}),begin(){},update(){}}),
        search:async opts=>{opts.onPlan({stages:[]});opts.onPhase('running',1,{stage:'screen',games:4,runs:4});opts.onProgress(1,1);
          if(finalPhase)opts.onPhase('finish',1,{stage:null,runs:100});return {rows:[{sum:1,teams:[]}],runs:100};}}};
    vm.createContext(ctx);vm.runInContext(fn,ctx);await ctx.cosmoSearchStart(state,grown?{results:{}}:null);
    assert.equal(state.phase,'done');assert.equal(writes.length,grown?0:1,`speed storage: grown=${grown}, finalPhase=${finalPhase}`);
    if(writes.length)assert.equal(writes[0][0],'cosmo.speed.v2');
  }
}
async function mutation(name,code,from,to,test){assert(code.includes(from),name+' anchor');let caught=false;
  try{await test(code.replace(from,to));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'mutation survived: '+name);console.log('MUTATION caught + restored:',name);
}
(async()=>{
  equipment();equipment(load(source));baseline();await speed();
  await mutation('whole bundle selection',source,'if(!(presetPower>originalPower))u.equip=clone(old.equip);',
    'u.equip=u.equip.map((e,i)=>old.equip[i]?.enhance>=15?clone(old.equip[i]):e);',s=>equipment(load(s)));
  await mutation('tie retains original',source,'presetPower>originalPower','presetPower>=originalPower',s=>equipment(load(s)));
  await mutation('preset substats only',source,'const rule=Stats.rule_for_content(content),presetPower=',
    'u.equip.forEach((e,i)=>e.subs.push(...(old.equip[i]?.subs||[])));const rule=Stats.rule_for_content(content),presetPower=',s=>equipment(load(s)));
  await mutation('picked comparison',ui,"selected&&(q?.all||q?.rows||[]).find(t=>t.keys.slice().sort().join(',')===selected)",'null',baseline);
  await mutation('selection after completion',ui,"if(r&&['op','clo'].includes(c.key))r.baseline=growthBaseline(c,cur[$('stage').value]);",'',baseline);
  await mutation('cosmo phase speed isolation',page,'if(sm&&!profileOverride)LS.set','if(sm)LS.set',speed);
  await mutation('cosmo final speed isolation',page,'if(sum&&!profileOverride)LS.set','if(sum)LS.set',speed);
  console.log('ALL OK overwrite review: bundles, slots, chips, PICK, speed; 7 mutations');
})().catch(e=>{console.error(e);process.exitCode=1;});
