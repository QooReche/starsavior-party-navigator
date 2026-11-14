// 스텔라 아카이브 육성 목표(11/14): 아카이브 5칸은 한 번의 여정 결과로 통째로 정해진다(한 칸 SG 는 현실적, 두 칸 동시 SG 는 어려움).
//  ① 주력 판단 = 공략 DB «여정 스탯 우선순위»(data/journey_priority.json): 어느 줄이든 첫 묶음(동률 포함)의 칸 하나가 950 이상이면 충족 → 아카이브는 키울 항목이 아님
//  ② 미충족이면 «다시 만든 기록» 후보: 기준표 예시 기록의 값(1250·515·473·168·129)을 우선순위 순서대로 배정, 같은 묶음 안에서는 지금 값이 높은 칸에 큰 값
//     (일반 디펜더는 두 줄 → 후보 둘 다 비교)
//  ③ 장비 묶음(지금/기준표) × 기록(지금/후보)을 통째로 조합 비교해 전투력이 가장 높은 조합 하나 — 섞지 않고, 같으면 지금 것, 결과가 지금보다 약해지지 않는다
//  ④ 채택되면 칩에 지금 주력 → 바뀌는 주력
// 제보(가상 수치로 재현): 왈츠 아세라 힘 247·체력 1250·인내 761·집중 122·보호 97 — 우선순위가 [힘, 체력] > 인내 > [집중, 보호] 라 체력 SG 로 이미 충족 → 목표 없음.
// 종전엔 칸별 max 로 «힘 1250 + 체력 1250 …»(합 3,905)이라는 불가능한 기록으로 계산해 육성 결과가 부풀려졌다. 공개 가상 픽스처만 쓴다. 실행: node tests/archive_whole_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),S=require('../myinfo_stats'),U=require('../ux_ui');
const growth=require('../data/growth.json'),grades=require('../data/archive_grades.json'),raw=require('./fixtures/myinfo_synthetic.json');
const priority=require('../data/journey_priority.json');
const view={...require('../data/myinfo_view.json'),itemSlots:require('../data/myinfo_slots.json')},slots=view.itemSlots;
const source=fs.readFileSync(require.resolve('../myinfo_reco'),'utf8'),uxSource=fs.readFileSync(require.resolve('../ux_ui'),'utf8');
const sum=a=>a.reduce((x,y)=>x+y,0),NAMES=['힘','체력','인내','집중','보호'],VALUES=[1250,515,473,168,129];
// 다른 VM 에서 만든 배열·객체는 deepEqual 이 «원형이 다르다»고 본다 → 비교값은 모두 JSON 으로 정규화한다
const plain=x=>x===undefined?undefined:JSON.parse(JSON.stringify(x)),same=(a,b,msg)=>assert.deepEqual(plain(a),plain(b),msg);
function load(code){const ctx={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,ctx);return ctx.module.exports;}
const specOf=key=>growth.assumed.units[key];
// 다른 항목은 모두 기준 이상(아카이브·장비만 본다): 기준표 세팅으로 만든 뒤 고친다
function account(key,journey,edit){const info=structuredClone(raw);info.units=[];info.star_link={level:240,source:[],slots:[]};info.star_link_level=240;
 for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
 const u=M.assume(key,info,growth).unit;u.level=240;u.favor=30;
 if(journey===null)delete u.gauntlet;else u.gauntlet.journey=journey.slice();
 if(edit)edit(u);info.units=[u];return info;}
const powerOf=(info,unit,content='op')=>S.final_stats(unit,info,growth,S.rule_for_content(content)).power;
const withRecord=(info,journey,equip)=>{const u=structuredClone(info.units[0]);u.gauntlet.journey=journey.slice();if(equip)u.equip=structuredClone(equip);return u;};
function run(m,key,journey,{content='op',edit=null,usePriority=true}={}){const info=account(key,journey,edit),before=JSON.stringify(info);
 const r=plain(m.overwrite(info,[{key,uid:specOf(key).uid}],growth,content,{slots,...(usePriority?{priority}:{})}));
 same(r.errors,[]);assert.equal(JSON.stringify(info),before,'원본 계정은 그대로');
 const a=r.changes[key],unit=r.info.units[0];
 return {info,r,a,unit,now:unit.gauntlet.journey,changed:!!a?.changedFields.includes('journey'),equipChanged:!!a?.changedFields.includes('equip'),
  power:r.profile.results[key].power,original:powerOf(info,info.units[0],content)};}
