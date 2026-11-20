"""Compare the production recommendation pipeline; account/results stay private.

Run with Playwright Python: <script> <account> <outside-repo result.json>.
Two native engine processes replace only the browser worker transport. Selection
uses the production screen/final budgets and seed; evaluation uses 200 fresh runs.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import low_priority


def worker():
    from battlesim.web import run_auto
    low_priority()
    version = json.loads((ROOT / 'sim/manifest.json').read_text(encoding='utf8'))['ver']
    for line in sys.stdin:
        m = json.loads(line)
        try:
            rows = []
            for t in m['teams']:
                opts = {**m.get('options', {}), **t.get('options', {})}
                if m.get('options', {}).get('rules_override') or t.get('options', {}).get('rules_override'):
                    opts['rules_override'] = {**m.get('options', {}).get('rules_override', {}),
                                              **t.get('options', {}).get('rules_override', {})}
                r = json.loads(run_auto(m['stage'], t['party'], m['n_runs'], m['seed'], opts))
                r['ver'] = version
                rows.append(dict(key=t['key'], result=r))
            print(json.dumps(rows, ensure_ascii=False), flush=True)
        except Exception as e:
            print(json.dumps(dict(error=str(e))), flush=True)


BRIDGE = """(() => {
 localStorage.setItem('pn.simauto','0');
 Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>3});
 Object.defineProperty(navigator,'deviceMemory',{get:()=>2});
 window.Worker=class {
  postMessage(m){if(m.type!=='run')return;this.onmessage?.({data:{...m,type:'stage',msg:'준비 끝'}});
   nativeRun(m).then(rows=>{if(this.dead)return;
    for(const row of rows)this.onmessage?.({data:{...m,...row,type:'team'}});
    this.onmessage?.({data:{...m,type:'done'}});
   }).catch(e=>this.onmessage?.({data:{...m,type:'error',msg:String(e)}}));
  }
  terminate(){this.dead=true;}
 };
})();"""


async def measure(account, output):
    from playwright.async_api import async_playwright
    sys.path.insert(0, str(ROOT / 'tests/e2e'))
    from test_page import test_server
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', r'E:\AI_mk2\pw-browsers')
    # Account is read once, never copied to a file or printed.
    info = json.loads(account.read_text(encoding='utf-8-sig'))
    queue = asyncio.Queue()
    children = []
    for _ in range(2):
        proc = await asyncio.create_subprocess_exec(sys.executable, '-X', 'utf8', '-I', __file__, '--worker',
                                                   stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                                   limit=32 * 1024 * 1024)
        children.append(proc)
        queue.put_nowait(proc)

    async def native(m):
        proc = await queue.get()
        try:
            proc.stdin.write((json.dumps(m, ensure_ascii=False) + '\n').encode('utf8'))
            await proc.stdin.drain()
            raw = await proc.stdout.readline()
            if not raw:
                raise RuntimeError('native worker exited')
            result = json.loads(raw)
            if isinstance(result, dict) and 'error' in result:
                raise RuntimeError(result['error'])
            return result
        finally:
            queue.put_nowait(proc)

    result = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                  selectionSeed=1, evaluationSeed=20261121, evaluationRuns=200,
                  score='mean progress * 100; not an in-game score', rows=[])
    stages = [('op', None, 'SECTOR 45-35'), ('op', None, 'SECTOR 45-36'),
              ('clo', '성간 회랑', 'FLOOR 400'), ('clo', '성간 회랑', 'FLOOR 500'),
              ('rush', '공허매장자', '공허매장자 Ⅳ'), ('equip', '잊혀진 맹세', '잊혀진 맹세 XX')]
    try:
        with test_server() as base:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch()
                try:
                    for ck, tab, name in stages:
                        pair = dict(content=ck, tab=tab, name=name, variants=[])
                        for neutral in [False, True]:
                            started = time.monotonic()
                            page = await browser.new_page()
                            errors = []
                            page.on('pageerror', lambda e: errors.append(str(e)))
                            await page.expose_function('nativeRun', native)
                            await page.add_init_script(BRIDGE)
                            await page.goto(base + '/index.html?c=op&pm=reco&auto=0')
                            await page.wait_for_function('window._ready && !!QK.d')
                            await page.evaluate('info=>miApply(info)', info)
                            await page.wait_for_function('MI.info && MI.growth && !MI.pending')
                            await page.select_option('#content', await page.evaluate('ck=>String(contents.findIndex(c=>c.key===ck))', ck))
                            si = await page.evaluate('x=>String(cur.findIndex(s=>s.name===x.name&&(!x.tab||s.tab===x.tab)))', dict(tab=tab, name=name))
                            if si == '-1':
                                raise RuntimeError('public stage not found: ' + name)
                            await page.select_option('#stage', si)
                            await page.evaluate('neutral=>{CFG.recommendation.neutralRoles=neutral;CFG.recommendation.placementBaseline=false;CFG.recommendation.placementCompare=false;}', neutral)
                            await page.wait_for_timeout(500)
                            print('selecting', ck, name, 'neutral' if neutral else 'legacy', flush=True)
                            await page.evaluate("window.measureError=null;window.measureDone=false;recoEnsure().then(()=>measureDone=true,e=>{measureError=String(e);measureDone=true;})")
                            last = time.monotonic()
                            while not await page.evaluate('measureDone'):
                                await asyncio.sleep(1)
                                if time.monotonic() - last > 45:
                                    print('recommendation running', ck, name, flush=True)
                                    last = time.monotonic()
                            error = await page.evaluate('measureError')
                            if error or errors:
                                raise RuntimeError(error or errors)
                            chosen = await page.evaluate("""() => {const snap=recoSnapshot();snap.plan(1);const t=LASTQ[1].rows[0];
                             return {party:snap.party(t),brk:snap.breakFor(t),options:snap.options,heuristic:t.v,
                               selection:snap.result(t),tab:snap.st.tab,stage:snap.c.key+'/'+snap.st.tab+'/'+snap.st.name};}""")
                            evaluated = (await native(dict(stage=chosen['stage'], teams=[dict(key='eval', party=chosen['party'], options=dict(break_skill=chosen['brk']))],
                                                           options={**chosen['options'], 'raw_runs': True}, n_runs=200, seed=20261121)))[0]['result']
                            raw = json.loads(evaluated['raw'])
                            assert evaluated['n'] == len(raw) == 200
                            assert chosen['selection'] is not None, 'selected team lacks final simulation'
                            turns = [r[2] for r in raw if r[0] == 'clear' and r[2] is not None]
                            pair['tab'] = chosen['tab']
                            pair['variants'].append(dict(neutral=neutral, selected=chosen, evaluation=evaluated,
                                                         clear=evaluated['clear'], score=100 * sum(r[3] for r in raw)/len(raw),
                                                         turns=sum(turns)/len(turns) if turns else evaluated.get('ttk'),
                                                         seconds=time.monotonic()-started))
                            await page.close()
                            print('completed', ck, name, 'neutral' if neutral else 'legacy', flush=True)
                        result['rows'].append(pair)
                        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
                finally:
                    await browser.close()
    finally:
        for proc in children:
            if proc.returncode is None:
                proc.terminate()
        await asyncio.gather(*(p.wait() for p in children))


def main():
    if '--worker' in sys.argv:
        worker()
        return
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('account', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    account, output = args.account.resolve(), args.output.resolve()
    if output.is_relative_to(ROOT) or output == account:
        ap.error('output must be outside repository and distinct from account')
    output.parent.mkdir(parents=True, exist_ok=True)
    low_priority()
    asyncio.run(measure(account, output))


if __name__ == '__main__':
    main()
