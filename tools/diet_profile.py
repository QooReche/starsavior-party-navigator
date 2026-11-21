# -*- coding: utf-8 -*-
"""엔진 다이어트 0단계 실측(docs/engine_diet_1122.md): run_auto 1판·8판·100판 시간 분해와 진단·기록 비용 비율.

측정 방법
  wall    : 프로파일러 없이 web.run_auto(화면 옵션 + raw_runs) 시간. 같은 프로세스에서 데우기 1회 뒤 n=1 x7·n=8 x3·n=100 x2 의 최솟값.
  profile : cProfile 로 n=8·n=100 각 1회 — support_report·assumptions_used(호출당), Battle.lines_of·Battle.log(판당) 의 비율.
            cProfile 은 함수 호출이 잦은 코드를 부풀리므로 비율은 «상한 쪽 근사»로만 본다.
  variant : mc.py 를 AST 로 바꾼 임시 사본(local/diet_variants/, 저장소에 안 넣음)으로 같은 wall 측정 —
            noguard = 원본 그대로 복사(복사본 자체의 차이 대조군), logguard = `self.log(...)` 문장을 `if self.timeline is not None:` 아래로,
            nohits = `self.rule_hits[...] += ...` 문장 삭제, both = 둘 다. 결과 해시가 기준선(tools/diet_baseline.py)과 같은지도 본다.
  mcreads : self.mc 를 읽기 횟수를 세는 dict 로 바꿔 n=8 에서 판당 읽기 수 x 읽기 1회 단가(timeit).

  python -X utf8 -I tools/diet_profile.py                 # 전부(약 5~10분), 결과 JSON 은 local/diet_profile.json
  python -X utf8 -I tools/diet_profile.py --worker DIR    # (내부) DIR/battlesim 으로 wall 만 재서 JSON 출력
"""
import argparse
import ast
import cProfile
import json
import os
import pstats
import shutil
import subprocess
import sys
import time
import timeit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = [
    ('op', 'op/NOA 상업지구/SECTOR 1-3', {}),
    ('clo_moon100', 'clo/달 회랑/FLOOR 100', {}),
    ('clo_sun250', 'clo/태양 회랑/FLOOR 250', {}),
    ('cosmo_gille1', 'cosmo/길레/길레 1단계', {}),
    ('cosmo_raid_bask3', 'x', {'cosmo_raid': {'boss': 'baskerville', 'step': 3, 'level': 0}}),
    ('guild_l1', 'x', {'guild': {'level': 1, 'sets': [0, 0, 0, 0], 'support': 'fire'}}),
]
PARTY = {'units': ['fei', 'professor-m', 'emily', 'wedding-carmen'], 'leader': 0}
OPT = {'build': 'standard', 'rules_override': {'power_penalty': 'model'}, 'raw_runs': True}
REPS = {1: 7, 8: 3, 100: 2}


def _extra(e):
    return json.dumps(dict(OPT, **e))


def wall(web):
    out = {}
    for name, stage, e in CASES:
        web.run_auto(stage, PARTY, 1, 99, _extra(e))      # 데우기(자료 읽기·캐시)
        row = {}
        for n, reps in REPS.items():
            best = None
            for _ in range(reps):
                t = time.perf_counter()
                web.run_auto(stage, PARTY, n, 1, _extra(e))
                dt = time.perf_counter() - t
                best = dt if best is None else min(best, dt)
            row[n] = round(best * 1000, 2)
        out[name] = row
    return out


def profile(web):
    out = {}
    want = {'support_report': ('mc.py', 'support_report'), 'assumptions_used': ('api.py', 'assumptions_used'),
            'lines_of': ('mc.py', 'lines_of'), 'log': ('mc.py', 'log'), 'Battle.run': ('mc.py', 'run'),
            'Battle.__init__': ('mc.py', '__init__'), 'norm_encounter': ('api.py', '_norm_encounter'),
            'build_defs': ('api.py', '_build_party'), 'dumps': ('__init__.py', 'dumps')}
    for name, stage, e in CASES:
        web.run_auto(stage, PARTY, 1, 99, _extra(e))
        row = {}
        for n in (8, 100):
            pr = cProfile.Profile()
            pr.enable()
            web.run_auto(stage, PARTY, n, 1, _extra(e))
            pr.disable()
            st = pstats.Stats(pr).stats
            total = sum(v[2] for v in st.values())     # tottime 합 = 프로파일 총시간
            got = {}
            for label, (fname, func) in want.items():
                hit = [(k, v) for k, v in st.items() if k[0].replace('\\', '/').endswith('/' + fname) and k[2] == func]
                if label == 'Battle.__init__':
                    hit = [(k, v) for k, v in hit if 'battlesim/mc.py' in k[0].replace('\\', '/')]
                ncalls = sum(v[1] for _, v in hit)
                tot = sum(v[2] for _, v in hit)
                cum = max([v[3] for _, v in hit] or [0])
                got[label] = dict(ncalls=ncalls, tottime_ms=round(tot * 1000, 2), cumtime_ms=round(cum * 1000, 2))
            row[n] = dict(total_ms=round(total * 1000, 2), funcs=got)
        out[name] = row
    return out


class _CountDict(dict):
    n = 0

    def __getitem__(self, k):
        _CountDict.n += 1
        return dict.__getitem__(self, k)


