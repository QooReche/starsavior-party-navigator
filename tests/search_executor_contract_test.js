const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),sources={};
const skip=new Set(['.git','lib','vendor','tests','tools','_tmp','node_modules','assets','data','sim','battlesim','docs','local']);
function scan(dir=''){
 for(const e of fs.readdirSync(path.join(root,dir),{withFileTypes:true})){
  if(e.isDirectory()){if(!skip.has(e.name)&&!e.name.startsWith('.'))scan(path.join(dir,e.name));}
  else if(/\.(js|html)$/.test(e.name)&&e.name!=='index.html')sources[path.join(dir,e.name)]=fs.readFileSync(path.join(root,dir,e.name),'utf8');
 }
}
scan();
function contract(files){
 const constructors=/new\s+(?:[\w$]+\s*\.\s*)*Worker\s*\(/g;
 for(const [file,src] of Object.entries(files))if(file!=='search_executor.js')assert(!constructors.test(src),file+' creates workers outside executor');
 assert.equal([...files['search_executor.js'].matchAll(constructors)].length,1,'one physical worker factory');
 const page=files['party_template.html'];
 const executor=page.indexOf('src="search_executor.js"'),guild=page.indexOf('src="guild_search.js"');
 assert(executor>=0&&guild>=0&&executor<guild,'executor must load before consumers');
 for(const [name,method] of [['scrPool','reserve'],['simDispatch','dispatch'],['simWatch','watch'],['simPoolDrop','drop']]){
  assert(new RegExp('function '+name+'\\([^]*?\\{return SIM_EXEC\\.'+method+'\\(').test(page),name+' bypasses executor');
 }
 assert.match(files['guild_search.js'],/Executor\.runPhase\(/);assert.match(files['guild_search.js'],/Executor\.workerPool\(/);
 assert.match(files['cosmo_search.js'],/Executor\.etaNew\(/);assert.match(files['growth_ui.js'],/SearchExecutor\.timedWorker\(/);
 assert(!/\bdocument\b|\bSIMQ\b|\bGuildSearch\b/.test(files['search_executor.js']),'core depends on DOM/content');
 assert.match(files['search_executor.js'],/const resources=workerPool\(\(\)=>/,'shared pool must use common resource owner');
 assert.match(files['search_executor.js'],/const resources=pool\|\|workerPool\(makeWorker\)/,'phase pool must use common resource owner');
}
contract(sources);
for(const file of ['party_template.html','guild_search.js','recommend_runtime.js','direct_run.js','cosmo_direct_page.js','future_search.js']){
 assert.throws(()=>contract({...sources,[file]:(sources[file]||'')+"\nnew Worker('sim_worker.js');"}),assert.AssertionError,file);
}
assert.throws(()=>contract({...sources,'party_template.html':sources['party_template.html'].replace('return SIM_EXEC.dispatch(','return localDispatch(')}),assert.AssertionError);
assert.throws(()=>contract({...sources,'party_template.html':sources['party_template.html'].replace('<script src="search_executor.js"></script>','')}),assert.AssertionError);
assert.throws(()=>contract({...sources,'search_executor.js':sources['search_executor.js'].replace('const resources=pool||workerPool(makeWorker)','const resources=pool||localPool(makeWorker)')}),assert.AssertionError);
console.log('PASS executor-only construction/delegation/loading/resource ownership; 9 bypass mutations rejected');
