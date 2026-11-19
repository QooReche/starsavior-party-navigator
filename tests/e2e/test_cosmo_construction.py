"""Cosmo-only direct entry block, real DOM at wide/narrow widths (no worker needed)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_direct_party import ready
from test_page import test_server

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'local/cosmo-construction'
MESSAGE = '코스모 게이트 직접 편성(3파티)은 공사 중이에요 · 지금은 자동 추천의 «3보스 편성 찾기»를 써 주세요'


def test_cosmo_construction(browser, base):
    OUT.mkdir(parents=True, exist_ok=True)
    for width in (1280, 360):
        def setup(page):
            # Saved local draft survives both the blocked entry and content changes.
            page.add_init_script("localStorage.setItem('pn.direct.v1',JSON.stringify({v:1,slots:[{key:'luna',grown:false},null,null,null],leader:'luna',brk:'auto'}))")
        page = ready(browser, base, width, info=None, query='?c=cosmo&pm=direct&auto=0', setup=setup)
        notice = page.locator('#direct-construction')
        assert notice.is_visible()
        assert page.locator('#direct-panel').is_hidden()
        assert MESSAGE in notice.inner_text()
        draft = page.evaluate('JSON.stringify(DIRECT.draft)')
        assert page.evaluate('DIRECT.draft.slots[0].key') == 'luna'

        def buttons(blocked):
            for selector in ('#mode-strip [data-pn-mode=direct]', '#start-screen [data-pn-mode=direct]'):
                b = page.locator(selector)
                assert b.is_disabled() == blocked
                assert b.get_attribute('aria-disabled') == str(blocked).lower()
                if blocked:
                    assert b.get_attribute('title') == '공사 중'
                    reason = page.locator('#' + b.get_attribute('aria-describedby'))
                    assert '공사 중' in reason.inner_text()
                else:
                    assert b.get_attribute('aria-describedby') is None

        def content(key):
            # Check immediately in the same event turn, without waits hiding a delayed update.
            result = page.evaluate('''key=>{
                const el=document.querySelector('#content');el.value=contents.findIndex(c=>c.key===key);
                el.dispatchEvent(new Event('change',{bubbles:true}));
                return {disabled:document.querySelector('#mode-strip [data-pn-mode=direct]').disabled,
                  notice:!document.querySelector('#direct-construction').hidden};
            }''', key)
            assert result == {'disabled': key == 'cosmo', 'notice': key == 'cosmo'}
            buttons(key == 'cosmo')

        buttons(True)
        img = notice.locator('img')
        img.scroll_into_view_if_needed()
        page.wait_for_function("document.querySelector('#direct-construction img').naturalWidth>0")
        assert img.get_attribute('aria-hidden') == 'true'
        assert img.get_attribute('data-gwen-art') == 'construction'
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.screenshot(path=str(OUT / f'construction-{width}.png'), full_page=True)
        for key in ('op', 'cube', 'guild', 'cosmo', 'op', 'cosmo'):
            content(key)
        assert page.evaluate('JSON.stringify(DIRECT.draft)') == draft
        notice.locator('[data-pn-mode=reco]').click()
        assert notice.is_hidden()
        assert page.evaluate('DIRECT.mode') == 'reco'
        assert page.locator('#direct-panel').is_hidden()
        page.evaluate("directNavigate('home')")
        buttons(True)
        page.locator('#start-screen .start-direct h2').click()
        assert page.evaluate('DIRECT.mode') == 'home', 'card click bypassed disabled button'
        page.evaluate("directNavigate('direct')")
        assert page.evaluate('DIRECT.mode') == 'home', 'programmatic navigation bypassed block'
        # Broken approved artwork uses the existing board scene, with decorative semantics.
        page.route('**/gwen/construction.*', lambda route: route.abort())
        page.goto(base + '/index.html?c=cosmo&pm=direct&auto=0')
        page.wait_for_function('window._ready')
        page.locator('#direct-construction img').scroll_into_view_if_needed()
        page.wait_for_function("(()=>{const i=document.querySelector('#direct-construction img');return i?.dataset.gwenArt==='board'&&i.naturalWidth>0})()")
        assert MESSAGE in notice.inner_text()
        assert not page.errors, page.errors
        page.close()


if __name__ == '__main__':
    with test_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            test_cosmo_construction(browser, base)
            print('PASS cosmo construction: 1280/360, direct URL + saved draft, transitions, accessibility, card guard, reco exit, board fallback')
        finally:
            browser.close()
