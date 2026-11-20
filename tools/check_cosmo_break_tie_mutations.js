// 메모리에서만 한 줄씩 바꾸며 AssertionError로 실패했는지 확인함.
const assert=require('node:assert/strict'),{spawnSync}=require('node:child_process');
const mutations=[
 ['기준 점수 제거','cosmo_search.js','metric(b.st,mode)-metric(a.st,mode) || ',''],
 ['반대 점수 제거','cosmo_search.js','other(b.st,mode)-other(a.st,mode) || ',''],
 ['클리어율 제거','cosmo_search.js','(b.st.clear||0)-(a.st.clear||0)','0'],
 ['동점 표시 제거','cosmo_search.js','...(brkTie?{brkTie:true}:{})','...{}'],
 ['기준 점수 동등 검사 제거','cosmo_search.js','metric(c.st,mode)===metric(pick.st,mode) && ',''],
 ['반대 점수 동등 검사 제거','cosmo_search.js',' && other(c.st,mode)===other(pick.st,mode)',''],
 ['후보 누락 무시','cosmo_search.js',' && candidates.length===brks.length',''],
 ['미장착 비교 무시','cosmo_search.js',' && brks.includes(null)',''],
 ['후보 하나도 동점','cosmo_search.js','candidates.length>1','candidates.length>0'],
 ['표 동점 문구 제거','cosmo_search.js','t.brkTie ? "<br>브레이크 스킬: 점수 차이 없음(아무거나 장착 가능)" : ',''],
 ['카드 동점 문구 제거','party_template.html','if(t.brkTie)return','if(false)return'],
 ['직접 편성에 동점 스킬 장착','cosmo_direct.js','!t.brkTie&&t.brk?','t.brk?'],
];
for(const [name,file,from,to] of mutations){
 const script=`const fs=require('node:fs'),read=fs.readFileSync;
 fs.readFileSync=function(f,...args){const s=read.call(this,f,...args);
 if(!String(f).replaceAll('\\\\','/').endsWith('/'+${JSON.stringify(file)}))return s;
 if(typeof s!=='string'||s.split(${JSON.stringify(from)}).length!==2)throw Error('mutation anchor missing');
 return s.replace(${JSON.stringify(from)},${JSON.stringify(to)});};
 require('./tests/cosmo_break_tie_test.js');`;
 const p=spawnSync(process.execPath,['-e',script],{encoding:'utf8',timeout:30000});
 assert(!p.error&&p.status!==0&&p.stderr.includes('AssertionError')&&!p.stderr.includes('mutation anchor missing'),name+' '+p.stdout+p.stderr);
 console.log('PASS mutation rejected: '+name);
}
console.log(`브레이크 변이 통과 ${mutations.length} / 실패 0`);
