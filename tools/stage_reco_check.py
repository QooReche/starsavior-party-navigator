"""작전·회랑 일반 추천(사이트 실제 경로)이 공략 사례 편성을 놓치는지 확인.

collect: Playwright 로 index.html 을 내 정보(비공개 파일)와 함께 열고, 사례 스테이지마다 화면의 실제 함수
  (recoCandidates → partyPool(24명) → rankAll → quickRank(빠른 계산, 내 정보 전투력) → scrPick(예선 후보) → simParty)를
  그대로 불러 후보 풀·순위·예선 후보와 각 팀의 시뮬 명세(화면이 작업자에 보내는 party·options 그대로)를 뽑음.
  시뮬은 돌리지 않음(자동 실행 끔). 진단용으로 «풀 없이 보유 전원 조합»의 빠른 계산 순위도 같은 함수로 잼.
eval: 네이티브 엔진(battlesim.web.run_auto = 작업자와 같은 함수)으로
  ① 화면 예선을 재현(후보 전부 8판, 상위 20팀 32판, 시드 1, 순위 scrCmp) — 사례 팀을 후보에 넣었다면 몇 위인지도 봄
  ② 예선 상위·사례 팀을 같은 시드(20261122)·400판으로 재평가하고 진행도 상위 20%·클리어율 차의 부트스트랩 95% 구간.
결과(계정 수치)는 --out(기본 E:/AI_mk2/role-private/casebook_myinfo/site_reco)에만 씀.

  E:/AI_mk2/venv-pw/Scripts/python.exe -X utf8 tools/stage_reco_check.py collect --myinfo PATH
  python -X utf8 -I tools/stage_reco_check.py eval [--workers 4]
"""
import argparse
import json
import math
import os
import random
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = Path('E:/AI_mk2/role-private/casebook_myinfo/site_reco')
SEED = 20261122
TOP_Q = 0.2
CASES = [   # tools/casebook_search_check.py STAGE_CASES 와 같음
    dict(id='04', content='clo', tab='성간 회랑', name='FLOOR 580', keys=['asherah-order-striker', 'gille', 'amora', 'wedding-carmen']),
    dict(id='05', content='clo', tab='성간 회랑', name='FLOOR 590', keys=['ceres-sun-supporter', 'asherah-order-striker', 'wedding-carmen', 'amora']),
    dict(id='09', content='op', tab='얼어붙은 바위 산', name='SECTOR 44-6', keys=['wedding-carmen', 'ceres-sun-supporter', 'amora', 'professor-m']),
]

