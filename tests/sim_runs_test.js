const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
const section=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
const workers=[],t={keys:['a','b','c','d'],combo:[]},st={tab:'1',name:'1-1'};
const ctx=vm.createContext({console,Set,MODE:'auto',MI:{pending:null},miMode:()=>false,
 SIMQ:{n:100,seed:1,busy:null,res:{},LOAD_MS:100,RUN_MS:100},LASTQ:{1:{rows:[t]}},cur:[st],
 contents:[{key:'op'}],$:()=>({value:'0'}),rkOf:()=>0,simParty:t=>({units:t.keys}),teamBreak:()=>null,
 ckey:()=>t.keys.join(','),simMain:r=>r,simCls:()=>'',esc:String,simOpt:()=>({}),
 document:{querySelector:()=>null},location:{href:'https://test/index.html'},setTimeout:()=>1,clearTimeout(){},run(){},simStop(){},
 Worker:class{constructor(){workers.push(this)}postMessage(req){this.req=req}terminate(){this.stopped=true}}});
vm.runInContext(section('const simSigB=','// 표시 상태는'),ctx);
vm.runInContext(section('function simCell(','function simBar('),ctx);
vm.runInContext(section('function simStart(','document.querySelectorAll(\'input[name="runs"]\')'),ctx);
const ev=s=>vm.runInContext(s,ctx);ctx.t=t;ctx.st=st;
const sig100=ev('simSig(st,t)');ctx.SIMQ.n=300;const sig300=ev('simSig(st,t)');
assert.notEqual(sig100,sig300);
ev('simStart(1)');assert.equal(workers[0].req.n_runs,300);
ctx.SIMQ.busy=null;ctx.SIMQ.n=100;
for(const rate of [0,0.349,0.35,0.5,0.65,0.651,1]){
 ctx.SIMQ.res[sig100]={n:100,clear:rate,ci:[0,1]};
 assert.equal(ev('simCell(1,t,st)').includes('data-refine'),rate>=0.35&&rate<=0.65);
}
ctx.SIMQ.res[sig100]={n:100,clear:0.5,ci:[0,1]};
ev('simRefine(1,"a,b,c,d")');const w=workers.at(-1),req=w.req;
assert.equal(req.n_runs,300);assert.equal(req.teams.length,1);
assert.equal(ev('simSig(st,t)'),sig100); // Until success, cancellation retains the 100 result.
w.onmessage({data:{type:'team',id:req.id,key:req.teams[0].key,result:{n:300,clear:0.5,ci:[0.4,0.6]}}});
w.onmessage({data:{type:'done',id:req.id}});
assert.equal(ev('simSig(st,t)'),sig300);
assert.equal(ctx.SIMQ.res[sig100].n,100);assert.equal(ctx.SIMQ.res[sig300].n,300);
assert(!ev('simCell(1,t,st)').includes('data-refine'));
ctx.SIMQ.refined.clear();assert.equal(ev('simSig(st,t)'),sig100);
console.log('PASS 100/300 requests/cache, inclusive boundary, one-team refinement, success-only promotion');
