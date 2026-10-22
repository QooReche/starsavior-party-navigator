// Exercise actual page startup and input handlers without a browser.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const section=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
function boot(saved,info=null){
  const option={disabled:true},grow={value:'1',options:['myinfo','1','0.8','1.25','manual'].map(value=>({value})),querySelector:()=>option};
  const els={grow,mypow:{value:''},rk:{value:'0',options:[]},mmode:{value:''},optbox:{},go:{}};
  const ctx=vm.createContext({$:id=>els[id],MI:{info},PW:saved.pw||{},
    LS:{get:k=>saved[k]??null,set:(k,v)=>{saved[k]=v}},miLoad(){},renderMi(){},updCount(){},run(){},refreshTabs(){},drawGraph(){},
    window:{Quick:true},QK:{d:{st:{op:{'tab|stage':{bp:80000}}},params:{}}},rkOf:()=>0});
  vm.runInContext(section('function miSelect(','let cur='),ctx);
  vm.runInContext(section('{const gv=LS.get(', '</script>'),ctx);
  vm.runInContext(section('function quickIn(', 'const qBase='),ctx);
  return {els,ctx,quick:()=>vm.runInContext('quickIn({key:"op"},{tab:"tab",name:"stage"})',ctx)};
}
const tests={
  legacy_total(){const saved={grow:'1.25',pow:'100000'},b=boot(saved);
    assert.equal(b.els.grow.value,'manual');assert.equal(b.els.mypow.value,'100000');assert.equal(b.quick().power,100000);
    assert.equal(boot(saved).quick().power,100000);},
  legacy_members(){const saved={grow:'1.25',pw:{luna:25000,gwen:25000,fei:25000,amora:25000}},b=boot(saved);
    assert.equal(b.els.grow.value,'manual');assert.equal(b.quick().growth,1.25);
    assert.deepEqual(b.ctx.PW,saved.pw);assert.equal(b.quick().power,null);},
  modes(){const saved={grow:'1.25',pow:'100000'},b=boot(saved);
    b.els.grow.value='0.8';vm.runInContext('miSelect()',b.ctx);
    const again=boot(saved);assert.equal(again.els.grow.value,'0.8');assert.equal(again.quick().power,null);
    vm.runInContext('manualSelect()',again.ctx);assert.equal(boot(saved).quick().power,100000);
    assert.equal(boot(saved).quick().growth,0.8);},
  defaults(){assert.equal(boot({grow:'1.25'}).els.grow.value,'1.25');assert.equal(boot({}).els.grow.value,'1');
    assert.equal(boot({grow:'1.25',pow:'100000'},{units:[]}).els.grow.value,'myinfo');}
};
let failed=0;for(const [name,test] of Object.entries(tests)){try{test();console.log('PASS',name)}catch(e){failed++;console.error('FAIL',name,e.message)}}
if(failed)process.exitCode=1;else console.log('ALL OK',Object.keys(tests).length);
