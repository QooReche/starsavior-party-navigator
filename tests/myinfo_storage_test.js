// Exercise actual page startup and input handlers without a browser.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const section=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
function boot(saved,info=null){
  const option={disabled:true},grow={value:'1',options:['myinfo','1','0.8','1.25','manual'].map(value=>({value})),querySelector:()=>option};
  const els={grow,mypow:{value:''},rk:{value:'0',options:[]},mmode:{value:''},optbox:{},go:{}};
  const ctx=vm.createContext({$:id=>els[id],MI:{info},PW:saved.pw||{},SHARE:{},applyShare(){},
    LS:{get:k=>saved[k]??null,set:(k,v)=>{saved[k]=v}},miLoad(){},renderMi(){},growthInit(){},updCount(){},run(){},refreshTabs(){},drawGraph(){},
    seasonRefresh(){},condChanged(){},setInterval(){},document:{addEventListener(){}},
    AUTO:false,SIMQ:{},REQ:false,window:{Quick:true},QK:{d:{st:{op:{'tab|stage':{bp:80000}}},params:{}}},rkOf:()=>0});
  vm.runInContext(section('function miSelect(','let cur='),ctx);
  vm.runInContext(section('{const gv=LS.get(', '</script>'),ctx);
  vm.runInContext(section('function quickIn(', 'const qBase='),ctx);
  return {els,ctx,quick:()=>vm.runInContext('quickIn({key:"op"},{tab:"tab",name:"stage"})',ctx)};
}
// 추천은 내 정보로만(2026-10-22 개편): 옛 육성·전투력 저장값(grow/pow/pw)은 시작할 때 쓰지 않는다
const tests={
  legacy_power_ignored(){const saved={grow:'1.25',pow:'100000',pw:{luna:25000,gwen:25000}},b=boot(saved);
    assert.notEqual(b.els.grow.value,'manual');assert.equal(b.els.mypow.value,'');assert.equal(b.quick().power,null);},
  myinfo_fixed(){const b=boot({grow:'1.25',pow:'100000'},{units:[]});assert.equal(b.els.grow.value,'myinfo');assert.equal(b.quick().power,null);},
  defaults(){assert.equal(boot({}).els.grow.value,'1');assert.equal(boot({grow:'0.8'}).els.grow.value,'0.8');},
  legacy_reco_auto_ignored(){
    for(const saved of [undefined,false,true]){
      let invalidated=0,rendered=0;
      const ctx=vm.createContext({location:{search:''},SHARE:{},MI:{info:{}},SIMQ:{kick:true},LASTQ:{old:{}},_rt:null,
        LS:{get:k=>{assert.notEqual(k,'reco.auto','must not read the retired preference');return saved}},
        clearTimeout(){},setTimeout(){assert.fail('normal selection must not schedule recommendation')},
        simInvalidate(){invalidated++},run(skip){assert.equal(skip,true);rendered++}});
      vm.runInContext(section('const AUTO=', 'function miGuide('),ctx);
      vm.runInContext('REQ=true;condChanged()',ctx);
      assert.equal(vm.runInContext('!REQ&&RECO.timer===null&&RECO.revision===1&&!SIMQ.kick&&Object.keys(LASTQ).length===0',ctx),true);
      assert.equal(invalidated,1);assert.equal(rendered,1);
    }
  }
};
let failed=0;for(const [name,test] of Object.entries(tests)){try{test();console.log('PASS',name)}catch(e){failed++;console.error('FAIL',name,e.message)}}
if(failed)process.exitCode=1;else console.log('ALL OK',Object.keys(tests).length);
