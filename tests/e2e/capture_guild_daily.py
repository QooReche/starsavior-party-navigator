"""Daily state captures with the e2e controlled worker; no private account or engine."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server, FULL
from test_direct_party import ready
from test_guild_daily_ui import SETUP

OUT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'local/guild-ux3'

def capture(p,name):
    p.locator('#guild-search').scroll_into_view_if_needed()
    p.screenshot(path=str(OUT/(name+'.png')),full_page=True)
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')

def audit(p,count):
    assert p.locator('#guild-search .cg-tab').count()==count
    cols=p.locator('[data-k=gs-team-summary]').evaluate('(e)=>getComputedStyle(e).gridTemplateColumns.split(" ").length')
    if p.viewport_size['width']==1280:assert cols==count,(cols,count)
    assert p.locator('#guild-search .cg-say [data-gwen-slot="guildSearch-result"]').count()==1
    p.wait_for_function('document.querySelector(\'[data-gwen-slot="guildSearch-result"] img\')?.naturalWidth>0')
    assert p.locator('#guild-search .season-actions').bounding_box()['y']<p.locator('#guild-search .cs-boss').first.bounding_box()['y']

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            for width in (1280,390):
                p=ready(browser,base,width,info=FULL,query='?pm=reco&season=force')
                try:
                    p.select_option('#content',p.evaluate('String(contents.findIndex(c=>c.key==="guild"))'))
                    p.evaluate(SETUP)
                    p.evaluate("Date.now=()=>Date.parse('2026-11-27T12:00:00+09:00');renderGuildSearch(true)")
                    capture(p,f'guild_idle_closed_{width}')
                    p.evaluate("Date.now=()=>Date.parse('2026-11-28T12:00:00+09:00');renderGuildSearch(true)")
                    capture(p,f'guild_idle_open_{width}')
                    p.locator('[data-gs=start]').click();p.wait_for_function('dailyQueue.length>0')
                    eta=p.locator('[data-k=gs-eta]').bounding_box()
                    assert abs(eta['x']+eta['width']/2-width/2)<2,eta
                    capture(p,f'guild_run_{width}')
                    p.evaluate('dailyFlush()');p.wait_for_function('GSR.phase==="done"',timeout=20000)
                    audit(p,1);capture(p,f'guild_result_1_{width}')
                    p.locator('[data-gs=follow]').click();p.wait_for_function('GSR.phase==="done" && GSR.teams.length===2',timeout=20000)
                    audit(p,2);capture(p,f'guild_result_2_{width}')
                    p.evaluate('dailyAuto=false;dailyQueue=[];dailyStopStage=7')
                    p.locator('[data-gs=start]').click();p.wait_for_function('dailyQueue.length>0')
                    p.evaluate('dailyFlush()');p.wait_for_function('GSR.plan?.stages[GSR.stageIndex]?.policyStage===7 && !dailyAuto',timeout=20000)
                    p.locator('[data-gs=partial]').click();p.wait_for_function('GSR.phase==="done"',timeout=20000)
                    assert p.evaluate('GSR.partial && !GSR.teams[0].evaluation.placementComplete')
                    audit(p,1);capture(p,f'guild_stopped_{width}')
                    assert not p.errors,p.errors
                    print('PASS daily captures and card geometry',width,flush=True)
                finally:
                    p.evaluate('dailyAuto=false;GSR.id++;GSR.handle?.cancel()');p.close()
        finally:browser.close()
