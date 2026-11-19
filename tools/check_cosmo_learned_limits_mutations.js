// 로드할 때만 변이한다. 실제 파일을 바꾸거나 실패·시간 초과를 검출로 오인하지 않는다.
const assert=require('node:assert/strict'),{spawnSync}=require('node:child_process');
const mutations=[
 ['학습에 전수 상한 적용','learned ? S.learned.maxScoreCombos : S.maxCombos','S.maxCombos'],
 ['학습 상한 제거','learned ? S.learned.maxScoreCombos : S.maxCombos','learned ? Infinity : S.maxCombos'],
 ['전수 상한 제거','learned ? S.learned.maxScoreCombos : S.maxCombos','learned ? S.learned.maxScoreCombos : Infinity'],
 ['상한 경계 포함','pl.combos > comboCap','pl.combos >= comboCap'],
 ['확대 대신 전수','if(info.fallback && S.maxCombos > 0 && pl.combos > S.maxCombos)','if(false)'],
 ['상한 이하도 확대','if(info.fallback && S.maxCombos > 0 && pl.combos > S.maxCombos)','if(info.fallback)'],
 ['K 확대 제거','K:c.K*factor','K:c.K'],
 ['M 확대 제거','M:c.M*factor','M:c.M'],
 ['감사 확대 제거','A:c.A*factor','A:c.A'],
 ['첫 판 재사용 제거','const missing=jobs.filter(j=>!res1[j.key]?.cosmo);','const missing=jobs;'],
 ['확대 ETA 누계 제거','stageTeams+=[...extraCore,...extraJobs].filter(j=>!res1[j.key]?.cosmo).length;',''],
 ['확대 안내 제거','(st.audit || []).filter(a=>a.expanded)','[].filter(a=>a.expanded)'],
];
for(const [name,from,to] of mutations){
 const script=`const fs=require('node:fs'),Module=require('node:module'),old=Module._extensions['.js'];
 Module._extensions['.js']=(m,f)=>{if(!f.endsWith('cosmo_search.js'))return old(m,f);const s=fs.readFileSync(f,'utf8');
 if(s.split(${JSON.stringify(from)}).length!==2)throw Error('mutation anchor missing');m._compile(s.replace(${JSON.stringify(from)},${JSON.stringify(to)}),f);};
 require('./tests/cosmo_learned_limits_test.js');`;
 const p=spawnSync(process.execPath,['-e',script],{encoding:'utf8',timeout:120000});
 assert(!p.error && p.status!==0 && p.stderr.includes('AssertionError')&&!p.stderr.includes('mutation anchor missing'),name+' '+p.stderr);
 console.log('PASS mutation rejected: '+name);
}
console.log(`변이 통과 ${mutations.length} / 실패 0`);
