// 큰 작업 목록을 push(...arr) 로 넘기면 함수 인자 한도를 넘어 RangeError 로 탐색 전체가 멈춘다(11/20 최종 리뷰: 대량 동점 → 전수 복귀 31만 작업).
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const C = require('../cosmo_search.js');
const src = fs.readFileSync(path.join(__dirname, '..', 'cosmo_search.js'), 'utf8');
assert.equal((src.match(/\.push\(\.\.\./g) || []).length, 0, 'cosmo_search.js 에 push(...큰 배열) 가 남아 있음 — pushAll 사용');
const big = Array.from({length: 400000}, (_, i) => i);
assert.throws(() => [].push(...big), RangeError, '대조군: 이 크기면 펼친 push 는 실패해야 함');
const out = C.pushAll([1], big);
assert.equal(out.length, 400001); assert.equal(out[400000], 399999);
console.log('PASS cosmo_push_limit: no spread push, pushAll 400k');