// 줄(우선순위 묶음들)과 지금 기록 → 다시 만든 기록(시험 쪽에서 따로 계산한 기대값)
function remake(groups,journey){const order=groups.flatMap(g=>g.slice().sort((a,b)=>journey[b]-journey[a]||a-b)),out=Array(5).fill(0);order.forEach((slot,i)=>{out[slot]=VALUES[i]});return out;}

function check(m=M,ux=U){
 const A='waltz-asherah',ASHERAH=[247,1250,761,122,97];
 same(priority.units[A].map(r=>r.groups),[[[0,1],[2],[3,4]]],'시험 전제: 왈츠 아세라 = [힘, 체력] > 인내 > [집중, 보호]');
 same([...specOf(A).journey].sort((a,b)=>b-a),VALUES,'시험 전제: 기준표 예시 기록의 값');
 // ① 제보 수치: 첫 묶음 [힘, 체력] 가운데 체력이 1250 → 충족 → 아카이브 목표 없음(통째 교체 후보도 만들지 않는다)
 {const x=run(m,A,ASHERAH);assert(!x.changed,'체력 SG 로 주력 충족');same(x.now,ASHERAH);assert.equal(x.a,undefined,'바꿀 항목 없음');assert.equal(x.power,x.original);}
 for(const j of [[950,0,0,0,0],[0,950,0,0,0],[1250,1250,0,0,0]]){const x=run(m,A,j);assert(!x.changed,'첫 묶음 한 칸이 950 이상이면 충족: '+j);same(x.now,j);}
 for(const j of [[949,949,1250,1250,1250]]){const x=run(m,A,j);same(x.now,j,'미충족 후보여도 지금 기록이 더 강하면 유지');assert(!x.changed);}
 // ② 미충족(힘 247·체력 500): 우선순위대로 다시 만든 기록 — 같은 묶음 [힘, 체력] 안에서는 지금 값이 높은 체력이 주력(1250), 힘이 다음(515)
 {const low=[247,500,300,122,97],x=run(m,A,low),want=remake(priority.units[A][0].groups,low);
  same(want,[515,1250,473,168,129],'시험 전제: 기대 기록');
  assert(x.changed,'미충족 → 교체');same(x.now,want);assert.equal(sum(x.now),sum(VALUES),'교체하면 합 = 예시 기록 합');
  assert.equal(x.now.filter(v=>v>=1250).length,1,'SG 는 한 칸');same(x.a.changes.journey,{before:low,after:want});
  assert.equal(x.power,powerOf(x.info,withRecord(x.info,want)),'육성 계정의 전투력 = 통째 교체한 기록의 전투력');assert(x.power>x.original);
  // ④ 칩: 주력이 그대로 체력이면 «주력 체력 … → 체력 SG»
  const f=ux.member(x.a,x.info,growth,'op',grades,view).fields.find(f=>f.field==='journey');
  assert.equal(f.label,'스텔라 아카이브 기록 다시 만들기');assert.match(f.short,/^\(주력 체력 .+ → 체력 SG\)$/);assert.match(f.detail,/기록 전체를 다시 만드는/);
  assert.equal(f.delta,x.power-x.original,'칩의 전투력 차이 = 통째 교체의 차이');}
 // 같은 묶음에서 지금 값이 힘 쪽이 높으면 힘이 주력, 지금 값이 같으면 칸 번호 순(힘)
 same(run(m,A,[500,247,300,122,97]).now,[1250,515,473,168,129]);same(run(m,A,[300,300,100,90,95]).now,[1250,515,473,129,168],'뒤 묶음 [집중, 보호]도 지금 값이 높은 칸에 큰 값');
 // 주력을 첫 묶음 밖(인내)에 찍은 약한 기록: 교체를 채택하고 칩에 «주력 인내 … → 체력 SG»(지금 주력을 버리는 추천임)
 {const other=[100,200,1000,122,97],x=run(m,A,other);assert(x.changed);same(x.now,[515,1250,473,168,129]);
  const d=ux.member(x.a,x.info,growth,'op',grades,view),f=d.fields.find(f=>f.field==='journey');
  assert.equal(f.short,`(주력 인내 ${ux.grade(1000,2,grades)||'1,000'} → 체력 SG)`);assert.match(f.detail,/지금보다 내려가는 칸: 인내/);
  assert.match(ux.todosHtml(d),/스텔라 아카이브 기록 다시 만들기 \(주력 인내 .+ → 체력 SG\)/);}
 // 집중 우선 패턴(아모라: 힘 > 집중 > [체력, 인내] > 보호), 서포터 기본(체력 > 인내 > [집중, 보호] > 힘)
 {const key='amora';same(priority.units[key][0].groups,[[0],[3],[1,2],[4]]);
  assert(!run(m,key,[950,0,0,0,0]).changed);const x=run(m,key,[100,300,400,1250,90]);
  assert(x.changed,'집중이 SG 여도 첫 묶음(힘)이 950 미만이면 미충족');same(x.now,[1250,168,473,515,129],'힘 1250 · 집중 515 · 인내(지금 높음) 473 · 체력 168 · 보호 129');}
 {const key=Object.keys(priority.units).find(k=>JSON.stringify(priority.units[k].map(r=>r.groups))===JSON.stringify([[[1],[2],[3,4],[0]]])&&specOf(k));
  assert(key,'시험 전제: 서포터 기본 패턴 구원자');assert(!run(m,key,[0,950,0,0,0]).changed);
  const x=run(m,key,[1250,300,200,50,60]);same(x.changed?x.now:null,x.changed?[129,1250,515,168,473]:null,'체력 1250 · 인내 515 · 보호(지금 높음) 473 · 집중 168 · 힘 129');}
 // 일반 디펜더(두 줄: 퓨어탱커 [체력, 인내] > 힘 > … / 공격력 탱커 힘 > 체력 > 인내 > …): 어느 줄이든 충족이면 충족, 미충족이면 후보 둘을 모두 비교해 전투력이 높은 쪽
 {const key=Object.keys(priority.units).find(k=>priority.units[k].length===2&&specOf(k));assert(key,'시험 전제: 두 줄 디펜더');
  const rows=priority.units[key].map(r=>r.groups);same(rows,[[[1,2],[0],[3,4]],[[0],[1],[2],[3,4]]]);
  for(const j of [[0,950,0,0,0],[0,0,950,0,0],[950,0,0,0,0]])assert(!run(m,key,j).changed,'두 줄 가운데 한 줄의 첫 묶음 충족: '+j);
  const low=[300,200,400,100,90],x=run(m,key,low),cands=rows.map(g=>remake(g,low));
  same(cands,[[473,515,1250,168,129],[1250,515,473,168,129]],'시험 전제: 줄마다 후보 하나');
  const powers=cands.map(c=>powerOf(x.info,withRecord(x.info,c)));assert.notEqual(powers[0],powers[1],'시험 전제: 두 후보의 전투력이 다름');
  assert(x.changed);same(x.now,cands[powers[1]>powers[0]?1:0],'두 후보 가운데 전투력이 높은 쪽');assert.equal(x.power,Math.max(...powers));}
 // 우선순위 표 없이 부르면(옛 호출) 기준표 기록의 주력 칸만 보고, 후보는 기준표 기록 그대로
 {const x=run(m,A,[100,400,300,100,50],{usePriority:false});assert(x.changed);same(x.now,specOf(A).journey);
  assert(!run(m,A,[950,0,0,0,0],{usePriority:false}).changed);assert(!run(m,A,specOf(A).journey,{usePriority:false}).changed,'같은 기록이면 그대로');}
 // 아카이브가 아예 없으면 다시 만든 기록(지금 값이 없으니 칸 번호 순)
 {const info=account(A,null),r=plain(m.overwrite(info,[{key:A,uid:specOf(A).uid}],growth,'op',{slots,priority}));same(r.errors,[]);
  same(r.info.units[0].gauntlet.journey,[1250,515,473,168,129]);assert(r.changes[A].changedFields.includes('journey'));}
 // ③ 장비 × 기록 조합 비교(11/14 리뷰 재현): 기준표 장비가 약해진 계정 — 무기만 +11, 옵션 75% 절삭. 한 축을 먼저 정하면 «지금 장비 + 지금 기록»보다 약해졌다(47,377 → 46,852)
 {const weaken=u=>{u.equip.forEach((e,i)=>{if(slots[e.item_id]===0)e.enhance=11;e.main.value=Math.floor(e.main.value*.25);e.subs.forEach(s=>{s.value=Math.floor(s.value*.25)})})};
  for(const [j,usePriority] of [[[100,1250,350,122,97],false],[[100,1250,350,122,97],true],[[100,300,350,122,97],true],[[100,300,350,122,97],false],[[900,1250,1250,1250,1250],false]]){
   const x=run(m,A,j,{edit:weaken,usePriority}),old=x.info.units[0],preset=specOf(A).equip;
   assert(x.power>=x.original,`결과가 지금보다 약해짐: ${x.original} → ${x.power} (${j}, 우선순위 ${usePriority})`);
   // 네 조합(장비 2 × 기록 2)을 시험 쪽에서 따로 계산: 가장 높은 조합과 같아야 하고, 섞인 장비·기록이 아니어야 한다
   const main=specOf(A).journey.indexOf(1250),met=usePriority?priority.units[A][0].groups[0].some(i=>j[i]>=950):j[main]>=950;
   const cand=met?[j]:[j,...(usePriority?priority.units[A].map(r=>remake(r.groups,j)):[specOf(A).journey])];
   const combos=[old.equip,preset].flatMap(e=>cand.map(rec=>({e,rec,p:powerOf(x.info,withRecord(x.info,rec,e))})));
   assert.equal(x.power,Math.max(...combos.map(c=>c.p)),'전투력이 가장 높은 조합: '+j);
   assert(cand.some(rec=>JSON.stringify(rec)===JSON.stringify(x.now)),'기록은 통째로: '+x.now);
   const eq=JSON.stringify(x.unit.equip);assert(eq===JSON.stringify(old.equip)||eq===JSON.stringify(preset),'장비는 묶음째로');}
  // 동시 교체: 장비도 기록도 약한 계정 → 둘 다 바뀐다
  const both=run(m,A,[100,300,350,122,97],{edit:weaken});assert(both.changed&&both.equipChanged,'장비·기록 동시 교체');same(both.unit.equip,specOf(A).equip);same(both.now,[515,1250,473,168,129]);
  // 같은 전투력이면 지금 것: 장비를 기준표 그대로(순서만 뒤집음) 둔 계정
  // 같은 전투력이면 지금 것(가져온 표지·순서 그대로): 기준표와 능력치가 같은 장비를 +11 로만 낮춰 후보에 올린 계정
  const tie=run(m,A,[100,1250,350,122,97],{edit:u=>{u.equip.reverse();u.equip.forEach(e=>{e.importTag='kept'});u.equip[0].enhance=11}});
  assert.equal(powerOf(tie.info,withRecord(tie.info,[100,1250,350,122,97],specOf(A).equip)),tie.original,'시험 전제: 두 장비 묶음의 전투력이 같음');
  assert(!tie.equipChanged&&!tie.changed,'동률이면 지금 장비');assert(tie.unit.equip.every(e=>e.importTag==='kept'));assert.equal(tie.power,tie.original);}
 // 플래시 포인트(Lv200 고정)도 같은 원칙
 {const x=run(m,A,ASHERAH,{content:'rush'});assert(!x.changed);assert(x.power>=x.original);}
 assert.equal(m.OVERWRITE_VERSION,'grown-account-v6');assert.equal(m.THRESHOLD_POLICY.archiveWhole,true);assert.equal(m.THRESHOLD_POLICY.archivePriority,'guide');assert.equal(m.THRESHOLD_POLICY.archiveMain,950);
}
// 공략 DB 지연 대비: 페이지 로스터에는 있는데 DB 에 없는 구원자는 직업 기본값으로 채우고 fallback 에 적는다(조용히 대체하지 않음). 실제 도구를 가짜 로스터로 돌린다
{const cp=require('node:child_process'),os=require('node:os'),path=require('node:path'),dir=fs.mkdtempSync(path.join(os.tmpdir(),'journey-priority-'));
 try{const tool=require.resolve('../tools/extract_journey_priority.js'),guide=require.resolve('../rawdata/guide_app-core.js'),roster=path.join(dir,'roster.json'),out=path.join(dir,'out.json');
  const real=require('../data/savior_reco.json').saviors.map(s=>({key:s.key,className:s.className}));
  // 지금 자료가 최신 추출과 같은가(가이드·로스터를 고치고 다시 안 뽑으면 실패)
  fs.writeFileSync(roster,JSON.stringify({saviors:real}));
  const now=cp.spawnSync('node',[tool,guide,roster,out],{encoding:'utf8'});assert.equal(now.status,0,now.stderr);
  same(JSON.parse(fs.readFileSync(out,'utf8')),priority,'data/journey_priority.json 이 낡음 — node tools/extract_journey_priority.js 다시 실행');
  const missing=Object.keys(priority.fallback);same(missing,real.map(s=>s.key).filter(k=>!new RegExp('^    "id": "'+k+'",?\\s*$','m').test(fs.readFileSync(guide,'utf8'))),'fallback = 로스터 − 공략 DB');
  console.log(`[알림] 공략 DB 에 없는 구원자 ${missing.length}명${missing.length?'(직업 기본값): '+missing.join(', '):''} · DB 받은 날짜 ${priority.db_fetched||'기록 없음'}`);
  assert.match(String(priority.db_fetched),/^\d{4}-\d{2}-\d{2}$/,'DB 받은 날짜 기록');
  for(const k of real.map(s=>s.key))assert(priority.units[k],k+' 우선순위 없음(로스터에 있음)');
  // 신규 구원자 셋(레인저·디펜더·모르는 직업)이 로스터에만 있는 경우
  fs.writeFileSync(roster,JSON.stringify({saviors:[...real.slice(0,2),{key:'new-ranger',className:'레인저'},{key:'new-defender',className:'디펜더'},{key:'new-unknown',className:'신규직업'}]}));
  const r=cp.spawnSync('node',[tool,guide,roster,out],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);
  const d=JSON.parse(fs.readFileSync(out,'utf8'));
  same(d.fallback,{'new-ranger':'레인저','new-defender':'디펜더','new-unknown':'신규직업'});assert.match(r.stdout,/\[알림\] 공략 DB 에 없는 구원자 3명/);
  same(d.units['new-ranger'].map(x=>x.groups),[[[0],[3],[1,2],[4]]],'레인저 기본 = 힘 > 집중 > [체력, 인내] > 보호');
  same(d.units['new-defender'].map(x=>x.groups),[[[1,2],[0],[3,4]],[[0],[1],[2],[3,4]]],'디펜더 기본 = 두 줄');
  same(d.units['new-unknown'].map(x=>x.groups),[[[0],[1,2],[3,4]]],'모르는 직업 = 가이드의 기본 분기');
  assert(!d.fallback[real[0].key]&&d.units[real[0].key],'DB 에 있는 구원자는 fallback 이 아님');
  // 직업 기본값으로 채운 구원자도 같은 규칙으로 판단한다(표시만 다름)
  {const key='waltz-asherah',fake={...priority,units:{...priority.units,[key]:d.units['new-ranger']},fallback:{[key]:'레인저'}};
   const info=account(key,[247,1250,761,122,97]),x=plain(M.overwrite(info,[{key,uid:specOf(key).uid}],growth,'op',{slots,priority:fake}));
   same(x.errors,[]);const cand=[1250,473,168,515,129],keep=powerOf(info,info.units[0]),swap=powerOf(info,withRecord(info,cand));
   same(x.info.units[0].gauntlet.journey,swap>keep?cand:[247,1250,761,122,97],'레인저 기본(힘 주력)이면 체력 SG 로는 충족이 아님 → 후보(힘 1250·집중 515·체력 473·인내 168·보호 129)와 비교');}
  // 직업이 없으면 기본값도 못 정한다 → 조용히 넘기지 않고 실패
  fs.writeFileSync(roster,JSON.stringify({saviors:[{key:'no-class'}]}));assert.notEqual(cp.spawnSync('node',[tool,guide,roster,out],{encoding:'utf8'}).status,0);
 }finally{fs.rmSync(dir,{recursive:true,force:true})}}
