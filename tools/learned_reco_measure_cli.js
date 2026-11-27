'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawn,spawnSync}=require('node:child_process'),readline=require('node:readline'),crypto=require('node:crypto');
const M=require('./learned_reco_measure.js'),root=path.resolve(__dirname,'..');
const workspace=process.env.STARSAVIOR_WORKSPACE||(path.basename(path.dirname(root))==='_worktrees'?path.dirname(path.dirname(root)):path.dirname(root));
const [collectFile,outDir,python='python',methods='F,A,C',seeds='1,2,3',ids='',workerCount='8']=process.argv.slice(2);
const workers=Number(workerCount);if(!Number.isInteger(workers)||workers<1)throw Error('Invalid worker count');
const input=JSON.parse(fs.readFileSync(collectFile,'utf8').replace(/^\uFEFF/,''));
const D=JSON.parse(fs.readFileSync(path.join(root,'index.html'),'utf8').match(/const D=(\{[^\n]+\});/)[1]);
const S=require('../data/cosmo_raid.json').search;
const platform=spawnSync(python,['-c','import sys,json; print(json.dumps({"version":sys.version,"hash_width":sys.hash_info.width}))'],{encoding:'utf8'});
if(platform.status!==0)throw Error(platform.stderr);
const provenance={python:JSON.parse(platform.stdout),head:spawnSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).stdout.trim(),
 inputHash:crypto.createHash('sha256').update(fs.readFileSync(collectFile)).digest('hex'),
 driverHash:crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,'learned_reco_measure.js'))).digest('hex')};
const children=new Set();
function worker(){const child=spawn(python,['-X','utf8','-I',path.join(__dirname,'learned_reco_measure.py'),'worker'],{cwd:root,stdio:['pipe','pipe','inherit']});children.add(child);
 const w={postMessage:m=>child.stdin.write(JSON.stringify(m)+'\n'),terminate:()=>{children.delete(child);child.kill();}};
 readline.createInterface({input:child.stdout}).on('line',line=>{try{w.onmessage?.({data:JSON.parse(line)});}catch(e){w.onerror?.(e);}});
 child.on('error',e=>w.onerror?.(e));child.on('exit',code=>{if(children.has(child))w.onerror?.(Error('worker exited '+code));});return w;}
async function main(){
 fs.mkdirSync(outDir,{recursive:true});
 for(const row of input){if(ids&&!ids.split(',').includes(row.id))continue;
   const relative=path.relative(path.join(workspace,'_private/role-private/learned_reco'),path.resolve(outDir));
   if(row.private&&(relative==='..'||relative.startsWith('..'+path.sep)||path.isAbsolute(relative)))throw Error('Private output directory required');
   for(const seed of seeds.split(',').map(Number))for(const method of methods.split(',')){
     const file=path.join(outDir,`${row.id}_${seed}_${method}_native.json`);if(fs.existsSync(file))continue;
     const pool=M.workerPool(worker,workers,row.c.key+'/'+row.st.tab+'/'+row.st.name);
     try{const result=await M.run(row,D,S,method,seed,pool.evaluate,(phase,n)=>console.error(`${row.id} ${seed} ${method} ${phase} ${n} games`));
       result.backend='native';result.workers=workers;result.provenance=provenance;result.nodePeakMB=process.resourceUsage().maxRSS/1024;
       fs.writeFileSync(file+'.tmp',JSON.stringify(result));fs.renameSync(file+'.tmp',file);
     }finally{pool.close();}
   }
 }
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>{for(const c of children)c.kill();});