def mcreads(web):
    from battlesim import mc as M
    orig = M.Battle.__init__

    def init(self, *a, **k):
        orig(self, *a, **k)
        self.mc = _CountDict(self.mc)
    out = {}
    M.Battle.__init__ = init
    try:
        for name, stage, e in CASES:
            _CountDict.n = 0
            web.run_auto(stage, PARTY, 8, 1, _extra(e))
            out[name] = round(_CountDict.n / 8)
    finally:
        M.Battle.__init__ = orig

    class S:
        def __init__(self):
            self.mc = {'a%d' % i: i for i in range(240)}
            self.mc['skill_end_timing'] = 'x'
    s = S()
    per = min(timeit.repeat("s.mc['skill_end_timing']", globals={'s': s}, number=2_000_000, repeat=5)) / 2_000_000
    base = min(timeit.repeat("s", globals={'s': s}, number=2_000_000, repeat=5)) / 2_000_000
    hits = defaultdict_unit()
    return dict(reads_per_run=out, read_ns=round((per - base) * 1e9, 1), rule_hit_ns=hits)


def defaultdict_unit():
    from collections import defaultdict

    class S:
        pass
    s = S()
    s.rule_hits = defaultdict(int)
    s.rule_hits['x'] = 0
    per = min(timeit.repeat("s.rule_hits['x'] += 1", globals={'s': s}, number=2_000_000, repeat=5)) / 2_000_000
    base = min(timeit.repeat("s", globals={'s': s}, number=2_000_000, repeat=5)) / 2_000_000
    return round((per - base) * 1e9, 1)


class _Diet(ast.NodeTransformer):
    def __init__(self, guard_log, drop_hits):
        self.guard_log, self.drop_hits = guard_log, drop_hits
        self.n_log = self.n_hits = 0

    def visit_AugAssign(self, node):
        t = node.target
        if self.drop_hits and isinstance(t, ast.Subscript) and isinstance(t.value, ast.Attribute) and t.value.attr == 'rule_hits':
            self.n_hits += 1
            return ast.Pass()
        return node

    def visit_Expr(self, node):
        c = node.value
        if (self.guard_log and isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == 'log'
                and isinstance(c.func.value, ast.Name) and c.func.value.id == 'self'):
            self.n_log += 1
            test = ast.Compare(left=ast.Attribute(value=ast.Name('self', ast.Load()), attr='timeline', ctx=ast.Load()),
                               ops=[ast.IsNot()], comparators=[ast.Constant(None)])
            return ast.If(test=test, body=[node], orelse=[])
        return node


def make_variant(name, guard_log, drop_hits):
    dst = os.path.join(ROOT, 'local', 'diet_variants', name)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(os.path.join(ROOT, 'battlesim'), os.path.join(dst, 'battlesim'), ignore=shutil.ignore_patterns('__pycache__'))
    src = os.path.join(dst, 'battlesim', 'mc.py')
    tr = _Diet(guard_log, drop_hits)
    if guard_log or drop_hits:
        tree = tr.visit(ast.parse(open(src, encoding='utf-8').read()))
        ast.fix_missing_locations(tree)
        with open(src, 'w', encoding='utf-8') as f:
            f.write('# -*- coding: utf-8 -*-\n' + ast.unparse(tree) + '\n')
    return dst, dict(log_sites=tr.n_log, hit_sites=tr.n_hits)


def run_worker(engine):
    env = dict(os.environ, PN_SRC=ROOT)
    r = subprocess.run([sys.executable, '-X', 'utf8', '-I', os.path.abspath(__file__), '--worker', engine],
                       capture_output=True, text=True, encoding='utf-8', env=env, cwd=ROOT)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def baseline_ok(engine):
    env = dict(os.environ, PN_SRC=ROOT)
    r = subprocess.run([sys.executable, '-X', 'utf8', '-I', os.path.join(ROOT, 'tools', 'diet_baseline.py'), '--engine', engine],
                       capture_output=True, text=True, encoding='utf-8', env=env, cwd=ROOT)
    return r.returncode == 0, r.stdout.strip()[-200:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-variants', action='store_true')
    ap.add_argument('--worker', help=argparse.SUPPRESS)
    ap.add_argument('--rounds', type=int, default=2, help='변형 wall 측정을 번갈아 몇 바퀴(최솟값 사용)')
    a = ap.parse_args()
    if a.worker:
        sys.path.insert(0, a.worker)
        from battlesim import web
        print(json.dumps(wall(web)))
        return
    sys.path.insert(0, ROOT)
    from battlesim import web
    res = dict(python=sys.version.split()[0], party=PARTY['units'], opt=OPT)
    res['wall'] = wall(web)
    print('wall', json.dumps(res['wall']), flush=True)
    res['profile'] = profile(web)
    print('profile done', flush=True)
    res['mcreads'] = mcreads(web)
    print('mcreads', json.dumps(res['mcreads']), flush=True)
    if not a.skip_variants:
        vs = {}
        for name, g, d in (('noguard', False, False), ('logguard', True, False), ('nohits', False, True), ('both', True, True)):
            dst, info = make_variant(name, g, d)
            vs[name] = dict(info, dir=dst, wall=None)
        for _ in range(a.rounds):           # 번갈아 재서 기계 상태 흔들림을 나눈다
            for name, v in vs.items():
                w = run_worker(v['dir'])
                v['wall'] = w if v['wall'] is None else {c: {n: min(v['wall'][c][n], w[c][n]) for n in w[c]} for c in w}
                print(name, json.dumps(w), flush=True)
        vs['both']['baseline'] = baseline_ok(vs['both']['dir'])
        print('both baseline', vs['both']['baseline'], flush=True)
        res['variants'] = {k: {kk: vv for kk, vv in v.items() if kk != 'dir'} for k, v in vs.items()}
    os.makedirs(os.path.join(ROOT, 'local'), exist_ok=True)
    with open(os.path.join(ROOT, 'local', 'diet_profile.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print('저장 local/diet_profile.json')


if __name__ == '__main__':
    main()
