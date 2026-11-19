"""소스를 디스크에 바꾸지 않고 로드할 때 변이 주입. 새 회귀 시험이 실제 결함을 잡는지 확인."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('확대 제거', 'of retry.limits.entries()', 'of retry.limits.slice(0, 1).entries()'),
    ('기존 job 재요청', '!evaluated.has(jobKey(b, e.keys, level))', 'true'),
    ('반감 후보 복귀 제거', '(attempt ? allJobs : jobsK)', 'jobsK'),
    ('구원자 이름 제거', 'const who = keys.join("·")', 'const who = ""'),
    ('후보 상한 제거', 'Math.min(L, cfg.maxCandidatesPerBoss, Math.floor', 'Math.min(L, Infinity, Math.floor'),
    ('판 수 상한 제거', 'Math.floor(cfg.maxRerankGames / (BOSSES * S.rerank.runs))', 'Infinity'),
    ('조합 검사 상한 제거', 'maxChecks: cfg.maxTripleChecks', 'maxChecks: Infinity'),
    ('ETA 재사용 누계 제거', 'msg, 2, carry)', 'msg, 2, 0)'),
    ('결과 누락 무시', 'extra.some(j => !resB[j.key] || !resB[j.key].cosmo)', 'false'),
    ('그웬 오류 분류 제거', '{gwenCause: "empty", attempts}', '{gwenCause: "other", attempts}'),
    ('빠른 선별 후보 복귀 제거', 'if (attempt) for (const j of source)', 'if (false) for (const j of source)'),
    ('부분 성공 제한 안내 제거', '(st.combineLimited ?', '(false ?'),
]
source = (ROOT / 'cosmo_search.js').read_text(encoding='utf-8')
for name, old, new in MUTATIONS:
    assert source.count(old) == 1, name
    script = """
const fs=require('fs'),Module=require('module'),path=require('path');
const original=Module._extensions['.js'];
Module._extensions['.js']=(m,f)=>{
 if(f===path.resolve('cosmo_search.js'))m._compile(fs.readFileSync(f,'utf8').replace(OLD,NEW),f);
 else original(m,f);
};
require('./tests/cosmo_retry_test.js');
""".replace('OLD', json.dumps(old)).replace('NEW', json.dumps(new))
    result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert result.returncode != 0 and 'AssertionError' in result.stderr, (name, result.stdout, result.stderr)
    print('검출:', name)
print('변이 검출 %d / 놓침 0' % len(MUTATIONS))