# 화면 안에서 도는 수집 함수. 화면 전역(recoCandidates·partyPool·quickRank·scrPick·simParty …)을 그대로 씀
COLLECT_JS = r"""
(caseKeys) => {
 const c=contents[$("content").value],st=cur[$("stage").value];
 const own=new Set([...document.querySelectorAll("#own input:checked")].map(x=>x.dataset.k));
 GIMACT=gimTop(c,st);SBACT=st.sb||[];DMW=[Math.min(1,(st.n-1)/2),c.boss?CFG.damage.weightBoss:CFG.damage.weightMob];
 const defPen=(CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty);
 const qi=quickIn(c,st);const t0=performance.now();
 const plan=recoCandidates(c,st,own,new Set(),defPen,qi);const tPlan=performance.now()-t0;
 const ck=ks=>ks.slice().sort().join(","),caseK=ck(caseKeys);
 const cands=plan.cands,pool=partyPool(cands).map(x=>x.s.key);
 const qt=plan.qt;const qIdx=qt.findIndex(t=>ck(t.keys)===caseK);
 const vIdx=plan.ranked.findIndex(x=>ck(x.combo.map(y=>y.s.key))===caseK);
 // 사례 팀을 화면과 같은 방식으로 만든 t(빠른 계산·내 정보 최종 능력치·배치·리더·브레이크)
 const pick=caseKeys.map(k=>cands.find(x=>x.s.key===k));
 let caseT=null,caseQPos=null,caseVPos=null;
 if(pick.every(Boolean)){const [v,got]=teamValue(pick,defPen);caseT=quickRank([{combo:pick,v,got}],qi)[0]||null;
  // 사례 팀이 풀 안 조합들 사이에 끼었다면 빠른 계산 순위 몇 위인가(quickRank 정렬 그대로 다시 세움)
  if(caseT){const qr=quickRank(plan.ranked.concat([{combo:pick,v,got,i:1e9}]),qi);caseQPos=qr.findIndex(t=>ck(t.keys)===caseK)+1;
   caseVPos=plan.ranked.filter(x=>x.v>v).length+1}}
 const box={all:qt};const scr=scrPick(qt,SCR_RK&&rkOf(c.key)?rkQuickTop(c,st,qt,SCR_RK):null);
 const byKey=new Map(qt.map(t=>[ck(t.keys),t]));
 const spec=t=>({keys:t.keys,party:simParty(t),bname:teamBreak(t)?.name||null,blv:teamBreak(t)?brkLv(teamBreak(t).name):null,
   vd:t.vd,rounds:t.q.rounds,left:t.q.left,v:t.v,power:t.q.power});
 const rows=quickRows(qt,st,1,{n:9,sc:null,result:()=>null,joint:null});
 // 진단: 풀 없이 보유 전원 4인 조합 전부를 같은 빠른 계산 순서로(시간도 잼)
 const t1=performance.now();const allc=[];const n=cands.length;let i=0;
 for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)for(let d=b+1;d<n;d++)for(let e=d+1;e<n;e++){const combo=[cands[a],cands[b],cands[d],cands[e]];allc.push({combo,v:0,got:null,i:i++})}
 const tGen=performance.now()-t1;const t2=performance.now();
 const qAll=quickRank(allc,qi);const tAll=performance.now()-t2;
 const fullPos=qAll.findIndex(t=>ck(t.keys)===caseK)+1;
 const vdCount=a=>a.reduce((o,t)=>(o[t.vd]=(o[t.vd]||0)+1,o),{});
 // 보유 전원 순위 상위 80 중 풀(24명) 밖 구원자를 품은 팀 수
 const poolSet=new Set(pool),top80=qAll.slice(0,80),outPool=top80.filter(t=>t.keys.some(k=>!poolSet.has(k))).length;
 const powerOf=k=>miProfile().results[k]?.power||0;
 const byPow=cands.map(x=>x.s.key).sort((a,b)=>powerOf(b)-powerOf(a));
 const U=[],UI=new Map(),pack=t=>{const pp=simParty(t);return {u:pp.units.map(u=>{const j=JSON.stringify(u);if(!UI.has(j)){UI.set(j,U.length);U.push(u)}return UI.get(j)}),
   leader:pp.leader,b:teamBreak(t)?.name||null,keys:t.keys}};
 const allSpecs=qt.map(pack);
 return {units:U,allSpecs,brkLv:Object.fromEntries([...new Set(allSpecs.map(x=>x.b).filter(Boolean))].map(b=>[b,brkLv(b)])),content:c.key,stage:st.tab+"|"+st.name,stageStr:c.key+"/"+st.tab+"/"+st.name,rp:st.rp||null,options:simOpt(c.key),seed:SIMQ.seed,
  scrRounds:SCR_ROUNDS,scrRk:SCR_RK,rk:rkOf(c.key),poolN:POOL_N,nCands:cands.length,nCombos:plan.ranked.length,
  pool,casePool:caseKeys.map(k=>pool.includes(k)),
  caseCandRank:caseKeys.map(k=>({k,scoreRank:cands.slice().sort((a,b)=>b.score-a.score).findIndex(x=>x.s.key===k)+1,
    dmgS:(D.dmg.units[k]||{}).s||0,dmgA:(D.dmg.units[k]||{}).a||0,powRank:byPow.indexOf(k)+1})),
  caseInRanked:vIdx>=0,caseQtIdx:qIdx,caseQPos,caseVPos,caseInScr:scr.includes(caseK),
  caseT:caseT?spec(caseT):null,
  quickVd:vdCount(qt),qtTop:qt.slice(0,10).map(spec),
  rows:rows.map(t=>spec(t)),
  scr:scr.map(k=>spec(byKey.get(k))),
  full:{n:qAll.length,genMs:tGen,rankMs:tAll,casePos:fullPos,vd:vdCount(qAll),top80OutOfPool:outPool,top:qAll.slice(0,10).map(t=>({keys:t.keys,vd:t.vd,rounds:t.q.rounds,left:t.q.left}))},
  ms:{plan:tPlan}}
}
"""


