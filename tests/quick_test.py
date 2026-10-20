# -*- coding: utf-8 -*-
"""빠른 계산 시험: ① Python(battlesim/quick.py) 과 JS(quick.js) 가 같은 입력에 같은 결과를 내는가(node 로 실행)
② 육성이 늘면 결과가 나빠지지 않는가(단조성) ③ 역보정이 걸리면 결과가 좋아지지 않는가 ④ 재료 없는 구원자는 ok=False.

사용: python -X utf8 -I tests/quick_test.py   (node 필요)
일부러 깨뜨려 보기: quick.js 의 1.85 를 1.8 로 바꾸면 ① 이 실패해야 한다."""
import json
import os
import random
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from battlesim import quick   # noqa: E402

FAIL = []


def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (('  ' + detail) if detail and not cond else ''))
    if not cond:
        FAIL.append(name)


def cases(q, n=300, seed=7):
    rnd = random.Random(seed)
    keys = sorted(q['sv'])
    stages = [(ck, sk) for ck in sorted(q['st']) for sk in sorted(q['st'][ck])]
    out = []
    for _ in range(n):
        ck, sk = rnd.choice(stages)
        team = rnd.sample(keys, 4)
        g = rnd.choice([None, 0.5, 0.8, 1.0, 1.3, 2.0])
        out.append(dict(ck=ck, sk=sk, keys=team, growth=g if g else 1.0))
    return out


def py_side(q, pen, cs):
    prm = q.get('params')
    res = []
    for c in cs:
        st = q['st'][c['ck']][c['sk']]
        r = quick.evaluate(c['keys'], st, q['sv'], pen, prm, growth=c['growth'])
        ng = quick.need_growth(c['keys'], st, q['sv'], pen, prm)
        res.append([r.get('ok'), r.get('clear'), r.get('rounds'), round(r.get('left', 0) or 0, 9), ng and round(ng, 9)])
    return res


JS = r"""
const fs=require('fs');const Q=require(process.argv[2]);
const q=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));const pen=JSON.parse(fs.readFileSync(process.argv[4],'utf8')).pen;
const cs=JSON.parse(fs.readFileSync(process.argv[5],'utf8'));const r9=x=>Math.round(x*1e9)/1e9;
const out=cs.map(c=>{const st=q.st[c.ck][c.sk];const r=Q.evaluate(c.keys,st,q.sv,pen,q.params,c.growth);const ng=Q.needGrowth(c.keys,st,q.sv,pen,q.params);
 return [r.ok,r.ok?r.clear:null,r.ok?r.rounds:null,r9(r.left||0),ng==null?null:r9(ng)]});
process.stdout.write(JSON.stringify(out));
"""


def js_side(cs):
    tmp = tempfile.mkdtemp(prefix='quick_test_')
    cf = os.path.join(tmp, 'cases.json')
    jf = os.path.join(tmp, 'run.js')
    json.dump(cs, open(cf, 'w', encoding='utf-8'))
    open(jf, 'w', encoding='utf-8').write(JS)
    p = subprocess.run(['node', jf, os.path.join(ROOT, 'quick.js'), os.path.join(ROOT, 'data', 'quick.json'),
                        os.path.join(ROOT, 'data', 'power_penalty.json'), cf], capture_output=True, text=True, encoding='utf-8')
    for f in (cf, jf):
        os.remove(f)
    os.rmdir(tmp)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def main():
    q, pen = quick.load(ROOT)
    check('계수(params)가 저장돼 있음', bool(q.get('params')))
    cs = cases(q)
    a, b = py_side(q, pen, cs), js_side(cs)
    a = [[x[0], x[1] if x[0] else None, x[2] if x[0] else None, x[3], x[4]] for x in a]
    diff = [i for i in range(len(cs)) if a[i] != b[i]]
    check('Python·JS 같은 결과 (%d건)' % len(cs), not diff, 'diff %d건, 첫 건 %s py=%s js=%s' % (len(diff), diff and cs[diff[0]], diff and a[diff[0]], diff and b[diff[0]]))
    prm = q['params']
    order = {'hard': 0, 'tight': 1, 'safe': 2}
    bad = 0
    bad_pen = 0
    for c in cs[:120]:
        st = q['st'][c['ck']][c['sk']]
        prev = -1
        for g in (0.4, 0.7, 0.9, 1.0, 1.5, 2.5):
            r = quick.evaluate(c['keys'], st, q['sv'], pen, prm, growth=g)
            if not r['ok']:
                break
            v = order[quick.verdict(r)]
            if v < prev:
                bad += 1
                break
            prev = v
        r1 = quick.evaluate(c['keys'], st, q['sv'], pen, prm, growth=0.6)
        r2 = quick.evaluate(c['keys'], st, q['sv'], pen, prm, growth=0.6, use_pen=False)
        if r1['ok'] and order[quick.verdict(r1)] > order[quick.verdict(r2)]:
            bad_pen += 1
    check('육성이 늘면 판정이 나빠지지 않음(단조성)', bad == 0, '%d건 위반' % bad)
    check('역보정이 걸리면 판정이 좋아지지 않음', bad_pen == 0, '%d건 위반' % bad_pen)
    st = next(iter(q['st']['op'].values()))
    check('재료 없는 구원자 -> ok=False', quick.evaluate(['__없음__', 'amora', 'annah', 'bell'], st, q['sv'], pen, prm)['ok'] is False)
    # 재료를 다시 만들어도 맞춘 계수가 남는가(codex 검토 차단 3)
    tmp = tempfile.mkdtemp(prefix='quick_build_')
    dst = os.path.join(tmp, 'quick.json')
    json.dump(dict(params=dict(A=9, B=9, H=0.9), calib=dict(acc=0.5)), open(dst, 'w', encoding='utf-8'))
    p = subprocess.run([sys.executable, '-X', 'utf8', '-I', os.path.join(ROOT, 'tools', 'build_quick_data.py'), dst],
                       capture_output=True, text=True, encoding='utf-8')
    kept = json.load(open(dst, encoding='utf-8')).get('params') if p.returncode == 0 else None
    os.remove(dst)
    os.rmdir(tmp)
    check('재료 다시 만들기가 계수를 보존', kept == dict(A=9, B=9, H=0.9), str(kept))
    print('실패 %d' % len(FAIL) if FAIL else '전부 통과')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
