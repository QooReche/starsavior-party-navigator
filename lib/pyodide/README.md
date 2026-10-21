# Pyodide 0.26.4 (브라우저 계산 엔진)

브라우저 시뮬(`sim_worker.js`)이 파이썬 전투 엔진을 돌리는 데 쓰는 Pyodide 핵심 파일 5개를 **외부 CDN 대신 이 사이트에서 직접** 내려준다.

- 출처: npm 공식 패키지 `pyodide@0.26.4`(registry.npmjs.org, tarball shasum `e1420722d86d78cb35a4734404eee5b070ca7189`), 파일은 손대지 않았다.
  jsdelivr `pyodide/v0.26.4/full/` 판과도 해시가 같다(2026-10-21 확인).
- 해시 = `SHA256SUMS`. `tests/web_test.py` 가 대조한다 — 파일을 바꾸면 시험이 깨진다.
- 라이선스: Apache-2.0 (https://github.com/pyodide/pyodide/blob/main/LICENSE)
- 판 올리기: 같은 방법으로 5개 파일을 받아 해시 두 출처 대조 → 교체 → `SHA256SUMS` 갱신 → `sim_worker.js` 의 PYODIDE 경로.
