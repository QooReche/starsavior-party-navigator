// Exercise actual page startup and input handlers without a browser.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const section=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
function boot(saved,info=null){
  const option={disabled:true},grow={value:'1',options:['myinfo','1','0.8','1.25','manual'].map(value=>({value})),querySelector:()=>option};
  const els={grow,mypow:{value:''},rk:{value:'0',options:[]},mmode:{value:''},optbox:{},go:{}};
  const ctx=vm.createContext({$:id=>els[id],MI:{info},PW:saved.pw||{},SHARE:{},applyShare(){},
    LS:{get:k=>saved[k]??null,set:(k,v)=>{saved[k]=v}},miLoad(){},renderMi(){},updCount(){},run(){},refreshTabs(){},drawGraph(){},
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
  defaults(){assert.equal(boot({}).els.grow.value,'1');assert.equal(boot({grow:'0.8'}).els.grow.value,'0.8');}
};
let failed=0;for(const [name,test] of Object.entries(tests)){try{test();console.log('PASS',name)}catch(e){failed++;console.error('FAIL',name,e.message)}}
if(failed)process.exitCode=1;else console.log('ALL OK',Object.keys(tests).length);
