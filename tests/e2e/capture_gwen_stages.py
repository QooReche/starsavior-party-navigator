"""Repeatable before/after captures, synthetic fixtures, no simulation workers."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server
from test_direct_party import ready

ROOT = Path(__file__).resolve().parents[2]


def capture(browser, base, out, width, mode):
    query = '?pm=' + ('direct&c=cosmo' if mode == 'cdirect' else mode)
    def setup(p):
        p.emulate_media(reduced_motion='reduce')
        p.add_init_script("Math.random=()=>.42; Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>2});")
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
