// Reproducible policy comparison. Native workers always use the current engine.
// Account and result files must remain outside the repository.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),cp=require('node:child_process'),readline=require('node:readline');
const root=path.resolve(__dirname,'..'),P=require('../party_placement.js');
function oldModules(ref){const cache={};function load(name){if(cache[name])return cache[name].exports;
  const m={exports:{}};cache[name]=m;const source=cp.execFileSync('git',['show',ref+':'+name],{cwd:root,encoding:'utf8'});
  const req=n=>['./cosmo_search.js','./guild_search.js','./cosmo_learned.js'].includes(n)?load(n.slice(2)):require(path.join(root,n));
  vm.runInThisContext('(function(module,exports,require){'+source+'\n})',{filename:ref+':'+name})(m,m.exports,req);return m.exports;
}return {C:load('cosmo_search.js'),GS:load('guild_search.js')};}
function transport(GS,progress){const children=new Set(),original=GS.runPhase;let games=0,active;
  function makeWorker(){const child=cp.spawn('python',['-X','utf8','-I',path.join(__dirname,'bench_cosmo_search.py'),'--worker'],{stdio:['pipe','pipe','inherit']});children.add(child);
    const w={postMessage:m=>child.stdin.write(JSON.stringify(m)+'\n'),terminate(){children.delete(child);child.kill();}};
    readline.createInterface({input:child.stdout}).on('line',s=>{try{w.onmessage?.({data:JSON.parse(s)});}catch(e){w.onerror?.(e);}});
    child.on('error',e=>w.onerror?.(e));child.on('exit',code=>{if(children.has(child))w.onerror?.(Error('worker exited '+code));});return w;
  }
  GS.runPhase=o=>{games+=o.jobs.length*o.runs;active=original({...o,workers:2});return active;};
  return {makeWorker,get games(){return games;},close(){active?.cancel();for(const c of children)c.kill();GS.runPhase=original;}};
}
async function main(){const [input,out,variant='rules']=process.argv.slice(2);if(!input||!out)throw Error('myinfo / private output / rules|free|B|A|guild-old|guild-new');
  const dest=path.resolve(out),base=fs.realpathSync(path.dirname(dest));if(base.toLowerCase().startsWith(root.toLowerCase())||dest===path.resolve(input))throw Error('private output must be outside repository and distinct from input');
  const D=JSON.parse(fs.readFileSync(path.join(root,'index.html'),'utf8').match(/const D=(\{[^\n]+\});/)[1]),info=JSON.parse(fs.readFileSync(input,'utf8').replace(/^\uFEFF/,''));
  const guild=variant.startsWith('guild'),profile=require('../myinfo_reco.js').profile(info,D.roster,require('../data/growth.json'),guild?'op':'cosmo');
  const breaks=Object.entries(require('../myinfo_import.js').mapBreak(info)||{}).filter(([n])=>D.cfg.breakSupported.includes(n)).map(([name,level])=>({name,level}));
  const old=['rules','free','guild-old'].includes(variant),mods=old?oldModules('5139b2e'):{C:require('../cosmo_search.js'),GS:require('../guild_search.js')},T=transport(mods.GS),start=performance.now(),phases=[];
  const onPhase=(msg,total)=>{phases.push({msg,total,seconds:(performance.now()-start)/1000});console.error(variant,msg,total);};
  try{let result;
    if(!guild){const G=require('../data/cosmo_raid.json'),S=structuredClone(G.search);
      S.minFront=S.minDealer=variant==='rules'?1:0;S.placement={...S.placement,enabled:variant!=='B'};
      result=await mods.C.search({S,bosses:G.season.bossOrder,results:profile.results,roster:D.roster,level:-1,levelMax:Math.min(...G.bosses.map(b=>b.levels.length)),mode:'top',workers:2,makeWorker:T.makeWorker,
        stage:'코스모 게이트',base:'',breaks,boundaries:Object.fromEntries(G.bosses.map(b=>[b.key,P.boundaries(b.levels)])),sampleSeed:20261119,onPhase});
    }else{const G=require('../data/guild_defense.json'),V=require('../guild_view.js'),GS=mods.GS,tiers=[0,0,0,0],cls=Object.fromEntries(D.roster.map(r=>[r.key,r.cls]));
      if(!old)result=await require('../guild_planner.js').search({S:G.search,G,V,results:profile.results,roster:D.roster,tiers,breaks,workers:2,makeWorker:T.makeWorker,stage:'길드방어전',base:'',onPhase});
      else{const S=JSON.parse(cp.execFileSync('git',['show','5139b2e:data/guild_defense.json'],{cwd:root,encoding:'utf8'})).search;
        S.excluded=require('../data/guild_defense.json').search.notes.filter(n=>['professor-m','waltz-asherah'].includes(n.key)).map(n=>n.key);
        const rows=GS.pool(S,profile.results,D.roster),combos=GS.combos(S,rows),run=async(jobs,runs,seed)=>{onPhase('길드 기존 단계',jobs.length);return GS.runPhase({jobs,runs,seed,workers:2,makeWorker:T.makeWorker,stage:'길드방어전',base:''}).promise;};
        const a=GS.screenJobs(S,G,V,combos,profile.results,cls,tiers),ar=await run(a,S.screen.runs,1);
        const b=GS.screenJobs(S,G,V,GS.pickTop(V,G,a,ar,tiers,S.screen2.keep,S),profile.results,cls,tiers),br=await run(b,S.screen2.runs,3);
        const c=GS.finalJobs(S,G,V,GS.pickFinalists(S,V,G,b,br,tiers),profile.results,cls,tiers),cr=await run(c,S.final.runs,2);
        let ranked=GS.rank(V,G,c,cr,tiers,GS.BREAK_CHECK.teams,S);const d=GS.breakJobs(ranked,breaks,profile.results,cls,tiers);
        if(d.length)ranked=GS.rank(V,G,d,await run(d,GS.BREAK_CHECK.runs,2),tiers,5,S);
        result={rows:ranked,pool:rows.length,combos:combos.length};
      }
    }
    delete result.growthOwned;fs.writeFileSync(dest,JSON.stringify({variant,engine:cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),seconds:(performance.now()-start)/1000,games:T.games,phases,result},null,2));
    console.error('완료',variant);
  }finally{T.close();}
}
module.exports={oldModules,transport};if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
