// 내 정보 불러오기(myinfo_import.js) 시험. node tests/myinfo_import_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const root=path.resolve(__dirname,'..');
const M=require(path.join(root,'myinfo_import.js'));
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
// index.html 의 D(데이터)에서 로스터만 꺼낸다
const m=/const D=(\{[\s\S]*?\});\s*\n/.exec(html);
let roster;
try{roster=JSON.parse(m[1]).roster}catch(e){roster=null}
assert.ok(roster&&roster.length>=50,'로스터를 읽지 못했습니다(index.html 을 build_party_html.py 로 다시 만든 뒤 실행)');
assert.ok(roster.every(s=>'uid' in s),'로스터에 uid 가 없습니다');
const withUid=roster.filter(s=>Number.isInteger(s.uid));
assert.ok(withUid.length>=roster.length-1,'uid 연결이 너무 적습니다: '+withUid.length+'/'+roster.length);
assert.equal(new Set(withUid.map(s=>s.uid)).size,withUid.length,'uid 중복');

// 서랍의 한 줄 명령 안내: 공개 도구 저장소 주소를 가리켜야 하고, 복사 버튼·안내가 있어야 한다
const cmd=/<code id="mi-cmd"[^>]*>([^<]+)<\/code>/.exec(html);
assert.ok(cmd,'한 줄 명령(mi-cmd)이 없습니다');
assert.ok(cmd[1].includes('raw.githubusercontent.com/QooReche/starsavior-myinfo/main/myinfo.ps1'),'명령의 도구 주소');
assert.ok(cmd[1].includes('-OutFile $f')&&cmd[1].includes('-File $f'),'명령 형식');
assert.ok(html.includes('id="mi-copy"')&&html.includes('https://github.com/QooReche/starsavior-myinfo'),'복사 버튼/도구 저장소 링크');

// 가짜 내 정보(실제 형식)
const info={format:'ss-myinfo-v1',game_build:'x',exported_at:'2026-10-22T00:00:00+09:00',star_link_level:343,
 tactics:{facility_level:5,common_level:111,groups:{}},
 units:[{id:1040,star:3,sigil:2,resonance:10,skills:{basic:7,special:7,ultimate:7,passive:4},favor:30,equip:[]},
        {id:1055,star:3,sigil:0,resonance:10,skills:{basic:7,special:10,ultimate:8,passive:4},favor:50,equip:[{}]},
        {id:999999,star:1,sigil:0,resonance:0,skills:{basic:1,special:1,ultimate:1,passive:1},favor:1,equip:[]}]};
assert.equal(M.validate(info),'');
assert.ok(M.validate({format:'other',units:[{id:1}]}).includes('내정보.json'));
assert.ok(M.validate({format:'ss-myinfo-v1',units:[]}).includes('비어'));
assert.ok(M.validate(null));
const r=M.mapOwned(info,roster);
const keyOf=uid=>(roster.find(s=>s.uid===uid)||{}).key;
assert.deepEqual(r.keys.sort(),[keyOf(1040),keyOf(1055)].sort());
assert.deepEqual(r.unknown,[999999]);

// 주소 해시 왕복(gzip + base64url)
(async()=>{
  const json=JSON.stringify(info);
  const b64=zlib.gzipSync(Buffer.from(json,'utf8')).toString('base64').replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  const got=await M.fromHash('#myinfo='+b64);
  assert.deepEqual(got,info);
  assert.equal(await M.fromHash('#other=1'),null);
  assert.equal(await M.fromHash(''),null);
  // 보유 브레이크 스킬: 없으면 null(직접 고르기), 있으면 이름별 레벨, 잘못된 값은 거부
  const base={format:M.FORMAT,star_link_level:1,units:[{id:1040,star:3,sigil:0,resonance:0,favor:1}]};
  assert.equal(M.mapBreak(base),null);
  const bs={...base,break_skills:[{id:101,level:1},{id:103,level:5},{id:105,level:8},{id:999,level:2}]};
  assert.equal(M.validate(bs),'');
  assert.deepEqual(M.mapBreak(bs),{'특이점 관측':1,'큐브 과부하':5,'차원 강습':8});
  assert.notEqual(M.validate({...base,break_skills:[{id:101,level:11}]}),'');
  assert.notEqual(M.validate({...base,break_skills:[{id:101}]}),'');
  // 실제로 내보낸 파일이 있으면 그것도 확인(개인 데이터라 저장소에는 없음)
  const real=process.env.MYINFO_REAL;
  if(real&&fs.existsSync(real)){
    const o=JSON.parse(fs.readFileSync(real,'utf8'));
    assert.equal(M.validate(o),'');
    const rr=M.mapOwned(o,roster);
    console.log('real file:',o.units.length,'units; mapped',rr.keys.length,'unknown',rr.unknown.length);
    assert.ok(rr.keys.length>=o.units.length-3);
  }
  console.log('myinfo_import_test OK (roster',roster.length,', uid',withUid.length,')');
})().catch(e=>{console.error(e);process.exit(1)});
