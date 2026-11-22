"""Inject faults at module load; tracked files are never modified."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    # 빠른 탐색·공통 난수 변이는 스위치 삭제(11/22)로 없음
    ('pool reuse', 'search_executor.js', 'return ws[i] || (ws[i] = makeWorker())', 'return (ws[i] = makeWorker())'),
    ('pool close', 'cosmo_search.js', 'if (workersPool) workersPool.close();', 'if (false) workersPool.close();'),
]
for name, file, old, new in MUTATIONS:
    source = (ROOT / file).read_text(encoding='utf-8')
    assert source.count(old) == 1, name
    script = """
const fs=require('fs'),Module=require('module'),path=require('path');
const original=Module._extensions['.js'];
Module._extensions['.js']=(m,f)=>{
 if(f===path.resolve(FILE))m._compile(fs.readFileSync(f,'utf8').replace(OLD,NEW),f);
 else original(m,f);
};
require('./tests/cosmo_speed_search_test.js');
""".replace('FILE', json.dumps(file)).replace('OLD', json.dumps(old)).replace('NEW', json.dumps(new))
    result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True,
                            encoding='utf-8', timeout=120)
    assert result.returncode != 0 and 'AssertionError' in result.stderr, (name, result.stdout, result.stderr)
    print('detected:', name)