def serve():
    class H(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(('127.0.0.1', 0), partial(H, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def collect(myinfo, out):
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', r'E:\AI_mk2\pw-browsers')
    from playwright.sync_api import sync_playwright
    info = Path(myinfo).read_text(encoding='utf-8')
    seed = {'pn.myinfo': info, 'pn.simauto': '0'}
    srv = serve()
    base = 'http://127.0.0.1:%d' % srv.server_port
    res = []
    with sync_playwright() as p:
        br = p.chromium.launch()
        page = br.new_page(viewport={'width': 1280, 'height': 900})
        page.add_init_script("(s=>{for(const [k,v] of Object.entries(s))localStorage.setItem(k,v)})(%s)" % json.dumps(seed))
        # 자동 시뮬을 막음(수집만): 시험의 수동 모드와 같은 방식
        page.add_init_script("document.addEventListener('DOMContentLoaded',()=>{simAutoOn=()=>false;},{once:true})")
        page.goto(base + '/index.html')
        page.wait_for_function("() => window._ready && MI.info && MI.growth && !MI.pending", timeout=120000)
        assert page.evaluate('miMode()'), '내 정보 모드가 아님'
        for c in CASES:
            ci = page.evaluate("k=>contents.findIndex(c=>c.key===k)", c['content'])
            page.select_option('#content', value=str(ci))
            page.wait_for_timeout(500)
            si = page.evaluate("([t,n])=>cur.findIndex(s=>s.tab===t&&s.name===n)", [c['tab'], c['name']])
            assert si >= 0, c
            page.evaluate("i=>{const s=document.querySelector('#stage');if(![...s.options].some(o=>+o.value===i)){const q=document.querySelector('#q');if(q){q.value='';q.dispatchEvent(new Event('input'))}}}", si)
            page.wait_for_timeout(500)
            page.select_option('#stage', value=str(si))
            page.dispatch_event('#stage', 'change')
            page.wait_for_timeout(800)
            assert page.evaluate("()=>cur[$('stage').value].name") == c['name']
            assert page.evaluate("()=>miMode()")
            t = time.time()
            r = page.evaluate(COLLECT_JS, c['keys'])
            r['id'] = c['id']
            r['caseKeys'] = c['keys']
            r['wall'] = time.time() - t
            res.append(r)
            print(c['id'], 'pool', r['casePool'], 'inRanked', r['caseInRanked'], 'qPos', r['caseQPos'], '/', r['nCombos'],
                  'inScr', r['caseInScr'], 'scr', len(r['scr']), 'fullPos', r['full']['casePos'], '/', r['full']['n'],
                  'top80OutOfPool', r['full']['top80OutOfPool'], 'ms', round(r['full']['rankMs']), flush=True)
        br.close()
    srv.shutdown()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'collect.json').write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')


def run_team(task):
    from battlesim.web import run_auto
    stage, party, n, seed, opts = task
    r = json.loads(run_auto(stage, party, n, seed, opts))
    return {k: r.get(k) for k in ('prog', 'clear', 'n', 'progs', 'ttk', 't60')}


def opts_of(r, s):
    o = dict(r['options'])
    o['break_skill'] = {'name': s['bname'], 'level': s['blv']} if s['bname'] else None
    return o


def topq(xs, q=TOP_Q):
    s = sorted(xs, reverse=True)
    m = max(1, math.ceil(len(s) * q - 1e-9))
    return sum(s[:m]) / m


def boot(a, b, stat, n=2000, seed=7):
    rnd = random.Random(seed)
    d = sorted(stat([a[rnd.randrange(len(a))] for _ in a]) - stat([b[rnd.randrange(len(b))] for _ in b]) for _ in range(n))
    return d[int(n * .025)], d[int(n * .975)]


def scr_cmp_key(r):   # 화면 scrCmp(t60 없음: 작전·회랑)
    return (-(r.get('t60') if r.get('t60') is not None else r['clear']), -r['clear'], -(r.get('prog') or 0), r.get('ttk') or 1e9)


def evaluate(out, workers):
    data = json.loads((out / 'collect.json').read_text(encoding='utf-8'))
    ck = lambda ks: ','.join(sorted(ks))
    rep = []
    with ProcessPoolExecutor(workers) as ex:
        for r in data:
            cs = r['caseT']
            teams = list(r['scr'])
            if cs and ck(cs['keys']) not in {ck(t['keys']) for t in teams}:
                teams.append(dict(cs, extra=True))      # 진단: 사례 팀을 예선 후보 끝에 넣어 봄
            t0 = time.time()
            r1 = list(ex.map(run_team, [(r['stageStr'], t['party'], r['scrRounds'][0]['n'], r['seed'], opts_of(r, t)) for t in teams]))
            o1 = sorted(range(len(teams)), key=lambda i: (scr_cmp_key(r1[i]), i))
            # 화면 예선 순위는 사례 팀 없이 정함(사례 팀은 «넣었다면» 위치만)
            o1_site = [i for i in o1 if not teams[i].get('extra')]
            up = o1_site[:r['scrRounds'][1]['top']]
            case_i = next((i for i, t in enumerate(teams) if cs and ck(t['keys']) == ck(cs['keys'])), None)
            up2 = up + ([case_i] if case_i is not None and case_i not in up else [])
            r2 = dict(zip(up2, ex.map(run_team, [(r['stageStr'], teams[i]['party'], r['scrRounds'][1]['n'], r['seed'], opts_of(r, teams[i])) for i in up2])))
            o2 = sorted(up, key=lambda i: (scr_cmp_key(r2[i]), up.index(i)))
            site_order = o2 + [i for i in o1_site if i not in set(up)]
            case_r1 = (sorted(range(len(teams)), key=lambda i: (scr_cmp_key(r1[i]), i)).index(case_i) + 1) if case_i is not None else None
            case_r2 = (sorted(up2, key=lambda i: (scr_cmp_key(r2[i]), i)).index(case_i) + 1) if case_i is not None else None
            t_scr = time.time() - t0
            # 400판 재평가: 예선 상위 5 + 사례 팀
            fin = site_order[:5] + ([case_i] if case_i is not None else [])
            ev = list(ex.map(run_team, [(r['stageStr'], teams[i]['party'], 400, SEED, opts_of(r, teams[i])) for i in fin]))
            rows = []
            for i, e in zip(fin, ev):
                rows.append(dict(keys=teams[i]['keys'], case=i == case_i, scr8=r1[i], scr32=r2.get(i), prog=e['prog'], clear=e['clear'],
                                 top=topq(e['progs']), progs=e['progs'], bname=teams[i]['bname']))
            site = rows[:-1] if case_i is not None else rows
            best = max(site, key=lambda x: (x['top'], x['clear']))
            best_mean = max(site, key=lambda x: (x['clear'], x['prog']))     # 화면 기준(scrCmp: 클리어율 → 진행도)
            cr = rows[-1] if case_i is not None else None
            v = None
            if cr:
                lo, hi = boot(cr['progs'], best['progs'], topq)
                clo, chi = boot([1.0 if p >= 1 else 0.0 for p in cr['progs']], [1.0 if p >= 1 else 0.0 for p in best['progs']], lambda x: sum(x) / len(x))
                d = cr['top'] - best['top']
                mlo, mhi = boot(cr['progs'], best_mean['progs'], lambda x: sum(x) / len(x))
                v = dict(mean_diff=cr['prog'] - best_mean['prog'], mean_ci=[mlo, mhi], best_mean=best_mean['keys'], diff=d, rel=d / best['top'] if best['top'] else None, ci=[lo, hi], clear_diff=cr['clear'] - best['clear'], clear_ci=[clo, chi],
                         verdict='사이트가 놓침' if lo > 0 else '사이트 우위' if hi < 0 else '유의차 없음')
            rep.append(dict(id=r['id'], n_scr=len(r['scr']), case_in_scr=r['caseInScr'], case_scr8_rank=case_r1, of=len(teams),
                            case_scr32_rank=case_r2, of32=len(up2), scr_sec=t_scr, rows=rows,
                            best_site=best['keys'], verdict=v))
            print(r['id'], 'scr8 rank', case_r1, '/', len(teams), 'scr32', case_r2, '/', len(up2), 'verdict', v and v['verdict'],
                  v and round(v['rel'] or 0, 3), 'scr %.0fs' % t_scr, flush=True)
    (out / 'eval.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')


def full_party(r, x):
    return {'units': [r['units'][i] for i in x['u']], 'leader': x['leader']}


def full_screen(out, workers):
    """고칠 방향 후보 검증: 풀(24명) 안 조합 전부를 1판(시드 1)으로 거른 뒤 상위 120팀에 화면 예선(8→32판)을 그대로 적용."""
    data = json.loads((out / 'collect.json').read_text(encoding='utf-8'))
    ck = lambda ks: ','.join(sorted(ks))
    rep = []
    with ProcessPoolExecutor(workers) as ex:
        for r in data:
            sp = r['allSpecs']
            opt = lambda x: dict(r['options'], break_skill={'name': x['b'], 'level': r['brkLv'][x['b']]} if x['b'] else None)
            t0 = time.time()
            r1 = list(ex.map(run_team, [(r['stageStr'], full_party(r, x), 1, r['seed'], opt(x)) for x in sp], chunksize=16))
            t1 = time.time() - t0
            o1 = sorted(range(len(sp)), key=lambda i: (scr_cmp_key(r1[i]), i))
            case = next((i for i, x in enumerate(sp) if ck(x['keys']) == ck(r['caseKeys'])), None)
            pool = o1[:120]
            r8 = dict(zip(pool, ex.map(run_team, [(r['stageStr'], full_party(r, sp[i]), 8, r['seed'], opt(sp[i])) for i in pool])))
            o8 = sorted(pool, key=lambda i: (scr_cmp_key(r8[i]), o1.index(i)))
            up = o8[:20]
            r32 = dict(zip(up, ex.map(run_team, [(r['stageStr'], full_party(r, sp[i]), 32, r['seed'], opt(sp[i])) for i in up])))
            o32 = sorted(up, key=lambda i: (scr_cmp_key(r32[i]), up.index(i)))
            fin = o32[:5]
            ev = list(ex.map(run_team, [(r['stageStr'], full_party(r, sp[i]), 400, SEED, opt(sp[i])) for i in fin]))
            site = json.loads((out / 'eval.json').read_text(encoding='utf-8'))
            srow = next(x for x in site if x['id'] == r['id'])
            sb = max([x for x in srow['rows'] if not x['case']], key=lambda x: (x['clear'], x['prog']))
            nb_i = max(range(len(fin)), key=lambda j: (ev[j]['clear'], ev[j]['prog']))
            nb = ev[nb_i]
            mlo, mhi = boot(nb['progs'], sb['progs'], lambda x: sum(x) / len(x))
            tlo, thi = boot(nb['progs'], sb['progs'], topq)
            row = dict(id=r['id'], n=len(sp), sec1=t1, case_rank1=(o1.index(case) + 1) if case is not None else None,
                       case_in120=case in pool if case is not None else None, case_rank8=(o8.index(case) + 1) if case in pool else None,
                       top5=[dict(keys=sp[i]['keys'], prog=e['prog'], clear=e['clear'], top=topq(e['progs'])) for i, e in zip(fin, ev)],
                       new_best=sp[fin[nb_i]]['keys'], new_vs_site_mean=[nb['prog'] - sb['prog'], mlo, mhi],
                       new_vs_site_top=[topq(nb['progs']) - topq(sb['progs']), tlo, thi], runs=len(sp) + 120 * 8 + 20 * 24)
            rep.append(row)
            print(r['id'], 'n', len(sp), '1판 %.0fs' % t1, 'case1', row['case_rank1'], 'in120', row['case_in120'], 'case8', row['case_rank8'],
                  'new-site mean %+.3f [%+.3f,%+.3f]' % tuple(row['new_vs_site_mean']), 'top %+.3f [%+.3f,%+.3f]' % tuple(row['new_vs_site_top']), flush=True)
    (out / 'full_screen.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['collect', 'eval', 'full'])
    ap.add_argument('--myinfo', default='E:/AI_mk2/role-private/op4212/myinfo_1121.json')
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    if ROOT in out.resolve().parents:
        raise SystemExit('--out 은 저장소 밖이어야 함(계정 결과)')
    if a.cmd == 'collect':
        collect(a.myinfo, out)
    elif a.cmd == 'eval':
        evaluate(out, a.workers)
    else:
        full_screen(out, a.workers)


if __name__ == '__main__':
    main()