// 우선순위 표 자체: 59명 모두 있고, 줄마다 다섯 칸이 한 번씩, 출처·등급 표기
{assert.equal(priority.grade,'guide');assert.match(priority.source,/guide_app-core\.js/);same(priority.stats,NAMES);
 for(const key of Object.keys(growth.assumed.units)){const rows=priority.units[key];assert(rows?.length>=1,key+' 우선순위 없음');
  for(const r of rows)same(r.groups.flat().slice().sort(),[0,1,2,3,4],key);}
 assert.equal(Object.values(priority.units).filter(r=>r.length===2).length,6,'두 줄(일반 디펜더) 6명');
 const hay=priority.units.haydee;same(hay.map(r=>r.groups),[[[2],[1],[3],[4],[0]]],'하이디 예외');}
check();console.log('PASS 스텔라 아카이브: 우선순위 주력 판단(제보 수치 = 목표 없음)·미충족이면 우선순위대로 다시 만들기·디펜더 두 줄·장비×기록 조합 비교(약해지지 않음)·동시 교체·동률 유지·칩');
// 무변경 대조군: VM 에 올린 «고치지 않은» 코드도 통과해야 한다(결함 주입이 VM 차이 때문에 잡히는 것이 아님을 먼저 확인)
check(load(source),load(uxSource));console.log('PASS 무변경 대조군(VM 에 올린 원본)');
// 결함 주입: 되돌리면 실패해야 한다
const rep=(s,a,b)=>{assert(s.includes(a),'주입 대상 없음: '+a);return s.replace(a,b)};
const mutants={
 '칸별 max 섞기(옛 동작)':[rep(source,"u.equip=clone(best.equip);if(best.record)u.gauntlet.journey=clone(best.record);","u.equip=clone(best.equip);if(best.record)u.gauntlet.journey=best.record.map((v,i)=>Math.max(v,old.gauntlet?.journey?.[i]||0));"),uxSource],
 '기준표 주력 칸만 봄(우선순위 무시)':[rep(source,"const rows=priority?.units?.[key];","const rows=null;"),uxSource],
 '첫 묶음의 첫 칸만 봄(동률 무시)':[rep(source,"first=rows?rows.map(g=>g[0]):[[main]];","first=rows?rows.map(g=>g[0].slice(0,1)):[[main]];"),uxSource],
 '첫 줄만 봄(디펜더 둘째 줄 무시)':[rep(source,"return rows?.length?rows.map(r=>r.groups):null;","return rows?.length?rows.slice(0,1).map(r=>r.groups):null;"),uxSource],
 '어느 칸이든 950 이상이면 충족':[rep(source,"return first.some(group=>group.some(i=>(journey?.[i]||0)>=THRESHOLD_POLICY.archiveMain));","return (journey||[]).some(v=>v>=THRESHOLD_POLICY.archiveMain);"),uxSource],
 '동률 묶음을 칸 번호 순으로만':[rep(source,"group.slice().sort((a,b)=>(journey?.[b]||0)-(journey?.[a]||0)||a-b)","group.slice()"),uxSource],
 '후보를 기준표 기록 그대로':[rep(source,"    if(!rows)return [clone(spec.journey)];","    if(true)return [clone(spec.journey)];"),uxSource],
 '언제나 다시 만든 기록으로':[rep(source,"[...(old.gauntlet?.journey?[old.gauntlet.journey]:[]),...archiveCandidates(","[...archiveCandidates("),uxSource],
 '언제나 지금 기록 유지':[rep(source,"if(!best||power>best.power)best={power,equip,record};","if(!best||(power>best.power&&record===records[0]))best={power,equip,record};"),uxSource],
 '동률이면 교체':[rep(source,"if(!best||power>best.power)","if(!best||power>=best.power)"),uxSource],
 '기록을 기준표 장비로 먼저 정함(리뷰 결함)':[rep(source,"for(const equip of equips)for(const record of records){","for(const equip of equips.slice(-1))for(const record of records){"),uxSource],
 '칩에 지금 주력을 안 보임':[source,rep(uxSource,"mb==null?'없음':names[mb]+' '+g(b,mb)","'없음'")],
 '칩 이름이 옛 «스텔라 아카이브»':[source,rep(uxSource,"f==='journey'?'스텔라 아카이브 기록 다시 만들기':labels[f]","labels[f]")]};
for(const [name,[code,ux]] of Object.entries(mutants)){let caught=false;try{check(load(code),load(ux))}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e}
 assert(caught,'결함 주입이 통과해 버림: '+name);console.log('MUTATION caught:',name)}
console.log('ALL OK archive whole record; '+Object.keys(mutants).length+' mutations');
