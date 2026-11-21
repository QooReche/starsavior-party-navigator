// JS 시험 공용 도우미: 화면 소스 읽기·구간 자르기·변이한 모듈 올리기.
// 화면 파일(party_template.html 등)을 문자열로 잘라 쓰는 시험은 여기 cut·line 을 쓴다 — 자르는 표지가 바뀌면 이 함수의 실패 문구로 바로 보인다.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{createRequire}=require('node:module');
const ROOT=path.resolve(__dirname,'..','..');
const rootRequire=createRequire(path.join(ROOT,'package.json'));
// 저장소 뿌리 기준 파일(확장자 포함)을 LF 로 읽는다
const readSrc=name=>fs.readFileSync(path.join(ROOT,name),'utf8').replace(/\r\n/g,'\n');
// s 에서 a 로 시작해 (a 뒤) 처음 나오는 b 앞까지
const cut=(s,a,b)=>{const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i,'구간 없음: '+a);return s.slice(i,j)};
// start 로 시작하는 줄 하나
const line=(s,start)=>{const m=s.match(new RegExp('^'+start.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'.*$','m'));assert(m,'줄 없음: '+start);return m[0]};
// CommonJS 모듈 소스(변이본 포함)를 새 문맥에서 올려 module.exports 를 돌려준다. 모듈 안의 require('./x') 는 저장소 뿌리 기준.
function loadModule(code,extra){const ctx={module:{exports:{}},require:rootRequire,...extra};vm.runInNewContext(code,ctx);return ctx.module.exports}
module.exports={ROOT,readSrc,cut,line,loadModule};
