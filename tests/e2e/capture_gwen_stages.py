"""Repeatable before/after captures, synthetic fixtures, no simulation workers."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server
from test_direct_party import ready

ROOT = Path(__file__).resolve().parents[2]


def result_fixture(p, mode):
    if mode == 'reco':
        p.evaluate('''() => {
          recoClearTimer();clearTimeout(_rt);SIMQ.auto=false;SIMQ.kick=false;REQ=true;RECO.standard=true;
          document.querySelectorAll('#own input').forEach((x,i)=>x.checked=i<8);updCount();run(true);
          const st=cur[$('stage').value];
          for(const box of Object.values(LASTQ))for(const t of box.rows)
            SIMQ.res[simSig(st,t)]={n:100,clear:.8,ci:[.7,.9],ta:35,ttk:35,frac:1,u:Object.fromEntries(t.keys.map(k=>[k,[.25,0]]))};
          run(true);
        }''')
    elif mode == 'direct':
        p.evaluate('''() => {
          for(const [slot,key] of ['luna','smile','carnelia','asherah-voyager'].entries())directChange({type:'put',key,slot});
          DIRECT.versions={engine:'capture',data:'capture'};directSync();const snap=DIRECT.expected.now;
          DIRECT.rows.now={sig:snap.sig,snapshot:snap,status:'done',result:{n:100,clear:.8,ci:[.7,.9],ta:35,frac:1,u:{}}};directResultsPaint();
        }''')
    elif mode == 'cdirect':
        p.evaluate('''() => {
          const keys=R.slice(0,12).map(s=>s.key);
          D.cosmoRaid.bosses.forEach((b,i)=>keys.slice(i*4,i*4+4).forEach((key,slot)=>cdChange({type:'draft',boss:b.key,action:{type:'put',key,slot}})));
          cdSync();for(const [boss,j] of Object.entries(CDIRECT.jobs))CDIRECT.cache.set(j.sig,{result:{clear:.8,ta:35,cosmo:{mean:10000,top:12000,clear:.8,frac:1}}});cdPaint();
        }''')


def capture(browser, base, out, width, mode):
    query = '?pm=' + ('direct&c=cosmo' if mode == 'cdirect' else mode)
    def setup(p):
        p.add_init_script("Math.random=()=>.42; if(navigator.hardwareConcurrency!==2)Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>2,configurable:true});")
    p = ready(browser, base, width, info=None, query=query, setup=setup)
    try:
        if mode == 'reco':
            p.evaluate("recoGwenShow(true,.65)")
        selector = {'home':'#start-screen', 'reco':'#reco-gwen-stage',
                    'direct':'#direct-panel', 'cdirect':'#cosmo-direct-panel'}[mode]
        p.locator(selector).scroll_into_view_if_needed()
        p.wait_for_function("document.querySelector('.gwen-lane-actor img')?.naturalWidth>0")
        p.wait_for_timeout(300)
        p.screenshot(path=str(out / f'{mode}-{width}.png'), full_page=True, animations='disabled')
        if mode != 'home':
            result_fixture(p, mode)
            result_selector = {'reco':'#out .result-summary','direct':'#direct-result-lane','cdirect':'[data-cd-gwen-slot]'}[mode]
            p.locator(result_selector).scroll_into_view_if_needed()
            p.wait_for_function("s=>document.querySelector(s+' img')?.naturalWidth>0", arg=result_selector)
            p.wait_for_timeout(300)
            p.screenshot(path=str(out / f'{mode}-result-{width}.png'), full_page=True, animations='disabled')
        assert not p.errors, p.errors
    finally:
        p.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('output')
    args = ap.parse_args()
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)
    with test_server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for width in (1280, 390):
                for mode in ('home', 'reco', 'direct', 'cdirect'):
                    capture(browser, base, out, width, mode)
                    print(f'PASS capture {mode} {width}', flush=True)
        finally:
            browser.close()
