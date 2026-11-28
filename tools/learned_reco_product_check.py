"""Check the default product recommendation against frozen U360 measurements.

Only transport requests are observed. No recommendation function, candidate,
setting, worker result, or measurement selection policy is injected.
Account inputs and outputs must remain in the private measurement directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from learned_reco_measure import ROOT, WORKSPACE, check_output, memory_guard, save_json


OBSERVE = r"""() => {
  const original = Worker.prototype.postMessage;
  window.productCheck = {active:false, requests:[]};
  Worker.prototype.postMessage = function(message, ...args) {
    if (window.productCheck.active && message?.type === 'run') {
      window.productCheck.requests.push({runs:message.n_runs, seed:message.seed,
        teams:message.teams.map(t => t.key)});
    }
    return original.call(this, message, ...args);
  };
}"""

START = r"""() => {
  if (CFG.recommendation?.learnedUnion?.value !== true) throw Error('Default U360 disabled');
  if (SIMQ.seed !== 1 || SIMQ.n !== 100) throw Error('Unexpected default seed/runs');
  const started = performance.now();
  productCheck.active = true;
  productCheck.done = false;
  directRun('reco').then(async () => {
    if (!DIRECT.bundle?.steps.every(s => s.status === 'done'))
      throw Error('Recommendation bundle did not complete: '+JSON.stringify(DIRECT.bundle?.steps));
    const completed = await RECO.task.promise;
    await new Promise(requestAnimationFrame);
    const c = contents[$('content').value], st = cur[$('stage').value];
    const sc = SIMQ.scr[scrKey(st,1)], t = LASTQ[1].rows[0];
    if (UiShared.teamKey(completed.team.keys) !== UiShared.teamKey(t.keys))
      throw Error('Final redraw changed the locked winner');
    if (!SIMQ.res[simSig(st,t)]) throw Error('Winner has no finalized result');
    productCheck.result = {
      seconds:(performance.now()-started)/1000,
      winner:{keys:t.keys, party:simParty(t), brk:teamBreak(t)},
      searchGames:productCheck.requests.reduce((n,r)=>n+r.runs*r.teams.length,0),
      fullN:sc.fullN, screen:{pool:sc.pool,order:sc.order,up:sc.up},
      settings:CFG.recommendation.learnedUnion,
      scan:{full:sc.full.length,observed:Object.keys(sc.res0).length,
        sample:sc.union?.sample?.length,outside:sc.union?.outside?.length},
      requests:productCheck.requests,
      browserEntry:'default directRun(reco), passive Worker.postMessage observation'
    };
  }).catch(e => productCheck.error=e.stack).finally(() => {
    productCheck.active=false; productCheck.done=true;
  });
}"""


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parity(result, expected):
    return dict(party=result['winner']['party'] == expected['winner']['party'],
                brk=result['winner']['brk'] == expected['winner']['brk'],
                searchGames=result['searchGames'] == expected['searchGames'],
                fullN=result['fullN'] == expected['fullN'],
                screen=result['screen'] == expected['screen'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--collect', required=True)
    ap.add_argument('--reference', required=True, help='Directory with frozen *_1_U360_browser/native.json')
    ap.add_argument('--myinfo', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--ids', default='')
    ap.add_argument('--screenshot', help='PNG in the designated learned_reco_1127/shots directory')
    ap.add_argument('--timeout', type=int, default=1800)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    check_output({'private': True}, out)
    shot = Path(a.screenshot).resolve() if a.screenshot else None
    if shot and not shot.is_relative_to((WORKSPACE / '_work' / 'accel-golden' / 'learned_reco_1127' / 'shots').resolve()):
        ap.error('Screenshot must stay in the designated shots directory')
    rows = json.loads(Path(a.collect).read_text(encoding='utf-8'))
    rows = [r for r in rows if not a.ids or r['id'] in a.ids.split(',')]
    if not rows or not all(r.get('private') for r in rows):
        ap.error('Expected private collected account stages')
    out.mkdir(parents=True, exist_ok=True)
    scratch = out / 'tmp'
    scratch.mkdir(exist_ok=True)
    os.environ['TEMP'] = os.environ['TMP'] = str(scratch)
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(WORKSPACE / '_env' / 'pw-browsers'))
    from playwright.sync_api import sync_playwright
    from stage_reco_check import serve
    from bench_screen import MemPeak

    info = Path(a.myinfo).read_text(encoding='utf-8')
    fingerprints = dict(collect=digest(a.collect), myinfo=digest(a.myinfo),
                        files={f:digest(ROOT / f) for f in
                               ('index.html', 'recommend_runtime.js', 'recommend_learned.js',
                                'cosmo_learned.js', 'party_contents.json', 'sim/manifest.json')})
    server = serve()
    base = 'http://127.0.0.1:%d/' % server.server_port
    summary = []
    try:
        with sync_playwright() as p:
            for row in rows:
                expected_file = next((Path(a.reference) / f"{row['id']}_1_U360_{kind}.json"
                                      for kind in ('browser', 'native')
                                      if (Path(a.reference) / f"{row['id']}_1_U360_{kind}.json").exists()), None)
                if not expected_file:
                    raise RuntimeError('Missing frozen reference for '+row['id'])
                expected = json.loads(expected_file.read_text(encoding='utf-8'))
                file = out / f"{row['id']}_1_U360_product.json"
                memory_guard()
                br = p.chromium.launch()
                try:
                    page = br.new_page(viewport={'width':1280, 'height':900})
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
                    page.add_init_script("Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>9}); Object.defineProperty(navigator,'deviceMemory',{get:()=>8});")
                    page.add_init_script('(s=>{localStorage.setItem("pn.myinfo",s);localStorage.setItem("pn.simauto","0")})(%s)' % json.dumps(info))
                    page.goto(base+'index.html?auto=0&pm=reco')
                    page.wait_for_function('window._ready && QK.d && MI.info && MI.growth && !MI.pending', timeout=120000)
                    ci = page.evaluate('k=>contents.findIndex(c=>c.key===k)', row['c']['key'])
                    page.select_option('#content', str(ci))
                    page.wait_for_timeout(500)
                    si = page.evaluate('([t,n])=>cur.findIndex(s=>s.tab===t&&s.name===n)', [row['st']['tab'],row['st']['name']])
                    assert si >= 0, 'Missing collected stage'
                    page.evaluate("()=>{const q=$('q');q.value='';q.dispatchEvent(new Event('input'));}")
                    page.wait_for_timeout(300)
                    page.select_option('#stage', str(si))
                    page.select_option('#rk', str(row['options'].get('rekindle',0)), force=True)
                    page.wait_for_timeout(500)
                    page.evaluate("directNavigate('direct')")
                    page.wait_for_function('!!DIRECT.draft')
                    page.evaluate("directNavigate('reco')")
                    assert page.evaluate("simOpt(contents[$('content').value].key)") == row['options'], 'Product content options changed'
                    page.evaluate(OBSERVE)
                    with MemPeak() as peak:
                        page.evaluate(START)
                        deadline, logged = time.monotonic()+a.timeout, 0
                        while True:
                            state = page.evaluate("({done:productCheck.done,error:productCheck.error,scan:scrAlertOf(RECO.task?.sc)==='scan'&&!!RECO.task?.sc?.got,forced:document.body.classList.contains('is-forced'),message:RECO.task?.message,bundle:DIRECT.bundle?.steps,simError:SIMQ.err,sc:RECO.task?.sc&&{round:RECO.task.sc.round,got:RECO.task.sc.got,left:RECO.task.sc.left,fullDone:RECO.task.sc.fullDone,sample:Object.keys(RECO.task.sc.union?.observed||{}).length,res0:Object.keys(RECO.task.sc.res0||{}).length}})")
                            if shot and not shot.exists() and state['scan'] and state['forced']:
                                shot.parent.mkdir(parents=True, exist_ok=True)
                                page.screenshot(path=str(shot), full_page=True)
                            if state['done']:
                                break
                            if time.monotonic() > deadline:
                                raise TimeoutError('Product recommendation exceeded timeout')
                            if time.monotonic()-logged > 30:
                                save_json(out / f"{row['id']}_progress.json", dict(state=state, pageErrors=errors))
                                print(row['id'], 'product recommendation running', flush=True)
                                logged = time.monotonic()
                            page.wait_for_timeout(2000)
                        if state.get('error'):
                            save_json(out / f"{row['id']}_failure.json", dict(state=state, pageErrors=errors,
                                      requests=page.evaluate('productCheck.requests'),fingerprints=fingerprints,
                                      screen=page.evaluate("()=>{const s=RECO.task?.sc;return s&&{full:s.full,pool:s.pool,order:s.order,up:s.up,fullN:s.fullN,res0:s.res0,res:s.res,res2:s.res2,union:s.union&&{sample:s.union.sample,outside:s.union.outside,rho:s.union.rho}}}")))
                            raise RuntimeError('Recommendation failed; inspect private failure JSON for '+row['id'])
                        result = page.evaluate('productCheck.result')
                    result.update(id=row['id'], seed=1, private=True, peakMB=peak.peak,
                                  fingerprints=fingerprints, reference_sha256=digest(expected_file))
                    result['parity'] = parity(result, expected)
                    save_json(file, result)
                    summary.append(dict(id=row['id'], parity=result['parity']))
                    save_json(out / 'summary.json', summary)
                    print(row['id'], 'PASS' if all(result['parity'].values()) else 'FAIL', result['parity'], flush=True)
                finally:
                    br.close()
    finally:
        server.shutdown()
    if shot and not shot.exists():
        raise AssertionError('No forced-scan screenshot captured')
    assert all(all(r['parity'].values()) for r in summary), 'Product differs from frozen U360 measurements'


if __name__ == '__main__':
    main()
