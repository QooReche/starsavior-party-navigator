"""Cosmo direct entry is open; ordinary drafts and guild restriction stay intact."""
from playwright.sync_api import sync_playwright
from test_direct_party import ready
from test_page import test_server


def test_entry(browser, base):
    for width in (1280, 360):
        def setup(page):
            page.add_init_script("localStorage.setItem('pn.direct.v1',JSON.stringify({v:1,slots:[{key:'luna',grown:false},null,null,null],leader:'luna',brk:'auto'}))")
        p=ready(browser,base,width,info=None,query='?c=cosmo&pm=direct&auto=0',setup=setup)
        assert p.locator('#cosmo-direct-panel').is_visible()
        assert p.locator('#direct-panel').is_hidden()
        assert p.locator('#cosmo-direct-panel [role=tab]').count()==3
        draft=p.evaluate('JSON.stringify(DIRECT.draft)')
        for key in ('op','cube','guild','cosmo'):
            p.select_option('#content',p.evaluate('key=>String(contents.findIndex(c=>c.key===key))',key))
            assert p.locator('#cosmo-direct-panel').is_visible()==(key=='cosmo')
            assert p.locator('#direct-panel').is_visible()==(key!='cosmo')
            assert p.locator('#mode-strip [data-pn-mode=direct]').is_enabled()
            if key=='guild':assert '아직 안 됨' in p.locator('#direct-state').inner_text()
        assert p.evaluate('JSON.stringify(DIRECT.draft)')==draft
        p.evaluate("directNavigate('reco');directNavigate('home')")
        p.wait_for_function("DIRECT.mode==='home'")
        p.locator('#start-screen [data-pn-mode=direct]').click()
        assert p.locator('#cosmo-direct-panel').is_visible()
        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert not p.errors,p.errors
        p.close()

if __name__=='__main__':
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            test_entry(browser,base)
            print('PASS cosmo direct entry: 1280/360, saved draft, content transitions, guild restriction, home entry')
        finally:browser.close()
