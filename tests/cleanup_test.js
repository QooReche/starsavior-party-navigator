// 실제 페이지 함수와 Worker를 합성 저장소·네트워크에서 실행하는 결함 회귀.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_import.js');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const part=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
function validation(){
 const valid=JSON.parse(fs.readFileSync(require.resolve('./fixtures/myinfo_synthetic.json'),'utf8'));
 valid.tactics.groups.TG_STAR={level:64,attack:65,defense:64,hp:65};
 assert.equal(M.validate(valid),'');
 for(const change of [u=>u.equip=[null],u=>u.equip=[{subs:[null]}],u=>u.equip=[{main:[]}],u=>u.gauntlet={potentials:[null]},u=>u.skills=[],u=>u.favor=NaN]){
  const bad=structuredClone(valid);change(bad.units[0]);assert.ok(M.validate(bad));
 }
}
function storage(){
 let fail=false,value=null;const c=vm.createContext({localStorage:{setItem(k,v){if(fail)throw Error('quota');value=v},getItem(){return value},removeItem(){if(fail)throw Error('denied');value=null}},MyInfoImport:M,MyInfoReco:{hash:()=>''}});
 vm.runInContext(part('const LS=','const SKILLS='),c);
 assert.equal(vm.runInContext('LS.set("myinfo",{a:1})',c),true);fail=true;
 assert.equal(vm.runInContext('LS.set("myinfo",{a:2})',c),false);
 fail=false;value='{invalid';
 const d=vm.createContext({localStorage:{getItem:()=>value},MyInfoImport:M,MyInfoReco:{hash:()=>''}});
 vm.runInContext(part('const LS=','const SKILLS='),d);assert.equal(vm.runInContext('MI.invalid&&MI.info===null',d),true);
}
function atomic(){
 const path=require('node:path'),{atomicText}=require('../tools/fileio.js');
 const dir=path.resolve(__dirname,'../local/cleanup-node-io');fs.mkdirSync(dir,{recursive:true});
 const out=path.join(dir,'out.txt');fs.writeFileSync(out,'old');const rename=fs.renameSync;
 try{fs.renameSync=()=>{throw Error('locked')};assert.throws(()=>atomicText(out,'새 값\r\n'),/locked/)}finally{fs.renameSync=rename}
 assert.equal(fs.readFileSync(out,'utf8'),'old');assert.deepEqual(fs.readdirSync(dir),['out.txt']);
 atomicText(out,'새 값\r\n');assert.equal(fs.readFileSync(out,'utf8'),'새 값\n');fs.unlinkSync(out);fs.rmdirSync(dir);
}
async function apply(){
 let failed=false,saved=null,status='',calculateFails=false;
 const order=[],info={format:'ss-myinfo-v1',units:[{id:1}]};
 const c=vm.createContext({MI:{importId:0,info:null},MyInfoImport:M,R:[{uid:1,key:'a'}],Set,
  miStatus(t){status=t},miGrowth:async()=>({}),miCheck(){order.push('calculate');if(calculateFails)throw Error('bad')},
  miReset(v){order.push('render');c.MI.info=v},LS:{set(k,v){order.push('save');if(failed)return false;saved=v;return true}},
  document:{querySelectorAll:()=>[]},saveSel(){},updCount(){},renderMi(){},rerun(){},miSummary:()=>'',
  syncOwn(){},sharedBar(){},rerunNow(){},SHARE:{},SIMQ:{},REQ:false});
 vm.runInContext(part('async function miApply(','$("mi-file").addEventListener'),c);
 calculateFails=true;assert.equal(await c.miApply(info),false);assert.equal(saved,null);assert.equal(c.MI.info,null);
 calculateFails=false;order.length=0;assert.equal(await c.miApply(info),true);assert.deepEqual(order,['calculate','render','save']);
 failed=true;await c.miApply(info);assert.equal(c.MI.saved,false);assert.match(status,/저장 안 됨/);
 assert.ok(html.includes('MI.saved?`저장됨 ${savedTime(date)}`:"저장 안 됨'));
 const calc=vm.createContext({R:[],MyInfoReco:{profile:()=>({results:{a:{power:Infinity,stats:{atk:1}}}})}});
 vm.runInContext(part('function miCheck(','function miLoad('),calc);
 assert.throws(()=>calc.miCheck(info,{}),/계산값/);
}
async function graph(){
 let visible=false,created=0,injected=0,scriptEl=null;
 const els={graphwrap:{hidden:false},cy:{innerHTML:''},gcw:{style:{}},gmode:{value:'party'}};
 const c=vm.createContext({
  cy:null,$:id=>els[id],
  document:{body:{classList:{contains:()=>visible}},
   createElement(){scriptEl={onload:null,onerror:null,src:''};return scriptEl},
   head:{appendChild(){injected++}}},
  D:{cytoUrl:'lib/cytoscape.min.js?v=test'},
  graphData:()=>({nodes:[],edges:[]}),Promise,setTimeout:()=>{}});
 vm.runInContext(part('let _cyP=null;','["gmode","gcenter","gmin","gconf"].forEach'),c);
 // 첫 표시 전: 스크립트 주입 안 함
 c.drawGraph();assert.equal(injected,0,'not visible: no inject');
 // 첫 표시: 1회 주입
 visible=true;c.drawGraph();assert.equal(injected,1,'first inject');
 // 로드 중 중복 호출: 주입 추가 없음
 c.drawGraph();c.drawGraph();assert.equal(injected,1,'concurrent: no extra inject');
 // 로드 완료: cytoscape() 1회 생성
 c.cytoscape=function(){created++;return {on(){},destroy(){}}};
 const p=vm.runInContext('_cyP',c);scriptEl.onload();
 await p;await Promise.resolve();
 assert.equal(created,1,'concurrent: 1 create');
 // 반복: 재주입·재생성 없음(cy 있고 graphDirty=false)
 c.drawGraph();await Promise.resolve();assert.equal(injected,1,'no re-inject');assert.equal(created,1,'no re-create');
 // graphDirty: 재생성하되 재주입 없음
 vm.runInContext('graphDirty=true',c);c.drawGraph();await Promise.resolve();
 assert.equal(injected,1,'dirty: no re-inject');assert.equal(created,2,'dirty: re-create');
 // 실패: 안내 표시, _cyP 초기화(재시도 가능)
 vm.runInContext('_cyP=null;graphDirty=true',c);c.cy=null;c.cytoscape=undefined;injected=0;scriptEl=null;
 visible=true;c.drawGraph();assert.equal(injected,1,'fail: inject');
 scriptEl.onerror(new Error('fail'));
 await new Promise(r=>setTimeout(r,0));
 assert.ok(els.cy.innerHTML.includes('구조도 라이브러리를 불러오지 못했습니다'),'failure msg');
 assert.equal(vm.runInContext('_cyP',c),null,'promise cleared for retry');
}
async function worker(status=200,badFile=false){
 let active=0,max=0,writes=0,python=false;
 const files=Array.from({length:12},(_,i)=>'file'+i);
 const c=vm.createContext({URL,Uint8Array,self:{location:{href:'http://local/sim_worker.js'}},postMessage(){},importScripts(){},
  loadPyodide:async()=>({FS:{mkdirTree(){},writeFile(){writes++}},runPython(){assert.equal(writes,files.length);python=true}}),
  fetch:async url=>{if(url.endsWith('manifest.json'))return {ok:status===200,status,json:async()=>({files,ver:'v'})};
   active++;max=Math.max(max,active);await new Promise(r=>setTimeout(r,2));active--;
   return {ok:!(badFile&&url.includes('file0?')),status:503,arrayBuffer:async()=>new ArrayBuffer(1)};}});
 vm.runInContext(fs.readFileSync(require.resolve('../sim_worker.js'),'utf8'),c);
 if(status!==200||badFile){await assert.rejects(c.boot('http://local/'),/HTTP/);assert.equal(python,false)}
 else{await c.boot('http://local/');assert.ok(max>=4&&max<=6);assert.equal(python,true)}
}
(async()=>{validation();storage();atomic();await apply();await graph();await worker();await worker(404);await worker(200,true);console.log('cleanup JS OK: validation/storage/recovery/atomic/graph/worker')})().catch(e=>{console.error(e);process.exitCode=1});
