"""Inject into module loading, leaving the working tree intact."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('local A bound stops later A', 'Ca[0].e.score < floor()) continue;', 'Ca[0].e.score < floor()) break;', 'cosmo_triples_test.js'),
    ('B bound loses compatible C', 'b.e.score + ca0 < floor()', 'b.e.score < floor()', 'cosmo_triples_test.js'),
    ('tie boundary pruned', 'base + c.e.score < floor()', 'base + c.e.score <= floor()', 'cosmo_triples_test.js'),
    ('zero remaining false exhaustion', 'attempts.push({limit,', 'if (budget.remaining <= 0) budget.exhausted = true; attempts.push({limit,', 'cosmo_retry_test.js'),
    ('remaining C tail omitted', 'Math.max(tail, nextB, nextA)', 'Math.max(nextB, nextA)', 'cosmo_triples_test.js'),
    ('next B omitted', 'Math.max(tail, nextB, nextA)', 'Math.max(tail, nextA)', 'cosmo_triples_test.js'),
    ('next A omitted', 'Math.max(tail, nextB, nextA)', 'Math.max(tail, nextB)', 'cosmo_triples_test.js'),
    ('ties certified', 'budget.upperBound < triples[n - 1].sum', 'budget.upperBound <= triples[n - 1].sum', 'cosmo_triples_test.js'),
    ('less than N certified', 'triples.length >= n && budget.upperBound < triples[n - 1].sum', 'triples.length > 0 && budget.upperBound < triples[triples.length - 1].sum', 'cosmo_triples_test.js'),
    ('certificate ignored', 'combineLimited: triplesLimited(triples, S.combine.topTriples, budget)', 'combineLimited: budget.exhausted', 'cosmo_retry_test.js'),
]
source = (ROOT / 'cosmo_search.js').read_text(encoding='utf8')
for name, old, new, test in MUTATIONS:
    assert source.count(old) == 1, (name, source.count(old))
    script = """
const fs=require('fs'),Module=require('module'),path=require('path');
const original=Module._extensions['.js'];
Module._extensions['.js']=(m,f)=>{
 if(f===path.resolve('cosmo_search.js'))m._compile(fs.readFileSync(f,'utf8').replace(OLD,NEW),f);
 else original(m,f);
};
require('./tests/'+TEST);
""".replace('OLD', json.dumps(old)).replace('NEW', json.dumps(new)).replace('TEST', json.dumps(test))
    result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True, encoding='utf8', timeout=60)
    assert result.returncode != 0 and 'AssertionError' in result.stderr, (name, result.stdout, result.stderr)
    print('Detected:', name)
print('Detected %d / missed 0' % len(MUTATIONS))
